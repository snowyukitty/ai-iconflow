<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Review Checklist — the scored rubric

After `python -m iconflow review --config iconflow.toml --html review.html`, **Read
`review.png` and inspect the Review Lab** before scoring each axis 1–5. Ship
only when every axis is ≥4, `iconflow check` is clean, and the target-specific
previews preserve the same idea.
If any axis is <4, make the single highest-impact change and re-render.

| # | Axis | What 5/5 looks like | Common 2/5 failure |
|---|---|---|---|
| 1 | **Legibility @16px** | one shape, instantly readable in the 16/32 cells and pixel-zoom | grey soup, filled-in counters, vanished strokes |
| 2 | **Distinctiveness ★** | the blacked-out silhouette **names a specific object** (tag, gem, folded map, cat); one specific idea + signature device; stands out in a row of 8 competitors | stock glyph (gear/rocket/✦), **a bare letter or generic shape on a gradient tile**, generic silhouette, looks like 10 other apps |
| 3 | **Balance & grid** | optically centered, sits in a keyline, has safe-area padding | off-center, touching edges, lopsided weight |
| 4 | **Color & contrast** | holds on white AND #0b0d12; 1 hue + accent; clean gradient; ownable palette | invisible on one bg, muddy/rainbow gradient, default-blue |
| 5 | **Scalability** | same idea at 16 and 512; richness only where size allows | detail that only works huge; dies when small |
| 6 | **Craft** | clean curves, even strokes, no stray nodes, intentional negative space | wobbly paths, uneven stroke weight, accidental gaps |

★ **Distinctiveness is the axis AI icons fail most.** It is judged primarily from
the **visual silhouette strip** and the bake-off `compare` sheet — not from the
colorful 256px version. The alpha footprint strip is useful for safe-area and
container shape, but opaque app-card icons must be judged from the visual
silhouette because that preserves glyph/cutout distinctiveness. If the
blackened visual shape is generic (a plain square/circle/teardrop), score ≤3 no
matter how nice the color is, and fix the *shape/idea* per
`docs/CONCEPTING.md`. Apply the **name-the-thing test**: say in one noun what the
silhouette is; if the honest answer is "the letter X" or "a rounded square with a
glyph in it," it is **≤3 regardless of polish** — a letter counts only when it
fuses into an object (fado's plate-F). Treat distinctiveness as a gate: do not
ship below 4 here even if every other axis is 5. The mechanical `check` now emits
an advisory *generic-silhouette / monogram* warning to flag the most common
offenders, but it is a hint, not the judge — you still score the axis by eye.

## How to read the contact sheet

- **Rows** = white / dark / mid-gray backgrounds. The mark must work on all three.
- **Columns** = 16 → 256px actual size. Scan left first; the left columns are the
  real test.
- **Pixel-zoom strip** = 16px and 32px blown up. Anti-aliasing mush, lost detail
  and off-grid blur show up here.
- **Alpha footprint** = the outer/container shape and safe-area footprint.
- Before scoring **craft**, scan the 128px and 256px alpha and visual-silhouette
  strips for spikes, pips and hairs: a doubled-back path segment is invisible at
  16px and in the source but renders from ~128px up, and `check` does not catch
  it. (L54.)
- **Visual silhouette** = the visible shape with color removed; use this for
  distinctiveness, especially on opaque rounded-card icons.
- **Target contexts** = the transformed web/app/tray assets, not just the raw
  SVG. Check the generated macOS template and any corner/mask transform here.
- **Maskable preview** = generated adaptive-icon crop previews plus the safe
  circle (radius 40% of the canvas; diameter 80%). Essential detail should
  remain inside that circle.

## Decision

- All axes ≥4, `check` clean, and every selected target preview intact → export
  the Review Lab receipt and run
  `iconflow ship --config iconflow.toml --review master-review.json` (or the
  low-level `build` command when deliberately working without a project config).
- Any axis <4 → name the weakest axis, apply the one change from the playbook
  §7 self-critique that raises it most, re-render. Repeat (usually 2–3 passes).

## Without a browser: the headless path

When the Lab cannot be opened — a headless agent session, a managed browser
that blocks it — the evidence still can be:

```bash
iconflow review --config iconflow.toml --evidence work/<slug>/evidence
iconflow score  --config iconflow.toml --evidence work/<slug>/evidence \
  --scores "legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4" \
  --rationale legibility="16px zoom: one shape, cut open" \
  ... one --rationale per axis ... \
  --notes "weakest axis and the decisive change" --reviewer-name "<you>" \
  --out master-review.json
```

`review --evidence` writes the contact sheet, `targets.png` (every selected
target's exact bytes in context: favicon tabs, maskable crops, desktop frames,
tray colour and template on light and dark bars, Android launchers and the
themed icon), the ladder and neighbourhood proofs when they apply, and
`findings.json` (inputs, warnings, advisories, measurements, the hash of every
sheet, and which sheet answers which axis). `score` walks the six axes, refuses
evidence whose source, contract or sheets changed, requires a reason of at
least a sentence for every axis, and writes a receipt that says
`review_surface.interactive_lab: false`. The gate is identical: `ship`
re-checks the hashes and the ≥4/5 floor, and a headless receipt is never a
lower bar — it is the same bar with the evidence named.

**Second opinion (advisory).** Another reviewer — by the workspace rule, a
different product from every author of the mark — scores the same evidence
into its own receipt with `score --reviewer-name <them> --out opinion.json`,
and the primary review attaches it with `--second-opinion opinion.json`. It is
recorded in the receipt, an opinion below 4 or two points from the primary on
any axis is reported as `second-opinion-dissent` by `score` and `ship`, and it
never gates and never replaces the primary score. Treat dissent as a reason to
look again, not as a vote.

If even the headless path is unavailable, record that limitation honestly and
follow `WORKFLOW.md`'s managed-browser fallback: inspect the static sheet and
exact target assets at real sizes, then use a complete source-bound `[review]`
approval. Do not treat an inaccessible Lab as a passed review or lower the
≥4/5 floor.

Record the final scores in your summary to the user so the quality is auditable.
Then record the case (`iconflow case new` with both `--first` and `--final`
scores) — the first-pass scores are how the system measures whether its
playbook is improving (see `docs/EVOLUTION.md`).
