# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (ingestion UI + notifications)

### Decisions
- Ingestion UI pages built across two separate sessions in this sprint; untestable until admin page adds LLM config.
- PDF upload uses `fetch` + `FormData` directly (not `api.post`) — the standard client hardcodes `Content-Type: application/json` which breaks multipart.
- `expire_review_claims` worker converted from a raw SQL UPDATE to ORM so individual claimer IDs are accessible for `claim_expired` notifications.
- SMTP email delivery deferred — spec marks it optional when unconfigured; admin page (Sprint 10) is a prerequisite.
- `record_submitted` and `claim_made` notify all domain users; `record_confirmed` / `record_returned` notify only the author; `claim_expired` notifies only the former claimer.

### Done
- Ingestion pages: `IngestionListPage`, `IngestionCreatePage` (PDF/HTML/JSON tabs), `IngestionDetailPage` (polling), `SectionSelectionPage`, `NavSelectionPage`, `CandidateReviewPage` (inline commit).
- Notifications backend: migration (`notifications` table), model, service helpers (`create_notification`, `notify_domain_users`), schemas, routes (`GET /notifications`, `POST /{id}/read`, `POST /read-all`), wired into `v1.py`.
- Notification hooks: tasks, workflows, principles (submit/confirm/return), review claim creation, worker ingestion complete/failed, worker claim expiry.
- Notifications frontend: `NotificationsPage` with per-item and bulk mark-as-read; bell badge in sidebar polling every 30 s.

### Next
Admin page (Sprint 10 prerequisite): LLM provider config, system settings, domain management. Required before ingestion pipeline can be end-to-end tested.