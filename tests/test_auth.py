"""Tests for JWT token verification logic."""

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from api.auth import StubTokenVerifier, TokenVerificationError


def _make_raw(
    private_key: RSAPrivateKey,
    payload: dict[str, Any],
) -> str:
    return jwt.encode(payload, private_key, algorithm="RS256")


@pytest.fixture()
def verifier(rsa_public_key: RSAPublicKey) -> StubTokenVerifier:
    return StubTokenVerifier(
        public_key=rsa_public_key,
        issuer="https://auth.test.example.com/",
        audience="blueprinted-test",
    )


@pytest.fixture()
def valid_payload() -> dict[str, Any]:
    now = int(time.time())
    return {
        "sub": "user-123",
        "email": "user@example.com",
        "roles": ["contributor"],
        "iss": "https://auth.test.example.com/",
        "aud": "blueprinted-test",
        "iat": now,
        "exp": now + 3600,
    }


def test_valid_token_decodes(
    verifier: StubTokenVerifier,
    rsa_private_key: RSAPrivateKey,
    valid_payload: dict[str, Any],
) -> None:
    token = _make_raw(rsa_private_key, valid_payload)
    claims = verifier.decode(token)
    assert claims["sub"] == "user-123"
    assert claims["email"] == "user@example.com"


def test_expired_token_raises(
    verifier: StubTokenVerifier,
    rsa_private_key: RSAPrivateKey,
    valid_payload: dict[str, Any],
) -> None:
    valid_payload["exp"] = int(time.time()) - 60
    token = _make_raw(rsa_private_key, valid_payload)
    with pytest.raises(TokenVerificationError, match="expired"):
        verifier.decode(token)


def test_wrong_audience_raises(
    verifier: StubTokenVerifier,
    rsa_private_key: RSAPrivateKey,
    valid_payload: dict[str, Any],
) -> None:
    valid_payload["aud"] = "wrong-audience"
    token = _make_raw(rsa_private_key, valid_payload)
    with pytest.raises(TokenVerificationError, match="audience"):
        verifier.decode(token)


def test_wrong_issuer_raises(
    verifier: StubTokenVerifier,
    rsa_private_key: RSAPrivateKey,
    valid_payload: dict[str, Any],
) -> None:
    valid_payload["iss"] = "https://evil.example.com/"
    token = _make_raw(rsa_private_key, valid_payload)
    with pytest.raises(TokenVerificationError, match="issuer"):
        verifier.decode(token)


def test_tampered_token_raises(
    verifier: StubTokenVerifier,
    rsa_private_key: RSAPrivateKey,
    valid_payload: dict[str, Any],
) -> None:
    token = _make_raw(rsa_private_key, valid_payload)
    tampered = token[:-4] + "XXXX"
    with pytest.raises(TokenVerificationError):
        verifier.decode(tampered)


def test_extract_roles_returns_list(
    verifier: StubTokenVerifier,
    rsa_private_key: RSAPrivateKey,
    valid_payload: dict[str, Any],
) -> None:
    token = _make_raw(rsa_private_key, valid_payload)
    claims = verifier.decode(token)
    assert verifier.extract_roles(claims) == ["contributor"]


def test_extract_roles_missing_claim_returns_empty(
    verifier: StubTokenVerifier,
) -> None:
    assert verifier.extract_roles({"sub": "x"}) == []
