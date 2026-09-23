import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.base import User, Role, CPSE, MigrationBatch, MigrationRecord

client = TestClient(app)

@pytest.fixture
def auth_headers(db_session):
    admin_role = Role(id="ADMIN", description="Admin")
    db_session.add(admin_role)
    db_session.commit()
    
    admin_user = User(user_id="admin1", email="admin@example.com", role_id="ADMIN")
    db_session.add(admin_user)
    db_session.commit()
    
    from app.auth.security import create_access_token
    token = create_access_token({"sub": "admin1", "role": "ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def test_migration_workflow(db_session, auth_headers):
    # 1. Create batch
    payload = {
        "name": "Test Migration Batch",
        "legacy_codes": ["L001", "L002"]
    }
    response = client.post("/api/v1/migration/batches", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    batch_id = data["batch_id"]
    assert data["status"] == "DRAFT"
    
    # 2. Validate batch
    response = client.post(f"/api/v1/migration/batches/{batch_id}/validate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED" # Because no mappings exist, so UNKNOWN national codes
    
    # Verify records
    records = db_session.query(MigrationRecord).filter_by(batch_id=batch_id).all()
    assert len(records) == 2
    assert all(r.national_code == "UNKNOWN" for r in records)
    
    # 3. Can't approve a FAILED batch
    response = client.post(f"/api/v1/migration/batches/{batch_id}/approve", headers=auth_headers)
    assert response.status_code == 400
    
    # 4. Modify batch to make it VALIDATED (mocking)
    batch = db_session.get(MigrationBatch, batch_id)
    batch.status = "VALIDATED"
    db_session.commit()
    
    # 5. Approve batch
    response = client.post(f"/api/v1/migration/batches/{batch_id}/approve", headers=auth_headers)
    assert response.status_code == 200
    
    # 6. Execute batch
    response = client.post(f"/api/v1/migration/batches/{batch_id}/execute", headers=auth_headers)
    assert response.status_code == 200
    
    # 7. Rollback batch
    response = client.post(f"/api/v1/migration/batches/{batch_id}/rollback", headers=auth_headers)
    assert response.status_code == 200
    
    batch = db_session.get(MigrationBatch, batch_id)
    assert batch.status == "ROLLED_BACK"
