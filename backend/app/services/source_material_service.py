from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid

from app.repositories.base import SourceMaterialRepo
from app.schemas.source_material import SourceMaterialCreate
from app.models.base import SourceMaterial

class SourceMaterialService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SourceMaterialRepo(db)

    def create_material(self, data: SourceMaterialCreate) -> SourceMaterial:
        # Check for uniqueness: CPSE + Legacy Code
        existing = self.repo.get_by_cpse_and_legacy_code(data.cpse_id, data.legacy_material_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Material with legacy code '{data.legacy_material_code}' already exists for CPSE '{data.cpse_id}'"
            )

        return self.repo.create(
            source_material_id=str(uuid.uuid4()),
            **data.model_dump()
        )

    def get_material(self, source_material_id: str) -> SourceMaterial:
        record = self.repo.get(source_material_id)
        if not record:
            raise HTTPException(status_code=404, detail="Source material not found")
        return record

    def get_materials_by_cpse(self, cpse_id: str, skip: int = 0, limit: int = 100) -> list[SourceMaterial]:
        return self.repo.get_by_cpse(cpse_id, limit=limit, offset=skip)
