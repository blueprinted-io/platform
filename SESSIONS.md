# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (admin users tab + CI fix)

### Decisions
- Admin users implicitly own all active domains (§7.2 already enforced at API layer); domain assignment UI suppressed for admin-role users is noted for a follow-up polish pass.
- `UserDomainSection` moved from DomainsPage to UsersPage — domain assignment belongs with user management, not domain registry.
- CI check in `/plan` skill was broken: `gh run list` used `displayTitle` field which doesn't exist in the installed `gh` version; failed silently due to `2>/dev/null`. Fix to the skill command is outstanding.
- `test_process_chunks.py` failures predated this session: tests passed raw `Settings` objects to `_process_single_chunk` which expects `LLMSettings`. Fixed by updating the fixture and removing inline `Settings` construction at call sites.

### Done
- `api/schemas/admin.py`: `UserListResponse` schema.
- `api/routes/admin.py`: `GET /admin/users` — lists all users ordered by email, Admin only.
- `app/src/pages/admin/AdminUsersPage.tsx`: user table with role badges; per-user domain assignment panel.
- `app/src/pages/admin/AdminDomainsPage.tsx`: removed `UserDomainSection`; fixed bug calling non-existent `GET /users` (now `GET /admin/users`).
- `app/src/pages/admin/AdminLayout.tsx`: added "Users" nav item.
- `app/src/App.tsx`: wired `/admin/users` route.
- `tests/test_process_chunks.py`: replaced inline `Settings` constructions with `LLMSettings` fixture; `test_process_chunks_with_llm_processes_all_queued` retains `Settings` in `ctx["settings"]` (correct path).
- `workers/main.py`: removed dead `original_filename` assignment (ruff F841). CI green.

### Next
End-to-end ingestion test: PDF path is unblocked. URL ingestion hung and failed — cause not yet diagnosed (Playwright availability or LLM config issue); check worker logs on next attempt. Also fix the `/plan` skill's CI check command (`displayTitle` → `name`).