# Output Targets — what each project type needs

The build engine produces the right file set per target. Pick targets with
`--targets web,tauri,tray` (comma list) or `--targets all`. Unknown target names
fail fast with a clear error. `iconflow review --config iconflow.toml` previews
the same target transforms; it does not approximate them with the raw master.

---

## `web` / `pwa` — website favicon + PWA

Produces, in the out dir:

| File | Size(s) | Purpose |
|---|---|---|
| `favicon.svg` | vector | primary favicon, modern browsers, scales + dark-mode |
| `favicon.ico` | 16, 32, 48 | legacy fallback (multi-size, PNG-packed) |
| `apple-touch-icon.png` | 180 | iOS home screen (flattened onto bg — never transparent) |
| `icon-192.png` | 192 | PWA manifest, home screen |
| `icon-512.png` | 512 | PWA manifest, splash |
| `icon-512-maskable.png` | 512 | Android adaptive (canonical 10% padding + solid bg; the exact bytes audited by `check`) |
| `site.webmanifest` | — | PWA manifest JSON |
| `favicon-head.html` | — | the `<head>` tags to paste |

Optional with `--windows-tiles`:

| File | Size | Purpose |
|---|---:|---|
| `mstile-70x70.png` | 70×70 | Windows tile |
| `mstile-144x144.png` | 144×144 | Windows tile / legacy meta use |
| `mstile-150x150.png` | 150×150 | Windows tile |
| `mstile-310x310.png` | 310×310 | Windows large tile |
| `mstile-310x150.png` | 310×150 | Windows wide tile |
| `browserconfig.xml` | — | Windows tile metadata |

`<head>` (also written to `favicon-head.html`):

```html
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
```

`favicon.ico` is a small compatibility fallback; keep it unless the consuming
product explicitly owns a narrower browser contract. Pass `--name`, `--theme`,
and `--bg` to fill the manifest.

If the identity master must remain a raster photo/emote, do not hide it inside
an SVG `<image>` data URI and use that wrapper as the primary favicon. Chromium
favicon/static-render paths may reject the embedded raster even when a normal
SVG viewer accepts it. Ship and link the generated PNG/ICO files directly; an
SVG link should point to a genuinely vector alternative.

Manifest and path customization:

```bash
python -m iconflow build master.svg --out ./public --targets web \
  --name "My App" --short-name "App" --description "A focused tool" \
  --path-prefix /assets/icons/ \
  --manifest-extra display_override='["standalone","browser"]' \
  --head-meta application-name="My App"
```

Use `--relative-paths` for local/static sites. It emits `./favicon.ico` style
paths in `favicon-head.html` and bare `icon-192.png` paths in the manifest.
Use `--start-url`, `--scope`, `--display`, `--orientation`, `--lang`, `--dir`,
`--categories`, and `--app-id` when the consuming app needs richer PWA metadata.

### Static local websites opened by desktop shortcut

If the shortcut opens a local `index.html` directly through `file://`, prefer
relative URLs in the consuming site's `<head>` and manifest:

```html
<link rel="icon" href="./favicon.ico" sizes="32x32">
<link rel="icon" href="./favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="./apple-touch-icon.png">
<link rel="manifest" href="./site.webmanifest">
```

Pass `--relative-paths` so manifest icon `src` values become `icon-192.png` and
equivalent 512/maskable paths. Root-relative `/...` paths are correct for hosted
sites, but they point at the filesystem root when opened as a local file.

For the Windows desktop entry, a tiny PowerShell launcher is usually more robust
than targeting the HTML file directly:

```powershell
$sitePath = Join-Path $PSScriptRoot "public\index.html"
Start-Process -FilePath $sitePath
```

Then create the shortcut with the high-level helper:

```bash
python -m iconflow shortcut \
  --powershell-script "D:\site\launch-site.ps1" \
  --icon "D:\site\build\icon.ico" \
  --workdir "D:\site" \
  --name "Site Name" \
  --out desktop \
  --verify
```

`--verify` should show `powershell.exe` as `TargetPath`, the launcher script in
`Arguments`, the project directory as `WorkingDirectory`, and the built `.ico`
as `IconLocation`.

---

## `tauri` — Tauri v2 desktop app bundle

Produces `icons/` matching what `src-tauri/` expects:

```
icons/32x32.png  64x64.png  128x128.png  128x128@2x.png  icon.png(512)
icons/icon.ico   (16,24,32,48,64,256)
icons/icon.icns  (16,32,64,128,256,512,1024)
```

Drop `icons/` into `src-tauri/` and reference in `tauri.conf.json > bundle.icon`.
The ICO directory order begins with 32px, matching the desktop development
contract, and every PNG/ICO/ICNS frame is rendered natively from the SVG.
See the [Tauri v2 app-icon contract](https://v2.tauri.app/develop/icons/) for
the upstream desktop and platform-project requirements.

This target is deliberately scoped to the **desktop bundle**. Tauri Android and
iOS assets live inside generated platform projects and need platform-specific
foreground/background/monochrome semantics plus opaque iOS variants. IconFlow
does not pretend that a single full-card master is enough to author those
families. Use the native platform asset tools until a future semantic
`tauri-mobile` target is introduced.

---

## `electron` — Electron / electron-builder

Produces `build/`:

```
build/icon.png   (1024; use --electron-radius 0.18 to pre-round corners)
build/icon.ico   (16,24,32,48,64,256)
build/icon.icns  (16,32,64,128,256,512,1024)
```

electron-builder auto-selects `icon.ico` (Windows), `icon.icns` (macOS),
`icon.png` (Linux) from `build/`. `--electron-radius` applies the same transparent
corner mask to the PNG **and every native ICO/ICNS frame**, so previews and
packaged applications cannot drift.

---

## `tray` — system-tray / menu-bar icon

Produces `tray/`:

| File | Size | Platform |
|---|---|---|
| `tray.png` | 32 | Windows tray (full color) |
| `tray@16.png` | 16 | Windows tray (small DPI) |
| `trayTemplate.png` | 16 | macOS menu bar (monochrome **template**, OS recolors) |
| `trayTemplate@2x.png` | 32 | macOS menu bar retina |
| `trayIcon.ts` | — | optional (`--tray-ts`): base64 data-URL module, like bookmark-manager |

Tray design notes (also in the playbook): a tray icon lives at 16px on a busy,
often-colored bar. Prefer a **bold single-glyph silhouette**; on macOS it MUST be
monochrome+alpha. For full-card app icons, pass a semantic mark-only source with
`--tray-svg tray.svg`. That source drives the color 16/32px assets, both macOS
template frames, and optional TypeScript module.

Without `--tray-svg`, `--tray-template-mode auto` preserves the alpha of a
sparse mark or attempts to isolate a contrasting mark from a full card. It
fails clearly when separation is unreliable instead of shipping a featureless
black square. `alpha` and `contrast` are explicit modes for callers that know
their source semantics. Verify the exact Windows and macOS outputs in the
target-aware Review Lab on both light and dark bars.

If the tray icon **recolors by state** (e.g. active/paused/error), render it from
ONE shared mark function used by both the built static icons *and* the live
recolor path, so the two never drift.

---

## Verifying & refreshing the icon on Windows (a real gotcha)

After you build/replace an exe's `.ico` (or a `.lnk` shortcut's icon), Windows
Explorer and the taskbar routinely keep showing the **old** icon. This is almost
always the **shell icon cache**, not a bad build — don't re-render chasing it
until you've confirmed the file itself:

- **Prove the bytes are right.** Extract the embedded icon
  (`[System.Drawing.Icon]::ExtractAssociatedIcon($exe)` → save → look), or copy
  the exe to a **fresh filename** and view that (a new path sidesteps the
  per-path cache). If the copy shows the new mark, the build is correct and it's
  purely a cache/display issue.
- **Force a refresh:** delete
  `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db` and
  `%LOCALAPPDATA%\IconCache.db`, run `ie4uinit.exe -ClearIconCache`, then restart
  `explorer.exe`. Touching the file's mtime nudges a stuck per-file icon.
- **Shortcuts:** the most reliable user-facing fix is to **delete and recreate**
  the desktop shortcut — that often updates instantly when cache-clearing won't.

If a consuming project regenerates icons with its **own Pillow script** (not this
toolkit), pack the multi-size `.ico` from the **largest** frame as the base image
— Pillow's ICO writer silently drops any requested size larger than the base, so
packing from the 16px frame yields a 16-only icon (looks fine in a shortcut,
blurry/upscaled everywhere larger).

---

## Combine freely

```bash
# a Tauri app that also has a tray and a marketing site:
python -m iconflow build master.svg --out ./dist --targets tauri,tray,web \
    --name "Proof Desk" --theme "#191a20" --bg "#fff4e8" \
    --tray-svg tray.svg --tray-ts
```

All targets reuse one network-isolated Chromium session. Within each SVG
source, every required size renders once and is then shared from cache; a
semantic `tray.svg` uses its own cache in the same session.

---

## `shortcut` — wire the built icon onto the Windows desktop (Windows-only)

After building, `iconflow shortcut` drops a `.lnk` (Desktop or Start menu) that
launches a target and wears the `.ico` you just produced. Use it to finish the
"send it to the desktop" step instead of hand-rolling COM PowerShell.

```bash
# Launch a hidden VBS tray app, name in Chinese, with the built icon:
python -m iconflow shortcut \
    --target wscript.exe --args '"D:\app\觀賽中心.vbs"' \
    --icon "D:\app\icons\build\icon.ico" --workdir "D:\app" \
    --name "世界盃2026觀賽中心" --out desktop
```

For the common "desktop icon launches a PowerShell helper script" case, avoid
fragile nested shell quoting with `--powershell-script`:

```bash
python -m iconflow shortcut \
    --powershell-script "D:\app\launch-app.ps1" \
    --icon "D:\app\icons\build\icon.ico" --workdir "D:\app" \
    --name "Research Workstation" --out desktop --verify
```

That expands to `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
"D:\app\launch-app.ps1"` internally. `--verify` reads the created shortcut back
through an ASCII temp copy and prints `TargetPath`, `Arguments`,
`WorkingDirectory`, and `IconLocation`; this catches quoting and CJK path issues
immediately.

`--out` is `desktop` (every redirected + local Desktop, e.g. OneDrive),
`startmenu`, or an explicit directory. It bakes in two Windows gotchas so you
don't rediscover them:

- **COM `Save()` corrupts non-ASCII paths** → it saves to an ASCII temp `.lnk`
  then `[IO.File]::Move`s to the real (e.g. CJK) name. Note the *same* COM bug
  means you can't verify a CJK `.lnk` with `CreateShortcut($cjkPath)` — copy it
  to an ASCII path first, then read.
- **PowerShell 5.1 reads BOM-less UTF-8 `.ps1` as ANSI** → the generated script
  is emitted as `utf-8-sig`, and CLI stdout is forced to UTF-8.
