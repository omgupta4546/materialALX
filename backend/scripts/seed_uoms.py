import os
import sys

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.connection import SessionLocal
from app.services.uom_service import UOMService

def seed_uoms():
    db = SessionLocal()
    svc = UOMService(db)
    
    uoms_to_seed = [
        # COUNT
        {"canonical_code": "EA", "name": "Each", "dimension": "COUNT", "aliases": ["PCS", "PIECES", "EACH", "NO"], "base_multiplier": 1.0, "is_base_unit": True},
        # MASS
        {"canonical_code": "KG", "name": "Kilogram", "dimension": "MASS", "aliases": ["KGS", "KILO"], "base_multiplier": 1.0, "is_base_unit": True},
        {"canonical_code": "MT", "name": "Metric Ton", "dimension": "MASS", "aliases": ["TON", "TONNE"], "base_multiplier": 1000.0, "is_base_unit": False},
        # LENGTH
        {"canonical_code": "MM", "name": "Millimeter", "dimension": "LENGTH", "aliases": ["MILLIMETER"], "base_multiplier": 1.0, "is_base_unit": True},
        {"canonical_code": "M", "name": "Meter", "dimension": "LENGTH", "aliases": ["MTR", "METER"], "base_multiplier": 1000.0, "is_base_unit": False},
        {"canonical_code": "IN", "name": "Inch", "dimension": "LENGTH", "aliases": ["INCH", "''", "\""], "base_multiplier": 25.4, "is_base_unit": False},
        # VOLUME
        {"canonical_code": "L", "name": "Liter", "dimension": "VOLUME", "aliases": ["LTR", "LITER"], "base_multiplier": 1.0, "is_base_unit": True},
    ]
    
    for uom_data in uoms_to_seed:
        if not svc.get_by_code(uom_data["canonical_code"]):
            svc.create(**uom_data)
            print(f"Seeded UOM: {uom_data['canonical_code']}")
        else:
            print(f"UOM {uom_data['canonical_code']} already exists.")
            
    db.close()

if __name__ == "__main__":
    seed_uoms()
