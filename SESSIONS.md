# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-29 (startup hook, embedding, HTML worker tests + two bug fixes)

### Decisions
- `_store_embedding` in `workers/main.py` used `:embedding::vector` which asyncpg rejects as a syntax error. Changed to `CAST(:embedding AS vector)`. This was a latent production bug — embeddings were silently broken; the new tests exposed it.
- Playwright mocked throughout HTML worker tests — CI workflow has no `playwright install chromium` step, so launching a real browser would fail.

### Done
- `tests/test_startup_hook.py`: processing→queued reset, extracting→extraction_queued reset, re-enqueue with/without ctx['redis']. Issue 5 closed in `docs/issues.md`.
- `tests/test_embedding_worker.py`: no-config exit, record-not-found exit, principle/workflow/task happy paths (respx), API error raises HTTPStatusError.
- `tests/test_html_worker.py`: _make_chunks_from_sections and _is_robots_allowed units; crawl_html single/site-nav/error paths; render_nav_pages happy/empty/partial-failure paths.
- `workers/main.py`: CAST() fix for asyncpg embedding update.
- `docs/issues.md`: issue 5 resolved.
- CI: clean pass after two-commit fix sequence.

### Next
All tracked platform test gaps and issues are now resolved. App-side: task list screen (§23.3) is the next natural screen to build in blueprinted-io/app.
