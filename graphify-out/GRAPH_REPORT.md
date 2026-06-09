# Graph Report - platform  (2026-06-09)

## Corpus Check
- 136 files · ~132,648 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1233 nodes · 2538 edges · 94 communities (77 shown, 17 thin omitted)
- Extraction: 85% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 368 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Ingestion Tests|Ingestion Tests]]
- [[_COMMUNITY_Ingestion API & Routes|Ingestion API & Routes]]
- [[_COMMUNITY_Auth & Project Config|Auth & Project Config]]
- [[_COMMUNITY_Auth Dependencies & Audit|Auth Dependencies & Audit]]
- [[_COMMUNITY_Test Infrastructure & API Keys|Test Infrastructure & API Keys]]
- [[_COMMUNITY_Admin Tests|Admin Tests]]
- [[_COMMUNITY_Record Schemas|Record Schemas]]
- [[_COMMUNITY_Admin Settings Service|Admin Settings Service]]
- [[_COMMUNITY_Task Domain|Task Domain]]
- [[_COMMUNITY_Review Queue Tests|Review Queue Tests]]
- [[_COMMUNITY_Ingestion Models|Ingestion Models]]
- [[_COMMUNITY_Test Factories|Test Factories]]
- [[_COMMUNITY_Database & Core Models|Database & Core Models]]
- [[_COMMUNITY_Workflow Domain|Workflow Domain]]
- [[_COMMUNITY_Triage Estimate Tests|Triage Estimate Tests]]
- [[_COMMUNITY_Lifecycle State Machine|Lifecycle State Machine]]
- [[_COMMUNITY_Principle Domain & Notifications|Principle Domain & Notifications]]
- [[_COMMUNITY_Ingestion Test Rationale|Ingestion Test Rationale]]
- [[_COMMUNITY_Ingestion Schemas|Ingestion Schemas]]
- [[_COMMUNITY_Search Service|Search Service]]
- [[_COMMUNITY_Search Tests|Search Tests]]
- [[_COMMUNITY_Request Dependencies|Request Dependencies]]
- [[_COMMUNITY_Machine Auth & API Keys|Machine Auth & API Keys]]
- [[_COMMUNITY_CLI Commands|CLI Commands]]
- [[_COMMUNITY_Triage Estimate Routes|Triage Estimate Routes]]
- [[_COMMUNITY_Workflow Tests|Workflow Tests]]
- [[_COMMUNITY_Test Auth Stubs|Test Auth Stubs]]
- [[_COMMUNITY_Notification Tests|Notification Tests]]
- [[_COMMUNITY_Token Verification|Token Verification]]
- [[_COMMUNITY_Worker Process Tests|Worker Process Tests]]
- [[_COMMUNITY_Module Group 30|Module Group 30]]
- [[_COMMUNITY_Module Group 31|Module Group 31]]
- [[_COMMUNITY_Module Group 32|Module Group 32]]
- [[_COMMUNITY_Module Group 33|Module Group 33]]
- [[_COMMUNITY_Module Group 34|Module Group 34]]
- [[_COMMUNITY_Module Group 35|Module Group 35]]
- [[_COMMUNITY_Module Group 36|Module Group 36]]
- [[_COMMUNITY_Module Group 37|Module Group 37]]
- [[_COMMUNITY_Module Group 38|Module Group 38]]
- [[_COMMUNITY_Module Group 39|Module Group 39]]
- [[_COMMUNITY_Module Group 40|Module Group 40]]
- [[_COMMUNITY_Module Group 41|Module Group 41]]
- [[_COMMUNITY_Module Group 42|Module Group 42]]
- [[_COMMUNITY_Module Group 43|Module Group 43]]
- [[_COMMUNITY_Module Group 44|Module Group 44]]
- [[_COMMUNITY_Module Group 45|Module Group 45]]
- [[_COMMUNITY_Module Group 46|Module Group 46]]
- [[_COMMUNITY_Module Group 47|Module Group 47]]
- [[_COMMUNITY_Module Group 48|Module Group 48]]
- [[_COMMUNITY_Module Group 49|Module Group 49]]
- [[_COMMUNITY_Module Group 50|Module Group 50]]
- [[_COMMUNITY_Module Group 51|Module Group 51]]
- [[_COMMUNITY_Module Group 52|Module Group 52]]
- [[_COMMUNITY_Module Group 53|Module Group 53]]
- [[_COMMUNITY_Module Group 54|Module Group 54]]
- [[_COMMUNITY_Module Group 55|Module Group 55]]
- [[_COMMUNITY_Module Group 56|Module Group 56]]
- [[_COMMUNITY_Module Group 57|Module Group 57]]
- [[_COMMUNITY_Module Group 58|Module Group 58]]
- [[_COMMUNITY_Module Group 59|Module Group 59]]
- [[_COMMUNITY_Module Group 70|Module Group 70]]
- [[_COMMUNITY_Module Group 71|Module Group 71]]
- [[_COMMUNITY_Module Group 72|Module Group 72]]
- [[_COMMUNITY_Module Group 73|Module Group 73]]
- [[_COMMUNITY_Module Group 74|Module Group 74]]
- [[_COMMUNITY_Module Group 75|Module Group 75]]
- [[_COMMUNITY_Module Group 76|Module Group 76]]
- [[_COMMUNITY_Module Group 77|Module Group 77]]
- [[_COMMUNITY_Module Group 78|Module Group 78]]
- [[_COMMUNITY_Module Group 84|Module Group 84]]
- [[_COMMUNITY_Module Group 86|Module Group 86]]
- [[_COMMUNITY_Module Group 89|Module Group 89]]
- [[_COMMUNITY_Module Group 90|Module Group 90]]
- [[_COMMUNITY_Module Group 91|Module Group 91]]
- [[_COMMUNITY_Module Group 92|Module Group 92]]
- [[_COMMUNITY_Module Group 93|Module Group 93]]

## God Nodes (most connected - your core abstractions)
1. `make_token()` - 188 edges
2. `create_engine()` - 50 edges
3. `Base` - 41 edges
4. `LifecycleResponse` - 36 edges
5. `Settings` - 30 edges
6. `task_payload()` - 29 edges
7. `Requirements Specification v4.7 (Current)` - 29 edges
8. `_create_and_submit_task()` - 22 edges
9. `_make_ingestion_with_triage_complete_chunk()` - 21 edges
10. `_admin_headers()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `WorkerSettings` --uses--> `Settings`  [INFERRED]
  workers/main.py → api/config.py
- `WorkerSettings` --uses--> `ReviewClaim`  [INFERRED]
  workers/main.py → api/models/review_claim.py
- `WorkerSettings` --uses--> `SystemSetting`  [INFERRED]
  workers/main.py → api/models/settings.py
- `WorkerSettings` --uses--> `Prompt`  [INFERRED]
  workers/main.py → api/prompts.py
- `run_migrations_online()` --calls--> `create_engine()`  [INFERRED]
  migrations/env.py → api/database.py

## Communities (94 total, 17 thin omitted)

### Community 0 - "Ingestion Tests"
Cohesion: 0.03
Nodes (75): _pdf_bytes(), _pdf_upload(), Tests for the Ingestion Pipeline API (§11).  Spec refs:   §11.3  Ingestion pipel, force=true bypasses dedup and creates a new ingestion record., Insert a minimal HTML ingestion row., Insert a minimal ingestion_nav_pages row., A page already in selected status is not re-queued., A task item missing a required field is rejected with 422. (+67 more)

### Community 1 - "Ingestion API & Routes"
Cohesion: 0.09
Nodes (56): IngestionNavPage, Discovered navigable page from an HTML site-nav crawl (§11.15)., healthz(), GET /healthz — public endpoint, no auth required.  Checks database connectivity, str, _embedding_response(), _get_embedding(), _make_ctx() (+48 more)

### Community 2 - "Auth & Project Config"
Cohesion: 0.06
Nodes (55): Authentik OIDC Provider Configuration, Blueprinted Roles Property Mapping, Authentik Setup Guide, Project Index (CLAUDE.md), API Keys Table Schema, ARQ Resumability via Application Checkpoints, Audit Log, Break-Glass Admin Confirm (+47 more)

### Community 3 - "Auth Dependencies & Audit"
Cohesion: 0.07
Nodes (42): Dependency factory that enforces role membership.      Usage:         @router.ge, require_role(), ReviewClaim, list_audit_log(), Audit log read endpoint (§9.6, §5.1).  GET /audit   Audit role only, paginated,, Return audit log entries, newest first. Accessible by Audit and Admin roles., claim_item(), _collect_queue_items() (+34 more)

### Community 4 - "Test Infrastructure & API Keys"
Cohesion: 0.07
Nodes (33): make_token(), Factory that produces signed RS256 JWTs for testing., Tests for scoped API key management and machine credential auth (§5.3, §9.6)., A valid bp_ key authenticates and can call read endpoints., A bp_ API key is rejected with 403 at any confirm endpoint., test_api_key_authenticates_for_data_endpoint(), test_create_api_key_invalid_role_returns_422(), test_create_api_key_returns_201_with_raw_key() (+25 more)

### Community 5 - "Admin Tests"
Cohesion: 0.08
Nodes (31): _admin_headers(), Tests for the Admin API (§23.11).  Spec refs:   §23.11  Admin endpoints — settin, test_create_domain_admin_returns_201(), test_create_domain_duplicate_returns_409(), test_create_domain_viewer_returns_403(), test_disable_domain_already_disabled_returns_409(), test_disable_nonexistent_domain_returns_404(), test_disable_then_enable_domain() (+23 more)

### Community 6 - "Record Schemas"
Cohesion: 0.12
Nodes (35): BaseModel, LifecycleResponse, Base response schema carrying the shared identity and lifecycle fields., PrincipleCreate, PrincipleResponse, PrincipleUpdate, PrincipleVersionSummary, Principle request and response schemas. (+27 more)

### Community 7 - "Admin Settings Service"
Cohesion: 0.08
Nodes (30): SystemSetting ORM model (§10.4)., SystemSetting, admin_health(), create_domain(), disable_domain(), enable_domain(), _get_domain_or_404(), patch_settings() (+22 more)

### Community 8 - "Task Domain"
Cohesion: 0.10
Nodes (27): Task, TaskStep, TaskStepAction, _build_steps(), _build_task(), commit_candidate(), Construct a Task ORM object (without steps) from extraction JSON., Attach TaskStep and TaskStepAction children to a Task. (+19 more)

### Community 9 - "Review Queue Tests"
Cohesion: 0.10
Nodes (28): _create_and_submit_task(), Tests for the Review Queue and Claiming API.  TEST_REVISED (v4.4 — dissolve Fact, All record types are domain-scoped; no-domain contributor sees nothing., An expired claim should not appear as an active claim on queue items., Create a draft task and submit it. Returns the task UUID string., test_claim_already_claimed_by_another_returns_409(), test_claim_draft_task_returns_422(), test_claim_invalid_entity_type_returns_422() (+20 more)

### Community 10 - "Ingestion Models"
Cohesion: 0.11
Nodes (24): IngestionCandidate, IngestionChunk, IngestionTriageEstimate, ORM models for the ingestion pipeline tables (SS11.13-SS11.15, SS11.8a)., LLM-generated candidate estimate for a chunk, reviewed before extraction runs (§, One structural section of an ingested source document (§11.14)., LLM-extracted candidate record awaiting human review (§11.8)., Read a previously stored ingestion file. (+16 more)

### Community 11 - "Test Factories"
Cohesion: 0.15
Nodes (25): Minimal valid request payload factories for governed record tests.  Each factory, task_payload(), task_step_action_payload(), task_step_payload(), Tests for the Tasks lifecycle API.  TEST_REVISED (v4.4/v4.5 — dissolve Facts/Con, task.irreversible is derived: True when any step is irreversible., Confirmed tasks are immutable — steps cannot be added after confirmation., test_add_irreversible_step_marks_task_irreversible() (+17 more)

### Community 12 - "Database & Core Models"
Cohesion: 0.12
Nodes (16): Base, Shared declarative base for all ORM models., DeclarativeBase, AuditLog, AuditLog ORM model (§9.6)., Domain, Domain and UserDomain ORM models.  §7.1 — domain registry and user assignment, UserDomain (+8 more)

### Community 13 - "Workflow Domain"
Cohesion: 0.15
Nodes (19): Workflow ORM models.  §9.5 — ordered sequence of Tasks with attached Principles., Workflow, WorkflowPrincipleRef, WorkflowTaskRef, add_task_ref(), attach_principle(), confirm_workflow(), create_workflow() (+11 more)

### Community 14 - "Triage Estimate Tests"
Cohesion: 0.24
Nodes (24): _auth(), _make_ingestion_with_triage_complete_chunk(), Tests for triage estimate review endpoints (§11.5a).  Spec refs:   §11.5a Triage, Seed an ingestion + chunk in triage_complete state; return (ingestion_id, chunk_, Insert estimate rows and return their IDs in order., _seed_estimates(), test_approve_all_rejected_moves_chunk_to_done(), test_approve_estimates_marks_approved() (+16 more)

### Community 15 - "Lifecycle State Machine"
Cohesion: 0.12
Nodes (23): is_machine_credential(), Return True if all roles in the list are agent-prefixed (§5.3)., assert_can_confirm(), assert_can_deprecate(), assert_can_mutate_refs(), assert_can_retire(), assert_can_return(), assert_can_revise() (+15 more)

### Community 16 - "Principle Domain & Notifications"
Cohesion: 0.14
Nodes (20): Notification, Principle, confirm_principle(), create_principle(), deprecate_principle(), _get_or_404(), get_principle(), Principles API endpoints. (+12 more)

### Community 17 - "Ingestion Test Rationale"
Cohesion: 0.13
Nodes (24): Nav pages endpoint rejects non-HTML ingestions., Insert a minimal ingestion row owned by user_id., Insert a minimal ingestion_candidates row., Candidate list for another user's ingestion is opaque 404., Cannot commit a candidate that has not been accepted., A contributor not assigned to the domain gets 403., _seed_candidate(), _seed_ingestion() (+16 more)

### Community 18 - "Ingestion Schemas"
Cohesion: 0.09
Nodes (17): CandidateCommitRequest, CandidateCommitResponse, HtmlIngestionRequest, IngestionCandidateResponse, IngestionChunkResponse, JsonIngestionRequest, JsonStepItem, NavSelectRequest (+9 more)

### Community 19 - "Search Service"
Cohesion: 0.14
Nodes (19): Search API endpoint (§12.2).  GET /api/v1/search  — full-text and optional seman, Search across all governed record types.      Full-text search is always perform, search_records(), Search API schemas (§12.2)., SearchResponse, SearchResult, _active_configs(), _fts_leg() (+11 more)

### Community 20 - "Search Tests"
Cohesion: 0.13
Nodes (20): _make_confirmed_task(), Tests for GET /api/v1/search (§12.2).  TEST_REVISED (v4.4 — dissolve Facts/Conce, Unknown type tokens in the filter are silently ignored (not a 422)., ?semantic=true with no embedding config falls back to fulltext gracefully., Confirmed records should not appear when searching for draft status., Create, submit, and confirm a Task containing the search keyword. Returns its id, test_domain_filter_non_matching_domain_returns_no_task(), test_search_empty_q_returns_422() (+12 more)

### Community 21 - "Request Dependencies"
Cohesion: 0.12
Nodes (15): _authenticate_api_key(), get_arq_pool(), get_current_user(), get_db_session(), get_token_verifier(), FastAPI dependency providers., Validate Bearer token (JWT or bp_ API key) and return the authenticated user., Yield a database session from the factory stored on app.state. (+7 more)

### Community 22 - "Machine Auth & API Keys"
Cohesion: 0.16
Nodes (18): AgentRole, Machine credential roles as defined in §5.2. Available from Sprint 10., create_api_key(), _generate_key(), list_api_keys(), Admin API key management endpoints (§5.3, §9.6).  GET    /admin/api-keys, Revoke an API key. Immediate effect — any bearer using this key gets 401., Return (raw_key, key_prefix, key_hash). (+10 more)

### Community 23 - "CLI Commands"
Cohesion: 0.10
Nodes (19): api_keys_create(), api_keys_revoke(), backup(), healthcheck(), migrate(), Blueprinted CLI — all operational tasks for a running instance.  Usage:     blue, Register a new tenant schema and run its migrations., Remove a tenant schema. Irreversible — take a backup first. (+11 more)

### Community 24 - "Triage Estimate Routes"
Cohesion: 0.16
Nodes (17): approve_estimates(), _get_chunk_or_404(), list_estimates(), merge_estimates(), patch_estimate(), Triage estimate review endpoints (§11.5a).  GET    /ingestions/{id}/chunks/{chun, Merge multiple estimates into one (§11.5a).      The first estimate in the list, Approve pending estimates, moving the chunk to extraction_queued (§11.5a). (+9 more)

### Community 25 - "Workflow Tests"
Cohesion: 0.19
Nodes (18): workflow_payload(), Tests for the Workflows lifecycle API.  Spec refs:   §9.3  Lifecycle state machi, Only confirmed Tasks may be referenced in a Workflow., test_add_confirmed_task_ref_to_workflow(), test_add_task_ref_to_confirmed_workflow_returns_422(), test_add_unconfirmed_task_ref_returns_422(), test_attach_confirmed_principle_to_workflow(), test_attach_unconfirmed_principle_returns_422() (+10 more)

### Community 26 - "Test Auth Stubs"
Cohesion: 0.13
Nodes (13): TokenVerifier for tests — verifies against a supplied RSA public key.      No HT, StubTokenVerifier, client(), pytest fixtures for the Blueprinted test suite.  Test DB setup runs via asyncio., Pre-seed the test domain and all contributor users with domain assignments., Async HTTP client with lifespan started and StubTokenVerifier installed., Test stub for arq.connections.ArqRedis. Records calls without touching Redis., Create all ORM tables once per session, outside the async event loop. (+5 more)

### Community 27 - "Notification Tests"
Cohesion: 0.29
Nodes (13): _delete_notifications_for(), _insert_notification(), Tests for the Notifications API (§13).  Spec refs:   §13  Notifications — list,, _seed_users(), test_list_notifications_empty_for_new_user(), test_list_notifications_returns_own_notifications(), test_list_notifications_unread_only_filter(), test_mark_all_read_only_affects_own_notifications() (+5 more)

### Community 28 - "Token Verification"
Cohesion: 0.15
Nodes (12): Return the roles list from claims, defaulting to empty., Verifies RS256 JWTs against a JWKS endpoint.      Fetches and caches JWKS on fir, TokenVerifier, create_session_factory(), configure_logging(), structlog configuration — JSON output, request ID propagation.  Call configure_l, Strip known secret field names from log events before output., Configure structlog for JSON output. Call once at startup. (+4 more)

### Community 29 - "Worker Process Tests"
Cohesion: 0.17
Nodes (10): Tests for the process_chunks ARQ job, _triage_chunk, extract_chunk, and helpers., test_validate_principle_missing_field(), test_validate_principle_valid(), test_validate_task_empty_steps(), test_validate_task_missing_field(), test_validate_task_valid(), Return an error string if the task candidate is missing required fields., Return an error string if the principle candidate is missing required fields. (+2 more)

### Community 30 - "Module Group 30"
Cohesion: 0.27
Nodes (15): apply_files(), call_model(), extract_paths(), fix_general(), fix_pip_audit(), get_logs(), log(), main() (+7 more)

### Community 31 - "Module Group 31"
Cohesion: 0.24
Nodes (15): create_engine(), _get_candidates(), _insert_extraction_queued_chunk(), _make_env_settings(), _principle_extraction_json(), Insert chunk at extraction_queued with one approved estimate.      Returns (inge, A task missing required fields gets candidate_status='invalid', chunk still done, Return a Settings with LLM configured for use in ARQ ctx dicts. (+7 more)

### Community 32 - "Module Group 32"
Cohesion: 0.14
Nodes (14): delete_ingestion(), get_ingestion_status(), list_candidates(), list_ingestions(), list_nav_pages(), Ingestion pipeline API endpoints (§11).  PDF upload, HTML URL, JSON payload, chu, List ingestions created by the current user, newest first., Return ingestion with its full chunk list (§11.5 section selection screen). (+6 more)

### Community 33 - "Module Group 33"
Cohesion: 0.24
Nodes (14): principle_payload(), Tests for the Principles lifecycle API.  Spec refs:   §9.3  Lifecycle state mach, test_create_principle_contributor_returns_201_draft(), test_create_principle_missing_summary_returns_422(), test_create_principle_response_has_required_fields(), test_create_principle_unauthenticated_returns_401(), test_create_principle_viewer_returns_403(), test_create_principle_with_domain() (+6 more)

### Community 34 - "Module Group 34"
Cohesion: 0.15
Nodes (5): get_settings(), Bootstrap configuration loaded from environment variables.  Runtime configuratio, Settings, Async SQLAlchemy engine and session management., BaseSettings

### Community 35 - "Module Group 35"
Cohesion: 0.32
Nodes (14): _chat_response(), _get_chunk(), _get_estimates(), _insert_queued_chunk(), Insert a minimal ingestion and a queued chunk. Returns (ingestion_id, chunk_id)., process_chunks triages all queued chunks and skips non-queued ones., Build a minimal chat completions response., test_process_chunks_with_llm_processes_all_queued() (+6 more)

### Community 36 - "Module Group 36"
Cohesion: 0.19
Nodes (13): JSON Import Schema v1, Manual JSON Authoring Guide, Extract Principle Prompt, Extract Task Prompt, Triage Category Classification, Triage Prompt, Changelog Propose Prompt (v1.1), Changelog Screen Prompt (v1.1) (+5 more)

### Community 37 - "Module Group 37"
Cohesion: 0.17
Nodes (11): LLMSettings, load_llm_settings(), Load LLM config from system_settings, falling back to env Settings.      The per, Resolved LLM configuration loaded from system_settings (per-job resolver)., llm_settings(), Resolved LLM settings for direct calls to _triage_chunk., test_process_chunks_no_llm_marks_done(), process_chunks() (+3 more)

### Community 38 - "Module Group 38"
Cohesion: 0.29
Nodes (8): _make_raw(), Tests for JWT token verification logic., test_expired_token_raises(), test_extract_roles_returns_list(), test_tampered_token_raises(), test_valid_token_decodes(), test_wrong_audience_raises(), test_wrong_issuer_raises()

### Community 39 - "Module Group 39"
Cohesion: 0.40
Nodes (10): _get_chunk_status(), _insert_ingestion_and_chunk(), Tests for the ARQ worker startup hook (§14, issue 5).  Covers:   - processing →, test_startup_populates_ctx(), test_startup_reenqueues_extraction_queued_chunks(), test_startup_resets_extracting_to_extraction_queued(), test_startup_resets_processing_to_queued(), test_startup_skips_reenqueue_without_redis() (+2 more)

### Community 40 - "Module Group 40"
Cohesion: 0.22
Nodes (9): load(), _load_all(), _parse_prompt_file(), Prompt, Prompt loading for the ingestion pipeline (§11.16).  Reads versioned markdown fi, A loaded prompt ready to be rendered into a message pair., Return (system_message, user_message) with variables substituted., Extract system and user_template text from a prompt markdown file. (+1 more)

### Community 41 - "Module Group 41"
Cohesion: 0.18
Nodes (9): list_notifications(), mark_all_read(), mark_read(), Notifications API endpoints (§13)., Return the current user's notifications, newest first., Mark a single notification as read., Mark all unread notifications for the current user as read., NotificationResponse (+1 more)

### Community 42 - "Module Group 42"
Cohesion: 0.20
Nodes (10): Ingestion, Ingestion job record — one per uploaded PDF, HTML source, or JSON payload (§11.1, _canonical_json(), create_html_ingestion(), create_json_ingestion(), _normalise_url(), Lowercase scheme+host, strip fragment, sort query params for stable dedup., Submit a URL for HTML ingestion (§11.10).      Single-page mode renders one URL (+2 more)

### Community 43 - "Module Group 43"
Cohesion: 0.25
Nodes (8): create_ingestion(), Strip path components and replace unsafe characters., Upload a PDF and start the chunking job (§11.9)., _sanitise_filename(), _ingestion_dir(), File storage abstraction (§4.4).  v1 implements local-disk storage only. The int, Write uploaded file to local storage. Returns (storage_path, sha256_hex)., save_ingestion_file()

### Community 44 - "Module Group 44"
Cohesion: 0.32
Nodes (8): Docker Compose Production Stack, MinIO S3-Compatible Storage, Docker Compose Dev Override, Blueprinted.io Brand Logo, Authentik OIDC Provider, Docker Compose Stack, Local Dev Setup Guide, Playwright Chromium for HTML Ingestion

### Community 45 - "Module Group 45"
Cohesion: 0.25
Nodes (7): args, command, args, command, mcpServers, context7, github

### Community 46 - "Module Group 46"
Cohesion: 0.25
Nodes (6): get_me(), User profile endpoints., Return the authenticated user's profile., Pydantic schemas for user API responses., Response schema for GET /api/v1/users/me., UserResponse

### Community 47 - "Module Group 47"
Cohesion: 0.29
Nodes (4): Request ID middleware and security headers., Attach a unique request ID to every request and response.      Binds the ID to s, RequestIDMiddleware, BaseHTTPMiddleware

### Community 48 - "Module Group 48"
Cohesion: 0.29
Nodes (3): Relationships API endpoints. §9.4, §23.9  All writes rejected with HTTP 422 in v, Relationship response schema. §9.4, RelationshipResponse

### Community 49 - "Module Group 49"
Cohesion: 0.38
Nodes (6): get_url(), Alembic migration environment.  Uses the synchronous psycopg2 driver for CLI mig, Run migrations without a live database connection (generates SQL)., Run migrations against a live database connection., run_migrations_offline(), run_migrations_online()

### Community 50 - "Module Group 50"
Cohesion: 0.29
Nodes (3): LifecycleMixin, Shared identity and lifecycle mixin for all governed record ORM models.  §9.1 —, Shared identity and lifecycle columns inherited by all governed record tables.

### Community 51 - "Module Group 51"
Cohesion: 0.40
Nodes (4): Raised when a JWT cannot be verified., Decode and verify a JWT. Returns the verified claims dict.          Raises Token, TokenVerificationError, Exception

### Community 52 - "Module Group 52"
Cohesion: 0.47
Nodes (5): api(), main(), psql(), Development seed script — populates the local dev database with realistic tasks., Run SQL directly via docker exec — used only for domain bootstrap.

### Community 53 - "Module Group 53"
Cohesion: 0.50
Nodes (4): OIDC token verification.  TokenVerifier validates RS256 JWTs issued by Authentik, Human roles as defined in §5.1., Role, Enum

### Community 54 - "Module Group 54"
Cohesion: 0.50
Nodes (3): _lifecycle_cols(), Return fresh lifecycle column instances for each table.      ForeignKey objects, upgrade()

### Community 55 - "Module Group 55"
Cohesion: 0.50
Nodes (4): Select nav pages to render and chunk (§11.11).      Selected pages are queued fo, select_nav_pages(), NavSelectResponse, Response for POST /ingestions/{id}/nav-select.

### Community 56 - "Module Group 56"
Cohesion: 0.50
Nodes (4): Queue selected chunks for LLM triage and extraction (§11.5).      Callable multi, select_chunks(), Response for POST /ingestions/{id}/select., SelectChunksResponse

### Community 57 - "Module Group 57"
Cohesion: 0.50
Nodes (4): IngestionResponse, IngestionStatusResponse, Ingestion job summary returned on create and status endpoints., Ingestion status with full chunk list (GET /ingestions/{id}/status).

### Community 58 - "Module Group 58"
Cohesion: 0.50
Nodes (3): ConfirmRequest, Shared lifecycle response schema for all governed record types.  §9.1 — identity, Optional body for confirm endpoints.      justification is required (non-empty)

## Ambiguous Edges - Review These
- `Authentik OIDC Provider` → `Blueprinted.io Brand Logo`  [AMBIGUOUS]
  platform/docs/authentik-logo.svg · relation: conceptually_related_to

## Knowledge Gaps
- **29 isolated node(s):** `command`, `args`, `command`, `args`, `Testing Principles` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Authentik OIDC Provider` and `Blueprinted.io Brand Logo`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `make_token()` connect `Test Infrastructure & API Keys` to `Ingestion Tests`, `Ingestion API & Routes`, `Module Group 33`, `Admin Tests`, `Review Queue Tests`, `Test Factories`, `Triage Estimate Tests`, `Ingestion Test Rationale`, `Search Tests`, `Workflow Tests`, `Test Auth Stubs`, `Notification Tests`?**
  _High betweenness centrality (0.273) - this node is a cross-community bridge._
- **Why does `User` connect `Request Dependencies` to `Module Group 32`, `Auth Dependencies & Audit`, `Admin Settings Service`, `Task Domain`, `Database & Core Models`, `Workflow Domain`, `Lifecycle State Machine`, `Principle Domain & Notifications`, `Machine Auth & API Keys`, `Test Auth Stubs`, `Notification Tests`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `create_engine()` connect `Module Group 31` to `Ingestion Tests`, `Ingestion API & Routes`, `Module Group 34`, `Module Group 35`, `Module Group 37`, `Module Group 39`, `Review Queue Tests`, `Ingestion Models`, `Triage Estimate Tests`, `Ingestion Test Rationale`, `Module Group 49`, `Test Auth Stubs`, `Notification Tests`, `Token Verification`, `Worker Process Tests`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 186 inferred relationships involving `make_token()` (e.g. with `test_me_returns_user_profile()` and `test_me_creates_user_on_first_call()`) actually correct?**
  _`make_token()` has 186 INFERRED edges - model-reasoned connections that need verification._
- **Are the 86 inferred relationships involving `str` (e.g. with `_store_embedding()` and `_exc_str()`) actually correct?**
  _`str` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `Base` (e.g. with `Task` and `TaskStep`) actually correct?**
  _`Base` has 24 INFERRED edges - model-reasoned connections that need verification._