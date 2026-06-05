# blueprinted.io — Platform

**AI-native knowledge governance platform.** Internal use only: not yet public.

---

## What this is

Blueprinted is a structured knowledge platform built around a single proposition:

> *Your agents consume the same knowledge and skills data that your humans do.*

Knowledge is expressed as governed, versioned API records, not documents or wikis. The API is the product. The UI is one consumer; AI agents, automation, and downstream products are others. All consumers use the same authentication and access rules with no privileged path.

This repository is a ground-up rebuild of the original MVP (`blueprinted-io/core`). The governance model and record types are largely unchanged — the rebuild is about foundations and architecture, not a redesign.

---

## What it adds over the MVP

The MVP (`lcs_mvp`) proved the model: governed Tasks, Workflows, and Primers (now Principles) with a review lifecycle. It ran on SQLite with cookie-based role switching. This platform is the production rebuild on proper foundations.

### Real authentication and authorisation

Cookie-switched roles are replaced by a self-hosted [Authentik](https://goauthentik.io/) OIDC identity provider. JWTs are RS256-signed and validated on every request. Five roles govern access — `admin`, `contributor`, `content_publisher`, `viewer`, `audit` — with domain-scoped enforcement so contributors only operate within their assigned areas.

### A real database

PostgreSQL 16 replaces SQLite, with pgvector as an extension. Beyond powering search today, the vector store is the foundation for relationship traversal, surfacing connections between records semantically rather than requiring explicit links to be authored.

### Ingestion redesigned

The MVP ingested content crudely. This platform replaces that with a proper pipeline:

- **PDF** — structured chunking via PyMuPDF (outline-aware, not naive page splits)
- **HTML** — full site-nav crawl with Playwright rendering, replacing a BeautifulSoup plaintext dump
- **JSON** — structured import that bypasses chunking entirely

The pipeline runs LLM triage to classify and estimate candidates, presents them for human review, then runs targeted extraction on approved candidates only. Nothing reaches the governed record store without a human in the loop.

### Search as a first-class citizen

Search was an afterthought in the MVP. Here it's a first-class API endpoint — full-text across all record types with optional semantic reranking via pgvector embeddings (60/40 hybrid). Embeddings are generated against any OpenAI-compatible API.

### Truly API-first

The MVP was a web app with a database behind it. This platform inverts that: the API is the product, and the UI (`blueprinted-io/app`) is simply one consumer of it, no different in principle to an automation pipeline, an AI agent, or a third-party product. No privileged routes, no server-rendered shortcuts.

---

## Stack

| Layer | Technology | Why? |
|---|---|---|
| API | FastAPI 0.136, Python 3.12, SQLAlchemy async | Async-native end-to-end; Python is the natural fit given LLM tooling |
| Database | PostgreSQL 16 + pgvector | pgvector adds semantic search and relationship traversal in-engine — no separate vector store |
| Migrations | Alembic | Standard SQLAlchemy migration tool; version-controlled schema history |
| Background jobs | ARQ + Redis | ARQ is async-native (matches FastAPI/asyncio stack); Redis doubles as queue and cache |
| Auth | Authentik 2025.4 (OIDC/RS256) | Self-hosted — no third-party data dependency; RS256 JWTs verify locally without a network round-trip |
| Ingestion | PyMuPDF (PDF), Playwright (HTML) | PyMuPDF is outline-aware (not naive page splits); Playwright renders JS-heavy sites that BeautifulSoup can't handle |
| Storage | MinIO / S3-compatible (optional) | S3-compatible API means a trivial swap to cloud storage (S3, R2) when needed |
| Logging | structlog (JSON, secret redaction) | JSON logs are machine-parseable; built-in processor pipeline makes secret redaction reliable |
| Linting / types | Ruff, mypy strict | Ruff replaces flake8 + isort + black in one fast pass; mypy strict surfaces async/typing bugs early |
| Tests | pytest-asyncio, 250+ tests | pytest-asyncio is required for testing async FastAPI routes and SQLAlchemy sessions |
| CI | GitHub Actions (pytest, ruff, mypy, pip-audit) | Native GitHub integration; pip-audit in CI catches vulnerable dependencies before merge |

---

## Running locally

```bash
# Start the full stack
cd deploy
docker compose up -d

# Run migrations
blueprinted migrate

# Health check
blueprinted healthcheck
```

See [docs/setup/](docs/setup/) for Authentik first-run configuration and full environment variable reference.

---

## Project structure

```
api/          FastAPI application — routes, models, schemas, services
workers/      ARQ worker entrypoint — background jobs
migrations/   Alembic migrations
prompts/      Versioned LLM prompt files (ingestion pipeline)
cli/          blueprinted CLI (migrate, healthcheck)
deploy/       Docker Compose stack and Dockerfile
tests/        pytest suite
docs/         Requirements spec, architecture notes, operational docs
```

---

## Status

Sprint 8 is in progress — core frontend read screens in the companion `blueprinted-io/app` repository. The backend API is feature-complete through Sprint 7.
