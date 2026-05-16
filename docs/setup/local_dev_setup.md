# Local Development Setup

Initial setup procedure for running the full Blueprinted stack locally.
Covers the manual steps that cannot be automated.

---

## Prerequisites

- Docker and Docker Compose installed
- Node.js 20+ and npm
- Python 3.12 and `uv`
- An Authentik instance configured with a `blueprinted` OIDC provider (Sprint 2)

---

## 1. Backend

From the `platform/` directory:

```bash
cp deploy/.env.example .env
```

Open `.env` and fill in the four required values (any values are fine for local dev):

```
POSTGRES_PASSWORD=localdev
APP_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
AUTHENTIK_DB_PASSWORD=localdev
AUTHENTIK_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
```

The `.env` file must live at the `platform/` root — Docker Compose loads it from the working directory, not from the `deploy/` subdirectory where the compose files live.

Then bring the stack up:

```bash
docker compose -f deploy/docker-compose.yml --env-file .env up
```

The `--env-file .env` flag is required because Docker Compose v2 resolves `.env` relative to the compose file location (`deploy/`), not the working directory.

Runs PostgreSQL, Redis, the FastAPI app, and the ARQ worker.

Once the stack is up, run migrations in a separate terminal:

```bash
docker compose -f deploy/docker-compose.yml --env-file .env exec api alembic -c migrations/alembic.ini upgrade head
```

This is required on first run and after any new migration is added. The worker startup hook will fail with an `UndefinedTableError` until migrations have run.

---

## 2. Frontend environment

```bash
cd app
cp .env.example .env.local
```

Edit `.env.local`:

```
VITE_OIDC_AUTHORITY=https://<your-authentik-host>/application/o/blueprinted/
VITE_OIDC_CLIENT_ID=<client-id-from-authentik>
VITE_API_BASE_URL=http://localhost:8000
```

Both `VITE_OIDC_AUTHORITY` and `VITE_OIDC_CLIENT_ID` are found in the Authentik
admin UI under the `blueprinted` OAuth2/OIDC provider.

---

## 3. Authentik — redirect URI

In the Authentik admin UI, open the `blueprinted` provider and add to
**Redirect URIs**:

```
http://localhost:5173/callback
```

Without this Authentik will reject the PKCE callback with a redirect_uri
mismatch error. Add the production URL here too when deploying.

---

## 4. Authentik — `blueprinted_roles` claim

The frontend reads `user.profile["blueprinted_roles"]` to determine role-aware
nav (admin link, etc.). A Property Mapping in Authentik must inject this claim
into the ID token.

**Customisation → Property Mappings → Create → Scope Mapping**

| Field | Value |
| --- | --- |
| Name | `blueprinted_roles` |
| Scope name | `blueprinted_roles` |
| Expression | See below |

```python
return list(request.user.ak_groups.values_list("name", flat=True))
```

Then attach the mapping to the `blueprinted` provider under
**Advanced → Scope Mappings**.

If this was configured in Sprint 2, verify the claim name is exactly
`blueprinted_roles`.

---

## 5. Playwright Chromium (worker — HTML ingestion only)

Required before HTML ingestion jobs (`crawl_html`, `render_nav_pages`) can run.
Not needed for PDF or JSON ingestion.

```bash
cd platform
uv run playwright install chromium
```

For Docker deployments, add to the worker image build:

```dockerfile
RUN playwright install --with-deps chromium
```

---

## Running the stack

```bash
# Terminal 1 — backend (from platform/)
docker compose -f deploy/docker-compose.yml --env-file .env up

# Terminal 2 — frontend (from app/)
npm run dev
```

Visit `http://localhost:5173` — the login page should appear and redirect to
Authentik on click.
