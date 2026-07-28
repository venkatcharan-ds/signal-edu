"""
Tests for JWT verification in app.core.security.

Covers:
  - ES256 token signed with a test EC key pair (Supabase asymmetric flow)
  - HS256 token signed with SUPABASE_JWT_SECRET (legacy symmetric flow)
  - Rejection: wrong audience
  - Rejection: expired token
  - Rejection: unknown kid (after JWKS re-fetch returns nothing)
  - Rejection: unsupported algorithm
"""
from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException

# ── Minimal env before importing app ─────────────────────────────────────────
_TEST_JWT_SECRET = "test-jwt-secret-at-least-32-chars!!"
_TEST_SUPABASE_URL = "https://testref.supabase.co"

_ENV = {
    "DATABASE_URL":              "postgresql+asyncpg://x:x@localhost/test",
    "SUPABASE_URL":              _TEST_SUPABASE_URL,
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_JWT_SECRET":       _TEST_JWT_SECRET,
    "GITHUB_CLIENT_ID":          "test-client-id",
    "GITHUB_CLIENT_SECRET":      "test-client-secret",
    "GEMINI_API_KEY":            "test-gemini-key",
    "ENVIRONMENT":               "test",
    "DEBUG":                     "false",
}
for k, v in _ENV.items():
    os.environ.setdefault(k, v)

from app.config import get_settings  # noqa: E402 — must follow env setup

get_settings.cache_clear()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_settings_and_jwks_cache():
    """Reset lru_cache and JWKS state between tests."""
    get_settings.cache_clear()
    import app.core.security as sec
    sec._jwks_cache.clear()
    sec._jwks_fetched_at = 0.0
    yield
    get_settings.cache_clear()
    sec._jwks_cache.clear()
    sec._jwks_fetched_at = 0.0


@pytest.fixture()
def ec_key_pair():
    """Generate a fresh P-256 key pair for each test."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture()
def test_kid():
    return "test-kid-001"


def _make_es256_token(
    private_key,
    kid: str,
    *,
    sub: str = "00000000-0000-0000-0000-000000000001",
    aud: str = "authenticated",
    iss: str | None = None,
    exp_offset: int = 3600,
    extra: dict | None = None,
) -> str:
    if iss is None:
        iss = _TEST_SUPABASE_URL.rstrip("/") + "/auth/v1"
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + exp_offset,
        "role": "authenticated",
        "email": "test@example.com",
        "user_metadata": {
            "user_name": "testuser",
            "avatar_url": "https://avatars.example.com/u/1",
            "provider_id": "12345678",
        },
        **(extra or {}),
    }
    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": kid})


def _make_hs256_token(
    *,
    sub: str = "00000000-0000-0000-0000-000000000001",
    aud: str = "authenticated",
    iss: str | None = None,
    exp_offset: int = 3600,
) -> str:
    if iss is None:
        iss = _TEST_SUPABASE_URL.rstrip("/") + "/auth/v1"
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + exp_offset,
        "role": "authenticated",
        "email": "test@example.com",
        "user_metadata": {"user_name": "testuser", "provider_id": "99999999"},
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


def _jwks_response(public_key, kid: str) -> MagicMock:
    """Build a mock httpx.Response containing the public key as a JWK."""
    from jwt.algorithms import ECAlgorithm
    jwk_dict = json.loads(ECAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = kid
    jwk_dict["alg"] = "ES256"
    jwk_dict["use"] = "sig"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"keys": [jwk_dict]}
    return mock_resp


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestES256:
    def test_valid_es256_token_is_accepted(self, ec_key_pair, test_kid):
        """A valid ES256 token with correct audience and issuer must be accepted."""
        private_key, public_key = ec_key_pair
        token = _make_es256_token(private_key, test_kid)

        with patch("httpx.get", return_value=_jwks_response(public_key, test_kid)):
            from app.core.security import verify_supabase_jwt
            result = verify_supabase_jwt(token)

        assert result.sub == "00000000-0000-0000-0000-000000000001"
        assert result.github_username == "testuser"
        assert result.github_id == 12345678

    def test_jwks_cache_prevents_refetch(self, ec_key_pair, test_kid):
        """Second call with same kid must NOT re-fetch JWKS."""
        private_key, public_key = ec_key_pair
        token = _make_es256_token(private_key, test_kid)

        with patch("httpx.get", return_value=_jwks_response(public_key, test_kid)) as mock_get:
            from app.core.security import verify_supabase_jwt
            verify_supabase_jwt(token)
            verify_supabase_jwt(token)

        assert mock_get.call_count == 1

    def test_unknown_kid_triggers_refetch_then_rejects(self, ec_key_pair, test_kid):
        """A kid absent from JWKS after re-fetch must raise 401."""
        private_key, _ = ec_key_pair
        token = _make_es256_token(private_key, "unknown-kid")

        # JWKS returns a different kid — 'unknown-kid' won't be in cache
        empty_resp = MagicMock()
        empty_resp.raise_for_status = MagicMock()
        empty_resp.json.return_value = {"keys": []}

        with patch("httpx.get", return_value=empty_resp):
            from app.core.security import verify_supabase_jwt
            with pytest.raises(HTTPException) as exc_info:
                verify_supabase_jwt(token)

        assert exc_info.value.status_code == 401
        assert "Unknown key id" in exc_info.value.detail

    def test_wrong_audience_rejected(self, ec_key_pair, test_kid):
        private_key, public_key = ec_key_pair
        token = _make_es256_token(private_key, test_kid, aud="wrong-audience")

        with patch("httpx.get", return_value=_jwks_response(public_key, test_kid)):
            from app.core.security import verify_supabase_jwt
            with pytest.raises(HTTPException) as exc_info:
                verify_supabase_jwt(token)

        assert exc_info.value.status_code == 401

    def test_expired_token_rejected(self, ec_key_pair, test_kid):
        private_key, public_key = ec_key_pair
        token = _make_es256_token(private_key, test_kid, exp_offset=-1)

        with patch("httpx.get", return_value=_jwks_response(public_key, test_kid)):
            from app.core.security import verify_supabase_jwt
            with pytest.raises(HTTPException) as exc_info:
                verify_supabase_jwt(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_missing_kid_rejected(self, ec_key_pair):
        """ES256 token without kid header must be rejected without hitting JWKS."""
        private_key, _ = ec_key_pair
        now = int(time.time())
        token = jwt.encode(
            {"sub": "x", "aud": "authenticated", "exp": now + 3600},
            private_key,
            algorithm="ES256",
            # no headers={"kid": ...}
        )

        with patch("httpx.get") as mock_get:
            from app.core.security import verify_supabase_jwt
            with pytest.raises(HTTPException) as exc_info:
                verify_supabase_jwt(token)

        mock_get.assert_not_called()
        assert exc_info.value.status_code == 401


class TestHS256:
    def test_valid_hs256_token_is_accepted(self):
        """Existing HS256 tokens (e.g. legacy anon tokens) must still be accepted."""
        token = _make_hs256_token()
        from app.core.security import verify_supabase_jwt
        result = verify_supabase_jwt(token)
        assert result.sub == "00000000-0000-0000-0000-000000000001"
        assert result.github_username == "testuser"

    def test_hs256_wrong_secret_rejected(self):
        now = int(time.time())
        iss = _TEST_SUPABASE_URL.rstrip("/") + "/auth/v1"
        token = jwt.encode(
            {"sub": "x", "aud": "authenticated", "iss": iss, "exp": now + 3600},
            "wrong-secret",
            algorithm="HS256",
        )
        from app.core.security import verify_supabase_jwt
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(token)
        assert exc_info.value.status_code == 401


class TestUnsupportedAlgorithm:
    def test_rs256_rejected(self):
        from app.core.security import verify_supabase_jwt
        now = int(time.time())
        # Build a token with RS256 alg header but HS256 signature (will fail header check)
        token = jwt.encode(
            {"sub": "x", "aud": "authenticated", "exp": now + 3600},
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        # Manually tamper the header to claim RS256
        parts = token.split(".")
        import base64, json as _json
        fake_header = base64.urlsafe_b64encode(
            _json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        tampered = f"{fake_header}.{parts[1]}.{parts[2]}"

        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(tampered)
        assert exc_info.value.status_code == 401
