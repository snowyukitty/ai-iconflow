<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# AGENTS.md — how an AI agent uses IconFlow

You are the **designer**. IconFlow gives you a design playbook, reusable SVG
building blocks, and a deterministic engine that turns ONE SVG into every icon
format — plus a render-and-review loop so you can see and fix your work before
shipping. This file is the contract for Claude, Codex, and any other agent.

## The procedure (follow in order)

Before step 0, resolve the runner. `python -m iconflow` below means the
`iconflow` command on PATH when the package is installed (`uv tool install
iconflow`, `pipx install iconflow`, or `pip install iconflow` — once
published on PyPI); from a source checkout use that checkout's venv interpreter
(`.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on POSIX). Run
`-m iconflow setup` once if needed, and use that one runner for every command
below. When invoked from another repository, keep the shell in the consuming
project so its config and final sources land there; use absolute paths for
toolkit docs and `work/<slug>/` drafts. See *Environment* for both modes.

0. **Read** `docs/LEARNINGS.md` — the rules distilled from every previously
   shipped icon. This is what makes the system self-evolving: past mistakes
   are only worth their cost if you apply them now. Optionally run
   `python -m iconflow case stats` to see the current weakest axis and any
   house-cliché warning before you start. Treat that signal as diagnostic; it
   does not itself authorize editing this shared toolkit.
1. **Read** `docs/DESIGN_PLAYBOOK.md`. From the consuming project, create its
   `iconflow.toml` with `python -m iconflow init --out iconflow.toml`, then
   record the app intent, user job, one-word
   essence, personality, existing brand palette, clichés, signature-device
   hypothesis, and exact output targets. A visual decision without a product
   job is not a complete brief. For privacy-sensitive work, reduce the brief to
   a neutral user-job verb rather than a sensitive category noun.
2. **Diverge for distinctiveness** (`docs/CONCEPTING.md`) — DO NOT skip; this is
   why most AI icons look generic. Generate 4+ concepts via different lenses,
   apply the cliché filter, add ONE signature device. Draft 2–3 finalist SVGs.
3. **Bake-off** the finalists:
   `python -m iconflow compare a.svg b.svg c.svg --out bake.png` →
   **Read `bake.png`**, run the silhouette + row tests, promote the most
   distinctive-yet-legible winner to `master.svg`. Run the name-the-thing test
   at both 128px and 16px; change the viewpoint if the noun changes. With color
   removed, test vertical cuts above detached round accents as punctuation and
   offset their centerlines by at least two output pixels (~128 viewBox units).
   (Shortcut for simple jobs: inspect the current catalog with
   `python -m iconflow styles`, start with
   `python -m iconflow new <preset>`, and still apply a signature device.)
4. **Author the SVG** by editing `master.svg`, using `docs/SVG_TECHNIQUES.md`
   (§10 = signature devices, §11 = semantic source/target variants). One bold
   idea, on the 1024 grid, inside the safe area. If a full-card app icon also
   needs a tray target, author a linked mark-only `tray.svg`; do not assume its
   card alpha is a meaningful menu-bar silhouette.
5. **Check + review:**
   `python -m iconflow check master.svg` → fix every warning. With a linked
   tray source, add `--tray-svg tray.svg --tray-template-mode <mode>`: it audits
   the macOS template the build will emit and reports one that kept none of the
   colour mark's features.
   `python -m iconflow review --config iconflow.toml --html review.html` →
   **Read `review.png` and open the Review Lab**. Inspect actual-size pixels,
   visual silhouette, alpha footprint, adaptive crops, and every selected
   target transform. Score against `docs/REVIEW_CHECKLIST.md` and export the
   JSON receipt. Distinctiveness is a gate—do not ship below 4/5 on it. If any
   axis <4, make the one change that helps most and re-render. Usually 2–3 passes.
   If managed browser policy blocks the Lab, inspect the static sheet and exact
   target assets at real sizes, then use a complete source-hash-bound approved
   fallback; record the blocked interactive check honestly and keep every gate.
6. **Ship** into the consuming project:
   `python -m iconflow ship --config iconflow.toml --review master-review.json`.
   `ship` re-runs automated QA, verifies the receipt belongs to the current SVG,
   tray source, selected targets, colors, scheme, radius, and template mode, and
   requires all six axes ≥4. The low-level `build`
   command remains for callers that own an equivalent quality gate. See
   `docs/OUTPUT_TARGETS.md` for the exact target file sets.
7. **Report** the brief essence, the cliché avoided, the signature device chosen,
   final rubric scores, and the produced file list.
8. **Record the case** (mandatory — this closes the self-evolution loop):
   `python -m iconflow case new --slug <slug> --essence <word> --device "..." --device-family <family> --device-detail "..." --concept-lens <lens> --cliche "..." --first "legibility=3 ..." --final "legibility=4 ..." --iterations N --lesson "..."`
   then fill in the created file's *Summary* / *What failed first* sections.
   Run `python -m iconflow case lint`, `case stats`, and (for a visual audit)
   `case atlas`. If stats says **DISTILL NOW** or flags an evolution target,
   edit the shared toolkit only when the current work supplies new,
   generalizable evidence and shared-toolkit writes are in scope. Otherwise
   report the signal to the owner. When authorized, follow `docs/EVOLUTION.md`
   and fold the lessons into the docs before ending.
   Public cases from privacy-sensitive work use neutral labels and omit sensitive
   category nouns, private repository names, local paths, and identifying
   operational details while preserving reusable visual evidence.

## Working files
Put draft SVGs, bake sheets, and review renders in `work/<slug>/` (gitignored),
not the repo root — e.g. `work/myapp/a.svg`, `work/myapp/bake.png`. The final
`master.svg` belongs in the consuming project; the case file in `casebook/`.

## Non-negotiables
- Always run **review** and actually inspect both the static sheet and selected
  target contexts before shipping. An icon is judged at 16px and after platform
  transforms, not at the size you draw it.
- Keep the editable `master.svg` in the project (it's the source of truth; rebuild
  any time).
- Don't ship if `check` has warnings, the receipt does not match the current
  source/targets, or any rubric axis <4/5.
- Don't end a session without recording the case (`iconflow case new`) — an
  unrecorded icon teaches the system nothing.

## Environment
- Needs Python 3.10+ + Playwright Chromium + Pillow. Two ways to have the runner:
  - **PATH install (primary, once `iconflow` is published on PyPI):**
    `uv tool install iconflow`, `pipx install iconflow`, or
    `pip install iconflow` in a venv. Then `iconflow` (≡ `python -m iconflow`)
    is on PATH; run `iconflow setup` once (the only network step) and
    `iconflow doctor` to prove the environment. Every document this file cites
    is packaged with the wheel and served by the CLI: `iconflow docs` lists
    them, `iconflow docs DESIGN_PLAYBOOK` prints one, and
    `iconflow docs --out ./iconflow-docs` exports the set. No checkout needed.
  - **Checkout / contributor (editable) mode — the only mode until PyPI is live:**
    clone the repository and run `scripts/setup.ps1` (Windows) or
    `scripts/setup.sh` (macOS/Linux). Each creates `.venv`, installs the checkout
    editable into it, runs `iconflow setup`, and installs the open Agent Skill
    into the common personal discovery locations. Use that venv interpreter
    (`.venv\Scripts\python.exe` / `.venv/bin/python`) as the runner.
- One-time `python -m iconflow setup` installs the Chromium runtime in either mode.
- Pure stdlib + two pip deps. No API keys, no external services, fully offline.
- Rendering runs network-isolated with page JavaScript, external resources, and
  animation disabled. Treat a safety warning as source content to remove, not a
  renderer feature to re-enable.
- Machine consumers (CI, other agents) read `--json` envelopes and the 0/1/2 exit
  codes from `docs/AGENT_CONTRACT.md`; the PR Proof action in
  `docs/PROOF_ACTION.md` is the reference consumer.

## Invocation from another project
With a PATH install nothing else is needed: run `iconflow ...` from the
consuming repository; its `iconflow.toml`, `master.svg`, receipt, and casebook
stay there.

From a checkout, the smoothest cross-project use is still the toolkit venv,
which the setup scripts already install editable:
```
path\to\iconflow\.venv\Scripts\python.exe -m iconflow ...
```
(or `python -m pip install -e path\to\iconflow` into any other interpreter).
If it is not installed editable, run commands from the `iconflow` checkout and
pass absolute paths to candidate SVGs and output files.

For Windows desktop shortcuts, prefer the high-level helper when launching a
PowerShell script:
```
python -m iconflow shortcut --powershell-script D:\app\launch.ps1 \
  --icon D:\app\icons\build\icon.ico --name "My App" --out desktop --verify
```
`--verify` reads the `.lnk` back after creation, which catches quoting and CJK
path issues immediately. Add `--content-address-icon` for delivery: it copies the
icon to `shortcut-icon-<sha12>.ico`, points the shortcut at the immutable alias,
and implies `--verify`, avoiding Explorer's stale path-keyed icon pixels.

## Getting this procedure into another agent

The procedure above ships as an open-format Agent Skill so a session in some
other repository follows the same gates without being handed this file.

- **Claude Code** — install the plugin, which carries the skill plus the
  `/iconflow:icon` and `/iconflow:setup` commands:

  ```
  /plugin marketplace add snowyukitty/ai-iconflow
  /plugin install iconflow@iconflow
  ```

- **Codex, Copilot, and other Agent Skills clients** — `iconflow skill install`
  deploys `SKILL.md` into `~/.claude/skills/`, `~/.agents/skills/`, and
  `~/.copilot/skills/` straight from the installed package; `--project` writes
  into the current repository instead. Both the setup scripts and a wheel
  install use this one code path, so a deployed copy never drifts from the
  canonical `skills/iconflow/SKILL.md`. Edit the canonical source and rerun the
  installer rather than editing a deployed copy.
- **Anything else** — `iconflow skill print` writes the whole procedure to
  stdout, and every agent can follow this file and call the same CLI.
