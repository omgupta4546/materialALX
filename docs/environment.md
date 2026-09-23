# Environment Setup and Validation

This document outlines the environment requirements for the National Material Intelligence & Harmonization Platform and how to validate your setup.

## Required Tools

- **Node.js & npm**: Required for running and building the React frontend.
- **Python & pip**: Required for the FastAPI backend and AI pipelines.
- **Git**: Version control.
- **Docker & Docker Compose**: Required for running infrastructure components like PostgreSQL (with pgvector) and Redis locally.

## Infrastructure Dependencies

- **PostgreSQL**: The main relational database. We use the `pgvector` extension for storing and querying AI embeddings.
- **Redis**: Used for background task queues and caching.

*Note: For local development, PostgreSQL and Redis will be run via Docker containers to avoid complex local installations.*

## Project Dependencies

- **Frontend Dependencies**: Managed via `npm` in the `/frontend` directory.
- **Python Dependencies**: Managed via `pip` in the `/backend` and `/ai` directories (or in a virtual environment).

## Validation Script

We have provided a script to automatically check your environment.

### Running the Script (Windows)

Open a PowerShell terminal in the project root and run:

```powershell
.\scripts\check-environment.ps1
```

The script will report `PASS` or `FAIL` for each requirement. For any failures, it will provide a beginner-friendly instruction on how to resolve the issue.

### Interpreting the Results

- **Tool Failures (Docker, etc.)**: Follow the provided instructions to download and install the missing software.
- **Database/Redis Failures**: If the CLI tools are not installed locally, you can rely on Docker to run these services. We will configure Docker Compose to provide these later.
- **Dependency Failures**: These are expected until we formally initialize the frontend (with `package.json`) and backend (with `requirements.txt`).
