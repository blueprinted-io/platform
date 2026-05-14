"""Tests for GET /api/v1/search (§12.2).

Uses "xyloquartz" as a distinctive search keyword that will not appear in
any default factory payloads, making result isolation straightforward.

Record creation happens inline per test (not via shared fixtures) to avoid
event-loop scoping mismatches between session-scoped async fixtures and
function-scoped test event loops (asyncpg enforces single-loop use).
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import fact_payload, task_payload, task_step_payload

pytestmark = pytest.mark.asyncio

_AUTHOR = "author-srch-001"
_REVIEWER = "reviewer-srch-001"
_VIEWER = "test-sub-001"

_KEYWORD = "xyloquartz"


async def _make_confirmed_fact(client: AsyncClient, make_token: Callable[..., str]) -> str:
    """Create, submit, and confirm a Fact containing the search keyword. Returns its id."""
    author_tok = make_token(sub=_AUTHOR, roles=["contributor"])
    reviewer_tok = make_token(sub=_REVIEWER, roles=["contributor"])

    r = await client.post(
        "/api/v1/facts",
        json=fact_payload(
            title=f"{_KEYWORD} calibration reference",
            body=f"{_KEYWORD} is a calibration marker used in sensor validation.",
        ),
        headers={"Authorization": f"Bearer {author_tok}"},
    )
    assert r.status_code == 201
    fact_id = r.json()["id"]

    await client.post(
        f"/api/v1/facts/{fact_id}/submit", headers={"Authorization": f"Bearer {author_tok}"}
    )
    r = await client.post(
        f"/api/v1/facts/{fact_id}/confirm", headers={"Authorization": f"Bearer {reviewer_tok}"}
    )
    assert r.status_code == 200
    return str(fact_id)


async def _make_confirmed_task(client: AsyncClient, make_token: Callable[..., str]) -> str:
    """Create, submit, and confirm a Task containing the search keyword. Returns its id."""
    author_tok = make_token(sub=_AUTHOR, roles=["contributor"])
    reviewer_tok = make_token(sub=_REVIEWER, roles=["contributor"])

    r = await client.post(
        "/api/v1/tasks",
        json=task_payload(
            title=f"Calibrate {_KEYWORD} sensor",
            outcome=f"Sensor validated against {_KEYWORD} standard.",
        ),
        headers={"Authorization": f"Bearer {author_tok}"},
    )
    assert r.status_code == 201
    task_id = r.json()["id"]

    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(step=f"Load {_KEYWORD} reference profile into sensor firmware"),
        headers={"Authorization": f"Bearer {author_tok}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/submit", headers={"Authorization": f"Bearer {author_tok}"}
    )
    r = await client.post(
        f"/api/v1/tasks/{task_id}/confirm", headers={"Authorization": f"Bearer {reviewer_tok}"}
    )
    assert r.status_code == 200
    return str(task_id)


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


async def test_search_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/search", params={"q": _KEYWORD})
    assert r.status_code == 401


async def test_search_missing_q_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get("/api/v1/search", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422


async def test_search_empty_q_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search", params={"q": ""}, headers={"Authorization": f"Bearer {tok}"}
    )
    assert r.status_code == 422


async def test_search_limit_above_max_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "limit": 101},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Full-text search — core behaviour
# ---------------------------------------------------------------------------


async def test_search_no_match_returns_empty(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": "zorblaxian-quantum-fizz-9999"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["results"] == []


async def test_search_returns_matching_confirmed_records(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    fact_id = await _make_confirmed_fact(client, make_token)
    task_id = await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2

    types_returned = {item["record_type"] for item in body["results"]}
    assert "fact" in types_returned
    assert "task" in types_returned

    ids_returned = {item["id"] for item in body["results"]}
    assert fact_id in ids_returned
    assert task_id in ids_returned


async def test_search_result_shape(client: AsyncClient, make_token: Callable[..., str]) -> None:
    fact_id = await _make_confirmed_fact(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "type": "fact"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    fact = next(x for x in results if x["id"] == fact_id)

    assert fact["record_type"] == "fact"
    assert "record_id" in fact
    assert isinstance(fact["version"], int)
    assert fact["status"] == "confirmed"
    assert fact["domain"] is None
    assert fact["match_type"] == "fulltext"
    assert isinstance(fact["score"], float)
    assert isinstance(fact["excerpt"], str)
    assert len(fact["excerpt"]) > 0


# ---------------------------------------------------------------------------
# Type filter
# ---------------------------------------------------------------------------


async def test_type_filter_limits_to_requested_types(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    fact_id = await _make_confirmed_fact(client, make_token)
    await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "type": "fact"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    types_returned = {item["record_type"] for item in body["results"]}
    assert types_returned == {"fact"}
    assert fact_id in {item["id"] for item in body["results"]}


async def test_type_filter_multiple_types(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    await _make_confirmed_fact(client, make_token)
    await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "type": "fact,task"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    types_returned = {item["record_type"] for item in r.json()["results"]}
    assert types_returned <= {"fact", "task"}


async def test_unknown_type_filter_ignored(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Unknown type tokens in the filter are silently ignored (not a 422)."""
    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "type": "fact,nonexistent"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    types_returned = {item["record_type"] for item in r.json()["results"]}
    assert "nonexistent" not in types_returned


# ---------------------------------------------------------------------------
# Domain filter
# ---------------------------------------------------------------------------


async def test_domain_filter_excludes_facts_and_concepts(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """When domain=X, facts and concepts are excluded (they have no domain field)."""
    await _make_confirmed_fact(client, make_token)
    task_id = await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "domain": "test-domain"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    types_returned = {item["record_type"] for item in body["results"]}
    assert "fact" not in types_returned
    assert "concept" not in types_returned
    assert task_id in {item["id"] for item in body["results"]}


async def test_domain_filter_non_matching_domain_returns_no_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "domain": "nonexistent-domain"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    ids_returned = {item["id"] for item in r.json()["results"]}
    assert task_id not in ids_returned


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


async def test_search_limit_respected(client: AsyncClient, make_token: Callable[..., str]) -> None:
    await _make_confirmed_fact(client, make_token)
    await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "limit": 1},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 1
    assert body["total"] >= 2


async def test_search_offset_paginates(client: AsyncClient, make_token: Callable[..., str]) -> None:
    await _make_confirmed_fact(client, make_token)
    await _make_confirmed_task(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r_page1 = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "limit": 1, "offset": 0},
        headers={"Authorization": f"Bearer {tok}"},
    )
    r_page2 = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "limit": 1, "offset": 1},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r_page1.status_code == 200
    assert r_page2.status_code == 200
    id_page1 = r_page1.json()["results"][0]["id"]
    id_page2 = r_page2.json()["results"][0]["id"]
    assert id_page1 != id_page2


# ---------------------------------------------------------------------------
# Semantic flag
# ---------------------------------------------------------------------------


async def test_semantic_flag_without_config_returns_results(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """?semantic=true with no embedding config falls back to fulltext gracefully."""
    await _make_confirmed_fact(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "semantic": "true"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["semantic_available"] is False
    assert len(body["results"]) >= 1


async def test_semantic_available_false_when_records_have_no_embeddings(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    await _make_confirmed_fact(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    # In the test environment, no embedding service is configured so all records
    # have NULL embeddings — semantic_available must be False.
    assert r.json()["semantic_available"] is False


# ---------------------------------------------------------------------------
# Status filter
# ---------------------------------------------------------------------------


async def test_status_filter_draft_excludes_confirmed_records(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Confirmed records should not appear when searching for draft status."""
    fact_id = await _make_confirmed_fact(client, make_token)

    tok = make_token(sub=_VIEWER, roles=["viewer"])
    r = await client.get(
        "/api/v1/search",
        params={"q": _KEYWORD, "status": "draft"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["results"]}
    assert fact_id not in ids
