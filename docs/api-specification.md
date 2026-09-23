# National Material Intelligence API Contract (v1)

This document defines the strict, canonical API contract for the frontend and backend teams. All endpoints are hosted under the `/api/v1` prefix.

## 1. Global Conventions
- **Request/Response Format**: `application/json`
- **Naming**: `snake_case` for all JSON payloads.
- **Timestamps**: ISO-8601 strings in UTC (e.g., `2026-09-08T12:00:00Z`).
- **Authorization**: Bearer Token in `Authorization` header (`Bearer <JWT>`).

### 1.1 Pagination & Response Envelope
All collections return a standardized envelope.
```json
{
  "data": [ ... ],
  "meta": {
    "total_count": 1500,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### 1.2 Errors
All errors follow RFC 7807 problem details or FastAPI validation standards.
```json
{
  "detail": [
    {
      "loc": ["body", "material_code"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 2. Endpoints by Domain

### 2.1 AUTH
#### `POST /auth/login`
- **Purpose**: Authenticate user and issue JWT.
- **Auth**: None
- **Request**: `{ "username": "admin", "password": "password123" }`
- **Response**: `{ "access_token": "ey...", "token_type": "bearer", "user": { "user_id": "U1", "role": "admin", "cpse_code": null } }`

#### `GET /auth/me`
- **Purpose**: Retrieve current user session.
- **Auth**: Required (Any)
- **Response**: `{ "user_id": "U1", "name": "Admin", "role": "admin", "permissions": ["*"] }`

### 2.2 CPSE
#### `GET /cpses`
- **Purpose**: List all registered organizations.
- **Auth**: Required (Any)
- **Response**: List of `{ "cpse_code": "AHM", "cpse_name": "AHM Steel", "sector": "Manufacturing" }`

### 2.3 MATERIALS (Source Materials)
#### `GET /materials`
- **Purpose**: Paginated list of source materials.
- **Auth**: Required (Any - Filtered by User's CPSE unless Admin)
- **Parameters**: `?cpse_code=AHM&limit=50&offset=0&search=valve`
- **Response**: Envelope containing `SourceMaterial` objects.

#### `GET /materials/{source_id}`
- **Purpose**: Retrieve single source material.
- **Auth**: Required
- **Response**: `{ "source_id": "uuid", "material_code": "MAT1", "description": "...", "attributes": {} }`

### 2.4 UPLOAD
#### `POST /uploads`
- **Purpose**: Upload a CSV file of source materials for ingestion.
- **Auth**: Required (Data Steward / Admin)
- **Request**: `multipart/form-data` with `file` and `cpse_code`.
- **Response**: `{ "upload_id": "uuid", "status": "PENDING" }`

### 2.5 JOBS
#### `GET /jobs/{job_id}`
- **Purpose**: Check status of async background tasks (upload processing, AI matching).
- **Auth**: Required
- **Response**: `{ "job_id": "uuid", "status": "COMPLETED", "records_processed": 1500, "errors": [] }`

### 2.6 AI PROCESSING
#### `POST /ai/normalize`
- **Purpose**: Synchronously normalize a raw text string (for testing/UI preview).
- **Auth**: Required
- **Request**: `{ "raw_text": "GATE VALVE 6IN CL300" }`
- **Response**: `{ "normalized_text": "GATE VALVE 6 INCH CLASS 300", "extracted_attributes": {"type": "GATE VALVE", "size": "6IN"} }`

#### `POST /ai/batch-process`
- **Purpose**: Trigger background normalization and embedding for a CPSE's catalog.
- **Auth**: Required (Admin)
- **Request**: `{ "cpse_code": "AHM" }`
- **Response**: `{ "job_id": "uuid" }`

### 2.7 MATCHES
#### `POST /matches/search`
- **Purpose**: Find semantic nearest neighbors for a given material.
- **Auth**: Required
- **Request**: `{ "source_id": "uuid", "threshold": 0.85, "limit": 10 }`
- **Response**: List of `{ "national_code": "NAT1", "score": 0.98, "match_category": "EXACT", "conflicts": [] }`

### 2.8 APPROVALS
#### `POST /approvals/{target_id}/approve`
- **Purpose**: Approve a pending mapping or National Material minting.
- **Auth**: Required (Engineer / Admin)
- **Request**: `{ "notes": "Looks good" }`
- **Response**: `{ "status": "APPROVED", "timestamp": "..." }`

### 2.9 NATIONAL MATERIALS
#### `GET /national-materials`
- **Purpose**: Search the golden record catalog.
- **Auth**: Required
- **Response**: Envelope containing `NationalMaterial` objects.

#### `POST /national-materials`
- **Purpose**: Manually mint a new National Material code.
- **Auth**: Required (Admin / Engineer)
- **Request**: `{ "primary_description": "...", "category_code": "CAT1", "attributes": {} }`
- **Response**: `{ "national_code": "NAT-1001", "status": "DRAFT" }`

### 2.10 MAPPINGS
#### `POST /mappings`
- **Purpose**: Map a source material to a national material.
- **Auth**: Required (Data Steward)
- **Request**: `{ "source_id": "uuid", "national_code": "NAT1", "mapping_type": "EXACT" }`
- **Response**: `{ "id": 1, "status": "PENDING_APPROVAL" }`

### 2.11 CLASSIFICATION
#### `GET /classifications`
- **Purpose**: Retrieve the nested taxonomy tree.
- **Auth**: Required
- **Response**: Nested tree of `{ "code": "CAT1", "name": "Valves", "children": [...] }`

### 2.12 UOM
#### `GET /uom`
- **Purpose**: Retrieve unit of measure master data.
- **Auth**: Required
- **Response**: List of `{ "canonical_code": "EA", "dimension": "Count" }`

### 2.13 RULES
#### `GET /rules`
- **Purpose**: Retrieve critical engineering rules.
- **Auth**: Required
- **Response**: List of `{ "category": "CAT-MOTOR", "attribute": "voltage", "severity": "CRITICAL" }`

### 2.14 DATA QUALITY
#### `GET /data-quality/report`
- **Purpose**: Retrieve data quality metrics for a CPSE.
- **Auth**: Required
- **Parameters**: `?cpse_code=AHM`
- **Response**: `{ "missing_mandatory": 150, "invalid_uom": 23, "overall_score": 85.5 }`

### 2.15 ANALYTICS
#### `GET /analytics/dashboard`
- **Purpose**: Retrieve high-level charting metrics.
- **Auth**: Required
- **Response**: `{ "total_materials": 15000, "mapped_materials": 12000, "pending_approvals": 45 }`

### 2.16 PROCUREMENT OPPORTUNITIES
#### `GET /procurement/opportunities`
- **Purpose**: Identify bulk purchasing overlaps across CPSEs mapped to the same National Code.
- **Auth**: Required
- **Response**: List of `{ "national_code": "NAT1", "total_spend": 150000.00, "participating_cpses": ["AHM", "NEC"] }`

### 2.17 AUDIT
#### `GET /audit`
- **Purpose**: Retrieve system audit logs.
- **Auth**: Required (Auditor / Admin)
- **Response**: Envelope of `{ "action": "CREATE_MAPPING", "user_id": "U1", "timestamp": "..." }`

### 2.18 ADMIN
#### `POST /admin/clear-cache`
- **Purpose**: Invalidate Redis/Application caches.
- **Auth**: Required (Admin)
- **Response**: `{ "status": "cleared" }`

### 2.19 EXPORT
#### `GET /exports/{cpse_code}`
- **Purpose**: Download mapped catalog for ERP ingestion.
- **Auth**: Required
- **Response**: Streamed CSV/JSON file download.

### 2.20 NOTIFICATIONS
#### `GET /notifications`
- **Purpose**: Retrieve user notifications.
- **Auth**: Required
- **Response**: Envelope of `{ "id": "uuid", "message": "...", "is_read": false }`

#### `POST /notifications/{id}/read`
- **Purpose**: Mark a notification as read.
- **Auth**: Required

### 2.21 MIGRATION
#### `POST /migration/sync`
- **Purpose**: Push approved mappings to the Mock ERP webhook.
- **Auth**: Required (Admin)
- **Request**: `{ "cpse_code": "AHM" }`
- **Response**: `{ "status": "SYNCING", "job_id": "uuid" }`

### 2.22 HEALTH
#### `GET /health`
- **Purpose**: Liveness and readiness probe.
- **Auth**: None
- **Response**: `{ "status": "ok", "db": "connected", "ai": "ready" }`
