---
name: iconflow
description: Design and generate high-quality app icons, website favicons, PWA icons, and system-tray/menu-bar icons. Use whenever a project needs an icon/favicon/logo mark created or regenerated — the agent authors an SVG following a design playbook, renders it small to self-review, then builds every format (.ico/.icns/.png, manifest, tray). Triggers on requests like "make an icon", "design a favicon", "tray icon", "app icon for this Tauri/Electron app".
---

# IconFlow skill

Toolkit lives at **`<AI_PROJECTS>/ai-iconflow`** (the source of truth), where
`<AI_PROJECTS>` is the workspace root directory named `AI_Projects`. Its drive
letter is not fixed — resolve it from the current repository's ancestors or the
workspace, and use that resolved path everywhere below. You are the designer;
the toolkit rasterizes your SVG exactly as a browser would and packs all
formats, with a render-and-review loop.

## Procedure (follow in order — do not skip diverge or review)

0. **Resolve the toolkit and runner first.** Resolve the absolute
   `<AI_PROJECTS>/ai-iconflow` path, then use its venv Python
   (`.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on POSIX) when
   present, otherwise `python`. `<ICONFLOW_PY>` below means that resolved
   executable. First time only: `<ICONFLOW_PY> -m iconflow setup`. Keep the
   shell in the consuming project unless a path explicitly points into the
   toolkit; do not `cd` in a way that changes where project files land.
1. **Read** `<AI_PROJECTS>/ai-iconflow/docs/LEARNINGS.md` (rules distilled from
   every previously shipped icon) and run
   `<ICONFLOW_PY> -m iconflow case stats --dir <AI_PROJECTS>/ai-iconflow/casebook`.
   Apply the existing guidance to this icon and avoid any house-cliché device it
   warns about. A stats signal is
   diagnostic; it does not by itself authorize editing the shared toolkit.
2. **Read** `<AI_PROJECTS>/ai-iconflow/docs/DESIGN_PLAYBOOK.md`. From the
   consuming project, run
   `<ICONFLOW_PY> -m iconflow init --out iconflow.toml`; keep `iconflow.toml`
   and the final sources in that project. Record the brief in it:
   app intent, user job, one-word essence, brand color (pull from the target
   project's existing CSS/theme if present), personality, clichés to avoid,
   signature-device hypothesis, and exact output targets. A visual decision
   without a product job is not a complete brief. For privacy-sensitive work,
   design from a neutral user-job verb (`reveal`, `route`, `discover`) rather
   than a sensitive category noun.
3. **Diverge for distinctiveness**
   (`<AI_PROJECTS>/ai-iconflow/docs/CONCEPTING.md`) — generate 4+ concepts
   via different lenses, apply the cliché filter, add ONE signature device.
   **Distinctiveness = specificity:** the mark must BE a specific object whose
   silhouette names a thing (a tag, a gem, a folded map, a cat), not a bare
   letter on a gradient tile (the *monogram trap*). Study CONCEPTING's exemplar
   gallery first, and apply the name-the-thing test in the bake-off.
   Draft 2–3 finalist SVGs (or start from a preset and add a signature device:
   `<ICONFLOW_PY> -m iconflow new <preset> --out <AI_PROJECTS>/ai-iconflow/work/<slug>/<draft>.svg`).
4. **Bake-off:** use resolved paths for every scratch artifact:
   `<ICONFLOW_PY> -m iconflow compare <AI_PROJECTS>/ai-iconflow/work/<slug>/a.svg <AI_PROJECTS>/ai-iconflow/work/<slug>/b.svg <AI_PROJECTS>/ai-iconflow/work/<slug>/c.svg --out <AI_PROJECTS>/ai-iconflow/work/<slug>/bake.png` →
   **Read that `bake.png`**, run the silhouette + row tests, promote the most
   distinctive-yet-legible winner to `master.svg`. Run the name-the-thing test
   at both 128px and 16px: if the noun changes, change the viewpoint before
   adding detail. Strip color and test detached accents as punctuation; a
   vertical cut centered over a round accent reads as `!` at 16px, so offset
   their centerlines by at least two output pixels (~128 viewBox units) or
   redesign the pair.
5. **Author** the consuming project's `master.svg` using
   `<AI_PROJECTS>/ai-iconflow/docs/SVG_TECHNIQUES.md` (§10 signature devices,
   §11 linked target
   compositions). If a full-card master also targets tray/menu bar, create a
   geometry-linked mark-only `tray.svg` and set it in `iconflow.toml`; do not
   let a card alpha collapse into a featureless tray square.
6. **Check + review (mandatory):**
   - `<ICONFLOW_PY> -m iconflow check master.svg` → fix every warning.
   - `<ICONFLOW_PY> -m iconflow review --config iconflow.toml --out <AI_PROJECTS>/ai-iconflow/work/<slug>/review.png --html <AI_PROJECTS>/ai-iconflow/work/<slug>/review.html` →
     **Read that `review.png` and open that Review Lab** (actual-size pixels,
     silhouette strip, alpha footprint, adaptive crops, target transforms).
     Score vs `<AI_PROJECTS>/ai-iconflow/docs/REVIEW_CHECKLIST.md` and export
     the JSON receipt.
     Distinctiveness is a gate — don't ship below 4/5. If any axis < 4, make the
     single highest-impact change and re-render. ~2–3 passes.
     If a managed browser blocks the local Review Lab, do not bypass policy:
     inspect the static sheet plus the exact target assets at real sizes, record all
     six scores and notes in the source-and-contract-hash-bound `[review]`
     approved fallback, and report the interactive check as blocked. The
     `contract_sha256` must bind the project, targets, colors, Electron radius,
     color scheme, tray mode, and semantic tray source. The ≥4/5 floor and gated
     `ship` still apply.
7. **Ship** into the consuming project:
   `<ICONFLOW_PY> -m iconflow ship --config iconflow.toml --review master-review.json`.
   `ship` re-runs QA, verifies the receipt matches the current SVG / tray source
   / targets / colors / scheme / radius / template, and requires all six axes
   ≥4. (The low-level `build` command remains for callers that own an equivalent
   quality gate.) See `<AI_PROJECTS>/ai-iconflow/docs/OUTPUT_TARGETS.md` for the
   exact target file set.
8. **Keep `master.svg`** in the project and **report** the cliché avoided, the
   signature device, final rubric scores + the produced file list.
9. **Record the case (mandatory — closes the self-evolution loop):**
   `<ICONFLOW_PY> -m iconflow case new --dir <AI_PROJECTS>/ai-iconflow/casebook --slug <slug> --essence <word> --device "..." --device-family <family> --device-detail "..." --concept-lens <lens> --cliche "..." --first "legibility=3 ..." --final "legibility=4 ..." --iterations N --lesson "..."`,
   fill in the created file's *Summary* / *What failed first*, then run
   `<ICONFLOW_PY> -m iconflow case lint --dir <AI_PROJECTS>/ai-iconflow/casebook`,
   `<ICONFLOW_PY> -m iconflow case stats --dir <AI_PROJECTS>/ai-iconflow/casebook`,
   and, for a visual audit,
   `<ICONFLOW_PY> -m iconflow case atlas --dir <AI_PROJECTS>/ai-iconflow/casebook --out <AI_PROJECTS>/ai-iconflow/work/<slug>/case-atlas.html`.
   If stats says **DISTILL NOW** or flags an evolution
   target, change the shared toolkit only when the current work supplies new,
   generalizable evidence and shared-toolkit writes are in scope; otherwise
   report the signal to its owner. When authorized, follow
   `<AI_PROJECTS>/ai-iconflow/docs/EVOLUTION.md` and flip promoted lesson
   checkboxes to `[x]`.
   For a public case derived from privacy-sensitive work, use a neutral project
   label and omit sensitive category nouns, private repository names, local
   paths, and identifying operational details; retain geometry, scores, failed
   readings, targets, and verification evidence.

## Rules
- Diverge before committing; always `review` and actually look at `review.png`
  (and `bake.png`) before building.
- Put draft SVGs / bake / review renders in `<AI_PROJECTS>/ai-iconflow/work/<slug>/`
  (gitignored), never the toolkit repo root.
- Never end the session without `iconflow case new` — an unrecorded icon
  teaches the system nothing.
- Don't ship if `check` has warnings or any rubric axis < 4/5 (distinctiveness
  is a hard gate).
- One style family per icon; 1 dominant color + 1 accent.
- **One dominant foreground shape.** Never cross/overlay two opaque elements
  (e.g. a line *through* a glyph) — they fuse into mud below ~32px and read as
  "blurry". Express the second idea via negative space, nesting, or a small
  corner accent, not a crossing overlay. Judge this on the 16/32px cells, not at
  1024. (See DESIGN_PLAYBOOK §6.)
- **Distinctiveness = specificity (the monogram trap).** A bare letter or generic
  shape on a gradient tile scores ≤3 on distinctiveness (below the ship gate) — it
  passes every mechanical check yet reads as generic. Make the mark a specific
  object; use a letter only when it FUSES into the object (fado's F = plates).
  `check` emits an advisory warning on live `<text>`; path monograms are yours to
  catch with the name-the-thing test. (See CONCEPTING "Distinctiveness =
  specificity" + exemplar gallery; DESIGN_PLAYBOOK §6.)

## Delivering to a desktop/tray app (esp. Windows)
- After `build` (or after rebuilding an exe that embeds the `.ico`), the OS shell
  often keeps showing the OLD icon — that's the **icon cache, not a bad build**.
  Confirm the file is actually correct before chasing it: extract its embedded
  icon (`[System.Drawing.Icon]::ExtractAssociatedIcon($exe)`), or copy the exe to
  a *fresh name* (a new path dodges the per-path cache) and look at that.
- Recreating a desktop shortcut is not a cache bust when `IconLocation` keeps
  the same `.ico` path. Prefer
  `iconflow shortcut ... --content-address-icon`: it installs
  `shortcut-icon-<sha12>.ico`, recreates the `.lnk`, and implies `--verify` so
  the actual `IconLocation` is read back. Inspect or extract the Shell-resolved
  icon when delivery is critical. If scripting the digest yourself,
  feature-detect `Get-FileHash` or use .NET SHA-256.
- Only with the user's explicit approval, and only after proving the source and
  shortcut are correct, use disruptive cache recovery as a last resort: delete
  `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db` plus `IconCache.db`,
  run `ie4uinit.exe -ClearIconCache`, and restart `explorer.exe`. Prefer the
  content-addressed shortcut path because it does not disturb the desktop session.
- If the project regenerates icons with its own Pillow script (not this toolkit),
  pack the multi-size `.ico` from the **largest** frame as the base image —
  Pillow's ICO writer drops any requested size larger than the base, silently
  yielding a 16px-only icon.
- For a tray icon that **recolors by state**, render it from ONE shared mark
  function used by both the built static icons and the live recolor path, so they
  can't drift.
