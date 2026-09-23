# Start the local ARQ worker
Set-Location -Path "backend"
arq app.worker.main.WorkerSettings
