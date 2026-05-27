# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-27 (Platform CI fix + design system migration)

### Decisions
- `bp-btn` and `bp-link` CSS classes were not defined in globals.css despite being used in TasksPage/TaskDetailPage — added them in this session alongside the page migrations.
- `Button`/`buttonVariants` shadcn imports removed from WorkflowDetailPage and PrincipleDetailPage; replaced with `bp-btn` throughout for consistency.

### Done
- `platform/workers/main.py`: fixed Ruff S110 (`try/except Exception: pass` → log warning), unblocking platform CI.
- `app/src/styles/globals.css`: added `.bp-btn`, `.bp-btn--secondary`, `.bp-btn--ghost`, `.bp-link` CSS rules.
- `app/src/pages/WorkflowsPage.tsx`: migrated to `bp-page` / `bp-page__head` / `bp-btn` / shadcn Table.
- `app/src/pages/WorkflowDetailPage.tsx`: migrated to `bp-page` / `bp-crumbs` / `bp-card` sections / `bp-btn` actions.
- `app/src/pages/PrinciplesPage.tsx`: migrated to `bp-page` layout.
- `app/src/pages/PrincipleDetailPage.tsx`: migrated to `bp-page` / `bp-crumbs` / `bp-card` sections / `bp-btn` actions.
- `app/src/pages/ReviewQueuePage.tsx`: migrated to `bp-page` / `bp-card`-wrapped table / `bp-btn` actions; removed shadcn `Button`/`Badge` dependencies.
- `app/src/pages/DashboardPage.tsx`: migrated to `bp-page` / `bp-card` placeholder.
- `app/src/pages/SearchPage.tsx`: migrated to `bp-page` / inline `bp-card` result links / type filter chips using design tokens.

- `app/src/components/TagInput.tsx`: extracted shared tag-chip input from 6 duplicated implementations.
- `app/src/styles/globals.css`: added `.bp-input`, `.bp-label`, `.bp-form-field` for raw `<input>` elements.
- Migrated all remaining pages to bp design system (commit `dda7ef5`):
  TaskCreatePage, TaskEditPage, WorkflowCreatePage, WorkflowEditPage,
  PrincipleCreatePage, PrincipleEditPage, IngestionListPage, IngestionCreatePage,
  IngestionDetailPage, CandidateReviewPage, NavSelectionPage, SectionSelectionPage,
  NotificationsPage, ProfilePage.

### Next
All app pages now use the bp design system. TypeScript clean (0 errors).
Next sprint task: per SESSIONS context / requirements.md.