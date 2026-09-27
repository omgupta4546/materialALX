<div align="center">
  <h1>National Material Intelligence & Harmonization Platform</h1>
  <p><b>🏆 Smart India Hackathon 2024</b></p>

  <p>An AI-assisted platform that harmonizes material masters across multiple CPSEs (Central Public Sector Enterprises).</p>

  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white"/>
</div>

<br/>

## 🏆 Problem Statement Overview
Different CPSEs currently maintain their material masters independently in disparate legacy ERP systems using inconsistent terminologies and formats. This lack of standardization leads to duplicate inventories, inefficient procurement, and hinders data-driven national-level decision making.

## 💡 Our Solution
The **National Material Intelligence & Harmonization Platform** acts as a central brain that ingests raw material data, leverages **Generative AI & Semantic Embeddings (pgvector)** to detect duplicates, standardize descriptions, and create a single unified **National Material Catalog**. 

### ✨ Key Features
- **Intelligent Ingestion:** Automated data pipeline to parse diverse CSV formats from different ERPs.
- **AI-Powered Matching:** LLM-based semantic matching using `sentence-transformers` and Postgres `pgvector` to identify similar and duplicate materials.
- **Interactive Dashboard:** Modern React-based UI to view analytics, track harmonization progress, and approve AI recommendations.
- **Automated Harmonization:** Smart extraction of key technical attributes (Make, Grade, Dimensions) to generate standardized descriptions.

---

## 🛠️ Tech Stack
- **Frontend:** React, Vite, TypeScript, Tailwind CSS, Lucide React
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **AI/ML:** sentence-transformers, Generative AI APIs, pgvector
- **Database:** PostgreSQL (with pgvector extension)
- **Background Jobs:** Redis, ARQ Worker

---

## 🚀 Quick Setup Guide (Local Development)

The following sequence runs the platform locally for SIH demonstration purposes.

### 1. Prerequisites
- **Node.js**: v18+ 
- **Python**: v3.11+ 
- **PostgreSQL**: With `pgvector` extension installed.
- **Redis**: Running locally (via WSL, Memurai, or native port 6379).

### 2. Configure Environment
```bash
cp .env.example .env
```
*(Default Demo Credentials: Admin `demo_admin`/`admin123` | Engineer `demo_engineer`/`engineer123`)*

### 3. Install Dependencies
```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd ../frontend && npm install
```

### 4. Database Setup & Seeding
```bash
cd backend
alembic upgrade head
python ../database/seed_database.py --demo
```

### 5. Run the Application
Open **three separate terminals** in the project root:

**Terminal 1 (Backend API):**
```bash
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 (Background Worker):**
```cmd
run_worker.bat
```

**Terminal 3 (Frontend):**
```bash
cd frontend
npm run dev
```

---

## 💻 Workflow / Demo Flow
1. **Login:** Use `demo_admin` / `admin123`.
2. **Dashboard:** View high-level metrics for material harmonization and duplicate detection.
3. **Upload & Ingestion:** Simulate ingestion of raw materials from CPSEs.
4. **AI Matching Engine:** Background workers automatically detect duplicate and semantically similar records.
5. **Human-in-the-Loop Approval:** Engineering Reviewers navigate to AI Matches and approve/reject recommendations.
6. **Harmonized Output:** A standardized National Material Code is generated.

---

## 📁 Repository Structure
- `/frontend` - React SPA (Vite, Tailwind).
- `/backend` - FastAPI Python REST API.
- `/ai` - AI pipeline for NLP description normalization & vector embeddings.
- `/database` - Alembic migrations & DB schemas.
- `/mock-erp` - Mock API adapters simulating legacy CPSE ERPs (e.g. SAP).

<br/>
<div align="center">
  <b>Built with ❤️ for Smart India Hackathon</b>
</div>
