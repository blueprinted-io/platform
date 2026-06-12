# blueprinted — Platform

Production backend for the blueprinted.io knowledge governance platform.

> **Status:** In active development, pre-release. Core API is feature-complete through Sprint 12. Not yet publicly deployed — the live demo at [app.blueprinted.io](https://app.blueprinted.io) runs the original MVP (`blueprinted-io/core`).

---

## What this is

Blueprinted is a structured knowledge platform built around a single proposition:

> *Your agents consume the same knowledge and skills data that your humans do.*

Knowledge is expressed as governed, versioned API records — not documents or wikis. The API is the product. The UI ([`blueprinted-io/app`](https://github.com/blueprinted-io/app)) is one consumer; AI agents, automation, and downstream products are others. All consumers use the same authentication and access rules with no privileged path.

This repository is a ground-up rebuild of [`blueprinted-io/core`](https://github.com/blueprinted-io/core). The governance model and record types are largely unchanged — the rebuild is about foundations and architecture.

---

## What's different from the MVP

| Area | MVP (`core`) | Platform (this repo) |
|------|-------------|----------------------|
| Auth | Cookie-switched roles | Authentik OIDC, RS256 JWTs, domain-scoped roles |
| Database | SQLite | PostgreSQL 16 + pgvector |
| Search | None | Full-text + semantic hybrid (60/40) via pgvector |
| Ingestion | Basic | PDF (outline-aware), HTML (Playwright), JSON; LLM triage + human review gate |
| Jobs | Synchronous | ARQ + Redis async job queue |
| Frontend | Server-rendered | Separate React app (`blueprinted-io/app`) |
| API design | Web app with a DB behind it | API-first; UI is just one consumer |

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.136, Python 3.12, SQLAlchemy async |
| Database | PostgreSQL 16 + pgvector |
| Migrations | Alembic |
| Background jobs | ARQ + Redis |
| Auth | Authentik 2025.4 (OIDC / RS256) |
| Ingestion | PyMuPDF (PDF), Playwright (HTML) |
| Storage | MinIO / S3-compatible (optional) |
| Logging | structlog (JSON, secret redaction) |
| Linting / types | Ruff, mypy strict |
| Tests | pytest-asyncio, 250+ tests |
| CI | GitHub Actions (pytest, ruff, mypy, pip-audit) |

---

## Running locally

```bash
# Start the full stack (PostgreSQL, Redis, MinIO, Authentik)
cd deploy
docker compose up -d

# Run migrations
blueprinted migrate

# Health check
blueprinted healthcheck
```

See [docs/setup/](docs/setup/) for Authentik first-run configuration and the full environment variable reference.

---

## Testing

Tests run against a real PostgreSQL instance — no database mocking. The schema is created fresh each session via SQLAlchemy.

Routes are exercised end-to-end through `httpx.AsyncClient` against the live ASGI app (via `asgi-lifespan`). JWT auth is replaced with a `StubTokenVerifier` and ARQ with a `StubArqPool` that records calls without touching Redis.

```bash
# Start the test database container first (port 5433)
pytest
```

---

## Project structure

```
api/          FastAPI application — routes, models, schemas, services
workers/      ARQ worker — background jobs
migrations/   Alembic migrations
prompts/      Versioned LLM prompt files (ingestion pipeline)
cli/          blueprinted CLI (migrate, healthcheck)
deploy/       Docker Compose stack and Dockerfile
tests/        pytest suite (250+ tests)
docs/         Requirements spec, architecture notes, setup guides
```

---

## Related repos

| Repo | Description |
|------|-------------|
| [`blueprinted-io/app`](https://github.com/blueprinted-io/app) | React frontend |
| [`blueprinted-io/core`](https://github.com/blueprinted-io/core) | Original MVP — best place to understand the data model |
