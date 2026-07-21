# Workflow — brief to evidence-backed ship

IconFlow separates design intent, visual evidence, and deterministic output so
none of them can silently stand in for the others:

```text
iconflow.toml → concepts → master.svg → check + Review Lab → review receipt → ship → casebook
```

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

## 3. Ship fail-closed

```bash
iconflow ship --config iconflow.toml --review master-review.json
```

Before writing output, `ship` verifies that the receipt:

- uses the supported schema and contains a full SHA-256 source digest;
- belongs to the current SVG, project name, and exact target set;
- matches the reviewed theme/background colors, raster color scheme, Electron
  radius, tray template mode, and semantic tray-source hash;
- has no automated warnings and has `status: ready`;
- contains every rubric axis with a score of at least 4.

It then re-runs current automated QA against the exact configured maskable
background and only builds after that second gate is clean. An explicitly
`approved` config with the reviewed `source_sha256` and complete scores is the
non-interactive fallback. `build` is intentionally lower level for integrations
that already own an equivalent quality gate.

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

## Security and determinism

SVG is treated as untrusted render input. Chromium runs with network and service
workers blocked, page JavaScript disabled, active/animated SVG content removed
or frozen, and sRGB/locale/timezone fixed. QA reports active or external content
so a designer removes it from the source rather than depending on disabled
behavior. Every emitted PNG is decoded and dimension-checked before packaging.
