# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-05 (relationships screen — §23.9)

### Decisions
- Audit log (§23.11) is Sprint 10 — `audit_log` table does not exist yet; deferred explicitly in spec.
- Relationships write endpoint returns `HTTP_422_UNPROCESSABLE_CONTENT` (not the deprecated `_ENTITY` alias).
- No ORM model existed for `Relationship` despite the table being in the Sprint 4 migration; added now.

### Done
- `api/models/relationship.py`: ORM model for the `relationships` table.
- `api/schemas/relationship.py`: `RelationshipResponse` Pydantic schema.
- `api/routes/relationships.py`: `GET /api/v1/relationships` (all authenticated roles); `POST` returns 422.
- `api/routes/v1.py`: relationships router registered.
- `tests/test_relationships.py`: 4 tests — unauthenticated 401, viewer/contributor 200 empty list, write 422.
- `app/src/pages/RelationshipsPage.tsx`: read-only list with empty state explaining v1 limitation.
- `app/src/App.tsx`: `/relationships` route wired.
- `platform/README.md`: Testing principles section added; committed after being overlooked earlier.

### Next
Sprint 8 is complete — all §23 screens built except audit log (Sprint 10). Close out Sprint 8 in SPRINTS.md and start Sprint 9 planning. Sprint 9 is the ingestion triage/extraction human review gate (spec v4.6, §11.5a) or whatever the next sprint item is per the spec.

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
