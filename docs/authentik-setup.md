# Authentik Setup Guide

This guide walks through configuring Authentik as the OIDC identity provider for a
Blueprinted instance. Complete this before enabling authentication in the API.

---

## 1. Start Authentik

From the repo root, start the Authentik services:

```bash
cp deploy/.env.example .env
# Fill in AUTHENTIK_DB_PASSWORD and AUTHENTIK_SECRET_KEY in .env
docker compose -f deploy/docker-compose.yml up auth auth-db auth-redis -d
```

Authentik takes 30–60 seconds to initialise on first start.

---

## 2. Complete the initial setup wizard

Open **http://localhost:9000/if/flow/initial-setup/** in a browser.

Create your admin account. This is the break-glass admin for Authentik itself — keep
the credentials secure and separate from your Blueprinted application credentials.

---

## 3. Create an OAuth2/OIDC Provider

1. Log in to the Authentik admin UI at **http://localhost:9000**
2. Navigate to **Applications → Providers → Create**
3. Select **OAuth2/OpenID Provider**
4. Configure:

| Field | Value |
|---|---|
| Name | `Blueprinted` |
| Authorization flow | `default-provider-authorization-explicit-consent` |
| Client type | `Confidential` |
| Redirect URIs | `http://localhost:3000/auth/callback` (frontend, Sprint 8) |
| Signing Key | Select the default signing key |
| Scopes | `openid`, `email`, `profile` — add `roles` scope below |

5. **Note the Client ID and Client Secret** — you will need these for `.env`.

---

## 4. Add a roles property mapping

Blueprinted reads roles from a JWT claim (default: `roles`). You need a property mapping
that injects the user's Authentik groups into this claim.

1. Navigate to **Customisation → Property Mappings → Create**
2. Select **OAuth2 Property Mapping**
3. Configure:

| Field | Value |
|---|---|
| Name | `Blueprinted Roles` |
| Scope name | `roles` |
| Expression | See below |

Expression:
```python
return [group.name for group in request.user.ak_groups.all()]
```

4. Return to your provider → **Edit** → under **Advanced protocol settings**, add
   `Blueprinted Roles` to the **Scopes** list.

---

## 5. Create an Authentik Application

1. Navigate to **Applications → Applications → Create**
2. Configure:

| Field | Value |
|---|---|
| Name | `Blueprinted` |
| Slug | `blueprinted` |
| Provider | Select the provider created in step 3 |

---

## 6. Create Blueprinted roles as Authentik groups

Blueprinted enforces five roles (§5.1). Create a matching Authentik group for each role
you want to assign to users.

Navigate to **Directory → Groups → Create** for each:

| Group name | Blueprinted role |
|---|---|
| `admin` | Full access, system settings |
| `contributor` | Create, submit, review in assigned domains |
| `content_publisher` | Export confirmed workflows |
| `viewer` | Read-only across all confirmed content |
| `audit` | Read-only + audit log access |

Assign users to groups via **Directory → Users → [user] → Groups**.

---

## 7. Collect the OIDC configuration values

From **Applications → Providers → Blueprinted**:

- **OpenID Configuration Issuer** → `OIDC_ISSUER`
- **JWKS URL** → `OIDC_JWKS_URI`
- **Client ID** → `OIDC_CLIENT_ID` and `OIDC_AUDIENCE`
- **Client Secret** → `OIDC_CLIENT_SECRET`

Update your `.env`:

```dotenv
OIDC_ISSUER=https://<your-authentik-host>/application/o/blueprinted/
OIDC_CLIENT_ID=blueprinted
OIDC_CLIENT_SECRET=<client-secret-from-step-3>
OIDC_JWKS_URI=https://<your-authentik-host>/application/o/blueprinted/jwks/
OIDC_AUDIENCE=blueprinted
OIDC_ROLES_CLAIM=roles
```

For a local Docker Compose install, `<your-authentik-host>` is `localhost:9000`.

---

## 8. Restart the API

```bash
docker compose -f deploy/docker-compose.yml restart api worker
```

Verify authentication is working:

```bash
blueprinted healthcheck
```

---

## Troubleshooting

**Token verification fails with "Invalid issuer"**
The `OIDC_ISSUER` value must exactly match the `iss` claim in the JWT. Copy it verbatim
from the Authentik provider page — trailing slash matters.

**Roles are empty in `GET /api/v1/users/me`**
Check that:
1. The `Blueprinted Roles` property mapping is added to the provider's scopes
2. The user is a member of at least one Authentik group
3. `OIDC_ROLES_CLAIM=roles` matches the scope name in the property mapping

**JWKS fetch fails at startup**
The API fetches JWKS on first token verification, not at startup. If the API starts
before Authentik is ready, the first authenticated request may be slow but will succeed
once Authentik is up.
