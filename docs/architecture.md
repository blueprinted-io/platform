# Architecture — blueprinted.io

This file covers two things: code architecture conventions, and working-practice rules that govern
how sessions are run. Both are in here because they share the same authority — violations of either
produce the same class of problem: work that diverges silently from intent.

---

## Plan Before Code

For every piece of new functionality, produce a written plan before writing any code. No exceptions.

A plan must include:
1. What is being built and which spec sections govern it
2. Files that will be created or modified
3. Any assumptions being made that are not explicit in the spec
4. Any potential issues or edge cases worth flagging before starting

Do not proceed to implementation until the plan has been reviewed. "Looks good, go ahead" is
sufficient — the point is a conscious human checkpoint, not a formal review.

For small isolated fixes (a typo, a missing import, a one-line correction to something just written
in the same session) proceed directly. If in doubt, plan first.

---

## Handling Ambiguity

When genuine ambiguity is encountered that is not covered by the spec, **stop and ask**.

Do not make assumptions and proceed silently. Do not pick the "most reasonable" interpretation
without flagging it. Stop, state what is ambiguous, and wait for instruction.

The spec is detailed. If something is genuinely not covered, that is a gap in the spec that should
be surfaced and resolved, not papered over with a guess.

---

## Session Scope

One session = one well-defined unit of work. A sprint is not a session scope — it is too large.
Appropriate session scopes include:
- "Implement the Task lifecycle API endpoints"
- "Write the Alembic migration for the core schema"
- "Set up the ARQ worker entrypoint and startup hook"

If a session is drifting beyond its original scope, stop and close it out rather than expanding
scope mid-session.

---

## Typing

All Python code is strongly typed. mypy must pass. No `Any` without an explicit comment explaining
why it is unavoidable.

---

## Async

FastAPI routes are async throughout. Blocking calls do not go in route handlers — they go in ARQ
background jobs.

---

## Logging

structlog for all logging. JSON output. Request ID on every request/response. Secrets are never
written to logs. structlog is configured to redact known secret field names. No `print()` statements
in application code.

---

## Error Handling

Errors are explicit and typed. No bare `except Exception`. No silent swallowing of errors. Failed
operations are logged with context before raising or returning.

---

## Configuration

Runtime configuration lives in `system_settings` (database-backed, managed via Admin UI and CLI).
Bootstrap configuration lives in environment variables. Nothing is hardcoded. No magic strings —
constants are named and documented.

---

## Multi-tenancy

Schema-per-tenant. Every database operation within a tenant context uses the correct schema. A
missed schema context is a data leak. The tenant schema is set at request time via middleware and
must never be assumed from application state.
