import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.base import User, Role
from app.auth.security import get_password_hash
from app.auth.router import get_current_user

client = TestClient(app)

@pytest.fixture
def auth_db(db_session):
    admin_role = Role(id="ADMIN", description="Admin")
    engineer_role = Role(id="ENGINEER", description="Engineer")
    db_session.add_all([admin_role, engineer_role])
    db_session.commit()
    
    pwd = get_password_hash("password123")
    
    admin_user = User(user_id="admin_auth", name="Admin User", cpse_code="SYS", email="admin@auth.com", role_id="ADMIN", password_hash=pwd)
    engineer_user = User(user_id="engineer_auth", name="Engineer User", cpse_code="SYS", email="engineer@auth.com", role_id="ENGINEER", password_hash=pwd)
    
    db_session.add_all([admin_user, engineer_user])
    db_session.commit()
    
    return {"admin": admin_user, "engineer": engineer_user}

def test_login_success(auth_db):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/api/v1/auth/login", json={"username": "admin_auth", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure(auth_db):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/api/v1/auth/login", json={"username": "admin_auth", "password": "wrongpassword"})
    assert response.status_code == 401
    
    response = client.post("/api/v1/auth/login", json={"username": "notfound", "password": "password123"})
    assert response.status_code == 401

def test_get_me(auth_db):
    app.dependency_overrides.pop(get_current_user, None)
    res = client.post("/api/v1/auth/login", json={"username": "admin_auth", "password": "password123"})
    token = res.json()["access_token"]
    
    res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["user_id"] == "admin_auth"
    assert res_me.json()["role"] == "ADMIN"

def test_logout():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

def test_rbac_protection(auth_db):
    app.dependency_overrides.pop(get_current_user, None)
    res = client.post("/api/v1/auth/login", json={"username": "engineer_auth", "password": "password123"})
    token = res.json()["access_token"]
    
    # Try to access a route that requires ADMIN or DATA_STEWARD (e.g. migration validation)
    # Using the migration batches mock endpoint which requires DATA_STEWARD or ADMIN
    response = client.post("/api/v1/migration/batches", json={"name": "Test", "legacy_codes": []}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "Required roles: ADMIN" in response.json()["detail"]
