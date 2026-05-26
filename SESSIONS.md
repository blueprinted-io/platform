# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-05-26 (OIDC silent renew fix + Authentik login page styling)

### Decisions
- Switched OIDC silent renew from iframe to refresh-token grant. Authentik blocks iframes via `X-Frame-Options: deny`; adding `offline_access` scope causes Authentik to issue a refresh token and `oidc-client-ts` uses `grant_type=refresh_token` directly — no redirect or iframe needed.
- Token storage moved from `sessionStorage` to `localStorage` so sessions survive tab close and browser restart.
- Authentik login page styled via Authentik's Custom CSS field (System → Brands) — no changes to app codebase. Flow title ("Welcome to authentik") changed via Flows → edit authentication flow → Title.
- Authentik logo served from `app/public/authentik-logo.svg` and referenced by URL in Authentik Brand settings.

### Done
- `app/src/lib/auth.ts`: added `offline_access` to scope, switched to `localStorage`, enabled `automaticSilentRenew: true`.
- `app/public/authentik-logo.svg`: "blue**printed**.io" SVG logo in brand colours for Authentik login page.
- Committed previously uncommitted design system work from 2026-05-18 session (tokens, shell, StatusBadge, 9 pages, Inter font).

### Next
Apply bp page-chrome styling (`bp-page`, `bp-page__head`, `bp-card`) to individual screens — start with TasksPage and TaskDetailPage to replace raw Tailwind padding/typography with the design system's page layout classes.