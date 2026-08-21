# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Create OS shortcuts that point at a target, wearing the icon you just built.

Windows `.lnk` only for now. This encodes three hard-won lessons so callers never
have to rediscover them:

  1. **COM Save() mangles non-ASCII paths.** `WScript.Shell.CreateShortcut(p).Save()`
     pushes `p` through the system ANSI codepage, so a CJK filename like
     "世界盃2026觀賽中心.lnk" becomes "???.lnk" and the save fails. Workaround:
     save to an ASCII temp path, then move it to the real Unicode name with
     .NET `[IO.File]::Move` (Unicode-safe).
  2. **Windows PowerShell 5.1 reads UTF-8 .ps1 as ANSI.** A BOM-less UTF-8 script
     mojibakes under powershell.exe. We emit the generated script as utf-8-sig
     (with BOM) so both `pwsh` and `powershell.exe` decode it correctly.
  3. **Explorer keys shortcut icons by path.** Recreating a `.lnk` against the
     same `icon.ico` can retain stale pixels. An optional content-addressed alias
     gives changed bytes a changed `IconLocation` and makes read-back meaningful.

It also resolves the desktop the way Windows actually redirects it (OneDrive +
local), dropping the shortcut in every real location.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _ps_exe() -> str | None:
    """Prefer PowerShell 7 (pwsh); fall back to Windows PowerShell."""
    return shutil.which("pwsh") or shutil.which("powershell")


def _psq(s: str | None) -> str:
    """Quote a Python string as a PowerShell single-quoted literal (or $null)."""
    if not s:
        return "$null"
    return "'" + s.replace("'", "''") + "'"


def _psbool(value: bool) -> str:
    return "$true" if value else "$false"


def install_content_addressed_icon(icon: str | Path) -> Path:
    """Copy an icon beside its source under a SHA-256-derived immutable name.

    The 12-hex prefix is sufficient for normal icon delivery. If that path
    somehow already contains different bytes, the full digest is used instead.
    Existing identical aliases are reused without rewriting their timestamps.
    """
    source = Path(icon).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"icon file not found: {source}")

    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    suffix = source.suffix or ".ico"
    destination = source.with_name(f"shortcut-icon-{digest[:12]}{suffix}")
    if destination == source:
        return source
    if destination.exists() and destination.read_bytes() != payload:
        destination = source.with_name(f"shortcut-icon-{digest}{suffix}")
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination


_PS_TEMPLATE = r"""$ErrorActionPreference = 'Stop'
$target  = {target}
$icon    = {icon}
$argline = {args}
$workdir = {workdir}
$desc    = {desc}
$name    = {name}
$outmode = {outmode}
$verify  = {verify}

if ($outmode -eq 'desktop') {{
    $dests = @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:USERPROFILE 'Desktop'))
}} elseif ($outmode -eq 'startmenu') {{
    $dests = @([Environment]::GetFolderPath('Programs'))
}} else {{
    $dests = @($outmode)
}}
$dests = $dests | Select-Object -Unique | ForEach-Object {{ Join-Path $_ ($name + '.lnk') }}

$ws = New-Object -ComObject WScript.Shell
foreach ($final in $dests) {{
    $dir = Split-Path -Parent $final
    if (-not (Test-Path -LiteralPath $dir)) {{ Write-Output ("SKIP " + $final + " (no such dir)"); continue }}
    # COM Save() corrupts CJK paths -> save ASCII temp, then Move to the real name.
    $tmp = Join-Path $env:TEMP ('iconflow_' + [Guid]::NewGuid().ToString('N') + '.lnk')
    try {{
        $s = $ws.CreateShortcut($tmp)
        $s.TargetPath = $target
        if ($argline) {{ $s.Arguments = $argline }}
        if ($workdir) {{ $s.WorkingDirectory = $workdir }}
        if ($icon)    {{ $s.IconLocation = "$icon,0" }}
        if ($desc)    {{ $s.Description = $desc }}
        $s.WindowStyle = 7
        $s.Save()
        if (Test-Path -LiteralPath $final) {{ Remove-Item -LiteralPath $final -Force }}
        [System.IO.File]::Move($tmp, $final)
        Write-Output ("OK   " + $final)
        if ($verify) {{
            # COM CreateShortcut has the same ANSI path issue for CJK .lnk reads;
            # verify through an ASCII temp copy.
            $verifyTmp = Join-Path $env:TEMP ('iconflow_verify_' + [Guid]::NewGuid().ToString('N') + '.lnk')
            Copy-Item -LiteralPath $final -Destination $verifyTmp -Force
            try {{
                $v = $ws.CreateShortcut($verifyTmp)
                Write-Output ("VERIFY TargetPath=" + $v.TargetPath)
                Write-Output ("VERIFY Arguments=" + $v.Arguments)
                Write-Output ("VERIFY WorkingDirectory=" + $v.WorkingDirectory)
                Write-Output ("VERIFY IconLocation=" + $v.IconLocation)
            }} finally {{
                if (Test-Path -LiteralPath $verifyTmp) {{ Remove-Item -LiteralPath $verifyTmp -Force -ErrorAction SilentlyContinue }}
            }}
        }}
    }} catch {{
        if (Test-Path -LiteralPath $tmp) {{ Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }}
        Write-Output ("FAIL " + $final + " : " + $_.Exception.Message)
    }}
}}
"""


def create_shortcut(*, target: str, name: str, icon: str = "", args: str = "",
                    workdir: str = "", desc: str = "", out: str = "desktop",
                    verify: bool = False,
                    content_address_icon: bool = False) -> list[str]:
    """Create a Windows .lnk named `name` pointing at `target`, wearing `icon`.

    `out` is "desktop" (every redirected + local desktop), "startmenu", or an
    explicit directory. Returns the PowerShell status lines (OK/FAIL/SKIP each).
    If `verify` is true, output also includes read-back TargetPath, Arguments,
    WorkingDirectory, and IconLocation lines for each created shortcut. When
    `content_address_icon` is true, the icon is copied beside its source under
    a SHA-256-derived name and verification is enabled automatically.
    """
    if sys.platform != "win32":
        raise SystemExit("iconflow shortcut: Windows-only (creates a .lnk).")
    ps = _ps_exe()
    if not ps:
        raise SystemExit("iconflow shortcut: neither pwsh nor powershell found on PATH.")

    lines: list[str] = []
    if content_address_icon:
        if not icon:
            raise SystemExit("iconflow shortcut: --content-address-icon requires --icon.")
        try:
            icon = str(install_content_addressed_icon(icon))
        except FileNotFoundError as exc:
            raise SystemExit(f"iconflow shortcut: {exc}") from exc
        verify = True
        lines.append(f"ICON {icon}")

    script = _PS_TEMPLATE.format(
        target=_psq(target), icon=_psq(icon), args=_psq(args),
        workdir=_psq(workdir), desc=_psq(desc), name=_psq(name),
        outmode=_psq(out), verify=_psbool(verify),
    )
    # utf-8-sig: the BOM makes powershell.exe (5.1) read the script as UTF-8.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8-sig",
        newline="\n",
        prefix="iconflow_shortcut_",
        suffix=".ps1",
        delete=False,
    ) as handle:
        handle.write(script)
        tmp = Path(handle.name)
    try:
        res = subprocess.run(
            [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],
            capture_output=True, text=True, encoding="utf-8",
        )
    finally:
        tmp.unlink(missing_ok=True)
    status_lines = [ln for ln in (res.stdout or "").splitlines() if ln.strip()]
    if res.returncode != 0 and not status_lines:
        raise SystemExit(f"iconflow shortcut: PowerShell failed:\n{res.stderr}")
    return lines + status_lines
