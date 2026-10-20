<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Workflow — brief to evidence-backed ship

IconFlow separates design intent, visual evidence, and deterministic output so
none of them can silently stand in for the others:

```text
iconflow.toml → concepts → master.svg → check + Review Lab → review receipt → ship → casebook
```

The receipt is the hinge. From 0.8 it carries the render plan — every byte
the build will write — so `ship` can prove the pixels that were reviewed are
the pixels it publishes ([`RENDER_PLAN.md`](RENDER_PLAN.md)); what a receipt
does and does not prove is in [`TRUST.md`](TRUST.md), and how the modules
divide this work is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 1. Create the contract

```bash
iconflow init --name "My App" --user-job "..." --essence proof \
  --targets web,tauri,electron,tray --tray-svg tray.svg
```

Relative paths in `iconflow.toml` resolve from the config file, not the current
shell directory. The tables have distinct roles:

- `[project]`: source, output, and casebook locations;
- `[brief]`: app intent, user job, essence, and personality;
- `[design]`: palette, clichés, signature device, normalized device family,
  execution detail, and winning concept lens;
- `[build]`: selected targets and their transforms, including a semantic tray
  source and template mode;
- `[review]`: an auditable manual fallback for approval, scores, and notes.

## 2. Produce evidence

After the required concept divergence and bake-off:

```bash
iconflow check master.svg --bg "#fff4e8"
iconflow check master.svg --tray-svg tray.svg --tray-template-mode alpha
iconflow review --config iconflow.toml \
  --out work/my-app/review.png --html work/my-app/review.html
```

The static sheet is suitable for terminals and pull requests. The self-contained
Review Lab carries the brief into the decision and previews the exact canonical
maskable, Electron-corner, Tauri desktop, color tray, and macOS template
transforms selected by the config. It has no remote dependencies.

Score all six axes only after inspecting 16px, pixel zoom, silhouette, adaptive
crops, and every selected target. Export the JSON receipt when all axes are at
least 4 and automated warnings are empty.

### Headless review (0.7+)

When no one can open the Lab — an agent session, CI — `review --evidence DIR`
writes the same evidence as sheets plus `findings.json` and the render plan
(`DIR/plan/`), and `iconflow score --evidence DIR` walks the six axes, takes a
score and a reason for each, and writes the receipt. `score` never renders: it
binds the scores to the evidence that was read and refuses evidence that was
edited or is stale (`AGENT_CONTRACT.md` § `score --json`).

### Managed-browser fallback

If a managed browser blocks the local Review Lab, do not weaken or bypass that
policy. Inspect `review.png` plus the exact emitted target assets at actual
16/32px sizes on their relevant light, dark, and transparent contexts. Record
all six scores and review notes in `[review]`, set `status = "approved"`, and
copy both `source_sha256` and `contract_sha256` from the reviewed JSON contract.
The second hash binds the project, exact target set, colors, Electron radius,
color scheme, tray mode, and semantic tray-source hash. Report the interactive
Lab as blocked. This is an evidence-path fallback, not a reduced gate: every
axis still must be at least 4 and `ship` still re-runs QA before writing output.
It is not available when `ios` is among the targets: a `[review]` table names
no pixels, and `ship` refuses an iOS approval without the render plan it
reviewed (`receipt-not-ready`). Use the headless path above instead — it needs
no browser window and binds the plan.

## 3. Ship fail-closed

```bash
iconflow ship --config iconflow.toml --review master-review.json
```

Before writing output, `ship` verifies that the receipt:

- uses the supported schema and contains a full SHA-256 source digest;
- carries a canonical contract digest for newly generated receipts;
- belongs to the current SVG, project name, and exact target set;
- matches the reviewed theme/background colors, raster color scheme, Electron
  radius, tray template mode, and semantic tray-source hash;
- has no automated warnings and has `status: ready`;
- contains every rubric axis with a score of at least 4.

It then re-runs current automated QA against the exact configured maskable
background and only builds after that second gate is clean. A receipt that
carries a render plan (0.8+) is also compared with the plan `ship` renders now:
any difference is `plan-drift` (exit 1) and nothing is written. `ship --plan
DIR/plan` publishes the reviewed bytes themselves instead of rendering again —
how a review made on one machine ships on another. An explicitly
`approved` config with the reviewed `source_sha256`, `contract_sha256`, complete
scores, and review notes is the non-interactive fallback described above (not
for `ios`). `build` is intentionally
lower level for integrations that already own an equivalent quality gate.

## 4. Learn from the delta

```bash
iconflow case new ...
iconflow case lint
iconflow case stats
iconflow case atlas --out case-atlas.html
```

The compact stats report drives automation; the dependency-free atlas makes
first→final score movement, taxonomy concentration, status, and undistilled
lessons visible to people. Follow `EVOLUTION.md` whenever either surface flags
an evolution target or `DISTILL NOW`.

## Machine output

`doctor`, `check`, `review`, `ship`, and `demo` accept `--json`. Stdout then
carries exactly one envelope (`schema`, `command`, `status`, `exit_code`,
`warnings`, `advisories`, `outputs`, `errors`) and every human line moves to
stderr, so an agent or CI job reads codes such as `stroke-floor` or
`receipt-stale-source` instead of prose. Exit codes mean the same thing with or
without `--json`: `0` completed (advisories allowed), `1` blocked by an IconFlow
gate (QA warnings, stale receipt, axis < 4, doctor FAIL), `2` usage,
configuration, or runtime failure. `review --receipt-template receipt.json`
also writes an unscored receipt bound to the current source and contract, which
an agent fills in and hands to `ship --review`. The frozen shape, the warning
codes, and the optional Review Packet fields are in
[`AGENT_CONTRACT.md`](AGENT_CONTRACT.md); `iconflow demo --out DIR` runs the
whole loop on the packaged brand family.

## Security and determinism

SVG is treated as untrusted render input. Before Chromium sees it, IconFlow
requires well-formed UTF-8 XML with an `<svg>` root, rejects DTD/entity
declarations, and caps input at 4 MiB, 50,000 elements, and 128 nesting levels.
Chromium runs with network and service workers blocked, page JavaScript disabled,
active/animated SVG content removed or frozen, and sRGB/locale/timezone fixed.
QA reports active or external content so a designer removes it from the source
rather than depending on disabled behavior. Every emitted PNG is decoded and
dimension-checked before packaging. Build output rejects existing symlinks,
junctions, and Windows reparse points instead of following them.
