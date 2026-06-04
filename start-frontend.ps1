# Starts the AgenticTrader web dashboard (Vite dev server).
Set-Location $PSScriptRoot\frontend
if (-not (Test-Path .\node_modules)) {
    Write-Host "Installing frontend deps..." -ForegroundColor Cyan
    npm install
}
npm run dev
