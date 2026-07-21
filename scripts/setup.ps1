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

# Install the /iconflow Claude Code skill from this repo (its canonical home).
$skillSrc = Join-Path $root "skills\iconflow\SKILL.md"
if (Test-Path $skillSrc) {
    $skillDst = Join-Path $env:USERPROFILE ".claude\skills\iconflow"
    New-Item -ItemType Directory -Path $skillDst -Force | Out-Null
    Copy-Item $skillSrc (Join-Path $skillDst "SKILL.md") -Force
    Write-Host "Installed /iconflow skill to $skillDst" -ForegroundColor Cyan
}

Write-Host "`nDone. Try:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m iconflow new gradient-glow --out master.svg"
Write-Host "  .\.venv\Scripts\python.exe -m iconflow review master.svg"
