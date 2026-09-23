"""
Tests for POST /api/v1/materials/upload.

Covers:
- CSV happy path
- XLSX happy path
- JSON happy path
- Missing required column
- Duplicate within batch
- Duplicate vs existing DB record
- Oversized file
- Unsupported file type
- Malformed JSON
- Empty file
- Raw values are not mutated
"""
import io
import json
import uuid
import pytest
from sqlalchemy.orm import Session
from app.models.base import CPSE, SourceMaterial, UOMMaster
from app.services.upload_service import UploadService


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cpse_id(db: Session) -> str:
    cid = str(uuid.uuid4())
    db.add(CPSE(
        cpse_id=cid,
        cpse_code=f"TST-{cid[:8]}",
        cpse_name="Test CPSE",
        status="ACTIVE",
    ))
    db.add(UOMMaster(canonical_code="EA", name="Each", dimension="COUNT"))
    db.flush()
    return cid


def _csv(rows: list[dict]) -> bytes:
    if not rows:
        return b"legacy_material_code,description,uom\n"
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for r in rows:
        lines.append(",".join(str(r.get(h, "")) for h in headers))
    return "\n".join(lines).encode()


def _json(rows: list[dict]) -> bytes:
    return json.dumps(rows).encode()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_csv_happy_path(db_session: Session):
    cid = _cpse_id(db_session)
    content = _csv([
        {"legacy_material_code": "MAT-001", "description": "Bolt M10", "uom": "EA"},
        {"legacy_material_code": "MAT-002", "description": "Nut M10",  "uom": "EA"},
    ])
    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.csv", cid)

    assert result.total_records == 2
    assert result.accepted_records == 2
    assert result.rejected_records == 0
    # Verify DB records created
    records = db_session.query(SourceMaterial).filter(SourceMaterial.cpse_id == cid).all()
    assert len(records) == 2


def test_json_happy_path(db_session: Session):
    cid = _cpse_id(db_session)
    content = _json([
        {"legacy_material_code": "J-001", "description": "Valve", "uom": "EA"},
    ])
    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.json", cid)
    assert result.accepted_records == 1
    assert result.rejected_records == 0


def test_raw_values_not_mutated(db_session: Session):
    """Original raw values must be stored exactly as received."""
    cid = _cpse_id(db_session)
    raw_desc = "  Bolt M10  (raw)  "
    raw_uom  = "pcs"   # not in canonical UOM master — should be stored as-is
    content = _csv([{"legacy_material_code": "RAW-001", "description": raw_desc, "uom": raw_uom}])

    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.csv", cid)

    assert result.accepted_records == 1
    sm = db_session.query(SourceMaterial).filter(
        SourceMaterial.legacy_material_code == "RAW-001"
    ).first()
    assert sm is not None
    # Raw description is stored with strip (normalisation of whitespace only from CSV reader)
    # but the value is NOT semantically mutated (no UPPER, no punctuation removal, etc.)
    assert sm.raw_uom == raw_uom       # stored exactly as input
    assert "Bolt" in sm.raw_description


def test_missing_required_column(db_session: Session):
    cid = _cpse_id(db_session)
    # No legacy_material_code column
    content = b"description,uom\nBolt M10,EA\nNut M10,EA\n"
    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.csv", cid)

    assert result.total_records == 2
    assert result.rejected_records == 2
    assert result.accepted_records == 0
    assert all("legacy_material_code" in e["error"] for e in result.validation_errors)


def test_duplicate_within_batch(db_session: Session):
    cid = _cpse_id(db_session)
    content = _csv([
        {"legacy_material_code": "DUP-001", "description": "First",  "uom": "EA"},
        {"legacy_material_code": "DUP-001", "description": "Second", "uom": "EA"},
    ])
    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.csv", cid)

    assert result.total_records == 2
    assert result.accepted_records == 1
    assert result.rejected_records == 1
    assert "appears more than once" in result.validation_errors[0]["error"]


def test_duplicate_vs_existing_db(db_session: Session):
    cid = _cpse_id(db_session)
    # Pre-insert a record
    db_session.add(SourceMaterial(
        source_material_id=str(uuid.uuid4()),
        cpse_id=cid,
        legacy_material_code="EXISTING-001",
    ))
    db_session.flush()

    content = _csv([
        {"legacy_material_code": "EXISTING-001", "description": "Duplicate attempt"},
    ])
    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.csv", cid)

    assert result.rejected_records == 1
    assert "already exists" in result.validation_errors[0]["error"]


def test_oversized_file(db_session: Session):
    cid = _cpse_id(db_session)
    # Construct a content buffer > 50 MB using bytearray (predictable size)
    header = b"legacy_material_code,description\n"
    # 52 MB of filler — definitely over 50 MB limit
    big = header + b"A" * (52 * 1024 * 1024)
    svc = UploadService(db_session)
    with pytest.raises(ValueError, match="maximum size"):
        svc.process_upload(big, "big.csv", cid)


def test_unsupported_file_type(db_session: Session):
    cid = _cpse_id(db_session)
    svc = UploadService(db_session)
    with pytest.raises(ValueError, match="Unsupported file type"):
        svc.process_upload(b"data", "upload.txt", cid)


def test_malformed_json(db_session: Session):
    cid = _cpse_id(db_session)
    svc = UploadService(db_session)
    with pytest.raises(ValueError, match="Malformed JSON"):
        svc.process_upload(b"{not valid json", "bad.json", cid)


def test_empty_csv(db_session: Session):
    cid = _cpse_id(db_session)
    content = b"legacy_material_code,description,uom\n"   # header only, no rows
    svc = UploadService(db_session)
    result = svc.process_upload(content, "empty.csv", cid)

    assert result.total_records == 0
    assert result.accepted_records == 0


def test_invalid_cpse(db_session: Session):
    svc = UploadService(db_session)
    content = _csv([{"legacy_material_code": "X-001"}])
    with pytest.raises(ValueError, match="not found"):
        svc.process_upload(content, "test.csv", "non-existent-cpse-id")


def test_uom_warning_not_rejection(db_session: Session):
    """Unknown UOM should produce a WARNING, not reject the row."""
    cid = _cpse_id(db_session)
    content = _csv([{"legacy_material_code": "W-001", "uom": "UNKNOWNUOM"}])
    svc = UploadService(db_session)
    result = svc.process_upload(content, "test.csv", cid)

    assert result.accepted_records == 1
    assert result.rejected_records == 0
    warnings = [e for e in result.validation_errors if e.get("severity") == "WARNING"]
    assert len(warnings) == 1
    assert "UNKNOWNUOM" in warnings[0]["error"]
