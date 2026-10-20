# ======================================================================
#   APPOINTMENT SLOT BOOKER - POWERSHELL LAUNCHER
# ======================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "         APPOINTMENT SLOT BOOKER - APPLICATION LAUNCHER               " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$backendDir = Join-Path $PSScriptRoot "backend"
Set-Location $backendDir

Write-Host "`n[Step 1/3] Checking Python..." -ForegroundColor Yellow
try {
    python --version
} catch {
    Write-Host "[ERROR] Python is not installed or not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Pause
    Exit
}

Write-Host "`n[Step 2/3] Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "`n[Step 3/3] Starting server and opening browser..." -ForegroundColor Green
Start-Process "http://127.0.0.1:5000"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  Server running at http://127.0.0.1:5000 (Press Ctrl+C to stop)      " -ForegroundColor Cyan
Write-Host "======================================================================`n" -ForegroundColor Cyan

python app.py
