# Privacy & Data Governance Policy

## 1. Multi-Tenant Data Isolation
The platform implements strict multi-tenant architecture at the application level to ensure CPSEs can only access their own authorized data.
- **Data Boundary**: All `SourceMaterial` and `ProcurementRecord` entries are strictly partitioned by `cpse_code`.
- **Enforcement**: Access control is enforced at the API routing layer. Endpoints inject the authenticated user's CPSE context into the SQL queries, guaranteeing that horizontal data leakage between CPSEs cannot occur.

## 2. Data Ownership and Sharing
- **Source Data Ownership**: CPSEs retain full ownership and intellectual property rights over their original uploaded data, legacy codes, and procurement histories.
- **Platform Ownership**: The central platform owns the derived Canonical (National) Material Catalog and the anonymized machine learning models trained on the aggregate data.
- **Sharing Policy**: Raw source descriptions, historical spend, and supplier pricing details of one CPSE are **strictly confidential** and cannot be viewed by other CPSEs. CPSEs only see the deduplicated National Material record and their own linked legacy codes.

## 3. Minimum Data Exposure
- API responses are scoped to the minimum required fields.
- Procurement intelligence and duplicate analysis metrics only aggregate the user's authorized CPSE data unless explicitly running a national-level aggregation (restricted to `DATA_STEWARD` and `ADMIN` roles).

## 4. Retention & Deletion Policy
- **Immutability Principle**: Historical legacy identifiers and approved material mappings are never deleted to ensure compliance and traceability.
- **Soft Deletes**: Deletions are processed as "soft deletes" or status deprecations (e.g., `status = DEPRECATED`) to maintain referential integrity.
- **Audit Logs**: All modifications by administrators or stewards are logged with timestamps and actor IDs indefinitely.

## 5. Anonymization & Synthetic Data (Demo Policy)
- **PII Protection**: Raw data containing Personal Identifiable Information (PII) is structurally excluded from the ingestion pipeline.
- **Pricing Data**: Procurement pricing details must be obfuscated or pseudonymized when used to train internal ML models unless explicit governance consent is granted.
- **Synthetic Data**: For hackathon, testing, or demonstration purposes, all underlying material descriptions and historical spend values are generated synthetically. **No actual live SAP integration or real procurement data is exposed.**
