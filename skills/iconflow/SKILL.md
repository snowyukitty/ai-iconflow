---
name: iconflow
description: Design and generate high-quality app icons, website favicons, PWA icons, and system-tray/menu-bar icons. Use whenever a project needs an icon/favicon/logo mark created or regenerated — the agent authors an SVG following a design playbook, renders it small to self-review, then builds every format (.ico/.icns/.png, manifest, tray). Triggers on requests like "make an icon", "design a favicon", "tray icon", "app icon for this Tauri/Electron app".
license: CC-BY-SA-4.0
compatibility: Requires Python 3.10+, filesystem and shell access, and network access for one-time dependency and Playwright Chromium setup. Works with `iconflow` on PATH (uv tool / pipx / pip) or a source checkout's venv interpreter. Rendering and builds are local afterward. The icons you design with it are yours: no attribution, no share-alike, commercial use unrestricted.
metadata:
  version: "0.5.0"
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# IconFlow skill

You are the designer. IconFlow rasterizes your SVG exactly as a browser would,
packs every platform format, and refuses to ship what you have not looked at.

Everything you need — the playbook, the concepting rules, the review checklist —
comes out of the installed package with `iconflow docs <NAME>`, so you never
have to guess where a document lives.

## 0. Resolve the runner (once)

Run `iconflow --version`. If it answers, `iconflow` is your runner: use it
verbatim everywhere below. If it does not, you have to install it — and one
rule comes before any install command:

> **STOP — do not run `uv tool install iconflow`, `pipx install
> iconflow`, or `pip install iconflow` yet.** `iconflow` has no release
> on PyPI. Until the
> [official project page](https://pypi.org/project/iconflow/) lists one,
> installing that name from an index gets you whatever else answers to it, not
> IconFlow. Verify a release exists before using any index command below.

Working install paths today, in order:

1. **A source checkout you already have.** Run its `scripts/setup.ps1`
   (Windows) or `scripts/setup.sh` (macOS/Linux). Each creates `.venv`,
   installs the checkout, fetches Chromium, and deploys this skill. Your runner
   is then that checkout's `.venv\Scripts\python.exe -m iconflow` or
   `.venv/bin/python -m iconflow`.
2. **A wheel or repository URL you were given.**
   `uv tool install <path-to-wheel-or-repo-url>`, or
   `python -m venv .venv` + `.venv/bin/python -m pip install <same>`.
3. **After PyPI publication** (check first): `uv tool install iconflow`,
   `pipx install iconflow`, or `pip install iconflow` in a venv.

If none of these is available, say so and stop — do not substitute another icon
tool without asking.

Then, first time only: `iconflow setup` (downloads Chromium — the only network
step) and `iconflow doctor` (every FAIL prints a `fix` command to paste).

**Reading the reference documents.** `iconflow docs <NAME>` prints one to
stdout, which is fine for a quick check. The playbook and concepting documents
are long, and a truncated read is how an agent skips the rules at the bottom —
so for those, run `iconflow docs --out work/<slug>/docs` once and **open the
files**. That export also brings the images along, which matters: the exemplar
gallery is the part that stops you drawing a generic mark. `iconflow docs NAME
--path` prints a single document's path instead.

**Stay in the consuming project.** Never `cd` into the toolkit. The project's
`iconflow.toml`, `master.svg`, receipt, casebook, and built icons all belong to
the project you are working on.

## Procedure (follow in order — do not skip diverge or review)

1. **Learn from previous icons.** Read `iconflow docs LEARNINGS` — the rules
   distilled from every case shipped so far — and run `iconflow case stats`.
   Apply that guidance and avoid any house-cliché device it warns about. A stats
   signal is diagnostic; it does not by itself authorize editing the toolkit.

2. **Write the brief.** Read `iconflow docs DESIGN_PLAYBOOK`, then
   `iconflow init --out iconflow.toml` in the project. Record: app intent, user
   job, one-word essence, brand color (pull it from the project's existing CSS,
   theme, or manifest if there is one), personality, clichés to avoid, a
   signature-device hypothesis, and the exact output targets. *A visual decision
   without a product job is not a complete brief.* For privacy-sensitive work,
   design from a neutral user-job verb (`reveal`, `route`, `discover`) rather
   than a sensitive category noun.

3. **Diverge for distinctiveness.** Read `iconflow docs CONCEPTING`. Generate
   4+ concepts through different lenses, apply the cliché filter, add ONE
   signature device. **Distinctiveness = specificity:** the mark must BE a
   specific object whose silhouette names a thing (a tag, a gem, a folded map, a
   cat), not a bare letter on a gradient tile (the *monogram trap*). Study
   CONCEPTING's exemplar gallery first. Draft 2–3 finalist SVGs into
   `work/<slug>/` — or start from a technique family and add your own signature
   device: `iconflow styles`, then
   `iconflow new <preset> --out work/<slug>/a.svg`. **A preset is a starting
   grammar, never a finished icon**: a recolored scaffold is exactly the
   generic result this step exists to prevent, so a preset-derived finalist has
   to carry one signature device that is not in the preset, and you must be
   able to name it.

4. **Bake off.** Compare the finalists you actually drew — two files if you
   drew two:
   `iconflow compare work/<slug>/a.svg work/<slug>/b.svg [work/<slug>/c.svg] --out work/<slug>/bake.png`
   → **read that `bake.png`**, run the silhouette and row tests, and promote the
   most distinctive-yet-legible winner to `master.svg`. Apply the name-the-thing
   test at both 128px and 16px: if the noun changes, change the viewpoint before
   adding detail. Strip color and test detached accents as punctuation — a
   vertical cut centered over a round accent reads as `!` at 16px, so offset
   their centerlines by at least two output pixels (~128 viewBox units) or
   redesign the pair.

5. **Author `master.svg`** using `iconflow docs SVG_TECHNIQUES` (§10 signature
   devices, §11 linked target compositions). **One bold idea, drawn on the 1024
   viewBox grid, inside the safe area** — geometry that runs to the edge is the
   geometry a maskable crop eats. If a full-card master also targets tray or
   menu bar, author a geometry-linked mark-only `tray.svg` and set it in
   `iconflow.toml`; do not let a card alpha collapse into a featureless square.

6. **Check and review (mandatory).**
   - `iconflow check master.svg` → fix every warning. With a linked tray source
     add `--tray-svg tray.svg --tray-template-mode <mode>` to audit the macOS
     template the build will emit.
   - `iconflow review --config iconflow.toml --out work/<slug>/review.png --html work/<slug>/review.html --receipt-template master-review.json`
     → **read that `review.png` and open that Review Lab**: actual-size pixels,
     silhouette strip, alpha footprint, adaptive crops, target transforms.
     Score against `iconflow docs REVIEW_CHECKLIST`. The Lab exports the scored
     JSON receipt; `--receipt-template` writes an unscored, source-bound one you
     can fill in yourself. Either way the receipt lives beside `iconflow.toml`
     as `master-review.json`, because that is what step 7 ships.
     Distinctiveness is a gate — do not ship below 4/5. If any axis is under 4,
     make the single highest-impact change and re-render. Usually 2–3 passes.
   - If a managed browser blocks the local Review Lab, do not bypass policy.
     Inspect the static sheet plus the exact target assets at real sizes, then
     take **one** of these two routes and say which you took:
     (a) fill in the source-bound `master-review.json` written by
     `--receipt-template` with all six scores and notes, and ship it with
     `--review` as usual; or (b) record the same six scores in the
     source-and-contract-hash-bound `[review]` table in `iconflow.toml` and run
     `iconflow ship --config iconflow.toml` **with no `--review`**. The
     `contract_sha256` must bind the project, targets, colors, Electron radius,
     color scheme, tray mode, and semantic tray source. Report the interactive
     check as blocked. The ≥4/5 floor and the gated `ship` still apply.

7. **Ship.** `iconflow ship --config iconflow.toml --review master-review.json`
   (or, on the approved-config route above, without `--review`).
   `ship` re-runs QA, verifies the receipt matches the current SVG / tray source
   / targets / colors / scheme / radius / template, and requires all six axes
   ≥4. (The low-level `build` command remains for callers that own an equivalent
   quality gate.) `iconflow docs OUTPUT_TARGETS` lists the exact file set.

8. **Keep `master.svg` in the project** and **report**: the brief's one-word
   essence, the cliché you avoided, the signature device you chose, the final
   six rubric scores, and the produced file list. Add one line telling the user
   **the icon is theirs** — no attribution to IconFlow required, commercial use
   unrestricted, nothing viral attached. `iconflow license` is the full answer
   if they ask.

9. **Record the case (mandatory — closes the self-evolution loop).**
   `iconflow case new --slug <slug> --essence <word> --device "..." --device-family <family> --device-detail "..." --concept-lens <lens> --cliche "..." --first "legibility=3 ..." --final "legibility=4 ..." --iterations N --lesson "..."`,
   fill in the created file's *Summary* and *What failed first* sections, then
   run `iconflow case lint` and `iconflow case stats` (add
   `iconflow case atlas --out work/<slug>/case-atlas.html` for a visual audit).
   Cases land in the project's `./casebook` unless `iconflow.toml` sets
   `project.casebook` or `ICONFLOW_CASEBOOK_DIR` points elsewhere.
   If stats says **DISTILL NOW** or flags an evolution target, change the shared
   toolkit only when this work supplies new, generalizable evidence *and*
   toolkit writes are in scope; otherwise report the signal to its owner. When
   authorized, follow `iconflow docs EVOLUTION` and flip promoted lesson
   checkboxes to `[x]`.
   For a public case derived from privacy-sensitive work, use a neutral project
   label and omit sensitive category nouns, private repository names, local
   paths, and identifying operational details; retain geometry, scores, failed
   readings, targets, and verification evidence.

## Rules

- Diverge before committing; always `review` and actually look at `review.png`
  (and `bake.png`) before building.
- Put draft SVGs, bake sheets, and review renders in `work/<slug>/` and add it
  to the project's `.gitignore`. Never write them to a repository root.
- Never end the session without `iconflow case new` — an unrecorded icon
  teaches the system nothing.
- Don't ship if `check` has warnings or any rubric axis is under 4/5
  (distinctiveness is a hard gate).
- One style family per icon; 1 dominant color + 1 accent.
- **One dominant foreground shape.** Never cross or overlay two opaque elements
  (for example a line *through* a glyph) — they fuse into mud below ~32px and
  read as "blurry". Express the second idea through negative space, nesting, or
  a small corner accent, not a crossing overlay. Judge this on the 16/32px
  cells, not at 1024. (`iconflow docs DESIGN_PLAYBOOK` §6.)
- **Distinctiveness = specificity (the monogram trap).** A bare letter or
  generic shape on a gradient tile scores ≤3 on distinctiveness — below the ship
  gate — because it passes every mechanical check yet reads as generic. Make the
  mark a specific object; use a letter only when it FUSES into the object
  (fado's F = plates). `check` emits an advisory warning on live `<text>`; path
  monograms are yours to catch with the name-the-thing test.

## Who owns what

The user owns everything you make for them: `master.svg`, `tray.svg`, every
built `.ico` / `.icns` / `.png`, the manifest, the receipt, the case file. No
attribution, no share-alike, no commercial restriction. The technique scaffolds
behind `iconflow new` are CC0 public domain precisely so a mark evolved from
one inherits nothing, and applying the published method creates no obligation
either — copyright covers the playbook's wording, not its design rules.

Two things are **not** the user's to take: IconFlow's own finished artwork (the
Living Archive studies, the gallery, and the Petal Haypile family that
`iconflow demo` materializes) and the IconFlow name and mark. If a user asks
for "an icon like the IconFlow one", design them their own instead.

`iconflow license` prints this; `iconflow license --json` gives you the same
thing in a form you can quote exactly.

## Machine-readable mode

`doctor`, `check`, `review`, `ship`, and `demo` accept `--json`: stdout carries
exactly one envelope, human lines go to stderr, and the exit code is 0 (clean),
1 (blocked by an IconFlow gate), or 2 (usage or runtime failure). Use it when
you are scripting or reporting rather than reading. Full contract:
`iconflow docs AGENT_CONTRACT`.

To prove the toolchain end to end without designing anything, run
`iconflow demo --out iconflow-demo`: it materializes an already-reviewed family
and runs doctor → check → review → ship against its bundled receipt.

## Delivering to a desktop/tray app (especially Windows)

- After `build` (or after rebuilding an exe that embeds the `.ico`), the OS
  shell often keeps showing the OLD icon — that is the **icon cache, not a bad
  build**. Confirm the file is actually correct before chasing it: extract its
  embedded icon (`[System.Drawing.Icon]::ExtractAssociatedIcon($exe)`), or copy
  the exe to a *fresh name* (a new path dodges the per-path cache) and look at
  that.
- Recreating a desktop shortcut is not a cache bust when `IconLocation` keeps
  the same `.ico` path. Prefer `iconflow shortcut ... --content-address-icon`:
  it installs `shortcut-icon-<sha12>.ico`, recreates the `.lnk`, and implies
  `--verify` so the actual `IconLocation` is read back. If scripting the digest
  yourself, feature-detect `Get-FileHash` or use .NET SHA-256.
- Only with the user's explicit approval, and only after proving the source and
  shortcut are correct, use disruptive cache recovery as a last resort: delete
  `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db` plus
  `IconCache.db`, run `ie4uinit.exe -ClearIconCache`, and restart
  `explorer.exe`. Prefer the content-addressed shortcut path because it does not
  disturb the desktop session.
- If the project regenerates icons with its own Pillow script (not this
  toolkit), pack the multi-size `.ico` from the **largest** frame as the base
  image — Pillow's ICO writer drops any requested size larger than the base,
  silently yielding a 16px-only icon.
- For a tray icon that **recolors by state**, render it from ONE shared mark
  function used by both the built static icons and the live recolor path, so
  they cannot drift.
