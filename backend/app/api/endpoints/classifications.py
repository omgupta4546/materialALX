import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db

from app.core.connection import SessionLocal
from app.models.base import Classification
from app.schemas.classifications import (
    ClassificationCreate, ClassificationUpdate, 
    ClassificationMove, ClassificationRead, ClassificationNode
)

router = APIRouter(tags=["Classifications"])



def build_tree(nodes: List[Classification], parent_id: Optional[str] = None) -> List[ClassificationNode]:
    """Recursively build a tree of classifications."""
    tree = []
    for node in nodes:
        if node.parent_id == parent_id:
            children = build_tree(nodes, node.classification_id)
            tree.append(ClassificationNode(
                classification_id=node.classification_id,
                code=node.code,
                name=node.name,
                description=node.description,
                level=node.level,
                status=node.status,
                parent_id=node.parent_id,
                version=node.version,
                is_latest=node.is_latest,
                children=children
            ))
    return tree

@router.get("/tree", response_model=List[ClassificationNode])
def get_classification_tree(db: Session = Depends(get_db)):
    """Return the entire ACTIVE taxonomy as a hierarchical tree."""
    # We only pull latest & active for the standard tree view
    all_nodes = db.query(Classification).filter(
        Classification.status == "ACTIVE",
        Classification.is_latest == True
    ).all()
    return build_tree(all_nodes, None)

@router.post("", response_model=ClassificationRead)
def create_classification(class_in: ClassificationCreate, db: Session = Depends(get_db)):
    """Admin: Create a new taxonomy classification node."""
    new_id = str(uuid.uuid4())
    
    level = 0
    if class_in.parent_id:
        parent = db.query(Classification).filter(Classification.classification_id == class_in.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent not found")
        level = parent.level + 1
        
    db_obj = Classification(
        classification_id=new_id,
        code=class_in.code,
        name=class_in.name,
        description=class_in.description,
        parent_id=class_in.parent_id,
        level=level,
        status="ACTIVE",
        version=1,
        is_latest=True
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@router.put("/{class_id}", response_model=ClassificationRead)
def update_classification(class_id: str, update_in: ClassificationUpdate, db: Session = Depends(get_db)):
    """Admin: Edit description or name of a classification."""
    obj = db.query(Classification).filter(Classification.classification_id == class_id, Classification.is_latest == True).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Classification not found or not latest")
        
    # Standard edit (not versioned for simple typo fixes to description, as per typical design, 
    # but could trigger new version if strict. We will just update inplace for now).
    if update_in.name: obj.name = update_in.name
    if update_in.description: obj.description = update_in.description
    
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/{class_id}/move", response_model=ClassificationRead)
def move_classification(class_id: str, move_in: ClassificationMove, db: Session = Depends(get_db)):
    """Admin: Move a classification to a new parent. This creates a new version for traceability."""
    obj = db.query(Classification).filter(Classification.classification_id == class_id, Classification.is_latest == True).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Classification not found or not latest")
        
    new_level = 0
    if move_in.new_parent_id:
        parent = db.query(Classification).filter(Classification.classification_id == move_in.new_parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="New parent not found")
        new_level = parent.level + 1
        
    # Deprecate old version
    obj.is_latest = False
    
    # Create new version
    new_id = str(uuid.uuid4())
    new_obj = Classification(
        classification_id=new_id,
        code=obj.code,
        name=obj.name,
        description=obj.description,
        parent_id=move_in.new_parent_id,
        level=new_level,
        status="ACTIVE",
        version=obj.version + 1,
        is_latest=True
    )
    
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return new_obj

@router.post("/{class_id}/deactivate")
def deactivate_classification(class_id: str, db: Session = Depends(get_db)):
    """Admin: Soft-delete a classification. Historical records pointing here remain intact."""
    obj = db.query(Classification).filter(Classification.classification_id == class_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Classification not found")
        
    obj.status = "INACTIVE"
    db.commit()
    return {"message": f"Classification {class_id} deactivated."}
