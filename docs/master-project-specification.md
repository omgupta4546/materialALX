# National Material Intelligence & Harmonization Platform
## Master Project Specification

This document is the single source of truth for every future implementation step of the National Material Intelligence & Harmonization Platform.

### Project Objective
Build an AI-assisted platform that harmonizes material masters across multiple CPSEs by:
- preserving source data
- normalizing material descriptions
- normalizing UOM
- extracting technical attributes
- classifying materials
- generating embeddings
- retrieving candidates
- detecting duplicates
- detecting near duplicates
- detecting functional equivalence
- detecting technical conflicts
- generating explainable recommendations
- creating canonical National Material Codes
- mapping legacy CPSE material codes
- supporting migration
- supporting human approval
- providing procurement intelligence
- maintaining audit/provenance
- supporting ERP/SAP integration
- enforcing security and CPSE data isolation

### Architecture Contracts

#### 1. Tech Stack

**Frontend:**
- React
- TypeScript
- Vite
- Tailwind
- React Router
- TanStack Query
- React Hook Form
- Zod
- Recharts

**Backend:**
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

**Database:**
- PostgreSQL
- pgvector

**Infrastructure:**
- Docker
- Redis
- Background Worker
- Object Storage abstraction

**AI:**
- Python
- Embedding Model
- LLM Provider abstraction
- Normalization
- Attribute Extraction
- Classification
- Candidate Retrieval
- Hybrid Matching
- Rules
- Risk
- Explainability

#### 2. Frontend Screens

- **Screen 1:** Login / Organization Selection
- **Screen 2:** Material Data Upload
- **Screen 3:** Material Explorer
- **Screen 4:** AI Match Review
- **Screen 5:** National Material Master
- **Screen 6:** Dashboard
  - **Dashboard charts:**
    - Materials by CPSE
    - Upload Categories
    - Confidence Distribution
    - Pending Approvals
    - Top Redundant Material Groups
    - Procurement Opportunities
    - Classification Coverage
    - Data Quality
    - Risk Distribution
    - Processing Health

#### 3. Database

**Core:**
- `cpse`
- `source_material`
- `normalized_material`
- `national_material`
- `material_mapping`
- `material_attribute`
- `classification`
- `match_result`
- `approval`
- `audit_log`

**Supporting:**
- `user`
- `role`
- `processing_job`
- `procurement_record`
- `file_upload`
- `notification`
- `uom_master`
- `attribute_definition`
- `matching_rule`
- `feedback_event`
- `model_registry`

#### 4. AI Pipeline

1. `raw material`
2. `→ normalization`
3. `→ UOM normalization`
4. `→ attribute extraction`
5. `→ classification`
6. `→ embedding`
7. `→ candidate retrieval`
8. `→ hybrid matching`
9. `→ critical attribute rules`
10. `→ risk engine`
11. `→ confidence calibration`
12. `→ explanation`
13. `→ human approval`

#### 5. Match Types

- `EXACT_DUPLICATE`
- `NEAR_DUPLICATE`
- `FUNCTIONALLY_EQUIVALENT`
- `RELATED`
- `NOT_EQUIVALENT`
- `REQUIRES_ENGINEERING_REVIEW`

#### 6. National Material Code

- The LLM must **never** generate authoritative IDs.
- Backend/database owns ID generation.
- **Code example:** `NMC-BRG-000182`
- **Requirements:** Must be unique, stable, source-code independent, and transaction safe.

#### 7. Data Rules

- Source material is immutable.
- Normalized material is separate.
- AI recommendation is never overwritten by human decision.
- Human approval is an independent event.
- Every material-master mutation is auditable.

#### 8. ERP Integration

- **Use:** `MaterialSourceAdapter`
- **Implement:** `CSVAdapter`, `MockERPAdapter`
- **Prepare:** `SAPAdapter` interface
- **Constraint:** Never claim live SAP connectivity.

#### 9. Security

- JWT prototype
- RBAC (Role-Based Access Control)
- CPSE data isolation
- Backend authorization
- Secrets outside source code

#### 10. Data

- Use synthetic data for development/demo.
- Never claim synthetic data is real CPSE data.

#### 11. Development Rule

Every future implementation prompt must:
- respect this master specification
- inspect existing implementation
- preserve working code
- avoid duplicate functionality
- follow established naming conventions
- update tests
- update documentation
- maintain API contracts
