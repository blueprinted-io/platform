# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-17 (task revise flow)

### Decisions
- Revise is allowed from any status, not just returned — the governance cycle handles it regardless of starting state.
- Returned tasks inherit the return note as their revision note automatically; all other statuses require an explicit note.
- `assert_can_revise` no longer checks status — only creator-or-admin ownership is enforced (§9.3).
- `list_tasks` returns only the latest version per `record_id` (subquery with `func.max`); older versions accessible via version history strip on the detail page.
- Duplicate draft prevention: revise endpoint returns 409 if `record_id/version+1` already exists.

### Done
- `POST /{record_id}/{version}/revise` endpoint: copies task and all steps/actions into a new draft version.
- `GET /{record_id}/versions` endpoint: returns `TaskVersionSummary` list for version history strip.
- `list_tasks` deduped to latest version per record; version history strip on `TaskDetailPage` links to older versions.
- `ReviseRequest` and `TaskVersionSummary` schemas added; `change_note` exposed on `LifecycleResponse`.
- `ReturnDialog` made generic with optional label/copy props — reused for revision note collection.
- Frontend revise flow: returned tasks fire immediately; all other statuses open the dialog for a note.
- Revision/return note shown to all users on the detail page (label adapts: "Return note" vs "Revision note").
- Disabled Authentik iframe silent renew (`automaticSilentRenew: false`) to eliminate `X-Frame-Options` console noise.
- `TaskEditPage` save uses `task.id` (UUID) for PATCH, not route params.

### Next
Apply the same revise flow to workflows and principles — the backend `assert_can_revise` signature change (removed `record_status`) is already committed, but the route handlers and frontend detail pages for both record types still need the revision note enforcement and dialog wired in.