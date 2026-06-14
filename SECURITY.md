# Security Policy

## Reporting a vulnerability

This is a private project. Report security issues directly to the maintainer:

**Email:** mathesonewan@gmail.com

Please include a description, reproduction steps, and potential impact. Do not open a public GitHub issue for security vulnerabilities.

## Dependency scanning

Python dependencies are audited via `pip-audit`, which runs automatically in CI on every push and on a weekly schedule via GitHub Actions.

To run locally:

```bash
uv run pip-audit --skip-editable
```

## Secrets

- Credentials are managed via environment variables — never committed to the repository.
- `SESSIONS.md` is committed to git; never write real credentials or tokens into it.
- See `.gitignore` for ignored secret file patterns.

## Authentication

- API authentication uses RS256 JWTs issued by Authentik (self-hosted OIDC).
- The backend verifies token signatures against the Authentik JWKS endpoint on every request.
- No session cookies or server-side sessions are used.
