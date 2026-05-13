# Session History

This file records close-out notes from each Claude Code session.
Paste the output of `/closeout` here at the end of every session.
When starting a new session, paste the most recent entry as context.

---

<!-- Sessions are added below in reverse chronological order (newest first) -->

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