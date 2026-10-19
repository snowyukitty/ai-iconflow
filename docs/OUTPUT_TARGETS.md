<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Output Targets — what each project type needs

The build engine produces the right file set per target. Pick targets with
`--targets web,tauri,tray` (comma list) or `--targets all`. `all` means the
desktop and web app-icon targets (`web, pwa, tauri, electron, tray`), frozen at
that set: a receipt records the expanded list, so growing `all` would turn
every approved `all` project stale on upgrade. `android`, `emote` and `ios`
are only built when they are named. Unknown target names fail fast with a clear error. `iconflow review --config iconflow.toml` previews
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
| `icon-512-maskable.png` | 512 | Android adaptive (the maskable composition below on a solid bg; the exact bytes audited by `check`) |
| `site.webmanifest` | — | PWA manifest JSON |
| `favicon-head.html` | — | the `<head>` tags to paste |

### The maskable / adaptive composition

One composition serves every adaptive crop IconFlow emits — the PWA's
`icon-512-maskable.png` and every Android layer — and `check`, `review` and
`ship` audit that one composition on the configured `background_color`
(`iconflow/audit.py`). Three `[build]` keys shape it; all are optional and a
0.6 config needs none of them:

| Key | Default | Meaning |
|---|---|---|
| `maskable_scale` | `0.8` (master), `1.0` (linked source) | share of the maskable canvas the artwork fills, 0.5–1.0 |
| `maskable_svg` | none | a linked source drawn for the crop, like `tray_svg` |
| `monochrome_svg` | `tray_svg` if set | mark-only source for Android's themed icon |

A square full-bleed mark does not have to round its corners or shrink its
cells to survive a circle crop: lower `maskable_scale` (the keyhole grid that
failed at 0.8 passed at 0.7 unchanged), or link a `maskable_svg`. A linked
source is gated on being the same mark — its figure, cropped to its own
bounds, must overlap the master's by at least the ladder's 0.62 IoU floor and
keep its aspect within 15% (`maskable-drift`) — so it may change scale,
padding and background, never the drawing.

A key enters the review contract only when it changes a shipped byte: an
explicit `maskable_scale = 0.8` on the master, or a linked source that no
selected target consumes, leaves every existing receipt valid.

Optional with `--windows-tiles`:

| File | Size | Purpose |
|---|---:|---|
| `mstile-70x70.png` | 70×70 | Windows tile |
| `mstile-144x144.png` | 144×144 | Windows tile / legacy meta use |
| `mstile-150x150.png` | 150×150 | Windows tile |
| `mstile-310x310.png` | 310×310 | Windows large tile |
| `mstile-310x150.png` | 310×150 | Windows wide tile |
| `browserconfig.xml` | — | Windows tile metadata |

### Manifest-defined Windows package assets

Microsoft Store/MSIX manifests can require additional fixed-size logo slots
and exact asset names beyond IconFlow's `web --windows-tiles` output. IconFlow
does not currently expose an `msix` target. Use `iconflow render` to produce
each required size directly from the reviewed SVG, inspect every actual-size
RGBA raster on representative light, gray, and dark contexts, and only then
copy the verified bytes to the exact filenames referenced by the package
manifest. A generic size-suffixed export is not a packaging contract, and one
large source handed to an implicit scaler is not an exact-size review.

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

This target is deliberately scoped to the **desktop bundle**. For Tauri
Android, add the `android` target below and copy `android/res/` into
`src-tauri/gen/android/app/src/main/res/` — do not run `cargo tauri icon`
over IconFlow's output directory, which would overwrite the desktop icons it
just wrote. iOS is not a target yet (see *Not targets yet*).

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

Audit the two reductions before you trust them. The colour asset and the macOS
template come from one source but discard different information, so a source
that is opaque wherever its halo reaches ships a good tray icon and a featureless
black lozenge in the menu bar:

```bash
python -m iconflow check master.svg --tray-svg tray.svg --tray-template-mode alpha
```

It compares the interior detail of the colour tray asset against the enclosed
holes of the derived template and reports when the template kept none of the
mark's features. The fix is a single broad transparent cut through the tray
source — see `docs/LEARNINGS.md` L48 and `SVG_TECHNIQUES.md` §11. The audit is
advisory and does not gate `ship`.

If the tray icon **recolors by state** (e.g. active/paused/error), render it from
ONE shared mark function used by both the built static icons *and* the live
recolor path, so the two never drift.

---

## `android` — Android launcher icons (adaptive, themed, legacy)

Produces `android/`, laid out as an Android resource tree:

| File | Size | Purpose |
|---|---|---|
| `res/mipmap-anydpi-v26/ic_launcher.xml` | XML | adaptive icon: background, foreground, monochrome |
| `res/mipmap-anydpi-v26/ic_launcher_round.xml` | XML | the same, for `android:roundIcon` |
| `res/values/ic_launcher_background.xml` | XML | background layer as a colour resource (`background_color`) |
| `res/mipmap-<d>/ic_launcher_foreground.png` | 108dp | adaptive foreground layer |
| `res/mipmap-<d>/ic_launcher_monochrome.png` | 108dp | themed-icon layer, Android 13+ (alpha only) |
| `res/mipmap-<d>/ic_launcher.png` | 48dp | legacy launcher icon, rounded-square keyline |
| `res/mipmap-<d>/ic_launcher_round.png` | 48dp | legacy round launcher icon |
| `play-store-512.png` | 512 | Google Play listing icon (full square; Play masks it) |

`<d>` is each of `mdpi` (1×), `hdpi` (1.5×), `xhdpi` (2×), `xxhdpi` (3×) and
`xxxhdpi` (4×): 108/162/216/324/432 px layers and 48/72/96/144/192 px legacy
icons. The artwork is rendered natively at the pixel size it occupies in each
density, never scaled down from one large render.

**Geometry.** A launcher shows the central 72dp of a 108dp layer through its
mask and guarantees only the central 66dp circle. IconFlow maps the maskable
canvas onto the layer at 66/0.8 = 82.5dp, so the maskable safe circle (radius
40%) lands exactly on Android's 66dp circle. With the default `maskable_scale`
of 0.8 the artwork's canvas fills 66/108 of the layer. That is why one
`maskable-detail` audit guards both the PWA and Android, and why
`maskable_scale` / `maskable_svg` reshape both together.

**Themed icon.** Android 13+ tints the monochrome layer and reads only its
alpha. IconFlow takes it from `monochrome_svg`, else `tray_svg` — a mark-only
source is exactly what a themed icon needs — and otherwise derives it the way
the macOS template is derived (`tray_template_mode`). A full-card master with
no mark-only source fails the build with that instruction instead of shipping
a featureless disc.

**Legacy icons** (before Android 8) show the same central 72dp of the
composition a modern launcher shows, cut to a 44dp keyline in the 48dp canvas:
a rounded square (`ic_launcher.png`) and a circle (`ic_launcher_round.png`).

**Install.** Copy `android/res/` into `app/src/main/res/` (a Tauri project's
lives at `src-tauri/gen/android/app/src/main/res/`) and point the manifest at
`@mipmap/ic_launcher` and `@mipmap/ic_launcher_round`. The `<monochrome>`
element needs `compileSdk` 33 or newer. Review the composition in the Review
Lab's Android card (circle, squircle, themed and legacy previews of the exact
bytes) before shipping.

```bash
iconflow build master.svg --targets android --bg "#11142A" --out out
```

---

## `ios` — iOS / iPadOS app icon (light, dark, tinted) — from 0.10

Produces `ios/`, an Xcode asset-catalog icon set plus two companions:

| File | Size | Purpose |
|---|---|---|
| `AppIcon.appiconset/Contents.json` | JSON | one 1024 px entry per appearance this build ships |
| `AppIcon.appiconset/icon-1024.png` | 1024 | **light** (Any): opaque RGB, full bleed — iOS masks the square itself |
| `AppIcon.appiconset/icon-1024-dark.png` | 1024 | **dark**: the mark on a transparent background (iOS draws its dark ground through it) |
| `AppIcon.appiconset/icon-1024-tinted.png` | 1024 | **tinted**: opaque 8-bit grayscale; iOS colours it by luminance |
| `icon-composer/mark.svg` | vector | the transparent full-canvas foreground layer Icon Composer imports (Xcode 26+) |
| `README.md` | text | install notes for Xcode, Expo, Capacitor, Flutter and Icon Composer, for exactly these files |

Xcode builds every iOS size from one 1024 px image per appearance ("Single
Size"). Apple's contract for the variants: *"Provide your tinted app icon as a
grayscale image. Provide your dark app icon with a transparent background so
the system-provided background can show through."* Both are optional — without
them iOS applies its own treatment — so IconFlow ships them only when it can
derive them honestly, and never invents one.

**Where the appearances come from.** The master's semantic layers
(`SVG_TECHNIQUES.md` §11). Declare the card or backdrop as
`id="iconflow-background"` and IconFlow:

- stretches it to the whole canvas for the **light** icon (the house card is
  inset; on iOS an inset card would show `background_color` as a border);
- removes it for the **dark** icon, rendered in the dark colour scheme, so a
  master with `prefers-color-scheme` styles gets its dark colours;
- composites the dark image once over black and keeps its luminance for the
  **tinted** icon — one fixed mapping, no per-image stretching.

The declared background must be **one shape** (`rect`, `circle`, `ellipse`,
`path` or `polygon`), a **direct child** of `<svg>`, the **first painted**
element, painted by a plain `fill` (an opaque colour, or a `linearGradient` /
`radialGradient` in the master) with no `transform`, `filter`, `mask`,
`clip-path`, `opacity`, `fill-opacity`, `style`, `class`, `data-lod`,
`display` or `visibility`, and nothing may refer to it. A stylesheet in such a
master is held to a small language that cannot hide a rule: top-level style
rules and one level of `@media` blocks of them (enough for
`prefers-color-scheme`), comments, and selectors of element, `.class` and
`#id` compounds joined by descendant or child combinators. A bare selector of
the card's element type or of `rect` (what full bleed turns the card into) is
refused, and so are strings, escapes, nested rules, other at-rules, siblings,
pseudo-classes, attributes and `*` — each could repaint the card or change
meaning once it is removed or extended. Style the dark icon with a linked
`ios_dark_svg` instead.

Rules are not the guarantee; rendering is. Whenever the master's mark ships
on its own — as the dark icon, or as the Icon Composer layer — the Chromium
that ships the pixels first proves it can stand alone: on the 1024 px rung, at
1024 px, in the light and the dark scheme, the mark IconFlow ships must equal
the master's mark with the card still in the document but not painting (in
full RGBA), and the master must equal its card painting alone with that mark
composited over it — both up to rounding (no channel moves more than 4
levels). A mark that depends on its card in any way — blending with
it (`mix-blend-mode`), a CSS function that reads the document
(`sibling-index()`), a motion path along it — fails the build. The fixes: ship
the light icon alone (`ios_variants = "system"`, which never separates the
mark), or remove the declaration and link `ios_dark_svg`. A declaration outside that subset fails the build
with the rule it broke; it never falls back silently. Geometry is never
guessed: an untagged master ships the **light icon alone** (flattened onto
`background_color`) and iOS derives dark and tinted, with an advisory saying
how to declare the layer.

**When the mark is not made for a dark screen.** A light card with a dark mark
loses the mark once the card is removed. The audit catches it
(`ios-dark-contrast`, `ios-tinted-faint`), and the fix is one of:

```toml
[build]
targets = ["web", "ios"]
ios_dark_svg = "master-dark.svg"   # the same mark, drawn for a dark ground
# or
ios_variants = "system"            # ship the light icon; iOS derives the rest
```

`ios_dark_svg` is a linked source like `maskable_svg`: captured once, hashed
into the approval (only when `ios` is a target), replayed by `ship --plan`.
Tinted is then derived from it.

**What the audit checks** (on the plan's own 1024 px files):

| Code | Gate | Rule |
|---|---|---|
| `ios-dark-empty` | blocks | the dark layer covers under 2% of the canvas |
| `ios-dark-contrast` | blocks | under 50% of the mark reaches 3:1 against iOS's dark ground (≈ `#1C1C1E`); pixels in the declared card colour are cuts and are not counted |
| `ios-tinted-faint` | blocks | the tinted mark's mean luminance is under 96/255 |
| `ios-underivable` | blocks | the declared layer cannot be honoured (the build fails with the same rule) |
| `ios-tinted-merge` | advisory | two large, clearly different colours become one grey in the tinted icon |
| `ios-variants-system` | advisory | dark and tinted are left to iOS |
| `ios-light-flattened` | advisory | no declared layer: the light icon is the master on `background_color` |

The thresholds are heuristics written down once in `iconflow/ios.py`; the
Review Lab's iOS card and the iOS row of `targets.png` show the actual files
(the dark ground and tint colour there are approximations). Xcode's `actool`
enforces none of the encodings — it compiles a light icon with alpha and an
RGB "tinted" image without a word — so IconFlow validates them on every build,
audit and imported plan, and CI compiles generated sets with `actool` and
checks what `assetutil` recorded.

**Install.** Replace your `Assets.xcassets/AppIcon.appiconset` (Xcode;
Capacitor's is under `ios/App/App/`, Flutter's under `ios/Runner/`), or point
Expo's `ios.icon` at the three PNGs (`{"light": …, "dark": …, "tinted": …}`).
The generated `ios/README.md` lists exactly the files this build wrote.

**Icon Composer.** Since Xcode 26 Apple prefers a layered `.icon` document,
made in Icon Composer from SVG layers. Its format is not published, so
IconFlow does not write one: `icon-composer/mark.svg` is the declared
foreground on a transparent full-size canvas, reduced to the 1024 px rung — a
starting point to import, with the background colour named in the README.
Glass, translucency and the mono annotation are design decisions made there.
Shapes the master paints in its card colour stay painted: they are not holes.

**Approvals.** An approval that ships `ios` must carry the render plan it
reviewed (Review Lab or `review --evidence` + `score`): appearances nobody saw
are not shipped. `ios` is not in `all`; ask for it by name. A build into a
folder that still holds iOS files this build does not write (dark and tinted
from an earlier build, say) is refused before anything changes.

```bash
iconflow build master.svg --targets ios --bg "#191A20" --out out
```

---

## Not targets yet — and why

Reviewed for 0.7 and deliberately left out:

- **Windows MSIX / Store tile assets.** Package manifests own both the exact
  filenames and the scale-qualified sizes (L43), and they differ by manifest.
  A generic set would be guessed filenames. Keep using `iconflow render` for
  the sizes a manifest names, plus `--windows-tiles` for pinned-site tiles.

MSIX is a candidate once a consuming project supplies the real manifest to
golden-test against. iOS was on this list until 0.10: 0.7 declined it because
its dark and tinted variants need semantic sources, not a transform of the
light icon — the semantic layers and `ios_dark_svg` above are those sources.

---

## `emote` — chat emotes for Twitch, Discord and Slack

| File | px | Where |
|---|---|---|
| `emote/28.png` | 28 | Twitch, as drawn in chat |
| `emote/56.png` | 56 | Twitch, 2× |
| `emote/112.png` | 112 | Twitch, 4× (Twitch uploads all three together) |
| `emote/128.png` | 128 | Discord and Slack custom emoji |

Each size is rendered natively from the SVG, transparent, never scaled down
from the largest. A file over its platform's upload limit — 25 KB for each
Twitch size, 128 KB for the 128 (Slack's cap; Discord allows 256 KB) — fails
the build with the size it reached, rather than failing in the upload form.

Emotes are judged at 22–28 px on light *and* dark chat, not at 16 px on one
background: review them that way ([`EMOTES.md`](EMOTES.md)). For a set, run
`iconflow family "emotes/*.svg"` ([`FAMILY.md`](FAMILY.md)) so no two members
are the same reaction at chat size.

```bash
iconflow build my-emote.svg --targets emote --out out
```

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
- **Force a refresh (last resort, with explicit user approval):** delete
  `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db` and
  `%LOCALAPPDATA%\IconCache.db`, run `ie4uinit.exe -ClearIconCache`, then restart
  `explorer.exe`. These actions disrupt the desktop session; prefer the
  content-addressed shortcut path below. Touching the file's mtime can nudge a
  stuck per-file icon.
- **Shortcuts:** changing the `.lnk` is not enough when `IconLocation` reuses the
  same canonical `.ico` path. Install a content-addressed copy such as
  `shortcut-icon-<first-12-sha256>.ico`, recreate the shortcut against that new
  path, read `IconLocation` back, and inspect or extract what the Shell resolves
  from the actual `.lnk`. `iconflow shortcut --content-address-icon` performs
  the copy and implies `--verify`. If scripting the digest yourself, do not
  assume `Get-FileHash` exists in every Windows PowerShell host; feature-detect
  it or use `System.Security.Cryptography.SHA256`.

If a consuming project regenerates icons with its **own Pillow script** (not this
toolkit), pack the multi-size `.ico` from the **largest** frame as the base image
— Pillow's ICO writer silently drops any requested size larger than the base, so
packing from the 16px frame yields a 16-only icon (looks fine in a shortcut,
blurry/upscaled everywhere larger).

---

## Combine freely

```bash
# a Tauri app with an Android build:
python -m iconflow build master.svg --out ./dist --targets tauri,android \
    --bg "#11142A" --tray-svg mark.svg

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
    --name "Research Workstation" --out desktop \
    --content-address-icon
```

That expands to `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
"D:\app\launch-app.ps1"` internally. `--verify` reads the created shortcut back
through an ASCII temp copy and prints `TargetPath`, `Arguments`,
`WorkingDirectory`, and `IconLocation`; this catches quoting and CJK path issues
immediately.

`--content-address-icon` copies the source icon beside it as
`shortcut-icon-<first-12-sha256>.ico`, points the `.lnk` at that immutable name,
and automatically enables read-back verification. Rebuilding different bytes
therefore creates a different `IconLocation`, which avoids the Shell's
path-keyed stale-icon failure without deleting system-wide caches. Keep the
canonical `icon.ico` as the build output; the hashed file is a delivery alias.

`--out` is `desktop` (every redirected + local Desktop, e.g. OneDrive),
`startmenu`, or an explicit directory. It bakes in two Windows gotchas so you
don't rediscover them:

- **COM `Save()` corrupts non-ASCII paths** → it saves to an ASCII temp `.lnk`
  then `[IO.File]::Move`s to the real (e.g. CJK) name. Note the *same* COM bug
  means you can't verify a CJK `.lnk` with `CreateShortcut($cjkPath)` — copy it
  to an ASCII path first, then read.
- **PowerShell 5.1 reads BOM-less UTF-8 `.ps1` as ANSI** → the generated script
  is emitted as `utf-8-sig`, and CLI stdout is forced to UTF-8.
