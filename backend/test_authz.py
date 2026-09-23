import os
os.environ["DATABASE_URL"] = "sqlite:///./antigravity.db"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.router import get_current_user
import unittest.mock as mock
import arq

# Mock arq.create_pool before instantiating TestClient if it runs lifespan
arq.create_pool = mock.AsyncMock()

def make_user(role: str, cpse: str):
    return {"user_id": f"test_{role.lower()}", "name": role, "role": role, "cpse": cpse, "permissions": ["read", "write"]}

@pytest.fixture
def client():
    with mock.patch("app.main.create_pool", new_callable=mock.AsyncMock):
        with TestClient(app) as c:
            yield c

def test_admin_global_access(client):
    app.dependency_overrides[get_current_user] = lambda: make_user("ADMIN", "ALL")
    # Admin querying globally
    response = client.get("/api/v1/materials")
    assert response.status_code == 200
    # Admin querying specific CPSE
    response = client.get("/api/v1/materials?cpse_id=CPSE-A")
    assert response.status_code == 200

def test_data_steward_global_access(client):
    app.dependency_overrides[get_current_user] = lambda: make_user("DATA_STEWARD", "ALL")
    response = client.get("/api/v1/materials")
    assert response.status_code == 200
    response = client.get("/api/v1/materials?cpse_id=CPSE-A")
    assert response.status_code == 200

def test_cpse_user_own_access(client):
    app.dependency_overrides[get_current_user] = lambda: make_user("CPSE_USER", "CPSE-A")
    # CPSE user querying globally should actually just be implicitly scoped to CPSE-A
    response = client.get("/api/v1/materials")
    assert response.status_code == 200
    
    # CPSE user querying specifically for their own CPSE
    response = client.get("/api/v1/materials?cpse_id=CPSE-A")
    assert response.status_code == 200

def test_cpse_user_other_access_forbidden(client):
    app.dependency_overrides[get_current_user] = lambda: make_user("CPSE_USER", "CPSE-A")
    response = client.get("/api/v1/materials?cpse_id=CPSE-B")
    assert response.status_code == 403
    assert "Cross-tenant data access is forbidden" in response.json()["detail"]

def test_engineer_own_access(client):
    app.dependency_overrides[get_current_user] = lambda: make_user("ENGINEER", "CPSE-B")
    response = client.get("/api/v1/materials?cpse_id=CPSE-B")
    assert response.status_code == 200
    
    response = client.get("/api/v1/materials?cpse_id=CPSE-A")
    assert response.status_code == 403

def test_matches_cpse_isolation(client):
    app.dependency_overrides[get_current_user] = lambda: make_user("CPSE_USER", "CPSE-A")
    # Test on matches endpoint as well
    response = client.get("/api/v1/matches?cpse_id=CPSE-B")
    assert response.status_code == 403

if __name__ == "__main__":
    pytest.main(["-v", __file__])
