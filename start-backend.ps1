# Starts the AgenticTrader backend (FastAPI + autonomous scheduler).
Set-Location $PSScriptRoot\backend
if (-not (Test-Path .\.venv)) {
    Write-Host "Creating venv and installing deps..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
if (-not (Test-Path .\.env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
