import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import MaterialSourceAdapter, SourceMaterialDTO

class CSVAdapter(MaterialSourceAdapter):
    """
    Adapter for processing flat CSV files.
    This simulates integration by treating a local/remote CSV as the 'ERP' source.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._mappings = {} # Simulates storing mappings locally

    def fetch_materials(self, since: Optional[datetime] = None) -> List[SourceMaterialDTO]:
        if not os.path.exists(self.file_path):
            return []
            
        results = []
        with open(self.file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Assume standard columns for simulation
                code = row.get("material_code", row.get("legacy_code", ""))
                desc = row.get("description", "")
                uom = row.get("uom", None)
                
                if code and desc:
                    results.append(SourceMaterialDTO(legacy_code=code, description=desc, uom=uom))
        return results

    def get_material(self, legacy_code: str) -> Optional[SourceMaterialDTO]:
        materials = self.fetch_materials()
        for m in materials:
            if m.legacy_code == legacy_code:
                return m
        return None

    def create_mapping(self, legacy_code: str, national_code: str) -> bool:
        self._mappings[legacy_code] = national_code
        return True

    def update_mapping(self, legacy_code: str, national_code: str) -> bool:
        self._mappings[legacy_code] = national_code
        return True

    def health_check(self) -> bool:
        return os.path.exists(self.file_path)

    def sync_status(self) -> Dict[str, Any]:
        return {
            "type": "CSV",
            "file_exists": self.health_check(),
            "mappings_synced": len(self._mappings)
        }
