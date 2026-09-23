# National Material Intelligence & Harmonization Platform

An AI-assisted platform that harmonizes material masters across multiple CPSEs.

## Repository Structure

- `/frontend` - React/TypeScript SPA built with Vite, Tailwind, and React Router. Contains the UI for uploading data, exploring materials, and the dashboard.
- `/backend` - Python/FastAPI application. Serves the REST API, handles authentication, and orchestrates database operations.
- `/ai` - Python-based AI pipeline for material description normalization, attribute extraction, classification, and embeddings generation.
- `/database` - Database migration scripts (Alembic) and SQL schemas for PostgreSQL + pgvector.
- `/data` - Local storage for synthetic data, CSV uploads, and temporary processing files (gitignored).
- `/mock-erp` - Mock API adapters simulating legacy CPSE ERPs (e.g., mock SAP endpoints) to demonstrate integration safely.
- `/integrations` - Interfaces and adapters for third-party tools, future real ERP connectivity, and authentication providers.
- `/infrastructure` - Docker Compose files, container definitions, and configurations (Redis, object storage) for local deployment.
- `/tests` - Unit, integration, and end-to-end test suites.
- `/docs` - Master project specification, architecture decision logs, and setup checklists.
- `/scripts` - Helper shell/Python scripts for database seeding, running local environments, and utility tasks.

## Prerequisites

Please refer to [`docs/setup-checklist.md`](docs/setup-checklist.md) for detailed installation instructions. You will need:
- Node.js & npm
- Python & pip
## SIH Demonstration Workflow (Local Development)

The following command sequence is designed to run the entire platform natively on Windows without Docker.

### 1. Prerequisites
- **Node.js**: v18+ 
- **Python**: v3.11+ 
- **PostgreSQL**: With `pgvector` extension installed.
- **Redis**: Running locally (via WSL, Memurai, or native port 6379).

### 2. Clone the Repository
```bash
git clone <repository-url>
cd <repository-folder>
```

### 3. Configure Environment
Copy the `.env.example` file to `.env` and verify credentials.
```bash
cp .env.example .env
```
*(The default demo credentials for the admin are `demo_admin`/`admin123` and for the engineer `demo_engineer`/`engineer123`.)*

### 4. Install Dependencies
**Backend:**
```bash
cd backend
pip install -r requirements.txt
cd ..
```
**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 5. Run Database Migrations
Initialize the PostgreSQL database schema using Alembic.
```bash
cd backend
alembic upgrade head
cd ..
```

### 6. Seed Demo Data
Populate the database with curated, synthetic data.
```bash
python database/seed_database.py --demo
```

### 7. Start the Platform
You will need to open **three separate terminals** from the project root:

**Terminal 1 (Backend API):**
```bash
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 (ARQ Worker):**
```cmd
run_worker.bat
```

**Terminal 3 (Frontend):**
```bash
cd frontend
npm run dev
```

### 6. Interactive Demonstration
Once the data is seeded, you can open `http://localhost` in your browser. The typical flow is:
1. **Frontend Login:** Use `demo_admin` / `admin123`.
2. **Dashboard:** View high-level metrics for material harmonization and duplicate detection.
3. **Material Explorer:** Browse the synthetic source materials ingested from the simulated CPSEs.
4. **AI Matching:** Run the background job to automatically detect duplicate and semantically similar records.
5. **Approval:** Navigate to the AI matches and approve a recommendation as an Engineering Reviewer.
6. **National Material:** View the newly created, harmonized National Material.
7. **Analytics:** Explore the analytics dashboards detailing harmonized spend and procurement intelligence.

## Architecture & Data Context

### Where Data Comes From
In a production setting, raw material data is ingested from various legacy CPSE ERP systems (e.g., SAP). For local development and demonstration purposes, we rely on CSV uploads and mock adapters.

### How Mock APIs Work
The `/mock-erp` directory simulates external systems. Instead of making live HTTP calls to real SAP instances, our `MaterialSourceAdapter` interface points to mock endpoints that return hardcoded or dynamically generated synthetic JSON payloads. This ensures development is safe, fast, and offline-capable.

### Which Parts Are Synthetic
- **Material Records:** All current material data used for development is fully synthetic and does not represent real, sensitive CPSE data.
- **ERP Endpoints:** The SAP/ERP integrations are mocked.
- **User Accounts:** Demo roles and users are synthetic.

### Which Parts Are Future Integrations
- **Real SAP Connectivity:** A true `SAPAdapter` will be implemented once secure connectivity and VPN/VPC peering is established with CPSEs.
- **Production Object Storage:** Local file storage will be replaced by AWS S3 / Azure Blob Storage.
- **Advanced LLM Providers:** The pipeline currently abstracts the LLM provider, which can be swapped for enterprise-grade, localized models in the future.
