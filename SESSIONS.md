# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-11 (Sprint 13: analytics dashboard + production DB migrations)

### Decisions
- Dashboard is fixed/role-aware for v1 (§15); customisable layout model is v2 — no abstractions built for it now, full rebuild when the time comes.
- Staleness threshold hardcoded at 90 days for v1; noted as a future system_setting candidate.
- return_rate_30d uses updated_at as a proxy for transition date (no transition history table); accurate enough for v1.

### Done
- `reviewed_at` was never populated on confirm — fixed in both `lifecycle_actions.confirm_record` and the inline path in `review.py`; required for staleness calculation to be meaningful.
- `GET /api/v1/analytics/dashboard`: contributor stats (drafts/submitted/returned + recently-returned list), reviewer queue depth, admin section (confirmed_30d, return_rate_30d, stale_confirmed_count, stale_by_domain). Schema in `api/schemas/analytics.py`, route in `api/routes/analytics.py`.
- 9 integration tests in `tests/test_analytics.py`; 354 total passing. Two new test subs added to conftest (`author-an-001`, `reviewer-an-001`).
- `DashboardPage.tsx` replaced: stat card grid, recently-returned list with edit links, review queue depth card, admin platform-health section with stale-by-domain breakdown.
- Production DB was 4 migrations behind (stuck at Sprint 10 triage-estimates); applied `return_severity`, `api_keys/audit_log`, `api_key_expires_at`, `(record_id, version)` unique constraint. API, worker, worker-ingestion rebuilt and restarted.

### Broken / Incomplete
- (carried) Auth failure rate limiting not implemented; Authentik theme logos broken — cosmetic.

### Next
Sprint 13 remaining items: profile preferences PATCH, or resolve the open mvp_audit decisions (force_submit, hard delete policy). Both are small. No prerequisites — platform and app repos are clean, deployed, and serving the dashboard.
