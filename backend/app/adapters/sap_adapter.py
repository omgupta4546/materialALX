from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import MaterialSourceAdapter, SourceMaterialDTO

class SAPAdapter(MaterialSourceAdapter):
    """
    Interface definition for a true SAP integration (ECC or S/4HANA).
    
    WARNING: This platform does NOT claim live out-of-the-box SAP integration.
    This class serves as the architectural stub for future implementation using 
    PyRFC (for BAPI), OData APIs, or IDocs.
    """

    def __init__(self, connection_config: Dict[str, Any]):
        self.config = connection_config
        self._connected = False

    def fetch_materials(self, since: Optional[datetime] = None) -> List[SourceMaterialDTO]:
        raise NotImplementedError("Live SAP integration is not implemented. Use CSVAdapter or MockERPAdapter.")

    def get_material(self, legacy_code: str) -> Optional[SourceMaterialDTO]:
        raise NotImplementedError("Live SAP integration is not implemented.")

    def create_mapping(self, legacy_code: str, national_code: str) -> bool:
        raise NotImplementedError("Live SAP integration is not implemented.")

    def update_mapping(self, legacy_code: str, national_code: str) -> bool:
        raise NotImplementedError("Live SAP integration is not implemented.")

    def health_check(self) -> bool:
        # In a real scenario, this would ping SAP gateway or RFC destination
        return False

    def sync_status(self) -> Dict[str, Any]:
        return {
            "type": "SAP",
            "connected": False,
            "message": "SAP adapter requires custom implementation (OData/RFC)."
        }
