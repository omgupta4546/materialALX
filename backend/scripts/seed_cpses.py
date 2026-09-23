import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.connection import SessionLocal, engine
from app.models.base import Base
from app.services.cpse_service import CPSEService
from app.schemas.cpse import CPSECreate
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FICTIONAL_CPSES = [
    {
        "cpse_code": "POWER_GRID_FIC",
        "cpse_name": "Power Grid Fiction Ltd",
        "sector": "Power",
        "description": "Fictional energy distribution CPSE",
        "status": "ACTIVE"
    },
    {
        "cpse_code": "STEEL_CORP_FAKE",
        "cpse_name": "Steel Corporation Fake",
        "sector": "Steel",
        "description": "Fictional steel manufacturing CPSE",
        "status": "ACTIVE"
    },
    {
        "cpse_code": "OIL_GAS_MOCK",
        "cpse_name": "Mock Oil & Gas Enterprise",
        "sector": "Oil & Gas",
        "description": "Fictional petrochemical CPSE",
        "status": "ACTIVE"
    },
    {
        "cpse_code": "MINING_FIC",
        "cpse_name": "Fictional Mining Corp",
        "sector": "Mining",
        "description": "Fictional coal and ore mining CPSE",
        "status": "ACTIVE"
    },
    {
        "cpse_code": "HEAVY_ENG_MOCK",
        "cpse_name": "Mock Heavy Engineering",
        "sector": "Heavy Engineering",
        "description": "Fictional heavy machinery CPSE",
        "status": "ACTIVE"
    }
]

def seed_cpses():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    service = CPSEService(db)
    
    logger.info("Starting CPSE seeding...")
    added_count = 0
    
    for cpse_data in FICTIONAL_CPSES:
        existing = service.get_cpse_by_code(cpse_data["cpse_code"])
        if not existing:
            cpse_in = CPSECreate(**cpse_data)
            service.create_cpse(cpse_in)
            logger.info(f"Created CPSE: {cpse_data['cpse_code']}")
            added_count += 1
        else:
            logger.info(f"Skipped CPSE (already exists): {cpse_data['cpse_code']}")
            
    logger.info(f"Seeding complete. Added {added_count} new CPSEs.")
    db.close()

if __name__ == "__main__":
    seed_cpses()
