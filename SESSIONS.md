# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

---

## Session — 2026-05-17 (workflow and principle screens)

### Decisions
- Workflow and principle detail pages use UUID-based URLs (`/workflows/:id`, `/principles/:id`) — the API routes these by primary key, not `record_id/version` as tasks do.
- Create screens added for both record types — "Save as draft" and "Save and submit" flow, matching the task pattern. Out of scope per spec but required to test the read screens.

### Done
- Workflow list screen — clickable rows, "New workflow" button.
- Workflow create screen (`/workflows/new`) — title, objective, domain, tags; draft/submit flow.
- Workflow detail screen — objective, task refs, principle refs, tags, lifecycle actions (submit/confirm/return with self-review prohibition).
- Principle list screen — clickable rows, "New principle" button.
- Principle create screen (`/principles/new`) — title, domain, summary, explanation, analogies, tags; draft/submit flow.
- Principle detail screen — summary, explanation, analogies, tags, lifecycle actions.
- Routes wired in `App.tsx`; all new/detail routes ordered correctly before `/:id` to avoid param capture.

### Next
Sprint 8 continues. Remaining unimplemented screens: Search (§23.10) and Review Queue (§23.7). Search is the more immediately useful of the two — the API endpoint (`GET /api/v1/search`) already exists.
