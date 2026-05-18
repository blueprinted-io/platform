# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (admin page + system_settings + per-job LLM resolver)

### Decisions
- `system_settings` table is a DB-backed key/value store; DB values override env vars via per-job resolver in the worker (not startup overlay), so LLM config changes take effect on the next job without a worker restart.
- LLM API keys encrypted with Fernet (keyed from `app_secret_key`); encrypted values are never returned via GET — write-only.
- `review_claim_expiry_hours` now read from `system_settings` on each claim; defaults to 48 h if not set.
- `crawl_html` robots.txt lookup replaced: was a broken try/except import of a non-existent module; now reads `SystemSetting` ORM directly.
- Admin frontend: three-tab layout (Settings / Domains / Health) under `/admin`; replaces the `ComingSoon` stub.

### Done
- Migration: `system_settings` table (key, value, encrypted, updated_at, updated_by_id).
- `api/models/settings.py`: `SystemSetting` ORM model.
- `api/services/settings_service.py`: `get_setting`, `set_setting`, Fernet encryption helpers, `load_llm_settings` per-job resolver, `LLMSettings` dataclass.
- `api/routes/admin.py`: `GET/PATCH /admin/settings`, domain CRUD (`GET/POST /admin/domains`, disable/enable), user-domain assignment (`GET/PUT /admin/users/{id}/domains`), `GET /admin/health`.
- `api/routes/v1.py`: admin router wired in.
- `workers/main.py`: `generate_embedding` and `process_chunks` use `load_llm_settings` per-job; `crawl_html` robots.txt uses `SystemSetting` ORM.
- `api/routes/review.py`: `claim_item` reads expiry hours from `system_settings`.
- Frontend: `AdminLayout`, `AdminSettingsPage`, `AdminDomainsPage` (with user assignment), `AdminHealthPage`; `api.ts` adds `put()`.

### Next
End-to-end ingestion pipeline test: add LLM config via admin settings page, run a PDF ingestion through to candidates. Machine auth (Sprint 10 remainder) is a separate workstream and not a prerequisite.