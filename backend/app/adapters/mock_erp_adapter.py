import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import MaterialSourceAdapter, SourceMaterialDTO

class MockERPAdapter(MaterialSourceAdapter):
    """
    Adapter for communicating with the Mock ERP microservice.
    Simulates RESTful integration with a modern ERP system.
    """
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url.rstrip("/")
        
    def fetch_materials(self, since: Optional[datetime] = None) -> List[SourceMaterialDTO]:
        try:
            # We assume a /api/materials endpoint on the mock ERP
            response = requests.get(f"{self.base_url}/api/materials")
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                results.append(SourceMaterialDTO(
                    legacy_code=item.get("legacy_code", ""),
                    description=item.get("description", ""),
                    uom=item.get("uom", None),
                    attributes=item.get("attributes", {})
                ))
            return results
        except requests.RequestException:
            return []

    def get_material(self, legacy_code: str) -> Optional[SourceMaterialDTO]:
        try:
            response = requests.get(f"{self.base_url}/api/materials/{legacy_code}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            
            item = response.json()
            return SourceMaterialDTO(
                legacy_code=item.get("legacy_code", ""),
                description=item.get("description", ""),
                uom=item.get("uom", None),
                attributes=item.get("attributes", {})
            )
        except requests.RequestException:
            return None

    def create_mapping(self, legacy_code: str, national_code: str) -> bool:
        try:
            response = requests.post(f"{self.base_url}/api/mappings", json={
                "legacy_code": legacy_code,
                "national_code": national_code
            })
            return response.status_code in (200, 201)
        except requests.RequestException:
            return False

    def update_mapping(self, legacy_code: str, national_code: str) -> bool:
        try:
            response = requests.put(f"{self.base_url}/api/mappings/{legacy_code}", json={
                "national_code": national_code
            })
            return response.status_code == 200
        except requests.RequestException:
            return False

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def sync_status(self) -> Dict[str, Any]:
        is_healthy = self.health_check()
        return {
            "type": "MockERP",
            "connected": is_healthy,
            "url": self.base_url
        }
