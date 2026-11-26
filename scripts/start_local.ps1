# Start Chanakya Research Commons locally (Backend FastAPI + Frontend Vite)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$PyExe = Join-Path $Root ".venv\Scripts\python.exe"
$NodeDir = Join-Path $Root ".tools\node"
if (Test-Path $NodeDir) {
    $env:PATH = "$NodeDir;$env:PATH"
}

Write-Host "Starting Chanakya Research Commons Backend API on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath $PyExe -ArgumentList "-m","uvicorn","backend.app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $Root

Write-Host "Starting Chanakya Research Commons Frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory (Join-Path $Root "frontend")

Write-Host ""
Write-Host "Platform running!" -ForegroundColor Yellow
Write-Host "  Frontend : http://localhost:5173"
Write-Host "  API Docs : http://localhost:8000/docs"
Write-Host "  Demo Admin   : admin@chanakya.edu.in / Chanakya@2026"
Write-Host "  Demo Faculty : faculty@chanakya.edu.in / Chanakya@2026"
Write-Host "  Demo Student : student@chanakya.edu.in / Chanakya@2026"
