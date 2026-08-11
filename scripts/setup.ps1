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

# Install the iconflow skill from its canonical directory in this repository.
$skillSrc = Join-Path $root "skills\iconflow"
if (Test-Path (Join-Path $skillSrc "SKILL.md")) {
    $skillDestinations = @(
        (Join-Path $env:USERPROFILE ".codex\skills\iconflow"),
        (Join-Path $env:USERPROFILE ".claude\skills\iconflow")
    )
    foreach ($skillDst in $skillDestinations) {
        New-Item -ItemType Directory -Path $skillDst -Force | Out-Null
        Copy-Item (Join-Path $skillSrc "SKILL.md") (Join-Path $skillDst "SKILL.md") -Force

        $agentsSrc = Join-Path $skillSrc "agents\openai.yaml"
        if (Test-Path $agentsSrc) {
            $agentsDst = Join-Path $skillDst "agents"
            New-Item -ItemType Directory -Path $agentsDst -Force | Out-Null
            Copy-Item $agentsSrc (Join-Path $agentsDst "openai.yaml") -Force
        }

        # README.md was part of an older deployment; the skill package now keeps
        # all operator guidance in SKILL.md and the repository-level README.
        $staleReadme = Join-Path $skillDst "README.md"
        if (Test-Path $staleReadme) {
            Remove-Item -LiteralPath $staleReadme -Force
        }
        Write-Host "Installed iconflow skill to $skillDst" -ForegroundColor Cyan
    }
}

Write-Host "`nDone. Try:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m iconflow new gradient-glow --out master.svg"
Write-Host "  .\.venv\Scripts\python.exe -m iconflow review master.svg"
