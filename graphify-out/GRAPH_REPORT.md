# Graph Report - .  (2026-06-10)

## Corpus Check
- 31 files · ~136,898 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1353 nodes · 2829 edges · 103 communities (81 shown, 22 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 413 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Ingestion Pipeline Tests|Ingestion Pipeline Tests]]
- [[_COMMUNITY_DB Engine & Migrations|DB Engine & Migrations]]
- [[_COMMUNITY_App Config & Settings|App Config & Settings]]
- [[_COMMUNITY_Auth & Audit Log Tests|Auth & Audit Log Tests]]
- [[_COMMUNITY_Review Records & ORM|Review Records & ORM]]
- [[_COMMUNITY_Admin API Tests|Admin API Tests]]
- [[_COMMUNITY_Admin Settings Service|Admin Settings Service]]
- [[_COMMUNITY_ARQ Worker & LLM Config|ARQ Worker & LLM Config]]
- [[_COMMUNITY_Relationships & Triage|Relationships & Triage]]
- [[_COMMUNITY_Ingestion ORM & Status|Ingestion ORM & Status]]
- [[_COMMUNITY_Task Lifecycle|Task Lifecycle]]
- [[_COMMUNITY_Spec Concepts & Docs|Spec Concepts & Docs]]
- [[_COMMUNITY_Workflow Lifecycle|Workflow Lifecycle]]
- [[_COMMUNITY_Notification System|Notification System]]
- [[_COMMUNITY_API Keys & CLI Commands|API Keys & CLI Commands]]
- [[_COMMUNITY_Test Payload Factories|Test Payload Factories]]
- [[_COMMUNITY_Triage Estimate Review|Triage Estimate Review]]
- [[_COMMUNITY_HTML Worker Tests|HTML Worker Tests]]
- [[_COMMUNITY_Machine Credential Guard|Machine Credential Guard]]
- [[_COMMUNITY_ORM Base & Domain Models|ORM Base & Domain Models]]
- [[_COMMUNITY_Principles & Notifications|Principles & Notifications]]
- [[_COMMUNITY_Domain Enforcement & Tasks|Domain Enforcement & Tasks]]
- [[_COMMUNITY_Search Tests|Search Tests]]
- [[_COMMUNITY_Lifecycle Mixin|Lifecycle Mixin]]
- [[_COMMUNITY_Workflow Tests|Workflow Tests]]
- [[_COMMUNITY_CI Auto-Fix Pipeline|CI Auto-Fix Pipeline]]
- [[_COMMUNITY_Embedding Worker Tests|Embedding Worker Tests]]
- [[_COMMUNITY_API Key Auth Tests|API Key Auth Tests]]
- [[_COMMUNITY_Ingestion Dedup & Auth|Ingestion Dedup & Auth]]
- [[_COMMUNITY_Principles Tests|Principles Tests]]
- [[_COMMUNITY_Agent Roles & API Keys|Agent Roles & API Keys]]
- [[_COMMUNITY_Dependency Injection|Dependency Injection]]
- [[_COMMUNITY_Spec Architecture Docs|Spec Architecture Docs]]
- [[_COMMUNITY_Robots & Chunking Tests|Robots & Chunking Tests]]
- [[_COMMUNITY_Audit Log Schema|Audit Log Schema]]
- [[_COMMUNITY_JWT Auth Tests|JWT Auth Tests]]
- [[_COMMUNITY_Prompt Loader|Prompt Loader]]
- [[_COMMUNITY_Storage & Ingestion Create|Storage & Ingestion Create]]
- [[_COMMUNITY_Ingestion Table Schema|Ingestion Table Schema]]
- [[_COMMUNITY_HTML Ingestion Seeds|HTML Ingestion Seeds]]
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
- [[_COMMUNITY_Module Group 60|Module Group 60]]
- [[_COMMUNITY_Module Group 74|Module Group 74]]
- [[_COMMUNITY_Module Group 75|Module Group 75]]
- [[_COMMUNITY_Module Group 76|Module Group 76]]
- [[_COMMUNITY_Module Group 77|Module Group 77]]
- [[_COMMUNITY_Module Group 78|Module Group 78]]
- [[_COMMUNITY_Module Group 79|Module Group 79]]
- [[_COMMUNITY_Module Group 80|Module Group 80]]
- [[_COMMUNITY_Module Group 81|Module Group 81]]
- [[_COMMUNITY_Module Group 82|Module Group 82]]
- [[_COMMUNITY_Module Group 83|Module Group 83]]
- [[_COMMUNITY_Module Group 84|Module Group 84]]
- [[_COMMUNITY_Module Group 85|Module Group 85]]
- [[_COMMUNITY_Module Group 86|Module Group 86]]
- [[_COMMUNITY_Module Group 92|Module Group 92]]
- [[_COMMUNITY_Module Group 94|Module Group 94]]
- [[_COMMUNITY_Module Group 97|Module Group 97]]
- [[_COMMUNITY_Module Group 98|Module Group 98]]
- [[_COMMUNITY_Module Group 99|Module Group 99]]
- [[_COMMUNITY_Module Group 100|Module Group 100]]
- [[_COMMUNITY_Module Group 101|Module Group 101]]
- [[_COMMUNITY_Module Group 102|Module Group 102]]

## God Nodes (most connected - your core abstractions)
1. `make_token()` - 186 edges
2. `create_engine()` - 50 edges
3. `LifecycleResponse` - 37 edges
4. `Base` - 35 edges
5. `Settings` - 32 edges
6. `task_payload()` - 29 edges
7. `Requirements Specification v4.7 (Current)` - 27 edges
8. `WorkerSettings` - 22 edges
9. `_create_and_submit_task()` - 22 edges
10. `_make_ingestion_with_triage_complete_chunk()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `TaskResponse` --conceptually_related_to--> `Lifecycle State Machine`  [INFERRED]
  api/schemas/task.py → platform/docs/requirements.md
- `WorkflowResponse` --conceptually_related_to--> `Lifecycle State Machine`  [INFERRED]
  api/schemas/workflow.py → platform/docs/requirements.md
- `Audit Log` --references--> `Admin Break-Glass Confirm`  [INFERRED]
  platform/docs/requirements.md → api/services/lifecycle.py
- `Audit log Pydantic schemas (§9.6).` --rationale_for--> `Audit Log`  [EXTRACTED]
  api/schemas/audit_log.py → platform/docs/requirements.md
- `Audit log read endpoint (§9.6, §5.1).  GET /audit   Audit role only, paginated,` --rationale_for--> `Audit Log`  [EXTRACTED]
  api/routes/audit_log.py → platform/docs/requirements.md

## Communities (103 total, 22 thin omitted)

### Community 0 - "Ingestion Pipeline Tests"
Cohesion: 0.04
Nodes (67): Tests for the Ingestion Pipeline API (§11).  Spec refs:   §11.3  Ingestion pipel, force=true bypasses dedup and creates a new ingestion record., Nav pages endpoint rejects non-HTML ingestions., A task item missing a required field is rejected with 422., Valid JSON payload creates ingestion in ready status with candidates immediately, Identical JSON payload returns the existing ingestion., JSON ingestion is synchronous — no worker job should be enqueued., task_order forward reference (id appears later in items) is accepted. (+59 more)

### Community 1 - "DB Engine & Migrations"
Cohesion: 0.06
Nodes (43): Base, Shared declarative base for all ORM models., DeclarativeBase, get_url(), Alembic migration environment.  Uses the synchronous psycopg2 driver for CLI mig, Run migrations without a live database connection (generates SQL)., Run migrations against a live database connection., run_migrations_offline() (+35 more)

### Community 2 - "App Config & Settings"
Cohesion: 0.05
Nodes (39): get_settings(), Bootstrap configuration loaded from environment variables.  Runtime configuratio, Settings, create_session_factory(), get_session(), Async SQLAlchemy engine and session management., Yield a database session from the factory stored on app.state., configure_logging() (+31 more)

### Community 3 - "Auth & Audit Log Tests"
Cohesion: 0.08
Nodes (46): is_machine_credential(), Return True if all roles in the list are agent-prefixed (§5.3)., Domain Enforcement (§7.3), Lifecycle State Machine, No-Machine-Can-Confirm (§10.2, §5.3), confirm_task(), create_task(), deprecate_task() (+38 more)

### Community 4 - "Review Records & ORM"
Cohesion: 0.06
Nodes (36): AgentRole, OIDC token verification.  TokenVerifier validates RS256 JWTs issued by Authentik, Return the roles list from claims, defaulting to empty., TokenVerifier for tests — verifies against a supplied RSA public key.      No HT, Machine credential roles as defined in §5.2. Available from Sprint 10., Raised when a JWT cannot be verified., Verifies RS256 JWTs against a JWKS endpoint.      Fetches and caches JWKS on fir, Decode and verify a JWT. Returns the verified claims dict.          Raises Token (+28 more)

### Community 5 - "Admin API Tests"
Cohesion: 0.05
Nodes (39): api_keys_create(), api_keys_revoke(), backup(), healthcheck(), migrate(), Blueprinted CLI — all operational tasks for a running instance.  Usage:     blue, Register a new tenant schema and run its migrations., Remove a tenant schema. Irreversible — take a backup first. (+31 more)

### Community 6 - "Admin Settings Service"
Cohesion: 0.11
Nodes (37): _chat_response(), _get_candidates(), _get_chunk(), _get_estimates(), _insert_extraction_queued_chunk(), _insert_queued_chunk(), _make_env_settings(), _principle_extraction_json() (+29 more)

### Community 7 - "ARQ Worker & LLM Config"
Cohesion: 0.07
Nodes (32): System Settings Store, SystemSetting ORM model (§10.4)., admin_health(), create_domain(), disable_domain(), enable_domain(), _get_domain_or_404(), patch_settings() (+24 more)

### Community 8 - "Relationships & Triage"
Cohesion: 0.08
Nodes (31): _admin_headers(), Tests for the Admin API (§23.11).  Spec refs:   §23.11  Admin endpoints — settin, test_create_domain_admin_returns_201(), test_create_domain_duplicate_returns_409(), test_create_domain_viewer_returns_403(), test_disable_domain_already_disabled_returns_409(), test_disable_nonexistent_domain_returns_404(), test_disable_then_enable_domain() (+23 more)

### Community 9 - "Ingestion ORM & Status"
Cohesion: 0.09
Nodes (40): Base, ARQ background worker, IngestionChunk status state machine, ingestion_triage_estimates Table, IngestionCandidate, IngestionChunk, IngestionNavPage, Discovered navigable page from an HTML site-nav crawl (§11.15). (+32 more)

### Community 10 - "Task Lifecycle"
Cohesion: 0.09
Nodes (36): claim_item(), _collect_queue_items(), confirm_via_review(), _get_active_claim(), _get_expiry_hours(), _get_record(), get_review_queue(), _get_user_domains() (+28 more)

### Community 11 - "Spec Concepts & Docs"
Cohesion: 0.08
Nodes (36): Agent Role Prefix — agent: prefix distinguishes machine from human credentials, Audit Log — append-only privileged operation trail (§9.6), Admin Break-Glass Confirm, CI Auto-fix Pipeline — event-driven GitHub Actions using synthetic.new GLM-5.1, Ingestion pipeline (triage → extraction), Iterative Ingestion — primary model; 2-5 chunk batches per pass, Knowledge Hierarchy — Domain > Workflows > Tasks + Principles, Machine Auth — API keys and OIDC client credentials (Sprint 10) (+28 more)

### Community 12 - "Workflow Lifecycle"
Cohesion: 0.15
Nodes (36): str, _count_chunks(), _count_nav_pages(), _get_ingestion_status(), _get_nav_page_status(), _insert_html_ingestion(), _insert_nav_page(), _make_ctx() (+28 more)

### Community 13 - "Notification System"
Cohesion: 0.08
Nodes (29): v1 APIRouter, Relationship ORM model.  §9.4 — infrastructure table; all writes rejected with H, Rationale: wrong taxonomy worse than no taxonomy; relationship semantics harder than they appear, list_api_keys(), List all API keys. Raw keys are never returned., list_audit_log(), Return audit log entries, newest first. Accessible by Audit and Admin roles., list_relationships() (+21 more)

### Community 14 - "API Keys & CLI Commands"
Cohesion: 0.14
Nodes (30): make_token(), Factory that produces signed RS256 JWTs for testing., _create_and_submit_task(), Tests for the Review Queue and Claiming API.  TEST_REVISED (v4.4 — dissolve Fact, All record types are domain-scoped; no-domain contributor sees nothing., An expired claim should not appear as an active claim on queue items., Create a draft task and submit it. Returns the task UUID string., test_claim_already_claimed_by_another_returns_409() (+22 more)

### Community 15 - "Test Payload Factories"
Cohesion: 0.11
Nodes (26): Minimal valid request payload factories for governed record tests.  Each factory, task_payload(), task_step_action_payload(), task_step_payload(), Tests for the Tasks lifecycle API.  TEST_REVISED (v4.4/v4.5 — dissolve Facts/Con, task.irreversible is derived: True when any step is irreversible., Confirmed tasks are immutable — steps cannot be added after confirmation., Confirmed records do not surface lint warnings (§9.10). (+18 more)

### Community 16 - "Triage Estimate Review"
Cohesion: 0.15
Nodes (25): BaseModel, _get_task_by_record_version(), get_task_diff(), get_task_version(), Tasks API endpoints, including steps.  §9.5  — Tasks schema: steps with actions,, Fetch a specific version of a Task by its stable record_id and version number., from_lint(), lint_warnings() (+17 more)

### Community 17 - "HTML Worker Tests"
Cohesion: 0.12
Nodes (24): Notification ORM model (§13)., list_notifications(), mark_all_read(), mark_read(), Notifications API endpoints (§13)., Return the current user's notifications, newest first., Mark a single notification as read., Mark all unread notifications for the current user as read. (+16 more)

### Community 18 - "Machine Credential Guard"
Cohesion: 0.14
Nodes (25): LifecycleResponse, delete_step(), update_step(), add_task_ref(), attach_principle(), detach_principle(), get_workflow(), Workflows API endpoints, including task-refs and principle-refs.  §9.5  — Workfl (+17 more)

### Community 19 - "ORM Base & Domain Models"
Cohesion: 0.19
Nodes (22): Principle ORM model.  §9.5 — foundational document-grain knowledge attached to W, confirm_principle(), create_principle(), deprecate_principle(), _get_or_404(), get_principle(), list_principle_versions(), list_principles() (+14 more)

### Community 20 - "Principles & Notifications"
Cohesion: 0.24
Nodes (24): _auth(), _make_ingestion_with_triage_complete_chunk(), Tests for triage estimate review endpoints (§11.5a).  Spec refs:   §11.5a Triage, Seed an ingestion + chunk in triage_complete state; return (ingestion_id, chunk_, Insert estimate rows and return their IDs in order., _seed_estimates(), test_approve_all_rejected_moves_chunk_to_done(), test_approve_estimates_marks_approved() (+16 more)

### Community 21 - "Domain Enforcement & Tasks"
Cohesion: 0.09
Nodes (17): ORM models for the ingestion pipeline tables (SS11.13-SS11.15, SS11.8a)., Ingestion job record — one per uploaded PDF, HTML source, or JSON payload (§11.1, CandidateCommitRequest, CandidateReviewRequest, IngestionChunkResponse, JsonIngestionRequest, JsonStepItem, JsonTaskItem (+9 more)

### Community 22 - "Search Tests"
Cohesion: 0.13
Nodes (20): _make_confirmed_task(), Tests for GET /api/v1/search (§12.2).  TEST_REVISED (v4.4 — dissolve Facts/Conce, Unknown type tokens in the filter are silently ignored (not a 422)., ?semantic=true with no embedding config falls back to fulltext gracefully., Confirmed records should not appear when searching for draft status., Create, submit, and confirm a Task containing the search keyword. Returns its id, test_domain_filter_non_matching_domain_returns_no_task(), test_search_empty_q_returns_422() (+12 more)

### Community 23 - "Lifecycle Mixin"
Cohesion: 0.19
Nodes (18): workflow_payload(), test_patch_confirmed_task_returns_422(), Tests for the Workflows lifecycle API.  Spec refs:   §9.3  Lifecycle state machi, Only confirmed Tasks may be referenced in a Workflow., test_add_confirmed_task_ref_to_workflow(), test_add_task_ref_to_confirmed_workflow_returns_422(), test_add_unconfirmed_task_ref_returns_422(), test_attach_confirmed_principle_to_workflow() (+10 more)

### Community 24 - "Workflow Tests"
Cohesion: 0.11
Nodes (14): Tests for scoped API key management and machine credential auth (§5.3, §9.6)., A valid bp_ key authenticates and can call read endpoints., A bp_ API key is rejected with 403 at any confirm endpoint., test_api_key_authenticates_for_data_endpoint(), test_create_api_key_invalid_role_returns_422(), test_create_api_key_returns_201_with_raw_key(), test_list_api_keys_does_not_return_raw_key(), test_list_api_keys_non_admin_returns_403() (+6 more)

### Community 25 - "CI Auto-Fix Pipeline"
Cohesion: 0.24
Nodes (17): Synthetic GLM-5.1 (CI auto-fix LLM), main (fix_ci), apply_files(), call_model(), extract_paths(), fix_general(), fix_pip_audit(), get_logs() (+9 more)

### Community 26 - "Embedding Worker Tests"
Cohesion: 0.12
Nodes (17): _pdf_bytes(), _pdf_upload(), Second upload of identical bytes returns the existing ingestion, no new row., Status endpoint 404s for ingestions belonging to another user (no info leak)., Empty chunk_ids list is rejected before status is checked., Cannot select chunks on a pending ingestion (not yet chunked)., Returns a files dict for httpx multipart upload., test_select_empty_chunk_ids_returns_422() (+9 more)

### Community 27 - "API Key Auth Tests"
Cohesion: 0.25
Nodes (16): _embedding_response(), _get_embedding(), _make_ctx(), Tests for the generate_embedding ARQ job (§12.1, §14).  Covers:   - No embedding, test_embedding_api_error_raises(), test_no_embedding_config_exits_cleanly(), test_principle_embedding_stored(), test_record_not_found_exits_cleanly() (+8 more)

### Community 28 - "Ingestion Dedup & Auth"
Cohesion: 0.23
Nodes (16): create_engine(), Startup hook crash-recovery (§14), Select on a ready ingestion queues matching pending chunks and returns count., Selecting a chunk already in queued status does not re-queue it., test_select_already_queued_chunk_is_skipped(), test_select_ready_ingestion_queues_chunks(), _get_chunk_status(), _insert_ingestion_and_chunk() (+8 more)

### Community 29 - "Principles Tests"
Cohesion: 0.16
Nodes (14): Human roles as defined in §5.1., Role, _authenticate_api_key(), get_arq_pool(), get_current_user(), get_token_verifier(), FastAPI dependency providers., Validate Bearer token (JWT or bp_ API key) and return the authenticated user. (+6 more)

### Community 30 - "Agent Roles & API Keys"
Cohesion: 0.13
Nodes (15): _canonical_json(), create_json_ingestion(), get_ingestion_status(), list_candidates(), list_ingestions(), list_nav_pages(), Ingestion pipeline API endpoints (§11).  PDF upload, HTML URL, JSON payload, chu, List ingestions created by the current user, newest first. (+7 more)

### Community 31 - "Dependency Injection"
Cohesion: 0.13
Nodes (15): Authentik OIDC Provider Configuration, Blueprinted Roles Property Mapping, Authentik Setup Guide, Blueprinted Platform, Technology Stack Overview, Testing Principles, Agent Roles (workflow_consumer/staleness_monitor/orphan_detector), Authentication and Authorisation Model (+7 more)

### Community 32 - "Spec Architecture Docs"
Cohesion: 0.24
Nodes (14): principle_payload(), Tests for the Principles lifecycle API.  Spec refs:   §9.3  Lifecycle state mach, test_create_principle_contributor_returns_201_draft(), test_create_principle_missing_summary_returns_422(), test_create_principle_response_has_required_fields(), test_create_principle_unauthenticated_returns_401(), test_create_principle_viewer_returns_403(), test_create_principle_with_domain() (+6 more)

### Community 33 - "Robots & Chunking Tests"
Cohesion: 0.19
Nodes (13): JSON Import Schema (v1.0), Manual JSON Authoring Guide, Extract Principle Prompt, Extract Task Prompt, Triage Category Classification, Triage Prompt, Changelog Propose Prompt (v1.1), Changelog Screen Prompt (v1.1) (+5 more)

### Community 34 - "Audit Log Schema"
Cohesion: 0.32
Nodes (12): ARQ Resumability via Application Checkpoints, Facts and Concepts Dissolved (v4.4), Human-in-the-Loop Governance, Ingestion Pipeline, Notifications System, Prompt Contracts, Record Taxonomy (Tasks, Workflows, Principles), Triage/Extraction Human Review Gate (+4 more)

### Community 35 - "JWT Auth Tests"
Cohesion: 0.24
Nodes (11): Auth failure rate limiting deferred, lifecycle_actions.py shared service, api/services/linting.py step quality warnings, Machine/human credential distinction via agent: prefix, Route deduplication via shared service layer decision, Session Sprint 10 machine auth, audit log, CLI, Session Sprint 11 Hardening (complete), Synthetic User record per API key decision (+3 more)

### Community 36 - "Prompt Loader"
Cohesion: 0.20
Nodes (11): Maps as Display Layer, MVP vs Platform Feature Continuity Audit, Export artifacts + SHA256 fingerprints (v1.1), force_submit admin override — Not needed, Hard delete — Explicitly out of scope, Return note severity (resolved in v4.8), Step linting / quality hints (resolved in v4.8), api_keys table schema (+3 more)

### Community 37 - "Storage & Ingestion Create"
Cohesion: 0.25
Nodes (10): _base_detail(), confirm_record(), deprecate_record(), Shared lifecycle mutations for governed records (tasks, workflows, principles)., confirmed → deprecated., confirmed → retired (permanent)., submitted → confirmed. Returns True if this was a break-glass confirm.      Call, submitted → returned. (+2 more)

### Community 38 - "Ingestion Table Schema"
Cohesion: 0.22
Nodes (9): load(), _load_all(), _parse_prompt_file(), Prompt, Prompt loading for the ingestion pipeline (§11.16).  Reads versioned markdown fi, A loaded prompt ready to be rendered into a message pair., Return (system_message, user_message) with variables substituted., Extract system and user_template text from a prompt markdown file. (+1 more)

### Community 39 - "HTML Ingestion Seeds"
Cohesion: 0.22
Nodes (10): API Keys Table Schema, Audit Log, CI Auto-Fix Pipeline, Machine Auth — API Keys and Agent Roles, AuditLog ORM model (§9.6)., Audit log read endpoint (§9.6, §5.1).  GET /audit   Audit role only, paginated,, AuditLogResponse, Audit log Pydantic schemas (§9.6). (+2 more)

### Community 40 - "Module Group 40"
Cohesion: 0.22
Nodes (10): Project Index (CLAUDE.md), No Machine Can Confirm, Schema-Per-Tenant Multi-Tenancy, TEST_REVISED Process, Architecture and Working Practice, Code Style Guide, Project Rules (Absolute), Absolute Rules (+2 more)

### Community 41 - "Module Group 41"
Cohesion: 0.20
Nodes (9): create_ingestion(), delete_ingestion(), Strip path components and replace unsafe characters., Upload a PDF and start the chunking job (§11.9)., _sanitise_filename(), File storage abstraction (§4.4).  v1 implements local-disk storage only. The int, Write uploaded file to local storage. Returns (storage_path, sha256_hex)., Remove the storage directory for an ingestion (no-op if absent). (+1 more)

### Community 42 - "Module Group 42"
Cohesion: 0.24
Nodes (10): Insert a minimal HTML ingestion row., Insert a minimal ingestion_nav_pages row., A page already in selected status is not re-queued., _seed_html_ingestion(), _seed_nav_page(), test_list_nav_pages_returns_pages(), test_nav_select_already_selected_page_is_skipped(), test_nav_select_empty_ids_returns_422() (+2 more)

### Community 43 - "Module Group 43"
Cohesion: 0.22
Nodes (9): Session v4.4/v4.5 backend refactor — dissolve Facts/Concepts, Embedding Generation Worker, Hybrid Search with pgvector, Backend Technology Stack, Database Stack PostgreSQL + pgvector, Search and Embeddings (§12), Sprint 7 — Search and Embeddings, Sprint 8 — Core Read Screens (Frontend) (+1 more)

### Community 44 - "Module Group 44"
Cohesion: 0.22
Nodes (9): Break-Glass Admin Confirm, Domain Scoping and Enforcement, Review Queue and Claiming, Self-Review Prohibition, Two-Directional Authoring and Governance, Domains organisational model, Lifecycle State Machine (draft→submitted→confirmed→deprecated/retired), Sprint 4 — Core Data Model and Lifecycle API (+1 more)

### Community 45 - "Module Group 45"
Cohesion: 0.32
Nodes (8): Docker Compose Production Stack, MinIO S3-Compatible Storage, Docker Compose Dev Override, Blueprinted.io Brand Logo, Authentik OIDC Provider, Docker Compose Stack, Local Dev Setup Guide, Playwright Chromium for HTML Ingestion

### Community 46 - "Module Group 46"
Cohesion: 0.25
Nodes (6): get_me(), User profile endpoints., Return the authenticated user's profile., Pydantic schemas for user API responses., Response schema for GET /api/v1/users/me., UserResponse

### Community 47 - "Module Group 47"
Cohesion: 0.25
Nodes (5): Tests for GET /api/v1/users/me., test_me_creates_user_on_first_call(), test_me_response_has_required_fields(), test_me_returns_user_profile(), test_me_syncs_updated_email()

### Community 48 - "Module Group 48"
Cohesion: 0.33
Nodes (7): Active Session Log — blueprinted.io, Auto-fix PR #3 partial rejection decision, Weekly pip-audit without --strict, Dependency Audit Workflow, Sprint 12 Next Steps, dependency-audit.yml GitHub Actions workflow, pip-audit --skip-editable step

### Community 49 - "Module Group 49"
Cohesion: 0.47
Nodes (6): extract_chunk ARQ job function, _triage_chunk ARQ job function, Session Triage/extraction split Sprint 11.5a, Ingestion Pipeline Sub-Specification, Triage Estimate Review (§11.5a), Sprint 6 — Ingestion Pipeline

### Community 50 - "Module Group 50"
Cohesion: 0.47
Nodes (5): args, command, mcpServers, context7, github

### Community 51 - "Module Group 51"
Cohesion: 0.33
Nodes (6): _build_task(), commit_candidate(), Construct a Task ORM object (without steps) from extraction JSON., Commit an accepted candidate into the governance pipeline (§11.8).      Creates, CandidateCommitResponse, Response from the commit endpoint.

### Community 52 - "Module Group 52"
Cohesion: 0.47
Nodes (5): api(), main(), psql(), Development seed script — populates the local dev database with realistic tasks., Run SQL directly via docker exec — used only for domain bootstrap.

### Community 53 - "Module Group 53"
Cohesion: 0.33
Nodes (4): Tests for the Relationships API. §9.4, §23.9  The relationships table exists as, test_create_relationship_returns_422(), test_list_relationships_contributor_returns_empty_list(), test_list_relationships_viewer_returns_empty_list()

### Community 54 - "Module Group 54"
Cohesion: 0.50
Nodes (3): _lifecycle_cols(), Return fresh lifecycle column instances for each table.      ForeignKey objects, upgrade()

### Community 55 - "Module Group 55"
Cohesion: 0.50
Nodes (3): ConfirmRequest, Shared lifecycle response schema for all governed record types.  §9.1 — identity, Optional body for confirm endpoints.      justification is required (non-empty)

### Community 56 - "Module Group 56"
Cohesion: 0.50
Nodes (4): create_html_ingestion(), _normalise_url(), Lowercase scheme+host, strip fragment, sort query params for stable dedup., Submit a URL for HTML ingestion (§11.10).      Single-page mode renders one URL

### Community 57 - "Module Group 57"
Cohesion: 0.50
Nodes (4): Select nav pages to render and chunk (§11.11).      Selected pages are queued fo, select_nav_pages(), NavSelectResponse, Response for POST /ingestions/{id}/nav-select.

### Community 58 - "Module Group 58"
Cohesion: 0.50
Nodes (4): IngestionResponse, IngestionStatusResponse, Ingestion job summary returned on create and status endpoints., Ingestion status with full chunk list (GET /ingestions/{id}/status).

### Community 59 - "Module Group 59"
Cohesion: 0.50
Nodes (4): Queue selected chunks for LLM triage and extraction (§11.5).      Callable multi, select_chunks(), Response for POST /ingestions/{id}/select., SelectChunksResponse

## Ambiguous Edges - Review These
- `Authentik OIDC Provider` → `Blueprinted.io Brand Logo`  [AMBIGUOUS]
  platform/docs/authentik-logo.svg · relation: conceptually_related_to

## Knowledge Gaps
- **53 isolated node(s):** `Testing Principles`, `Sprint History`, `Sprint 1 — Foundation`, `Blueprinted Roles Property Mapping`, `Session Protocol` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Authentik OIDC Provider` and `Blueprinted.io Brand Logo`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `make_token()` connect `API Keys & CLI Commands` to `Ingestion Pipeline Tests`, `DB Engine & Migrations`, `Spec Architecture Docs`, `Admin API Tests`, `Relationships & Triage`, `Module Group 42`, `Module Group 47`, `Test Payload Factories`, `HTML Worker Tests`, `Principles & Notifications`, `Module Group 53`, `Search Tests`, `Lifecycle Mixin`, `Workflow Tests`, `Embedding Worker Tests`, `API Key Auth Tests`, `Ingestion Dedup & Auth`?**
  _High betweenness centrality (0.247) - this node is a cross-community bridge._
- **Why does `Base` connect `DB Engine & Migrations` to `App Config & Settings`, `HTML Ingestion Seeds`, `ARQ Worker & LLM Config`, `Ingestion ORM & Status`, `Spec Concepts & Docs`, `Notification System`, `HTML Worker Tests`, `ORM Base & Domain Models`, `Domain Enforcement & Tasks`, `Principles Tests`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `User` connect `Principles Tests` to `DB Engine & Migrations`, `Auth & Audit Log Tests`, `Review Records & ORM`, `ARQ Worker & LLM Config`, `HTML Ingestion Seeds`, `Task Lifecycle`, `Triage Estimate Review`, `HTML Worker Tests`, `Machine Credential Guard`, `ORM Base & Domain Models`, `Domain Enforcement & Tasks`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 184 inferred relationships involving `make_token()` (e.g. with `test_me_returns_user_profile()` and `test_me_creates_user_on_first_call()`) actually correct?**
  _`make_token()` has 184 INFERRED edges - model-reasoned connections that need verification._
- **Are the 86 inferred relationships involving `str` (e.g. with `_store_embedding()` and `_exc_str()`) actually correct?**
  _`str` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `LifecycleResponse` (e.g. with `TaskStepActionCreate` and `TaskStepActionResponse`) actually correct?**
  _`LifecycleResponse` has 30 INFERRED edges - model-reasoned connections that need verification._