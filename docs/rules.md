# Rules — blueprinted.io

## Absolute Rules

These rules are non-negotiable. They do not bend for convenience, for "just this once", or because a simpler approach is available.

1. **No direct database access outside the core service.** The ingestion pipeline, CLI, and all other first-party components communicate with the database exclusively via the versioned API (`/api/v1/`). Nothing gets direct database access except the core FastAPI service. No exceptions.

2. **No machine can confirm.** The state transition from `submitted` to `confirmed` on any governed record (Task, Workflow, Principle) cannot be performed by any automated process, agent credential, API key, or background job. Confirm endpoints reject all non-human credentials at the API layer regardless of scope.

   **Enforcement is phased (decided Sprint 3):** In Sprints 4–9, confirm endpoints require a valid human OIDC JWT. Machine credentials don't exist before Sprint 10, so this is sufficient. In Sprint 10, an explicit machine-credential rejection check is added. Do not add that check earlier and do not flag the absence of it as a gap — it is intentional.

   Background jobs (embedding generation, flag propagation) may write to confirmed records but cannot perform the state transition.

3. **Imports never create confirmed records.** The ingestion pipeline may only create `draft` or `submitted` records. The `confirmed` status cannot be set by any import path. Enforced at the API layer.

4. **Tests are not modified to make them pass.** If a test is failing, the default assumption is that the implementation is wrong, not the test. Do not modify a test file to make a failing test pass.

   If a test is itself incorrect (spec gap, deliberate design change), stop, identify the specific test, state the reasoning, and wait for explicit human instruction. If a test is authorised to change, the commit must include a `TEST_REVISED` marker and rationale. See §10.4 of the spec.

5. **No floating dependencies.** All dependencies are pinned. No `>=` without an upper bound in production dependencies.

---

## ARQ Worker Rules

The ARQ worker startup hook is load-bearing. On worker startup, any chunks in `processing` state must be reset to `queued` with a `worker_restart` note. Without this, chunks left in-flight when a worker dies are silently skipped — this is a data loss scenario. The startup hook must never be removed or disabled.

Resumability is an application-code responsibility, not an ARQ framework feature. Job functions process only `queued` chunks on each invocation. This is intentional and must not be "simplified" to process all non-done chunks.

---

## Ingestion Pipeline Rules

The ingestion pipeline produces **task and principle candidates only**. It does not produce workflow candidates. Workflow composition is always a human act.

Iterative processing is the primary model. The section selection endpoint (`POST /api/v1/ingestions/{id}/select`) is callable multiple times on the same ingestion. Previously processed chunks are not affected by subsequent calls.

Partial completion is not a failure state. An ingestion job with 3 of 40 chunks processed is a valid, useful state.

---

## Embedding Rules

The pgvector column dimension is fixed at schema creation time. Changing the embedding model to one that produces a different dimension is a breaking migration — it requires dropping and recreating the embedding column and re-embedding every confirmed record. This is not a routine configuration change.

Embedding generation is triggered on every confirmed state transition — including new versions of existing records. A revised record that reaches `confirmed` must have its embedding regenerated.

---

## Relationship Rules

In v1, no relationship kinds are defined. All writes to the relationships API are rejected with HTTP 422. The `relationships` table exists for v1.1 readiness. Do not add relationship kind values without a spec update and explicit instruction.

---

## References

- Requirements specification: `docs/requirements.md`
- Session history: `SESSIONS.md`
- Migration patterns: §18 of the spec
- Test revision process: §10.4 of the spec
- ARQ startup hook: §14 of the spec — load-bearing, do not remove
- Embedding model switching: §12 of the spec — breaking operation
