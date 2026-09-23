import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.base import User, SourceMaterial
from app.auth.security import get_password_hash
from app.auth.router import get_current_user

client = TestClient(app)

@pytest.fixture
def test_users(db_session):
    pwd = get_password_hash("password123")
    
    admin_user = User(user_id="admin_user", name="Admin User", cpse_code="SYS", email="admin@auth.com", role_id="ADMIN", password_hash=pwd)
    bus_user = User(user_id="bus_user", name="BUS User", cpse_code="BUS", email="bus@auth.com", role_id="CPSE_USER", password_hash=pwd)
    
    db_session.add_all([admin_user, bus_user])
    db_session.commit()
    
    return {"admin": admin_user, "bus": bus_user}

def test_tenant_isolation_analytics(test_users):
    # Clear get_current_user dependency overrides
    app.dependency_overrides.pop(get_current_user, None)
    
    # Login as BUS user
    res = client.post("/api/v1/auth/login", json={"username": "bus_user", "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. BUS user tries to explicitly query CPI data -> 403 Forbidden
    response = client.get("/api/v1/analytics/overview?cpse_code=CPI", headers=headers)
    assert response.status_code == 403
    assert "Cross-tenant data access is forbidden" in response.json()["detail"]
    
    # 2. BUS user queries their own data -> 200 OK
    response = client.get("/api/v1/analytics/overview?cpse_code=BUS", headers=headers)
    assert response.status_code == 200

def test_tenant_isolation_exports(test_users):
    app.dependency_overrides.pop(get_current_user, None)
    
    # Login as BUS user
    res = client.post("/api/v1/auth/login", json={"username": "bus_user", "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # BUS user tries to download material master (forbidden for non-admins)
    response = client.get("/api/v1/exports/material-master?format=csv", headers=headers)
    assert response.status_code == 403
    assert "Only admins and stewards" in response.json()["detail"]
    
    # BUS user tries to download mapping for CPI
    response = client.get("/api/v1/exports/cpse-mapping?cpse_code=CPI&format=csv", headers=headers)
    assert response.status_code == 403

def test_admin_tenant_access(test_users):
    app.dependency_overrides.pop(get_current_user, None)
    
    # Login as ADMIN user
    res = client.post("/api/v1/auth/login", json={"username": "admin_user", "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Admin can query CPI
    response = client.get("/api/v1/analytics/overview?cpse_code=CPI", headers=headers)
    assert response.status_code == 200
    
    # Admin can download material master
    response = client.get("/api/v1/exports/material-master?format=csv", headers=headers)
    assert response.status_code == 200
