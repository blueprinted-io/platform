# MVP vs. Platform — Feature Continuity Audit

Conducted by Fable 5, 2026-06-10. Comparison of the original SQLite MVP against the
current FastAPI/PostgreSQL platform. Documents what survived, what regressed, what was
deliberately deferred, and where the spec has gaps.

**Status as of 2026-06-10:** Spec gaps 1 (return severity) and 2 (step linting) resolved
in spec v4.8. Items 3 (force_submit) and 4 (hard delete) closed as explicit non-features
with rationale in §25 key decisions.

---

## What survived faithfully

- Audit trail on every lifecycle action — table + helper exist; route wiring is Sprint 11
- Human-in-the-loop governance (no-machine-can-confirm, self-review prohibition, admin
  break-glass with justification)
- Platform's break-glass is stricter than the MVP (justification now required)

---

## Spec gaps — not tracked anywhere currently

### ~~Return note severity~~ — Resolved in v4.8

`return_severity TEXT` added to §9.2 shared lifecycle fields and to `ReturnRequest` in all
three record schemas. Migration `20260610_3b4c5d6e7f8a_return_severity.py` adds the column
to `tasks`, `workflows`, `principles`. Values: `"info" | "warning" | "critical"` | NULL.

### ~~Step linting / quality hints~~ — Resolved in v4.8 (spec entry; implementation Sprint 11)

§9.10 added to spec: non-blocking lint warnings on abstract verbs, missing completion
criterion, empty action list. Computed on write/GET for authored records; not stored; not
surfaced on confirmed records.

### ~~Export artifacts + SHA256 fingerprints~~ — Resolved in v4.9 (explicit v1.1)

Decision: v1.1, alongside the export endpoint. SHA256 fingerprinting without an export
surface has no value — both ship together. §9.8 stub updated with description. §24 parked
decisions entry added. §25 key decision: fingerprinting is a governance audit feature, not
cosmetic.

---

## Product decisions — Closed

### ~~`force_submit` admin override~~ — Not needed (§25 key decisions)

Decision: `force_submit` is not being added. The MVP needed it to paper over missing
domain-at-create; that gap no longer exists. Break-glass confirm covers the genuine admin
override case on the review side. Documented in §25.

### ~~Hard delete~~ — Explicitly out of scope (§25 key decisions)

Decision: No hard delete on governed records. The append-only lifecycle is an audit trail
integrity guarantee. Test data and ingestion errors are handled by retire/deprecate. Direct
DB access is the intentional escape hatch for exceptional cases. Documented in §25.

---

## Known planned gaps (not regressions)

| Item | Status | Target |
|------|--------|--------|
| Audit log on all lifecycle events | Sprint 11 — confirm, break-glass, return, retire, domain admin | Sprint 11 |
| Staleness calculation | Schema + machine role exist; no calculation or dashboard yet | Dashboard spec (§23.2) |
| Changelog pipeline | `changelog_runs` / `changelog_impacts` tables explicitly stubbed | v1.1 |
| Achievements / gamification | `achievements` / `user_achievements` tables explicitly stubbed | v1.1 |

---

## Full comparison table

| Feature | MVP | Platform | Status |
|---------|-----|----------|--------|
| Audit on all lifecycle events | Full | API keys only | Sprint 11 (known) |
| Return note severity | `[info/warning/critical]` prefix | Note field only | **Spec gap** |
| `force_submit` admin override | Yes | No | **Product decision needed** |
| `force_confirm` / break-glass | Yes (no justification) | Yes (justification required) | Platform is stricter — good |
| Step linting / quality hints | Yes (221-line linting.py) | No | **Spec gap** |
| Staleness calculation | Yes (dashboard-driven) | Schema only | Planned, no timeline |
| Changelog pipeline | Full (441-line LLM pipeline) | Tables stubbed | Explicit v1.1 |
| Achievements / gamification | Yes | Tables stubbed | Explicit v1.1 |
| Hard delete | Yes (with integrity checks) | No endpoint | **Decision needed** |
| Export artifacts + SHA256 | Yes | Not in spec | **Spec gap** |
