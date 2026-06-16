# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-16 (Sprint 14: ingestion UX overhaul + preferences + HTML ordering + branding)

### Decisions
- Removed "accept" as a mandatory gate before committing candidates — batch commit now accepts pending/accepted/edited directly, skips discarded and already-committed silently.
- Vite 6 `allowedHosts: true` required for LAN dev access; dev-only, not a security issue.
- Authentik branding applied via Blueprint YAML auto-applied by auth-worker; no manual Authentik UI changes needed.

### Done
- Sprint 14 item 2: HTML nav ordering — `nav_order` on `ingestion_nav_pages`, `nav_page_id` FK on `ingestion_chunks`, worker stamps both, status query orders by `nav_order`. Two migrations applied.
- Sprint 14 item 3: User preferences — JSONB `preferences` on `users`, `PATCH /users/me/preferences` with locale validation, `SettingsPage.tsx` (locale + notification toggles). TEST_REVISED (6 new tests).
- Sprint 14 item 4: Authentik branding — `blueprinted-brand.yaml` blueprint, `logo.svg`, docker-compose volume mounts for auth + auth-worker.
- Sprint 14 item 1: Ingestion UX overhaul — `POST /candidates/commit-batch` and `POST /candidates/{id}/promote` endpoints; `CandidateReviewPage` rewritten with multi-select, batch commit panel, discard, promote-back, no raw JSON. TEST_REVISED (7 new tests; fixed `_seed_nav_page` for `nav_order NOT NULL`).
- Vite LAN fix — `allowedHosts: true`; resolves `__WS_TOKEN__ is not defined` on non-localhost access.

### Next
Sprint 14 fully shipped. Run `alembic upgrade head` against the dev DB to apply the two new migrations before testing. Next candidates: force_submit policy (mvp_audit), hard-delete policy, or auth failure rate limiting.
