# One-time setup for AI IconFlow (Windows / PowerShell).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "$root\.venv")) {
    Write-Host "Creating virtual env..." -ForegroundColor Cyan
    python -m venv .venv
}
& "$root\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$root\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& "$root\.venv\Scripts\python.exe" -m playwright install chromium
Write-Host "`nDone. Try:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m iconflow new gradient-glow --out master.svg"
Write-Host "  .\.venv\Scripts\python.exe -m iconflow review master.svg"
