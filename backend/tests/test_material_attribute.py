import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.base import AttributeDefinition, MaterialAttribute, Classification, NationalMaterial
from app.repositories.base import AttributeDefinitionRepo, MaterialAttributeRepo, NationalMaterialRepo

def test_attribute_definition_creation(db_session: Session):
    repo = AttributeDefinitionRepo(db_session)
    
    # 1. Create a classification first (setup)
    class_id = str(uuid.uuid4())
    class_code = f"CLS-{uuid.uuid4().hex[:8]}"
    db_session.add(Classification(classification_id=class_id, code=class_code, name="Test Category"))
    db_session.flush()

    # 2. Create Attribute Definition
    attr_def = repo.create(
        attribute_definition_id=str(uuid.uuid4()),
        classification_id=class_id,
        attribute_name="Bore Size",
        data_type="NUMBER",
        is_required=False,
        description="Inner diameter of bearing"
    )
    
    assert attr_def.attribute_name == "Bore Size"
    assert attr_def.data_type == "NUMBER"
    assert not attr_def.is_required


def test_material_attribute_constraints(db_session: Session):
    repo = MaterialAttributeRepo(db_session)
    nm_repo = NationalMaterialRepo(db_session)
    
    # 1. Setup a national material to reference
    national_material_id = str(uuid.uuid4())
    nm_repo.create(
        national_material_id=national_material_id,
        national_material_code=f"NM-{uuid.uuid4().hex[:8]}",
        canonical_description="Test Material for Attr"
    )

    # 2. Test valid creation (linking to national material only)
    attr = repo.create(
        material_attribute_id=str(uuid.uuid4()),
        national_material_id=national_material_id,
        attribute_name="Voltage",
        original_value="220V",
        normalized_value="220",
        unit="V",
        extraction_method="MANUAL"
    )
    assert attr.normalized_value == "220"

    # 3. Test invalid creation (linking to both should fail constraint)
    with pytest.raises(IntegrityError):
        repo.create(
            material_attribute_id=str(uuid.uuid4()),
            national_material_id=national_material_id,
            normalized_material_id=str(uuid.uuid4()), # both populated
            attribute_name="Invalid Attr",
            original_value="Bad"
        )
        db_session.flush()
    db_session.rollback()

    # 4. Test invalid creation (linking to neither should fail constraint)
    with pytest.raises(IntegrityError):
        repo.create(
            material_attribute_id=str(uuid.uuid4()),
            attribute_name="Invalid Attr 2",
            original_value="Bad"
        )
        db_session.flush()
    db_session.rollback()
