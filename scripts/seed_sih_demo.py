import sys
import os
import json

# Add backend to path so we can run scripts from root
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

import uuid
from sqlalchemy.orm import Session
from app.core.connection import SessionLocal
from app.models.base import CPSE, NationalMaterial, Classification

def seed_sih_demo():
    db: Session = SessionLocal()
    
    # 1. Ensure Demo CPSE
    cpse = db.query(CPSE).filter_by(cpse_code="DEMO-SIH").first()
    if not cpse:
        cpse = CPSE(
            cpse_code="DEMO-SIH",
            cpse_name="SIH Demo Organization",
            sector="Manufacturing",
            status="ACTIVE"
        )
        db.add(cpse)
        db.commit()
        db.refresh(cpse)
        print(f"Created CPSE DEMO-SIH (ID: {cpse.cpse_id})")
    else:
        print(f"Found CPSE DEMO-SIH (ID: {cpse.cpse_id})")

    # 2. Ensure classification for Valve
    valve_class = db.query(Classification).filter_by(code="VALVE-01").first()
    if not valve_class:
        valve_class = Classification(
            classification_id=str(uuid.uuid4()),
            code="VALVE-01",
            name="Valves",
            level="CATEGORY",
            description="All mechanical valves"
        )
        db.add(valve_class)
        db.commit()
        
    # 3. Ensure National Material Target (NAT-001)
    nat = db.query(NationalMaterial).filter_by(national_material_code="NAT-001").first()
    if not nat:
        nat = NationalMaterial(
            national_material_id=str(uuid.uuid4()),
            national_material_code="NAT-001",
            classification_id=valve_class.classification_id if valve_class else None,
            canonical_description="GATE VALVE 6IN CL150 CS",
            canonical_uom="EA",
            status="ACTIVE",
            attributes={
                "type": "GATE VALVE",
                "size": "6IN",
                "pressure_class": "150#",
                "body_material": "CS"
            }
        )
        db.add(nat)
        db.commit()
        print("Created National Material NAT-001")
    else:
        print("Found National Material NAT-001")

    # 4. Generate demo_upload_batch.json
    batch_data = [
        {
            "material_code": "SRC-DEMO-001",
            "description": "GATE VALVE 6IN CLASS 150 (Synthetic Safe Match)",
            "uom": "EA"
        },
        {
            "material_code": "SRC-DEMO-002",
            "description": "GATE VALVE 6IN CLASS 300 (Synthetic Dangerous Match)",
            "uom": "EA"
        },
        {
            "material_code": "SRC-DEMO-003",
            "description": "BALL BEARING 6205 2RS SKF (Synthetic No Match)",
            "uom": "EA"
        }
    ]
    
    out_path = os.path.join(os.path.dirname(__file__), "../demo_upload_batch.json")
    with open(out_path, "w") as f:
        json.dump(batch_data, f, indent=2)
        
    print(f"\n✅ Created demo_upload_batch.json at {out_path}")
    print(f"   Please login to the UI, select 'SIH Demo Organization', and upload this file.")
    print(f"   - SRC-DEMO-001 will safely match to NAT-001.")
    print(f"   - SRC-DEMO-002 will trigger Engineering Review due to pressure clash (150# vs 300#).")

if __name__ == "__main__":
    seed_sih_demo()
