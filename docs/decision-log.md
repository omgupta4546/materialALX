# Architectural Decision Log

This document records significant architectural decisions for the National Material Intelligence & Harmonization Platform.

## 1. Tech Stack Selection
**Date:** 2026-09-08
**Decision:** Standardize on React/TypeScript/Vite for frontend, Python/FastAPI for backend, and PostgreSQL/pgvector for database.
**Rationale:** Provides a robust, type-safe ecosystem with native support for vector search (pgvector) essential for AI match retrieval and embeddings.

## 2. ID Generation Strategy
**Date:** 2026-09-08
**Decision:** Backend/Database owns National Material Code generation. LLMs must never generate authoritative IDs.
**Rationale:** Ensures IDs are transaction-safe, unique, stable, and independent of probabilistic models.

## 3. Data Immutability
**Date:** 2026-09-08
**Decision:** Source material is immutable. Normalized material is stored separately.
**Rationale:** Preserves auditability and provenance. Allows re-processing of raw data without data loss or corruption.

## 4. Separation of AI and Human Decisions
**Date:** 2026-09-08
**Decision:** AI recommendations are never overwritten by human decisions. Human approval is recorded as an independent event.
**Rationale:** Maintains clear provenance of why a decision was made and prevents corruption of AI confidence metrics and historical explanations.

## 5. ERP Connectivity Scope
**Date:** 2026-09-08
**Decision:** Implement CSVAdapter and MockERPAdapter. Prepare SAPAdapter interface but never claim live SAP connectivity.
**Rationale:** Allows full end-to-end development and demonstration using synthetic data without requiring complex, sensitive real-world ERP integration during the initial build phase.

## 6. Security and Isolation
**Date:** 2026-09-08
**Decision:** Enforce CPSE data isolation, RBAC, and backend authorization.
**Rationale:** Ensures that cross-tenant data bleed is impossible and maintains trust when integrating data from multiple independent CPSEs.
