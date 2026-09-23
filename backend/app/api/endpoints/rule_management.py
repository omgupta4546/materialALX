"""
api/endpoints/rule_management.py

Admin-only REST API for governing matching rules:
  - CriticalRule CRUD (per category / attribute)
  - GlobalMatchingConfig (weights, thresholds, approval policy)

Every mutating action:
  1. Creates a new versioned DB record (immutable history).
  2. Writes an AuditLog entry.
  3. Returns the new active config.

Guarded by require_role([Roles.ADMIN]) — CPSE users are forbidden.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db

from app.auth.rbac import require_role, Roles
from app.core.connection import SessionLocal
from app.models.base import AuditLog, CriticalRule, GlobalMatchingConfig
from app.schemas.rule_management import (
    CriticalRuleCreate,
    CriticalRuleHistory,
    CriticalRuleRead,
    CriticalRuleUpdate,
    GlobalMatchingConfigCreate,
    GlobalMatchingConfigRead,
    RuleAuditEntry,
)

router = APIRouter(tags=["Rule Management"])

# Only ADMIN may write rules; ENGINEER / DATA_STEWARD may read.
ADMIN_ONLY  = [Roles.ADMIN]
READ_ROLES  = [Roles.ADMIN, Roles.ENGINEER, Roles.DATA_STEWARD]


# ──────────────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────────────




def _write_audit(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    old_value: Optional[Dict[str, Any]],
    new_value: Optional[Dict[str, Any]],
    actor_id: Optional[str],
):
    """Append an immutable audit event — never updated, never deleted."""
    entry = AuditLog(
        audit_id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        actor_id=actor_id,
        timestamp=datetime.utcnow(),
        source="rule_management_api",
        rules_version="n/a",
    )
    db.add(entry)


# ──────────────────────────────────────────────────────────────────────────────
# Critical Rules
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/critical-rules",
    response_model=List[CriticalRuleRead],
    dependencies=[Depends(require_role(READ_ROLES))],
    summary="List all active critical rules",
)
def list_critical_rules(
    classification_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return current (is_latest=True) critical rules, optionally filtered by category."""
    q = db.query(CriticalRule).filter(
        CriticalRule.is_latest == True,
        CriticalRule.status == "ACTIVE",
    )
    if classification_code:
        q = q.filter(CriticalRule.classification_code == classification_code.upper())
    return q.order_by(CriticalRule.classification_code, CriticalRule.attribute).all()


@router.get(
    "/critical-rules/{rule_id}/history",
    response_model=CriticalRuleHistory,
    dependencies=[Depends(require_role(READ_ROLES))],
    summary="Full version history for a rule",
)
def critical_rule_history(rule_id: str, db: Session = Depends(get_db)):
    """Return all versions of a rule chain identified by its current id."""
    rule = db.query(CriticalRule).filter(CriticalRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    # History = all rows with same classification_code + attribute (all versions)
    history = (
        db.query(CriticalRule)
        .filter(
            CriticalRule.classification_code == rule.classification_code,
            CriticalRule.attribute == rule.attribute,
        )
        .order_by(CriticalRule.version.asc())
        .all()
    )
    return CriticalRuleHistory(
        classification_code=rule.classification_code,
        attribute=rule.attribute,
        versions=history,
    )


@router.post(
    "/critical-rules",
    response_model=CriticalRuleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(ADMIN_ONLY))],
    summary="[ADMIN] Create a new critical rule",
)
def create_critical_rule(
    payload: CriticalRuleCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(ADMIN_ONLY)),
):
    # Prevent duplicates — one active rule per (code, attribute)
    existing = db.query(CriticalRule).filter(
        CriticalRule.classification_code == payload.classification_code.upper(),
        CriticalRule.attribute == payload.attribute.lower(),
        CriticalRule.is_latest == True,
        CriticalRule.status == "ACTIVE",
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Active rule already exists for {payload.classification_code}/{payload.attribute}. Use PUT to update.",
        )

    new_rule = CriticalRule(
        id=str(uuid.uuid4()),
        classification_code=payload.classification_code.upper(),
        attribute=payload.attribute.lower(),
        severity=payload.severity,
        conflict_behavior=payload.conflict_behavior,
        notes=payload.notes,
        version=1,
        is_latest=True,
        status="ACTIVE",
        created_by=current_user.get("user_id"),
    )
    db.add(new_rule)

    _write_audit(
        db,
        entity_type="critical_rule",
        entity_id=new_rule.id,
        action="CREATE",
        old_value=None,
        new_value={
            "classification_code": new_rule.classification_code,
            "attribute": new_rule.attribute,
            "severity": new_rule.severity,
            "conflict_behavior": new_rule.conflict_behavior,
        },
        actor_id=current_user.get("user_id"),
    )

    db.commit()
    db.refresh(new_rule)
    return new_rule


@router.put(
    "/critical-rules/{rule_id}",
    response_model=CriticalRuleRead,
    dependencies=[Depends(require_role(ADMIN_ONLY))],
    summary="[ADMIN] Update a critical rule (creates new version)",
)
def update_critical_rule(
    rule_id: str,
    payload: CriticalRuleUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(ADMIN_ONLY)),
):
    old = db.query(CriticalRule).filter(
        CriticalRule.id == rule_id,
        CriticalRule.is_latest == True,
    ).first()
    if not old:
        raise HTTPException(status_code=404, detail="Active rule not found")

    old_snapshot = {
        "id": old.id,
        "severity": old.severity,
        "conflict_behavior": old.conflict_behavior,
        "version": old.version,
    }

    # Retire old version
    old.is_latest = False

    # Create new version
    new_rule = CriticalRule(
        id=str(uuid.uuid4()),
        classification_code=old.classification_code,
        attribute=old.attribute,
        severity=payload.severity or old.severity,
        conflict_behavior=payload.conflict_behavior or old.conflict_behavior,
        notes=payload.notes or old.notes,
        version=old.version + 1,
        is_latest=True,
        status="ACTIVE",
        created_by=current_user.get("user_id"),
    )
    db.add(new_rule)

    _write_audit(
        db,
        entity_type="critical_rule",
        entity_id=new_rule.id,
        action="UPDATE",
        old_value=old_snapshot,
        new_value={
            "id": new_rule.id,
            "severity": new_rule.severity,
            "conflict_behavior": new_rule.conflict_behavior,
            "version": new_rule.version,
        },
        actor_id=current_user.get("user_id"),
    )

    db.commit()
    db.refresh(new_rule)
    return new_rule


@router.delete(
    "/critical-rules/{rule_id}",
    dependencies=[Depends(require_role(ADMIN_ONLY))],
    summary="[ADMIN] Deactivate a critical rule (soft-delete)",
)
def deactivate_critical_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(ADMIN_ONLY)),
):
    rule = db.query(CriticalRule).filter(
        CriticalRule.id == rule_id,
        CriticalRule.is_latest == True,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Active rule not found")

    old_snapshot = {"severity": rule.severity, "status": rule.status}
    rule.status = "INACTIVE"

    _write_audit(
        db,
        entity_type="critical_rule",
        entity_id=rule_id,
        action="DEACTIVATE",
        old_value=old_snapshot,
        new_value={"status": "INACTIVE"},
        actor_id=current_user.get("user_id"),
    )

    db.commit()
    return {"message": f"Rule {rule_id} deactivated successfully."}


# ──────────────────────────────────────────────────────────────────────────────
# Global Matching Config
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/config",
    response_model=GlobalMatchingConfigRead,
    dependencies=[Depends(require_role(READ_ROLES))],
    summary="Get the current active global matching configuration",
)
def get_active_config(db: Session = Depends(get_db)):
    cfg = db.query(GlobalMatchingConfig).filter(GlobalMatchingConfig.is_latest == True).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="No global config found. Seed one via POST /config.")
    return cfg


@router.get(
    "/config/history",
    response_model=List[GlobalMatchingConfigRead],
    dependencies=[Depends(require_role(READ_ROLES))],
    summary="Full version history of global matching config",
)
def get_config_history(db: Session = Depends(get_db)):
    return (
        db.query(GlobalMatchingConfig)
        .order_by(GlobalMatchingConfig.version.desc())
        .all()
    )


@router.post(
    "/config",
    response_model=GlobalMatchingConfigRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(ADMIN_ONLY))],
    summary="[ADMIN] Publish a new global matching config (creates versioned record)",
)
def publish_global_config(
    payload: GlobalMatchingConfigCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(ADMIN_ONLY)),
):
    # Retire current latest
    current = db.query(GlobalMatchingConfig).filter(GlobalMatchingConfig.is_latest == True).first()
    old_snapshot: Optional[Dict[str, Any]] = None
    next_version = 1

    if current:
        old_snapshot = {
            "config_id": current.config_id,
            "version": current.version,
            "weight_semantic": current.weight_semantic,
            "weight_attribute": current.weight_attribute,
            "auto_approve_enabled": current.auto_approve_enabled,
        }
        current.is_latest = False
        next_version = current.version + 1

    new_cfg = GlobalMatchingConfig(
        config_id=str(uuid.uuid4()),
        version=next_version,
        is_latest=True,
        weight_semantic=payload.weight_semantic,
        weight_attribute=payload.weight_attribute,
        weight_manufacturer=payload.weight_manufacturer,
        weight_mpn=payload.weight_mpn,
        threshold_exact_duplicate=payload.threshold_exact_duplicate,
        threshold_near_duplicate=payload.threshold_near_duplicate,
        threshold_functionally_equivalent=payload.threshold_functionally_equivalent,
        threshold_related=payload.threshold_related,
        penalty_missing_attribute=payload.penalty_missing_attribute,
        penalty_critical_conflict=payload.penalty_critical_conflict,
        auto_approve_enabled=payload.auto_approve_enabled,
        auto_approve_threshold=payload.auto_approve_threshold,
        auto_approve_max_risk_level=payload.auto_approve_max_risk_level,
        high_risk_categories=payload.high_risk_categories,
        medium_risk_categories=payload.medium_risk_categories,
        created_by=current_user.get("user_id"),
        change_note=payload.change_note,
    )
    db.add(new_cfg)

    _write_audit(
        db,
        entity_type="global_matching_config",
        entity_id=new_cfg.config_id,
        action="PUBLISH",
        old_value=old_snapshot,
        new_value={
            "config_id": new_cfg.config_id,
            "version": new_cfg.version,
            "weight_semantic": new_cfg.weight_semantic,
            "weight_attribute": new_cfg.weight_attribute,
            "auto_approve_enabled": new_cfg.auto_approve_enabled,
            "auto_approve_max_risk_level": new_cfg.auto_approve_max_risk_level,
        },
        actor_id=current_user.get("user_id"),
    )

    db.commit()
    db.refresh(new_cfg)
    return new_cfg


# ──────────────────────────────────────────────────────────────────────────────
# Audit log read-back
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/audit",
    response_model=List[RuleAuditEntry],
    dependencies=[Depends(require_role(READ_ROLES))],
    summary="Audit trail for all rule management changes",
)
def get_rule_audit_trail(
    limit: int = 100,
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).filter(
        AuditLog.source == "rule_management_api",
    )
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    entries = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        RuleAuditEntry(
            audit_id=e.audit_id,
            action=e.action,
            old_value=e.old_value,
            new_value=e.new_value,
            actor_id=e.actor_id,
            timestamp=e.timestamp,
        )
        for e in entries
    ]
