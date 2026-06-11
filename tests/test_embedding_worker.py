"""Tests for the generate_embedding ARQ job (§12.1, §14).

Covers:
  - No embedding config → exits cleanly without exception
  - Record not found → exits cleanly without exception
  - Principle happy path: embedding fetched and stored
  - Workflow happy path: embedding fetched and stored
  - Task happy path: embedding fetched and stored (includes step text)
  - API error → exception raised

Test approach: real test DB, load_llm_settings mocked to return
controlled LLMSettings, embedding HTTP call mocked via respx.
"""

import uuid
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import respx
import sqlalchemy as sa
from httpx import AsyncClient, HTTPStatusError, Response
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.config import Settings
from api.database import create_engine
from api.services.settings_service import LLMSettings
from workers.embeddings import generate_embedding

pytestmark = pytest.mark.asyncio

_EMB_URL = "http://embedding.test"
_EMB_ENDPOINT = f"{_EMB_URL}/embeddings"
_TEST_VECTOR = [0.1] * 1536

_CONFIGURED_LLM = LLMSettings(
    triage_base_url="",
    triage_model="",
    triage_api_key="",
    triage_timeout=60,
    extraction_base_url="",
    extraction_model="",
    extraction_api_key="",
    extraction_timeout=120,
    embedding_base_url=_EMB_URL,
    embedding_model="text-embedding-test",
    embedding_api_key="",
    embedding_timeout=30,
)

_NO_EMBEDDING_LLM = LLMSettings(
    triage_base_url="",
    triage_model="",
    triage_api_key="",
    triage_timeout=60,
    extraction_base_url="",
    extraction_model="",
    extraction_api_key="",
    extraction_timeout=120,
    embedding_base_url="",
    embedding_model="",
    embedding_api_key="",
    embedding_timeout=30,
)

def _embedding_response() -> Response:
    return Response(200, json={"data": [{"embedding": _TEST_VECTOR}]})


def _make_ctx(test_settings: Settings) -> dict[str, Any]:
    engine = create_engine(test_settings)
    return {"settings": test_settings, "db_engine": engine}


async def _get_embedding(
    engine: AsyncEngine, table: str, record_id: uuid.UUID
) -> list[float] | None:
    async with AsyncSession(engine) as session:
        row = (
            await session.execute(
                sa.text(f"SELECT embedding::text FROM {table} WHERE id = :id"),
                {"id": record_id},
            )
        ).fetchone()
    if row is None or row[0] is None:
        return None
    # pgvector returns embedding as a string like "[0.1,0.2,...]"
    return [float(x) for x in row[0].strip("[]").split(",")]


# ---------------------------------------------------------------------------
# No embedding config — exits cleanly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_embedding_config_exits_cleanly(test_settings: Settings) -> None:
    ctx = _make_ctx(test_settings)
    try:
        no_embed = AsyncMock(return_value=_NO_EMBEDDING_LLM)
        with patch("workers.embeddings.load_llm_settings", new=no_embed):
            await generate_embedding(ctx, "principle", str(uuid.uuid4()))
    finally:
        await ctx["db_engine"].dispose()


# ---------------------------------------------------------------------------
# Record not found — exits cleanly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_not_found_exits_cleanly(test_settings: Settings) -> None:
    ctx = _make_ctx(test_settings)
    try:
        configured = AsyncMock(return_value=_CONFIGURED_LLM)
        with patch("workers.embeddings.load_llm_settings", new=configured):
            await generate_embedding(ctx, "principle", str(uuid.uuid4()))
    finally:
        await ctx["db_engine"].dispose()


# ---------------------------------------------------------------------------
# Principle happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_principle_embedding_stored(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    resp = await client.post(
        "/api/v1/principles",
        json={
            "title": "Emb test principle",
            "summary": "Summary for embedding.",
            "explanation": "Explanation for embedding.",
            "domain": "test-domain",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    principle_id = uuid.UUID(resp.json()["id"])

    respx.post(_EMB_ENDPOINT).mock(return_value=_embedding_response())

    ctx = _make_ctx(test_settings)
    try:
        configured = AsyncMock(return_value=_CONFIGURED_LLM)
        with patch("workers.embeddings.load_llm_settings", new=configured):
            await generate_embedding(ctx, "principle", str(principle_id))

        stored = await _get_embedding(ctx["db_engine"], "principles", principle_id)
    finally:
        await ctx["db_engine"].dispose()

    assert stored is not None
    assert len(stored) == 1536


# ---------------------------------------------------------------------------
# Workflow happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_workflow_embedding_stored(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    resp = await client.post(
        "/api/v1/workflows",
        json={
            "title": "Emb test workflow",
            "objective": "Objective for embedding.",
            "domain": "test-domain",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    workflow_id = uuid.UUID(resp.json()["id"])

    respx.post(_EMB_ENDPOINT).mock(return_value=_embedding_response())

    ctx = _make_ctx(test_settings)
    try:
        configured = AsyncMock(return_value=_CONFIGURED_LLM)
        with patch("workers.embeddings.load_llm_settings", new=configured):
            await generate_embedding(ctx, "workflow", str(workflow_id))

        stored = await _get_embedding(ctx["db_engine"], "workflows", workflow_id)
    finally:
        await ctx["db_engine"].dispose()

    assert stored is not None
    assert len(stored) == 1536


# ---------------------------------------------------------------------------
# Task happy path (includes step text in embedding input)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_task_embedding_stored(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    task_resp = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Emb test task",
            "outcome": "Outcome for embedding.",
            "domain": "test-domain",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert task_resp.status_code == 201
    task_id = uuid.UUID(task_resp.json()["id"])

    await client.post(
        f"/api/v1/tasks/{task_resp.json()['record_id']}/{task_resp.json()['version']}/steps",
        json={"step": "Do the thing", "completion": "Done.", "irreversible": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    respx.post(_EMB_ENDPOINT).mock(return_value=_embedding_response())

    ctx = _make_ctx(test_settings)
    try:
        configured = AsyncMock(return_value=_CONFIGURED_LLM)
        with patch("workers.embeddings.load_llm_settings", new=configured):
            await generate_embedding(ctx, "task", str(task_id))

        stored = await _get_embedding(ctx["db_engine"], "tasks", task_id)
    finally:
        await ctx["db_engine"].dispose()

    assert stored is not None
    assert len(stored) == 1536


# ---------------------------------------------------------------------------
# API error → exception raised
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_embedding_api_error_raises(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    resp = await client.post(
        "/api/v1/principles",
        json={
            "title": "Emb error principle",
            "summary": "Summary.",
            "explanation": "Explanation.",
            "domain": "test-domain",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    principle_id = resp.json()["id"]

    respx.post(_EMB_ENDPOINT).mock(return_value=Response(500))

    ctx = _make_ctx(test_settings)
    try:
        configured = AsyncMock(return_value=_CONFIGURED_LLM)
        with patch("workers.embeddings.load_llm_settings", new=configured):
            with pytest.raises(HTTPStatusError):
                await generate_embedding(ctx, "principle", principle_id)
    finally:
        await ctx["db_engine"].dispose()
