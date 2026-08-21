# One-time setup for AI IconFlow (Windows / PowerShell).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "$root\.venv")) {
    Write-Host "Creating virtual env..." -ForegroundColor Cyan
    python -m venv .venv
}
& "$root\.venv\Scripts\python.exe" -m pip install -e $root
& "$root\.venv\Scripts\python.exe" -m iconflow setup

# `skill install` owns every deployment path, so a wheel install and a checkout
# put the same files in the same places.
& "$root\.venv\Scripts\python.exe" -m iconflow skill install

Write-Host "`nDone. Try:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m iconflow doctor"
Write-Host "  .\.venv\Scripts\python.exe -m iconflow demo --out iconflow-demo"
