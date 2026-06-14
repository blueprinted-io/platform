# Blueprinted Platform — Project Memory

Durable context for AI harness sessions. Update when decisions or constraints change.

## Architecture

- **FastAPI** async API with SQLAlchemy 2.0 async + Alembic migrations
- **PostgreSQL** with pgvector extension for semantic search
- **ARQ** (Redis-backed) for background ingestion workers
- **Authentik** OIDC — backend verifies RS256 JWTs; no session cookies
- **structlog** for structured JSON logging
- **slowapi** for rate limiting; **secure** for security headers

## Key constraints

- Single operator, single tenant (v1 scope).
- Human-in-the-loop: no machine may perform a confirmed state transition on a governed record.
- Independent git repo — run `git` from inside `platform/`. Not a monorepo.
- Never write real credentials into `SESSIONS.md` — it is committed to git.
- Knowledge graph at `graphify-out/` — use `graphify query` for codebase questions when available.

## Repo layout

```
api/          FastAPI routes and dependencies
workers/      ARQ background workers (ingestion pipeline)
cli/          Typer CLI tooling
migrations/   Alembic migrations
tests/        pytest test suite (real DB — no mocks)
```

## Sprint state

- See `SPRINTS.md` for sprint history.
- See `SESSIONS.md` for the active session (one entry only; archive in `SESSIONS_ARCHIVE.md`).
- Full spec: `docs/requirements.md`

## Decisions

- Admins implicitly own all domains (§7.2); domain assignment UI hidden for admin-role users.
- Domain → Maps → Workflows → Tasks hierarchy; Maps are display-layer only, no governance lifecycle.
- Ingestion: triage → human review gate → extraction (spec v4.6 §11.5a).
- Worker split (god-worker → triage + extraction workers) planned for Sprint 13.
- Tests must hit a real DB — never mock the database layer (prior incident: mocked tests masked a broken migration).
- Test DB: `blueprinted-test-db` container on port 5433; deploy stack on 5432.
