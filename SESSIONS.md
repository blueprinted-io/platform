# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-18 (CI fix + Playwright Dockerfile)

### Decisions
- `/plan` skill CI check used `displayTitle` (invalid field) piped to `/dev/null` — silent failure treated as "no runs". Fixed by using `name` field; error output now visible.
- Playwright Chromium binary was never in the Docker image — `--with-deps` fails on `python:3.12-slim` (Debian) because Ubuntu font packages are absent. Fixed by installing Chromium system deps explicitly and running `playwright install chromium` without `--with-deps`.
- Stuck HTML ingestion (status `chunking`) was reset to `failed` in the DB — the `crawl_html` job was consumed by the old worker before Playwright was available. User should delete and re-submit.

### Done
- `.claude/commands/plan.md`: `displayTitle` → `name` in both `gh run list` commands.
- `deploy/Dockerfile`: installs Chromium system deps and runs `playwright install chromium` at build time. Worker container verified: Chromium launches successfully.

### Next
End-to-end URL ingestion test: Playwright is now installed. Delete the stuck HTML ingestion and re-submit the URL to verify the full `crawl_html` → `render_nav_pages` → candidate review path. PDF ingestion is also unblocked — verify end-to-end with LLM configured.