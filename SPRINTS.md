# Sprint History — blueprinted.io
Compact sprint retrospectives. Newest first.
Updated at the end of each sprint.

---

## Sprint 10 — Machine Auth, CLI, Observability

**Goal:** Machine credentials for agent access, audit log, CLI operational commands
**Status:** Complete
**Spec at start:** v4.6 → **at end:** v4.7

**Completed:**
- Spec v4.7: `api_keys` and `audit_log` table schemas defined (spec gap closed before implementation)
- `AgentRole` enum (workflow_consumer, staleness_monitor, orphan_detector) added to `auth.py`
- `is_machine_credential()` helper — `agent:` role prefix as human/machine distinction
- `assert_can_confirm` rejects machine credentials with HTTP 403 (no-machine-can-confirm, §5.3)
- `api_keys` table + ORM model + migration — SHA-256 hash storage, `bp_` prefix format, 288-bit entropy
- `GET/POST/DELETE /api/v1/admin/api-keys` — Admin-only; raw key returned once on creation
- `bp_` Bearer token auth in `get_current_user` — synthetic User record per key, role forwarded
- `audit_log` table + ORM model + migration — append-only, JSONB detail column
- `write_audit_event()` service helper — used on api_key_created and api_key_revoked
- `GET /api/v1/audit` — Audit and Admin roles, newest-first, paginated
- CLI: `blueprinted tenants list|create|delete` (stubs), `backup` (pg_dump wrapper), `upgrade` (pre-flight + migrate + restart), `api-keys create|revoke`
- `cli/**/*.py` added to ruff per-file-ignores (subprocess/print intentional in CLI)
- 21 new tests: test_api_keys.py (13), test_audit_log.py (8)

**Decisions:**
- Machine/human distinction is role-prefix based (`agent:`) — same OIDC JWT validation path, no separate token type
- Synthetic User record per API key (`sub = "apikey:<id>"`) — allows `CurrentUser` dependency to work unchanged across all routes
- `last_used_at` updated inline (not fire-and-forget) — simpler, v1 latency acceptable
- `audit_log` event for break_glass_confirm not yet wired — confirm endpoint refactor deferred to Sprint 11 hardening
- `blueprinted tenants` commands are stubs — multi-tenant provisioning is post-v1 work

**Spec changes:**
- v4.7: `api_keys` table defined (§9.6), `audit_log` table defined (§9.6), §5.3 extended with credential distinction mechanism and HTTP 403 response text

---

## Sprint 9 — Frontend Admin and Supporting

**Goal:** Admin write screens, write/lifecycle actions for governed records, ingestion estimate review
**Status:** Complete (delivered within Sprint 8 sessions — scope expanded in practice)
**Spec at start:** v4.5 → **at end:** v4.6

**Completed:**
- Admin: domain create/enable/disable, user domain assignment, system settings + LLM config + test-connection
- Governed records: task/workflow/principle create, edit, revise, lifecycle actions (submit/confirm/return) inline on detail pages
- Ingestion: estimate review page (type toggle, reject, merge, approve) wired to triage estimates API
- Notifications: mark read, mark all read
- Relationships list view (§23.9)
- CI auto-fix pipeline: event-driven GitHub Actions workflow using synthetic.new GLM-5.1

**Decisions:**
- Dashboard (§23.2) stubbed — customisable layout model needs speccing before implementation; see §24
- Profile PATCH deferred — Authentik owns identity; platform-specific preferences deferred to v1.1; profile photo reads `picture` JWT claim
- Admin user POST not implemented — users created via Authentik JIT upsert, no platform-side user creation needed

---

## Sprint 8 — Core Read Screens (frontend)

**Goal:** Build core read screens in `blueprinted-io/app` — tasks, workflows, principles, search, review queue
**Status:** Complete
**Spec at start:** v4.3 → **at end:** v4.5 (spec amendments made mid-sprint)

**Completed:**
- Task list, detail, create, edit, revise, diff view
- Workflow list, detail, create, edit, diff view
- Principle list, detail, create, edit
- Review queue with claim/confirm/return inline actions
- Search page with full-text and semantic results
- Ingestion: list, create (PDF/HTML/JSON), detail/status, section selection, nav selection, candidate review, estimate review
- Notifications page with mark-read and mark-all-read
- Admin: settings (LLM config, test-connection), domains, users (domain assignment), health
- Relationships list view (§23.9)
- Dashboard stubbed (§23.2) — pending component model spec
- Profile page (read-only, §23.1) — PATCH deferred pending preference model spec

**Decisions:**
- Facts and Concepts dissolved (v4.4) — authored inline on tasks as `TEXT[]`; no standalone screens
- PyJWT upgraded 2.12.1 → 2.13.0 via auto-fix pipeline (PYSEC-2026-175/177/178/179)

**Spec changes:**
- v4.4: Facts and Concepts dissolved (§9.5, §23.5)
- v4.5: Various frontend clarifications

**Carried forward:**
- Dashboard analytics endpoint and component model — needs design before implementation (§23.2, §24)
- Profile PATCH — deferred pending platform-owned preference model (§23.1, §24)

---

## Sprint 7 — Search and Embeddings

**Goal:** Full-text and semantic search API; embedding generation on confirm transitions
**Status:** Complete
**Spec at start:** v4.2 → **at end:** v4.2

**Completed:**
- ARQ pool wired into FastAPI lifespan (`app.state.arq_pool`)
- `generate_embedding` job fully implemented — fetches record text per type, calls OpenAI-compatible embedding API via httpx, writes to pgvector column
- Embedding triggered on all five record-type confirm endpoints and review confirm path
- GIN tsvector indexes migration (`a1b2c3d4e5f6`)
- `GET /api/v1/search` — UNION ALL full-text across all types, optional semantic reranking (60%/40% hybrid), domain filter, pagination
- 162 tests passing

**Decisions:**
- Domain filter excludes facts and concepts entirely when `?domain=X` is specified — they have no domain column and surface implicitly through tasks. Confirmed by user; should be added to §12.
- S608 (SQL injection) Ruff false positive suppressed via `per-file-ignores` for `search.py` — all SQL strings are built from hardcoded `_TypeConfig` fields, never user input.
- Confirmed-record test helpers use inline `async def _make_confirmed_X()` functions rather than session-scoped fixtures — event loop scope mismatches make session-scoped async DB fixtures unsafe in this suite.
- Sprint 7 was executed before Sprint 6 (ingestion pipeline). Both were unblocked after Sprint 5; search/embeddings was chosen first as the lower-risk sprint.

**Spec changes:**
- None — domain filter decision noted for future §12 addition but not yet committed to spec.

**Carried forward:**
- `api.services.settings` module does not exist — `crawl_html` robots.txt setting lookup will always fail silently until this is built (Sprint 10 or later).

---

## Sprint 6 — Ingestion Pipeline

**Goal:** Full document ingestion pipeline — PDF, HTML, and JSON source types; LLM extraction; candidate review and commit
**Status:** Complete (including task_order spec gap, resolved after Sprint 7)
**Spec at start:** v4.2 → **at end:** v4.3

**Completed:**
- Ingestion ORM models: `Ingestion`, `IngestionChunk`, `IngestionCandidate`, `IngestionNavPage`; worker startup hook chunk reset implemented
- `prompts/ingestion/` — triage, extract_task, extract_principle; `api/prompts.py` loader
- `process_chunks` ARQ job — triage + extraction via LLM, candidate creation
- PDF ingestion: `POST /api/v1/ingestions`, `GET /ingestions/{id}/status`, `POST /ingestions/{id}/select`
- Candidate review and commit: `GET /candidates`, `PATCH /candidates/{id}`, `POST /candidates/{id}/commit`
- HTML ingestion: `POST /api/v1/ingestions/html`, `crawl_html` and `render_nav_pages` ARQ jobs, nav page listing and selection
- JSON ingestion: `POST /api/v1/ingestions/json` — candidates created directly, no chunking
- `task_order` cross-reference validation via optional `id` field on `JsonTaskItem`
- 250 tests passing

**Decisions:**
- `raw_facts`/`raw_concepts` stored as `TEXT[]` on tasks at commit time — linking to governed Fact/Concept records at commit is not feasible; operators link manually after commit. Later dissolved entirely in v4.4 (Sprint 8).
- `irreversible` is per-step, not per-task — extraction prompt had it at task level (spec error); corrected at commit time.
- Domain required in `CandidateCommitRequest` body, not stored on the candidate — accommodates absent domain in extracted JSON.
- Same-origin-only nav link deduplication in `crawl_html`.
- `task_order` cross-reference validation requires optional per-item `id` field; tasks without `id` must have empty `task_order`.

**Spec changes:**
- v4.3: §11.16 Prompt Contracts added; §11.4 clarified candidate JSON vs. import payload format; `json_import_schema_spec.md` updated with `id` field and cross-reference validation rules.

**Carried forward:**
- `playwright install chromium` must be added to deployment runbook.
- `api.services.settings` not yet built — `crawl_html` robots.txt setting defaults to `true` silently.
- `IngestionNavPage.parent_id` always NULL — multi-level nav deferred to v1.1.

---

## Sprint 5 — Review Queue

**Goal:** Review queue, claim/release mechanics, confirm/return via review path, claim expiry job
**Status:** Complete
**Spec at start:** v4.2 → **at end:** v4.2

**Completed:**
- `GET /api/v1/review/queue` — domain-scoped, own-submissions excluded, paginated, active claim info embedded
- `POST /api/v1/review/{type}/{id}/claim` — advisory claim with 48h expiry; re-claim refreshes expiry; 409 on conflict
- `POST /api/v1/review/{type}/{id}/release`
- `POST /api/v1/review/{type}/{id}/confirm` and `.../return` — lifecycle rules enforced, auto-release on action
- `expire_review_claims` ARQ cron job — runs every 15 minutes
- Worker DB initialisation in `startup()` hook — `ctx["db_engine"]` set for use by job functions
- 145 tests passing

**Decisions:**
- `REVIEW_CLAIM_EXPIRY_HOURS_DEFAULT = 48` hardcoded pending system_settings service (Sprint 10).
- Facts and Concepts are not claimable — consistent with `review_claims.entity_type` which enumerates only task/workflow/principle.
- Review confirm does not yet enqueue embedding generation — stub follows same pattern as record-level confirm (Sprint 7 placeholder comment in place).

**Spec changes:**
- None.

**Carried forward:**
- Embedding generation still a no-op stub on all confirm transitions — wired up in Sprint 7.
- No admin API for managing domains/user_domains (§7.5 deferred to Sprint 10).

---

## Sprint 4 — Core Data Model and Lifecycle API

**Goal:** ORM models, Alembic migration, CRUD + lifecycle endpoints for all five governed record types; domain enforcement
**Status:** Complete
**Spec at start:** v4.1 → **at end:** v4.2

**Completed:**
- `LifecycleMixin` with shared identity + lifecycle columns; ORM models for Fact, Concept, Principle, Task (with TaskStep, TaskStepAction, TaskFactRef, TaskConceptRef, TaskStepScreenshot), Workflow (with WorkflowTaskRef, WorkflowPrincipleRef); pgvector `Vector(1536)` embedding column on all five types
- Migration `b4c5d6e7f8a9` — all 14 tables, pgvector extension, stub relationships and review_claims tables
- Pydantic schemas for all five types; lifecycle service (`assert_can_edit/submit/confirm/return/deprecate/retire`)
- Full CRUD + lifecycle route handlers for all five types; `Annotated` dependency pattern for role checks
- Domain enforcement: `domains`, `user_domains` tables; `assert_domain_active`, `assert_domain_access` in lifecycle service; migration `d6e7f8a9b0c1`; domain made NOT NULL on tasks/workflows/principles
- 119 tests passing

**Decisions:**
- Admin self-review exemption — admins can confirm their own submissions as break-glass. Spec updated in §5.1.
- `task_fact_refs.fact_record_id` has no DB FK — `record_id` is not unique across versions; application layer enforces confirmed-only references.
- `ConfirmRequest | None = None` pattern — ruff B008 fires on function-call defaults; `None` with inline `body.justification if body else None` is correct.

**Spec changes:**
- v4.2: §5, §5.1 (admin self-review exemption); §7.1–7.5 (domain enforcement); §9.2, §9.5 (domain field required); §25 (decision log).

**Carried forward:**
- Domain management admin API (§7.5) deferred to Sprint 10.
- Embedding generation is a no-op stub — wired up in Sprint 7.
- Worker startup chunk reset is a placeholder — implemented in Sprint 6.

---

## Sprint 3 — Test Infrastructure and Specification Gaps

**Goal:** Full test suite for all governed record types (pending Sprint 4); resolve no-machine-can-confirm phased enforcement gap
**Status:** Complete
**Spec at start:** v4.1 → **at end:** v4.1

**Completed:**
- `tests/factories.py` — minimal valid payload helpers for all five record types
- `tests/test_facts.py` (37 tests), `test_concepts.py` (20), `test_tasks.py` (22), `test_principles.py` (15), `test_workflows.py` (20) — full lifecycle coverage, all skipped pending Sprint 4 implementation
- `tests/conftest.py` — `_env_file=None` added to `test_settings` fixture to prevent pydantic-settings reading project `.env`
- `docs/requirements.md` §5.3 updated — phased enforcement decision documented
- `CLAUDE.md` updated — same decision in standing rules

**Decisions:**
- No-machine-can-confirm phased enforcement: Sprints 4–9 enforce via OIDC JWT requirement (machine credentials don't exist yet); Sprint 10 adds explicit machine-credential rejection when machine auth is introduced. Absolute rule unchanged — only the mechanical check is sequenced.

**Spec changes:**
- §5.3 updated — phased enforcement approach documented. No version bump.

---

## Sprint 2 — Human Auth (Authentik)

**Goal:** Authentik running in Docker Compose; OIDC provider configured; JWT validation in FastAPI
**Status:** Complete
**Spec at start:** v4.1 → **at end:** v4.1

**Completed:**
- Authentik Docker Compose stack running (`auth`, `auth-db`, `auth-redis`, `auth-worker`)
- Authentik first-time setup completed; akadmin account created
- Groups created for all five Blueprinted roles: admin, contributor, content_publisher, viewer, audit
- OAuth2/OpenID provider `blueprinted` registered (RS256, implicit consent)
- `blueprinted-roles` scope mapping created (`return [group.name for group in request.user.ak_groups.all()]`)
- All OIDC env vars populated in `.env`; JWKS endpoint verified live

**Decisions:**
- None — infrastructure setup only. No spec sections affected.

**Spec changes:**
- None.

**Carried forward:**
- FastAPI OIDC token validation (`api/auth.py`) not implemented until Sprint 4.

---

## Sprint 1 — Foundation

**Goal:** Project scaffold, tooling, CI pipeline, Docker Compose stack
**Status:** Complete
**Spec at start:** v4.1 → **at end:** v4.1

**Completed:**
- `pyproject.toml` — Python 3.12, all production and dev dependencies pinned, Ruff, mypy strict, pytest config, `blueprinted` CLI entry point
- `api/` skeleton — `config.py`, `logging.py` (structlog JSON, secret redaction), `middleware.py` (request ID), `database.py` (async SQLAlchemy), `dependencies.py`, `main.py` (lifespan, secure.py headers), `routes/health.py`
- `migrations/` — Alembic with multi-tenant-aware `env.py` stub; `alembic.ini`
- `cli/main.py` — `blueprinted migrate` (dry-run, status, tenant stub), `blueprinted healthcheck`
- `workers/main.py` — ARQ entrypoint with load-bearing startup hook, Sprint 4 placeholder
- `deploy/docker-compose.yml` — pgvector/pg16, Redis 7.4, Authentik 2025.4.1, MinIO opt-in
- `deploy/docker-compose.override.yml`, `deploy/Dockerfile`, `deploy/.env.example`
- `tests/conftest.py`, `tests/test_health.py` (2 tests passing)
- `.github/workflows/ci.yml` — pytest, ruff, mypy, pip-audit
- Committed `8e5a116`

**Decisions:**
- Python 3.12 — not specified in spec; chosen as stable with full typing support.
- `asgi-lifespan` added as dev dependency — `httpx.ASGITransport` does not trigger FastAPI lifespan; `LifespanManager` required for all test client fixtures.
- `structlog.stdlib.add_logger_name` omitted — incompatible with `PrintLoggerFactory` at runtime.
- `asyncio.run()` in `setup_test_db` — session-scoped async fixtures have event-loop teardown conflicts; table creation isolated in its own `asyncio.run()` call.

**Spec changes:**
- None.

**Carried forward:**
- App service not yet in Docker Compose — added during Sprint 4.
- Multi-tenancy stub only — not enforced until schema migration work.
