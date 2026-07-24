# Plan: Sprint 15 — Agent Ingestion Path (demo readiness)

**Source**: `docs/demo-prep.md` intent + Fable 5 roadmap divergence (see Decision below)
**Complexity**: Small–Medium (backend only)
**Spec bump**: v4.10 → v4.11

## Decision record (autonomous — documented per session protocol)

Chosen over the formally-deferred Sprint 15 items (auth-failure rate limiting,
`last_used_at` caching). Rationale: `docs/demo-prep.md` is the freshest, most
concrete statement of intent (untracked, product-goal, "the demo moment"), and
it points at a **real gap**: an agent API credential cannot currently drive
ingestion, because every ingestion write endpoint requires human
`Role.CONTRIBUTOR`/`Role.ADMIN`, while API keys can only carry a consumer
`AgentRole`. Rate limiting is deferred again (genuinely lower priority).

## Summary
Add a producer machine role `agent:ingestion_agent` that may drive the ingestion
pipeline end-to-end — create ingestion, list/commit candidates, reach `submitted`
so content lands in the human review queue — while the no-machine-can-confirm
invariant stays intact (confirm is unconditionally blocked for all `agent:` roles
by `assert_can_confirm`). This makes the demo narrative real: machine drafts and
submits, human confirms, enforced in code.

## Sub-decisions (estimated maintainer's choice)
1. **Domain access on commit**: machine producers are cross-domain — waive
   `assert_domain_access` for `is_machine_credential` users; keep
   `assert_domain_active`. Domain governance bites at human confirm (reviewer
   must have domain access). Documented in §7.3 / §11.
2. **Target status**: agent may commit to `draft` or `submitted`. `submitted`
   is a *request for review*, not approval, so it is governance-consistent and
   gives the sharper demo ("machine did everything except the one human-only
   act: confirm").
3. **API-key create validation**: `_VALID_AGENT_ROLES` and `ApiKeyCreate.role`
   both derive from the `AgentRole` enum, so the new role is creatable via the
   existing admin endpoint with no schema change.

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Role enum | `api/auth.py:32` `AgentRole` | `NAME = "agent:snake_case"` |
| Role gate | `api/dependencies.py:188` `require_role` | `{r.value for r in roles}` membership |
| Domain waiver | `api/services/lifecycle.py:216` | early-return guard style |
| Tests | `tests/test_api_keys.py:34` | admin `make_token` creates key -> use raw `bp_` as Bearer |
| JSON ingest | `api/routes/ingestions.py:856` | deterministic, no chunking/LLM — ideal for tests |

## Files to Change
| File | Action | Why |
|---|---|---|
| `api/auth.py` | UPDATE | Add `AgentRole.INGESTION_AGENT`; docstring §5.2 |
| `api/dependencies.py` | UPDATE | `require_role(*roles: Role \| AgentRole)` |
| `api/services/lifecycle.py` | UPDATE | Permit ingestion_agent in `assert_can_submit` via `_SUBMIT_ROLES` |
| `api/routes/ingestions.py` | UPDATE | `_Writer` includes ingestion_agent; waive domain-access for machines in `commit_candidate` + `commit_batch` |
| `tests/test_agent_ingestion.py` | CREATE | End-to-end producer path + invariant proofs |
| `docs/requirements.md` | UPDATE | §5.2 new role, §11 machine-producer perms, version -> v4.11 |

## Tasks
### Task 1: producer role
- Add `INGESTION_AGENT = "agent:ingestion_agent"` to `AgentRole`.
- **Validate**: `python -c "from api.auth import AgentRole; print(AgentRole.INGESTION_AGENT.value)"`

### Task 2: role gate accepts agent roles
- Broaden `require_role` signature to `Role | AgentRole`; import `AgentRole`.
- Update `_Writer` in `ingestions.py` to include `AgentRole.INGESTION_AGENT`.

### Task 3: submit + domain semantics for machine producers
- `lifecycle._SUBMIT_ROLES = _CONTRIBUTOR_OR_ADMIN | {AgentRole.INGESTION_AGENT.value}`.
- In `commit_candidate`/`commit_batch`: `assert_domain_active` always; call
  `assert_domain_access` only when `not is_machine_credential(user.roles)`.

### Task 4: tests
- ingestion_agent key is creatable (201).
- ingestion_agent: JSON ingest -> list candidates -> commit-batch `submitted` -> record is `submitted`.
- ingestion_agent commits to a domain it is not assigned to -> succeeds (cross-domain waiver).
- ingestion_agent -> confirm endpoint -> 403 (machine-cannot-confirm).
- consumer agent (`agent:workflow_consumer`) -> JSON ingest -> 403 (only producer permitted).

### Task 5: spec
- Bump `requirements.md` to v4.11; document §5.2 role, §11 producer permissions, §7.3 machine domain waiver.

## Validation
```bash
cd platform
TEST_DATABASE_URL=postgresql+asyncpg://blueprinted:blueprinted@localhost:5433/blueprinted_test \
TEST_DATABASE_URL_SYNC=postgresql+psycopg2://blueprinted:blueprinted@localhost:5433/blueprinted_test \
  uv run pytest tests/test_agent_ingestion.py -q
uv run pytest -q          # full suite, no regressions
uv run ruff check .
uv run mypy .
```

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Broadening `assert_can_submit` lets a machine submit arbitrary records | Low | Only the ingestion-commit route is open to agents; all other submit paths keep human `require_role` |
| Domain waiver leaks cross-domain writes | Low | Waiver is scoped to ingestion commit; confirm (governance gate) still enforces domain access for the human reviewer |
| mypy strict rejects `Role \| AgentRole` union | Low | Both are `str, Enum` with `.value`; union is well-typed |

## Acceptance
- [ ] All tasks complete
- [ ] New + full test suite green; ruff + mypy clean
- [ ] Spec bumped and decision documented in SPRINTS.md + SESSIONS.md
- [ ] Patterns mirrored, not reinvented
