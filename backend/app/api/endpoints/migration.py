from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import uuid

from app.api.deps import get_db
from app.auth.rbac import require_role
from app.models.base import MigrationBatch, MigrationRecord, MaterialMapping, User

router = APIRouter()

class MigrationBatchCreate(BaseModel):
    name: str
    legacy_codes: List[str]

class MigrationBatchResponse(BaseModel):
    batch_id: str
    name: str
    status: str
    created_by: Optional[str]
    created_at: datetime
    record_count: int

@router.post("/batches", response_model=MigrationBatchResponse, status_code=201)
def create_migration_batch(
    payload: MigrationBatchCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["DATA_STEWARD", "ADMIN"]))
):
    """Create a new migration batch in DRAFT status."""
    batch = MigrationBatch(
        batch_id=str(uuid.uuid4()),
        name=payload.name,
        status="DRAFT",
        created_by=user.get("user_id") or user.get("sub")
    )
    db.add(batch)
    
    # We find the approved mappings for these legacy codes
    mappings = db.query(MaterialMapping).filter(
        MaterialMapping.source.has(legacy_material_code=MaterialMapping.source_material_id.in_(payload.legacy_codes)), # Simplifying join for mock
        MaterialMapping.status == "APPROVED"
    ).all() # This is a placeholder logic for the actual join required.
    
    # Actually let's just do a simpler loop for the hackathon
    count = 0
    for code in payload.legacy_codes:
        # Check if there is an approved mapping
        mapping = db.query(MaterialMapping).join(MaterialMapping.source).filter(
            MaterialMapping.source.has(legacy_material_code=code),
            MaterialMapping.status == "APPROVED"
        ).first()
        
        national_code = mapping.national.national_material_code if mapping else "UNKNOWN"
        mapping_id = mapping.mapping_id if mapping else None
        
        record = MigrationRecord(
            record_id=str(uuid.uuid4()),
            batch_id=batch.batch_id,
            legacy_code=code,
            national_code=national_code,
            mapping_id=mapping_id,
            status="DRAFT"
        )
        db.add(record)
        count += 1
        
    db.commit()
    db.refresh(batch)
    
    return MigrationBatchResponse(
        batch_id=batch.batch_id,
        name=batch.name,
        status=batch.status,
        created_by=batch.created_by,
        created_at=batch.created_at,
        record_count=count
    )

@router.get("/batches", response_model=List[MigrationBatchResponse])
def list_migration_batches(db: Session = Depends(get_db)):
    batches = db.query(MigrationBatch).order_by(MigrationBatch.created_at.desc()).all()
    results = []
    for b in batches:
        count = db.query(MigrationRecord).filter(MigrationRecord.batch_id == b.batch_id).count()
        results.append(MigrationBatchResponse(
            batch_id=b.batch_id,
            name=b.name,
            status=b.status,
            created_by=b.created_by,
            created_at=b.created_at,
            record_count=count
        ))
    return results

@router.post("/batches/{batch_id}/validate")
def validate_batch(batch_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["DATA_STEWARD", "ADMIN"]))):
    batch = db.query(MigrationBatch).filter(MigrationBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
        
    records = db.query(MigrationRecord).filter(MigrationRecord.batch_id == batch_id).all()
    all_valid = all(r.national_code != "UNKNOWN" for r in records)
    
    new_status = "VALIDATED" if all_valid else "FAILED"
    batch.status = new_status
    for r in records:
        r.status = new_status
        r.operator_id = user.get("user_id") or user.get("sub")
        
    db.commit()
    return {"status": new_status}

@router.post("/batches/{batch_id}/approve")
def approve_batch(batch_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["ADMIN"]))):
    batch = db.query(MigrationBatch).filter(MigrationBatch.batch_id == batch_id).first()
    if not batch or batch.status != "VALIDATED":
        raise HTTPException(status_code=400, detail="Batch must be VALIDATED to approve")
        
    batch.status = "APPROVED"
    db.query(MigrationRecord).filter(MigrationRecord.batch_id == batch_id).update({"status": "APPROVED", "operator_id": user.get("user_id") or user.get("sub")})
    db.commit()
    return {"status": "APPROVED"}

@router.post("/batches/{batch_id}/execute")
def execute_batch(batch_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["ADMIN"]))):
    batch = db.query(MigrationBatch).filter(MigrationBatch.batch_id == batch_id).first()
    if not batch or batch.status not in ["APPROVED", "READY"]:
        raise HTTPException(status_code=400, detail="Batch must be APPROVED or READY to execute")
        
    # Simulate execution
    batch.status = "EXECUTED"
    db.query(MigrationRecord).filter(MigrationRecord.batch_id == batch_id).update({
        "status": "EXECUTED",
        "operator_id": user.get("user_id") or user.get("sub"),
        "result": "Simulated successful SAP OData sync"
    })
    db.commit()
    return {"status": "EXECUTED"}

@router.post("/batches/{batch_id}/rollback")
def rollback_batch(batch_id: str, db: Session = Depends(get_db), user: dict = Depends(require_role(["ADMIN"]))):
    batch = db.query(MigrationBatch).filter(MigrationBatch.batch_id == batch_id).first()
    if not batch or batch.status != "EXECUTED":
        raise HTTPException(status_code=400, detail="Only EXECUTED batches can be rolled back")
        
    batch.status = "ROLLED_BACK"
    db.query(MigrationRecord).filter(MigrationRecord.batch_id == batch_id).update({
        "status": "ROLLED_BACK",
        "operator_id": user.get("user_id") or user.get("sub"),
        "result": "Rolled back successfully"
    })
    db.commit()
    return {"status": "ROLLED_BACK"}
