import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.connection import SessionLocal
from app.auth.router import get_current_user
from app.api.deps import get_db
import unittest.mock as mock

# Mock arq.create_pool before instantiating TestClient if it runs lifespan
import arq
arq.create_pool = mock.AsyncMock()

def override_get_current_user():
    return {"user_id": 1, "username": "admin", "role": "ADMIN", "cpse": "ALL"}

# Apply overrides globally for tests
app.dependency_overrides[get_current_user] = override_get_current_user

def test_endpoints():
    endpoints = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/materials-by-cpse",
        "/api/v1/analytics/confidence-distribution",
        "/api/v1/analytics/redundant-material-groups",
        "/api/v1/analytics/procurement-opportunities",
        "/api/v1/analytics/classification-coverage",
        "/api/v1/analytics/data-quality",
        "/api/v1/analytics/upload-categories",
        "/api/v1/analytics/processing-health",
        "/api/v1/analytics/risk-distribution"
    ]
    
    with mock.patch("app.main.create_pool", new_callable=mock.AsyncMock):
        with TestClient(app) as client:
            for ep in endpoints:
                print(f"\n--- Testing GET {ep} ---")
                response = client.get(ep)
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    print("Response:", json.dumps(response.json(), indent=2))
                else:
                    print("Response:", response.text)

if __name__ == "__main__":
    test_endpoints()
