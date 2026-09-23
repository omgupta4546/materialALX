# Setup Checklist & Prerequisites

Welcome to the National Material Intelligence & Harmonization Platform! This guide will help you install all necessary tools to run this application locally.

## Current System Status
We have checked your system and found the following:

- ✅ **Node.js**: Installed (v24.13.0)
- ✅ **npm**: Installed (11.6.2)
- ✅ **Python**: Installed (3.14.2)
- ✅ **pip**: Installed (25.3)
- ✅ **Git**: Installed (2.52.0)
- ❌ **Docker**: **NOT INSTALLED**
- ❌ **Docker Compose**: **NOT INSTALLED**

## How to Install Missing Dependencies

Since Docker and Docker Compose are not installed, follow the steps below to set them up.

### Installing Docker Desktop (Includes Docker Compose)

Docker is used to run our database (PostgreSQL with pgvector) and other infrastructure components locally without polluting your host machine.

**For Windows:**
1. Visit the [Docker Desktop download page](https://www.docker.com/products/docker-desktop/).
2. Click **Download for Windows**.
3. Run the downloaded installer (`Docker Desktop Installer.exe`).
4. Ensure "Use WSL 2 instead of Hyper-V" is checked during installation (recommended for performance).
5. Follow the installation wizard prompts and restart your computer if requested.
6. Open Docker Desktop after installation to ensure the Docker Engine starts.
7. Note: Docker Desktop includes Docker Compose automatically.

**Verification:**
After installing, open a new terminal and run:
```bash
docker --version
docker compose version
```

### Other Installed Dependencies (For Reference)
If you ever need to reinstall other dependencies:
- **Node.js & npm**: Download from [nodejs.org](https://nodejs.org/).
- **Python & pip**: Download from [python.org](https://www.python.org/downloads/).
- **Git**: Download from [git-scm.com](https://git-scm.com/downloads).
