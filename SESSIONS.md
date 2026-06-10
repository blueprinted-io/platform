# Active Session — blueprinted.io
One entry only. On closeout: move this entry to the top of SESSIONS_ARCHIVE.md (above existing entries), replace with new entry.
Archive: SESSIONS_ARCHIVE.md (do not load unless explicitly asked).
Format and rules: docs/session_protocol.md

## Session — 2026-06-09 (HTTPS tunnel setup — Cloudflare + Authentik)

### Decisions
- Authentik derives OIDC issuer from the incoming request's Host + X-Forwarded-Proto headers — no static issuer config needed; Cloudflare tunnel supplies both automatically.
- JWKS URI kept on internal IP (http://192.168.1.82:9000/...) — API fetches it server-to-server; no reason to hairpin through the tunnel.
- AUTHENTIK_URL passed through docker-compose as belt-and-suspenders; not load-bearing given Cloudflare header behaviour.
- Vite dev server must be started with --host 0.0.0.0 to be reachable through the tunnel; orphaned instances from prior sessions were killed and replaced.

### Done
- deploy/docker-compose.yml: Authentik 2025.4.1 → 2025.6.2; AUTHENTIK_URL env passthrough added.

### Broken / Incomplete
- .env changes (OIDC_ISSUER, CORS_ALLOWED_ORIGINS, AUTHENTIK_URL) and app/.env.local (VITE_OIDC_AUTHORITY) are gitignored and exist only on the VM — must be re-applied manually if the stack is rebuilt on a new machine.
- Authentik theme logos broken after tunnel setup — cosmetic, deferred.

### Next
Sprint 11 Hardening. Start with audit log wiring via the confirm-endpoint refactor — dedup the three record-type route files and thread DB session into assert_can_confirm as one unit. Run /plan.
