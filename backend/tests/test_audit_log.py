import pytest
from sqlalchemy.orm import Session
from app.models.base import AuditLog
from app.repositories.base import AuditLogRepo
import uuid

def test_audit_log_creation_and_json(db_session: Session):
    repo = AuditLogRepo(db_session)
    entity_id = str(uuid.uuid4())
    actor_id = "user-123"
    log = repo.log(
        action="UPDATE",
        entity_id=entity_id,
        entity_type="MATERIAL",
        old_value={"status": "DRAFT", "score": 10},
        new_value={"status": "ACTIVE", "score": 20},
        actor_id=actor_id,
        source="API",
        request_id="req-abc"
    )
    db_session.flush()
    assert log.audit_id is not None
    assert log.action == "UPDATE"
    assert log.entity_id == entity_id
    assert log.old_value["status"] == "DRAFT"
    assert log.new_value["score"] == 20
    assert log.source == "API"
    assert log.request_id == "req-abc"
    fetched = db_session.query(AuditLog).filter(AuditLog.audit_id == log.audit_id).first()
    assert fetched is not None
    assert fetched.old_value["score"] == 10
    assert fetched.new_value["status"] == "ACTIVE"
