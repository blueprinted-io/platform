# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-29 (task diff view — §23.3)

### Decisions
- Diff endpoint returns full `TaskResponse` objects for both current and previous versions rather than a computed delta — simpler backend, frontend computes what changed.
- Diff access restricted to `_Writer` (Contributor/Admin); read-only users have no path to reach a versioned diff.
- `includeCoAuthoredBy: false` added to `~/.claude/settings.json` — co-author attribution removed from all future commits.

### Done
- `api/schemas/task.py`: `TaskDiffResponse` schema (`current`, `previous` both `TaskResponse`).
- `api/routes/tasks.py`: `GET /tasks/{record_id}/{version}/diff` — 404 for v1, returns both versions for v2+.
- `app/src/pages/TaskDiffPage.tsx`: side-by-side scalar field diff (amber highlight on changed), inline added/removed colouring for facts/concepts/tags, step-level added/removed/modified labelling.
- `app/src/App.tsx`: route `tasks/:recordId/:version/diff` wired.
- `app/src/pages/TaskDetailPage.tsx`: "View changes" link in version bar (visible when `task.version > 1`).

### Next
All §23.3 Task screens are now complete. §23.4 Workflow diff view is the natural parallel next step, or move on to another sprint item.
