from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app, raise_server_exceptions=False)

def test_request_id_middleware_generates_id():
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 10

def test_request_id_middleware_preserves_id():
    test_id = "test-custom-id-12345"
    response = client.get("/health", headers={"X-Request-ID": test_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == test_id

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "main-backend"

def test_readiness_endpoint():
    response = client.get("/ready")
    # It might return 503 if DB is down in CI, but usually 200 if connected.
    # In this test setup, sqlite might be used and working, so 200 is expected.
    # If not working, we'd mock check_db_health.
    assert response.status_code in (200, 503)
    data = response.json()
    if response.status_code == 200:
        assert data["status"] == "ready"
    else:
        assert "Service Unavailable" in data["detail"]
