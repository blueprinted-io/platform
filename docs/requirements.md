# blueprinted.io

## Platform Rebuild — Requirements Specification

**Version 4.1 · May 2026**

*Confidential. Internal Use Only*

github.com/blueprinted-io/core

v4.1 changes from v4.0: Relationship kinds deferred to v1.1 (§9.4). Tests-immutable rule clarified with TEST_REVISED process (§10.4). Authentik scoped to human auth only in Sprint 2; machine auth moved to Sprint 10 (§5, §5.3, §26). Sprint plan reframed with effort hours and confidence ratings (§26). Iterative ingestion established as primary model (§11, §11.5, §11.7). Embedding dimension behaviour clarified (§12). ARQ resumability corrected — application code responsibility, not framework (§14). Agent role relationship_suggester moved to v1.1 (§5.2). Relationship screen write UI deferred to v1.1 (§23.9). Key decisions log updated throughout (§25).

---

# 1. Purpose and Scope

This document captures the complete requirements for a ground-up rebuild of the Blueprinted platform. It supersedes the existing MVP codebase and represents the authoritative specification from which the rebuild will be planned, implemented, and validated.

The existing MVP (lcs_mvp) is retained as a reference implementation only. No data migration is required. This is a clean-slate rebuild.

This specification has been through four structured review cycles. All decisions are deliberate and reasoned. Where features are deferred or stubbed, that deferral is explicit and documented.

---

# 2. Product Vision

Blueprinted is an AI-native knowledge governance platform. Its core proposition is that knowledge and skills are not documents or presentations — they are structured, governed, API-expressed records.

> *"Your agents consume the same knowledge and skills data that your humans do."*

The API is the product. The UI is one consumer. AI agents are another. Both are equal first-class consumers. There is no privileged access path.

The API surface is the primary contract. The UI is one consumer and uses the same authentication and authorisation as any other consumer. Some endpoints are deliberately shaped for UI use cases (dashboard, search results); they remain governed by the same versioning and access rules.

## 2.1 Target Audiences

- L&D and training professionals who need governed, auditable knowledge bases
- Technically-minded practitioners, DevOps engineers, developers, applied ML practitioners
- Operational teams in non-obvious verticals: film/TV equipment rental, cybersecurity operations, enterprise IT

---

# 3. Deployment Model

**Primary target:** Self-hosted, operator-managed instances

**Multi-tenancy:** Multi-tenant capable from day one, SaaS optionality preserved

Self-hosted is the primary deployment target. The architecture supports multiple tenants so a hosted SaaS option is viable in future without architectural rework. The delta between self-hosted and SaaS is infrastructure and billing, not application architecture.

The schema-per-tenant model is a deliberate forward bet on SaaS optionality. For single-tenant self-hosted installs — the majority of v1 deployments — it adds complexity that buys nothing immediately. That complexity is accepted because retrofitting multi-tenancy later is significantly harder than building it in. The `blueprinted migrate` CLI must handle the multi-schema iteration cleanly before a second tenant is ever added.

## 3.1 Docker Compose Stack

| Service | Purpose |
| --- | --- |
| api | FastAPI application, core platform |
| worker | ARQ async job worker, same codebase, different entrypoint |
| db | PostgreSQL 16 with pgvector extension |
| redis | ARQ job broker and rate limit backend |
| auth | Authentik, OIDC identity provider |
| storage | MinIO, S3-compatible object storage (optional, see §4.4) |

Fresh clone to running instance target: under ten minutes including Authentik initial setup.

---

# 4. Technology Stack

## 4.1 Backend

| Component | Decision |
| --- | --- |
| Language | Python, well-architected, strongly typed throughout |
| Framework | FastAPI, async, Pydantic v2, dependency injection |
| Type checking | mypy, enforced in CI |
| Linting | Ruff |
| Dependency management | uv |
| Testing | pytest, tests written before implementation, TEST_REVISED process for legitimate changes |
| Structured logging | structlog, JSON output from day one |
| CLI | Typer, all operational tasks scriptable |
| Background jobs | ARQ + Redis, durable, resumable via application-layer checkpointing |
| Rate limiting | slowapi + Redis backend |
| Security headers | secure.py middleware |

*Note: Python was chosen over Go despite Go's single-binary deployment advantage. Go remains a named future option; the architecture does not preclude it.*

## 4.2 Frontend

| Component | Decision |
| --- | --- |
| Framework | React with TypeScript |
| Build tool | Vite |
| Styling | Tailwind CSS |
| Component primitives | shadcn/ui, unstyled, accessible, owned in codebase |
| Design tokens | #111827 near-black · #ffffff white · #f59e0b amber · Inter typeface |

The frontend is a hard-separated API consumer. No direct database access. No shared internal models with the backend. Consumes the versioned API exclusively.

## 4.3 Database

| Component | Decision |
| --- | --- |
| Primary store | PostgreSQL 16 |
| Tenancy model | Schema-per-tenant, hard isolation at database layer |
| Vector search | pgvector extension, semantic search and fact deduplication |
| Full text search | PostgreSQL tsvector, structured field filtering |
| Migrations | Alembic, runs per-tenant schema on upgrade |
| ORM | SQLAlchemy with shared lifecycle mixin |
| Future | Neo4j, named migration target if graph complexity warrants it |

## 4.4 File Storage

**Default:** Local disk, mounted Docker volume

**Option:** S3-compatible object storage — AWS S3, Cloudflare R2, MinIO, Backblaze B2

**Abstraction:** fsspec, application code is storage-backend agnostic

**Configuration:** Configured via system_settings: storage_backend, storage_bucket, storage_endpoint, storage_key

New installs default to local disk via a mounted Docker volume. Operators who need S3-compatible storage configure the relevant system_settings keys and the application switches backends transparently.

MinIO is included as an optional service in Docker Compose for operators who want S3-compatible storage without an external cloud dependency. It is not enabled by default.

| Storage location | Path pattern |
| --- | --- |
| PDF uploads | uploads/ingestions/{ingestion_id}/{filename} |
| Step screenshots | uploads/screenshots/{task_record_id}/{step_id}/{filename} |
| Export artifacts | exports/{export_id}/{filename} |
| Operator logos | logos/{tenant_slug}/{filename} |

All upload endpoints enforce: maximum file size (configurable via system_settings), MIME type validation, filename sanitisation. Files are never served directly, always via controlled download endpoints.

---

# 5. Authentication and Authorisation

**Provider:** Authentik, self-hostable, OIDC/SAML, bundled in Docker Compose

**Protocol:** OIDC throughout, no hand-rolled auth under any circumstances

**Human auth:** OIDC flows via Authentik, browser redirects, PKCE flow in React frontend

**Machine auth:** OIDC client credentials flow and scoped API keys — Sprint 10, see §5.3

Authentik is operationally non-trivial. Sprint 2 delivers human OIDC only: Docker Compose configuration, Authentik up and running, FastAPI token validation, and a working PKCE flow in the React frontend. This is the hard dependency for all subsequent development — contributors can log in, sessions work, role-based access is enforced.

Machine credentials and scoped API keys are deliberately deferred to Sprint 10. They are needed for agent access and third-party integrations, but those use cases do not exist until the core platform exists. Attempting to specify and implement machine auth before the API surface is stable adds complexity with no immediate return.

The Authentik configuration guide — covering Docker Compose setup, realm configuration, OIDC client registration, and the PKCE flow — is a first-class operator documentation deliverable from Sprint 2.

## 5.1 Human Roles

| Role | Capabilities |
| --- | --- |
| Admin | Full access, break-glass operations, all domains implicit, system settings |
| Contributor | Create, submit, review/confirm in assigned domains. Cannot review own content. |
| Content Publisher | Export confirmed workflows. Sees all confirmed content. |
| Viewer | Read-only across all confirmed content and domains. |
| Audit | Read-only with audit log access. |

Self-review prohibition: a Contributor cannot confirm or return content they created. Enforced at the API layer, not the UI layer.

**Small team note:** Self-hosted installs frequently operate with two or three contributors. The self-review prohibition can create review queue starvation in very small teams. Admin break-glass confirm (with mandatory justification, audit log entry, and visible UI scar on the confirmed record) is the relief valve for this scenario. This is not a normal flow and should feel like a controlled breach.

## 5.2 Agent Roles

Agent roles are available from Sprint 10, when machine auth is implemented.

| Role | Capabilities | Available |
| --- | --- | --- |
| agent:workflow_consumer | Read confirmed Workflows via API. Read only. | Sprint 10 |
| agent:staleness_monitor | Flag confirmed records for human attention. No write access. | Sprint 10 |
| agent:orphan_detector | Identify unlinked Tasks and Principles. No write access. | Sprint 10 |
| agent:relationship_suggester | Propose relationship edges only. Cannot confirm anything. | v1.1 (no relationship kinds defined in v1) |

**Absolute constraint (enforced from Sprint 4, before machine auth exists):** no machine credential can ever call a confirm endpoint. This constraint is a property of the confirm endpoints themselves — it does not depend on machine auth existing to be enforced. Human confirmation of governed knowledge is non-negotiable.

## 5.3 Machine Auth — Sprint 10

Machine auth is implemented in Sprint 10 alongside the CLI and admin tooling it supports.

| Method | Description |
| --- | --- |
| OIDC client credentials | For long-running agent processes. Client ID and secret registered in Authentik. |
| Scoped API keys | For short-lived integrations and operator scripts. Managed via Admin UI and CLI. |

The no-machine-can-confirm constraint is implemented in Sprint 4 as a property of the confirm endpoints. It does not wait for Sprint 10.

---

# 6. API Design

**Versioning:** URL-based, /api/v1/ prefix

**Breaking changes:** New version prefix required (/api/v2/). Never a patch to an existing version.

**Consumers:** Human UI, AI agents, third-party integrations — all equal, no privileged path

**Documentation:** OpenAPI generated from FastAPI route definitions, source of truth, not separately maintained

The API version contract is the formal boundary between core and all consumers including the future delivery product. This principle is documented in contributor docs from day one.

---

# 7. Domains

Domains are admin-managed organisational subdivisions of knowledge within a tenant. They are not security boundaries between organisations — tenants provide that isolation.

- Contributors can only create, submit, and review content in their assigned domains
- Admin is implicitly entitled to all domains
- Viewer, Audit, and Content Publisher see all confirmed content across all domains without assignment
- Facts and Concepts are domain-agnostic; domain scoping applies to Tasks, Workflows, and Principles only

---

# 8. Review Queue and Claiming

## 8.1 Global Review Queue

A filtered view, no dedicated table. Shows all submitted records in the reviewer's entitled domains that are not their own content. Not assigned — any qualified reviewer can act on any item.

## 8.2 Claiming Model

- **Unclaimed:** visible and actionable by all qualified reviewers in the domain
- **Claimed:** one reviewer holds it. Others see it as claimed with expiry time visible.
- **Claim abandoned:** reviewer explicitly releases, returns to unclaimed
- **Claim expired:** auto-released by ARQ worker after configurable window (default 48 hours)
- **Confirmed or Returned:** claim resolves, item leaves queue

```
review_claims
  id              UUID PRIMARY KEY
  entity_type     TEXT         -- 'task' | 'workflow' | 'principle'
  entity_id       UUID         -- FK to the specific version id
  claimed_by      UUID FK → users.id
  claimed_at      TIMESTAMPTZ
  expires_at      TIMESTAMPTZ
  released_at     TIMESTAMPTZ  -- NULL = active claim
```

## 8.3 Ingestion Review Queue

Separate from the global review queue. Candidate records staged in ingestion_candidates after job completion. A contributor reviews, accepting, editing, or discarding each. Accepted candidates commit as draft records and enter the governance pipeline.

---

# 9. Data Model

## 9.1 Shared Identity Pattern

```
id          UUID  PRIMARY KEY  -- key for this specific version
record_id   UUID  NOT NULL     -- stable identity across all versions
version     INT   NOT NULL     -- incrementing per record_id
```

## 9.2 Shared Lifecycle Fields

```
status               TEXT         -- draft | submitted | confirmed | deprecated | returned | retired
created_at           TIMESTAMPTZ
updated_at           TIMESTAMPTZ
created_by           UUID FK → users.id
updated_by           UUID FK → users.id
reviewed_at          TIMESTAMPTZ  -- drives staleness calculation
reviewed_by          UUID FK → users.id
change_note          TEXT
needs_review_flag    BOOL NOT NULL DEFAULT FALSE
needs_review_note    TEXT
```

## 9.3 Lifecycle State Machine

```
draft → submitted → confirmed → deprecated
            ↓               ↑
         returned ──────────┘  (revised and resubmitted)

confirmed → retired  (admin only, permanent)
```

## 9.4 Relationship Kind Taxonomy

The relationship kind is a closed enum at the API layer. Unknown values are rejected with HTTP 422. Extension requires a GitHub issue, maintainer approval, a migration adding the new value, and documentation update. The bar for adding a new kind is high: a candidate kind must not duplicate an existing mechanism in the data model, and its semantics and enforcement point must be fully specified before the migration is written.

```python
class RelationshipKind(str, Enum):
    pass  # No kinds defined in v1. See below.
```

**v1 ships with no relationship kinds.** The `relationships` table and API endpoints exist as infrastructure. All writes to the relationships API are rejected with HTTP 422 until a kind is added via the extension process. This is intentional — relationship semantics are harder to specify correctly than they appear, and the wrong taxonomy is worse than no taxonomy.

The four candidate kinds considered and deferred:

- `conflicts_with` — semantically ambiguous. "Cannot both be active" requires a definition of active (both confirmed? both in the same workflow?) and an enforcement point, neither of which is obvious.
- `supersedes` — redundant with the `record_id`/`version` identity pattern. A new confirmed version of a record supersedes its predecessor by definition.
- `references` — redundant with `task_fact_refs` and `task_concept_refs` for the primary use case.
- `depends_on` — conflicts with the no-workflow-prerequisites rule and creates a third location for precondition logic alongside Task Dependencies and Workflow composition.

Relationship kind specification is a v1.1 workstream, informed by real usage patterns from the authoring UI and ingestion pipeline.

## 9.5 Record Taxonomy

### Facts

Atomic, declarative, verifiable statements of truth. Domain-agnostic. Immutable once confirmed — changes require deprecation and replacement. Embedding populated asynchronously on confirmation.

```
facts
  + shared identity and lifecycle fields
  title            TEXT NOT NULL
  body             TEXT NOT NULL
  tags             TEXT[]
  embedding        vector(1536)  -- dimension fixed at schema creation; see §12
```

### Concepts

Explanatory, contextual knowledge — the why behind procedures. Domain-agnostic. Immutable once confirmed.

```
concepts
  + shared identity and lifecycle fields
  title            TEXT NOT NULL
  summary          TEXT NOT NULL
  explanation      TEXT NOT NULL
  analogies        TEXT
  tags             TEXT[]
  embedding        vector(1536)
```

### Principles

Foundational document-grain knowledge attached to Workflows. Reusable across multiple Workflows. Full governed lifecycle. Formerly called Primers, renamed throughout.

```
principles
  + shared identity and lifecycle fields
  title            TEXT NOT NULL
  summary          TEXT NOT NULL
  explanation      TEXT NOT NULL
  analogies        TEXT
  domain           TEXT
  tags             TEXT[]
  ingestion_id     UUID FK → ingestions.id
  embedding        vector(1536)
```

### Tasks

The governed procedure unit. References Facts and Concepts rather than owning them. Steps are owned by the Task. Task-level irreversibility is derived — a Task is irreversible if any Step has irreversible = TRUE.

```
tasks
  + shared identity and lifecycle fields
  title                       TEXT NOT NULL
  outcome                     TEXT NOT NULL
  procedure_name              TEXT NOT NULL
  domain                      TEXT
  software_name               TEXT
  software_version            TEXT
  media_url                   TEXT
  ingestion_id                UUID FK → ingestions.id
  has_deprecated_fact_ref     BOOL NOT NULL DEFAULT FALSE
  has_deprecated_concept_ref  BOOL NOT NULL DEFAULT FALSE
  tags                        TEXT[]
  embedding                   vector(1536)

task_fact_refs
  task_id            UUID FK → tasks.id
  fact_record_id     UUID FK → facts.record_id  -- resolves to latest confirmed
  order_index        INT NOT NULL

task_concept_refs
  task_id            UUID FK → tasks.id
  concept_record_id  UUID FK → concepts.record_id  -- resolves to latest confirmed
  order_index        INT NOT NULL

task_steps
  id               UUID PRIMARY KEY
  task_id          UUID FK → tasks.id
  order_index      INT NOT NULL
  step             TEXT NOT NULL   -- step label/title
  notes            TEXT            -- alternatives, caveats, references
  completion       TEXT NOT NULL   -- 'you know this step is done when...'
  irreversible     BOOL NOT NULL DEFAULT FALSE

task_step_actions
  id           UUID PRIMARY KEY
  step_id      UUID FK → task_steps.id
  order_index  INT NOT NULL
  instruction  TEXT NOT NULL

task_step_screenshots
  id           UUID PRIMARY KEY
  step_id      UUID FK → task_steps.id
  order_index  INT NOT NULL
  storage_path TEXT NOT NULL  -- resolved via storage backend abstraction
```

### Workflows

An ordered sequence of Tasks with attached Principles. The consumable product. References latest confirmed Task versions.

```
workflows
  + shared identity and lifecycle fields
  title                       TEXT NOT NULL
  objective                   TEXT NOT NULL
  domain                      TEXT
  tags                        TEXT[]
  ingestion_id                UUID FK → ingestions.id
  has_incoming_task_change    BOOL NOT NULL DEFAULT FALSE
  has_pending_task_confirm    BOOL NOT NULL DEFAULT FALSE
  embedding                   vector(1536)

workflow_task_refs
  workflow_id        UUID FK → workflows.id
  task_record_id     UUID FK → tasks.record_id  -- resolves to latest confirmed
  order_index        INT NOT NULL

workflow_principle_refs
  workflow_id          UUID FK → workflows.id
  principle_record_id  UUID FK → principles.record_id  -- resolves to latest confirmed
  attached_at          TIMESTAMPTZ
  attached_by          UUID FK → users.id
```

### Relationships

```
relationships
  id              UUID PRIMARY KEY
  source_id       UUID NOT NULL
  source_type     TEXT NOT NULL  -- 'fact'|'concept'|'task'|'workflow'|'principle'
  target_id       UUID NOT NULL
  target_type     TEXT NOT NULL
  kind            TEXT NOT NULL  -- RelationshipKind enum (closed, no kinds in v1)
  created_at      TIMESTAMPTZ NOT NULL
  created_by      UUID NOT NULL  -- user or agent credential
  agent_suggested BOOL NOT NULL DEFAULT FALSE
  note            TEXT
```

All writes rejected with HTTP 422 in v1. Table exists for v1.1 readiness.

### Assessments — Removed from v1

Assessments are not included in v1. No table, no API endpoints, no UI, no system_settings toggle. Reintroduced as a properly specced feature in a future version after assessment theory review.

## 9.6 Platform Tables

```
users, sessions, user_domains, domains
achievements, user_achievements   -- stub: tables exist, no specified behaviour in v1
system_settings
audit_log
notifications
review_claims
```

## 9.7 Ingestion Pipeline Tables

```
ingestions
ingestion_chunks
ingestion_candidates   -- structured typed staging, replaces raw LLM blob review
ingestion_nav_pages
```

## 9.8 Export and Delivery Tables — v1 Stubs

These tables exist in the migration schema but have no API endpoints, no UI, and no behaviour in v1.

```
export_artifacts       -- stub
presentation_tokens    -- stub
changelog_runs         -- stub
changelog_impacts      -- stub
```

---

# 10. Key Design Principles

## 10.1 Facts and Concepts are Immutable Once Confirmed

A confirmed Fact or Concept cannot be edited. Deprecate and replace. Tasks referencing deprecated records are flagged automatically via has_deprecated_fact_ref and has_deprecated_concept_ref.

## 10.2 No Machine Can Confirm

"Confirm" means the state transition from `submitted` to `confirmed` on a governed record (Fact, Concept, Task, Workflow, Principle). No agent credential, API key, or automated process can call a confirm endpoint. Enforced at the API layer regardless of credential scopes.

Automated workers may write to confirmed records via background jobs (embedding generation, flag propagation) but cannot perform the state transition. This distinction is important: the ARQ embedding worker writes an embedding vector to a confirmed record — it does not confirm anything.

## 10.3 Every First-Party Component is an API Consumer

UI, ingestion pipeline, CLI, future modules — all consume the versioned API. Nothing gets direct database access except the core service itself.

## 10.4 Tests are Written Before Implementation

Tests are written before implementation. A failing test is a blocker requiring human investigation before any code change is made. The default assumption is always that the implementation is wrong, not the test.

**AI is prohibited from modifying existing test files to make a failing test pass.** If an AI coding assistant determines that a test is itself incorrect — because the spec was incomplete at the time of writing, or because a deliberate design decision has changed the expected behaviour — it must stop, flag the specific test and its reasoning, and wait for explicit human instruction before any modification is made.

When a test is legitimately revised, the commit must include:

- A `TEST_REVISED` marker in the commit message
- The reason the test was wrong (spec gap, deliberate design change, or authoring error)
- The human decision that authorised the change

A `TEST_REVISED` commit is not a failure state. It is the correct process when a test needs to change. What it prevents is silent revision — the quiet weakening of a contract to fit an implementation that should have been fixed instead.

**The failure mode this rule exists to prevent:** an AI assistant changes `assert response.status_code == 403` to `assert response.status_code == 200` because the implementation returns 200, and the build passes, and nobody notices the access control is gone.

Sprint 3 test design precedes all feature implementation but cannot anticipate every edge case. `TEST_REVISED` commits are expected and normal. Their frequency is a signal worth tracking — a cluster of `TEST_REVISED` commits against a single sprint's tests indicates the spec for that area was underspecified and should be reviewed before implementation proceeds further.

## 10.5 Everything Configurable is Configurable via UI

Runtime configuration lives in system_settings, managed via Admin UI and CLI. Bootstrap configuration lives in environment variables. Nothing is hardcoded.

## 10.6 Imports Never Create Confirmed Records

The ingestion pipeline can only create draft or submitted records. The confirmed state cannot be set by import. Enforced at the API layer.

## 10.7 Staleness is Tracked Not Assumed

Confirmed records have reviewed_at and reviewed_by. The staleness threshold is configurable. Staleness surfaces in dashboards — it does not automatically deprecate or invalidate records.

---

# 11. Ingestion Pipeline Sub-Specification

The ingestion pipeline is a hard-separated first-party API consumer living in the backend monorepo. It communicates with core exclusively via the versioned API. No shared internal models, no direct database access.

**Iterative processing is the primary model.** Single-pass processing of an entire document is not a goal and not optimised for — it is simply iterative processing with one large batch, and for any document of meaningful size it will produce an unmanageable candidate review queue.

The intended operator workflow is:

1. Upload the document
2. Review the chunk list, select a small number of sections (2-5 is typical)
3. Run triage and extraction on the selected batch
4. Review and commit candidates from that batch
5. Return to the chunk list and select the next batch
6. Repeat until the document is processed to the desired depth

An operator is never expected to process an entire document in one session. The chunk list persists. Processed chunks are marked done. The operator can stop at any point and resume later. There is no concept of an ingestion job being "incomplete" — every committed batch is a valid stopping point.

**High-volume ingestion patterns** — bulk processing of large corpora with minimal per-candidate review — are a v1.1 workstream. v1 is optimised for quality over throughput. The human reviewer is the quality gate on every candidate.

The ingestion pipeline produces **task and principle candidates only**. Workflows are not extracted. Workflow composition is always a human act — it expresses expert judgment about how tasks should be sequenced for a specific operational context. That judgment cannot be extracted from documentation by an LLM. The ingestion pipeline produces the raw material; humans compose it into workflows using the authoring UI.

## 11.1 LLM Provider Strategy

Blueprinted supports any provider that exposes an OpenAI-compatible API shape (chat completions endpoint). Anthropic native format is supported as a secondary option via a translation adapter. The provider is configured via system_settings — no provider lock-in.

| Setting | Purpose |
| --- | --- |
| llm_triage_base_url / model | Classification and triage stage |
| llm_extraction_base_url / model | Task and Principle extraction stage |
| llm_output_base_url / model | Output rendering stage |
| llm_embedding_base_url / model | Embedding generation for pgvector |
| llm_{pipeline}_api_key | Per-pipeline API key, stored encrypted, never logged |
| llm_{pipeline}_timeout_seconds | Per-pipeline timeout |

**Convenience mode:** if per-pipeline settings are empty, all stages fall back to shared llm_base_url and llm_model. This is the default for new installs. Operators should validate convenience mode end-to-end before configuring per-pipeline overrides.

API keys are stored encrypted in system_settings. Never logged. Never returned via API response. The audit log records which provider profile was used per chunk — base URL and model only, never the key.

## 11.2 LLM Provider Formats

| Format | Configuration |
| --- | --- |
| OpenAI-compatible | Default. Set llm_base_url to any OpenAI-compatible endpoint. Works with OpenAI, Groq, Together, Ollama, Synthetic.new, LM Studio, and others. |
| Anthropic native | Set llm_provider_format = 'anthropic'. Adapter translates to Anthropic Messages API. Works with claude-* models directly. |

**Important:** OpenAI-compatible covers chat completions. Structured extraction quality depends on provider tool-use or JSON-mode support, which varies significantly across providers. The Anthropic native adapter is not a simple header swap — the Messages API has structural differences around system prompts, tool use shape, and streaming events. Recommended providers for each pipeline stage are documented in operator docs.

## 11.3 Pipeline Stages

| Stage | Description |
| --- | --- |
| 1. Structural decomposition | PDF chunked by document structure — bookmarks, headings, section breaks. Falls back to character-count chunking if no structure detected. Scanned PDFs detected and rejected with explicit error. |
| 2. Section selection | Operator reviews chunk list and selects a batch of sections to process (typically 2-5). Primary navigation surface — returned to repeatedly. See §11.5. |
| 3. Triage / classification | Each selected chunk classified: task_candidate, principle_candidate, reference_material, or skip. Confidence score and reason captured per chunk. |
| 4. Extraction | Classified chunks processed by extraction LLM. Produces structured typed candidates written to ingestion_candidates. |
| 5. Human review | Contributor reviews candidates from this batch. Accept, edit, or discard each. |
| 6. Commit | Accepted candidates committed as draft or submitted records via API. ingestion_candidates.committed_record_id set. Operator returns to stage 2 for the next batch. |

## 11.4 Candidate Output Schemas

### Task Candidate

```json
{
  "type": "task",
  "title": "string, required",
  "outcome": "string, required",
  "procedure_name": "string, required",
  "domain": "string, optional",
  "software_name": "string, optional",
  "software_version": "string, optional",
  "facts": ["string array"],
  "concepts": ["string array"],
  "steps": [
    {
      "step": "string, required",
      "actions": ["string array, optional"],
      "notes": "string, optional",
      "completion": "string, required"
    }
  ]
}
```

### Principle Candidate

```json
{
  "type": "principle",
  "title": "string, required",
  "summary": "string, required",
  "explanation": "string, required",
  "analogies": "string, optional",
  "domain": "string, optional"
}
```

## 11.5 Section Selection Flow

The section selection screen is the **primary navigation surface for ingestion**. It is not a one-time setup step — the operator returns to it repeatedly throughout the processing of a document.

After PDF chunking completes, the operator is presented with the section selection screen. This screen persists for the lifetime of the ingestion job and can be returned to at any point.

**Screen shows per chunk:**
- Section title
- Page range
- Word count
- Brief text preview
- Current chunk status: pending / queued / processing / done / error / skipped

**Operator actions:**
- Select individual chunks to queue for the current batch
- Select all unprocessed / deselect all controls available
- Submit selection — selected chunks marked `chunk_status = queued`, LLM triage and extraction fires
- Return to this screen at any point to queue the next batch

**Recommended batch size:** 2-5 sections per pass. Large batches produce large candidate queues. The operator controls their own review burden.

Scanned sections are automatically excluded and flagged. They cannot be selected.

Chunks in `done`, `error`, or `skipped` status are visually distinct. Done chunks show a candidate count. Error chunks show a retry option.

```
POST /api/v1/ingestions/{id}/select
Body:     { "chunk_ids": ["uuid1", "uuid2", ...] }
Response: { "queued_count": N, "ingestion_id": "uuid" }
```

This endpoint is callable multiple times on the same ingestion. Each call queues the specified chunks. Previously processed chunks are not affected.

## 11.6 Candidate Validation Rules

- Required fields missing → candidate marked invalid, chunk marked extraction_failed
- Steps array empty on task candidate → candidate marked invalid
- Unknown fields → stripped silently, not an error
- LLM returns non-JSON → chunk marked extraction_failed, error captured
- Partial extraction: valid candidates proceed, invalid marked separately

## 11.7 Failure Behaviour

- Chunk extraction_failed → error captured in ingestion_chunks record
- Operator notified via notification system
- Chunk available for manual retry via UI; other chunks continue
- **Job durability:** ARQ persists queued jobs in Redis. Jobs that have not begun executing survive worker restarts. Jobs that were mid-execution do not — see resumability below.
- **Resumability:** Implemented in application code via chunk_status checkpoints. The job function processes only `queued` chunks on each invocation. A worker startup hook resets any `processing` chunks to `queued` to recover from mid-execution crashes. Without this hook, crashed in-flight chunks are silently skipped — this is a data loss scenario and the hook is mandatory.

**Partial completion is not a failure state.** An ingestion job where 3 of 40 chunks have been processed and committed is a valid, useful state. The operator has three chunks worth of confirmed candidates in the governance pipeline and 37 chunks available to process when they choose. There is no pressure to complete an ingestion job. Abandoning an ingestion job after partial processing is explicitly supported — the committed records remain, the ingestion record is retained for reference, and no cleanup is required.

## 11.8 ingestion_candidates Table

```
ingestion_candidates
  id                    UUID PRIMARY KEY
  ingestion_id          UUID FK → ingestions.id
  chunk_id              UUID FK → ingestion_chunks.id
  record_type           TEXT         -- 'task' | 'principle'
  proposed_json         JSONB        -- structured typed candidate
  candidate_status      TEXT         -- pending|accepted|edited|discarded|invalid
  review_note           TEXT
  committed_record_id   UUID         -- set on accept, points to created record
  reviewed_by           UUID FK → users.id
  reviewed_at           TIMESTAMPTZ
```

---

# 12. Search and Embeddings

**Structured filtering:** PostgreSQL tsvector — title, domain, tags, software name

**Semantic search:** pgvector — outcome, step content, fact body, concept body

**Embedding dimensions:** Determined by the embedding model. The default configuration targets 1536-dimensional vectors, compatible with `text-embedding-3-small` and many open-source alternatives. The pgvector column declaration locks the dimension at schema creation time.

**Embedding generation:** Async ARQ job triggered on record confirmation, and on every subsequent confirmation of a new version of the same record_id.

**Changing embedding models is a breaking operation.** A model producing a different vector dimension than the one declared in the schema cannot be used without a migration. That migration must:

1. Drop and recreate the embedding column with the new dimension
2. Trigger background re-embedding of every confirmed record via ARQ
3. Exclude records from semantic search until their embedding is regenerated

This is not a routine configuration change. Operators should choose their embedding model before the first confirmed records are created and treat it as stable infrastructure. The system_settings key `llm_embedding_model` controls which model is used; changing it without running the associated migration will produce dimension mismatches and silent semantic search failures. Recommended compatible models are documented in operator docs.

## 12.1 Embedding Lifecycle

When any governed record transitions to confirmed, an ARQ job fires to generate and store its embedding vector. When a record is revised and a new version confirmed, the embedding job fires again for the new version. Confirmation is not blocked by embedding generation — the record is confirmed immediately and embeddings follow in the background.

Graceful degradation: records without embeddings are excluded from semantic search results but remain discoverable via tsvector. No errors, reduced result set until embeddings catch up. The `semantic_available` flag in the search response signals current embedding coverage.

**UI note:** the `semantic_available: false` flag must be surfaced to users in a human-readable form — not as a raw API field. When semantic coverage is incomplete, the search UI should indicate this clearly so operators understand why newly confirmed records may not appear in semantic results immediately.

## 12.2 Search API

```
GET /api/v1/search
  ?q=string           Search query (required)
  ?type=string        Comma-separated record types: task,workflow,fact,concept,principle
  ?domain=string      Filter by domain
  ?status=string      Filter by status (default: confirmed)
  ?semantic=bool      Enable semantic search (default: false)
  ?limit=int          Results per page (default: 20, max: 100)
  ?offset=int         Pagination offset
```

Response shape:

```json
{
  "results": [
    {
      "record_id": "uuid",
      "record_type": "task",
      "version": 3,
      "title": "string",
      "status": "confirmed",
      "domain": "string",
      "match_type": "semantic|fulltext|hybrid",
      "score": 0.87,
      "excerpt": "string"
    }
  ],
  "total": 42,
  "semantic_available": true
}
```

Hybrid ranking: semantic score and tsvector rank each normalised to 0-1. Weighted combination: semantic 60%, tsvector 40% when both available. Weights configurable via system_settings (search_semantic_weight, search_fulltext_weight).

---

# 13. Notifications

**Mechanism:** In-app notification bell + optional email via SMTP

**SMTP:** Configurable via Admin UI in system_settings. Optional — notifications are in-app only if unconfigured.

**User preferences:** Deferred to v1.1. Notification kind values are stable and preference-addressable from day one.

## 13.1 Notifications Table

```
notifications
  id              UUID PRIMARY KEY
  user_id         UUID FK → users.id
  kind            TEXT  -- stable kind value (see §13.3)
  entity_type     TEXT
  entity_id       UUID
  message         TEXT
  created_at      TIMESTAMPTZ
  read_at         TIMESTAMPTZ     -- NULL = unread (in-app)
  emailed_at      TIMESTAMPTZ     -- NULL = not yet emailed
  delivered_at    TIMESTAMPTZ     -- NULL = pending delivery
  delivery_error  TEXT            -- last delivery error if failed
```

## 13.2 SMTP Failure Model

| Scenario | Behaviour |
| --- | --- |
| SMTP not configured | In-app only. delivered_at stays NULL. No error recorded. No retry. Documented expected behaviour. |
| Delivery succeeds | delivered_at set. delivery_error NULL. |
| Delivery fails | ARQ retries 3x: 5min, 15min, 45min backoff. After 3 failures: delivery_error set, no further retries, admin notified in-app. |

Admin dashboard surfaces a count of notifications with delivery_error set.

## 13.3 Notification Kinds

Kind values are stable from v1. They form a de-facto contract for v1.1 user preference configuration.

```
record_confirmed       -- a record the user authored has been confirmed
record_returned        -- a record the user authored has been returned for changes
record_submitted       -- a record in user's domain has been submitted for review
claim_made             -- a review item in user's domain has been claimed by someone else
claim_expired          -- a review claim has expired and returned to the queue
ingestion_complete     -- an ingestion job the user started has completed
ingestion_failed       -- an ingestion job the user started has failed
fact_deprecated        -- a fact referenced by user's tasks has been deprecated
concept_deprecated     -- a concept referenced by user's tasks has been deprecated
```

---

# 14. Background Job Processing

**Framework:** ARQ + Redis

**Worker:** Separate process, same codebase, different entrypoint

**Durability:** Jobs are persisted in Redis before execution. If the worker process dies before a job begins executing, the job remains in the Redis queue and will be picked up when the worker restarts. Jobs that were mid-execution when the worker died are a different case — see Resumability below.

**Resumability:** ARQ does not natively resume a partially-executed job. If the worker dies mid-execution, ARQ's default behaviour is to mark the job as failed. Resumability for ingestion jobs is a property of the application code, not the framework.

This is implemented as follows:

- Each ingestion job function begins by querying chunk_status and processing only chunks in `queued` state
- Chunks in `processing` state when the worker died represent in-flight LLM calls that were lost. A worker startup hook resets any `processing` chunks to `queued` with a `worker_restart` note in the chunk error field
- This means a worker restart may re-process a chunk whose LLM call completed but whose result was never written — acceptable, as extraction is idempotent from the operator's perspective
- Chunks in `done`, `error`, or `skipped` state are never re-processed

**The startup hook is not optional.** Without it, chunks left in `processing` state after a worker crash are silently skipped on resume, producing an ingestion job that appears complete but is missing candidates. This is a data loss scenario. Mark the startup hook clearly in code — it is load-bearing and must not be removed during refactoring.

| Job | Trigger |
| --- | --- |
| PDF chunking | Ingestion job submitted |
| LLM triage | Chunks queued after section selection |
| LLM extraction | Chunks passing triage |
| Embedding generation | Record confirmed (any version) |
| Email delivery | Notification created with SMTP configured |
| Review claim expiry | Scheduled, every 15 minutes |
| Export generation (stub) | v1 stub, no behaviour |
| Changelog impact analysis (stub) | v1 stub, no behaviour |

---

# 15. Analytics and Dashboards

**Primary user:** Non-technical — content managers, L&D professionals, team leads

**Model:** Role-aware, not user-defined

| Role | Dashboard Content |
| --- | --- |
| Contributor | My submitted records awaiting review, my drafts, recently returned records |
| Reviewer / Contributor | Review queue depth, records awaiting confirmation in my domains |
| Admin | Pipeline velocity, staleness by domain, system health, job queue status |
| Viewer / Audit | Knowledge base health, coverage by domain, recent confirmations |

## 15.1 LearningOps Metrics

- Throughput: confirmed records per 30 days
- Cycle time: average hours from submit to confirm
- Return rate: percentage of submissions returned
- Recovery time: average hours from return to confirm
- Staleness by domain: confirmed records not reviewed within threshold

---

# 16. Observability

**Logging:** structlog, JSON structured output. Request ID on every request/response.

**Health check:** /healthz, public, no auth. DB connectivity and migration state.

**In-app dashboard:** Admin-facing instance health, first-class feature

**Metrics:** Prometheus exposition, named future addition

Secrets are never written to logs. structlog configured to redact known secret field names.

---

# 17. Security

## 17.1 Rate Limiting

| Endpoint | Limit |
| --- | --- |
| POST /api/v1/auth/* | 10 requests/minute per IP |
| POST /api/v1/ingestions | 5 requests/hour per user |
| GET /api/v1/* | 100 requests/minute per credential |
| POST /api/v1/* | 30 requests/minute per credential |

## 17.2 File Upload Security

- Maximum file size enforced at API layer, configurable via system_settings
- MIME type validation — file must be what it claims to be
- Filename sanitisation, no path traversal
- Files stored via storage abstraction layer, never served directly

## 17.3 Supply Chain and Other Controls

- pip-audit in CI, CVE scanning on every push
- Dependabot enabled, automated dependency update PRs
- Pinned dependencies, no floating versions in production
- secure.py middleware, security headers on every response
- CSRF: not a concern for API-first Bearer token architecture
- Prompt injection: mitigated architecturally by human review gate
- SSRF via LLM base URL: admin-trust boundary, documented in operator docs

---

# 18. Multi-Tenant Migration Strategy

## 18.1 blueprinted migrate

- Pre-flight: verify connectivity, check current schema version per tenant
- Migrate system schema first
- Migrate tenant schemas sequentially, alphabetical order by tenant slug
- On failure: stop immediately, log which tenant failed, do not attempt remaining

```
blueprinted migrate               Run all pending migrations
blueprinted migrate --dry-run     Show what would run without executing
blueprinted migrate --tenant acme Migrate single tenant, used for recovery
blueprinted migrate --status      Show migration version per schema
```

Dry-run output example:
```
System schema: 3 pending migrations
tenant_acme:   2 pending migrations
tenant_veeam:  2 pending migrations
tenant_demo:   current
```

## 18.2 Failure Handling

- No automatic rollback in v1, forward-only migrations
- Recovery: restore from backup, then `blueprinted migrate --tenant {failed}`
- `blueprinted backup` strongly recommended before `blueprinted upgrade`
- Parallel migration is a named future optimisation, not v1

---

# 19. Repository Structure

## 19.1 blueprinted-io/core — Backend Monorepo

```
/api          FastAPI application, versioned routes, middleware, auth
/ingestion    Ingestion pipeline, hard API consumer, no direct DB access
/cli          Typer CLI, all operational tasks
/workers      ARQ background job definitions
/tests        Test suite
/docs         Operator and contributor documentation
/migrations   Alembic migration files
/seed         Documentation tenant seed data
/deploy       Docker Compose files, environment templates
```

## 19.2 blueprinted-io/app — React Frontend

Hard-separated API consumer. TypeScript, Vite, Tailwind, shadcn/ui. Own CI/CD pipeline.

## 19.3 blueprinted-io/deliver — Delivery Product (Future)

AI-native learning experience layer. Queries Blueprinted core API. Not an LMS. Name TBD. Own repository, own CI/CD pipeline, independent deployment lifecycle.

---

# 20. CI/CD

## 20.1 Backend CI — GitHub Actions

- Trigger: every push and pull request
- Services: PostgreSQL 16 + pgvector, Redis 7
- Steps: checkout → setup Python → install → migrate → pytest → Ruff → mypy → pip-audit
- Tests must pass before merge to main

## 20.2 Frontend CI — GitHub Actions

- Trigger: every push and pull request
- Steps: checkout → install → TypeScript check → build

## 20.3 Deployment

**Current:** Manual — git pull, blueprinted migrate, Docker Compose restart

**Future:** Docker image tagged on merge to main. Operators run blueprinted upgrade.

---

# 21. CLI

**Framework:** Typer

- `blueprinted migrate` — run migrations. Supports --dry-run, --tenant, --status
- `blueprinted tenants list|create|delete`
- `blueprinted backup` — dump tenant schemas
- `blueprinted upgrade` — pre-flight, backup prompt, migrate, restart
- `blueprinted healthcheck` — verify instance state
- `blueprinted api-keys create|revoke` — Sprint 10

---

# 22. Documentation

Blueprinted ships with markdown documentation in `/docs` for v1. A seeded documentation tenant — Blueprinted using Blueprinted to document itself — is a post-v1 demonstration project, not a v1 launch requirement.

- **Operator docs:** installation, configuration, upgrade, backup, Authentik setup guide, embedding model selection guide
- **Contributor docs:** architecture, data model, API reference, extension patterns
- **Conceptual docs:** justification articles and research

The seeded documentation tenant is a compelling proof of concept and will be built. It requires a stable platform and a second reviewer to satisfy the self-review prohibition cleanly. It is a 6-month follow-on to v1, not a launch deliverable.

---

# 23. Frontend Screen Inventory

A flat inventory of all views. Role column shows minimum role required. Primary API calls shown — supporting calls omitted for brevity.

## 23.1 Auth and Profile

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Login | Public | OIDC PKCE flow via Authentik |
| Profile | All roles | GET /api/v1/users/me, PATCH /api/v1/users/me |

## 23.2 Dashboard

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Home dashboard (role-aware) | All roles | GET /api/v1/analytics/dashboard |

## 23.3 Tasks

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Task list | Contributor, Admin | GET /api/v1/tasks |
| Task detail / view | All roles | GET /api/v1/tasks/{record_id}/{version} |
| Task create | Contributor, Admin | POST /api/v1/tasks |
| Task revise | Contributor, Admin | POST /api/v1/tasks/{record_id}/{version}/revise |
| Task diff view | Contributor, Admin | GET /api/v1/tasks/{record_id}/{version}/diff |

## 23.4 Workflows

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Workflow list | All roles | GET /api/v1/workflows |
| Workflow detail | All roles | GET /api/v1/workflows/{record_id}/{version} |
| Workflow create / edit | Contributor, Admin | POST /api/v1/workflows |
| Workflow diff view | Contributor, Admin | GET /api/v1/workflows/{record_id}/{version}/diff |

## 23.5 Facts and Concepts

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Facts list | Contributor, Admin | GET /api/v1/facts |
| Fact create | Contributor, Admin | POST /api/v1/facts |
| Fact detail | All roles | GET /api/v1/facts/{record_id} |
| Concepts list | Contributor, Admin | GET /api/v1/concepts |
| Concept create | Contributor, Admin | POST /api/v1/concepts |
| Concept detail | All roles | GET /api/v1/concepts/{record_id} |

## 23.6 Principles

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Principles list | All roles | GET /api/v1/principles |
| Principle detail | All roles | GET /api/v1/principles/{record_id}/{version} |
| Principle create / edit | Contributor, Admin | POST /api/v1/principles |

## 23.7 Review Queue

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Global review queue | Contributor, Admin | GET /api/v1/review/queue |
| Review item, claim | Contributor, Admin | POST /api/v1/review/{type}/{id}/claim |
| Review item, confirm | Contributor, Admin | POST /api/v1/review/{type}/{id}/confirm |
| Review item, return | Contributor, Admin | POST /api/v1/review/{type}/{id}/return |

## 23.8 Ingestion

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Ingestion home / history | Contributor, Admin | GET /api/v1/ingestions |
| PDF upload | Contributor, Admin | POST /api/v1/ingestions |
| Section selection (primary navigation surface, returned to repeatedly) | Contributor, Admin | POST /api/v1/ingestions/{id}/select |
| Ingestion status / progress | Contributor, Admin | GET /api/v1/ingestions/{id}/status |
| Candidate review | Contributor, Admin | GET /api/v1/ingestions/{id}/candidates |
| JSON import | Contributor, Admin | POST /api/v1/ingestions/json |

## 23.9 Relationships

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Relationship list view | All roles | GET /api/v1/relationships |

*Note: The "Propose relationship" write UI is absent from v1. No relationship kinds are defined in v1 — writes are rejected at the API layer. The list view exists for forward compatibility and to display any relationships added via future migration. Full graph visualisation is deferred to v2.*

## 23.10 Search

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Search | All roles | GET /api/v1/search |

## 23.11 Admin

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| User management | Admin | GET/POST/PATCH /api/v1/admin/users |
| Domain management | Admin | GET/POST /api/v1/admin/domains |
| System settings | Admin | GET/PATCH /api/v1/admin/settings |
| LLM provider config | Admin | PATCH /api/v1/admin/settings |
| Tenant management | Admin | GET/POST /api/v1/admin/tenants |
| API key management | Admin + own keys | GET/POST/DELETE /api/v1/admin/api-keys (Sprint 10) |
| Monitoring / instance health | Admin | GET /api/v1/admin/health |
| Audit log | Audit role | GET /api/v1/audit |
| Notifications | All roles | GET /api/v1/notifications |

*Note: Achievements screen exists in the screen inventory but behaviour is unspecified in v1 — stub only. Export screens exist in the MVP but are absent from v1.*

---

# 24. Parked Decisions

- *Go rebuild — triggered if scale demands single-binary deployment or Python performance bottlenecks*
- *Neo4j migration — triggered if graph traversal complexity exceeds PostgreSQL recursive CTE capability*
- *Delivery product architecture and naming — AI-native learning experience layer, not an LMS*
- *Performance-based assessment — future module, potentially separate product*
- *Embedding-based semantic fact deduplication at scale — pgvector is the planned solution*
- *Export and delivery layer — properly specced before v2 sprint planning*
- *Assessment module — reintroduced after assessment theory review*
- *Achievements specification — secondary to core functionality, reintroduced in future sprint*
- *Parallel tenant migration — optimisation for 100+ tenant deployments*
- *Prometheus metrics — once a live instance justifies the overhead*
- *Grafana community dashboard — analytics endpoints to be documented for community contribution*
- *User notification preferences — v1.1 addition. Notification kind values are stable from v1 to support this.*
- *Full relationship graph visualisation — v2. v1 is a read-only list view.*
- *Relationship kind specification — v1.1 workstream informed by real usage patterns*
- *High-volume ingestion patterns — v1.1. v1 is optimised for quality over throughput.*
- *Seeded documentation tenant — post-v1 demonstration project. v1 ships with markdown docs.*
- *agent:relationship_suggester role — v1.1, alongside first relationship kind definition*

---

# 25. Key Decisions Log

| Decision | Rationale |
| --- | --- |
| Python over Go | Personal project timeline, strong AI assistance. Go remains future option. |
| PostgreSQL over Neo4j | Operational simplicity for self-hosted. Graph semantics in data model from day one. |
| Schema-per-tenant | Hard isolation at DB layer. Forward bet on SaaS optionality. Acknowledged complexity for single-tenant v1 installs. |
| Facts and Concepts immutable | A fact is either correct or it isn't. Prior confirmed version was simply wrong. |
| No machine can confirm | Human confirmation of governed knowledge is non-negotiable. Enforced at confirm endpoints, not at credential layer. |
| Claiming not assigning | Self-organising review queue. No bottlenecks, scales naturally. Admin break-glass for small teams. |
| Principles not Primers | Principle implies foundational and enduring. Primer implies introductory and temporary. |
| Dependencies dissolved | Most dependencies are facts or relationship edges. No separate table needed. |
| Ingestion in backend monorepo | Ingestion is core to the platform. Hard-separated internally via API. |
| ARQ over BackgroundTasks | BackgroundTasks loses jobs on restart. Large PDF ingestion cannot silently disappear. |
| pgvector from day one | Justified by semantic search and fact deduplication. Single dependency, two use cases. |
| Role-aware dashboards | Primary user is non-technical. Clarity over configurability. |
| Assessments removed from v1 | Needs assessment theory review. No half-built features behind flags. |
| Export tables as stubs | Behaviour unspecified. Tables exist in schema, no endpoints or UI in v1. |
| Async embeddings | Confirmation must be instant. Embeddings catch up in background via ARQ. Re-triggered on every new confirmed version. |
| Relationship kinds deferred to v1.1 | Semantics harder to specify correctly than they appear. Wrong taxonomy worse than no taxonomy. All four candidate v1 kinds either redundant with existing mechanisms or underspecified. |
| Relationship table exists in v1 | Infrastructure readiness. Writes rejected until kinds defined. |
| No relationship write UI in v1 | No kinds to propose. List view retained for forward compatibility. |
| Sequential tenant migrations | Simple, observable, safely restartable. Parallelism is a named future optimisation. |
| Local disk default storage | Simplest self-hosted experience. S3-compatible option available via fsspec abstraction. |
| OpenAI-compatible API primary | Maximum provider flexibility. Anthropic native format supported via translation adapter. Structured extraction quality depends on provider tool-use support — documented in operator docs. |
| Authentik as single OIDC provider | Right long-term answer for self-hosted. Human auth only in Sprint 2. Machine auth Sprint 10. |
| Machine auth deferred to Sprint 10 | Core platform must exist before the API surface machine credentials consume is stable enough to specify. No-machine-can-confirm enforced from Sprint 4 regardless. |
| v1 relationship view is list not graph | Full graph visualisation is a significant frontend undertaking. Deferred to v2 deliberately. |
| Notification preferences deferred to v1.1 | Kind values stabilised in v1 to support future preference configuration cleanly. |
| Clean slate, no migration | Frees rebuild from legacy schema compromises. Existing instance as reference only. |
| Embedding model is stable infrastructure | pgvector column dimension fixed at schema creation. Changing models requires migration and full re-embedding. Operators choose model before first confirmed records. |
| ARQ resumability is application code | ARQ does not natively resume partially-executed jobs. Chunk-level resumability via chunk_status checkpoints and mandatory worker startup hook. |
| Iterative ingestion as primary model | Single-pass processing of large documents produces unmanageable candidate queues. Operator controls review burden via batch size. High-volume patterns are v1.1. |
| Ingestion produces tasks and principles only | Workflows are human-composed judgment. LLM extracts raw material; humans sequence it. |
| TEST_REVISED process over immutable tests | Immutable tests cause legitimate spec gaps to become permanent bugs. TEST_REVISED commits preserve the protection against silent weakening while allowing honest corrections. |
| Seeded documentation tenant deferred | Requires stable platform and second reviewer for self-review prohibition. Post-v1 demonstration project. |

---

# 26. Sprint Overview

Not the done thing to include sprint planning in a requirements document. Doing it anyway.

**This is a personal project. There are no deadlines. The timeline exists as a pacing tool, not a commitment.** A sprint that takes twice as long as estimated is not a failure — it is information. The estimates below represent a best guess at effort in focused working hours. Calendar time is irrelevant. Life intervenes. That is expected and fine.

**The governing principle is: it takes as long as it takes.** Shipping something right is the only goal. Shipping something fast that needs to be rebuilt is not progress.

Effort estimates are given in focused hours rather than calendar weeks. A "focused hour" means productive working time — not time with the IDE open while distracted. Be honest with yourself about what that means in practice.

The confidence column reflects how well-understood the scope is at planning time. Low confidence means the scope has significant unknowns or the technology is new. Low-confidence sprints should be reviewed at the start of the sprint before work begins — spend an hour re-reading the relevant spec sections and identifying the first three things that could go wrong before writing any code.

| Sprint | Title | Est. Hours | Confidence | Depends on |
| --- | --- | --- | --- | --- |
| 1 | Foundation | 40-60h | Medium | Nothing |
| 2 | Authentik — Human Auth | 50-70h | Low | Sprint 1 |
| 3 | Test Design | 30-40h | Medium | Sprint 2 |
| 4 | Core Data Model and Lifecycle API | 120-160h | Low | Sprint 3 |
| 5 | Review Queue and Claiming | 40-60h | Medium | Sprint 4 |
| 6 | Ingestion Pipeline | 120-160h | Low | Sprint 4 |
| 7 | Search and Embeddings | 40-60h | Medium | Sprint 4 |
| 8 | Frontend — Core Screens | 80-120h | Medium | Sprints 2, 4 |
| 9 | Frontend — Admin and Supporting | 60-80h | Medium | Sprint 8 |
| 10 | Machine Auth, CLI, Observability | 60-80h | Low | Sprint 4 |
| 11 | Hardening | 40-60h | Medium | Sprints 8-10 |
| 12 | Integration and Buffer | 40-60h | Low | All previous |

**Total estimated range: 720-1010 focused hours.**

**On confidence ratings:**
- *High* — well-understood scope, familiar technology, clear acceptance criteria
- *Medium* — mostly understood, some unknowns, technology is new but documented
- *Low* — significant unknowns, new technology, or scope that depends on decisions not yet made

**On the total estimate:** 720-1010 hours is a wide range deliberately. At 10 focused hours per week that is 72-100 weeks. At 20 hours per week it is 36-50 weeks. Neither of those numbers should cause alarm. The platform being built is not trivial. It takes as long as it takes.

**Sprints 5, 6, and 7 can run in parallel after Sprint 4.** Sprints 8 and 9 are a split of what would otherwise be a single oversized frontend sprint.

**Sprint 3 note:** Test design at this stage is necessarily speculative — the full implementation behaviour cannot be known in advance. Tests written here represent the best current understanding of the contracts defined in this specification. `TEST_REVISED` commits during later sprints are expected and do not indicate a process failure. A concentration of `TEST_REVISED` commits against any one area is a signal to pause and review whether that area of the spec needs clarification before implementation continues. Sprint 3 is not a one-time event — a short test review pass is recommended at the start of each feature sprint to catch spec gaps before they become implementation gaps.

**Sprint 2 note:** Delivers human OIDC only. Machine credentials and scoped API keys are Sprint 10 work. The no-machine-can-confirm constraint is enforced from Sprint 4 regardless — it is a property of the confirm endpoints, not of the credential system.

---

*blueprinted.io · github.com/blueprinted-io/core · AGPL 3.0*

*Requirements Specification v4.1 · May 2026*