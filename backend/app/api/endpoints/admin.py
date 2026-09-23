"""
api/endpoints/admin.py

Unified Admin / Governance API.
All write routes require ADMIN role.
Read routes allow ADMIN + DATA_STEWARD (+ ENGINEER for registries).
Every mutating action writes an immutable AuditLog entry.

Covered entities:
  Users, Roles, CPSEs, Synonyms, UOM Master, Matching Rules,
  Model Registry, Prompt Registry, Governance Policies (GovernancePolicy),
  Audit Log read-back
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.api.deps import get_db

from app.auth.rbac import require_role, Roles
from app.core.connection import SessionLocal
from app.models.base import (
    AuditLog, CPSE, MatchingRule, ModelRegistry, PromptRegistry,
    Role, Synonym, UOMMaster, User,
)

router = APIRouter(tags=["Admin"])

ADMIN_ONLY   = [Roles.ADMIN]
READ_ROLES   = [Roles.ADMIN, Roles.DATA_STEWARD, Roles.ENGINEER]
WRITE_ROLES  = [Roles.ADMIN, Roles.DATA_STEWARD]





def _audit(
    db: Session, entity_type: str, entity_id: str,
    action: str, old: Any, new: Any, actor_id: Optional[str],
):
    db.add(AuditLog(
        audit_id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old,
        new_value=new,
        actor_id=actor_id,
        timestamp=datetime.utcnow(),
        source="admin_api",
    ))


# ══════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    name: Optional[str]
    email: Optional[str]
    role_id: Optional[str]
    cpse_code: Optional[str]
    permissions: Optional[List[str]]
    is_retired: bool

class UserCreate(BaseModel):
    user_id: str
    name: str
    email: str
    role_id: str
    cpse_code: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[str] = None
    cpse_code: Optional[str] = None
    permissions: Optional[List[str]] = None


@router.get("/users", response_model=List[UserRead], dependencies=[Depends(require_role(ADMIN_ONLY))])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.name).all()


@router.post("/users", response_model=UserRead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    if db.query(User).filter(User.user_id == payload.user_id).first():
        raise HTTPException(409, "User ID already exists")
    u = User(**payload.model_dump())
    db.add(u)
    _audit(db, "user", u.user_id, "CREATE", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(u)
    return u


@router.put("/users/{user_id}", response_model=UserRead, dependencies=[Depends(require_role(ADMIN_ONLY))])
def update_user(
    user_id: str, payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    u = db.query(User).filter(User.user_id == user_id).first()
    if not u: raise HTTPException(404, "User not found")
    old = {"role_id": u.role_id, "cpse_code": u.cpse_code, "permissions": u.permissions}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    _audit(db, "user", user_id, "UPDATE", old, payload.model_dump(exclude_none=True), current_user.get("user_id"))
    db.commit(); db.refresh(u)
    return u


@router.delete("/users/{user_id}", dependencies=[Depends(require_role(ADMIN_ONLY))])
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    u = db.query(User).filter(User.user_id == user_id).first()
    if not u: raise HTTPException(404, "User not found")
    u.is_retired = True
    _audit(db, "user", user_id, "DEACTIVATE", {"is_retired": False}, {"is_retired": True}, current_user.get("user_id"))
    db.commit()
    return {"message": f"User {user_id} deactivated"}


# ══════════════════════════════════════════════════════════════════
# ROLES
# ══════════════════════════════════════════════════════════════════

class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    description: Optional[str]

class RoleCreate(BaseModel):
    id: str
    description: Optional[str] = None


@router.get("/roles", response_model=List[RoleRead], dependencies=[Depends(require_role(ADMIN_ONLY))])
def list_roles(db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.id).all()


@router.post("/roles", response_model=RoleRead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    if db.query(Role).filter(Role.id == payload.id).first():
        raise HTTPException(409, "Role already exists")
    r = Role(**payload.model_dump())
    db.add(r)
    _audit(db, "role", r.id, "CREATE", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(r)
    return r


# ══════════════════════════════════════════════════════════════════
# CPSEs
# ══════════════════════════════════════════════════════════════════

class CPSERead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    cpse_id: str
    cpse_code: str
    cpse_name: str
    sector: Optional[str]
    description: Optional[str]
    status: str

class CPSECreate(BaseModel):
    cpse_code: str
    cpse_name: str
    sector: Optional[str] = None
    description: Optional[str] = None

class CPSEUpdate(BaseModel):
    cpse_name: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.get("/cpses", response_model=List[CPSERead], dependencies=[Depends(require_role(READ_ROLES))])
def list_cpses(db: Session = Depends(get_db)):
    return db.query(CPSE).order_by(CPSE.cpse_name).all()


@router.post("/cpses", response_model=CPSERead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def create_cpse(
    payload: CPSECreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    c = CPSE(cpse_id=str(uuid.uuid4()), **payload.model_dump())
    db.add(c)
    _audit(db, "cpse", c.cpse_id, "CREATE", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(c)
    return c


@router.put("/cpses/{cpse_id}", response_model=CPSERead, dependencies=[Depends(require_role(ADMIN_ONLY))])
def update_cpse(
    cpse_id: str, payload: CPSEUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    c = db.query(CPSE).filter(CPSE.cpse_id == cpse_id).first()
    if not c: raise HTTPException(404, "CPSE not found")
    old = {"cpse_name": c.cpse_name, "status": c.status}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    _audit(db, "cpse", cpse_id, "UPDATE", old, payload.model_dump(exclude_none=True), current_user.get("user_id"))
    db.commit(); db.refresh(c)
    return c


# ══════════════════════════════════════════════════════════════════
# SYNONYMS
# ══════════════════════════════════════════════════════════════════

class SynonymRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    term: str
    expansion: str
    is_ambiguous: bool
    source: Optional[str]

class SynonymCreate(BaseModel):
    term: str
    expansion: str
    is_ambiguous: bool = False
    source: str = "MANUAL"


@router.get("/synonyms", response_model=List[SynonymRead], dependencies=[Depends(require_role(READ_ROLES))])
def list_synonyms(
    term: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Synonym)
    if term:
        q = q.filter(Synonym.term.ilike(f"%{term}%"))
    return q.order_by(Synonym.term).limit(limit).all()


@router.post("/synonyms", response_model=SynonymRead, status_code=201, dependencies=[Depends(require_role(WRITE_ROLES))])
def create_synonym(
    payload: SynonymCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(WRITE_ROLES)),
):
    s = Synonym(**payload.model_dump())
    db.add(s)
    _audit(db, "synonym", f"{payload.term}:{payload.expansion}", "CREATE", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(s)
    return s


@router.delete("/synonyms/{synonym_id}", dependencies=[Depends(require_role(ADMIN_ONLY))])
def delete_synonym(
    synonym_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    s = db.query(Synonym).filter(Synonym.id == synonym_id).first()
    if not s: raise HTTPException(404, "Synonym not found")
    old = {"term": s.term, "expansion": s.expansion}
    _audit(db, "synonym", str(synonym_id), "DELETE", old, None, current_user.get("user_id"))
    db.delete(s)
    db.commit()
    return {"message": "Synonym deleted"}


# ══════════════════════════════════════════════════════════════════
# UOM MASTER
# ══════════════════════════════════════════════════════════════════

class UOMRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    canonical_code: str
    name: Optional[str]
    dimension: Optional[str]
    aliases: Optional[List[str]]
    status: str
    base_multiplier: Optional[float]
    is_base_unit: bool

class UOMCreate(BaseModel):
    canonical_code: str
    name: str
    dimension: str
    aliases: List[str] = Field(default_factory=list)
    base_multiplier: float = 1.0
    is_base_unit: bool = False

class UOMUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    status: Optional[str] = None
    base_multiplier: Optional[float] = None


@router.get("/uoms", response_model=List[UOMRead], dependencies=[Depends(require_role(READ_ROLES))])
def list_uoms(dimension: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(UOMMaster)
    if dimension:
        q = q.filter(UOMMaster.dimension == dimension)
    return q.order_by(UOMMaster.canonical_code).all()


@router.post("/uoms", response_model=UOMRead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def create_uom(
    payload: UOMCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    if db.query(UOMMaster).filter(UOMMaster.canonical_code == payload.canonical_code).first():
        raise HTTPException(409, "UOM already exists")
    u = UOMMaster(**payload.model_dump())
    db.add(u)
    _audit(db, "uom", u.canonical_code, "CREATE", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(u)
    return u


@router.put("/uoms/{code}", response_model=UOMRead, dependencies=[Depends(require_role(ADMIN_ONLY))])
def update_uom(
    code: str, payload: UOMUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    u = db.query(UOMMaster).filter(UOMMaster.canonical_code == code).first()
    if not u: raise HTTPException(404, "UOM not found")
    old = {"name": u.name, "aliases": u.aliases, "status": u.status}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    _audit(db, "uom", code, "UPDATE", old, payload.model_dump(exclude_none=True), current_user.get("user_id"))
    db.commit(); db.refresh(u)
    return u


# ══════════════════════════════════════════════════════════════════
# MATCHING RULES
# ══════════════════════════════════════════════════════════════════

class MatchingRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule_id: str
    rule_name: str
    description: Optional[str]
    logic_payload: Optional[Dict[str, Any]]
    is_active: bool

class MatchingRuleCreate(BaseModel):
    rule_name: str
    description: Optional[str] = None
    logic_payload: Dict[str, Any] = Field(default_factory=dict)

class MatchingRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    description: Optional[str] = None
    logic_payload: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


@router.get("/matching-rules", response_model=List[MatchingRuleRead], dependencies=[Depends(require_role(READ_ROLES))])
def list_matching_rules(db: Session = Depends(get_db)):
    return db.query(MatchingRule).order_by(MatchingRule.rule_name).all()


@router.post("/matching-rules", response_model=MatchingRuleRead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def create_matching_rule(
    payload: MatchingRuleCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    r = MatchingRule(rule_id=str(uuid.uuid4()), **payload.model_dump())
    db.add(r)
    _audit(db, "matching_rule", r.rule_id, "CREATE", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(r)
    return r


@router.put("/matching-rules/{rule_id}", response_model=MatchingRuleRead, dependencies=[Depends(require_role(ADMIN_ONLY))])
def update_matching_rule(
    rule_id: str, payload: MatchingRuleUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    r = db.query(MatchingRule).filter(MatchingRule.rule_id == rule_id).first()
    if not r: raise HTTPException(404, "Rule not found")
    old = {"rule_name": r.rule_name, "is_active": r.is_active}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    _audit(db, "matching_rule", rule_id, "UPDATE", old, payload.model_dump(exclude_none=True), current_user.get("user_id"))
    db.commit(); db.refresh(r)
    return r


# ══════════════════════════════════════════════════════════════════
# MODEL REGISTRY
# ══════════════════════════════════════════════════════════════════

class ModelRegistryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model_id: str
    model_name: str
    model_version: str
    provider: str
    task: str
    embedding_dimension: Optional[int]
    deployment_status: str
    created_at: datetime

class ModelRegistryCreate(BaseModel):
    model_name: str
    model_version: str
    provider: str
    task: str
    embedding_dimension: Optional[int] = None

class ModelStatusUpdate(BaseModel):
    deployment_status: str  # ACTIVE | DEPRECATED | ARCHIVED


@router.get("/model-registry", response_model=List[ModelRegistryRead], dependencies=[Depends(require_role(READ_ROLES))])
def list_models(db: Session = Depends(get_db)):
    return db.query(ModelRegistry).order_by(desc(ModelRegistry.created_at)).all()


@router.post("/model-registry", response_model=ModelRegistryRead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def register_model(
    payload: ModelRegistryCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    m = ModelRegistry(model_id=str(uuid.uuid4()), **payload.model_dump())
    db.add(m)
    _audit(db, "model_registry", m.model_id, "REGISTER", None, payload.model_dump(), current_user.get("user_id"))
    db.commit(); db.refresh(m)
    return m


@router.patch("/model-registry/{model_id}/status", response_model=ModelRegistryRead, dependencies=[Depends(require_role(ADMIN_ONLY))])
def update_model_status(
    model_id: str, payload: ModelStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    valid = {"ACTIVE", "DEPRECATED", "ARCHIVED"}
    if payload.deployment_status not in valid:
        raise HTTPException(400, f"Status must be one of {valid}")
    m = db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()
    if not m: raise HTTPException(404, "Model not found")
    old = {"deployment_status": m.deployment_status}
    m.deployment_status = payload.deployment_status
    _audit(db, "model_registry", model_id, "STATUS_CHANGE", old, {"deployment_status": payload.deployment_status}, current_user.get("user_id"))
    db.commit(); db.refresh(m)
    return m


# ══════════════════════════════════════════════════════════════════
# PROMPT REGISTRY
# ══════════════════════════════════════════════════════════════════

class PromptRegistryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    prompt_id: str
    task: str
    prompt_version: str
    prompt_template: str
    is_active: bool
    created_at: datetime

class PromptRegistryCreate(BaseModel):
    task: str
    prompt_version: str
    prompt_template: str


@router.get("/prompt-registry", response_model=List[PromptRegistryRead], dependencies=[Depends(require_role(READ_ROLES))])
def list_prompts(db: Session = Depends(get_db)):
    return db.query(PromptRegistry).order_by(desc(PromptRegistry.created_at)).all()


@router.post("/prompt-registry", response_model=PromptRegistryRead, status_code=201, dependencies=[Depends(require_role(ADMIN_ONLY))])
def register_prompt(
    payload: PromptRegistryCreate,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    p = PromptRegistry(prompt_id=str(uuid.uuid4()), is_active=True, **payload.model_dump())
    db.add(p)
    _audit(db, "prompt_registry", p.prompt_id, "REGISTER", None,
           {"task": p.task, "prompt_version": p.prompt_version}, current_user.get("user_id"))
    db.commit(); db.refresh(p)
    return p


@router.patch("/prompt-registry/{prompt_id}/deactivate", dependencies=[Depends(require_role(ADMIN_ONLY))])
def deactivate_prompt(
    prompt_id: str,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(require_role(ADMIN_ONLY)),
):
    p = db.query(PromptRegistry).filter(PromptRegistry.prompt_id == prompt_id).first()
    if not p: raise HTTPException(404, "Prompt not found")
    p.is_active = False
    _audit(db, "prompt_registry", prompt_id, "DEACTIVATE", {"is_active": True}, {"is_active": False}, current_user.get("user_id"))
    db.commit()
    return {"message": "Prompt deactivated"}


# ══════════════════════════════════════════════════════════════════
# AUDIT LOG (read-back)
# ══════════════════════════════════════════════════════════════════

class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    audit_id: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    action: Optional[str]
    old_value: Optional[Any]
    new_value: Optional[Any]
    actor_id: Optional[str]
    timestamp: datetime
    source: Optional[str]


@router.get("/audit", response_model=List[AuditLogRead], dependencies=[Depends(require_role(ADMIN_ONLY))])
def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = Query(200, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    return q.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()


@router.get("/audit/summary", dependencies=[Depends(require_role(ADMIN_ONLY))])
def audit_summary(db: Session = Depends(get_db)):
    """Quick counts by entity_type for the governance dashboard."""
    rows = (
        db.query(AuditLog.entity_type, func.count(AuditLog.audit_id).label("count"))
        .group_by(AuditLog.entity_type)
        .order_by(desc(func.count(AuditLog.audit_id)))
        .all()
    )
    return {"breakdown": [{"entity_type": r[0], "count": r[1]} for r in rows]}
