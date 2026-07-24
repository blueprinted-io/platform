"""OIDC token verification.

TokenVerifier validates RS256 JWTs issued by Authentik (or any OIDC provider).
It fetches the provider's JWKS on first use and caches the signing keys.

For testing, swap app.state.token_verifier with a StubTokenVerifier instance
that holds a pre-generated public key — no HTTP calls, no live Authentik needed.
"""

from enum import Enum
from typing import Any

import jwt
import structlog
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt import PyJWKClient, PyJWKClientError
from jwt.types import Options

log = structlog.get_logger(__name__)


class Role(str, Enum):
    """Human roles as defined in §5.1."""

    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    CONTENT_PUBLISHER = "content_publisher"
    VIEWER = "viewer"
    AUDIT = "audit"


class AgentRole(str, Enum):
    """Machine credential roles as defined in §5.2.

    Consumer roles (Sprint 10) read governed content. The producer role
    (ingestion_agent, Sprint 15) may drive the ingestion pipeline — create
    ingestions and commit candidates up to submitted — but like every agent:
    role is unconditionally barred from confirming records (§5.3, §10.2).
    """

    WORKFLOW_CONSUMER = "agent:workflow_consumer"
    STALENESS_MONITOR = "agent:staleness_monitor"
    ORPHAN_DETECTOR = "agent:orphan_detector"
    INGESTION_AGENT = "agent:ingestion_agent"


def is_machine_credential(roles: list[str]) -> bool:
    """Return True if all roles in the list are agent-prefixed (§5.3)."""
    return bool(roles) and all(r.startswith("agent:") for r in roles)


class TokenVerificationError(Exception):
    """Raised when a JWT cannot be verified."""


class TokenVerifier:
    """Verifies RS256 JWTs against a JWKS endpoint.

    Fetches and caches JWKS on first use. Call invalidate_cache() to force
    a re-fetch (e.g. after a key rotation failure).
    """

    def __init__(
        self,
        jwks_uri: str,
        issuer: str,
        audience: str,
        roles_claim: str = "roles",
    ) -> None:
        self._jwks_uri = jwks_uri
        self._issuer = issuer
        self._audience = audience
        self._roles_claim = roles_claim
        # PyJWKClient handles caching internally
        self._client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=300)

    def decode(self, token: str) -> dict[str, Any]:
        """Decode and verify a JWT. Returns the verified claims dict.

        Raises TokenVerificationError on any failure.
        """
        try:
            signing_key = self._client.get_signing_key_from_jwt(token)
        except PyJWKClientError as exc:
            raise TokenVerificationError(f"JWKS lookup failed: {exc}") from exc

        options: Options = {}
        if not self._issuer:
            options["verify_iss"] = False
        if not self._audience:
            options["verify_aud"] = False

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self._issuer or None,
                audience=self._audience or None,
                options=options,
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenVerificationError("Token has expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise TokenVerificationError("Invalid audience") from exc
        except jwt.InvalidIssuerError as exc:
            raise TokenVerificationError("Invalid issuer") from exc
        except jwt.DecodeError as exc:
            raise TokenVerificationError(f"Token decode failed: {exc}") from exc

        return claims

    def extract_roles(self, claims: dict[str, Any]) -> list[str]:
        """Return the roles list from claims, defaulting to empty."""
        raw = claims.get(self._roles_claim, [])
        if isinstance(raw, list):
            return [str(r) for r in raw]
        return []


class StubTokenVerifier(TokenVerifier):
    """TokenVerifier for tests — verifies against a supplied RSA public key.

    No HTTP calls. No live OIDC provider needed.
    """

    def __init__(
        self,
        public_key: RSAPublicKey,
        issuer: str = "https://test.example.com/",
        audience: str = "blueprinted-test",
        roles_claim: str = "roles",
    ) -> None:
        # Do not call super().__init__ — we bypass PyJWKClient entirely
        self._public_key = public_key
        self._issuer = issuer
        self._audience = audience
        self._roles_claim = roles_claim

    def decode(self, token: str) -> dict[str, Any]:
        options: Options = {}
        if not self._issuer:
            options["verify_iss"] = False
        if not self._audience:
            options["verify_aud"] = False

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                issuer=self._issuer or None,
                audience=self._audience or None,
                options=options,
            )
            return claims
        except jwt.ExpiredSignatureError as exc:
            raise TokenVerificationError("Token has expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise TokenVerificationError("Invalid audience") from exc
        except jwt.InvalidIssuerError as exc:
            raise TokenVerificationError("Invalid issuer") from exc
        except jwt.DecodeError as exc:
            raise TokenVerificationError(f"Token decode failed: {exc}") from exc
