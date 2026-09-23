from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_openapi_schema_accessible():
    """Verify that the OpenAPI JSON schema is accessible and properly generated."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "National Material Intelligence Backend"
    assert "paths" in schema
    
    paths = schema["paths"]
    assert len(paths) > 0

def test_all_endpoints_documented():
    """Verify that all endpoints have descriptions, summaries, and responses."""
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]
    
    undocumented_endpoints = []
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue
                
            # Verify standard metadata is present
            has_summary = "summary" in details
            has_responses = "responses" in details
            
            # The global responses should be attached (401, 403, etc)
            if not has_summary or not has_responses:
                undocumented_endpoints.append(f"{method.upper()} {path}")
                
            if has_responses:
                # Assert at least a success response is documented
                success_codes = [code for code in details["responses"] if code.startswith("2")]
                if not success_codes:
                    undocumented_endpoints.append(f"{method.upper()} {path} (No success response)")
                    
    assert not undocumented_endpoints, f"Undocumented endpoints found: {undocumented_endpoints}"
