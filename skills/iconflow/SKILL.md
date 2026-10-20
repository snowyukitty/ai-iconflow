---
name: iconflow
description: Design and generate high-quality app icons, website favicons, PWA icons, Android adaptive/themed launcher icons, iOS/iPadOS app icons (light, dark, tinted), and system-tray/menu-bar icons, then propagate the approved mark into a brand kit (lockups, store tiles, Open Graph and social cards). Use whenever a project needs an icon/favicon/logo mark created or regenerated — the agent authors an SVG following a design playbook, renders it small to self-review, then builds every format (.ico/.icns/.png, manifest, Android res/, tray). Triggers on requests like "make an icon", "design a favicon", "tray icon", "app icon for this Tauri/Electron app", "Android launcher icon", "iOS app icon / dark and tinted icon", "OG image / social card for our logo".
license: CC-BY-SA-4.0
compatibility: Requires Python 3.10+, filesystem and shell access, and network access for one-time dependency and Playwright Chromium setup. Works with `iconflow` on PATH (uv tool / pipx / pip) or a source checkout's venv interpreter. Rendering and builds are local afterward. The icons you design with it are yours: no attribution, no share-alike, commercial use unrestricted.
metadata:
  version: "0.10.1"
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
verbatim everywhere below. If it does not, install it — preferring, in order:

1. `uv tool install iconflow`
2. `pipx install iconflow`
3. a venv: `python -m venv .venv` then `.venv/bin/python -m pip install iconflow`
   (`.venv\Scripts\python.exe` on Windows). Your runner is then that
   interpreter followed by `-m iconflow` — substitute it for `iconflow` in
   every command below.

Working from a source checkout instead? Run its `scripts/setup.ps1` or
`scripts/setup.sh` and use the `.venv` interpreter it creates.

If none of these is available, say so and stop — do not substitute another icon
tool without asking.

Then, first time only: `iconflow setup` (downloads Chromium — the only network
step) and `iconflow doctor` (every FAIL prints a `fix` command to paste).

**A command or flag below that the runner does not know means the installed
toolkit predates it** (`score`, `budget`, `brand`, `review --evidence` and the
`android` target arrived in 0.7; the `ios` target in 0.10). Upgrade it — `uv tool upgrade iconflow` or
`pipx upgrade iconflow` — and say so; never improvise a substitute for a gate.

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
   `iconflow init --out iconflow.toml` in the project (it detects the targets
   from the project files and says why; check them). Record: app intent, user
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
   redesign the pair. `compare` then prints each finalist's **16px budget**:
   cuts under 128 units, gaps that fuse, thin accents, and how many cuts and
   parts survive at 16px (`iconflow budget <finalists> --sheet
   work/<slug>/budget.png` rings them; `iconflow docs LEGIBILITY_BUDGET`). It
   advises and never gates; act on it now, while changing the concept is cheap.

4c. **Run the neighbourhood on every finalist** (mandatory for the winner):
   `iconflow neighbours <finalist>.svg --config iconflow.toml --sheet work/<slug>/neighbours.png`
   → **read that sheet**. It puts the candidate beside the known marks it is
   nearest to at real 16px — a bundled collision set of generic forms (bar
   chart, bell, `#`, letters) and IconFlow's own corpus — with distances. A
   finalist inside the radius of a generic form is L9's silhouette-collision
   kill made visible: redesign it, never widen the radius. Put the marks this
   product must not resemble under `[neighbours] avoid` in `iconflow.toml`
   (`"@collision"` promotes the generic forms); only that set gates, the
   bundled corpus advises. Not a clearance check; `iconflow docs NEIGHBOURHOOD`.

4d. **For a set of marks** — a suite of app icons, a toolbar, an emote pack —
   also run `iconflow family "<set>/*.svg" --sheet work/<slug>/family.png` and
   **read that sheet**. Members that share a carrier (a plate, a head) are
   compared on what the carrier does not explain; two that are one mark at
   16px are `family-twins` (exit 1). Change what tells them apart, never only
   their colour. Emotes are built with `--targets emote` (Twitch 28/56/112,
   Discord/Slack 128, upload limits enforced) and judged at 22–28px on light
   and dark chat. `iconflow docs FAMILY`, `iconflow docs EMOTES`.

5. **Author `master.svg`** using `iconflow docs SVG_TECHNIQUES` (§10 signature
   devices, §11 linked target compositions). **One bold idea, drawn on the 1024
   viewBox grid, inside the safe area** — geometry that runs to the edge is the
   geometry a maskable crop eats. If a full-card master also targets tray or
   menu bar, author a geometry-linked mark-only `tray.svg` and set it in
   `iconflow.toml`; do not let a card alpha collapse into a featureless square.
   **Android** is never part of `all`; name it (`[build] targets = ["web",
   "android"]`). Its adaptive layer is the maskable composition, so one fix
   serves both: if corner detail dies in the circle crop, set `[build]`
   `maskable_scale` lower (0.5–1.0,
   default 0.8) or link a `maskable_svg` drawn for the crop. Android 13+ tints
   a themed icon from alpha alone, so give it a mark-only `monochrome_svg`
   (falls back to `tray_svg`). `iconflow docs OUTPUT_TARGETS` § android.
   **iOS** (0.10) is never part of `all` either; name it (`"ios"`). Give the
   card `id="iconflow-background"` — one empty shape, the first thing drawn,
   a direct child of `<svg>`, painted by a plain `fill` — and IconFlow
   stretches it to full bleed for the light icon and removes it for the dark
   and tinted ones, after proving by rendering that the mark does not depend
   on it. Without the declaration it ships the light icon alone and iOS
   derives the rest. If the audit says the mark vanishes on the dark home
   screen (`ios-dark-contrast`, `ios-tinted-faint`), link `ios_dark_svg` (the
   mark drawn for a dark ground) or set `ios_variants = "system"`; never
   lighten the master to pass. Keep stylesheets out of a master with a
   declared card. `iconflow docs OUTPUT_TARGETS` § ios.

5b. **Optional — open the detail ladder** if the icon will also be seen large
   (a store listing, a splash, an about box, print). Read
   `iconflow docs DETAIL_LADDER`, then annotate groups with
   `data-lod="glyph mark plate"`, `"mark plate"`, `"plate"`. Every size is then
   rendered from its own rung, and the shipped `favicon.svg` carries a `@media`
   layer that does the same in a browser. **The ladder grows inward**: every
   trait that defines the outer contour stays on the `glyph` rung; the rungs
   above it own only what happens inside it. Audit it with
   `iconflow ladder master.svg --sheet work/<slug>/ladder.png` and **read that
   sheet** — detail must APPEAR as the size grows, never change identity. A
   source with no `data-lod` is flat, which is a valid answer and costs nothing.

6. **Check and review (mandatory).**
   - `iconflow check --config iconflow.toml` → fix every warning. With
     `--config`, `check` runs exactly the audit `review` and `ship` run — the
     configured targets, `background_color`, colour scheme and linked sources —
     so on the same machine a clean `check` means a clean `ship` audit (a
     `ship --plan` elsewhere measures the reviewed bytes instead). `--config` brings the
     `[neighbours]` sets in (`neighbour-collision` gates;
     `neighbour-familiar` and `neighbour-house-rut` advise). With a linked tray
     source add `--tray-svg tray.svg --tray-template-mode <mode>` to audit the
     macOS template the build will emit. A laddered source is also gated here on the
     same-mark invariant (`ladder-*` codes); a flat one never sees it.
   - `iconflow review --config iconflow.toml --out work/<slug>/review.png --html work/<slug>/review.html --receipt-template master-review.json`
     → **read that `review.png` and open that Review Lab**: actual-size pixels,
     silhouette strip, alpha footprint, adaptive crops, target transforms.
     Score against `iconflow docs REVIEW_CHECKLIST`. The Lab exports the scored
     JSON receipt; `--receipt-template` writes an unscored, source-bound one you
     can fill in yourself. Either way the receipt lives beside `iconflow.toml`
     as `master-review.json`, because that is what step 7 ships.
     Distinctiveness is a gate — do not ship below 4/5. If any axis is under 4,
     make the single highest-impact change and re-render. Usually 2–3 passes.
   - **No browser (a headless agent session, a managed browser that blocks
     the Lab)?** Use the headless path, which is the Lab's evidence without
     the Lab and the same gate:
     `iconflow review --config iconflow.toml --evidence work/<slug>/evidence`
     writes the contact sheet, a target-context sheet of the exact shipped
     bytes (maskable crops, tray templates on both bars, Android launchers),
     the ladder and neighbourhood proofs, and `findings.json`. **Read every
     sheet**, then
     `iconflow score --config iconflow.toml --evidence work/<slug>/evidence --scores "legibility=4 ..." --rationale legibility="what you saw, on which sheet" ... --notes "..." --reviewer-name "<you>" --out master-review.json`.
     `score` refuses stale or edited evidence, needs a reason for every axis,
     and records `review_surface.interactive_lab = false` in the receipt. An
     independent reviewer (a different product) may score the same evidence
     into its own receipt; attach it with `--second-opinion`. It is recorded
     and its dissent reported, and it never replaces the ≥4/5 gate.
   - If you must work without even `score`, do not bypass policy.
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
   A receipt from 0.8 on carries the **render plan** the review showed, and
   `ship` refuses (`plan-drift`) when the pixels it would write are not those
   pixels — a toolchain change explains drift, it never approves it. Shipping
   on another machine (CI)? Publish the reviewed bytes themselves:
   `ship --config iconflow.toml --review master-review.json --plan work/<slug>/evidence/plan`.
   Never re-score to make drift go away without looking at the new pixels.
   `iconflow docs RENDER_PLAN`.
   From IconFlow 0.9 the automated audit measures those same plan files (the
   16, 32 and 512 px frames and the maskable composition), so what was audited
   is what was reviewed and what ships; `ship --json` reports it as
   `outputs.plan.audited`, and `outputs.receipt_sha256` names the exact
   receipt it accepted. A receipt proves consistency, not who reviewed: never
   present a self-declared reviewer name as an authentication.

7b. **Optional — propagate the mark** when the product also needs lockups,
   store tiles, or Open Graph / GitHub social cards. Give `[brand]` in
   `iconflow.toml` an **outlined** wordmark (no live `<text>`; `iconflow brand
   outline --text ... --font ...` outlines a permissively licensed font), then
   `iconflow brand build --config iconflow.toml --review master-review.json`
   (add `--ship` to build the icons in the same transaction) and **read
   `brand-sheet.png`**. It accepts only what `ship` accepts. When replacing an
   older mark, `iconflow brand sync --manifest brand-kit --project <site>`
   lists every file still carrying the old one — fix those, do not delete
   blindly. Publishing the cards is the user's step. `iconflow docs BRAND_KIT`.

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

`doctor`, `check`, `review`, `score`, `ship`, `budget`, `ladder`, `neighbours`,
`family`, `brand build|sync|outline`, and `demo` accept `--json`: stdout carries
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
