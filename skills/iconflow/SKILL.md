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

0. **Read** `<AI_PROJECTS>/ai-iconflow/docs/LEARNINGS.md` (rules distilled from
   every previously shipped icon) and run `python -m iconflow case stats` —
   apply the flagged evolution target and avoid any house-cliché signature
   device it warns about.
1. **Read** `<AI_PROJECTS>/ai-iconflow/docs/DESIGN_PLAYBOOK.md`, then
   `python -m iconflow init` to create `iconflow.toml`. Record the brief in it:
   app intent, user job, one-word essence, brand color (pull from the target
   project's existing CSS/theme if present), personality, clichés to avoid,
   signature-device hypothesis, and exact output targets. A visual decision
   without a product job is not a complete brief.
2. **cd** into `<AI_PROJECTS>/ai-iconflow` and use its venv python
   (`.venv\Scripts\python.exe`) if present, else `python`. First time only:
   `python -m iconflow setup`.
3. **Diverge for distinctiveness** (`docs\CONCEPTING.md`) — generate 4+ concepts
   via different lenses, apply the cliché filter, add ONE signature device.
   **Distinctiveness = specificity:** the mark must BE a specific object whose
   silhouette names a thing (a tag, a gem, a folded map, a cat), not a bare
   letter on a gradient tile (the *monogram trap*). Study CONCEPTING's exemplar
   gallery first, and apply the name-the-thing test in the bake-off.
   Draft 2–3 finalist SVGs (or start from a preset and add a signature device:
   `python -m iconflow new <gradient-glow|flat-geometric|line-mark|mascot> --out master.svg`).
4. **Bake-off:** `python -m iconflow compare a.svg b.svg c.svg --out bake.png` →
   **Read `bake.png`**, run the silhouette + row tests, promote the most
   distinctive-yet-legible winner to `master.svg`.
5. **Author** `master.svg` using `docs\SVG_TECHNIQUES.md` (§10 signature devices).
6. **Check + review (mandatory):**
   - `python -m iconflow check master.svg` → fix every warning.
   - `python -m iconflow review --config iconflow.toml --html review.html` →
     **Read `review.png` and open the Review Lab** (actual-size pixels,
     silhouette strip, alpha footprint, adaptive crops, target transforms).
     Score vs `docs\REVIEW_CHECKLIST.md` and export the JSON receipt.
     Distinctiveness is a gate — don't ship below 4/5. If any axis < 4, make the
     single highest-impact change and re-render. ~2–3 passes.
7. **Ship** into the consuming project:
   `python -m iconflow ship --config iconflow.toml --review master-review.json`.
   `ship` re-runs QA, verifies the receipt matches the current SVG / tray source
   / targets / colors / scheme / radius / template, and requires all six axes
   ≥4. (The low-level `build` command remains for callers that own an equivalent
   quality gate.) See `docs\OUTPUT_TARGETS.md` for the exact target file set.
8. **Keep `master.svg`** in the project and **report** the cliché avoided, the
   signature device, final rubric scores + the produced file list.
9. **Record the case (mandatory — closes the self-evolution loop):**
   `python -m iconflow case new --slug <slug> --essence <word> --device "..." --device-family <family> --device-detail "..." --concept-lens <lens> --cliche "..." --first "legibility=3 ..." --final "legibility=4 ..." --iterations N --lesson "..."`,
   fill in the created file's *Summary* / *What failed first*, then run
   `python -m iconflow case lint`, `case stats`, and (for a visual audit)
   `case atlas`. If stats says **DISTILL NOW** or flags an evolution target,
   follow `docs\EVOLUTION.md` (promote lessons into `docs\LEARNINGS.md` / the
   playbook, flip lesson checkboxes to `[x]`).

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
- To refresh the display: delete
  `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db` + `IconCache.db`,
  run `ie4uinit.exe -ClearIconCache`, restart `explorer.exe`; touching the file's
  mtime nudges a stuck per-file icon. The most reliable user-facing fix for a
  desktop **shortcut** is to delete and recreate it.
- If the project regenerates icons with its own Pillow script (not this toolkit),
  pack the multi-size `.ico` from the **largest** frame as the base image —
  Pillow's ICO writer drops any requested size larger than the base, silently
  yielding a 16px-only icon.
- For a tray icon that **recolors by state**, render it from ONE shared mark
  function used by both the built static icons and the live recolor path, so they
  can't drift.
