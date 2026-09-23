from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repositories.base import CPSERepo
from app.models.base import CPSE
from app.schemas.cpse import CPSECreate, CPSEUpdate

class CPSEService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CPSERepo(db)

    def get_cpse(self, cpse_id: str) -> Optional[CPSE]:
        return self.repo.get(cpse_id)
        
    def get_cpse_by_code(self, code: str) -> Optional[CPSE]:
        return self.repo.get_by_code(code)

    def list_cpses(self, skip: int = 0, limit: int = 100) -> List[CPSE]:
        return self.db.query(CPSE).offset(skip).limit(limit).all()

    def create_cpse(self, cpse_in: CPSECreate) -> CPSE:
        existing = self.repo.get_by_code(cpse_in.cpse_code)
        if existing:
            raise HTTPException(status_code=400, detail="CPSE code already exists")
            
        new_cpse = CPSE(
            cpse_code=cpse_in.cpse_code,
            cpse_name=cpse_in.cpse_name,
            sector=cpse_in.sector,
            description=cpse_in.description,
            status=cpse_in.status
        )
        self.db.add(new_cpse)
        self.db.commit()
        self.db.refresh(new_cpse)
        return new_cpse

    def update_cpse(self, cpse_id: str, cpse_in: CPSEUpdate) -> CPSE:
        cpse = self.repo.get_or_raise(cpse_id)
        
        update_data = cpse_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cpse, field, value)
            
        self.db.commit()
        self.db.refresh(cpse)
        return cpse

    def delete_cpse(self, cpse_id: str) -> None:
        cpse = self.repo.get_or_raise(cpse_id)
        self.db.delete(cpse)
        self.db.commit()
