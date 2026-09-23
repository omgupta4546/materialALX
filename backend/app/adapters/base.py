from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class SourceMaterialDTO:
    """Data Transfer Object representing a material fetched from a source system."""
    def __init__(self, legacy_code: str, description: str, uom: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
        self.legacy_code = legacy_code
        self.description = description
        self.uom = uom
        self.attributes = attributes or {}

class MaterialSourceAdapter(ABC):
    """
    Abstract interface for integrating external ERP or source systems.
    The core platform relies on this interface to avoid proprietary coupling.
    """

    @abstractmethod
    def fetch_materials(self, since: Optional[datetime] = None) -> List[SourceMaterialDTO]:
        """Fetch materials from the source system. Optionally filter by modification date."""
        pass

    @abstractmethod
    def get_material(self, legacy_code: str) -> Optional[SourceMaterialDTO]:
        """Fetch a single material by its legacy code."""
        pass

    @abstractmethod
    def create_mapping(self, legacy_code: str, national_code: str) -> bool:
        """Inform the source system that a new mapping to a National Material code has been established."""
        pass

    @abstractmethod
    def update_mapping(self, legacy_code: str, national_code: str) -> bool:
        """Update an existing mapping in the source system."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check connection health to the source system."""
        pass

    @abstractmethod
    def sync_status(self) -> Dict[str, Any]:
        """Return diagnostic metrics regarding synchronization status."""
        pass
