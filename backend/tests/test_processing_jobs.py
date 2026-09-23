import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def mock_redis_pool():
    with patch("app.api.endpoints.jobs.get_redis_pool", new_callable=AsyncMock) as mock:
        yield mock

client = TestClient(app)

def test_create_job(db_session: Session):
    response = client.post("/api/v1/jobs", json={"job_type": "TEST_JOB", "target_ids": ["123"]})
    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] is not None
    assert data["job_type"] == "TEST_JOB"
    assert data["status"] == "PENDING"
    assert data["records_processed"] == 0
    assert data["total_records"] == 1
    assert data["successful"] == 0
    assert data["failed"] == 0

def test_get_job(db_session: Session):
    response = client.post("/api/v1/jobs", json={"job_type": "TEST_JOB", "target_ids": ["123"]})
    job_id = response.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "PENDING"

def test_get_job_status(db_session: Session):
    response = client.post("/api/v1/jobs", json={"job_type": "TEST_JOB", "target_ids": ["123"]})
    job_id = response.json()["job_id"]

    response = client.get(f"/api/v1/jobs/{job_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "PENDING"



def test_cancel_job(db_session: Session):
    response = client.post("/api/v1/jobs", json={"job_type": "TEST_JOB", "target_ids": ["123"]})
    job_id = response.json()["job_id"]

    response = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Job cancellation requested"

def test_retry_job(db_session: Session):
    response = client.post("/api/v1/jobs", json={"job_type": "TEST_JOB", "target_ids": ["123"]})
    job_id = response.json()["job_id"]

    # cancel first to test retry
    client.post(f"/api/v1/jobs/{job_id}/cancel")

    response = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"

def test_retry_invalid_state(db_session: Session):
    response = client.post("/api/v1/jobs", json={"job_type": "TEST_JOB", "target_ids": ["123"]})
    job_id = response.json()["job_id"]

    # currently PENDING, shouldn't be retried
    response = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert response.status_code == 400
