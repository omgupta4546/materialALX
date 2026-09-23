# PostgreSQL Database Seeding

This document outlines the operational procedures for initializing the National Material Intelligence platform database. The seeding pipeline is built exclusively for PostgreSQL (enabling pgvector for AI model integration) and guarantees perfect idempotency.

## Prerequisites

1. **Docker Engine**: Required to host PostgreSQL locally with the `pgvector` extension.
2. **Python Environment**: Ensure `sqlalchemy`, `pgvector`, and `psycopg2-binary` are installed.

## PostgreSQL Setup

Spin up the local testing database container:

```bash
docker run --name material_pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d pgvector/pgvector:pg16
```

## Seed Commands

The platform exposes an idempotent CLI script designed to validate, configure, and safely ingest JSON master schemas alongside CSV datasets.

**Environment Variable:**
By default, the script connects to `postgresql://postgres:postgres@localhost:5432/postgres`. You can override this via the `--db-url` flag or environment logic.

### 1. Full Development Dataset
Ingests the entire `15,000` row synthetic material catalog, alongside all reference data.
```bash
python database/seed_database.py
```

### 2. Demo Dataset
Ingests the curated `400` row visually comprehensible demo dataset. Recommended for rapid local UI testing.
```bash
python database/seed_database.py --demo
```

### 3. Validation Mode
Pre-flights the JSON schemas and CSV dictionaries through Pydantic validators without opening a database transaction.
```bash
python database/seed_database.py --validate
```

### 4. Clear Tables
Issues a destructive purge before beginning the seed pipeline.
```bash
python database/seed_database.py --clear
```

## Idempotency & Rollback Behavior
The script leverages raw PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` commands routed through SQLAlchemy. 
- You can execute `python database/seed_database.py` 100 times sequentially. The `SourceMaterial` row count will permanently stay exactly equivalent to the CSV input row count. No uncontrolled duplicates will ever be created.
- If a CSV contains an invalid reference violation (e.g. referencing a CPSE that does not exist), the entire operation halts and issues a `session.rollback()`, ensuring the database never rests in a partially-seeded state.

## Expected Row Counts
If seeding successfully using the `--demo` flag, expect:
- **CPSEs**: 5
- **SourceMaterials**: 400
- **ProcurementRecords**: ~325

## Testing
To run the automated idempotency verification suite:
```bash
export TEST_DB_URL=postgresql://postgres:postgres@localhost:5432/postgres
pytest tests/database/test_seed.py -v
```
