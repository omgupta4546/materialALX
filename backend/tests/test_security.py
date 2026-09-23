import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

def test_security_headers():
    response = client.get("/api/v1/auth/login") # any endpoint
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"

def test_upload_invalid_file_type():
    from app.auth.router import get_current_user
    from app.models.base import User
    
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "test", "role": "ADMIN"}
    
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    data = {"cpse_id": "TEST_CPSE"}
    
    response = client.post("/api/v1/materials/upload", files=files, data=data)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
    
    app.dependency_overrides.pop(get_current_user, None)

def test_upload_file_size_limit():
    from app.auth.router import get_current_user
    from app.models.base import User
    
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "test", "role": "ADMIN"}
    
    # 50MB + 1 byte
    large_content = b"0" * ((50 * 1024 * 1024) + 1)
    files = {"file": ("test.csv", large_content, "text/csv")}
    data = {"cpse_id": "TEST_CPSE"}
    
    response = client.post("/api/v1/materials/upload", files=files, data=data)
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]
    
    app.dependency_overrides.pop(get_current_user, None)

def test_generic_exception_sanitization():
    @app.get("/api/v1/test-error")
    def test_error():
        raise Exception("Super secret internal detail")
        
    response = client.get("/api/v1/test-error")
    assert response.status_code == 500
    assert "unexpected internal server error" in response.json()["detail"]
    assert "Super secret internal detail" not in response.json()["detail"]
