#Requires -Version 7
<#
.SYNOPSIS
Deploy the launch site and its redirect shell to their own Pages projects.

.DESCRIPTION
The directory-to-project mapping is fixed here on purpose. Swapping the two
takes the production site down: the redirect shell's catch-all, served from the
apex, would redirect ai-iconflow.com to itself.

The content deploy runs with the working directory inside website/ because
Cloudflare Pages resolves functions/ relative to Wrangler's working directory.
Deploying from the repository root ships no Functions bundle and prints no
error, which silently restores content on iconflow.pages.dev.
#>
[CmdletBinding()]
param(
    [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$canonical = 'https://ai-iconflow.com'

Write-Host '==> Deploying site content to project "iconflow"' -ForegroundColor Cyan
$contentLog = npx wrangler pages deploy . --cwd website --project-name iconflow --branch main --commit-dirty=true 2>&1
$contentLog | Write-Host
if ($contentLog -notmatch 'Uploading Functions bundle') {
    throw 'Content deploy shipped no Functions bundle. iconflow.pages.dev would serve content instead of redirecting.'
}

Write-Host '==> Deploying redirect shell to project "ai-iconflow"' -ForegroundColor Cyan
npx wrangler pages deploy website-redirect --project-name ai-iconflow --branch main --commit-dirty=true 2>&1 | Write-Host

if ($SkipVerify) { return }

Write-Host '==> Verifying the host contract' -ForegroundColor Cyan
# Cloudflare needs a moment to promote the new deployment to the aliases.
Start-Sleep -Seconds 10

$failures = @()

function Test-Host {
    param([string]$Url, [int]$Expect, [string]$ExpectLocation)
    $response = Invoke-WebRequest -Uri $Url -MaximumRedirection 0 -SkipHttpErrorCheck -ErrorAction Stop
    $status = [int]$response.StatusCode
    $location = $response.Headers['Location'] -join ''
    $ok = $status -eq $Expect -and ($ExpectLocation -eq '' -or $location -eq $ExpectLocation)
    $mark = if ($ok) { 'ok  ' } else { 'FAIL' }
    Write-Host ("  {0} {1} -> {2} {3}" -f $mark, $Url, $status, $location)
    if (-not $ok) { return "$Url expected $Expect $ExpectLocation, got $status $location" }
    return $null
}

$failures += Test-Host -Url "$canonical/" -Expect 200
$failures += Test-Host -Url "$canonical/gallery/" -Expect 200
$failures += Test-Host -Url 'https://iconflow.pages.dev/gallery/' -Expect 301 -ExpectLocation "$canonical/gallery/"
$failures += Test-Host -Url 'https://www.ai-iconflow.com/gallery/' -Expect 301 -ExpectLocation "$canonical/gallery/"
$failures += Test-Host -Url 'https://ai-iconflow.pages.dev/' -Expect 301 -ExpectLocation "$canonical/"

$failures = $failures | Where-Object { $_ }
if ($failures) {
    $failures | ForEach-Object { Write-Error $_ }
    throw 'Host contract verification failed.'
}
Write-Host 'Host contract verified.' -ForegroundColor Green
