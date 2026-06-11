"""Worker queue routing tests (§14, v4.11).

An ARQ worker fails any job whose function it does not have registered, so
queue routing is part of the job contract: every enqueue of an ingestion job
must pass _queue_name=INGESTION_QUEUE, and default-queue jobs must not set a
queue name. These tests statically scan every enqueue_job call site in api/
and workers/ and check it against the functions each worker registers.
"""

import re
from pathlib import Path

from workers.ingestion import WorkerSettings as IngestionWorkerSettings
from workers.main import WorkerSettings as DefaultWorkerSettings
from workers.queues import INGESTION_QUEUE

_REPO_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_FUNCTIONS = {f.__name__ for f in DefaultWorkerSettings.functions}  # type: ignore[attr-defined]
_INGESTION_FUNCTIONS = {f.__name__ for f in IngestionWorkerSettings.functions}  # type: ignore[attr-defined]


def _enqueue_call_sites() -> list[tuple[str, str, str]]:
    """Return (location, job_name, call_text) for every enqueue_job call in api/ and workers/."""
    sites: list[tuple[str, str, str]] = []
    for directory in ("api", "workers"):
        for path in sorted((_REPO_ROOT / directory).rglob("*.py")):
            source = path.read_text()
            for match in re.finditer(r"\.enqueue_job\(", source):
                # Capture the full call by tracking paren depth from the open paren.
                depth = 0
                end = match.end() - 1
                while end < len(source):
                    if source[end] == "(":
                        depth += 1
                    elif source[end] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    end += 1
                call_text = source[match.start() : end + 1]
                name_match = re.search(r'"(\w+)"', call_text)
                assert name_match is not None, f"unparseable enqueue_job call in {path}"
                line = source[: match.start()].count("\n") + 1
                location = f"{path.relative_to(_REPO_ROOT)}:{line}"
                sites.append((location, name_match.group(1), call_text))
    return sites


def test_workers_register_disjoint_function_sets() -> None:
    overlap = _DEFAULT_FUNCTIONS & _INGESTION_FUNCTIONS
    assert not overlap, f"functions registered on both workers: {overlap}"


def test_ingestion_worker_owns_the_ingestion_queue() -> None:
    assert IngestionWorkerSettings.queue_name == INGESTION_QUEUE
    assert not hasattr(DefaultWorkerSettings, "queue_name"), (
        "default worker must consume ARQ's default queue"
    )


def test_every_enqueued_function_is_registered_on_a_worker() -> None:
    registered = _DEFAULT_FUNCTIONS | _INGESTION_FUNCTIONS
    for location, job_name, _ in _enqueue_call_sites():
        assert job_name in registered, (
            f"{location}: enqueues {job_name!r}, which no worker registers"
        )


def test_enqueue_sites_route_to_the_owning_queue() -> None:
    for location, job_name, call_text in _enqueue_call_sites():
        if job_name in _INGESTION_FUNCTIONS:
            assert "_queue_name=INGESTION_QUEUE" in call_text.replace(" ", "").replace("\n", ""), (
                f"{location}: {job_name!r} runs on the ingestion worker but the enqueue"
                " does not pass _queue_name=INGESTION_QUEUE — the job would sit on the"
                " default queue and fail"
            )
        elif job_name in _DEFAULT_FUNCTIONS:
            assert "_queue_name" not in call_text, (
                f"{location}: {job_name!r} runs on the default worker and must not"
                " set _queue_name"
            )
