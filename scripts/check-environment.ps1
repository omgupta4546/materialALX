$ErrorActionPreference = "Continue"

Write-Host "========================================"
Write-Host " ENVIRONMENT VALIDATION"
Write-Host "========================================"

function Check-Tool {
    param($Name, $Exe, $Help)
    Write-Host "Checking $Name... " -NoNewline
    if (Get-Command $Exe -ErrorAction SilentlyContinue) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL" -ForegroundColor Red
        Write-Host "  -> Instruction: $Help" -ForegroundColor Yellow
    }
}

Check-Tool "Node.js" "node" "Download and install Node.js from https://nodejs.org/"
Check-Tool "npm" "npm" "npm comes with Node.js. Please install Node.js."
Check-Tool "Python" "python" "Download and install Python from https://www.python.org/downloads/"
Check-Tool "pip" "pip" "pip comes with Python. Please install Python."
Check-Tool "Git" "git" "Download and install Git from https://git-scm.com/downloads"
Check-Tool "Docker" "docker" "Download and install Docker Desktop for Windows from https://www.docker.com/products/docker-desktop/"

Write-Host "Checking Docker Compose... " -NoNewline
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    $compose = docker compose version 2>&1
    if ($LASTEXITCODE -eq 0 -or $?) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL" -ForegroundColor Red
        Write-Host "  -> Instruction: Docker Compose is missing. Please update Docker Desktop." -ForegroundColor Yellow
    }
} else {
    Write-Host "FAIL" -ForegroundColor Red
    Write-Host "  -> Instruction: Docker Compose requires Docker. Please install Docker Desktop." -ForegroundColor Yellow
}

Write-Host "Checking PostgreSQL... " -NoNewline
if (Get-Command psql -ErrorAction SilentlyContinue) {
    Write-Host "PASS" -ForegroundColor Green
} else {
    Write-Host "FAIL" -ForegroundColor Red
    Write-Host "  -> Instruction: Install PostgreSQL CLI from https://www.postgresql.org/download/ or wait to rely on Docker." -ForegroundColor Yellow
}

Write-Host "Checking Redis... " -NoNewline
if (Get-Command redis-cli -ErrorAction SilentlyContinue) {
    Write-Host "PASS" -ForegroundColor Green
} else {
    Write-Host "FAIL" -ForegroundColor Red
    Write-Host "  -> Instruction: Redis CLI not found. On Windows, Redis is best run via Docker." -ForegroundColor Yellow
}

Write-Host "Checking Frontend Dependencies... " -NoNewline
if (Test-Path "frontend/node_modules") {
    Write-Host "PASS" -ForegroundColor Green
} else {
    Write-Host "FAIL" -ForegroundColor Red
    Write-Host "  -> Instruction: Navigate to the 'frontend' directory and run 'npm install'. (Requires package.json to be created first)" -ForegroundColor Yellow
}

Write-Host "Checking Python Dependencies... " -NoNewline
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -eq 0 -or $?) {
        Write-Host "PASS" -ForegroundColor Green
    } else {
        Write-Host "FAIL" -ForegroundColor Red
        Write-Host "  -> Instruction: Navigate to 'backend' directory and run 'pip install -r requirements.txt'. (Or wait until we create it)" -ForegroundColor Yellow
    }
} else {
    Write-Host "FAIL" -ForegroundColor Red
    Write-Host "  -> Instruction: Python is not installed. Please install Python first." -ForegroundColor Yellow
}

Write-Host "========================================"
