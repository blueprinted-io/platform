# MVP vs. Platform — Feature Continuity Audit

Conducted by Fable 5, 2026-06-10. Comparison of the original SQLite MVP against the
current FastAPI/PostgreSQL platform. Documents what survived, what regressed, what was
deliberately deferred, and where the spec has gaps.

---

## What survived faithfully

- Audit trail on every lifecycle action — table + helper exist; route wiring is Sprint 11
- Human-in-the-loop governance (no-machine-can-confirm, self-review prohibition, admin
  break-glass with justification)
- Platform's break-glass is stricter than the MVP (justification now required)

---

## Spec gaps — not tracked anywhere currently

### Return note severity

The MVP attaches a `note` to every audit action, and `return_for_changes` notes carry a
`[severity]` prefix: `[info]`, `[warning]`, `[critical]`. The platform's `ReturnRequest`
has a `note` field but no severity classification in the schema or spec. Minor, but useful
for review queue triage.

**Recommended action:** Add `severity: Literal["info", "warning", "critical"] | None`
to `ReturnRequest` and thread it into the audit event detail. One migration, one schema
field, one spec line.

### Step linting / quality hints

The MVP has a 221-line `linting.py` that validates task steps on create, edit, and
display: flags abstract verbs ("ensure", "handle", "manage"), checks completion criteria
are present, validates step structure. Returns warnings — not a hard block. Provides
disproportionate quality signal for ~2 hours of work.

Not mentioned anywhere in the platform spec. Almost certainly dropped during the
governance-infrastructure rewrite focus.

**Recommended action:** Add `§9.x Step quality linting` to the spec before v1.

### Export artifacts + SHA256 fingerprints

The MVP has an `export_artifacts` table with SHA256 fingerprints of exported workflow
bundles. Not in the platform spec at all — not mentioned, not stubbed. The platform
currently has no export endpoint or fingerprinting.

**Recommended action:** Decide whether this is v1 or v1.1 and add a spec entry. If
deferred, add an explicit stub comment so it isn't re-discovered as a surprise.

---

## Product decisions needed

### `force_submit` admin override

The MVP has `force_submit` as an explicit admin-only endpoint, audited with
`note="admin forced submission"`, with a visible "scar" flag on the record detail page.
The platform has no equivalent — there is no way for an admin to push a draft directly
to submitted state, bypassing the contributor workflow.

**Origin note:** In the MVP, `force_submit` partly existed to paper over the absence of
domain-assignment at create time (tasks could be created without a domain). The
platform's domain-required-at-create model eliminates that original use case. Whether a
genuine admin override is needed is a product call, not an inherited requirement.

**Recommended action:** Make an explicit decision — add `force_submit` or document why
it's out of scope.

### Hard delete

The MVP allows hard delete of tasks and primers (admin always; contributors on own
draft/submitted records), with referential integrity checks against workflows before
deletion, and an audit entry at `version=0`. The platform has no `DELETE /tasks/{id}`
endpoint — only step-level delete. This is probably intentional (immutable audit trail),
but it means there's no way to remove test data or fix ingestion errors in production
without direct DB access.

**Recommended action:** Add a spec entry making the decision explicit: either a
soft-delete or admin-only hard-delete endpoint with the same referential integrity check,
or a documented statement that hard delete is out of scope and DB access is the
intentional escape hatch.

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
