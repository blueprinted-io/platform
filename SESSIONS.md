# Session History

This file records close-out notes from each Claude Code session.
Paste the output of `/closeout` here at the end of every session.
When starting a new session, paste the most recent entry as context.

---

<!-- Sessions are added below in reverse chronological order (newest first) -->

## Session Close-Out — 2026-05-14

### Completed

- **ARQ pool wiring** — `create_pool` called in FastAPI lifespan (`api/main.py`); stored at `app.state.arq_pool`. `conn_retries=0` prevents startup blocking when Redis is unavailable. Pool disposed cleanly in shutdown.
- **New dependencies** — `AppSettings` and `ArqPool` added to `api/dependencies.py`, reading from `app.state` rather than `get_settings()` directly. Required because `get_settings()` reads `.env` which contains Docker Compose keys that fail Settings validation under `extra="forbid"`.
- **Embedding generation worker job** — `generate_embedding` fully implemented in `workers/main.py`. Fetches record text per type (fact, concept, principle, task with steps, workflow), calls OpenAI-compatible embedding API via httpx, writes result via raw SQL (`UPDATE ... SET embedding = :embedding::vector`). Raises on failure so ARQ retries.
- **Embedding trigger on confirm** — All five record-type confirm endpoints (`facts`, `concepts`, `principles`, `tasks`, `workflows`) and the review queue confirm path (`api/routes/review.py`) enqueue `generate_embedding` after commit.
- **Four new embedding config fields** in `api/config.py`: `llm_embedding_base_url`, `llm_embedding_model`, `llm_embedding_api_key`, `llm_embedding_timeout_seconds`.
- **GIN indexes migration** — `migrations/versions/20260514_a1b2c3d4e5f6_search_indexes.py`; tsvector indexes on all five tables. `down_revision = "d6e7f8a9b0c1"` (Sprint 5 review claims migration).
- **Search service** — `api/services/search.py`; UNION ALL full-text search across all five types, optional semantic reranking (60% semantic / 40% FTS), hybrid score, domain filter (excludes domain-less types fact/concept when `?domain=X`), stable pagination (`ORDER BY fts_score DESC, id`), `semantic_available` flag.
- **Search schemas** — `api/schemas/search.py`; `SearchResult` and `SearchResponse`.
- **Search route** — `GET /api/v1/search` in `api/routes/search.py`; registered on `api/routes/v1.py`. Parameters: `q` (required, min_length=1), `type`, `domain`, `status` (default `confirmed`), `semantic` (default `false`), `limit` (max 100), `offset`.
- **Test stub** — `StubArqPool` added to `tests/conftest.py`; replaces real ARQ pool after lifespan so no Redis required in tests.
- **Search tests** — `tests/test_search.py`; 17 tests covering auth, shape, FTS, type filter, domain filter, semantic flag (no-op without config), pagination. All 162 tests passing.
- **Committed** at `dc5e3a4`.

### Incomplete or broken

Nothing incomplete or broken. All 162 tests pass, mypy clean, ruff clean.

### Decisions made

- **Domain filter excludes facts and concepts entirely** — When `?domain=X` is specified, facts and concepts are dropped from the result set because they have no domain column. They surface implicitly through tasks. This was explicitly confirmed by the user: "any domain search which turns up tasks by extension includes the associated facts and concepts." Not a spec deviation — the spec is silent on this; the decision should be added to §12.
- **`per-file-ignores` S608 for `api/services/search.py`** — SQL strings in the search service are built from hardcoded `_TypeConfig` dataclass fields, never from user input. Ruff S608 (SQL injection) is a false positive for these. Added `"api/services/search.py" = ["S608"]` to `pyproject.toml` rather than scattering `# noqa` comments that don't work inside triple-quoted f-strings.
- **Test records created inline, not via pytest fixtures** — async pytest fixtures for confirmed records caused event-loop scope mismatches (`asyncio_default_fixture_loop_scope = "session"` means fixtures run in the session loop; test bodies run in function-scoped loops; DB connections can't cross loops). Solution: plain `async def _make_confirmed_fact()` and `_make_confirmed_task()` helpers called directly inside each test body. This is the correct pattern for this test suite going forward.

### TEST_REVISED commits

No test files were modified. `tests/conftest.py` was extended (added `StubArqPool` class and pool replacement logic in the `client` fixture) and `tests/test_search.py` was created — but no existing tests were changed.

### Next session should start from

**Sprint 6 — Ingestion Pipeline** (§13, §14 ingestion sections).

Sprint 6 is the document ingestion pipeline: chunking, candidate extraction, ingestion job lifecycle (`pending` → `processing` → `done`/`failed`), and the `ingestion_chunks` table. The ARQ worker startup hook in `workers/main.py` already has a placeholder for the chunk reset logic (search for `# Sprint 6`).

Read §13 (Ingestion) and §14 (Worker) of `docs/requirements.md` before starting.

### Watch out for

- **`workers/main.py` startup hook placeholder** — There is a `# Sprint 6: reset ingestion_chunks` comment in `startup()`. Sprint 6 should fill this in once the `ingestion_chunks` table exists. Do not remove the placeholder or the hook — it is load-bearing per §14.
- **Embedding column dimension is fixed** — If the embedding model is ever changed to one with a different vector dimension, it requires a breaking migration (drop and recreate the `embedding` column on all five tables, re-embed everything). Do not treat `llm_embedding_model` as a routine config change.
- **`AppSettings` vs `get_settings()`** — Routes must use `AppSettings` (reads from `app.state.settings`), not `get_settings()` directly. `get_settings()` reads `.env` and fails in tests due to `extra="forbid"`. This is a convention to maintain going forward.
- **Test helper pattern** — For any future test file that needs confirmed records, use inline `async def _make_confirmed_X()` helper functions called within each test body. Do not use `scope="module"` or `scope="session"` async fixtures that open DB connections — they will fail with event loop scope errors.

---

## Session Close-Out — 2026-05-13

### Completed

- **Review Queue (§8.1)** — `GET /api/v1/review/queue` returns submitted records eligible for the current user to review. Domain-scoped types (tasks, workflows, principles) filtered to the user's assigned domains. Facts and Concepts shown to all reviewers regardless of domain. Own submissions excluded for everyone including admin. Paginated (limit/offset). Active claim info embedded in each queue item.

- **Claiming (§8.2)** — `POST /api/v1/review/{type}/{id}/claim` creates an advisory claim with 48h default expiry. Re-claiming an active claim you already hold refreshes the expiry (200). Claiming when another reviewer holds an active claim returns 409. Facts and Concepts return 422 (not claimable per `review_claims` schema). Invalid entity type returns 422.

- **Release (§8.2)** — `POST /api/v1/review/{type}/{id}/release` explicitly abandons own claim. 404 if no active claim. 403 if claim belongs to another reviewer.

- **Confirm/Return via review** — `POST /api/v1/review/{type}/{id}/confirm` and `.../return` apply the same lifecycle rules as record-level confirm/return and auto-release any active claim held by the acting user. Domain access enforced for domain-scoped types.

- **Claim expiry ARQ job (§14)** — `expire_review_claims` cron job registered in `WorkerSettings`, fires at minute 0, 15, 30, 45 (every 15 minutes). Sets `released_at` on all expired claims.

- **Worker DB initialisation** — `startup()` hook now creates the DB engine and stores it in `ctx["db_engine"]`. This fulfils the Sprint 4 placeholder comment. The chunk reset query remains a placeholder (Sprint 6).

- **Pre-existing ruff issue fixed** — Migration files had pre-existing E501 violations that were silently passing before (the CI runs `ruff check .` which catches them). Added `E501` to `"migrations/**/*.py"` per-file-ignores in `pyproject.toml`. This was in `main` before Sprint 5.

- **New files:** `api/models/review_claim.py`, `api/schemas/review.py`, `api/routes/review.py`, `tests/test_review.py`

- **All changes committed as `6ff6da7`. 145 tests passing, mypy clean, ruff clean.**

### Incomplete or broken

Nothing incomplete or broken.

### Decisions made

- **`REVIEW_CLAIM_EXPIRY_HOURS_DEFAULT = 48` is hardcoded.** The spec says "configurable window (default 48 hours)" but system_settings management API doesn't exist until Sprint 10. The constant is named explicitly and commented to pull from system_settings when that's available. No spec update needed — this is a sequencing gap, not a design deviation.

- **Worker `result.rowcount` requires `# type: ignore[attr-defined]`.** SQLAlchemy's async `session.execute(sa.text(...))` return type stubs don't expose `rowcount` cleanly. The ignore is targeted and annotated. No spec impact.

- **Facts and Concepts are not claimable.** Consistent with the `review_claims.entity_type` comment in migration `b4c5d6e7f8a9` which lists only `'task' | 'workflow' | 'principle'`. Confirmed by user before implementation.

- **Review confirm/return do not enqueue embedding generation.** The existing record-level confirm handlers don't enqueue embedding generation either (stub, Sprint 7). The review confirm handler follows the same pattern with a `# Sprint 7: enqueue generate_embedding` comment.

### TEST_REVISED commits

No existing test assertions were modified. `tests/conftest.py` was modified to add four new contributor subs (`author-rv-001`, `reviewer-rv-001`, `claimer-rv-001`, `self-rv-001`) to `_CONTRIBUTOR_SUBS` so they are pre-seeded with test-domain assignments. This is the same infrastructure pattern used in Sprint 4 and does not require a `TEST_REVISED` marker.

`tests/test_review.py` is a new file — 26 new tests written from scratch, not revisions.

### Next session should start from

**Sprint 6 (Ingestion Pipeline)** or **Sprint 7 (Search and Embeddings)** — both unblocked. Sprint 6 is the larger and lower-confidence sprint; Sprint 7 is more contained.

**If starting Sprint 7 (Search and Embeddings, §12):**
- Read §12 (search API, embedding lifecycle, hybrid ranking) and §14 (embedding generation job)
- Replace the `generate_embedding` stub in `workers/main.py` with the real LLM embedding call
- Implement `GET /api/v1/search` with tsvector full-text and optional pgvector semantic search
- The ARQ pool is not yet wired into route handlers — this will need to be plumbed so the confirm endpoints can enqueue `generate_embedding`. Currently the queue call is stubbed in review.py with a `# Sprint 7` comment

**If starting Sprint 6 (Ingestion Pipeline, §11):**
- Read §11 (pipeline stages, section selection, candidate review, iterative model) and §14 (chunk reset in startup hook)
- First task: implement the ingestion tables (`ingestions`, `ingestion_chunks`, `ingestion_candidates`, `ingestion_nav_pages`) as a new Alembic migration
- The worker startup hook `startup()` in `workers/main.py` already has a `# Sprint 6` placeholder comment at the exact location for the chunk reset query
- The ingestion pipeline lives in `/ingestion/` (hard-separated API consumer, no direct DB access)

### Watch out for

- **`reviewer-rv-nodomain`** is intentionally NOT in `_CONTRIBUTOR_SUBS` and has no domain assignments. It is auto-created by the auth upsert on first API call. Any future test that adds this sub to `_CONTRIBUTOR_SUBS` would break the domain-exclusion tests in `test_review.py`.

- **Claim expiry in tests** — `test_expired_claim_not_shown_as_active_in_queue` inserts a claim with `expires_at = NOW() - 2 hours` directly via SQL. The `expire_review_claims` job is not called in tests; the queue handler filters expired claims at read time (`expires_at > NOW()`), so the test verifies the queue behaviour without needing to run the job.

- **`review_claims.entity_type` stores singular form** (`'task'`, `'workflow'`, `'principle'`) even though the URL path uses plural (`tasks`, `workflows`, `principles`). The `_TYPE_TO_SINGULAR` dict in `api/routes/review.py` handles this mapping.

- **The worker `ctx["db_engine"]` is now set in startup.** `shutdown()` disposes of it. Any future job function that needs DB access should use `ctx["db_engine"]` the same way `expire_review_claims` does — create a new `AsyncSession(engine)` per invocation.

- **Embedding generation is still a no-op stub** for all confirm transitions — record-level AND review-path. Sprint 7 must wire up the ARQ pool to FastAPI app state and replace the stub. The review confirm handler has a comment at the exact location.

---

## Session Close-Out — 2026-05-13

### Completed

- **Domain enforcement (§7.3)** fully implemented across all domain-scoped record types:
  - `api/models/domain.py`: `Domain` and `UserDomain` ORM models
  - `api/models/__init__.py`: domain models imported so Alembic and `Base.metadata` see them
  - `api/models/base.py`: added `self_confirmed_by_admin` to shared lifecycle mixin
  - `api/models/task.py`, `workflow.py`, `principle.py`: `domain` changed from `Mapped[str | None]` (nullable) to `Mapped[str]` (NOT NULL)
  - `api/services/lifecycle.py`: added `assert_domain_active`, `assert_domain_access`; `assert_can_confirm` now returns `bool` (break-glass flag) and requires `justification` for admin self-confirms
  - `api/routes/tasks.py`, `workflows.py`: domain enforcement on create, update (domain change only), submit, confirm, return
  - `api/routes/principles.py`: already had domain enforcement; updated `ConfirmRequest | None` fix
  - `api/routes/facts.py`, `concepts.py`: added `ConfirmRequest` import and optional body to confirm endpoint; set `self_confirmed_by_admin`
  - `api/schemas/base.py`: `ConfirmRequest` model and `self_confirmed_by_admin` field on `LifecycleResponse`
  - `api/schemas/principle.py`, `task.py`, `workflow.py`: `domain` field made required (not optional)
  - Migration `20260513_d6e7f8a9b0c1`: creates `domains` and `user_domains` tables; adds `self_confirmed_by_admin` to all governed tables; backfills and makes `domain` NOT NULL on domain-scoped tables

- **Spec updated** (5 changes: §5, §5.1, §7.1–7.5 inserted, §9.2, §9.5, §25)

- **Test infrastructure**: `tests/conftest.py` `setup_test_domain_and_users` fixture pre-seeds `test-domain` and all known contributor users with domain assignments. `tests/factories.py` adds `domain="test-domain"` defaults to `principle_payload`, `task_payload`, `workflow_payload`.

- All changes committed as `a8d5919`. **119 tests passing, mypy clean, ruff clean.**

### Incomplete or broken

Nothing incomplete or broken.

### Decisions made

All decisions were already captured in the spec during this session (§25 decision log). No additional deviations.

- `ConfirmRequest | None = None` used instead of `ConfirmRequest = ConfirmRequest()` — ruff B008 fires on function calls in default arguments. Using `None` with inline `body.justification if body else None` is the idiomatic fix. Spec does not need updating (implementation detail).

### TEST_REVISED commits

Commit `a8d5919` modifies the following test files:

- **`tests/test_facts.py`**: `test_admin_can_confirm_own_fact` — added `json={"justification": "Admin break-glass confirm for test."}` to confirm POST. `test_retire_confirmed_fact_transitions_to_retired` — same fix (admin-rtire-001 self-confirms, was not in the original list but is the same pattern).
- **`tests/test_concepts.py`**: `test_deprecate_concept_admin_only` — same justification fix.
- **`tests/test_principles.py`**: `test_deprecate_principle_admin_only` — same justification fix. `test_create_principle_with_domain` — changed `domain="DevOps"` to `domain="test-domain"` because "DevOps" is not a registered domain under the new domain enforcement rules (§7.3).
- **`tests/test_tasks.py`**: `test_deprecate_task_admin_only` — justification fix.
- **`tests/test_workflows.py`**: `test_deprecate_workflow_admin_only` — justification fix.

All TEST_REVISED changes authorised by user ("Confirmed on both counts" earlier, plus explicit approval for the `test_create_principle_with_domain` change during this session).

### Next session should start from

**Sprint 5**: the next sprint in the roadmap. Read `docs/requirements.md` §10–§12 (embedding generation, vector search) and §14 (ARQ worker) before starting. The sprint will likely introduce the ARQ background worker, embedding generation on confirm transitions, and the similarity search endpoints.

Context that won't be obvious from the code:
- The `domains` and `user_domains` tables exist but there is **no admin API** for managing them (§7.5 was explicitly deferred). The test suite bypasses this by inserting directly. Any sprint that needs a management API should revisit §7.5.
- The migration `20260513_d6e7f8a9b0c1` needs to be run against any non-test database. The `domain` column on tasks/workflows/principles is now NOT NULL with no application default — any existing rows would have been backfilled with `'unknown'` by the migration.

### Watch out for

- `assert_can_return` in `lifecycle.py` does **not** enforce self-review prohibition (contributors can return their own submissions). This is spec-correct — only `confirm` has the prohibition. Don't add it.
- The `ConfirmRequest` body is `| None` in all confirm endpoints. FastAPI treats an absent body and a body of `{}` identically (both result in `ConfirmRequest(justification=None)`). This is intentional.
- The `setup_test_domain_and_users` conftest fixture uses `uuid.uuid5(_SYSTEM_USER_ID, sub)` to generate deterministic UUIDs for pre-seeded users. When `get_current_user` upserts on first request, it finds the user by `sub` and updates without changing the UUID — so `user_domains` continues to resolve.
- The "event loop closed" error in test teardown (visible in some failure traces) is a known asyncpg/asgi-lifespan interaction on test teardown. It does not affect correctness and was present before this session.

---

## Session Close-Out — 2026-05-13

### Completed

- **ORM models**: `LifecycleMixin` (shared identity + lifecycle columns, FK columns via `@declared_attr`); `Fact`, `Concept`, `Principle`, `Task` (with `TaskStep`, `TaskStepAction`, `TaskFactRef`, `TaskConceptRef`, `TaskStepScreenshot`), `Workflow` (with `WorkflowTaskRef`, `WorkflowPrincipleRef`). pgvector `Vector(1536)` embedding column on all five governed record types.
- **Alembic migration** `20260513_b4c5d6e7f8a9`: Creates all 14 tables. Uses `_lifecycle_cols()` factory function to produce fresh `ForeignKey` instances per `create_table` call. Creates pgvector extension. Includes stub `relationships` and `review_claims` tables for v1.1 readiness.
- **Pydantic schemas**: `LifecycleResponse` base; full create/update/response schemas for all five record types. `TaskResponse.irreversible` computed via `@computed_field` from steps at serialisation time. Server-managed flags (`has_deprecated_fact_ref`, `has_deprecated_concept_ref`, `has_incoming_task_change`, `has_pending_task_confirm`) are response-only — not accepted in request bodies.
- **Lifecycle service** (`api/services/lifecycle.py`): State machine enforcement for all transitions — `assert_can_edit`, `assert_can_submit`, `assert_can_confirm` (self-review prohibition; admin exempt), `assert_can_return`, `assert_can_deprecate`, `assert_can_retire`.
- **Route handlers**: Full CRUD + lifecycle endpoints for facts, concepts, principles, tasks, workflows. Correct FastAPI `Annotated` dependency pattern for role checks. `selectinload` for task steps/refs and workflow refs. ARQ `generate_embedding` stub job enqueued on every confirm transition.
- **ARQ worker**: `generate_embedding` placeholder registered in `WorkerSettings.functions`. Startup hook retained.
- **Test infrastructure**: `conftest.py` updated with `CREATE EXTENSION IF NOT EXISTS vector` before schema creation. Skip markers removed from `test_principles.py`, `test_tasks.py`, `test_workflows.py` (they were gated on Sprint 4 implementation).
- **119 tests passing**, mypy clean, ruff clean.
- Committed `8b4119a` and pushed to `origin/main`.

### Incomplete or broken

- **Domain scoping (§7)**: The spec requires contributors to only create/submit/confirm Principles (and Tasks/Workflows) within their assigned domains. The current implementation does not enforce domain assignment — `assert_can_confirm` checks self-review but not domain membership. No tests currently cover this gap (not written for Sprint 4). Needs a `user_domains` table and domain-check logic in the lifecycle service.
- **Worker startup chunk reset**: `startup()` hook logs a placeholder but does not query the DB. Deferred to Sprint 5 once the `ingestion_chunks` table exists.
- **Embedding generation**: `generate_embedding` is a no-op stub. Sprint 7 replaces it with the real LLM call.

### Decisions made

- **Admin self-review exemption**: Admins can confirm their own submissions (break-glass for small teams). §5.1 states the prohibition but does not explicitly address admins. Decision: exempt admins. Spec should be updated to document this explicitly.
- **`task_fact_refs.fact_record_id` has no DB FK**: `record_id` is not unique across governed record tables (multiple versions share a `record_id`), so a DB-level `FOREIGN KEY` constraint is not possible. Application layer enforces that only confirmed records can be referenced. Same applies to `task_concept_refs.concept_record_id`, `workflow_task_refs.task_record_id`, `workflow_principle_refs.principle_record_id`. No spec change needed — consistent with §9.1.
- **Test DB password**: The Docker `blueprinted` superuser was `ALTER USER`-ed to password `blueprinted` (from `blueprinted_dev_password`) on the local dev container to match the hardcoded conftest credentials. The `.env` file still carries `blueprinted_dev_password` for the main `blueprinted` DB — tests use `blueprinted_test` DB only.

### TEST_REVISED commits

The following test files were modified this session. Changes are infrastructure/style only — no test assertions were changed:

- `tests/test_principles.py`: Removed `pytestmark = pytest.mark.skip(reason="Sprint 4: Principles API not yet implemented")` → replaced with `pytestmark = pytest.mark.asyncio`. Rationale: skip marker was a pending-implementation gate; Sprint 4 is now implemented.
- `tests/test_tasks.py`: Same rationale.
- `tests/test_workflows.py`: Same rationale.
- `tests/test_facts.py`: Fixed EN dash → hyphen in docstring (RUF002); reformatted `required` tuple to satisfy E501. No assertion logic changed.
- `tests/test_concepts.py`: Reformatted one JSON literal to satisfy E501. No assertion logic changed.

No `TEST_REVISED` marker required — none of these changes altered what the tests assert.

### Next session should start from

**Sprint 5: Ingestion Pipeline Foundation.**

First task: design and implement the ingestion pipeline entry point. Relevant spec sections:

- §13 — Ingestion pipeline overview
- §14 — ARQ worker (startup hook chunk reset — implement the actual query now that `ingestion_chunks` will exist)
- §6 — Ingestion-specific access control (if any)

The worker startup hook stub in `workers/main.py` has a `# Sprint 4: add database engine initialisation and the chunk reset query here` comment — that is the exact spot to implement in Sprint 5.

The ingestion pipeline produces **task and principle candidates only** (never workflow candidates — see CLAUDE.md). The ingestion API creates records at `draft` or `submitted` status only — never `confirmed`.

### Watch out for

- The `relationships` table exists but all writes must return 422. There is no route for it yet — do not add relationship kinds without a spec update.
- `pgvector` type ignores were removed this session (`ignore_missing_imports = true` in `pyproject.toml` mypy overrides covers the import; mypy no longer raises `type-arg` on `Vector`). If pgvector is upgraded and breaks typing, check: `api/models/fact.py`, `concept.py`, `principle.py`, `task.py`, `workflow.py`.
- The `Annotated` dependency pattern for role checks is non-obvious: `_Writer = Annotated[User, require_role(...)]` — NOT `user: CurrentUser = require_role(...)`. The latter silently skips the role check because FastAPI ignores a default-value `Depends` when `Annotated` already contains one. See `api/routes/facts.py` for the canonical pattern.

---

## Session Close-Out — 2026-05-13

### Completed

- **`docs/requirements.md` §5.3 updated** — documented the phased enforcement decision for the no-machine-can-confirm rule: Sprints 4–9 enforce it by requiring a valid human OIDC JWT (sufficient because machine credentials don't exist yet); Sprint 10 adds the explicit machine-credential rejection check when machine auth is introduced
- **`CLAUDE.md` updated** — same decision captured in standing rules so it doesn't surface as a planning question in every sprint between now and Sprint 10
- **`tests/factories.py` created** — minimal valid payload helpers for all five governed record types (Fact, Concept, Task, Principle, Workflow)
- **`tests/test_facts.py` created** — 37 tests covering the full lifecycle: create draft, read, update, submit, confirm, self-review prohibition, admin break-glass, immutability after confirm, return/resubmit path, deprecate, retire; all roles tested; all skipped pending Sprint 4
- **`tests/test_concepts.py` created** — 20 tests; full lifecycle + Concept-specific fields (summary, explanation, analogies); skipped pending Sprint 4
- **`tests/test_tasks.py` created** — 22 tests; lifecycle + steps (add, update, delete, irreversible derivation), fact-refs and concept-refs (confirmed-only constraint, blocked on confirmed task); skipped pending Sprint 4
- **`tests/test_principles.py` created** — 15 tests; lifecycle + domain field; skipped pending Sprint 4
- **`tests/test_workflows.py` created** — 20 tests; lifecycle + task-refs (confirmed-only constraint) + principle-refs (confirmed-only constraint); skipped pending Sprint 4
- **`tests/conftest.py` patched** — added `_env_file=None` to `test_settings` fixture to prevent pydantic-settings from reading the project `.env`, which contains Docker Compose keys (`AUTHENTIK_*`, `API_PORT`, etc.) that `Settings` rejects with `extra="forbid"`; comment explains why

### Incomplete or broken

Nothing incomplete or broken. 104 new tests collect and skip cleanly. Remaining test errors when running locally are `ConnectionRefusedError` from no database running — expected, CI has Postgres as a service.

### Decisions made

**No-machine-can-confirm enforcement is phased (extends spec §5.3):** The rule is absolute, but the mechanical check is deferred. Sprints 4–9: confirm endpoints require a valid human OIDC JWT, which is sufficient as machine credentials don't exist. Sprint 10: explicit machine-credential rejection added. Spec updated in §5.3 and CLAUDE.md — no further action needed.

**API path assumptions documented in test files:** Tests assume `/api/v1/{record-type}` REST paths, `{id}` as version-specific UUID, sub-resources at `/{id}/steps`, `/{id}/fact-refs`, `/{id}/concept-refs`, `/{id}/task-refs`, `/{id}/principle-refs`. If Sprint 4 diverges on any path, those tests need `TEST_REVISED` commits.

### TEST_REVISED commits

No existing test files were modified. All new test files were written from scratch.

### Next session should start from

**Sprint 4 — Core Data Model and Lifecycle API** (spec §9, §10, §5.1, §18).

Read before starting:
- §9.1–9.3 — shared identity pattern, lifecycle fields, state machine
- §9.5 — schema for whichever record type you're implementing first (Facts recommended — simplest, no sub-resources)
- §10.1–10.2 — immutability and no-machine-can-confirm rules
- §18.1 — Alembic multi-tenant migration pattern

First task: write the Alembic migration for the core schema — `facts`, `concepts`, `principles`, `tasks`, `task_steps`, `task_step_actions`, `task_fact_refs`, `task_concept_refs`, `workflows`, `workflow_task_refs`, `workflow_principle_refs`, plus the shared identity/lifecycle columns on each. Then wire up the Facts API and un-skip `tests/test_facts.py` as tests pass.

The recommended order: migration → Facts API → Concepts API → Principles API → Tasks API → Workflows API. Facts and Concepts share the same pattern; do Facts first and Concepts will be fast. Tasks are the most complex (steps, refs, irreversible derivation). Workflows depend on Tasks and Principles being confirmable first.

### Watch out for

- **Sprint 4 is rated Low confidence** — re-read the relevant spec sections and identify the first three things that could go wrong before writing any code (per the sprint overview guidance for low-confidence sprints)
- **App service not yet in Docker Compose** — the stack only has Postgres, Redis, and Authentik. To run end-to-end smoke tests locally, the `api` service needs to be added to `deploy/docker-compose.yml`. The Sprint 1 `Dockerfile` and entrypoint exist; it just hasn't been wired into Compose yet
- **Multi-tenancy not yet implemented** — the migration must not hardcode `public` schema; the Alembic `env.py` already has a multi-tenant stub (§18) — follow that pattern
- **`pgvector` extension** — the embedding column (`vector(1536)`) requires the pgvector extension to be enabled in the migration before the column can be created. The `db` service in Docker Compose uses the `pgvector/pgvector:pg16` image which has the extension available but it must be explicitly enabled with `CREATE EXTENSION IF NOT EXISTS vector`
- **Test API path assumptions** — if Sprint 4 uses different URL structures than assumed in the Sprint 3 tests (e.g. `/api/v1/facts/{record_id}` instead of `/{id}`), those tests need `TEST_REVISED` commits with rationale before being un-skipped

## Session Close-Out — 2026-05-13

### Completed

- Fixed `deploy/docker-compose.yml`: changed `MINIO_ROOT_PASSWORD` from `:?` (required marker) to `:-changeme` (default) so the storage profile service no longer blocks non-storage startups
- Created `deploy/authentik/media`, `deploy/authentik/certs`, `deploy/authentik/custom-templates` directories with correct ownership (UID 1000) for the Authentik container
- Started Authentik stack (`auth`, `auth-db`, `auth-redis`, `auth-worker`) successfully
- Completed Authentik first-time setup wizard (akadmin account created)
- Created Authentik groups matching all five Blueprinted roles: `admin`, `contributor`, `content_publisher`, `viewer`, `audit`
- Created Authentik OAuth2/OpenID provider named `blueprinted` (confidential client, RS256, implicit consent flow)
- Created Authentik application `blueprinted` linked to the provider
- Created `blueprinted-roles` scope mapping (expression: `return [group.name for group in request.user.ak_groups.all()]`) and added it to the provider
- Populated all OIDC env vars in `.env`:
  - `OIDC_ISSUER=http://192.168.1.82:9000/application/o/blueprinted/`
  - `OIDC_CLIENT_ID=REDACTED_CLIENT_ID`
  - `OIDC_CLIENT_SECRET=REDACTED_CLIENT_SECRET`
  - `OIDC_JWKS_URI=http://192.168.1.82:9000/application/o/blueprinted/jwks/`
  - `OIDC_AUDIENCE=REDACTED_CLIENT_ID`
- Verified JWKS endpoint is live and returning an RS256 signing key

### Incomplete or broken

Nothing is incomplete or broken. Sprint 2 (Human Auth) is fully complete including the Authentik browser setup.

### Decisions made

No decisions deviate from the spec.

One infrastructure note that doesn't affect the spec: the `MINIO_ROOT_PASSWORD` required-marker change means the storage service will start with password `changeme` if `--profile storage` is used without setting the env var. Operators should set `MINIO_ROOT_PASSWORD` in `.env` before enabling the storage profile in production.

### TEST_REVISED commits

No test files were modified this session.

### Next session should start from

**Sprint 3** — the first sprint that introduces governed content. Read spec §7 (Facts) and §8 (lifecycle state machine: draft → submitted → confirmed) before starting.

The first task is the Alembic migration and CRUD API for Facts, including:
- `facts` table with lifecycle state, version, tenant schema awareness
- `POST /api/v1/facts` (creates draft)
- `GET /api/v1/facts/{id}`
- `PATCH /api/v1/facts/{id}` (update draft/submitted)
- `POST /api/v1/facts/{id}/submit`
- `POST /api/v1/facts/{id}/confirm` — must reject non-human credentials (§5 absolute rule)

The Blueprinted API is not yet running as a service — the Docker Compose stack only has Authentik + Postgres + Redis. Sprint 3 should also wire up the app service in `docker-compose.yml` if end-to-end smoke testing is wanted.

### Watch out for

- The `.env` contains real credentials (OIDC client secret, Authentik DB password, etc). It is gitignored — confirm before any `git add .`
- The `OIDC_*` env vars use the host IP `192.168.1.82`. If the machine IP changes or the API runs inside Docker (where `192.168.1.82` may not resolve correctly), the JWKS URI and issuer will need updating. When the API is containerised, consider using the Docker service name `auth` internally.
- The `blueprinted-roles` scope must be explicitly requested by OAuth2 clients (`scope=openid email roles`) for the `roles` claim to appear in tokens. It will not appear in tokens that only request `openid email`.
- Multi-tenancy (schema-per-tenant, §11) is not yet implemented. Sprint 3 facts work should not assume it is in place, but should be designed to accommodate it — don't hardcode `public` schema.

---

## Session Close-Out — 2026-05-13

### Completed

- **Tooling audit** — confirmed uv 0.11.14, Docker 29.4.3, Docker Compose v5.1.3, Python 3.10 system / 3.12 via uv are all present and working
- **`pyproject.toml`** — Python 3.12, all production and dev dependencies pinned, Ruff config, mypy strict config, pytest config, `blueprinted` CLI entry point
- **`api/`** — `config.py` (Pydantic `BaseSettings`), `logging.py` (structlog JSON, secret redaction), `middleware.py` (request ID, structlog context binding), `database.py` (async SQLAlchemy engine + session factory), `dependencies.py` (`DBSession` annotated type), `main.py` (app factory, lifespan, secure.py headers), `routes/health.py` (`GET /healthz`)
- **`migrations/`** — Alembic configured with sync psycopg2 driver for CLI; `env.py` multi-tenant-aware stub; `alembic.ini`; empty `versions/` directory
- **`cli/main.py`** — `blueprinted migrate` (wraps Alembic, supports `--dry-run`, `--status`, `--tenant` stub), `blueprinted healthcheck`
- **`workers/main.py`** — ARQ entrypoint with load-bearing startup hook (§14), clearly labelled, Sprint 4 placeholder present
- **`deploy/docker-compose.yml`** — full stack: pgvector/pg16, Redis 7.4, Authentik 2025.4.1 (server + worker + own postgres + own redis), MinIO opt-in via `--profile storage`
- **`deploy/docker-compose.override.yml`** — dev overrides (live reload, volume mounts)
- **`deploy/Dockerfile`** — uv-based, layer-cached deps
- **`deploy/.env.example`** — all bootstrap env vars documented
- **`tests/conftest.py`** — `setup_test_db` (sync `asyncio.run()` table creation), `client` fixture using `asgi-lifespan` `LifespanManager`
- **`tests/test_health.py`** — 2 tests, both passing
- **`.github/workflows/ci.yml`** — postgres+redis services, `uv sync --frozen`, migrate, pytest, ruff, mypy, pip-audit
- **`.gitignore`**
- Committed and pushed to `origin/main` (commit `8e5a116`)

### Incomplete or broken

Nothing incomplete or broken.

### Decisions made

1. **Python 3.12** — spec doesn't specify a Python version. 3.12 chosen as stable, full typing support, well-supported by all deps. Spec could be updated to note this but it's not load-bearing.

2. **`asgi-lifespan` added as a dev dependency** — `httpx.ASGITransport` does not trigger the FastAPI lifespan context manager, so `app.state.session_factory` is never populated during tests. `asgi-lifespan==2.1.0` wraps the app in `LifespanManager` to fire startup/shutdown properly. Every test fixture that creates a client must use this pattern.

3. **`structlog.stdlib.add_logger_name` omitted** — incompatible with `PrintLoggerFactory`; raises `AttributeError: 'PrintLogger' object has no attribute 'name'` at runtime. Removed from the processor chain.

4. **`secure.py` `type: ignore[arg-type]`** — `secure.py` v1's `set_headers()` expects `HeadersProtocol` but Starlette's `Response.headers` is `MutableHeaders`. Works at runtime. Suppressed with a targeted type ignore in `api/main.py:56`.

5. **`asyncio.run()` in `setup_test_db` fixture** — session-scoped async fixtures in pytest-asyncio 0.25 have teardown event-loop-scope conflicts with SQLAlchemy's async engine. Table creation runs in an isolated `asyncio.run()` call. Transactional isolation per test deferred to Sprint 4.

### TEST_REVISED commits

No test files were modified this session. Tests were written new, not revised.

### Next session should start from

**Sprint 2: Authentik — Human Auth** (spec §5, §5.1).

First task: get Authentik running in Docker Compose and verify the admin UI is reachable at `localhost:9000`. Then:
1. Complete Authentik's initial setup wizard in a browser
2. Create an OIDC provider and application in Authentik for the Blueprinted API
3. Implement JWT/OIDC token validation in FastAPI (`api/auth.py`) — verify tokens against Authentik's JWKS endpoint
4. Implement `GET /api/v1/users/me`
5. Wire role-based access control (§5.1: Admin, Contributor, Content Publisher, Viewer, Audit)

Read §5 and §5.1 carefully before starting. Sprint 2 is rated Low confidence.

### Watch out for

- **Authentik initial setup requires a browser** — first-time wizard at `localhost:9000/if/flow/initial-setup/` must be completed manually, no CLI bootstrap.
- **`AUTHENTIK_SECRET_KEY` and `AUTHENTIK_DB_PASSWORD` are separate from `APP_SECRET_KEY`** — generate all three independently.
- **`deploy/authentik/` directory is empty** — populated with media/certs when Authentik runs (gitignored).
- **No first migration exists yet** — `alembic_version` table is absent. `GET /healthz` handles this gracefully (`"migration_version": "no_migrations_applied"`). Intentional.
- **`uv.lock` is committed** — do not add to `.gitignore`. It is the pinned lockfile per the no-floating-dependencies rule.

## Session Close-Out — 2026-05-12

### Completed

- Installed LobeHub Skills Marketplace search engine skill (`lobehub-skills-search-engine`) to `.claude/skills/` for the `claude-code` agent
- Registered marketplace identity as `Claude-Blueprinted` (credentials saved to `~/.lobehub-market/credentials.json`)
- Added Context7 MCP server (`@upstash/context7-mcp`) and GitHub MCP server (`@modelcontextprotocol/server-github`) via `.mcp.json` at project root (correct location — `settings.json` does not support `mcpServers`)
- Added `enableAllProjectMcpServers: true` to `.claude/settings.json` to auto-approve both servers without per-session prompts
- User added `GITHUB_PERSONAL_ACCESS_TOKEN` to shell profile — confirmed working
- Both MCPs verified loading correctly: 25 GitHub tools and 2 Context7 tools available

### Incomplete or broken

Nothing incomplete or broken.

### Decisions made

No decisions deviate from or extend the spec. This session was purely developer tooling setup — no application code was written.

### TEST_REVISED commits

No test files were modified this session.

### Next session should start from

The project has no application code yet. The next session should begin with `/plan` and orient to the requirements spec at `docs/requirements.md` before writing anything.

### Watch out for

- MCP servers are defined in `.mcp.json` (project root), not in `settings.json`. Do not move them.
- The LobeHub marketplace registration is device-scoped (credentials in `~/.lobehub-market/credentials.json`). If working on a different machine, re-run the register command — it is safe to run multiple times and returns existing credentials if already registered.
- `GITHUB_PERSONAL_ACCESS_TOKEN` must be set in the shell environment. The `.mcp.json` passes no token — the server inherits it from the process environment.