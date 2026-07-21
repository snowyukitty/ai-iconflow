# IconFlow examples

These examples demonstrate the decision workflow, not a gallery of presets.
Keep drafts, bake sheets, and review artifacts in `work/<slug>/`; keep the final
`master.svg`, `iconflow.toml`, and case record with the consuming project.

## 1. Brief → gated multi-target family

Start by recording the user job. This keeps the icon tied to the app's function
instead of the first category glyph that comes to mind.

```bash
python -m iconflow init \
  --name "Evidence Desk" \
  --app-intent "collect sources and turn them into a defensible decision" \
  --user-job "compare evidence without losing provenance" \
  --essence proof \
  --personality precise --personality calm \
  --palette graphite --palette coral \
  --cliche sparkle --cliche checkmark --cliche stacked-documents \
  --signature-device "one asymmetric evidence gate" \
  --device-family ownable-geometry \
  --concept-lens verb-system \
  --targets web,tauri,electron,tray
```

Read `docs/LEARNINGS.md`, `docs/DESIGN_PLAYBOOK.md`, and
`docs/CONCEPTING.md`. Write at least four genuinely different concepts in words;
turn the strongest 2–3 into SVG finalists.

```bash
python -m iconflow compare \
  work/evidence-desk/verb.svg \
  work/evidence-desk/negative-space.svg \
  work/evidence-desk/letterform.svg \
  --out work/evidence-desk/bake.png
```

Read `bake.png`. Choose by 16px legibility and the visual-shape column, then
promote the winner and simplify it once more.

```bash
python -m iconflow check master.svg
python -m iconflow review --config iconflow.toml \
  --out work/evidence-desk/review.png \
  --html work/evidence-desk/review.html
```

After the visual review, score all six axes and export the JSON receipt. Shipping
is deliberately blocked if one score is absent/below 4, the SVG has changed, or
the receipt targets do not match `iconflow.toml`.

```bash
python -m iconflow ship --config iconflow.toml \
  --review master-review.json
```

## 2. Start from a technique family

Presets demonstrate construction; they are not finished logos.

```bash
python -m iconflow new gradient-glow --out work/my-app/a.svg
python -m iconflow new flat-geometric --out work/my-app/b.svg
python -m iconflow new line-mark --out work/my-app/c.svg
python -m iconflow new mascot --out work/my-app/d.svg
```

Replace the IconFlow house rail in every candidate with the consuming app's
user job and one signature device. Do not select a preset merely because its
style looks attractive at 128px; compare the resulting app-specific concepts.

## 3. A static guide launched from Windows

For a local planning or research site, the user's job is often `route`,
`compare`, or `decide`—not the event/category noun. Build web and Electron
assets so the page and desktop entry share one identity.

```bash
python -m iconflow build master.svg --out ./public/icons \
  --targets web,electron --name "Planning Desk" \
  --relative-paths

python -m iconflow shortcut \
  --powershell-script "D:\PlanningDesk\launch-site.ps1" \
  --icon "D:\PlanningDesk\public\icons\build\icon.ico" \
  --workdir "D:\PlanningDesk" \
  --name "Planning Desk" --out desktop --verify
```

The Tokyo Game Show case in
[`casebook/2026-06-19-tgs-planning-site.md`](../casebook/2026-06-19-tgs-planning-site.md)
shows the pattern: a route through a folded guide card beat literal ticket,
gamepad, and expo-badge concepts because it described what the site helped the
user do.

## 4. Full app card + semantic tray source

A full-card app icon can become a featureless macOS template if a pipeline uses
the card's alpha as the tray mark. Prefer a mark-only SVG that shares stable
semantic geometry with the master.

```text
master.svg
  #iconflow-background
  #iconflow-mark
    #iconflow-signature

tray.svg
  #iconflow-mark
    #iconflow-signature
```

[`brand/master.svg`](../brand/master.svg) and
[`brand/tray.svg`](../brand/tray.svg) are the reference implementation. Review
the actual 16px color tray and macOS template outputs, not only the app icon.

```bash
python -m iconflow build master.svg --out ./icon-out \
  --targets web,tauri,electron,tray \
  --name "My App" --tray-svg tray.svg --tray-template-mode auto
```

## 5. Close the case

Record what failed first, not just the polished result. First-pass scores tell
the design system which guidance is not preventing mistakes yet.

```bash
python -m iconflow case new --slug evidence-desk \
  --project "Evidence Desk" --targets web,tauri,electron,tray \
  --essence proof --style flat-geometric \
  --device-family ownable-geometry \
  --device-detail "asymmetric evidence gate with two-pixel counter" \
  --concept-lens verb-system \
  --cliche "sparkle / checkmark / stacked documents" \
  --first "legibility=3 distinctiveness=4 balance=4 color=5 scalability=3 craft=4" \
  --final "legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4" \
  --iterations 2 \
  --lesson "A signature counter must occupy two deliberate pixels at 16px."

python -m iconflow case lint
python -m iconflow case stats
python -m iconflow case atlas --out case-atlas.html
```

If stats reports `DISTILL NOW` or an evolution target, follow
`docs/EVOLUTION.md` before ending the design session.
