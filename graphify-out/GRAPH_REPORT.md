# Graph Report - .  (2026-06-11)

## Corpus Check
- 2 files · ~139,494 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1502 nodes · 3151 edges · 116 communities (95 shown, 21 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 439 edges (avg confidence: 0.75)
- Token cost: 115,941 input · 6,500 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Ingestion API Tests|Ingestion API Tests]]
- [[_COMMUNITY_Lifecycle & Governance Services|Lifecycle & Governance Services]]
- [[_COMMUNITY_CLI Commands|CLI Commands]]
- [[_COMMUNITY_Deploy Stack & Startup Recovery|Deploy Stack & Startup Recovery]]
- [[_COMMUNITY_Admin API Tests|Admin API Tests]]
- [[_COMMUNITY_JWT Factory & Pagination Tests|JWT Factory & Pagination Tests]]
- [[_COMMUNITY_Ingestion ORM & Schemas|Ingestion ORM & Schemas]]
- [[_COMMUNITY_Chunk Processing Tests|Chunk Processing Tests]]
- [[_COMMUNITY_Platform Decisions Log|Platform Decisions Log]]
- [[_COMMUNITY_Review Queue & Claims|Review Queue & Claims]]
- [[_COMMUNITY_HTML Ingestion API & Tests|HTML Ingestion API & Tests]]
- [[_COMMUNITY_Tasks API & Diffs|Tasks API & Diffs]]
- [[_COMMUNITY_Record Payload Factories & Task Tests|Record Payload Factories & Task Tests]]
- [[_COMMUNITY_Session History Concepts|Session History Concepts]]
- [[_COMMUNITY_LLM Settings Resolver|LLM Settings Resolver]]
- [[_COMMUNITY_Notifications|Notifications]]
- [[_COMMUNITY_Admin API|Admin API]]
- [[_COMMUNITY_Roles & Principles API|Roles & Principles API]]
- [[_COMMUNITY_Architecture Reference Docs|Architecture Reference Docs]]
- [[_COMMUNITY_ARQ Worker & Chunking|ARQ Worker & Chunking]]
- [[_COMMUNITY_Triage Estimate Tests|Triage Estimate Tests]]
- [[_COMMUNITY_Triage Review Gate & Prompts|Triage Review Gate & Prompts]]
- [[_COMMUNITY_Workflows API|Workflows API]]
- [[_COMMUNITY_Candidate Review Tests|Candidate Review Tests]]
- [[_COMMUNITY_ORM Base & Models|ORM Base & Models]]
- [[_COMMUNITY_Ingestions API|Ingestions API]]
- [[_COMMUNITY_Hybrid Search|Hybrid Search]]
- [[_COMMUNITY_Search Tests|Search Tests]]
- [[_COMMUNITY_Sprint 10-11 Hardening Concepts|Sprint 10-11 Hardening Concepts]]
- [[_COMMUNITY_Workflow Tests|Workflow Tests]]
- [[_COMMUNITY_API Key Tests|API Key Tests]]
- [[_COMMUNITY_Nav Page Selection|Nav Page Selection]]
- [[_COMMUNITY_CI Auto-Fix Script|CI Auto-Fix Script]]
- [[_COMMUNITY_Triage Estimates API|Triage Estimates API]]
- [[_COMMUNITY_Authentik Setup & Platform Overview|Authentik Setup & Platform Overview]]
- [[_COMMUNITY_API Keys & Agent Roles|API Keys & Agent Roles]]
- [[_COMMUNITY_Candidate Commit|Candidate Commit]]
- [[_COMMUNITY_Pytest Fixtures|Pytest Fixtures]]
- [[_COMMUNITY_Principle Tests|Principle Tests]]
- [[_COMMUNITY_FastAPI Dependencies|FastAPI Dependencies]]
- [[_COMMUNITY_Prompts & JSON Import Docs|Prompts & JSON Import Docs]]
- [[_COMMUNITY_App Configuration|App Configuration]]
- [[_COMMUNITY_Backend Stack Concepts|Backend Stack Concepts]]
- [[_COMMUNITY_Auth Tests|Auth Tests]]
- [[_COMMUNITY_System Settings|System Settings]]
- [[_COMMUNITY_Project Working Practices|Project Working Practices]]
- [[_COMMUNITY_V1 Router & Pagination|V1 Router & Pagination]]
- [[_COMMUNITY_Prompt Loading|Prompt Loading]]
- [[_COMMUNITY_MVP Audit & Rate Limits|MVP Audit & Rate Limits]]
- [[_COMMUNITY_Relationships API|Relationships API]]
- [[_COMMUNITY_Ingestion Table Models|Ingestion Table Models]]
- [[_COMMUNITY_App Bootstrap|App Bootstrap]]
- [[_COMMUNITY_Docker Compose Services|Docker Compose Services]]
- [[_COMMUNITY_User Profile API|User Profile API]]
- [[_COMMUNITY_Audit Write Helpers|Audit Write Helpers]]
- [[_COMMUNITY_User Profile Tests|User Profile Tests]]
- [[_COMMUNITY_Alembic Environment|Alembic Environment]]
- [[_COMMUNITY_Request ID Middleware|Request ID Middleware]]
- [[_COMMUNITY_Audit Log API|Audit Log API]]
- [[_COMMUNITY_PDF Chunking|PDF Chunking]]
- [[_COMMUNITY_Active Session Log|Active Session Log]]
- [[_COMMUNITY_Token Verifiers|Token Verifiers]]
- [[_COMMUNITY_Task Validation Tests|Task Validation Tests]]
- [[_COMMUNITY_File Storage|File Storage]]
- [[_COMMUNITY_MCP Config|MCP Config]]
- [[_COMMUNITY_Dev Seed Script|Dev Seed Script]]
- [[_COMMUNITY_Relationship Tests|Relationship Tests]]
- [[_COMMUNITY_Principle Validation|Principle Validation]]
- [[_COMMUNITY_Lifecycle Mixin|Lifecycle Mixin]]
- [[_COMMUNITY_Core Schema Migration|Core Schema Migration]]
- [[_COMMUNITY_OIDC Auth & Roles|OIDC Auth & Roles]]
- [[_COMMUNITY_JWT Verification Errors|JWT Verification Errors]]
- [[_COMMUNITY_Chunk Selection|Chunk Selection]]
- [[_COMMUNITY_Structlog Config|Structlog Config]]
- [[_COMMUNITY_Lifecycle Schemas|Lifecycle Schemas]]
- [[_COMMUNITY_Health Tests|Health Tests]]
- [[_COMMUNITY_Health Endpoint|Health Endpoint]]
- [[_COMMUNITY_Rate Limiter|Rate Limiter]]
- [[_COMMUNITY_V1 Router|V1 Router]]
- [[_COMMUNITY_CI Auto-Fix Session|CI Auto-Fix Session]]
- [[_COMMUNITY_Fable 5 Review Session|Fable 5 Review Session]]
- [[_COMMUNITY_LLM Repair Session|LLM Repair Session]]
- [[_COMMUNITY_Self-Hosted Deployment|Self-Hosted Deployment]]
- [[_COMMUNITY_bp Design System|bp Design System]]
- [[_COMMUNITY_CI Maintenance Workflows|CI Maintenance Workflows]]
- [[_COMMUNITY_Queue Constants|Queue Constants]]
- [[_COMMUNITY_CI Workflows|CI Workflows]]
- [[_COMMUNITY_Irreversible Step Flag|Irreversible Step Flag]]
- [[_COMMUNITY_JSON Import Validation|JSON Import Validation]]
- [[_COMMUNITY_Knowledge Governance Platform|Knowledge Governance Platform]]
- [[_COMMUNITY_Blueprinted CLI|Blueprinted CLI]]
- [[_COMMUNITY_Project CLAUDE|Project CLAUDE.md]]
- [[_COMMUNITY_Step Linting|Step Linting]]
- [[_COMMUNITY_Docs Restructure Session|Docs Restructure Session]]
- [[_COMMUNITY_Frontend Stack|Frontend Stack]]

## God Nodes (most connected - your core abstractions)
1. `make_token()` - 191 edges
2. `create_engine()` - 50 edges
3. `LifecycleResponse` - 37 edges
4. `Base` - 35 edges
5. `Settings` - 32 edges
6. `task_payload()` - 29 edges
7. `WorkerSettings` - 28 edges
8. `Requirements Specification v4.7 (Current)` - 27 edges
9. `_create_and_submit_task()` - 22 edges
10. `_make_ingestion_with_triage_complete_chunk()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `TaskResponse` --conceptually_related_to--> `Lifecycle State Machine`  [INFERRED]
  api/schemas/task.py → platform/docs/requirements.md
- `WorkflowResponse` --conceptually_related_to--> `Lifecycle State Machine`  [INFERRED]
  api/schemas/workflow.py → platform/docs/requirements.md
- `Audit Log` --references--> `Admin Break-Glass Confirm`  [INFERRED]
  platform/docs/requirements.md → api/services/lifecycle.py
- `Session 2026-05-29 — Worker Tests + asyncpg CAST() Embedding Fix` --references--> `startup()`  [EXTRACTED]
  SESSIONS_ARCHIVE.md → workers/ingestion.py
- `call_llm()` --implements--> `LLM Provider Strategy (§11.1, §11.2)`  [INFERRED]
  workers/llm.py → docs/requirements.md

## Hyperedges (group relationships)
- **Sprint 12 Two-Worker Contract** — sessions_archive_worker_split, sessions_archive_ingestion_queue_routing, sessions_archive_startup_recovery_hook, sessions_worker_ingestion_deploy [EXTRACTED 1.00]
- **Pagination Envelope Adoption (Backend to Frontend)** — sessions_archive_page_envelope, sessions_page_envelope, sessions_getallpages_walker, sessions_paginationcontrols [EXTRACTED 1.00]
- **Governance Review Controls** — sessions_archive_lifecycle_state_machine, sessions_archive_self_review_prohibition, sessions_archive_break_glass_confirm, sessions_archive_domain_enforcement, sessions_archive_review_claims [INFERRED 0.85]

## Communities (116 total, 21 thin omitted)

### Community 0 - "Ingestion API Tests"
Cohesion: 0.03
Nodes (74): _pdf_bytes(), _pdf_upload(), Tests for the Ingestion Pipeline API (§11).  Spec refs:   §11.3  Ingestion pipel, force=true bypasses dedup and creates a new ingestion record., Insert a minimal HTML ingestion row., Insert a minimal ingestion_nav_pages row., A page already in selected status is not re-queued., A task item missing a required field is rejected with 422. (+66 more)

### Community 1 - "Lifecycle & Governance Services"
Cohesion: 0.05
Nodes (61): is_machine_credential(), Return True if all roles in the list are agent-prefixed (§5.3)., Domain Enforcement (§7.3), Review Queue Claiming Model (§8.2), confirm_task(), deprecate_task(), _get_task(), Fetch a Task with all sub-resources loaded. (+53 more)

### Community 2 - "CLI Commands"
Cohesion: 0.05
Nodes (39): api_keys_create(), api_keys_revoke(), backup(), healthcheck(), migrate(), Blueprinted CLI — all operational tasks for a running instance.  Usage:     blue, Register a new tenant schema and run its migrations., Remove a tenant schema. Irreversible — take a backup first. (+31 more)

### Community 3 - "Deploy Stack & Startup Recovery"
Cohesion: 0.07
Nodes (39): Startup hook crash-recovery (§14), api service (FastAPI), auth service (Authentik OIDC), db service (PostgreSQL 16 + pgvector), redis service (ARQ broker + rate limit backend), storage service (MinIO, optional), worker service (default ARQ worker), worker-ingestion service (ingestion ARQ worker) (+31 more)

### Community 4 - "Admin API Tests"
Cohesion: 0.08
Nodes (31): _admin_headers(), Tests for the Admin API (§23.11).  Spec refs:   §23.11  Admin endpoints — settin, test_create_domain_admin_returns_201(), test_create_domain_duplicate_returns_409(), test_create_domain_viewer_returns_403(), test_disable_domain_already_disabled_returns_409(), test_disable_nonexistent_domain_returns_404(), test_disable_then_enable_domain() (+23 more)

### Community 5 - "JWT Factory & Pagination Tests"
Cohesion: 0.11
Nodes (36): make_token(), Factory that produces signed RS256 JWTs for testing., Tests for the §6 pagination convention (v4.11) on governed record lists.  Covers, test_list_rejects_out_of_bounds_params(), test_list_returns_page_envelope_with_defaults(), test_list_tasks_offset_past_end_returns_empty_page(), test_list_tasks_respects_limit(), test_list_tasks_returns_latest_version_only_and_total_counts_records() (+28 more)

### Community 6 - "Ingestion ORM & Schemas"
Cohesion: 0.05
Nodes (33): ORM models for the ingestion pipeline tables (SS11.13-SS11.15, SS11.8a)., Ingestion job record — one per uploaded PDF, HTML source, or JSON payload (§11.1, CandidateCommitRequest, CandidateReviewRequest, HtmlIngestionRequest, IngestionCandidateResponse, IngestionChunkResponse, IngestionResponse (+25 more)

### Community 7 - "Chunk Processing Tests"
Cohesion: 0.14
Nodes (33): create_engine(), _chat_response(), _get_candidates(), _get_chunk(), _get_estimates(), _insert_extraction_queued_chunk(), _insert_queued_chunk(), _make_env_settings() (+25 more)

### Community 8 - "Platform Decisions Log"
Cohesion: 0.08
Nodes (36): Agent Role Prefix — agent: prefix distinguishes machine from human credentials, Audit Log — append-only privileged operation trail (§9.6), Admin Break-Glass Confirm, CI Auto-fix Pipeline — event-driven GitHub Actions using synthetic.new GLM-5.1, Ingestion pipeline (triage → extraction), Iterative Ingestion — primary model; 2-5 chunk batches per pass, Knowledge Hierarchy — Domain > Workflows > Tasks + Principles, Machine Auth — API keys and OIDC client credentials (Sprint 10) (+28 more)

### Community 9 - "Review Queue & Claims"
Cohesion: 0.09
Nodes (35): ReviewClaim ORM model.  Maps to the review_claims table created in migration b4c, claim_item(), _collect_queue_items(), confirm_via_review(), _get_active_claim(), _get_expiry_hours(), _get_record(), get_review_queue() (+27 more)

### Community 10 - "HTML Ingestion API & Tests"
Cohesion: 0.16
Nodes (36): create_html_ingestion(), Submit a URL for HTML ingestion (§11.10).      Single-page mode renders one URL, str, _count_chunks(), _count_nav_pages(), _get_ingestion_status(), _get_nav_page_status(), _insert_html_ingestion() (+28 more)

### Community 11 - "Tasks API & Diffs"
Cohesion: 0.14
Nodes (26): _get_task_by_record_version(), get_task_diff(), get_task_version(), Tasks API endpoints, including steps.  §9.5  — Tasks schema: steps with actions,, Fetch a specific version of a Task by its stable record_id and version number., LifecycleResponse, Base response schema carrying the shared identity and lifecycle fields., from_lint() (+18 more)

### Community 12 - "Record Payload Factories & Task Tests"
Cohesion: 0.11
Nodes (26): Minimal valid request payload factories for governed record tests.  Each factory, task_payload(), task_step_action_payload(), task_step_payload(), Tests for the Tasks lifecycle API.  TEST_REVISED (v4.4/v4.5 — dissolve Facts/Con, task.irreversible is derived: True when any step is irreversible., Confirmed tasks are immutable — steps cannot be added after confirmation., Confirmed records do not surface lint warnings (§9.10). (+18 more)

### Community 13 - "Session History Concepts"
Cohesion: 0.07
Nodes (31): Auth failure rate limiting deferred, Audit Log, Authentik Identity Provider, Break-Glass Confirm, Domain Enforcement (§7.3), Embedding Generation Worker, Fable 5 Review Hardening Roadmap, Facts/Concepts Dissolution (v4.4) (+23 more)

### Community 14 - "LLM Settings Resolver"
Cohesion: 0.12
Nodes (28): Embedding Lifecycle (§12.1), LLMSettings, load_llm_settings(), Load LLM config from system_settings, falling back to env Settings.      The per, Resolved LLM configuration loaded from system_settings (per-job resolver)., Session 2026-05-29 — Worker Tests + asyncpg CAST() Embedding Fix, _embedding_response(), _get_embedding() (+20 more)

### Community 15 - "Notifications"
Cohesion: 0.13
Nodes (23): Notification ORM model (§13)., list_notifications(), mark_all_read(), mark_read(), Notifications API endpoints (§13)., Return the current user's notifications, newest first., Mark a single notification as read., Mark all unread notifications for the current user as read. (+15 more)

### Community 16 - "Admin API"
Cohesion: 0.14
Nodes (21): BaseModel, admin_health(), disable_domain(), enable_domain(), _get_domain_or_404(), Admin API endpoints (§23.11).  All endpoints require the Admin role.  Routes:, Probe GET {base_url}/models and return available model IDs.      If api_key is b, test_llm_connection() (+13 more)

### Community 17 - "Roles & Principles API"
Cohesion: 0.17
Nodes (24): Dependency factory that enforces role membership.      Usage:         @router.ge, require_role(), Principle ORM model.  §9.5 — foundational document-grain knowledge attached to W, confirm_principle(), create_principle(), deprecate_principle(), _get_or_404(), get_principle() (+16 more)

### Community 18 - "Architecture Reference Docs"
Cohesion: 0.12
Nodes (26): API Keys Table Schema, ARQ Resumability via Application Checkpoints, Break-Glass Admin Confirm, Domain Scoping and Enforcement, Facts and Concepts Dissolved (v4.4), Ingestion Pipeline, ingestion_triage_estimates Table, Lifecycle State Machine (+18 more)

### Community 19 - "ARQ Worker & Chunking"
Cohesion: 0.10
Nodes (25): ARQ background worker, IngestionChunk status state machine, Read a previously stored ingestion file., read_ingestion_file(), _call_llm(), chunk_pdf(), expire_review_claims(), extract_chunk() (+17 more)

### Community 20 - "Triage Estimate Tests"
Cohesion: 0.24
Nodes (24): _auth(), _make_ingestion_with_triage_complete_chunk(), Tests for triage estimate review endpoints (§11.5a).  Spec refs:   §11.5a Triage, Seed an ingestion + chunk in triage_complete state; return (ingestion_id, chunk_, Insert estimate rows and return their IDs in order., _seed_estimates(), test_approve_all_rejected_moves_chunk_to_done(), test_approve_estimates_marks_approved() (+16 more)

### Community 21 - "Triage Review Gate & Prompts"
Cohesion: 0.13
Nodes (23): load(), Return the cached Prompt for the given pipeline stage.      Raises KeyError if s, Triage/Extraction Human Review Gate, LLM Provider Strategy (§11.1, §11.2), Estimate Review UI, Session 2026-05-18 — LLM Ingestion Pipeline Repair (json_repair, fence stripping), Session 2026-05-27 — Triage/Extraction Split (§11.5a), exc_str() (+15 more)

### Community 22 - "Workflows API"
Cohesion: 0.12
Nodes (22): LifecycleResponse, delete_step(), update_step(), attach_principle(), detach_principle(), get_workflow(), Workflows API endpoints, including task-refs and principle-refs.  §9.5  — Workfl, remove_task_ref() (+14 more)

### Community 23 - "Candidate Review Tests"
Cohesion: 0.13
Nodes (24): Nav pages endpoint rejects non-HTML ingestions., Insert a minimal ingestion row owned by user_id., Insert a minimal ingestion_candidates row., Candidate list for another user's ingestion is opaque 404., Cannot commit a candidate that has not been accepted., A contributor not assigned to the domain gets 403., _seed_candidate(), _seed_ingestion() (+16 more)

### Community 24 - "ORM Base & Models"
Cohesion: 0.17
Nodes (18): Base, Shared declarative base for all ORM models., DeclarativeBase, LifecycleMixin, Shared identity and lifecycle columns inherited by all governed record tables., Domain, Domain and UserDomain ORM models.  §7.1 — domain registry and user assignment, UserDomain (+10 more)

### Community 25 - "Ingestions API"
Cohesion: 0.10
Nodes (21): _canonical_json(), create_ingestion(), create_json_ingestion(), get_ingestion_status(), list_candidates(), list_ingestions(), list_nav_pages(), _normalise_url() (+13 more)

### Community 26 - "Hybrid Search"
Cohesion: 0.14
Nodes (19): Search API endpoint (§12.2).  GET /api/v1/search  — full-text and optional seman, Search across all governed record types.      Full-text search is always perform, search_records(), Search API schemas (§12.2)., SearchResponse, SearchResult, _active_configs(), _fts_leg() (+11 more)

### Community 27 - "Search Tests"
Cohesion: 0.13
Nodes (20): _make_confirmed_task(), Tests for GET /api/v1/search (§12.2).  TEST_REVISED (v4.4 — dissolve Facts/Conce, Unknown type tokens in the filter are silently ignored (not a 422)., ?semantic=true with no embedding config falls back to fulltext gracefully., Confirmed records should not appear when searching for draft status., Create, submit, and confirm a Task containing the search keyword. Returns its id, test_domain_filter_non_matching_domain_returns_no_task(), test_search_empty_q_returns_422() (+12 more)

### Community 28 - "Sprint 10-11 Hardening Concepts"
Cohesion: 0.14
Nodes (20): extract_chunk ARQ job function, lifecycle_actions.py shared service, api/services/linting.py step quality warnings, Machine/human credential distinction via agent: prefix, Route deduplication via shared service layer decision, Session Sprint 10 machine auth, audit log, CLI, Session Sprint 11 Hardening (complete), Synthetic User record per API key decision (+12 more)

### Community 29 - "Workflow Tests"
Cohesion: 0.19
Nodes (18): workflow_payload(), test_patch_confirmed_task_returns_422(), Tests for the Workflows lifecycle API.  Spec refs:   §9.3  Lifecycle state machi, Only confirmed Tasks may be referenced in a Workflow., test_add_confirmed_task_ref_to_workflow(), test_add_task_ref_to_confirmed_workflow_returns_422(), test_add_unconfirmed_task_ref_returns_422(), test_attach_confirmed_principle_to_workflow() (+10 more)

### Community 30 - "API Key Tests"
Cohesion: 0.11
Nodes (14): Tests for scoped API key management and machine credential auth (§5.3, §9.6)., A valid bp_ key authenticates and can call read endpoints., A bp_ API key is rejected with 403 at any confirm endpoint., test_api_key_authenticates_for_data_endpoint(), test_create_api_key_invalid_role_returns_422(), test_create_api_key_returns_201_with_raw_key(), test_list_api_keys_does_not_return_raw_key(), test_list_api_keys_non_admin_returns_403() (+6 more)

### Community 31 - "Nav Page Selection"
Cohesion: 0.13
Nodes (18): HTML Ingestion and Nav Discovery (§11.10, §11.11), Select nav pages to render and chunk (§11.11).      Selected pages are queued fo, select_nav_pages(), test_make_chunks_empty_sections(), test_make_chunks_populates_fields(), test_make_chunks_preview_truncated(), test_make_chunks_skips_empty_text(), _make_chunks_from_sections() (+10 more)

### Community 32 - "CI Auto-Fix Script"
Cohesion: 0.24
Nodes (17): Synthetic GLM-5.1 (CI auto-fix LLM), main (fix_ci), apply_files(), call_model(), extract_paths(), fix_general(), fix_pip_audit(), get_logs() (+9 more)

### Community 33 - "Triage Estimates API"
Cohesion: 0.18
Nodes (16): approve_estimates(), _get_chunk_or_404(), list_estimates(), merge_estimates(), patch_estimate(), Triage estimate review endpoints (§11.5a).  GET    /ingestions/{id}/chunks/{chun, Merge multiple estimates into one (§11.5a).      The first estimate in the list, Approve pending estimates, moving the chunk to extraction_queued (§11.5a). (+8 more)

### Community 34 - "Authentik Setup & Platform Overview"
Cohesion: 0.12
Nodes (16): Authentik OIDC Provider Configuration, Blueprinted Roles Property Mapping, Authentik Setup Guide, Human-in-the-Loop Governance, Blueprinted Platform, Technology Stack Overview, Testing Principles, Agent Roles (workflow_consumer/staleness_monitor/orphan_detector) (+8 more)

### Community 35 - "API Keys & Agent Roles"
Cohesion: 0.20
Nodes (14): AgentRole, Machine credential roles as defined in §5.2. Available from Sprint 10., create_api_key(), _generate_key(), list_api_keys(), Admin API key management endpoints (§5.3, §9.6).  GET    /admin/api-keys, Return (raw_key, key_prefix, key_hash)., List all API keys. Raw keys are never returned. (+6 more)

### Community 36 - "Candidate Commit"
Cohesion: 0.17
Nodes (15): Task, TaskStep, TaskStepAction, _build_steps(), _build_task(), commit_candidate(), Construct a Task ORM object (without steps) from extraction JSON., Attach TaskStep and TaskStepAction children to a Task. (+7 more)

### Community 37 - "Pytest Fixtures"
Cohesion: 0.14
Nodes (11): ArqPool dependency, client(), pytest fixtures for the Blueprinted test suite.  Test DB setup runs via asyncio., Pre-seed the test domain and all contributor users with domain assignments., Async HTTP client with lifespan started and StubTokenVerifier installed., Test stub for arq.connections.ArqRedis. Records calls without touching Redis., Create all ORM tables once per session, outside the async event loop., setup_test_db() (+3 more)

### Community 38 - "Principle Tests"
Cohesion: 0.24
Nodes (14): principle_payload(), Tests for the Principles lifecycle API.  Spec refs:   §9.3  Lifecycle state mach, test_create_principle_contributor_returns_201_draft(), test_create_principle_missing_summary_returns_422(), test_create_principle_response_has_required_fields(), test_create_principle_unauthenticated_returns_401(), test_create_principle_viewer_returns_403(), test_create_principle_with_domain() (+6 more)

### Community 39 - "FastAPI Dependencies"
Cohesion: 0.17
Nodes (11): get_session(), _authenticate_api_key(), get_arq_pool(), get_current_user(), get_token_verifier(), FastAPI dependency providers., Validate Bearer token (JWT or bp_ API key) and return the authenticated user., Yield a database session from the factory stored on app.state. (+3 more)

### Community 40 - "Prompts & JSON Import Docs"
Cohesion: 0.19
Nodes (13): JSON Import Schema (v1.0), Manual JSON Authoring Guide, Extract Principle Prompt, Extract Task Prompt, Triage Category Classification, Triage Prompt, Changelog Propose Prompt (v1.1), Changelog Screen Prompt (v1.1) (+5 more)

### Community 41 - "App Configuration"
Cohesion: 0.17
Nodes (4): Bootstrap configuration loaded from environment variables.  Runtime configuratio, Settings, Async SQLAlchemy engine and session management., BaseSettings

### Community 42 - "Backend Stack Concepts"
Cohesion: 0.17
Nodes (12): Session v4.4/v4.5 backend refactor — dissolve Facts/Concepts, CI Auto-Fix Pipeline, Embedding Generation Worker, Hybrid Search with pgvector, Backend Technology Stack, Database Stack PostgreSQL + pgvector, Search and Embeddings (§12), Active Session (SESSIONS.md) (+4 more)

### Community 43 - "Auth Tests"
Cohesion: 0.29
Nodes (8): _make_raw(), Tests for JWT token verification logic., test_expired_token_raises(), test_extract_roles_returns_list(), test_tampered_token_raises(), test_valid_token_decodes(), test_wrong_audience_raises(), test_wrong_issuer_raises()

### Community 44 - "System Settings"
Cohesion: 0.29
Nodes (8): System Settings Store, SystemSetting ORM model (§10.4)., patch_settings(), _decrypt(), _encrypt(), _make_fernet(), System settings service — DB-backed key/value config store (§10.4, §11.1).  LLM, set_setting()

### Community 45 - "Project Working Practices"
Cohesion: 0.22
Nodes (10): Project Index (CLAUDE.md), No-Machine-Can-Confirm (§10.2, §5.3), Schema-Per-Tenant Multi-Tenancy, TEST_REVISED Process, Architecture and Working Practice, Code Style Guide, Project Rules (Absolute), Absolute Rules (+2 more)

### Community 46 - "V1 Router & Pagination"
Cohesion: 0.24
Nodes (9): v1 APIRouter, list_relationships(), list_tasks(), list_workflows(), Page, Generic pagination envelope for list endpoints.  §6 — API pagination convention, Paginated response envelope., Fetch every page of a list endpoint, returning (all items, reported total). (+1 more)

### Community 47 - "Prompt Loading"
Cohesion: 0.28
Nodes (7): _load_all(), _parse_prompt_file(), Prompt, Prompt loading for the ingestion pipeline (§11.16).  Reads versioned markdown fi, A loaded prompt ready to be rendered into a message pair., Return (system_message, user_message) with variables substituted., Extract system and user_template text from a prompt markdown file.

### Community 48 - "MVP Audit & Rate Limits"
Cohesion: 0.22
Nodes (9): Rate Limiting (§17.1, Sprint 11), MVP vs Platform Feature Continuity Audit, Export artifacts + SHA256 fingerprints (v1.1), force_submit admin override — Not needed, Hard delete — Explicitly out of scope, Return note severity (resolved in v4.8), Step linting / quality hints (resolved in v4.8), Step Quality Linting (§9.10) (+1 more)

### Community 49 - "Relationships API"
Cohesion: 0.29
Nodes (5): Relationship ORM model.  §9.4 — infrastructure table; all writes rejected with H, Rationale: wrong taxonomy worse than no taxonomy; relationship semantics harder than they appear, Relationships API endpoints. §9.4, §23.9  All writes rejected with HTTP 422 in v, Relationship response schema. §9.4, RelationshipResponse

### Community 50 - "Ingestion Table Models"
Cohesion: 0.36
Nodes (8): Base, IngestionCandidate, IngestionChunk, IngestionNavPage, Discovered navigable page from an HTML site-nav crawl (§11.15)., One structural section of an ingested source document (§11.14)., LLM-extracted candidate record awaiting human review (§11.8)., api/models __init__ — ORM model registry

### Community 51 - "App Bootstrap"
Cohesion: 0.39
Nodes (7): get_settings(), create_session_factory(), configure_logging(), Configure structlog for JSON output. Call once at startup., create_app(), lifespan(), FastAPI application factory.

### Community 52 - "Docker Compose Services"
Cohesion: 0.32
Nodes (8): Docker Compose Production Stack, MinIO S3-Compatible Storage, Docker Compose Dev Override, Blueprinted.io Brand Logo, Authentik OIDC Provider, Docker Compose Stack, Local Dev Setup Guide, Playwright Chromium for HTML Ingestion

### Community 53 - "User Profile API"
Cohesion: 0.25
Nodes (6): get_me(), User profile endpoints., Return the authenticated user's profile., Pydantic schemas for user API responses., Response schema for GET /api/v1/users/me., UserResponse

### Community 54 - "Audit Write Helpers"
Cohesion: 0.25
Nodes (7): create_domain(), replace_user_domains(), Revoke an API key. Immediate effect — any bearer using this key gets 401., revoke_api_key(), Audit log write helpers (§9.6)., Append an entry to the audit log. Caller must commit the session., write_audit_event()

### Community 55 - "User Profile Tests"
Cohesion: 0.25
Nodes (5): Tests for GET /api/v1/users/me., test_me_creates_user_on_first_call(), test_me_response_has_required_fields(), test_me_returns_user_profile(), test_me_syncs_updated_email()

### Community 56 - "Alembic Environment"
Cohesion: 0.38
Nodes (6): get_url(), Alembic migration environment.  Uses the synchronous psycopg2 driver for CLI mig, Run migrations without a live database connection (generates SQL)., Run migrations against a live database connection., run_migrations_offline(), run_migrations_online()

### Community 57 - "Request ID Middleware"
Cohesion: 0.29
Nodes (4): Request ID middleware and security headers., Attach a unique request ID to every request and response.      Binds the ID to s, RequestIDMiddleware, BaseHTTPMiddleware

### Community 58 - "Audit Log API"
Cohesion: 0.29
Nodes (7): Audit Log, AuditLog ORM model (§9.6)., list_audit_log(), Audit log read endpoint (§9.6, §5.1).  GET /audit   Audit role only, paginated,, Return audit log entries, newest first. Accessible by Audit and Admin roles., AuditLogResponse, Audit log Pydantic schemas (§9.6).

### Community 59 - "PDF Chunking"
Cohesion: 0.33
Nodes (6): PDF Ingestion (§11.9), chunk_pdf(), _extract_chunks_from_pdf(), PDF chunking job (§11.9, §14). Runs on the ingestion worker., Parse a PDF into chunk dicts using PyMuPDF hybrid outline+heading strategy (§11., Parse a PDF into ingestion_chunks and update the ingestion status (§11.9, §14).

### Community 60 - "Active Session Log"
Cohesion: 0.33
Nodes (7): Active Session Log — blueprinted.io, Auto-fix PR #3 partial rejection decision, Weekly pip-audit without --strict, Dependency Audit Workflow, Sprint 12 Next Steps, dependency-audit.yml GitHub Actions workflow, pip-audit --skip-editable step

### Community 61 - "Token Verifiers"
Cohesion: 0.29
Nodes (5): Return the roles list from claims, defaulting to empty., TokenVerifier for tests — verifies against a supplied RSA public key.      No HT, Verifies RS256 JWTs against a JWKS endpoint.      Fetches and caches JWKS on fir, TokenVerifier, verifier()

### Community 62 - "Task Validation Tests"
Cohesion: 0.38
Nodes (7): test_validate_task_empty_steps(), test_validate_task_missing_field(), test_validate_task_valid(), Return an error string if the task candidate is missing required fields., _validate_task(), Return an error string if the task candidate is missing required fields., _validate_task()

### Community 63 - "File Storage"
Cohesion: 0.33
Nodes (5): delete_ingestion(), File storage abstraction (§4.4).  v1 implements local-disk storage only. The int, Write uploaded file to local storage. Returns (storage_path, sha256_hex)., Remove the storage directory for an ingestion (no-op if absent)., save_ingestion_file()

### Community 64 - "MCP Config"
Cohesion: 0.47
Nodes (5): args, command, mcpServers, context7, github

### Community 65 - "Dev Seed Script"
Cohesion: 0.47
Nodes (5): api(), main(), psql(), Development seed script — populates the local dev database with realistic tasks., Run SQL directly via docker exec — used only for domain bootstrap.

### Community 66 - "Relationship Tests"
Cohesion: 0.33
Nodes (4): Tests for the Relationships API. §9.4, §23.9  The relationships table exists as, test_create_relationship_returns_422(), test_list_relationships_contributor_returns_empty_list(), test_list_relationships_viewer_returns_empty_list()

### Community 67 - "Principle Validation"
Cohesion: 0.40
Nodes (6): test_validate_principle_missing_field(), test_validate_principle_valid(), Return an error string if the principle candidate is missing required fields., _validate_principle(), Return an error string if the principle candidate is missing required fields., _validate_principle()

### Community 69 - "Core Schema Migration"
Cohesion: 0.50
Nodes (3): _lifecycle_cols(), Return fresh lifecycle column instances for each table.      ForeignKey objects, upgrade()

### Community 70 - "OIDC Auth & Roles"
Cohesion: 0.50
Nodes (4): OIDC token verification.  TokenVerifier validates RS256 JWTs issued by Authentik, Human roles as defined in §5.1., Role, Enum

### Community 71 - "JWT Verification Errors"
Cohesion: 0.40
Nodes (4): Raised when a JWT cannot be verified., Decode and verify a JWT. Returns the verified claims dict.          Raises Token, TokenVerificationError, Exception

### Community 72 - "Chunk Selection"
Cohesion: 0.50
Nodes (4): Queue selected chunks for LLM triage and extraction (§11.5).      Callable multi, select_chunks(), Response for POST /ingestions/{id}/select., SelectChunksResponse

### Community 73 - "Structlog Config"
Cohesion: 0.50
Nodes (3): structlog configuration — JSON output, request ID propagation.  Call configure_l, Strip known secret field names from log events before output., _redact_secrets()

### Community 74 - "Lifecycle Schemas"
Cohesion: 0.50
Nodes (3): ConfirmRequest, Shared lifecycle response schema for all governed record types.  §9.1 — identity, Optional body for confirm endpoints.      justification is required (non-empty)

## Ambiguous Edges - Review These
- `Authentik OIDC Provider` → `Blueprinted.io Brand Logo`  [AMBIGUOUS]
  platform/docs/authentik-logo.svg · relation: conceptually_related_to

## Knowledge Gaps
- **70 isolated node(s):** `Testing Principles`, `Sprint History`, `Sprint 1 — Foundation`, `Blueprinted Roles Property Mapping`, `Session Protocol` (+65 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Authentik OIDC Provider` and `Blueprinted.io Brand Logo`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `make_token()` connect `JWT Factory & Pagination Tests` to `Ingestion API Tests`, `CLI Commands`, `Relationship Tests`, `Admin API Tests`, `Pytest Fixtures`, `Principle Tests`, `Record Payload Factories & Task Tests`, `LLM Settings Resolver`, `Notifications`, `Triage Estimate Tests`, `Candidate Review Tests`, `User Profile Tests`, `Search Tests`, `Workflow Tests`, `API Key Tests`?**
  _High betweenness centrality (0.224) - this node is a cross-community bridge._
- **Why does `Base` connect `ORM Base & Models` to `Candidate Commit`, `Pytest Fixtures`, `Ingestion ORM & Schemas`, `Platform Decisions Log`, `App Configuration`, `Review Queue & Claims`, `System Settings`, `Notifications`, `Roles & Principles API`, `Ingestion Table Models`, `Architecture Reference Docs`, `Relationships API`, `Alembic Environment`, `Audit Log API`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `create_engine()` connect `Chunk Processing Tests` to `Ingestion API Tests`, `Deploy Stack & Startup Recovery`, `Pytest Fixtures`, `JWT Factory & Pagination Tests`, `App Configuration`, `HTML Ingestion API & Tests`, `LLM Settings Resolver`, `Notifications`, `ARQ Worker & Chunking`, `Triage Estimate Tests`, `App Bootstrap`, `Candidate Review Tests`, `Alembic Environment`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 189 inferred relationships involving `make_token()` (e.g. with `test_me_returns_user_profile()` and `test_me_creates_user_on_first_call()`) actually correct?**
  _`make_token()` has 189 INFERRED edges - model-reasoned connections that need verification._
- **Are the 86 inferred relationships involving `str` (e.g. with `_store_embedding()` and `_exc_str()`) actually correct?**
  _`str` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `LifecycleResponse` (e.g. with `TaskStepActionCreate` and `TaskStepActionResponse`) actually correct?**
  _`LifecycleResponse` has 30 INFERRED edges - model-reasoned connections that need verification._