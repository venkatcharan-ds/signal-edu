"""
Health endpoint smoke test.
Sets required env vars before importing app so Settings() doesn't raise.
"""
import os
import pytest

# Inject minimal required settings before any app import
_ENV_DEFAULTS = {
    "DATABASE_URL":             "postgresql+asyncpg://x:x@localhost/test",
    "SUPABASE_URL":             "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_JWT_SECRET":      "test-jwt-secret-32-chars-minimum!!",
    "GITHUB_CLIENT_ID":         "test-client-id",
    "GITHUB_CLIENT_SECRET":     "test-client-secret",
    "ANTHROPIC_API_KEY":        "test-anthropic-key",
    "ENVIRONMENT":              "test",
    "DEBUG":                    "false",
}

for key, value in _ENV_DEFAULTS.items():
    os.environ.setdefault(key, value)


@pytest.fixture(scope="module")
def client():
    from app.config import get_settings
    get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["environment"] == "test"
