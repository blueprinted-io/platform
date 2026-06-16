# Graph Report - .  (2026-06-12)

## Corpus Check
- 5 files · ~141,827 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1633 nodes · 3359 edges · 131 communities (103 shown, 28 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 502 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Ingestion Tests|Ingestion Tests]]
- [[_COMMUNITY_Analytics Dashboard|Analytics Dashboard]]
- [[_COMMUNITY_Auth and Dependencies|Auth and Dependencies]]
- [[_COMMUNITY_CLI Commands|CLI Commands]]
- [[_COMMUNITY_Session Archive|Session Archive]]
- [[_COMMUNITY_Triage and Audit Concepts|Triage and Audit Concepts]]
- [[_COMMUNITY_Workflow and Task Schemas|Workflow and Task Schemas]]
- [[_COMMUNITY_Database and Chunk Processing|Database and Chunk Processing]]
- [[_COMMUNITY_Admin Tests|Admin Tests]]
- [[_COMMUNITY_Ingestion Models|Ingestion Models]]
- [[_COMMUNITY_Pagination and Conftest|Pagination and Conftest]]
- [[_COMMUNITY_Config and Admin Routes|Config and Admin Routes]]
- [[_COMMUNITY_Lifecycle and Review|Lifecycle and Review]]
- [[_COMMUNITY_CI and Graph Decisions|CI and Graph Decisions]]
- [[_COMMUNITY_Test Factories|Test Factories]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 103|Community 103]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 105|Community 105]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]
- [[_COMMUNITY_Community 110|Community 110]]
- [[_COMMUNITY_Community 111|Community 111]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 113|Community 113]]
- [[_COMMUNITY_Community 114|Community 114]]
- [[_COMMUNITY_Community 115|Community 115]]
- [[_COMMUNITY_Community 121|Community 121]]
- [[_COMMUNITY_Community 123|Community 123]]
- [[_COMMUNITY_Community 126|Community 126]]
- [[_COMMUNITY_Community 127|Community 127]]
- [[_COMMUNITY_Community 128|Community 128]]
- [[_COMMUNITY_Community 129|Community 129]]
- [[_COMMUNITY_Community 130|Community 130]]

## God Nodes (most connected - your core abstractions)
1. `make_token()` - 199 edges
2. `create_engine()` - 50 edges
3. `LifecycleResponse` - 37 edges
4. `Base` - 35 edges
5. `Settings` - 32 edges
6. `task_payload()` - 30 edges
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
- **Analytics dashboard SQL queries powering contributor/reviewer/admin sections** — routes_analytics_contributor_counts_sql, routes_analytics_recently_returned_sql, routes_analytics_queue_depth_sql, routes_analytics_admin_throughput_sql, routes_analytics_staleness_sql [INFERRED 0.95]
- **Analytics Pydantic response schemas** — schemas_analytics_dashboard_response, schemas_analytics_contributor_stats, schemas_analytics_reviewer_stats, schemas_analytics_admin_stats, schemas_analytics_recent_record, schemas_analytics_domain_staleness [EXTRACTED 1.00]
- **Analytics test helper functions for task lifecycle** — tests_test_analytics_create_task_helper, tests_test_analytics_submit_task_helper, tests_test_analytics_confirm_task_helper, tests_test_analytics_return_task_helper [EXTRACTED 1.00]
- **Analytics integration test suite (9 tests)** — tests_test_analytics_test_dashboard_requires_auth, tests_test_analytics_test_dashboard_viewer_can_access, tests_test_analytics_test_contributor_stats_count_own_records, tests_test_analytics_test_recently_returned, tests_test_analytics_test_reviewer_queue_depth, tests_test_analytics_test_reviewer_queue_excludes_own, tests_test_analytics_test_admin_section_present, tests_test_analytics_test_admin_confirmed_30d, tests_test_analytics_test_reviewed_at_set_on_confirm [EXTRACTED 1.00]

## Communities (131 total, 28 thin omitted)

### Community 0 - "Ingestion Tests"
Cohesion: 0.03
Nodes (74): _pdf_bytes(), _pdf_upload(), Tests for the Ingestion Pipeline API (§11).  Spec refs:   §11.3  Ingestion pipel, force=true bypasses dedup and creates a new ingestion record., Insert a minimal HTML ingestion row., Insert a minimal ingestion_nav_pages row., A page already in selected status is not re-queued., A task item missing a required field is rejected with 422. (+66 more)

### Community 1 - "Analytics Dashboard"
Cohesion: 0.08
Nodes (48): DBSession dependency, User ORM model, return_rate_30d uses updated_at as proxy for transition date, reviewed_at never populated on confirm — fixed for staleness calculation, Role-aware fixed dashboard layout (§15 v1 design), Staleness threshold 90-day hardcoded for v1 (future system_setting), _admin_stats(), _ADMIN_THROUGHPUT_SQL — 30-day confirmed/returned counts (+40 more)

### Community 2 - "Auth and Dependencies"
Cohesion: 0.07
Nodes (43): OIDC token verification.  TokenVerifier validates RS256 JWTs issued by Authentik, Human roles as defined in §5.1., Role, Dependency factory that enforces role membership.      Usage:         @router.ge, require_role(), Enum, ReviewClaim ORM model.  Maps to the review_claims table created in migration b4c, Analytics APIRouter (+35 more)

### Community 3 - "CLI Commands"
Cohesion: 0.05
Nodes (39): api_keys_create(), api_keys_revoke(), backup(), healthcheck(), migrate(), Blueprinted CLI — all operational tasks for a running instance.  Usage:     blue, Register a new tenant schema and run its migrations., Remove a tenant schema. Irreversible — take a backup first. (+31 more)

### Community 4 - "Session Archive"
Cohesion: 0.04
Nodes (45): Session docs restructure + task create + confirm flow, Session LLM ingestion pipeline repair, response_format: json_object removed from extraction LLM, Session — admin page + system_settings + per-job LLM resolver, Session — admin settings test-connection + model picker, Session — admin users tab + CI fix, Session Close-Out — ARQ pool wiring + Sprint 7 Search and Embeddings, Session Close-Out — Auth Flow Debugging (+37 more)

### Community 5 - "Triage and Audit Concepts"
Cohesion: 0.07
Nodes (44): Agent Role Prefix — agent: prefix distinguishes machine from human credentials, Audit Log — append-only privileged operation trail (§9.6), Admin Break-Glass Confirm, CI Auto-fix Pipeline — event-driven GitHub Actions using synthetic.new GLM-5.1, Ingestion pipeline (triage → extraction), Iterative Ingestion — primary model; 2-5 chunk batches per pass, Machine Auth — API keys and OIDC client credentials (Sprint 10), No Machine Can Confirm — absolute constraint on govern record lifecycle (+36 more)

### Community 6 - "Workflow and Task Schemas"
Cohesion: 0.12
Nodes (37): BaseModel, LifecycleResponse, get_workflow(), Workflows API endpoints, including task-refs and principle-refs.  §9.5  — Workfl, LifecycleResponse, Base response schema carrying the shared identity and lifecycle fields., from_lint(), lint_warnings() (+29 more)

### Community 7 - "Database and Chunk Processing"
Cohesion: 0.13
Nodes (35): create_engine(), _chat_response(), _get_candidates(), _get_chunk(), _get_estimates(), _insert_extraction_queued_chunk(), _insert_queued_chunk(), _make_env_settings() (+27 more)

### Community 8 - "Admin Tests"
Cohesion: 0.08
Nodes (31): _admin_headers(), Tests for the Admin API (§23.11).  Spec refs:   §23.11  Admin endpoints — settin, test_create_domain_admin_returns_201(), test_create_domain_duplicate_returns_409(), test_create_domain_viewer_returns_403(), test_disable_domain_already_disabled_returns_409(), test_disable_nonexistent_domain_returns_404(), test_disable_then_enable_domain() (+23 more)

### Community 9 - "Ingestion Models"
Cohesion: 0.09
Nodes (39): Base, ARQ background worker, IngestionChunk status state machine, ingestion_triage_estimates Table, IngestionCandidate, IngestionChunk, IngestionNavPage, Discovered navigable page from an HTML site-nav crawl (§11.15). (+31 more)

### Community 10 - "Pagination and Conftest"
Cohesion: 0.11
Nodes (36): make_token(), Factory that produces signed RS256 JWTs for testing., Tests for the §6 pagination convention (v4.11) on governed record lists.  Covers, test_list_rejects_out_of_bounds_params(), test_list_returns_page_envelope_with_defaults(), test_list_tasks_offset_past_end_returns_empty_page(), test_list_tasks_respects_limit(), test_list_tasks_returns_latest_version_only_and_total_counts_records() (+28 more)

### Community 11 - "Config and Admin Routes"
Cohesion: 0.08
Nodes (30): get_settings(), Bootstrap configuration loaded from environment variables.  Runtime configuratio, System Settings Store, SystemSetting ORM model (§10.4)., admin_health(), disable_domain(), enable_domain(), _get_domain_or_404() (+22 more)

### Community 12 - "Lifecycle and Review"
Cohesion: 0.09
Nodes (37): is_machine_credential(), Return True if all roles in the list are agent-prefixed (§5.3)., Domain Enforcement (§7.3), confirm_task(), add_task_ref(), attach_principle(), confirm_workflow(), create_workflow() (+29 more)

### Community 13 - "CI and Graph Decisions"
Cohesion: 0.06
Nodes (37): Session CI auto-fix pipeline, Session Fable 5 review documentation + graphify wiring, GLM-5.1 chosen as auto-fix model, graphify-out/ committed to git decision, Capture: Fourth source type (capture ingestion with event stream + screenshots), Capture: Full capture tooling (desktop/extension with pre-submission editing), Capture-based ingestion (workflow recording as a source type), Recorded workflow sessions are step-shaped (one session ≈ one task candidate); composes with governance instead of competing; redaction must happen client-side at capture time; never-confirmed rule applies unchanged (+29 more)

### Community 14 - "Test Factories"
Cohesion: 0.11
Nodes (26): Minimal valid request payload factories for governed record tests.  Each factory, task_payload(), task_step_action_payload(), task_step_payload(), Tests for the Tasks lifecycle API.  TEST_REVISED (v4.4/v4.5 — dissolve Facts/Con, task.irreversible is derived: True when any step is irreversible., Confirmed tasks are immutable — steps cannot be added after confirmation., Confirmed records do not surface lint warnings (§9.10). (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.20
Nodes (29): healthz(), GET /healthz — public endpoint, no auth required.  Checks database connectivity, create_html_ingestion(), Submit a URL for HTML ingestion (§11.10).      Single-page mode renders one URL, str, _count_chunks(), _count_nav_pages(), _get_ingestion_status() (+21 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (28): Embedding Lifecycle (§12.1), LLMSettings, load_llm_settings(), Load LLM config from system_settings, falling back to env Settings.      The per, Resolved LLM configuration loaded from system_settings (per-job resolver)., Session 2026-05-29 — Worker Tests + asyncpg CAST() Embedding Fix, _embedding_response(), _get_embedding() (+20 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (26): Principle ORM model.  §9.5 — foundational document-grain knowledge attached to W, confirm_principle(), create_principle(), deprecate_principle(), _get_or_404(), get_principle(), list_principle_versions(), list_principles() (+18 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (27): Task, TaskStep, TaskStepAction, _build_steps(), _build_task(), commit_candidate(), Construct a Task ORM object (without steps) from extraction JSON., Attach TaskStep and TaskStepAction children to a Task. (+19 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (23): Notification ORM model (§13)., list_notifications(), mark_all_read(), mark_read(), Notifications API endpoints (§13)., Return the current user's notifications, newest first., Mark a single notification as read., Mark all unread notifications for the current user as read. (+15 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (25): HTML Ingestion and Nav Discovery (§11.10, §11.11), Select nav pages to render and chunk (§11.11).      Selected pages are queued fo, select_nav_pages(), test_is_robots_allowed_blocks(), test_is_robots_allowed_permits(), test_is_robots_allowed_unreachable_defaults_to_true(), test_make_chunks_empty_sections(), test_make_chunks_populates_fields() (+17 more)

### Community 21 - "Community 21"
Cohesion: 0.24
Nodes (24): _auth(), _make_ingestion_with_triage_complete_chunk(), Tests for triage estimate review endpoints (§11.5a).  Spec refs:   §11.5a Triage, Seed an ingestion + chunk in triage_complete state; return (ingestion_id, chunk_, Insert estimate rows and return their IDs in order., _seed_estimates(), test_approve_all_rejected_moves_chunk_to_done(), test_approve_estimates_marks_approved() (+16 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (24): Nav pages endpoint rejects non-HTML ingestions., Insert a minimal ingestion row owned by user_id., Insert a minimal ingestion_candidates row., Candidate list for another user's ingestion is opaque 404., Cannot commit a candidate that has not been accepted., A contributor not assigned to the domain gets 403., _seed_candidate(), _seed_ingestion() (+16 more)

### Community 23 - "Community 23"
Cohesion: 0.15
Nodes (21): Triage/Extraction Human Review Gate, LLM Provider Strategy (§11.1, §11.2), Estimate Review UI, Session 2026-05-18 — LLM Ingestion Pipeline Repair (json_repair, fence stripping), Session 2026-05-27 — Triage/Extraction Split (§11.5a), exc_str(), Return a non-empty string describing an exception.      Some httpx exceptions (e, extract_chunk() (+13 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (19): Search API endpoint (§12.2).  GET /api/v1/search  — full-text and optional seman, Search across all governed record types.      Full-text search is always perform, search_records(), Search API schemas (§12.2)., SearchResponse, SearchResult, _active_configs(), _fts_leg() (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (20): _make_confirmed_task(), Tests for GET /api/v1/search (§12.2).  TEST_REVISED (v4.4 — dissolve Facts/Conce, Unknown type tokens in the filter are silently ignored (not a 422)., ?semantic=true with no embedding config falls back to fulltext gracefully., Confirmed records should not appear when searching for draft status., Create, submit, and confirm a Task containing the search keyword. Returns its id, test_domain_filter_non_matching_domain_returns_no_task(), test_search_empty_q_returns_422() (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (16): Raised when a JWT cannot be verified., Decode and verify a JWT. Returns the verified claims dict.          Raises Token, TokenVerificationError, get_session(), Async SQLAlchemy engine and session management., _authenticate_api_key(), get_arq_pool(), get_current_user() (+8 more)

### Community 27 - "Community 27"
Cohesion: 0.20
Nodes (15): Base, Shared declarative base for all ORM models., DeclarativeBase, LifecycleMixin, Shared identity and lifecycle columns inherited by all governed record tables., Task ORM models.  §9.5 — governed procedure unit. The atomic unit of knowledge i, TaskStepImage, User ORM model.  Users are provisioned just-in-time on first authenticated reque (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (13): ORM models for the ingestion pipeline tables (SS11.13-SS11.15, SS11.8a)., Ingestion job record — one per uploaded PDF, HTML source, or JSON payload (§11.1, CandidateCommitRequest, HtmlIngestionRequest, IngestionCandidateResponse, JsonStepItem, JsonTaskItem, Pydantic schemas for ingestion pipeline API (§11). (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.19
Nodes (18): workflow_payload(), test_patch_confirmed_task_returns_422(), Tests for the Workflows lifecycle API.  Spec refs:   §9.3  Lifecycle state machi, Only confirmed Tasks may be referenced in a Workflow., test_add_confirmed_task_ref_to_workflow(), test_add_task_ref_to_confirmed_workflow_returns_422(), test_add_unconfirmed_task_ref_returns_422(), test_attach_confirmed_principle_to_workflow() (+10 more)

### Community 30 - "Community 30"
Cohesion: 0.11
Nodes (14): Tests for scoped API key management and machine credential auth (§5.3, §9.6)., A valid bp_ key authenticates and can call read endpoints., A bp_ API key is rejected with 403 at any confirm endpoint., test_api_key_authenticates_for_data_endpoint(), test_create_api_key_invalid_role_returns_422(), test_create_api_key_returns_201_with_raw_key(), test_list_api_keys_does_not_return_raw_key(), test_list_api_keys_non_admin_returns_403() (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.15
Nodes (18): extract_chunk ARQ job function, _triage_chunk ARQ job function, Session Triage/extraction split Sprint 11.5a, Domain Scoping and Enforcement, Maps as Display Layer, Prompt Contracts, Two-Directional Authoring and Governance, Triage stops at triage_complete with estimate rows; extraction is a separate ARQ job triggered by approve; reference_material/skip chunks skip to done; idempotency via chunk_id + record_type guard (+10 more)

### Community 32 - "Community 32"
Cohesion: 0.24
Nodes (17): Synthetic GLM-5.1 (CI auto-fix LLM), main (fix_ci), apply_files(), call_model(), extract_paths(), fix_general(), fix_pip_audit(), get_logs() (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (15): _canonical_json(), create_json_ingestion(), get_ingestion_status(), list_candidates(), list_nav_pages(), _normalise_url(), Ingestion pipeline API endpoints (§11).  PDF upload, HTML URL, JSON payload, chu, Return ingestion with its full chunk list (§11.5 section selection screen). (+7 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (11): ArqPool dependency, client(), pytest fixtures for the Blueprinted test suite.  Test DB setup runs via asyncio., Pre-seed the test domain and all contributor users with domain assignments., Async HTTP client with lifespan started and StubTokenVerifier installed., Test stub for arq.connections.ArqRedis. Records calls without touching Redis., Create all ORM tables once per session, outside the async event loop., setup_test_db() (+3 more)

### Community 35 - "Community 35"
Cohesion: 0.23
Nodes (13): AgentRole, Machine credential roles as defined in §5.2. Available from Sprint 10., ApiKey, create_api_key(), _generate_key(), Admin API key management endpoints (§5.3, §9.6).  GET    /admin/api-keys, Return (raw_key, key_prefix, key_hash)., Create a scoped API key. The raw key is returned once — store it securely. (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.21
Nodes (15): API Keys Table Schema, Break-Glass Admin Confirm, Facts and Concepts Dissolved (v4.4), Human-in-the-Loop Governance, Lifecycle State Machine, Machine Auth — API Keys and Agent Roles, No-Machine-Can-Confirm (§10.2, §5.3), Record Taxonomy (Tasks, Workflows, Principles) (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (15): Authentik OIDC Provider Configuration, Blueprinted Roles Property Mapping, Authentik Setup Guide, Blueprinted Platform, Technology Stack Overview, Testing Principles, Agent Roles (workflow_consumer/staleness_monitor/orphan_detector), Authentication and Authorisation Model (+7 more)

### Community 38 - "Community 38"
Cohesion: 0.24
Nodes (14): principle_payload(), Tests for the Principles lifecycle API.  Spec refs:   §9.3  Lifecycle state mach, test_create_principle_contributor_returns_201_draft(), test_create_principle_missing_summary_returns_422(), test_create_principle_response_has_required_fields(), test_create_principle_unauthenticated_returns_401(), test_create_principle_viewer_returns_403(), test_create_principle_with_domain() (+6 more)

### Community 39 - "Community 39"
Cohesion: 0.29
Nodes (13): Startup hook crash-recovery (§14), _get_chunk_status(), _insert_ingestion_and_chunk(), Tests for the ARQ worker startup hook (§14, issue 5).  Covers:   - processing →, test_startup_populates_ctx(), test_startup_reenqueues_extraction_queued_chunks(), test_startup_resets_extracting_to_extraction_queued(), test_startup_resets_processing_to_queued() (+5 more)

### Community 40 - "Community 40"
Cohesion: 0.19
Nodes (13): JSON Import Schema (v1.0), Manual JSON Authoring Guide, Extract Principle Prompt, Extract Task Prompt, Triage Category Classification, Triage Prompt, Changelog Propose Prompt (v1.1), Changelog Screen Prompt (v1.1) (+5 more)

### Community 41 - "Community 41"
Cohesion: 0.17
Nodes (12): Session v4.4/v4.5 backend refactor — dissolve Facts/Concepts, CI Auto-Fix Pipeline, Embedding Generation Worker, Hybrid Search with pgvector, Backend Technology Stack, Database Stack PostgreSQL + pgvector, Search and Embeddings (§12), Active Session (SESSIONS.md) (+4 more)

### Community 42 - "Community 42"
Cohesion: 0.24
Nodes (9): create_session_factory(), configure_logging(), structlog configuration — JSON output, request ID propagation.  Call configure_l, Strip known secret field names from log events before output., Configure structlog for JSON output. Call once at startup., _redact_secrets(), create_app(), lifespan() (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.29
Nodes (8): _make_raw(), Tests for JWT token verification logic., test_expired_token_raises(), test_extract_roles_returns_list(), test_tampered_token_raises(), test_valid_token_decodes(), test_wrong_audience_raises(), test_wrong_issuer_raises()

### Community 44 - "Community 44"
Cohesion: 0.20
Nodes (10): Audit Log, AuditLog ORM model (§9.6)., Revoke an API key. Immediate effect — any bearer using this key gets 401., revoke_api_key(), Audit log read endpoint (§9.6, §5.1).  GET /audit   Audit role only, paginated,, AuditLogResponse, Audit log Pydantic schemas (§9.6)., Audit log write helpers (§9.6). (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (11): HTML Ingestion (Playwright Crawl), Ingestion Pipeline, Ingestion Queue Routing, JSON Ingestion, Notifications System, LLM JSON Parsing (_parse_llm_json + json_repair), Review Claims and Enforcement, Worker Startup Recovery Hook (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.27
Nodes (10): lifecycle_actions.py shared service, api/services/linting.py step quality warnings, Machine/human credential distinction via agent: prefix, Route deduplication via shared service layer decision, Session Sprint 10 machine auth, audit log, CLI, Session Sprint 11 Hardening (complete), Synthetic User record per API key decision, audit_log table schema (+2 more)

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (9): create_ingestion(), delete_ingestion(), Strip path components and replace unsafe characters., Upload a PDF and start the chunking job (§11.9)., _sanitise_filename(), File storage abstraction (§4.4).  v1 implements local-disk storage only. The int, Write uploaded file to local storage. Returns (storage_path, sha256_hex)., Remove the storage directory for an ingestion (no-op if absent). (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.24
Nodes (10): Audit Log, Authentik Identity Provider, Break-Glass Confirm, Domain Enforcement (§7.3), Shared Lifecycle Actions Service, Governance Lifecycle State Machine, Machine Auth via API Keys, OIDC PKCE Auth Flow (+2 more)

### Community 49 - "Community 49"
Cohesion: 0.20
Nodes (10): Auth failure rate limiting deferred, Embedding Generation Worker, Fable 5 Review Hardening Roadmap, Facts/Concepts Dissolution (v4.4), Page Envelope (v4.11 Pagination Convention), Hybrid Search Service, slowapi Rate Limiting, api.getAllPages Walker (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (10): worker-ingestion service (ingestion ARQ worker), Pagination Convention — Page Envelope (§6, v4.11), Startup Hook Chunk Recovery (ARQ Resumability), Two-Worker Split (§14, v4.11), Session 2026-06-11 — Sprint 12: Pagination + Worker Split, ARQ ingestion worker configuration., Ingestion worker startup hook — LOAD-BEARING, do not remove (§14).      Initiali, startup() (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.22
Nodes (9): load(), Return the cached Prompt for the given pipeline stage.      Raises KeyError if s, process_chunks(), Run LLM triage on queued chunks (§11.3 stage 3, §14).      Each chunk moves to t, chunk_pdf(), _extract_chunks_from_pdf(), PDF chunking job (§11.9, §14). Runs on the ingestion worker., Parse a PDF into chunk dicts using PyMuPDF hybrid outline+heading strategy (§11. (+1 more)

### Community 52 - "Community 52"
Cohesion: 0.28
Nodes (7): _load_all(), _parse_prompt_file(), Prompt, Prompt loading for the ingestion pipeline (§11.16).  Reads versioned markdown fi, A loaded prompt ready to be rendered into a message pair., Return (system_message, user_message) with variables substituted., Extract system and user_template text from a prompt markdown file.

### Community 53 - "Community 53"
Cohesion: 0.25
Nodes (9): Project Index (CLAUDE.md), Schema-Per-Tenant Multi-Tenancy, TEST_REVISED Process, Architecture and Working Practice, Code Style Guide, Project Rules (Absolute), Absolute Rules, Session Protocol (+1 more)

### Community 54 - "Community 54"
Cohesion: 0.22
Nodes (9): Rate Limiting (§17.1, Sprint 11), MVP vs Platform Feature Continuity Audit, Export artifacts + SHA256 fingerprints (v1.1), force_submit admin override — Not needed, Hard delete — Explicitly out of scope, Return note severity (resolved in v4.8), Step linting / quality hints (resolved in v4.8), Step Quality Linting (§9.10) (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.31
Nodes (8): _base_detail(), deprecate_record(), Shared lifecycle mutations for governed records (tasks, workflows, principles)., confirmed → deprecated., confirmed → retired (permanent)., submitted → returned., retire_record(), return_record()

### Community 57 - "Community 57"
Cohesion: 0.29
Nodes (5): Relationship ORM model.  §9.4 — infrastructure table; all writes rejected with H, Rationale: wrong taxonomy worse than no taxonomy; relationship semantics harder than they appear, Relationships API endpoints. §9.4, §23.9  All writes rejected with HTTP 422 in v, Relationship response schema. §9.4, RelationshipResponse

### Community 58 - "Community 58"
Cohesion: 0.25
Nodes (6): get_me(), User profile endpoints., Return the authenticated user's profile., Pydantic schemas for user API responses., Response schema for GET /api/v1/users/me., UserResponse

### Community 59 - "Community 59"
Cohesion: 0.32
Nodes (5): _enqueue_call_sites(), Worker queue routing tests (§14, v4.11).  An ARQ worker fails any job whose func, Return (location, job_name, call_text) for every enqueue_job call in api/ and wo, test_enqueue_sites_route_to_the_owning_queue(), test_every_enqueued_function_is_registered_on_a_worker()

### Community 60 - "Community 60"
Cohesion: 0.32
Nodes (8): Docker Compose Production Stack, MinIO S3-Compatible Storage, Docker Compose Dev Override, Blueprinted.io Brand Logo, Authentik OIDC Provider, Docker Compose Stack, Local Dev Setup Guide, Playwright Chromium for HTML Ingestion

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (5): Tests for GET /api/v1/users/me., test_me_creates_user_on_first_call(), test_me_response_has_required_fields(), test_me_returns_user_profile(), test_me_syncs_updated_email()

### Community 62 - "Community 62"
Cohesion: 0.29
Nodes (5): Return the roles list from claims, defaulting to empty., TokenVerifier for tests — verifies against a supplied RSA public key.      No HT, Verifies RS256 JWTs against a JWKS endpoint.      Fetches and caches JWKS on fir, TokenVerifier, verifier()

### Community 63 - "Community 63"
Cohesion: 0.29
Nodes (4): Request ID middleware and security headers., Attach a unique request ID to every request and response.      Binds the ID to s, RequestIDMiddleware, BaseHTTPMiddleware

### Community 64 - "Community 64"
Cohesion: 0.29
Nodes (7): v1 APIRouter, list_api_keys(), List all API keys. Raw keys are never returned., list_audit_log(), Return audit log entries, newest first. Accessible by Audit and Admin roles., list_relationships(), list_workflows()

### Community 65 - "Community 65"
Cohesion: 0.38
Nodes (6): get_url(), Alembic migration environment.  Uses the synchronous psycopg2 driver for CLI mig, Run migrations without a live database connection (generates SQL)., Run migrations against a live database connection., run_migrations_offline(), run_migrations_online()

### Community 66 - "Community 66"
Cohesion: 0.33
Nodes (6): list_tasks(), Page, Generic pagination envelope for list endpoints.  §6 — API pagination convention, Paginated response envelope., Fetch every page of a list endpoint, returning (all items, reported total)., _walk_all_pages()

### Community 67 - "Community 67"
Cohesion: 0.38
Nodes (7): test_validate_task_empty_steps(), test_validate_task_missing_field(), test_validate_task_valid(), Return an error string if the task candidate is missing required fields., _validate_task(), Return an error string if the task candidate is missing required fields., _validate_task()

### Community 68 - "Community 68"
Cohesion: 0.29
Nodes (7): ARQ Resumability via Application Checkpoints, Ingestion Pipeline, Notifications System, Issues Tracker, Iterative Ingestion as Primary Model, JSON Ingestion (§11.12), PDF Ingestion (§11.9)

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (5): dispose_worker_ctx(), Shared worker plumbing: ctx init/teardown and error formatting., Dispose the database engine created by init_worker_ctx., Ingestion ARQ worker entrypoint (§14).  Start with: arq workers.ingestion.Worker, shutdown()

### Community 70 - "Community 70"
Cohesion: 0.33
Nodes (7): Active Session Log — blueprinted.io, Auto-fix PR #3 partial rejection decision, Weekly pip-audit without --strict, Dependency Audit Workflow, Sprint 12 Next Steps, dependency-audit.yml GitHub Actions workflow, pip-audit --skip-editable step

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (5): Domain, Domain and UserDomain ORM models.  §7.1 — domain registry and user assignment, UserDomain, create_domain(), replace_user_domains()

### Community 72 - "Community 72"
Cohesion: 0.33
Nodes (6): delete_step(), update_step(), detach_principle(), remove_task_ref(), assert_can_mutate_refs(), Raise 422 if steps/refs cannot be added to a record in its current status.

### Community 73 - "Community 73"
Cohesion: 0.47
Nodes (5): args, command, mcpServers, context7, github

### Community 74 - "Community 74"
Cohesion: 0.47
Nodes (6): Knowledge Hierarchy — Domain > Workflows > Tasks + Principles, Principle schema, Record Taxonomy (Principles/Tasks/Workflows/Relationships), Relationship Kind Taxonomy (empty in v1), Task schema with steps/actions/images, Workflow schema with task refs and principle refs

### Community 75 - "Community 75"
Cohesion: 0.47
Nodes (5): api(), main(), psql(), Development seed script — populates the local dev database with realistic tasks., Run SQL directly via docker exec — used only for domain bootstrap.

### Community 76 - "Community 76"
Cohesion: 0.40
Nodes (6): api service (FastAPI), auth service (Authentik OIDC), db service (PostgreSQL 16 + pgvector), redis service (ARQ broker + rate limit backend), storage service (MinIO, optional), worker service (default ARQ worker)

### Community 77 - "Community 77"
Cohesion: 0.33
Nodes (4): Tests for the Relationships API. §9.4, §23.9  The relationships table exists as, test_create_relationship_returns_422(), test_list_relationships_contributor_returns_empty_list(), test_list_relationships_viewer_returns_empty_list()

### Community 79 - "Community 79"
Cohesion: 0.40
Nodes (4): Review Queue Claiming Model (§8.2), expire_review_claims(), Scheduled maintenance jobs (§8.2, §14). Runs on the default worker., Release review claims whose expiry has passed (§8.2, §14).      Runs every 15 mi

### Community 80 - "Community 80"
Cohesion: 0.50
Nodes (3): _lifecycle_cols(), Return fresh lifecycle column instances for each table.      ForeignKey objects, upgrade()

### Community 81 - "Community 81"
Cohesion: 0.50
Nodes (3): ConfirmRequest, Shared lifecycle response schema for all governed record types.  §9.1 — identity, Optional body for confirm endpoints.      justification is required (non-empty)

### Community 82 - "Community 82"
Cohesion: 0.50
Nodes (4): Queue selected chunks for LLM triage and extraction (§11.5).      Callable multi, select_chunks(), Response for POST /ingestions/{id}/select., SelectChunksResponse

### Community 83 - "Community 83"
Cohesion: 0.50
Nodes (4): IngestionResponse, IngestionStatusResponse, Ingestion job summary returned on create and status endpoints., Ingestion status with full chunk list (GET /ingestions/{id}/status).

## Ambiguous Edges - Review These
- `Authentik OIDC Provider` → `Blueprinted.io Brand Logo`  [AMBIGUOUS]
  platform/docs/authentik-logo.svg · relation: conceptually_related_to

## Knowledge Gaps
- **82 isolated node(s):** `Testing Principles`, `Sprint History`, `Sprint 1 — Foundation`, `Blueprinted Roles Property Mapping`, `Session Protocol` (+77 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Authentik OIDC Provider` and `Blueprinted.io Brand Logo`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `make_token()` connect `Pagination and Conftest` to `Ingestion Tests`, `Analytics Dashboard`, `Community 34`, `CLI Commands`, `Community 38`, `Admin Tests`, `Community 77`, `Test Factories`, `Community 16`, `Community 61`, `Community 19`, `Community 21`, `Community 22`, `Community 25`, `Community 29`, `Community 30`?**
  _High betweenness centrality (0.231) - this node is a cross-community bridge._
- **Why does `Ingestion Pipeline` connect `Community 68` to `Community 36`, `Ingestion Models`, `Config and Admin Routes`, `Community 51`, `Community 20`, `Community 23`, `Community 31`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `Sprint 6 — Ingestion Pipeline` connect `Community 31` to `Community 41`, `Community 68`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 197 inferred relationships involving `make_token()` (e.g. with `test_me_returns_user_profile()` and `test_me_creates_user_on_first_call()`) actually correct?**
  _`make_token()` has 197 INFERRED edges - model-reasoned connections that need verification._
- **Are the 86 inferred relationships involving `str` (e.g. with `_store_embedding()` and `_exc_str()`) actually correct?**
  _`str` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `LifecycleResponse` (e.g. with `TaskStepActionCreate` and `TaskStepActionResponse`) actually correct?**
  _`LifecycleResponse` has 30 INFERRED edges - model-reasoned connections that need verification._