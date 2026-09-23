@echo off
REM Start the local ARQ worker
cd backend
arq app.worker.main.WorkerSettings
