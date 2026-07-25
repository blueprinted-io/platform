# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-07-24 (Sprint 15: agent ingestion path — demo readiness)

### Decisions
- Chose the agent ingestion path over the formally-deferred Sprint 15 items (auth-failure rate limiting, `last_used_at` caching), driven by `docs/demo-prep.md` intent — the real gap blocking the demo narrative. Rate limiting and `last_used_at` remain deferred.
- Producer agents are cross-domain: `assert_domain_access` is waived for machine credentials at ingestion commit (`assert_domain_active` still applies); domain governance binds at human confirm instead.
- `assert_can_submit` permits the producer role — submitting is a request for review, not an approval. Confirm stays machine-barred, unchanged.
- First autonomous-mode sprint: decisions estimated from prior maintainer choices and documented rather than paused on.

### Done
- Producer role `agent:ingestion_agent` (§5.2) — an agent API credential can now drive ingestion end to end (create ingestion → commit candidates → submitted → human review queue) with no-machine-can-confirm intact. Committed and pushed to platform main.
- `require_role` widened to accept agent roles; ingestion write + commit endpoints admit the producer; domain-access waived for machine credentials.
- `tests/test_agent_ingestion.py` — 5 tests: end-to-end producer path, cross-domain waiver, machine-cannot-confirm (403), consumer-agent-cannot-ingest (403). Full suite 371 pass; ruff clean; mypy (api/cli/workers) clean.
- Spec `requirements.md` v4.11 → v4.12 documenting the role, permissions, and domain waiver.
- Corrected the stale Sprint 14 "In progress" status line in SPRINTS.md to Complete.
- CI/ops (post-sprint): patched app advisories (js-yaml, postcss) and platform pip-audit advisories (json-repair 0.60.1, msgpack 1.2.1) — all CI green.
- Repaired the CI auto-fix bot: dead model → `syn:large:text` alias; hardened `fix_ci.py` against placeholder/invalid model output (reject echoed template, validate pyproject TOML before `uv lock`). Rotated `SYNTHETIC_API_KEY` (done by operator).
- Verified the auto-fix bot end to end via a throwaway canary — it produced correct fix PRs on both the pip-audit and ruff strategies; canary and bot PRs cleaned up.

### Broken / Incomplete
- Pre-existing mypy errors remain in `seed/` and `tests/` (8 total) — outside CI's `api/ cli/ workers/` scope, so CI is unaffected. Not introduced this sprint; not fixed this sprint.

### Next
The agent ingestion path is code-complete but the demo (`docs/demo-prep.md`) is not yet exercised end to end against a running stack. Pick up: create a real `agent:ingestion_agent` key via the admin endpoint, run an agent ingestion against the deploy stack, and walk the review-queue → human-confirm flow. Prerequisite: deploy stack running and at least one contributor/reviewer account provisioned in Authentik.
