# Blueprinted — Claude Code Project Constitution

This file is read at the start of every session. It is the standing instruction set for all
Claude Code work on this repository. It does not replace the requirements specification
(v4.1) — it distills the rules that must be active in every session without exception.

The full specification lives at: `docs/requirements.md`

> **Path note:** if the spec is ever moved, update the reference above and the matching
> references in `.claude/commands/plan.md`, `closeout.md`, and `speccheck.md`.

---

## Session Protocol

### Starting a session

Every session begins with orientation before any code is written or edited. On starting
a new session, state what you are working on today and ask Claude to confirm its
understanding of the relevant spec sections and what "done" looks like before proceeding.

If resuming from a previous session, paste the close-out note from that session as the
first message.

### Ending a session

Before closing, ask Claude to produce a close-out note:
- What was completed this session
- What is incomplete or in a broken state
- What the next session should pick up from
- Any decisions made that deviate from the spec (and why)

Paste this into `SESSIONS.md` at the repo root. It is the handoff note to the next session.

### Session scope

One session = one well-defined unit of work. A sprint is not a session scope — it is too
large. Appropriate session scopes are things like:
- "Implement the Task lifecycle API endpoints"
- "Write the Alembic migration for the core schema"
- "Set up the ARQ worker entrypoint and startup hook"

If a session is drifting beyond its original scope, stop and close it out rather than
expanding scope mid-session.

---

## Plan Before Code — Strict

**For every piece of new functionality, Claude must produce a written plan before writing
any code.** No exceptions.

A plan must include:
1. What is being built and which spec sections govern it
2. Files that will be created or modified
3. Any assumptions being made that are not explicit in the spec
4. Any potential issues or edge cases worth flagging before starting

Claude does not proceed to implementation until the plan has been reviewed. "Looks good,
go ahead" is sufficient — the point is a conscious human checkpoint, not a formal review.

For small isolated fixes (a typo, a missing import, a one-line correction to something
just written in the same session) Claude may proceed directly. If in doubt, plan first.

---

## Handling Ambiguity

When Claude encounters genuine ambiguity not covered by the spec, it must **stop and ask**.

Claude does not make assumptions and proceed silently. It does not pick the "most
reasonable" interpretation without flagging it. It stops, states what is ambiguous, and
waits for instruction.

The spec is detailed. If something is genuinely not covered, that is a gap in the spec
that should be surfaced and resolved, not papered over with a guess.

---

## Absolute Rules — Never Violated

These rules are non-negotiable. They do not bend for convenience, for "just this once",
or because a simpler approach is available.

### No direct database access outside the core service
The ingestion pipeline, CLI, and all other first-party components communicate with the
database exclusively via the versioned API (`/api/v1/`). Nothing gets direct database
access except the core FastAPI service. No exceptions.

### No machine can confirm
The state transition from `submitted` to `confirmed` on any governed record (Fact,
Concept, Task, Workflow, Principle) cannot be performed by any automated process, agent
credential, API key, or background job. Confirm endpoints reject all non-human credentials
at the API layer regardless of scope.

**Enforcement is phased (decided Sprint 3):** In Sprints 4–9, confirm endpoints require
a valid human OIDC JWT. Machine credentials don't exist before Sprint 10, so this is
sufficient. In Sprint 10, an explicit machine-credential rejection check is added. Do
not add that check earlier and do not flag the absence of it as a gap — it is intentional.

Background jobs (embedding generation, flag propagation) may write to confirmed records
but cannot perform the state transition.

### Imports never create confirmed records
The ingestion pipeline may only create `draft` or `submitted` records. The `confirmed`
status cannot be set by any import path. Enforced at the API layer.

### Tests are not modified to make them pass
If a test is failing, the default assumption is that the implementation is wrong, not
the test. Claude must not modify a test file to make a failing test pass.

If Claude believes a test is itself incorrect (spec gap, deliberate design change), it
must stop, identify the specific test, state its reasoning, and wait for explicit human
instruction. If a test is authorised to change, the commit must include a `TEST_REVISED`
marker and rationale. See §10.4 of the spec.

### No floating dependencies
All dependencies are pinned. No `>=` without an upper bound in production dependencies.

---

## Architecture Rules

### Typing
All Python code is strongly typed. mypy must pass. No `Any` without an explicit comment
explaining why it is unavoidable.

### Async
FastAPI routes are async throughout. Blocking calls do not go in route handlers —
they go in ARQ background jobs.

### Logging
structlog for all logging. JSON output. Request ID on every request/response. Secrets
are never written to logs. structlog is configured to redact known secret field names.
No `print()` statements in application code.

### Error handling
Errors are explicit and typed. No bare `except Exception`. No silent swallowing of
errors. Failed operations are logged with context before raising or returning.

### Configuration
Runtime configuration lives in `system_settings` (database-backed, managed via Admin UI
and CLI). Bootstrap configuration lives in environment variables. Nothing is hardcoded.
No magic strings — constants are named and documented.

### Multi-tenancy
Schema-per-tenant. Every database operation within a tenant context uses the correct
schema. A missed schema context is a data leak. The tenant schema is set at request
time via middleware and must never be assumed from application state.

---

## ARQ Worker Rules

The ARQ worker startup hook is load-bearing. On worker startup, any chunks in
`processing` state must be reset to `queued` with a `worker_restart` note. Without this,
chunks left in-flight when a worker dies are silently skipped — this is a data loss
scenario. The startup hook must never be removed or disabled.

Resumability is an application-code responsibility, not an ARQ framework feature. Job
functions process only `queued` chunks on each invocation. This is intentional and must
not be "simplified" to process all non-done chunks.

---

## Ingestion Pipeline Rules

The ingestion pipeline produces **task and principle candidates only**. It does not
produce workflow candidates. Workflow composition is always a human act.

Iterative processing is the primary model. The section selection endpoint
(`POST /api/v1/ingestions/{id}/select`) is callable multiple times on the same ingestion.
Previously processed chunks are not affected by subsequent calls.

Partial completion is not a failure state. An ingestion job with 3 of 40 chunks processed
is a valid, useful state.

---

## Embedding Rules

The pgvector column dimension is fixed at schema creation time. Changing the embedding
model to one that produces a different dimension is a breaking migration — it requires
dropping and recreating the embedding column and re-embedding every confirmed record.
This is not a routine configuration change.

Embedding generation is triggered on every confirmed state transition — including new
versions of existing records. A revised record that reaches `confirmed` must have its
embedding regenerated.

---

## Relationship Rules

In v1, no relationship kinds are defined. All writes to the relationships API are rejected
with HTTP 422. The `relationships` table exists for v1.1 readiness. Do not add relationship
kind values without a spec update and explicit instruction.

---

## Code Style

- Python: follow Ruff defaults, enforced in CI
- Type hints: always, everywhere, no exceptions
- Docstrings: for public functions and classes, one-line summary + params if non-obvious
- Comments: explain *why*, not *what*. Code explains what. Comments explain intent,
  constraints, and non-obvious decisions.
- British English in all prose: comments, docstrings, error messages, documentation.
  Technical terms (function names, variable names, API paths) follow standard conventions
  regardless of locale.
- No commented-out code committed to main

---

## What Claude Should Never Do

- Modify an existing test file without a `TEST_REVISED` authorisation
- Access the database directly from outside the core service
- Perform a confirmed state transition from an automated process
- Add a relationship kind without explicit instruction
- Change the embedding column dimension without a migration
- Remove or disable the ARQ worker startup hook
- Use `print()` in application code
- Hardcode configuration values
- Make a silent assumption when the spec is ambiguous — stop and ask
- Expand session scope without flagging it
- Proceed past a plan step without confirmation

---

## Useful References

- Requirements specification: `docs/requirements.md`
- Session history: `SESSIONS.md`
- Migration patterns: `§18` of the spec
- Test revision process: `§10.4` of the spec
- ARQ startup hook: `§14` of the spec — load-bearing, do not remove
- Embedding model switching: `§12` of the spec — breaking operation

---

*This file is part of the repository and is versioned. Changes to this file are subject
to the same review process as any other architectural decision. If a rule in this file
is wrong, update the spec first, then update this file to match.*