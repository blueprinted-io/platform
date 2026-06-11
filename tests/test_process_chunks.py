"""Tests for the process_chunks ARQ job, _triage_chunk, extract_chunk, and helpers.

Spec sections: §11.3, §11.6, §11.7.

Covers:
  - prompts.py: load() returns Prompt; render() interpolates variables
  - No-LLM path: queued chunks marked done when LLM not configured
  - Triage: task_candidate → chunk triage_complete with pending estimates
  - Triage: principle_candidate → chunk triage_complete with pending estimates
  - Triage: reference_material / skip → chunk done, no estimates
  - Triage: non-JSON → chunk status="error"
  - Triage: unknown category → chunk status="error"
  - Extraction: approved task estimate → task candidate written, chunk done
  - Extraction: approved principle estimate → principle candidate written, chunk done
  - Extraction: missing required fields → candidate_status="invalid"
  - Extraction: LLM error → chunk status="error"

Test approach: call _triage_chunk() / extract_chunk() directly with a real
test DB and mocked httpx via respx.
"""

import json
import uuid
from typing import Any

import pytest
import respx
import sqlalchemy as sa
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api import prompts as prompt_store
from api.config import Settings
from api.database import create_engine
from api.models.ingestion import IngestionCandidate, IngestionChunk, IngestionTriageEstimate
from api.prompts import Prompt
from api.services.settings_service import LLMSettings
from workers.extraction import (
    _triage_chunk,
    _validate_principle,
    _validate_task,
    extract_chunk,
    process_chunks,
)

pytestmark = pytest.mark.asyncio

_LLM_URL = "http://llm.test"
_LLM_CHAT = f"{_LLM_URL}/chat/completions"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def llm_settings() -> LLMSettings:
    """Resolved LLM settings for direct calls to _triage_chunk."""
    return LLMSettings(
        triage_base_url=_LLM_URL,
        triage_model="test-model",
        triage_api_key="",
        triage_timeout=60,
        extraction_base_url=_LLM_URL,
        extraction_model="test-model",
        extraction_api_key="",
        extraction_timeout=120,
        embedding_base_url="",
        embedding_model="text-embedding-3-small",
        embedding_api_key="",
        embedding_timeout=30,
    )


def _make_env_settings(test_settings: Settings) -> Settings:
    """Return a Settings with LLM configured for use in ARQ ctx dicts."""
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="test",
        database_url=test_settings.database_url,
        database_url_sync=test_settings.database_url_sync,
        redis_url=test_settings.redis_url,
        log_level="WARNING",
        app_secret_key="ci-test-secret",  # type: ignore[arg-type]
        oidc_issuer="https://auth.test.example.com/",
        oidc_audience="blueprinted-test",
        oidc_roles_claim="roles",
        llm_base_url=_LLM_URL,
        llm_model="test-model",
    )


def _chat_response(content: str) -> Response:
    """Build a minimal chat completions response."""
    return Response(
        200,
        json={
            "choices": [{"message": {"role": "assistant", "content": content}}]
        },
    )


def _triage_json(
    category: str = "task_candidate",
    estimates: list[dict[str, str]] | None = None,
) -> str:
    payload: dict[str, Any] = {"category": category, "confidence": 0.9, "reason": "test"}
    if category not in ("reference_material", "skip"):
        if estimates is None:
            record_type = "principle" if category == "principle_candidate" else "task"
            estimates = [{"title": "Test Estimate", "type": record_type}]
        payload["estimates"] = estimates
    return json.dumps(payload)


def _task_extraction_json(tasks: list[dict[str, Any]] | None = None) -> str:
    if tasks is None:
        tasks = [
            {
                "id": "T001",
                "title": "iSCSI Initiator Installation",
                "outcome": "open-iscsi is installed and running.",
                "software_name": "open-iscsi",
                "software_version": "22.04",
                "procedure_name": "Package installation via apt",
                "facts": ["iscsid manages iSCSI sessions."],
                "concepts": ["Without this step iSCSI connections cannot be made."],
                "dependencies": ["Ubuntu with sudo access."],
                "irreversible": False,
                "steps": [
                    {
                        "text": "Run apt update.",
                        "completion": "Terminal returns with no errors.",
                        "actions": ["sudo apt update"],
                        "notes": None,
                    }
                ],
            }
        ]
    return json.dumps({"tasks": tasks})


def _principle_extraction_json(principles: list[dict[str, Any]] | None = None) -> str:
    if principles is None:
        principles = [
            {
                "title": "iSCSI Protocol Fundamentals",
                "summary": "Explains how iSCSI maps SCSI commands onto TCP/IP.",
                "explanation": "## Overview\niSCSI sends SCSI commands over TCP.",
                "analogies": None,
                "software_name": None,
                "software_version": None,
            }
        ]
    return json.dumps({"principles": principles})


async def _insert_queued_chunk(
    engine: AsyncEngine,
    ingestion_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a minimal ingestion and a queued chunk. Returns (ingestion_id, chunk_id)."""
    if ingestion_id is None:
        ingestion_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions
                  (id, source_type, status, created_by, original_filename, source_sha256)
                VALUES (:id, 'pdf', 'ready', :user, 'test.pdf', :sha)
                ON CONFLICT DO NOTHING
            """),
            {
                "id": ingestion_id,
                "user": system_user_id,
                "sha": str(uuid.uuid4()).replace("-", ""),
            },
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_title, section_level,
                   text, text_preview, word_count, chunk_status, is_scanned,
                   candidate_count)
                VALUES (:id, :iid, 0, 'Test Section', 1,
                        'Full chunk text for testing.', 'Full chunk text', 5,
                        'queued', false, 0)
            """),
            {"id": chunk_id, "iid": ingestion_id},
        )
    return ingestion_id, chunk_id


async def _insert_extraction_queued_chunk(
    engine: AsyncEngine,
    record_type: str = "task",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Insert chunk at extraction_queued with one approved estimate.

    Returns (ingestion_id, chunk_id, estimate_id).
    """
    ingestion_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    estimate_id = uuid.uuid4()
    system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions
                  (id, source_type, status, created_by, original_filename, source_sha256)
                VALUES (:id, 'pdf', 'ready', :user, 'test.pdf', :sha)
            """),
            {
                "id": ingestion_id,
                "user": system_user_id,
                "sha": str(uuid.uuid4()).replace("-", ""),
            },
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_title, section_level,
                   text, text_preview, word_count, chunk_status, is_scanned,
                   candidate_count)
                VALUES (:id, :iid, 0, 'Test Section', 1,
                        'Full chunk text for testing.', 'Full chunk text', 5,
                        'extraction_queued', false, 0)
            """),
            {"id": chunk_id, "iid": ingestion_id},
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_triage_estimates
                  (id, ingestion_id, chunk_id, record_type, approved_type,
                   estimated_title, estimate_status, sort_order)
                VALUES (:id, :iid, :cid, :rtype, :rtype, 'Test Estimate', 'approved', 0)
            """),
            {
                "id": estimate_id,
                "iid": ingestion_id,
                "cid": chunk_id,
                "rtype": record_type,
            },
        )
    return ingestion_id, chunk_id, estimate_id


async def _get_chunk(engine: AsyncEngine, chunk_id: uuid.UUID) -> dict[str, Any]:
    async with AsyncSession(engine) as session:
        ch = await session.get(IngestionChunk, chunk_id)
        assert ch is not None
        return {
            "chunk_status": ch.chunk_status,
            "candidate_count": ch.candidate_count,
            "error_detail": ch.error_detail,
        }


async def _get_candidates(
    engine: AsyncEngine, chunk_id: uuid.UUID
) -> list[dict[str, Any]]:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            sa.select(IngestionCandidate).where(
                IngestionCandidate.chunk_id == chunk_id
            )
        )
        return [
            {
                "record_type": c.record_type,
                "candidate_status": c.candidate_status,
                "proposed_json": c.proposed_json,
                "review_note": c.review_note,
            }
            for c in result.scalars().all()
        ]


async def _get_estimates(
    engine: AsyncEngine, chunk_id: uuid.UUID
) -> list[dict[str, Any]]:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            sa.select(IngestionTriageEstimate)
            .where(IngestionTriageEstimate.chunk_id == chunk_id)
            .order_by(IngestionTriageEstimate.sort_order)
        )
        return [
            {
                "record_type": e.record_type,
                "approved_type": e.approved_type,
                "estimated_title": e.estimated_title,
                "estimate_status": e.estimate_status,
            }
            for e in result.scalars().all()
        ]


# ---------------------------------------------------------------------------
# prompts module
# ---------------------------------------------------------------------------


def test_load_triage_returns_prompt() -> None:
    p = prompt_store.load("triage")
    assert isinstance(p, Prompt)
    assert p.stage == "triage"
    assert "Classify" in p.system
    assert "{section_title}" in p.user_template
    assert "{text}" in p.user_template


def test_load_extract_task_returns_prompt() -> None:
    p = prompt_store.load("extract_task")
    assert "extracting structured task records" in p.system
    assert "{section_title}" in p.user_template


def test_load_extract_principle_returns_prompt() -> None:
    p = prompt_store.load("extract_principle")
    assert "principle" in p.system.lower()
    assert "{section_title}" in p.user_template


def test_load_unknown_stage_raises_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown"):
        prompt_store.load("nonexistent")


def test_prompt_render_substitutes_variables() -> None:
    p = prompt_store.load("triage")
    system, user = p.render(section_title="3.2 iSCSI", text="Install open-iscsi.")
    assert system == p.system
    assert "3.2 iSCSI" in user
    assert "Install open-iscsi." in user


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


# TEST_REVISED: procedure_name removed from required fields (eba8088); tests updated to reflect
# that the LLM output schema no longer includes procedure_name as a required field.
def test_validate_task_valid() -> None:
    assert _validate_task({
        "title": "T", "outcome": "O",
        "steps": [{"text": "s", "completion": "c", "actions": [], "notes": None}],
    }) is None


def test_validate_task_missing_field() -> None:
    err = _validate_task({"title": "T", "steps": [{"text": "s"}]})
    assert err is not None
    assert "outcome" in err


def test_validate_task_empty_steps() -> None:
    err = _validate_task({"title": "T", "outcome": "O", "steps": []})
    assert err is not None
    assert "empty" in err


def test_validate_principle_valid() -> None:
    assert _validate_principle({
        "title": "T", "summary": "S", "explanation": "E"
    }) is None


def test_validate_principle_missing_field() -> None:
    err = _validate_principle({"title": "T", "summary": "S"})
    assert err is not None
    assert "explanation" in err


# ---------------------------------------------------------------------------
# No-LLM path
# ---------------------------------------------------------------------------


async def test_process_chunks_no_llm_marks_done(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    ingestion_id, chunk_id = await _insert_queued_chunk(engine)

    ctx: dict[str, Any] = {"settings": test_settings, "db_engine": engine}
    await process_chunks(ctx, str(ingestion_id))

    chunk = await _get_chunk(engine, chunk_id)
    assert chunk["chunk_status"] == "done"
    await engine.dispose()


# ---------------------------------------------------------------------------
# Triage phase: task_candidate
# ---------------------------------------------------------------------------


@respx.mock
async def test_triage_chunk_task_candidate(
    test_settings: Settings, llm_settings: LLMSettings
) -> None:
    engine = create_engine(test_settings)
    ingestion_id, chunk_id = await _insert_queued_chunk(engine)

    respx.post(_LLM_CHAT).mock(
        return_value=_chat_response(_triage_json("task_candidate"))
    )

    async with AsyncSession(engine) as session:
        chunk = await session.get(IngestionChunk, chunk_id)
        assert chunk is not None
        await _triage_chunk(engine, llm_settings, chunk, prompt_store.load("triage"))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "triage_complete"

    estimates = await _get_estimates(engine, chunk_id)
    assert len(estimates) == 1
    assert estimates[0]["record_type"] == "task"
    assert estimates[0]["estimate_status"] == "pending"
    await engine.dispose()


# ---------------------------------------------------------------------------
# Triage phase: principle_candidate
# ---------------------------------------------------------------------------


@respx.mock
async def test_triage_chunk_principle_candidate(
    test_settings: Settings, llm_settings: LLMSettings
) -> None:
    engine = create_engine(test_settings)
    ingestion_id, chunk_id = await _insert_queued_chunk(engine)

    respx.post(_LLM_CHAT).mock(
        return_value=_chat_response(_triage_json("principle_candidate"))
    )

    async with AsyncSession(engine) as session:
        chunk = await session.get(IngestionChunk, chunk_id)
        assert chunk is not None
        await _triage_chunk(engine, llm_settings, chunk, prompt_store.load("triage"))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "triage_complete"

    estimates = await _get_estimates(engine, chunk_id)
    assert len(estimates) == 1
    assert estimates[0]["record_type"] == "principle"
    assert estimates[0]["estimate_status"] == "pending"
    await engine.dispose()


# ---------------------------------------------------------------------------
# Triage phase: reference_material / skip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", ["reference_material", "skip"])
@respx.mock
async def test_triage_chunk_no_extraction(
    category: str, test_settings: Settings, llm_settings: LLMSettings
) -> None:
    engine = create_engine(test_settings)
    ingestion_id, chunk_id = await _insert_queued_chunk(engine)

    respx.post(_LLM_CHAT).mock(
        return_value=_chat_response(_triage_json(category))
    )

    async with AsyncSession(engine) as session:
        chunk = await session.get(IngestionChunk, chunk_id)
        assert chunk is not None
        await _triage_chunk(engine, llm_settings, chunk, prompt_store.load("triage"))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "done"
    assert state["candidate_count"] == 0
    estimates = await _get_estimates(engine, chunk_id)
    assert estimates == []
    await engine.dispose()


# ---------------------------------------------------------------------------
# Triage error paths
# ---------------------------------------------------------------------------


@respx.mock
async def test_triage_non_json_marks_chunk_error(
    test_settings: Settings, llm_settings: LLMSettings
) -> None:
    engine = create_engine(test_settings)
    ingestion_id, chunk_id = await _insert_queued_chunk(engine)

    respx.post(_LLM_CHAT).mock(
        return_value=_chat_response("Sorry, I cannot classify this content.")
    )

    async with AsyncSession(engine) as session:
        chunk = await session.get(IngestionChunk, chunk_id)
        assert chunk is not None
        await _triage_chunk(engine, llm_settings, chunk, prompt_store.load("triage"))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "error"
    assert state["error_detail"] is not None
    await engine.dispose()


@respx.mock
async def test_triage_unknown_category_marks_chunk_error(
    test_settings: Settings, llm_settings: LLMSettings
) -> None:
    engine = create_engine(test_settings)
    ingestion_id, chunk_id = await _insert_queued_chunk(engine)

    respx.post(_LLM_CHAT).mock(
        return_value=_chat_response(
            json.dumps({"category": "hallucinated_category", "confidence": 0.5, "reason": "oops"})
        )
    )

    async with AsyncSession(engine) as session:
        chunk = await session.get(IngestionChunk, chunk_id)
        assert chunk is not None
        await _triage_chunk(engine, llm_settings, chunk, prompt_store.load("triage"))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "error"
    assert "hallucinated_category" in (state["error_detail"] or "")
    await engine.dispose()


# ---------------------------------------------------------------------------
# Extraction phase: task candidate
# ---------------------------------------------------------------------------


@respx.mock
async def test_extract_chunk_task_candidate(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    _, chunk_id, _ = await _insert_extraction_queued_chunk(
        engine, record_type="task"
    )

    respx.post(_LLM_CHAT).mock(return_value=_chat_response(_task_extraction_json()))

    env_settings = _make_env_settings(test_settings)
    ctx: dict[str, Any] = {"settings": env_settings, "db_engine": engine}
    await extract_chunk(ctx, str(chunk_id))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "done"
    assert state["candidate_count"] == 1

    candidates = await _get_candidates(engine, chunk_id)
    assert len(candidates) == 1
    assert candidates[0]["record_type"] == "task"
    assert candidates[0]["candidate_status"] == "pending"
    assert candidates[0]["proposed_json"]["title"] == "iSCSI Initiator Installation"
    await engine.dispose()


# ---------------------------------------------------------------------------
# Extraction phase: principle candidate
# ---------------------------------------------------------------------------


@respx.mock
async def test_extract_chunk_principle_candidate(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    _, chunk_id, _ = await _insert_extraction_queued_chunk(
        engine, record_type="principle"
    )

    respx.post(_LLM_CHAT).mock(return_value=_chat_response(_principle_extraction_json()))

    env_settings = _make_env_settings(test_settings)
    ctx: dict[str, Any] = {"settings": env_settings, "db_engine": engine}
    await extract_chunk(ctx, str(chunk_id))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "done"
    assert state["candidate_count"] == 1

    candidates = await _get_candidates(engine, chunk_id)
    assert len(candidates) == 1
    assert candidates[0]["record_type"] == "principle"
    assert candidates[0]["candidate_status"] == "pending"
    await engine.dispose()


# ---------------------------------------------------------------------------
# Extraction phase: invalid candidate
# ---------------------------------------------------------------------------


@respx.mock
async def test_invalid_task_candidate_marked_invalid(test_settings: Settings) -> None:
    """A task missing required fields gets candidate_status='invalid', chunk still done."""
    engine = create_engine(test_settings)
    _, chunk_id, _ = await _insert_extraction_queued_chunk(
        engine, record_type="task"
    )

    bad_task = json.dumps({"tasks": [{"title": "Only title, no steps or outcome"}]})
    respx.post(_LLM_CHAT).mock(return_value=_chat_response(bad_task))

    env_settings = _make_env_settings(test_settings)
    ctx: dict[str, Any] = {"settings": env_settings, "db_engine": engine}
    await extract_chunk(ctx, str(chunk_id))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "done"
    assert state["candidate_count"] == 0  # invalid candidates don't count

    candidates = await _get_candidates(engine, chunk_id)
    assert len(candidates) == 1
    assert candidates[0]["candidate_status"] == "invalid"
    assert candidates[0]["review_note"] is not None
    await engine.dispose()


# ---------------------------------------------------------------------------
# Extraction phase: LLM error marks chunk error
# ---------------------------------------------------------------------------


@respx.mock
async def test_extraction_llm_error_marks_chunk_error(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    _, chunk_id, _ = await _insert_extraction_queued_chunk(
        engine, record_type="task"
    )

    respx.post(_LLM_CHAT).mock(return_value=Response(500))

    env_settings = _make_env_settings(test_settings)
    ctx: dict[str, Any] = {"settings": env_settings, "db_engine": engine}
    await extract_chunk(ctx, str(chunk_id))

    state = await _get_chunk(engine, chunk_id)
    assert state["chunk_status"] == "error"
    await engine.dispose()


# ---------------------------------------------------------------------------
# process_chunks full job with LLM configured
# ---------------------------------------------------------------------------


@respx.mock
async def test_process_chunks_with_llm_processes_all_queued(
    test_settings: Settings,
) -> None:
    """process_chunks triages all queued chunks and skips non-queued ones."""
    engine = create_engine(test_settings)
    ingestion_id = uuid.uuid4()
    _, chunk_id_1 = await _insert_queued_chunk(engine, ingestion_id)
    _, chunk_id_2 = await _insert_queued_chunk(engine, ingestion_id)

    # Set chunk_2 to done so it should be skipped
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("UPDATE ingestion_chunks SET chunk_status='done' WHERE id=:id"),
            {"id": chunk_id_2},
        )

    # One LLM call: triage for chunk_1 only (chunk_2 is already done)
    respx.post(_LLM_CHAT).mock(
        return_value=_chat_response(_triage_json("task_candidate"))
    )

    env_settings = _make_env_settings(test_settings)
    ctx: dict[str, Any] = {"settings": env_settings, "db_engine": engine}
    await process_chunks(ctx, str(ingestion_id))

    state_1 = await _get_chunk(engine, chunk_id_1)
    state_2 = await _get_chunk(engine, chunk_id_2)

    assert state_1["chunk_status"] == "triage_complete"
    assert state_2["chunk_status"] == "done"  # unchanged — was already done

    estimates_1 = await _get_estimates(engine, chunk_id_1)
    assert len(estimates_1) == 1
    assert estimates_1[0]["record_type"] == "task"

    await engine.dispose()
