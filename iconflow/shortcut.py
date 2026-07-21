"""Create OS shortcuts that point at a target, wearing the icon you just built.

Windows `.lnk` only for now. This encodes two hard-won lessons so callers never
have to rediscover them:

  1. **COM Save() mangles non-ASCII paths.** `WScript.Shell.CreateShortcut(p).Save()`
     pushes `p` through the system ANSI codepage, so a CJK filename like
     "世界盃2026觀賽中心.lnk" becomes "???.lnk" and the save fails. Workaround:
     save to an ASCII temp path, then move it to the real Unicode name with
     .NET `[IO.File]::Move` (Unicode-safe).
  2. **Windows PowerShell 5.1 reads UTF-8 .ps1 as ANSI.** A BOM-less UTF-8 script
     mojibakes under powershell.exe. We emit the generated script as utf-8-sig
     (with BOM) so both `pwsh` and `powershell.exe` decode it correctly.

It also resolves the desktop the way Windows actually redirects it (OneDrive +
local), dropping the shortcut in every real location.
"""
from __future__ import annotations

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
                    verify: bool = False) -> list[str]:
    """Create a Windows .lnk named `name` pointing at `target`, wearing `icon`.

    `out` is "desktop" (every redirected + local desktop), "startmenu", or an
    explicit directory. Returns the PowerShell status lines (OK/FAIL/SKIP each).
    If `verify` is true, output also includes read-back TargetPath, Arguments,
    WorkingDirectory, and IconLocation lines for each created shortcut.
    """
    if sys.platform != "win32":
        raise SystemExit("iconflow shortcut: Windows-only (creates a .lnk).")
    ps = _ps_exe()
    if not ps:
        raise SystemExit("iconflow shortcut: neither pwsh nor powershell found on PATH.")

    script = _PS_TEMPLATE.format(
        target=_psq(target), icon=_psq(icon), args=_psq(args),
        workdir=_psq(workdir), desc=_psq(desc), name=_psq(name),
        outmode=_psq(out), verify=_psbool(verify),
    )
    # utf-8-sig: the BOM makes powershell.exe (5.1) read the script as UTF-8.
    tmp = Path(tempfile.gettempdir()) / f"iconflow_shortcut_{id(script)}.ps1"
    tmp.write_text(script, encoding="utf-8-sig")
    try:
        res = subprocess.run(
            [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],
            capture_output=True, text=True, encoding="utf-8",
        )
    finally:
        tmp.unlink(missing_ok=True)
    lines = [ln for ln in (res.stdout or "").splitlines() if ln.strip()]
    if res.returncode != 0 and not lines:
        raise SystemExit(f"iconflow shortcut: PowerShell failed:\n{res.stderr}")
    return lines
