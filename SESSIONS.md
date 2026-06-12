# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-12 (repo housekeeping: core clone, READMEs, CI fix)

### Decisions
- `core` repo cloned into the local blueprinted workspace alongside `platform` and `app`; root README documents all three as independent repos.
- `graphify-out/graph.html` untracked and gitignored — it was skewing GitHub language stats to 60.9% HTML; the JSON/markdown graph data (useful to LLMs) remains committed.

### Done
- Cloned `blueprinted-io/core` into `/home/ewan/projects/blueprinted/core`.
- Rewrote READMEs for all three repos: `core` (clearer MVP status, cross-links), `app` (added stack table, auth flow, cross-links), `platform` (reframed as pre-release, cleaned structure). All three pushed.
- Created `ORG_README.md` at workspace root — ready to drop into the `blueprinted-io/.github` org profile repo.
- Fixed platform CI: ruff I001 (unsorted imports) in `api/routes/analytics.py` and `tests/test_analytics.py`; E501 line wrap in test. CI green.
- `graphify-out/graph.html` removed from git tracking; `.gitignore` updated. Pushed.

### Broken / Incomplete
- (carried) Auth failure rate limiting not implemented; Authentik theme logos broken — cosmetic.
- `app` repo has an unstaged change in `DashboardPage.tsx` — carried over from Sprint 13, not part of this session.

### Next
Sprint 13 remaining items: profile preferences PATCH, or resolve the open mvp_audit decisions (force_submit, hard delete policy). No prerequisites — all repos clean and CI green.
