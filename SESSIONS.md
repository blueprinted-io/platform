# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-06 (CI auto-fix pipeline)

### Decisions
- `claude-code-action` is incompatible with non-Anthropic model providers — model name validation is in the CLI binary, not the action wrapper. Custom script is the only viable path with synthetic.new.
- GLM-5.1 (`hf:zai-org/GLM-5.1`) chosen as the fix model — only synthetic.new model returning standard `content` at scale; GLM-4.7-Flash also works but is weaker.
- Scheduled remote agent (claude.ai routines) replaced by event-driven GitHub Actions — Anthropic imposes a 5 runs/day limit on timed automations.
- Auto-fix script restricted to writing only `api/`, `tests/`, `cli/`, `workers/`, `pyproject.toml` — prevents model from overwriting workflow scripts or other sensitive paths.
- Workflow gates on `head_repository.full_name == github.repository` and checks out main (not the failing SHA) — prevents pwn-request / untrusted code execution with secrets.
- `SYNTHETIC_API_KEY` stored as GitHub Actions secret; never committed.

### Done
- `.github/workflows/auto-fix.yml`: event-driven workflow triggering on CI failure; security hardened (fork gate, branch name validation, safe checkout).
- `.github/scripts/fix_ci.py`: custom fix script calling synthetic.new OpenAI endpoint with GLM-5.1; strips GHA log prefix; path-traversal-safe allowlist; pip-audit and general (ruff/mypy/pytest) strategies.
- `platform/README.md`: Why? column added to stack table; Testing principles section added.
- 19 community skills installed globally from antigravity-awesome-skills (stack coverage + architecture/research skills).
- End-to-end verified: CI failure → auto-fix PR opened and merged successfully.

### Next
Sprint 8 complete. Close out Sprint 8 in SPRINTS.md, then plan Sprint 9. The candidate is the ingestion triage/extraction human review gate (spec §11.5a, noted in memory as planned sprint work). Run `/plan` to confirm scope against the current spec before writing any code.

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
