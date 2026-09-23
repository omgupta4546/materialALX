import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.base import Classification
from app.repositories.base import ClassificationRepo

def test_classification_hierarchy(db_session: Session):
    repo = ClassificationRepo(db_session)
    
    # 1. Root
    root_id = str(uuid.uuid4())
    root = repo.create(
        classification_id=root_id,
        code="ROOT1",
        name="Root Category",
        level=0
    )
    
    assert root.parent_id is None
    
    # 2. Child
    child_id = str(uuid.uuid4())
    child = repo.create(
        classification_id=child_id,
        parent_id=root_id,
        code="CHILD1",
        name="Child Category",
        level=1
    )
    
    assert child.parent_id == root_id
    
    # 3. Test queries
    roots = repo.get_roots()
    assert any(r.classification_id == root_id for r in roots)
    
    children = repo.get_children(root_id)
    assert len(children) == 1
    assert children[0].classification_id == child_id

    # 4. ORM Relationship
    # Need to query from db to ensure relationship loaded
    root_from_db = repo.db.query(Classification).filter_by(classification_id=root_id).first()
    assert len(root_from_db.children) == 1
    assert root_from_db.children[0].classification_id == child_id
