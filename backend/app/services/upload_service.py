"""
app/services/upload_service.py — Full upload pipeline for materials.

Workflow:
    1. Validate file type and size
    2. Persist FileUpload metadata
    3. Create ProcessingJob (PENDING)
    4. Parse bytes → list of raw dicts (CSV / XLSX / JSON)
    5. Validate each row (required columns, UOM, duplicate codes)
    6. Persist accepted rows as SourceMaterial (immutable — raw values preserved)
    7. Update ProcessingJob to COMPLETED / FAILED with stats

Rules:
    - Raw source values are NEVER mutated.
    - Legacy codes are lowercased for uniqueness check only — stored as-is.
    - UOM validation is permissive (warn, not reject) unless config says strict.
"""
from __future__ import annotations

import csv
import io
import json
import uuid
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import BackgroundTasks

from app.models.base import FileUpload, ProcessingJob, SourceMaterial, UOMMaster, CPSE
from app.core.connection import engine

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Columns the parser understands. All are optional except legacy_material_code.
COLUMN_MAP = {
    # CSV / XLSX header           → SourceMaterial field
    "legacy_material_code":       "legacy_material_code",
    "material_code":              "legacy_material_code",
    "mat_code":                   "legacy_material_code",
    "description":                "raw_description",
    "raw_description":            "raw_description",
    "uom":                        "raw_uom",
    "raw_uom":                    "raw_uom",
    "unit":                       "raw_uom",
    "unit_of_measure":            "raw_uom",
    "category":                   "raw_category",
    "raw_category":               "raw_category",
    "manufacturer":               "manufacturer",
    "manufacturer_part_number":   "manufacturer_part_number",
    "mpn":                        "manufacturer_part_number",
    "part_number":                "manufacturer_part_number",
    "specification":              "raw_specification",
    "raw_specification":          "raw_specification",
    "spec":                       "raw_specification",
    "plant":                      "plant",
    "source_system":              "source_system",
    "source_file":                "source_file",
    "source_record_reference":    "source_record_reference",
    "reference":                  "source_record_reference",
}

REQUIRED_FIELDS = {"legacy_material_code"}

# ─────────────────────────────────────────────────────────────────────────────
# RESULT TYPES
# ─────────────────────────────────────────────────────────────────────────────

class UploadResult:
    __slots__ = (
        "job_id", "upload_id", "total_records",
        "accepted_records", "rejected_records", "validation_errors"
    )
    def __init__(self, job_id: str, upload_id: str):
        self.job_id = job_id
        self.upload_id = upload_id
        self.total_records = 0
        self.accepted_records = 0
        self.rejected_records = 0
        self.validation_errors: list[dict] = []


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────

def _parse_csv(content: bytes) -> list[dict[str, Any]]:
    try:
        decoded = content.decode("utf-8-sig")  # strips BOM if present
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(decoded))
    return [dict(row) for row in reader]


def _parse_xlsx(content: bytes) -> list[dict[str, Any]]:
    try:
        import openpyxl
    except ImportError:
        raise ValueError("openpyxl is required to process XLSX files. Install it with: pip install openpyxl")
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    result = []
    for row in rows[1:]:
        result.append({headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)})
    return result


def _parse_json(content: bytes) -> list[dict[str, Any]]:
    try:
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e}")
    if isinstance(data, dict):
        # Wrap single object
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON payload must be an array of objects or a single object.")
    return data


def _parse_file(content: bytes, filename: str) -> list[dict[str, Any]]:
    ext = (filename.rsplit(".", 1)[-1]).lower()
    if ext == "csv":
        return _parse_csv(content)
    elif ext in ("xlsx", "xls"):
        return _parse_xlsx(content)
    elif ext == "json":
        return _parse_json(content)
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Accepted types: CSV, XLSX, JSON")


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_header(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _map_row(raw_row: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """
    Map a raw CSV/XLSX/JSON row to SourceMaterial field dict.
    Returns (mapped_dict, error_message) — error is None on success.
    """
    mapped: dict[str, Any] = {}
    for raw_key, raw_val in raw_row.items():
        normalised_key = _normalise_header(str(raw_key))
        field = COLUMN_MAP.get(normalised_key)
        if field:
            # Prefer first occurrence (most specific column wins)
            if field not in mapped:
                mapped[field] = str(raw_val).strip() if raw_val is not None else ""

    # Check required fields
    missing = REQUIRED_FIELDS - set(mapped.keys())
    if missing or not mapped.get("legacy_material_code"):
        return None, f"Missing required column(s): {', '.join(missing or ['legacy_material_code'])}"

    return mapped, None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class UploadService:

    def __init__(self, db: Session):
        self.db = db

    # ── Step 1: validate file-level concerns ──────────────────────────────────

    def _preflight(self, content: bytes, filename: str, cpse_id: str) -> None:
        byte_size = len(content)
        if byte_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB "
                f"(received {byte_size // (1024*1024)} MB)."
            )
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ("csv", "xlsx", "xls", "json"):
            raise ValueError(
                f"Unsupported file type '.{ext}'. Accepted: CSV, XLSX, JSON."
            )
        # Validate CPSE exists
        cpse = self.db.query(CPSE).filter(CPSE.cpse_id == cpse_id).first()
        if not cpse:
            raise ValueError(f"CPSE '{cpse_id}' not found.")

    # ── Step 2: persist file upload record ───────────────────────────────────

    def _create_file_record(
        self, filename: str, file_size: int, cpse_id: str, job_id: str
    ) -> FileUpload:
        record = FileUpload(
            id=str(uuid.uuid4()),
            cpse_code=None,   # not stored by code here; cpse_id used instead
            filename=filename,
            file_size=file_size,
            job_id=job_id,
            status="UPLOADED",
        )
        self.db.add(record)
        return record

    # ── Step 3: create processing job ────────────────────────────────────────

    def _create_job(self, job_id: str, filename: str) -> ProcessingJob:
        job = ProcessingJob(
            job_id=job_id,
            job_type="UPLOAD_PROCESSING",
            status="PENDING",
            records_processed=0,
            total_records=0,
            details={"filename": filename},
        )
        self.db.add(job)
        self.db.flush()
        return job

    # ── Step 4–6: parse, validate, persist ───────────────────────────────────

    def _load_known_uoms(self) -> set[str]:
        rows = self.db.query(UOMMaster.canonical_code).all()
        codes = {r.canonical_code.upper() for r in rows}
        # Also pull all aliases
        alias_rows = self.db.query(UOMMaster.aliases).all()
        for r in alias_rows:
            if r.aliases:
                codes.update(a.upper() for a in r.aliases)
        return codes

    def _load_existing_legacy_codes(self, cpse_id: str) -> set[str]:
        """Load existing (cpse_id, legacy_code) pairs as lowercase for dedup."""
        rows = self.db.query(SourceMaterial.legacy_material_code).filter(
            SourceMaterial.cpse_id == cpse_id
        ).all()
        return {r.legacy_material_code.lower() for r in rows}

    def _process_rows(
        self,
        raw_rows: list[dict],
        cpse_id: str,
        source_file: str,
        job: ProcessingJob,
        result: UploadResult,
    ) -> None:
        known_uoms = self._load_known_uoms()
        existing_codes = self._load_existing_legacy_codes(cpse_id)
        seen_codes: set[str] = set()   # within-batch dedup

        result.total_records = len(raw_rows)
        job.total_records = len(raw_rows)
        self.db.flush()

        for row_idx, raw_row in enumerate(raw_rows, start=1):
            mapped, err = _map_row(raw_row)

            if err:
                result.rejected_records += 1
                result.validation_errors.append({
                    "row": row_idx,
                    "error": err,
                    "data": {k: str(v)[:80] for k, v in raw_row.items()},
                })
                continue

            legacy_code = mapped["legacy_material_code"]
            legacy_code_lower = legacy_code.lower()

            # ── Duplicate check (within this batch first) ───────────────────
            if legacy_code_lower in seen_codes:
                result.rejected_records += 1
                result.validation_errors.append({
                    "row": row_idx,
                    "error": f"Duplicate legacy_material_code '{legacy_code}' appears more than once in this file.",
                    "data": {"legacy_material_code": legacy_code},
                })
                continue

            # ── Duplicate check (DB) ─────────────────────────────────────────
            if legacy_code_lower in existing_codes:
                result.rejected_records += 1
                result.validation_errors.append({
                    "row": row_idx,
                    "error": f"Duplicate legacy_material_code '{legacy_code}' already exists for this CPSE.",
                    "data": {"legacy_material_code": legacy_code},
                })
                continue

            # ── UOM validation (warn, not reject) ────────────────────────────
            raw_uom = mapped.get("raw_uom", "")
            uom_warning = None
            if raw_uom and known_uoms and raw_uom.upper() not in known_uoms:
                uom_warning = f"UOM '{raw_uom}' not in canonical UOM master — stored as-is."

            # ── Persist — raw values are NEVER mutated ───────────────────────
            sm = SourceMaterial(
                source_material_id=str(uuid.uuid4()),
                cpse_id=cpse_id,
                legacy_material_code=legacy_code,                       # original casing
                raw_description=mapped.get("raw_description") or None,
                raw_uom=mapped.get("raw_uom") or None,                  # original raw value
                raw_category=mapped.get("raw_category") or None,
                manufacturer=mapped.get("manufacturer") or None,
                manufacturer_part_number=mapped.get("manufacturer_part_number") or None,
                raw_specification=mapped.get("raw_specification") or None,
                plant=mapped.get("plant") or None,
                source_system=mapped.get("source_system") or None,
                source_file=source_file,
                source_record_reference=mapped.get("source_record_reference") or None,
            )
            try:
                self.db.add(sm)
                self.db.flush()  # catch DB-level constraint violations per row
            except IntegrityError as ie:
                self.db.rollback()
                result.rejected_records += 1
                result.validation_errors.append({
                    "row": row_idx,
                    "error": f"Database constraint violation: {str(ie.orig)}",
                    "data": {"legacy_material_code": legacy_code},
                })
                # Reload session state after rollback
                existing_codes = self._load_existing_legacy_codes(cpse_id)
                continue

            seen_codes.add(legacy_code_lower)
            existing_codes.add(legacy_code_lower)
            result.accepted_records += 1

            if uom_warning:
                result.validation_errors.append({
                    "row": row_idx,
                    "severity": "WARNING",
                    "error": uom_warning,
                    "data": {"legacy_material_code": legacy_code, "raw_uom": raw_uom},
                })

            if row_idx % 100 == 0:
                job.records_processed = result.accepted_records
                self.db.flush()

    # ── Public entry point ────────────────────────────────────────────────────

    def process_upload(self, content: bytes, filename: str, cpse_id: str) -> UploadResult:
        self._preflight(content, filename, cpse_id)

        job_id = str(uuid.uuid4())
        result = UploadResult(job_id=job_id, upload_id="")

        file_record = self._create_file_record(filename, len(content), cpse_id, job_id)
        result.upload_id = file_record.id

        job = self._create_job(job_id, filename)
        self.db.flush()

        raw_rows = _parse_file(content, filename)
        self._process_rows(raw_rows, cpse_id, filename, job, result)
        job.records_processed = result.accepted_records
        job.total_records = result.total_records
        job.status = "COMPLETED" if result.accepted_records or result.rejected_records == 0 else "FAILED"
        self.db.flush()
        self.db.commit()
        return result

    async def process_upload_async(
        self, content: bytes, filename: str, cpse_id: str, redis_pool
    ) -> UploadResult:
        # Step 1: preflight checks
        self._preflight(content, filename, cpse_id)

        job_id = str(uuid.uuid4())
        result = UploadResult(job_id=job_id, upload_id="")

        # Step 2: file record
        file_record = self._create_file_record(filename, len(content), cpse_id, job_id)
        result.upload_id = file_record.id

        # Step 3: job
        job = self._create_job(job_id, filename)
        self.db.flush()

        # Queue the background processing task in Redis using arq
        if redis_pool:
            await redis_pool.enqueue_job(
                "process_upload_job",
                content, filename, cpse_id, job_id, result.upload_id
            )
        else:
            log.warning("Redis pool not found. Job will not be processed.")

        return result

