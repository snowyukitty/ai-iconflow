# AGENTS.md — how an AI agent uses IconFlow

You are the **designer**. IconFlow gives you a design playbook, reusable SVG
building blocks, and a deterministic engine that turns ONE SVG into every icon
format — plus a render-and-review loop so you can see and fix your work before
shipping. This file is the contract for Claude, Codex, and any other agent.

## The procedure (follow in order)

0. **Read** `docs/LEARNINGS.md` — the rules distilled from every previously
   shipped icon. This is what makes the system self-evolving: past mistakes
   are only worth their cost if you apply them now. Optionally run
   `python -m iconflow case stats` to see the current weakest axis and any
   house-cliché warning before you start.
1. **Read** `docs/DESIGN_PLAYBOOK.md`. Create `iconflow.toml` with
   `python -m iconflow init`, then record the app intent, user job, one-word
   essence, personality, existing brand palette, clichés, signature-device
   hypothesis, and exact output targets. A visual decision without a product
   job is not a complete brief.
2. **Diverge for distinctiveness** (`docs/CONCEPTING.md`) — DO NOT skip; this is
   why most AI icons look generic. Generate 4+ concepts via different lenses,
   apply the cliché filter, add ONE signature device. Draft 2–3 finalist SVGs.
3. **Bake-off** the finalists:
   `python -m iconflow compare a.svg b.svg c.svg --out bake.png` →
   **Read `bake.png`**, run the silhouette + row tests, promote the most
   distinctive-yet-legible winner to `master.svg`.
   (Shortcut for simple jobs: start from a preset
   `python -m iconflow new <gradient-glow|flat-geometric|line-mark|mascot>` and
   still apply a signature device.)
4. **Author the SVG** by editing `master.svg`, using `docs/SVG_TECHNIQUES.md`
   (§10 = signature devices, §11 = semantic source/target variants). One bold
   idea, on the 1024 grid, inside the safe area. If a full-card app icon also
   needs a tray target, author a linked mark-only `tray.svg`; do not assume its
   card alpha is a meaningful menu-bar silhouette.
5. **Check + review:**
   `python -m iconflow check master.svg` → fix every warning.
   `python -m iconflow review --config iconflow.toml --html review.html` →
   **Read `review.png` and open the Review Lab**. Inspect actual-size pixels,
   visual silhouette, alpha footprint, adaptive crops, and every selected
   target transform. Score against `docs/REVIEW_CHECKLIST.md` and export the
   JSON receipt. Distinctiveness is a gate—do not ship below 4/5 on it. If any
   axis <4, make the one change that helps most and re-render. Usually 2–3 passes.
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
   follow `docs/EVOLUTION.md` and fold the lessons into the docs before ending.

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
- Needs Python + Playwright Chromium + Pillow. One-time: `python -m iconflow setup`
  (or `scripts/setup.ps1` on Windows), which installs the Chromium runtime.
- Pure stdlib + two pip deps. No API keys, no external services, fully offline.
- Rendering runs network-isolated with page JavaScript, external resources, and
  animation disabled. Treat a safety warning as source content to remove, not a
  renderer feature to re-enable.

## Invocation from another project
This repo is self-contained. For the smoothest cross-project use, install it
editable once into the toolkit venv:
```
path\to\ai-iconflow\.venv\Scripts\python.exe -m pip install -e path\to\ai-iconflow
```

Then agents can call `python -m iconflow ...` from any consuming repo. If it is
not installed editable, run commands from the `ai-iconflow` checkout and pass
absolute paths to candidate SVGs and output files.

For Windows desktop shortcuts, prefer the high-level helper when launching a
PowerShell script:
```
python -m iconflow shortcut --powershell-script D:\app\launch.ps1 \
  --icon D:\app\icons\build\icon.ico --name "My App" --out desktop --verify
```
`--verify` reads the `.lnk` back after creation, which catches quoting and CJK
path issues immediately.

Claude Code users also get the global `/iconflow` skill (see README).
