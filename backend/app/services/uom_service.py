from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.base import UOMMaster

class UOMService:
    def __init__(self, db: Session):
        self.db = db
        
    def get_all(self, dimension: Optional[str] = None, status: Optional[str] = None) -> List[UOMMaster]:
        query = self.db.query(UOMMaster)
        if dimension:
            query = query.filter(UOMMaster.dimension == dimension)
        if status:
            query = query.filter(UOMMaster.status == status)
        return query.all()

    def get_by_code(self, canonical_code: str) -> Optional[UOMMaster]:
        return self.db.query(UOMMaster).filter(UOMMaster.canonical_code == canonical_code).first()

    def create(self, canonical_code: str, name: str, dimension: str, aliases: List[str], 
               base_multiplier: float = 1.0, is_base_unit: bool = False, status: str = "ACTIVE") -> UOMMaster:
        if self.get_by_code(canonical_code):
            raise ValueError(f"UOM {canonical_code} already exists.")
            
        uom = UOMMaster(
            canonical_code=canonical_code,
            name=name,
            dimension=dimension,
            aliases=aliases,
            base_multiplier=base_multiplier,
            is_base_unit=is_base_unit,
            status=status
        )
        self.db.add(uom)
        self.db.commit()
        self.db.refresh(uom)
        return uom

    def normalize(self, raw_uom: str) -> Optional[str]:
        """
        Takes a raw UOM string (e.g. 'PCS', 'KG', 'EACH') and returns the canonical_code.
        First attempts exact match, then searches aliases (case-insensitive).
        """
        if not raw_uom:
            return None
            
        raw_upper = raw_uom.strip().upper()
        
        # 1. Exact canonical match
        uom = self.get_by_code(raw_upper)
        if uom:
            return uom.canonical_code
            
        # 2. Search aliases
        # This is a bit inefficient for a large DB, but UOMMaster is typically very small.
        # For larger scales, caching or a dedicated synonym table is better.
        all_uoms = self.db.query(UOMMaster).all()
        for uom in all_uoms:
            if uom.aliases:
                aliases_upper = [a.upper() for a in uom.aliases]
                if raw_upper in aliases_upper:
                    return uom.canonical_code
                    
        return None

    def convert(self, value: float, from_uom: str, to_uom: str) -> float:
        """
        Safely converts a value from one UOM to another by mathematically routing
        through the base unit. Both UOMs must share the same dimension.
        """
        from_canonical = self.normalize(from_uom)
        to_canonical = self.normalize(to_uom)
        
        if not from_canonical or not to_canonical:
            raise ValueError("One or both UOMs could not be recognized.")
            
        uom_src = self.get_by_code(from_canonical)
        uom_dst = self.get_by_code(to_canonical)
        
        if uom_src.dimension != uom_dst.dimension:
            raise ValueError(f"Incompatible dimensions: Cannot convert {uom_src.dimension} to {uom_dst.dimension}")
            
        # Mathematical conversion through the base unit
        # To Base: value * uom_src.base_multiplier
        # To Dest: (value * uom_src.base_multiplier) / uom_dst.base_multiplier
        return (value * uom_src.base_multiplier) / uom_dst.base_multiplier
