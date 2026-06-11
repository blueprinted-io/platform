# blueprinted.io

## Platform Rebuild — Requirements Specification

**Version 4.11 · June 2026**

*Confidential. Internal Use Only*

github.com/blueprinted-io/platform

v4.11 changes from v4.10: Sprint 12. §6 pagination convention added — `Page` envelope `{items, total, limit, offset}`, `limit` default 20 / max 100, applied to `/tasks`, `/workflows`, `/principles` list endpoints. Response shape change within `/api/v1` accepted as a pre-GA exception to the breaking-changes rule (no external consumers yet; the app frontend adopts the envelope in Sprint 8 work). §14 worker split: ingestion jobs (`chunk_pdf`, `process_chunks`, `extract_chunk`, `crawl_html`, `render_nav_pages`) move to a dedicated ARQ worker on queue `ingestion`; embeddings and review-claim expiry remain on the default worker. Chunk-recovery startup logic lives with the ingestion worker only.

v4.10 changes from v4.9: Sprint 11 hardening complete. §9.6 audit event types table extended — `record_confirmed`, `break_glass_confirm`, `record_returned`, `record_deprecated`, `record_retired`, `domain_created`, `user_domains_updated` all now wired and tested. `api_keys` table gains `expires_at TIMESTAMPTZ NULL` — set via `expires_at_days` on key creation; expired keys return 401. Unique constraint `(record_id, version)` added to `tasks`, `workflows`, `principles` tables. Rate limiting added (slowapi, Redis backend): 30/min on `GET /search`, 10/min on `POST /ingestions`. `api/services/linting.py` implemented and wired into `TaskResponse.lint_warnings` computed field — advisory warnings on abstract verbs, missing completion, empty actions; suppressed on confirmed records.

v4.9 changes from v4.8: §9.8 export_artifacts stub described — workflow bundle export with SHA256 fingerprint, explicit v1.1. §24 parked decisions updated. §25 key decision: export fingerprinting is a governance audit feature, not deferred arbitrarily. docs/mvp_audit.md export artifacts item closed.

v4.8 changes from v4.7: MVP continuity audit (Fable 5, 2026-06-10). `return_severity` field added to §9.2 shared lifecycle fields and `ReturnRequest` schema — values `"info" | "warning" | "critical"`, nullable; threaded through all three record-type return endpoints. §9.10 Step quality linting added — non-blocking warnings on abstract verbs, missing completion criterion, empty action list; computed on write/read, not stored. §25 key decisions: No hard delete on governed records (audit trail integrity; DB access is intentional escape hatch). No `force_submit` (MVP workaround for missing domain-at-create; that gap no longer exists; break-glass covers genuine admin override). See `docs/mvp_audit.md` for full comparison.

v4.7 changes from v4.6: Machine auth schemas specified (Sprint 10). `api_keys` table added to §9.6 — scoped API keys for agent access, SHA-256 hash storage, `bp_` prefix format, `last_used_at` async update, no-machine-can-confirm enforcement via `agent:` role prefix check. `audit_log` table added to §9.6 — append-only, generic `detail JSONB` column, v1 event types: `break_glass_confirm`, `api_key_created`, `api_key_revoked`. §5.3 extended with credential distinction mechanism (human roles vs `agent:` prefix), HTTP 403 response text for machine-on-confirm attempts, and Authentik OIDC client credentials setup flow.

v4.6 changes from v4.5: Triage and extraction separated by a human review gate (§11.3, §11.5, §11.5a, §11.8a). Triage is now a two-output stage: chunk classification (task_candidate | principle_candidate | reference_material | skip) and a candidate estimate list (one entry per expected candidate, each with an estimated title and type). The operator reviews the estimate list before extraction runs — correcting types (principle → task and vice versa), discarding unwanted candidates, and merging multiple estimates into a single targeted extraction. The extraction LLM receives the approved estimate list as input and performs targeted extraction per approved candidate rather than open-ended extraction of all content. This decoupling means the cheap triage model runs speculatively on every chunk, but the expensive extraction model runs only on human-approved candidates with precise intent. chunk_status gains two new values: triage_complete (triage done, awaiting estimate review) and extraction_queued (estimates approved, awaiting extraction). New table: ingestion_triage_estimates (§11.8a). Operator workflow description updated. §11.5 updated. §11.6 updated. §11.7 updated.

v4.5 changes from v4.4: Three procedure-level corrections following review of the original MVP design document. (1) `procedure_name` removed from the Task schema — it duplicated the task `title` with no distinct meaning; a task's title is the name of its procedure. Removed from `tasks` table, ingestion candidate schema, and JSON import schema. (2) `notes` on `task_steps` formally described: it holds alternatives, caveats, and tool-choice guidance that contextualises a step's actions without being an action itself (e.g. step: "Open /etc/fstab in a text editor"; action: "sudo nano /etc/fstab"; note: "vim or any other editor may be substituted for nano"). This field existed in the schema; it now has authoritative prose. (3) `task_step_screenshots` renamed to `task_step_images` — "image" is the correct generalisation for non-software contexts where a screenshot is not the right word. `caption TEXT` field added to support alt text and display labels. Step image storage path updated in §4.4. LLM-assisted image-to-step association during ingestion deferred to v1.1 (§24); in v1 images are attached to steps manually post-ingestion.

v4.4 changes from v4.3: Facts and Concepts dissolved as independently governed record types (§9.5). The task was always the atomic unit of knowledge in Blueprinted — Facts and Concepts were originally specced with their own governance lifecycle (draft → submitted → confirmed) on the assumption they would be reusable across tasks, but this introduced maintenance overhead grossly disproportionate to the value: every atomic string required its own review cycle. In practice, a fact that is wrong within a task means the task needs revision, not an independent fact record. Facts and Concepts are now `TEXT[]` arrays on the `tasks` table — authored and revised as part of the task, not as standalone governed records. Impact: `facts` and `concepts` tables dropped; `task_fact_refs` and `task_concept_refs` junction tables dropped; `has_deprecated_fact_ref` and `has_deprecated_concept_ref` flags removed from tasks; `raw_facts`/`raw_concepts` columns (added Sprint 7 for ingestion output) renamed to `facts`/`concepts` and promoted to the primary representation; `/api/v1/facts/*` and `/api/v1/concepts/*` API endpoints removed; §23.5 Facts and Concepts screens removed; `fact_deprecated` and `concept_deprecated` notification kinds removed; search endpoint no longer indexes fact/concept records; domain enforcement table simplified (Facts and Concepts no longer exist as domain-agnostic entities). §10.1 (Facts and Concepts immutability design principle) removed. Key decisions log updated. The `raw_facts`/`raw_concepts` naming in the previously committed ingestion migration is an acknowledged artefact — the rename is handled in the v4.4 migration.

v4.3 changes from v4.2: Prompt contracts defined as a first-class spec concern (§11.16). LLM prompts for v1 ingestion stages (triage, task extraction, principle extraction) extracted from inline code strings into versioned prompts/ingestion/*.md files referenced by code. Operator-editable prompts deferred to v1.1 — v1 ships prompts as part of the platform release, change-on-release semantics. Primer→principle terminology corrected in all extracted prompts. Triage output values aligned to v4.1's four-category model (task_candidate | principle_candidate | reference_material | skip). JSON import schema drift between three existing documents resolved — docs/operational_documentation/json_import_schema_spec.md becomes the single source of truth; prompts/external/manual_json_authoring.md rewritten to match. v1.1+ prompts (changelog-impact pipeline, principle-level rewriting) extracted to prompts/v1.1/ but not specced; await their feature subsections. §4.1 backend stack extended with prompt-loading row. Note added in §11.4 distinguishing pipeline-internal candidate schemas from the JSON import payload format.

v4.2 changes from v4.1: Ingestion pipeline source types fully specified (§11). PDF ingestion subsection added covering library choice (PyMuPDF), hybrid outline-and-heading chunking strategy, scanned-PDF heuristic, and failure modes (§11.9). HTML ingestion subsection added covering single-page and site-nav crawl modes, Playwright rendering, content extraction, and auth-walled content deferral to v1.1 (§11.10). Nav discovery and selection flow added (§11.11). JSON ingestion subsection added clarifying that JSON bypasses chunking and section selection (§11.12). ingestions, ingestion_chunks, and ingestion_nav_pages table schemas added — all three previously listed in §9.7 without definitions (§11.13, §11.14, §11.15). §11.5 generalised to acknowledge HTML and JSON sources. §4.1 backend stack extended with PyMuPDF and Playwright dependencies and AGPL3 obligation note. §4.4 storage table generalised for non-file ingestion sources. §23.8 API endpoints extended for HTML upload and nav selection. New system_settings: ingestion_pdf_chunk_size_chars, ingestion_html_respect_robots_txt.

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
| PDF extraction | PyMuPDF (fitz), AGPL3, bundles native MuPDF binary, best-in-class extraction quality |
| HTML rendering | Playwright with Chromium, headless rendering of static and JS-rendered pages |
| Prompt loading | Plain markdown files under `prompts/`, loaded at startup via `api/prompts.py`. No templating framework in v1; simple `.format()` substitution sufficient. |

*Note: Python was chosen over Go despite Go's single-binary deployment advantage. Go remains a named future option; the architecture does not preclude it.*

*Note: PyMuPDF and Playwright both add native dependencies to the worker container. PyMuPDF ships as wheels for all major platforms including Linux ARM64. Playwright requires `playwright install --with-deps chromium` during image build, adding ~300MB. Both are AGPL3-compatible (PyMuPDF is AGPL3, Playwright is Apache 2.0). The AGPL3 obligations of PyMuPDF and MuPDF apply to downstream redistributors — documented in operator deployment notes.*

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
| Vector search | pgvector extension, semantic search across tasks, workflows, and principles |
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
| Ingestion source files | uploads/ingestions/{ingestion_id}/{filename} — PDF uploads only. HTML and JSON ingestions have no source file storage. |
| Step images | uploads/images/{task_record_id}/{step_id}/{filename} |
| Export artifacts | exports/{export_id}/{filename} |
| Operator logos | logos/{tenant_slug}/{filename} |

All upload endpoints enforce: maximum file size (configurable via system_settings), MIME type validation, filename sanitisation. Files are never served directly, always via controlled download endpoints.

---

# 5. Authentication and Authorisation

**Provider:** Authentik, self-hostable, OIDC/SAML, bundled in Docker Compose

**Protocol:** OIDC throughout, no hand-rolled auth under any circumstances

**Human auth:** OIDC flows via Authentik, browser redirects, PKCE flow in React frontend

**Machine auth:** OIDC client credentials flow and scoped API keys — Sprint 10, see §5.3

Authentik is operationally non-trivial. Sprint 2 delivers human OIDC only: Docker Compose configuration, Authentik up and running, FastAPI token validation, and JWT validation tested with mock JWTs against the JWKS endpoint. The PKCE flow in the React frontend is implemented in Sprint 8 when the blueprinted-io/app repository exists. This is the hard dependency for all subsequent development — contributors can log in, sessions work, role-based access is enforced.

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

The break-glass flow requires two concrete data changes:

1. A `self_confirmed_by_admin BOOLEAN NOT NULL DEFAULT FALSE` field on all governed record tables (tasks, workflows, principles). Set to TRUE when an admin confirms their own content.

2. The confirm endpoint must require a non-empty `justification` string in the request body when `self_confirmed_by_admin` would fire. Confirm requests from an admin on their own content that omit `justification` are rejected with HTTP 422.

The audit log entry and visible UI scar are downstream of this flag. The flag is the data integrity piece that makes the rest possible. The `audit_log` table does not exist yet — that is a sequencing gap, not a reason to defer the flag.

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
| OIDC client credentials | For long-running agent processes. Client ID and secret registered in Authentik. JWT contains `roles` claim with one or more `agent:*` values. Token validation is identical to human tokens — same JWKS endpoint, same RS256 verification. |
| Scoped API keys | For short-lived integrations and operator scripts. Managed via Admin UI and CLI. See `api_keys` table in §9.6. |

**Distinguishing machine from human credentials:** Human role names are plain strings (`admin`, `contributor`, `viewer`, etc.). All agent roles are prefixed `agent:`. Any token or API key whose role starts with `agent:` is treated as a machine credential throughout the platform.

**No-machine-can-confirm enforcement approach (decided Sprint 3):** The rule is absolute and permanent, but the *mechanical enforcement* is phased. In Sprints 4–9, confirm endpoints require a valid human OIDC JWT. Since machine credentials do not exist before Sprint 10, this is sufficient — there is nothing else to reject. In Sprint 10, when machine credentials are introduced, the confirm endpoints gain an explicit check: if the authenticated credential's role begins with `agent:`, the confirm endpoint returns HTTP 403 with `{"detail": "Machine credentials cannot confirm governed records."}`. The rule is not weakened between sprints; the threat model simply does not yet have the credential type that the check guards against.

**Authentik setup for OIDC client credentials:** A machine agent registers as an OAuth2 application in Authentik with client credentials grant type. The operator assigns the appropriate agent role group. The resulting `client_id` and `client_secret` are stored by the agent process and used to obtain a short-lived JWT via `POST /application/o/token/` with `grant_type=client_credentials`. The JWT is validated by the platform identically to human tokens.

---

# 6. API Design

**Versioning:** URL-based, /api/v1/ prefix

**Breaking changes:** New version prefix required (/api/v2/). Never a patch to an existing version.

**Consumers:** Human UI, AI agents, third-party integrations — all equal, no privileged path

**Documentation:** OpenAPI generated from FastAPI route definitions, source of truth, not separately maintained

**Pagination:** List endpoints return a `Page` envelope: `{items, total, limit, offset}`. Query parameters `limit` (default 20, min 1, max 100) and `offset` (default 0, min 0). `total` is the count of distinct records — for governed records, latest version only. Ordering is `created_at` descending with `id` descending as tiebreaker, so pages are stable under concurrent inserts. Applies to the governed record lists (`/tasks`, `/workflows`, `/principles`); remaining list endpoints adopt the envelope as they are next touched.

The API version contract is the formal boundary between core and all consumers including the future delivery product. This principle is documented in contributor docs from day one.

---

# 7. Domains

Domains are admin-managed organisational subdivisions of knowledge within a tenant. They are not security boundaries between organisations — tenants provide that isolation.

- Contributors can only create, submit, and review content in their assigned domains
- Admin is implicitly entitled to all domains
- Viewer, Audit, and Content Publisher see all confirmed content across all domains without assignment
- Domain scoping applies to Tasks, Workflows, and Principles. Facts and Concepts no longer exist as independent records — they are string arrays on Tasks and inherit domain context from their parent task.

## 7.1 Domain Registry

Domains are admin-managed records in a central registry. They are not security boundaries — tenants provide isolation. Domains are organisational subdivisions within a tenant.

```
domains
  name          TEXT PRIMARY KEY       -- slug: [a-z0-9][a-z0-9_-]*
  created_at    TIMESTAMPTZ NOT NULL
  created_by    UUID FK → users.id
  disabled_at   TIMESTAMPTZ            -- NULL = active; soft-delete only

user_domains
  user_id       UUID FK → users.id     NOT NULL
  domain        TEXT FK → domains.name NOT NULL
  created_at    TIMESTAMPTZ NOT NULL
  created_by    UUID FK → users.id     NOT NULL
  PRIMARY KEY (user_id, domain)
```

Domain names are normalised to lowercase slugs on creation: `[a-z0-9][a-z0-9_-]*`. Names containing uppercase or spaces are rejected with HTTP 422. A domain cannot be deleted once created — disable it instead. Disabled domains remain on existing records but cannot be assigned to new records or users.

## 7.2 Domain Assignment

Domain assignment is admin-only. Users cannot self-assign domains.

| Role | Domain behaviour |
| --- | --- |
| Admin | Implicitly entitled to all active domains. No user_domains entries required or stored. |
| Contributor | Entitled only to explicitly assigned domains. |
| Viewer | Domain-agnostic. Sees all confirmed content. Cannot be assigned domains. |
| Audit | Domain-agnostic. Same as Viewer. |
| Content Publisher | Domain-agnostic. Same as Viewer. |

Attempting to assign domains to a domain-agnostic role returns HTTP 400.

## 7.3 Domain Enforcement

Enforcement fires at the API layer on write operations. Read operations are not domain-gated for confirmed content — any authenticated user can read any confirmed record regardless of domain assignment.

| Operation | Enforcement |
| --- | --- |
| Create Task / Workflow / Principle | Contributor must be assigned to the domain. HTTP 403 if not. |
| Submit Task / Workflow / Principle | Same check as create. |
| Review / Confirm | Reviewer must be assigned to the record's domain. HTTP 403. |
| Create with no domain | HTTP 422. Domain required. |
| Create with disabled domain | HTTP 422. Must be active. |
Admin bypasses all domain enforcement.

## 7.4 Domain on Records

`domain` is a `TEXT NOT NULL` field on Tasks, Workflows, and Principles. It stores the domain name slug. It is **not** a database-level FK — referential integrity is application-enforced at write time. Facts and concepts are string arrays on the Task record and inherit domain context from their parent task; they have no independent domain field.

## 7.5 Domain API Endpoints

```
GET  /api/v1/admin/domains                    List all domains
POST /api/v1/admin/domains                    Create domain (Admin only)
POST /api/v1/admin/domains/{name}/disable     Soft-delete (Admin only)
POST /api/v1/admin/domains/{name}/enable      Re-enable (Admin only)
GET  /api/v1/admin/users/{id}/domains         List user's domain assignments
PUT  /api/v1/admin/users/{id}/domains         Replace user's domain assignments
```

`PUT /api/v1/admin/users/{id}/domains` is a full replace — deletes all existing assignments and inserts the new set atomically. Partial update is not supported.

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
status                    TEXT         -- draft | submitted | confirmed | deprecated | returned | retired
created_at                TIMESTAMPTZ
updated_at                TIMESTAMPTZ
created_by                UUID FK → users.id
updated_by                UUID FK → users.id
reviewed_at               TIMESTAMPTZ  -- drives staleness calculation
reviewed_by               UUID FK → users.id
change_note               TEXT
return_severity           TEXT         -- "info" | "warning" | "critical" — reviewer's assessment of urgency; NULL if no severity set
needs_review_flag         BOOL NOT NULL DEFAULT FALSE
needs_review_note         TEXT
self_confirmed_by_admin   BOOL NOT NULL DEFAULT FALSE  -- set when admin confirms own content (§5.1 break-glass)
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
- `references` — redundant with inline facts/concepts on the task record for the primary use case.
- `depends_on` — conflicts with the no-workflow-prerequisites rule and creates a third location for precondition logic alongside Task Dependencies and Workflow composition.

Relationship kind specification is a v1.1 workstream, informed by real usage patterns from the authoring UI and ingestion pipeline.

## 9.5 Record Taxonomy

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

The governed procedure unit and the atomic unit of knowledge in Blueprinted. Owns its facts and concepts directly as string arrays — these are not references to independent records. Steps are owned by the Task. Task-level irreversibility is derived — a Task is irreversible if any Step has irreversible = TRUE.

Each step is composed of four elements: the step text (the intent — what is being done), an ordered list of actions (the concrete how — specific commands, menu paths, or tool interactions), notes (alternatives, caveats, and tool-choice guidance that contextualise the actions without being actions themselves), and a completion criterion (the observable proof that the step is done). Images may be attached to a step when the text alone cannot be made unambiguous.

```
tasks
  + shared identity and lifecycle fields
  title                       TEXT NOT NULL
  outcome                     TEXT NOT NULL
  domain                      TEXT
  software_name               TEXT
  software_version            TEXT
  media_url                   TEXT
  ingestion_id                UUID FK → ingestions.id
  facts                       TEXT[]   -- atomic statements of truth for this task
  concepts                    TEXT[]   -- contextual knowledge explaining why this task exists
  tags                        TEXT[]
  embedding                   vector(1536)

task_steps
  id               UUID PRIMARY KEY
  task_id          UUID FK → tasks.id
  order_index      INT NOT NULL
  step             TEXT NOT NULL        -- the intent: what is being done
  notes            TEXT                 -- alternatives, caveats, tool-choice guidance
  completion       TEXT NOT NULL        -- observable proof the step is done
  irreversible     BOOL NOT NULL DEFAULT FALSE

task_step_actions
  id           UUID PRIMARY KEY
  step_id      UUID FK → task_steps.id
  order_index  INT NOT NULL
  instruction  TEXT NOT NULL            -- concrete command, menu path, or interaction

task_step_images
  id           UUID PRIMARY KEY
  step_id      UUID FK → task_steps.id
  order_index  INT NOT NULL
  storage_path TEXT NOT NULL            -- resolved via storage backend abstraction
  caption      TEXT                     -- alt text or display label
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
  task_record_id     UUID  -- application-enforced: must reference a confirmed task record_id
  order_index        INT NOT NULL

workflow_principle_refs
  workflow_id          UUID FK → workflows.id
  principle_record_id  UUID  -- application-enforced: must reference a confirmed principle record_id
  attached_at          TIMESTAMPTZ
  attached_by          UUID FK → users.id
```

### Relationships

```
relationships
  id              UUID PRIMARY KEY
  source_id       UUID NOT NULL
  source_type     TEXT NOT NULL  -- 'task'|'workflow'|'principle'
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
api_keys
audit_log
notifications
review_claims
```

### api_keys Table

Stores scoped API keys for machine access (agent processes and short-lived integrations). The raw key is generated once and shown once on creation — only a SHA-256 hash is stored. The first eight characters of the raw key are stored as `key_prefix` for display in listings.

```
api_keys
  id           UUID PRIMARY KEY
  name         TEXT NOT NULL           -- operator-assigned label for display
  key_prefix   TEXT NOT NULL           -- first 8 chars of raw key, for identification in listings
  key_hash     TEXT NOT NULL           -- SHA-256 hex digest of the full raw key
  role         TEXT NOT NULL           -- agent:workflow_consumer | agent:staleness_monitor | agent:orphan_detector
  created_by   UUID NOT NULL FK → users.id
  created_at   TIMESTAMPTZ NOT NULL
  last_used_at TIMESTAMPTZ             -- updated on each authenticated request, nullable
  revoked_at   TIMESTAMPTZ             -- null = active
  revoked_by   UUID FK → users.id      -- null = not yet revoked
```

**Key format:** `bp_` prefix followed by 48 random URL-safe base64 characters (288 bits of entropy). Example: `bp_aB3xZ9qRmK...`. The prefix `bp_` allows secrets scanners to detect accidental leaks.

**Authentication flow:** The API accepts `Authorization: Bearer <key>` where the value matches the `bp_` prefix. The middleware computes SHA-256 of the presented key, looks up the hash in `api_keys`, and rejects if `revoked_at IS NOT NULL`. On match, the request proceeds with the role from `api_keys.role` as the credential identity. `last_used_at` is updated asynchronously (fire-and-forget) to avoid adding latency to every authenticated request.

**No-machine-can-confirm enforcement:** Any credential whose role starts with `agent:` is a machine credential. Confirm endpoints check the role prefix and return HTTP 403 if it begins with `agent:`. This applies to both OIDC client credential JWTs (where the `roles` claim contains only `agent:*` values) and scoped API keys.

### audit_log Table

Append-only audit trail. No updates or deletes. Written by the platform on significant privileged operations.

```
audit_log
  id           UUID PRIMARY KEY
  event_type   TEXT NOT NULL           -- see event types below
  actor_id     UUID NOT NULL FK → users.id
  actor_type   TEXT NOT NULL           -- 'user' | 'agent'
  target_id    UUID                    -- entity affected; null for non-entity events
  target_type  TEXT                    -- 'task' | 'workflow' | 'principle' | 'api_key' | null
  detail       JSONB NOT NULL DEFAULT '{}'  -- event-specific structured data
  created_at   TIMESTAMPTZ NOT NULL
```

**Event types in v1:**

| event_type | Written when | detail fields |
| --- | --- | --- |
| `record_confirmed` | A governed record transitions submitted → confirmed | `record_type`, `record_id`, `version` |
| `break_glass_confirm` | Admin self-confirms their own record (§5.1) | `record_type`, `record_id`, `version`, `justification` |
| `record_returned` | A governed record transitions submitted → returned | `record_type`, `record_id`, `version`, `note?`, `severity?` |
| `record_deprecated` | A confirmed record transitions → deprecated | `record_type`, `record_id`, `version` |
| `record_retired` | A confirmed record transitions → retired | `record_type`, `record_id`, `version` |
| `domain_created` | Admin creates a domain | `domain` |
| `user_domains_updated` | Admin replaces a user's domain assignments | `user_id`, `added[]`, `removed[]` |
| `api_key_created` | Admin creates an API key | `name`, `role` |
| `api_key_revoked` | Admin revokes an API key | `name`, `role` |

The schema is intentionally generic — `detail` carries event-specific structure without requiring schema migrations for new event types.

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
export_artifacts       -- v1.1. Records each workflow bundle export: workflow record_id,
                          version, exported_at, exported_by, sha256 fingerprint of the
                          bundle payload. Enables recipients to verify they hold an
                          unmodified export and operators to audit what was shared and when.
presentation_tokens    -- stub
changelog_runs         -- stub
changelog_impacts      -- stub
```

## 9.9 Authoring Model and the Knowledge Hierarchy

### The hierarchy

```
Domain
└── Workflows        (the consumable product — expresses "how" the domain works)
    ├── Tasks        (atomic procedural units that compose the workflow)
    └── Principles   (governing knowledge that informs the workflow)
```

Principles are attached to Workflows, never to Tasks. A Principle captures foundational knowledge that gives a workflow its context and rationale — it is not a step-level annotation.

Tasks are the atomic unit of knowledge. They are independently governed, independently versioned, and reusable across multiple workflows. A task exists in its own right; a workflow composes tasks into a coherent procedure.

### Two-directional authoring and governance

The platform operates with two directions of travel that run in opposition to each other. This opposition is intentional — it is the primary quality mechanism.

**Top-down authoring (human mental model):**
The operator starts from intent and works downward.

1. Establish the domain ("Veeam Backup & Replication")
2. Express the workflows that characterise the domain ("Back up a vSphere Virtual Machine")
3. For each workflow, identify the tasks that compose it and the principles that inform it
4. Author each task and principle

This is the natural human authoring journey. It follows the same path a subject-matter expert would take when documenting a system: start with what the system does, then explain how.

**Bottom-up governance (machine/audit model):**
The governance lifecycle runs upward through the same hierarchy.

- Tasks and Principles are confirmed independently through the review queue
- A Workflow can only reference confirmed Task and Principle records
- A Workflow cannot be confirmed until its constituent records are confirmed
- Domains contain the confirmed Workflows that represent its knowledge

**The friction between directions is the quality gate.** An operator cannot ship a workflow that references unconfirmed tasks. That friction forces each atomic unit of knowledge to be reviewed and confirmed on its own terms, not just "good enough in context." The independence of the review is what gives machine consumers and audit confidence that every record in the system has been explicitly validated.

### Mapping

The activity of authoring a domain's content top-down is called **mapping** the domain. It is not a separate governed entity or a distinct pipeline stage — it is simply the authoring journey described above. "Map" is the operator-facing term for the work of populating a domain with workflows, tasks, and principles. The term captures the exploratory, top-down nature of the activity without implying a rigid process.

### UI implication

The platform's authoring UI should support workflow-first authoring: create or select a workflow, stub the tasks it needs from within that workflow context, fill each task in from there. This mirrors the human mental model. The governance layer enforces quality bottom-up regardless of which direction the author travelled to create the records.

This is a Sprint 10+ frontend concern. The data model already supports it — workflows reference tasks by `record_id`, and tasks are independently governed. The current UI requires tasks to exist before a workflow can reference them; a workflow-first authoring mode removes that friction without changing any backend behaviour.

## 9.10 Step Quality Linting

The platform validates task steps on create and update and returns warnings (not hard errors). Linting does not block submission or confirmation — it surfaces quality signals to the author before a record enters the review queue.

**Rules (all non-blocking — warnings only):**

- **Abstract verb flag** — step text beginning with abstract verbs ("ensure", "handle", "manage", "maintain", "support", "address") is flagged. These verbs describe intent without describing action.
- **Missing completion criterion** — a step with no `completion` value set is flagged.
- **Empty action list** — a step with no actions is flagged.

**API behaviour:**

Steps that fail lint rules are accepted and saved. The response includes a `lint_warnings` array at the task level listing `{step_index, rule, message}` objects. A task with lint warnings may still be submitted and confirmed; the warnings are advisory.

Warnings are not stored — they are computed on every write response and on GET for the authored record. The lint result is not surfaced on confirmed records (reviewers see the record as-authored).

---

# 10. Key Design Principles

## 10.1 No Machine Can Confirm

"Confirm" means the state transition from `submitted` to `confirmed` on a governed record (Task, Workflow, Principle). No agent credential, API key, or automated process can call a confirm endpoint. Enforced at the API layer regardless of credential scopes.

Automated workers may write to confirmed records via background jobs (embedding generation, flag propagation) but cannot perform the state transition. This distinction is important: the ARQ embedding worker writes an embedding vector to a confirmed record — it does not confirm anything.

## 10.2 Every First-Party Component is an API Consumer

UI, ingestion pipeline, CLI, future modules — all consume the versioned API. Nothing gets direct database access except the core service itself.

## 10.3 Tests are Written Before Implementation

Tests are written before implementation. A failing test is a blocker requiring human investigation before any code change is made. The default assumption is always that the implementation is wrong, not the test.

**AI is prohibited from modifying existing test files to make a failing test pass.** If an AI coding assistant determines that a test is itself incorrect — because the spec was incomplete at the time of writing, or because a deliberate design decision has changed the expected behaviour — it must stop, flag the specific test and its reasoning, and wait for explicit human instruction before any modification is made.

When a test is legitimately revised, the commit must include:

- A `TEST_REVISED` marker in the commit message
- The reason the test was wrong (spec gap, deliberate design change, or authoring error)
- The human decision that authorised the change

A `TEST_REVISED` commit is not a failure state. It is the correct process when a test needs to change. What it prevents is silent revision — the quiet weakening of a contract to fit an implementation that should have been fixed instead.

**The failure mode this rule exists to prevent:** an AI assistant changes `assert response.status_code == 403` to `assert response.status_code == 200` because the implementation returns 200, and the build passes, and nobody notices the access control is gone.

Sprint 3 test design precedes all feature implementation but cannot anticipate every edge case. `TEST_REVISED` commits are expected and normal. Their frequency is a signal worth tracking — a cluster of `TEST_REVISED` commits against a single sprint's tests indicates the spec for that area was underspecified and should be reviewed before implementation proceeds further.

## 10.4 Everything Configurable is Configurable via UI

Runtime configuration lives in system_settings, managed via Admin UI and CLI. Bootstrap configuration lives in environment variables. Nothing is hardcoded.

## 10.5 Imports Never Create Confirmed Records

The ingestion pipeline can only create draft or submitted records. The confirmed state cannot be set by import. Enforced at the API layer.

## 10.6 Staleness is Tracked Not Assumed

Confirmed records have reviewed_at and reviewed_by. The staleness threshold is configurable. Staleness surfaces in dashboards — it does not automatically deprecate or invalidate records.

---

# 11. Ingestion Pipeline Sub-Specification

The ingestion pipeline is a hard-separated first-party API consumer living in the backend monorepo. It communicates with core exclusively via the versioned API. No shared internal models, no direct database access.

v1 supports three ingestion sources: PDF upload, HTML (single page or site-nav crawl), and JSON import. All three converge on the same ingestion_chunks representation after their source-specific decomposition stage, and share stages 2–6 of the pipeline. Source-specific behaviour is documented in §11.9 (PDF), §11.10 (HTML), and §11.12 (JSON).

**Iterative processing is the primary model.** Single-pass processing of an entire document is not a goal and not optimised for — it is simply iterative processing with one large batch, and for any document of meaningful size it will produce an unmanageable candidate review queue.

The intended operator workflow is:

1. Upload the document
2. Review the chunk list, select a small number of sections (2-5 is typical)
3. Run triage on the selected batch — each chunk is classified and a candidate estimate list produced
4. Review the estimate list: correct types, discard unwanted candidates, merge over-split candidates
5. Approve estimates to trigger targeted extraction
6. Review and commit the extracted candidates
7. Return to the chunk list and select the next batch
8. Repeat until the document is processed to the desired depth

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
| 1. Structural decomposition | Source-specific. PDF: outline-and-heading hybrid chunking (§11.9). HTML: heading-based chunking, single page or site-nav crawl (§11.10, §11.11). JSON: schema validation, direct conversion to candidates without chunking (§11.12). |
| 2. Section selection | Operator reviews chunk list and selects a batch of sections to process (typically 2-5). Primary navigation surface — returned to repeatedly. See §11.5. |
| 3. Triage | Each selected chunk classified (task_candidate, principle_candidate, reference_material, skip) and a candidate estimate list produced (one entry per expected candidate, each with estimated title and type). Cheap model. Chunk moves to triage_complete. See §11.5. |
| 4. Estimate review | Operator reviews the estimate list. May correct types (principle ↔ task), discard unwanted candidates, or merge over-split candidates into a single targeted extraction. Approving the list moves the chunk to extraction_queued. See §11.5a. |
| 5. Extraction | Extraction LLM runs per approved estimate, not per chunk. Each estimate produces one structured candidate. Expensive model; runs only on human-approved candidates with explicit intent. Chunk moves to done. |
| 6. Candidate review | Contributor reviews extracted candidates. Accept, edit, or discard each. |
| 7. Commit | Accepted candidates committed as draft or submitted records via API. ingestion_candidates.committed_record_id set. Operator returns to stage 2 for the next batch. |

## 11.4 Candidate Output Schemas

### Task Candidate

```json
{
  "type": "task",
  "title": "string, required",
  "outcome": "string, required",
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

> **Note:** The candidate schemas above describe the output of the LLM extraction stages. This is the pipeline-internal representation written to `ingestion_candidates`. It is not the same as the JSON import payload format used by `POST /api/v1/ingestions/json` — that format is defined in `docs/operational_documentation/json_import_schema_spec.md`.

## 11.5 Section Selection Flow

The section selection screen is the **primary navigation surface for ingestion**. It is not a one-time setup step — the operator returns to it repeatedly throughout the processing of a document.

Applies to PDF and HTML ingestions only. JSON ingestions bypass this stage — see §11.12.

After structural decomposition completes (PDF chunking, or HTML rendering and chunking, or HTML nav-crawl), the operator is presented with the section selection screen. This screen persists for the lifetime of the ingestion job and can be returned to at any point.

**Screen shows per chunk:**
- Section title
- Page range
- Word count
- Brief text preview
- Current chunk status: pending / queued / processing / done / error / skipped

**Operator actions:**
- Select individual chunks to queue for the current batch
- Select all unprocessed / deselect all controls available
- Submit selection — selected chunks marked `chunk_status = queued`, triage job fires
- Return to this screen at any point to queue the next batch

**Recommended batch size:** 2-5 sections per pass. Large batches produce large estimate review queues. The operator controls their own review burden.

Scanned sections are automatically excluded and flagged. They cannot be selected.

Chunk status values and their display treatment:

| Status | Meaning | Display |
| --- | --- | --- |
| pending | Not yet queued | Default |
| queued | Queued for triage | Subtle indicator |
| processing | Triage running | Spinner |
| triage_complete | Triage done, estimates awaiting review | Action required badge |
| extraction_queued | Estimates approved, extraction pending | Subtle indicator |
| done | Extraction complete | Candidate count shown |
| error | Failed at triage or extraction | Retry option shown |
| skipped | Manually excluded | Muted |

```
POST /api/v1/ingestions/{id}/select
Body:     { "chunk_ids": ["uuid1", "uuid2", ...] }
Response: { "queued_count": N, "ingestion_id": "uuid" }
```

This endpoint is callable multiple times on the same ingestion. Each call queues the specified chunks. Previously processed chunks are not affected.

## 11.5a Triage Estimate Review

After triage completes, each chunk in `triage_complete` state has an associated estimate list in `ingestion_triage_estimates`. The operator reviews this list before extraction runs.

**The estimate list shows per chunk:**
- One row per expected candidate
- Estimated title (LLM's best guess at the candidate name)
- Type (task or principle) with a toggle to correct it
- A discard control to remove unwanted candidates
- A merge control to combine two or more estimates into one targeted extraction

**Merge behaviour:** When estimates are merged, the operator provides (or edits) a single combined title. The extraction LLM receives this merged title as its target and extracts one candidate. The individual estimates that were merged are marked `merged` and do not receive their own extraction call. This is the primary remedy for over-splitting — where a section describes one procedure but the triage LLM identified it as multiple discrete tasks.

**Type correction:** Changing an estimate's type (e.g. principle → task) causes extraction to use the task extraction prompt and produce a task candidate, regardless of the chunk's original triage classification.

**Approving the list:** The operator approves the estimate list for a chunk, moving it to `extraction_queued`. Chunks with all estimates discarded move directly to `done` with zero candidates and no extraction call.

```
GET  /api/v1/ingestions/{id}/chunks/{chunk_id}/estimates
Response: [ { "id": "uuid", "estimated_title": "...", "record_type": "task|principle",
              "approved_type": "task|principle", "estimate_status": "pending|approved|rejected|merged",
              "merged_into_id": "uuid|null", "sort_order": N } ]

PATCH /api/v1/ingestions/{id}/chunks/{chunk_id}/estimates/{estimate_id}
Body: { "approved_type": "task|principle", "estimated_title": "...", "estimate_status": "rejected" }

POST /api/v1/ingestions/{id}/chunks/{chunk_id}/estimates/merge
Body: { "estimate_ids": ["uuid1", "uuid2"], "merged_title": "..." }
Response: { "surviving_id": "uuid" }

POST /api/v1/ingestions/{id}/chunks/{chunk_id}/estimates/approve
Response: { "extraction_queued": N }
```

## 11.6 Candidate Validation Rules

- Required fields missing → candidate marked invalid
- Steps array empty on task candidate → candidate marked invalid
- Unknown fields → stripped silently, not an error
- LLM returns non-JSON → estimate marked error, chunk error_detail updated; other estimates in the chunk continue
- Partial extraction: valid candidates proceed, invalid marked separately
- If all estimates for a chunk error → chunk marked error

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

## 11.8a ingestion_triage_estimates Table

Stores the candidate estimate list produced by the triage LLM for each chunk. One row per estimated candidate. Created when a chunk reaches `triage_complete`. Read and edited during the estimate review step (§11.5a). Consumed by the extraction job when the chunk is approved.

```
ingestion_triage_estimates
  id                UUID PRIMARY KEY
  ingestion_id      UUID FK → ingestions.id
  chunk_id          UUID FK → ingestion_chunks.id
  record_type       TEXT         -- LLM's original classification: 'task' | 'principle'
  approved_type     TEXT         -- human-corrected type, defaults to record_type
  estimated_title   TEXT         -- LLM's estimated candidate title
  estimate_status   TEXT         -- pending | approved | rejected | merged
  merged_into_id    UUID FK → ingestion_triage_estimates.id  -- null unless merged
  sort_order        INT NOT NULL -- display order within chunk, assigned by triage
```

`estimate_status` transitions:
- `pending` → `approved` (operator approves without change)
- `pending` → `rejected` (operator discards)
- `pending` → `merged` (operator merges into another estimate; merged_into_id set)

The surviving estimate in a merge inherits the operator-provided `merged_title` via an `estimated_title` update. Its `estimate_status` remains `pending` until the chunk is approved.

The extraction job processes only estimates in `approved` status. Each approved estimate produces exactly one extraction LLM call and one `ingestion_candidates` row.

## 11.9 PDF Ingestion

PDF ingestion uses PyMuPDF (fitz) for text extraction, outline parsing, and structural inspection. The library is AGPL3-licensed, consistent with Blueprinted's licence.

### Source acceptance

| Check | Action on failure |
| --- | --- |
| File MIME type is application/pdf | Reject upload at API |
| File size under configured maximum | Reject upload at API |
| File not duplicate of existing ingestion (SHA-256 match) | Redirect to existing ingestion |
| Document yields any extractable text at all | Mark ingestion failed, message: "Scanned or image-only PDF — please supply a text-based PDF or copy content into a manual import." |

Scanned-PDF heuristic: if text extraction across the whole document returns empty content, the document is treated as scanned and rejected. OCR is not in scope for v1. Documents with mixed scanned and text pages will pass the heuristic but produce sparse chunks on the scanned pages — operators see this in the chunk word count and can deselect those sections.

### Chunking strategy

The chunking algorithm uses a hybrid of outline (bookmarks) and heading detection:

1. **Outline pass:** PyMuPDF extracts the PDF's outline (bookmarks). If present, top-level outline entries define top-level section boundaries. Each top-level outline entry becomes a parent chunk boundary.
2. **Heading pass within sections:** within each top-level section, PyMuPDF inspects text rendering (font size, weight, position) to detect headings. Detected headings define subsection boundaries inside the parent.
3. **Outline absent:** if the document has no outline at all, the entire document is treated as one section and heading detection alone defines chunk boundaries.
4. **Headings absent:** if neither outline nor headings are detected, fall back to character-count chunking with a configurable chunk size (default 4000 characters, configurable via `ingestion_pdf_chunk_size_chars` in system_settings).

The hybrid approach handles three real-world failure modes: documents with good outlines but no heading detection (rare, but happens with scanned-to-PDF workflows that preserve bookmarks); documents with no outline but well-marked headings (common in technical documentation exported from web formats); and documents that have neither (typically scanned receipts, but occasionally legitimate technical PDFs).

### Chunk metadata

Each PDF chunk records:

- `section_title` — from outline entry or detected heading; NULL only if fallback character-count chunking was used
- `section_level` — heading depth (1 = top-level, 2 = subsection, etc.); 0 if unknown
- `pages_json` — array of page numbers spanned by the chunk; pages are inclusive of any page on which any chunk content appears
- `text` — extracted plain text, with PyMuPDF's reading-order heuristic applied

### Duplicate detection

SHA-256 hash of the uploaded PDF bytes is computed and stored on `ingestions.source_sha256`. A subsequent upload with the same hash redirects to the existing ingestion record rather than creating a new one. This is reliable for PDF because the file is the source of truth — the content does not change between uploads. HTML duplicate detection is weaker (§11.10).

### Failure modes

| Failure | Detection | Handling |
| --- | --- | --- |
| Scanned / no extractable text | Empty text extraction across document | Ingestion marked failed, explicit operator message |
| PyMuPDF parse error (corrupt PDF) | Exception during open | Ingestion marked failed, message captures parse error |
| File over size limit | Pre-upload check | Rejected at API layer, not stored |
| Duplicate upload | SHA-256 match | Redirect to existing ingestion record |

## 11.10 HTML Ingestion

HTML ingestion uses Playwright with Chromium for headless rendering. This handles both static HTML and JavaScript-rendered pages that require a browser to produce their final content.

### Source modes

**Single page:** A single URL is submitted. Playwright renders the page, content is extracted, and heading-based chunking is applied to produce ingestion_chunks. This is the default and simplest mode.

**Site-nav crawl:** A root URL is submitted. Blueprinted discovers navigable pages via the page's navigation structure (§11.11). The operator reviews the discovered pages and selects which to include. Each selected page is rendered and chunked individually, producing one or more ingestion_chunks per page.

### Source acceptance

| Check | Action on failure |
| --- | --- |
| URL scheme is http:// or https:// | Reject at API |
| URL is reachable (HTTP 200 or redirect chain resolves) | Mark ingestion failed with error |
| Page yields any extractable text content | Mark ingestion failed, message: "No extractable content — page may require authentication or render client-only content" |
| Robots.txt compliance (configurable via `ingestion_html_respect_robots_txt`) | If true, reject pages disallowed by robots.txt with a warning; honour Crawl-delay |

**Auth-walled content:** Pages requiring login are not supported in v1. Playwright does not hold authenticated sessions. If a page returns a login redirect or renders only an auth wall, the ingestion fails with an explicit error. Authenticated HTML ingestion is deferred to v1.1.

### Content extraction and chunking

After Playwright renders the page:

1. Playwright returns the DOM's innerText (rendered text, not raw HTML). Hidden elements excluded. Navigation chrome (top nav, sidebar, footer) is heuristically stripped — content within `<main>`, `<article>`, or the largest text-bearing block element is preferred.
2. Heading-based chunking is applied: H1–H6 tags define section boundaries. Each heading and its following content until the next same-or-higher heading forms a chunk.
3. If no headings are detected, the entire page is treated as a single chunk.
4. Scanned-content heuristic: not applicable to HTML. HTML that renders as text is always extractable.

### Chunk metadata

HTML chunks record the same fields as PDF chunks (§11.14) with these differences:

- `pages_json` is NULL for HTML chunks — pages are a PDF concept
- `section_title` is derived from the heading tag content, or the page `<title>` if no headings exist
- `source_url` records which page URL the chunk came from, relevant for site-nav crawls spanning multiple pages

### Duplicate detection

SHA-256 of the source URL (lowercased, query-string normalised) is stored on `ingestions.source_sha256`. A subsequent ingestion of the same URL redirects to the existing ingestion. Content changes under a stable URL are not automatically detected in v1 — re-ingestion after content change requires the existing ingestion to be abandoned or a new ingestion created with `?force=true`. The `?force=true` flag bypasses the SHA-256 redirect and creates a new ingestion record.

### Failure modes

| Failure | Detection | Handling |
| --- | --- | --- |
| URL unreachable | HTTP error or timeout | Ingestion marked failed, error captured |
| Auth-walled page | No text content extracted | Ingestion marked failed, explicit operator message |
| Robots.txt disallowed | robots.txt check | Ingestion rejected at API (configurable) |
| Playwright timeout | Browser timeout | Ingestion marked failed, timeout duration logged |
| No extractable content | Empty text after extraction | Ingestion marked failed, explicit operator message |

## 11.11 Nav Discovery and Selection

Nav discovery is the process by which Blueprinted discovers pages available for ingestion from an HTML source URL. It is used only for site-nav crawl mode (§11.10).

### Discovery

Playwright renders the root URL. Blueprinted inspects the rendered DOM for navigable links:

1. Links within `<nav>`, `<aside>`, or elements with `role="navigation"` are treated as nav links
2. Links are followed one level deep from the root by default
3. Each discovered link is stored as an `ingestion_nav_pages` row with its URL, title (from link text or target page `<title>`), and position in the nav hierarchy
4. Duplicate URLs (same URL discovered via multiple nav links) are deduplicated

### Selection

After nav discovery completes, the operator is presented with the discovered page list. This is the nav-mode equivalent of the section selection screen (§11.5).

The operator:
- Sees all discovered pages with their titles and nav depth
- Selects pages to include in the ingestion
- Submits the selection — selected pages are queued for rendering and chunking

```
POST /api/v1/ingestions/{id}/nav-select
Body:     { "nav_page_ids": ["uuid1", "uuid2", ...] }
Response: { "queued_count": N, "ingestion_id": "uuid" }
```

Selected nav pages are rendered individually. Each rendered page's content is chunked and appended to the ingestion's `ingestion_chunks`. After rendering, the ingestion proceeds to section selection (§11.5) to allow the operator to choose which chunks to process.

### Nav page statuses

| Status | Meaning |
| --- | --- |
| pending | Discovered, not yet selected or skipped by operator |
| selected | Operator selected; rendering queued |
| rendered | Page rendered and chunked successfully |
| failed | Rendering failed — error captured |
| skipped | Operator explicitly skipped |

## 11.12 JSON Ingestion

JSON ingestion accepts a pre-structured payload conforming to the import schema defined in `docs/operational_documentation/json_import_schema_spec.md`. Unlike PDF and HTML, JSON ingestion does not go through chunking or LLM extraction — the payload is already structured, and the LLM stages would discard information rather than add it.

### Flow

1. Operator submits JSON via `POST /api/v1/ingestions/json`
2. Payload validated against schema; any validation failure rejects the entire payload with descriptive error (no partial imports — see schema spec §Validation Rules)
3. Valid payload converted directly to `ingestion_candidates` rows (`record_type = 'task'` or `'principle'`, `candidate_status = 'pending'`)
4. No chunks are created; `ingestion_chunks` is empty for JSON ingestions
5. Operator proceeds directly to candidate review (§11.5 is skipped; the review screen surfaces candidates immediately)

### Source storage

JSON payloads are not stored as files. The validated payload structure is recorded in the resulting `ingestion_candidates` rows. The original payload is not retained — re-importing requires resubmission.

### Duplicate detection

SHA-256 of the canonical-JSON-encoded payload (sorted keys, no whitespace) is computed and stored on `ingestions.source_sha256`. A resubmission with the same hash redirects to the existing ingestion.

### Schema authority

The JSON import schema is versioned independently and lives in `docs/operational_documentation/json_import_schema_spec.md`. Changes to the schema are made there. This specification references it but does not redefine it.

## 11.13 ingestions Table

```
ingestions
  id                    UUID PRIMARY KEY
  source_type           TEXT NOT NULL        -- 'pdf' | 'html' | 'json'
  status                TEXT NOT NULL        -- pending | chunking | ready | failed
  created_by            UUID FK → users.id
  created_at            TIMESTAMPTZ NOT NULL
  updated_at            TIMESTAMPTZ NOT NULL
  original_filename     TEXT                 -- PDF only; NULL for html and json
  storage_path          TEXT                 -- PDF only; path via storage abstraction
  source_url            TEXT                 -- HTML only; NULL for pdf and json
  source_sha256         TEXT                 -- dedup hash (PDF: file bytes SHA-256; HTML: normalised URL SHA-256; JSON: canonical payload SHA-256)
  page_count            INT                  -- PDF only; populated after chunking
  chunk_count           INT                  -- populated after chunking; 0 for JSON ingestions
  error_detail          TEXT                 -- set when status = failed
```

Status lifecycle:

- `pending` — ingestion record created, source not yet processed
- `chunking` — structural decomposition in progress (PDF/HTML)
- `ready` — chunks available for section selection (PDF/HTML) or candidates available for review (JSON)
- `failed` — structural decomposition failed; see `error_detail`

## 11.14 ingestion_chunks Table

```
ingestion_chunks
  id                UUID PRIMARY KEY
  ingestion_id      UUID FK → ingestions.id NOT NULL
  chunk_index       INT NOT NULL              -- ordering within ingestion
  section_title     TEXT                      -- from outline entry, heading, or nav page title; NULL only in character-count fallback
  section_level     INT NOT NULL DEFAULT 0    -- heading depth (1 = top-level, 2 = subsection); 0 if unknown
  pages_json        JSONB                     -- array of page numbers spanned; NULL for HTML chunks
  source_url        TEXT                      -- HTML site-nav crawls: the page URL this chunk came from; NULL for PDF
  text              TEXT NOT NULL             -- full extracted text for LLM processing
  text_preview      TEXT NOT NULL             -- first ~200 characters, for section selection UI
  word_count        INT NOT NULL
  chunk_status      TEXT NOT NULL DEFAULT 'pending'   -- pending | queued | processing | done | error | skipped
  is_scanned        BOOL NOT NULL DEFAULT FALSE        -- PDF: true if chunk is from a scanned page; always false for HTML
  error_detail      TEXT                      -- set when chunk_status = error
  candidate_count   INT NOT NULL DEFAULT 0    -- updated when candidates are written for this chunk
```

## 11.15 ingestion_nav_pages Table

Stores pages discovered during HTML site-nav crawl (§11.11). Only populated for HTML ingestions in site-nav crawl mode. Always empty for PDF and JSON ingestions.

```
ingestion_nav_pages
  id                UUID PRIMARY KEY
  ingestion_id      UUID FK → ingestions.id NOT NULL
  url               TEXT NOT NULL
  title             TEXT                      -- from link text or page <title>
  nav_level         INT NOT NULL DEFAULT 1    -- depth in nav hierarchy (1 = root-level, 2 = child, etc.)
  parent_id         UUID FK → ingestion_nav_pages.id  -- NULL for root-level pages
  nav_status        TEXT NOT NULL DEFAULT 'pending'    -- pending | selected | rendered | failed | skipped
  error_detail      TEXT                      -- set when nav_status = failed
  chunk_count       INT NOT NULL DEFAULT 0    -- number of chunks produced from this page after rendering
```

## 11.16 Prompt Contracts

The ingestion pipeline's LLM stages depend on three prompts: triage, task extraction, and principle extraction. These prompts are the platform's contract with the LLM — they determine whether extracted candidates are useful, conformant, and safe to surface to operators. They are treated as code, not configuration.

### Storage

Prompts live in version-controlled markdown files under `prompts/ingestion/`:

```
prompts/
  ingestion/
    triage.md
    extract_task.md
    extract_principle.md
```

Each file is a self-contained prompt with its system message, output schema, and at least one known-good example. Files are loaded by code at startup. No inline prompt strings exist in the Python source.

### File structure

Each prompt file follows the same structure:

```
# {Prompt Name}

**Purpose:** one-paragraph statement of what this prompt does and where it fits in the pipeline.

**Input contract:** what the calling code provides — variables interpolated into the user message,
expected formatting, length limits.

**Output schema:** the JSON shape expected back, with field types and required/optional markers.

## System Prompt

[the system message verbatim]

## User Message Template

[the user message template with variable placeholders]

## Known-Good Example

Input: [an example chunk]
Output: [the JSON the prompt should produce]
```

### Loading

A `prompts.py` module exposes a `load(stage: str) -> Prompt` function. The `Prompt` object exposes `system`, `user_template`, and a `render(**kwargs)` method that performs variable substitution and returns the message pair ready for the LLM client. The module reads files at import time and caches them.

### Operator visibility

Operators cannot edit prompts in v1. Prompts ship with the platform release and change only via platform upgrade. The Admin UI displays the active prompt files for each stage as read-only content, sourced from disk, so that operators understand what is being sent to their configured LLM providers. This transparency requirement is non-negotiable — operators paying for LLM tokens must be able to see what is being sent.

### Operator-editable prompts (v1.1+)

Operator-editable prompts are a planned v1.1 feature. The shape under consideration:

- Operators can override platform-shipped prompts per pipeline stage via the Admin UI
- Overrides are stored in `system_settings` (or a dedicated `prompt_overrides` table)
- Active prompt source recorded per `ingestion_chunk` for audit traceability
- Overrides survive platform upgrades; platform updates to the default prompt are surfaced to operators with a diff view

v1 deliberately ships without this. The complexity of override storage, upgrade-time diff surfacing, and audit traceability is non-trivial, and shipping it half-built creates the worst of both worlds.

### Prompt versioning

Prompts are versioned via git history. Each prompt file's commit history is the authoritative change log. No separate `prompt_version` field is recorded on `ingestion_chunks` in v1 — the active git SHA at the time of platform release defines the prompt version for all chunks processed in that release window. This collapses to a per-chunk version field if and when operator overrides arrive in v1.1.

### Prompt design principles

Prompts that are added or modified must satisfy:

1. **Strict output schema.** Every prompt declares a JSON-only output schema, and the schema is validated at parse time. Invalid responses are treated as extraction failures and surfaced to the operator, not silently retried.
2. **Embedded known-good example.** Each prompt contains at least one fully-worked example of the kind of output expected. The example is in the prompt body, not just the documentation, because that is where it does the actual grounding work for the model.
3. **Explicit invent-prohibition.** Each extraction prompt instructs the model not to invent content not present in the source. This is the single most important defence against hallucinated tasks, facts, or concepts.
4. **No em dashes.** Each prompt explicitly forbids em dashes in output. This is a Blueprinted house-style decision propagated to extracted content from day one.
5. **Field-by-field guidance.** Extraction prompts include precise definitions of each field, with good-and-bad examples for fields that are commonly misinterpreted (the `concepts` field is the canonical example — generic explanations of the product are wrong; task-specific reasons-this-task-exists are right).

Prompts that pass these criteria can be added without further spec change. Substantive changes to existing prompts require a worklog entry justifying the change.

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
  ?type=string        Comma-separated record types: task,workflow,principle
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
```

---

# 14. Background Job Processing

**Framework:** ARQ + Redis

**Workers (v4.11):** Two worker processes, same codebase, different entrypoints. The default worker (`workers.main.WorkerSettings`, default queue) owns embedding generation and the review-claim-expiry cron. The ingestion worker (`workers.ingestion.WorkerSettings`, queue `ingestion`) owns `chunk_pdf`, `process_chunks`, `extract_chunk`, `crawl_html`, `render_nav_pages` — isolating long-running LLM work from fast jobs. Every enqueue of an ingestion job must pass `_queue_name="ingestion"`; an ARQ worker fails jobs whose function it does not have registered, so queue routing is part of the job contract.

**Durability:** Jobs are persisted in Redis before execution. If the worker process dies before a job begins executing, the job remains in the Redis queue and will be picked up when the worker restarts. Jobs that were mid-execution when the worker died are a different case — see Resumability below.

**Resumability:** ARQ does not natively resume a partially-executed job. If the worker dies mid-execution, ARQ's default behaviour is to mark the job as failed. Resumability for ingestion jobs is a property of the application code, not the framework.

This is implemented as follows:

- Each ingestion job function begins by querying chunk_status and processing only chunks in `queued` state
- Chunks in `processing` state when the worker died represent in-flight LLM calls that were lost. A worker startup hook resets any `processing` chunks to `queued` with a `worker_restart` note in the chunk error field
- This means a worker restart may re-process a chunk whose LLM call completed but whose result was never written — acceptable, as extraction is idempotent from the operator's perspective
- Chunks in `done`, `error`, or `skipped` state are never re-processed

**The startup hook is not optional.** Without it, chunks left in `processing` state after a worker crash are silently skipped on resume, producing an ingestion job that appears complete but is missing candidates. This is a data loss scenario. Mark the startup hook clearly in code — it is load-bearing and must not be removed during refactoring. As of v4.11 it runs on the ingestion worker only (the recovery targets ingestion chunks; running it twice would double-enqueue orphaned extraction jobs).

New system_settings keys introduced by §11: `ingestion_pdf_chunk_size_chars` (default 4000, fallback chunk size when no PDF structure detected), `ingestion_html_respect_robots_txt` (default true, controls whether HTML ingestion observes robots.txt).

| Job | Trigger |
| --- | --- |
| PDF chunking / HTML rendering / JSON validation | Ingestion job submitted |
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

## 19.1 blueprinted-io/platform — Backend Monorepo

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
| Profile | All roles | GET /api/v1/users/me |

**Profile ownership:** Authentik owns identity — name, email, password, and profile photo (`picture` JWT claim). The platform profile page is read-only in v1, displaying what the JWT provides. Platform-specific preferences (notification preferences, UI preferences) are deferred to v1.1. `PATCH /api/v1/users/me` is deferred until platform-owned fields are specified. Profile photo upload to platform storage is a v1.1 item; v1 reads the `picture` claim from the JWT if present.

## 23.2 Dashboard

| Screen | Role | Primary API Calls |
| --- | --- | --- |
| Home dashboard (role-aware) | All roles | GET /api/v1/analytics/dashboard (deferred) |

**Dashboard stub:** The dashboard is a placeholder in v0.x. The MVP had fixed role-specific layouts (Admin: throughput/cycle time/review velocity/intervention rates; Contributor: work completed and outstanding). The v1 production version will support customisable layouts with standard role-default configurations. `GET /api/v1/analytics/dashboard` and the analytics subsystem are not implemented until the component inventory and layout model are fully specified. See §24.

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

## 23.5 Facts and Concepts — Removed (v4.4)

Facts and Concepts no longer exist as independently governed records. They are authored inline on the Task create/edit screen as string arrays. No standalone screens. See v4.4 changelog.

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
| HTML upload (single page or site-nav crawl) | Contributor, Admin | POST /api/v1/ingestions/html |
| Nav discovery results (site-nav crawl only) | Contributor, Admin | GET /api/v1/ingestions/{id}/nav-pages |
| Nav page selection (site-nav crawl only) | Contributor, Admin | POST /api/v1/ingestions/{id}/nav-select |
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

*Note: Achievements screen exists in the screen inventory but behaviour is unspecified in v1 — stub only. Export screens exist in the MVP but are absent from v1. Tenant management and API key management are Sprint 10. Audit log is Sprint 10 (table does not exist yet). Dashboard analytics endpoint is deferred pending component specification (§23.2).*

---

# 24. Parked Decisions

- *Go rebuild — triggered if scale demands single-binary deployment or Python performance bottlenecks*
- *Neo4j migration — triggered if graph traversal complexity exceeds PostgreSQL recursive CTE capability*
- *Delivery product architecture and naming — AI-native learning experience layer, not an LMS*
- *Performance-based assessment — future module, potentially separate product*
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
- *LLM-assisted image-to-step association during ingestion — v1.1. In v1, images are attached to steps manually post-ingestion. The MVP demonstrated this is reliably achievable via LLM; complexity deferred until core ingestion is stable.*
- *Dashboard analytics subsystem — deferred pending component inventory and layout model specification. The MVP had fixed role-specific layouts; the production version will support customisable layouts with role-default configurations. No implementation until the component model is specified.*
- *Profile PATCH and platform-owned preferences — deferred to v1.1. Authentik owns identity (name, email, photo). Platform-specific preferences (notification prefs, UI prefs, display name override) await preference model specification.*
- *Profile photo upload to platform storage — v1.1. v1 reads the `picture` JWT claim from Authentik if present.*
- *IdP role configuration operator docs — a generic "configuring Blueprinted roles at your identity provider" guide covering Authentik (default), Entra ID, Okta, and Keycloak. The five roles and their meanings, plus how to express them as app roles / groups and emit them as a JWT claim. Blocks enterprise deployment self-service.*
- *Workflow-first authoring mode — UI to support creating a workflow, stubbing tasks from within it, and filling them in from there. Data model already supports it; frontend change only. See §9.9.*
- *Seeded documentation tenant — post-v1 demonstration project. v1 ships with markdown docs.*
- *agent:relationship_suggester role — v1.1, alongside first relationship kind definition*
- *Export artifacts and SHA256 fingerprinting — v1.1. Workflow bundle export with per-export SHA256 fingerprint stored in export_artifacts table. Enables audit of what was shared and verification of bundle integrity by recipients. Table exists as stub; no endpoints or UI in v1.*

---

# 25. Key Decisions Log

| Decision | Rationale |
| --- | --- |
| Python over Go | Personal project timeline, strong AI assistance. Go remains future option. |
| PostgreSQL over Neo4j | Operational simplicity for self-hosted. Graph semantics in data model from day one. |
| Schema-per-tenant | Hard isolation at DB layer. Forward bet on SaaS optionality. Acknowledged complexity for single-tenant v1 installs. |
| Facts and Concepts dissolved (v4.4) | Independent governance lifecycle created maintenance overhead disproportionate to value. Task is the atomic unit — facts and concepts are string arrays on the task, revised when the task is revised. |
| No machine can confirm | Human confirmation of governed knowledge is non-negotiable. Enforced at confirm endpoints, not at credential layer. |
| Claiming not assigning | Self-organising review queue. No bottlenecks, scales naturally. Admin break-glass for small teams. |
| Principles not Primers | Principle implies foundational and enduring. Primer implies introductory and temporary. |
| Dependencies dissolved | Most dependencies are facts or relationship edges. No separate table needed. |
| Ingestion in backend monorepo | Ingestion is core to the platform. Hard-separated internally via API. |
| ARQ over BackgroundTasks | BackgroundTasks loses jobs on restart. Large PDF ingestion cannot silently disappear. |
| pgvector from day one | Justified by semantic search across tasks, workflows, and principles. Single dependency. |
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
| Domain as soft-deletable slug registry | Replicates MVP pattern. Hard delete orphans existing records. Domain name stored as free-text slug on records, not a DB FK — application-enforced at write time. Disabled domains remain on historical records for audit integrity. |
| No hard delete on governed records | The governed record lifecycle is append-only by design. Hard delete would break audit trail integrity. Test data and ingestion errors are corrected by retiring or deprecating records, not deleting them. Direct DB access is the intentional escape hatch for exceptional cases. |
| No `force_submit` admin override | MVP had `force_submit` to paper over missing domain assignment at create time. Platform requires domain at create — the original use case no longer exists. Genuine admin override is covered by break-glass confirm. `force_submit` would bypass the contributor governance step with no compensating check. |
| Export fingerprinting deferred to v1.1 | SHA256 fingerprinting of exported workflow bundles is a governance audit feature, not cosmetic. Deferred because the export endpoint itself is v1.1 — fingerprinting without an export surface has no value. Both ship together. |
| Admin break-glass requires justification + scar flag | `self_confirmed_by_admin` flag added to shared lifecycle fields. Confirm endpoint requires non-empty justification when admin confirms own content. Audit log entry deferred until `audit_log` table exists in Sprint 10. |
| `record_id` ref columns are application-enforced not DB FK | `record_id` is not unique across versions. DB-level FK cannot reference it. Application validates existence of a confirmed record with that `record_id` before inserting into ref tables. |
| PKCE frontend flow deferred to Sprint 8 | blueprinted-io/app repository did not exist during Sprint 2. Backend JWT validation tested with mock JWTs. PKCE implemented when React frontend exists. |

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

*blueprinted.io · github.com/blueprinted-io/platform · AGPL 3.0*

*Requirements Specification v4.2 · May 2026*