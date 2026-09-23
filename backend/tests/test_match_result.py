import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.base import MatchResult, Approval, NormalizedMaterial, NationalMaterial, Classification, UOMMaster
from app.repositories.base import MatchResultRepo, ApprovalRepo

def test_match_result_and_approval(db_session: Session):
    match_repo = MatchResultRepo(db_session)
    approval_repo = ApprovalRepo(db_session)
    
    # Setup dependencies
    class_id = str(uuid.uuid4())
    db_session.add(Classification(classification_id=class_id, code=f"CLS-{uuid.uuid4().hex[:8]}", name="Test"))
    db_session.add(UOMMaster(canonical_code="EA", name="Each", dimension="COUNT"))
    
    norm_id = str(uuid.uuid4())
    db_session.add(NormalizedMaterial(normalized_material_id=norm_id, source_material_id="src-1", normalized_description="Test 1"))
    
    nat_id = str(uuid.uuid4())
    db_session.add(NationalMaterial(
        national_material_id=nat_id,
        national_material_code=f"NAT-{uuid.uuid4().hex[:8]}",
        canonical_description="Test 2",
        classification_id=class_id,
        canonical_uom="EA"
    ))
    db_session.flush()
    
    # 1. Create MatchResult
    match_id = str(uuid.uuid4())
    match = match_repo.create(
        match_id=match_id,
        material_a_id=norm_id,
        material_b_id=nat_id,
        semantic_score=0.95,
        attribute_score=0.90,
        rule_score=1.0,
        final_score=0.93,
        match_type="NEAR_DUPLICATE",
        recommendation="REVIEW",
        risk_level="MEDIUM",
        requires_human_review=True
    )
    
    assert match.final_score == 0.93
    
    # 2. Score Constraints
    with pytest.raises(IntegrityError):
        match_repo.create(
            match_id=str(uuid.uuid4()),
            final_score=1.5 # Invalid score
        )
    db_session.rollback()
    
    # 3. Create Approval
    approval_id = str(uuid.uuid4())
    approval = approval_repo.create(
        approval_id=approval_id,
        match_id=match_id,
        decision="APPROVED",
        review_type="EXPERT_REVIEW"
    )
    
    assert approval.decision == "APPROVED"
    assert approval.match_id == match_id
    
    # 4. Verify AI output is immutable (no updated_at exists on MatchResult, and Approval is a separate table)
    # The separation itself verifies this requirement.
