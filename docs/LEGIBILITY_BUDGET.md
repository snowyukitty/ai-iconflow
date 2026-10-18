<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The 16px legibility budget

Legibility is the casebook's weakest first-pass axis (3.2 across 202 cases on
2026-10-18), and the lessons it keeps teaching are budget rules: a signature
cut needs two output pixels (L15), an idea-carrying accent needs about 128
units (L16), so does every separating gap (L20, L26), a mark inside a tile
cannot afford them (L28), and 16px has room for one idea (L31). Each of those
was learned in review — after the bake-off had already chosen the concept.

`iconflow budget` measures them **before** the bake-off:

```bash
iconflow budget work/<slug>/a.svg work/<slug>/b.svg work/<slug>/c.svg \
  --sheet work/<slug>/budget.png
```

`iconflow compare` prints the same measurement under its sheet, and
`review --evidence` records it in `findings.json` (`metrics.budget`). The
sheet rings every narrow feature on the 256px render, labelled with its width
in grid units, beside the real 16px render enlarged.

## What it measures

The glyph rung — what ships at 16px — is rendered at 256px (4 grid units per
pixel) and at 16px. Colours are grouped into classes; the **ground** is
transparency, or the card when one opaque class holds most of the canvas.

| Code | Measurement | Rule |
|---|---|---|
| `budget-cut` | an enclosed cut narrower than **128 units** (2 px at 16px) | L15 |
| `budget-gap` | a gap separating two parts narrower than **64 units** (1 px): they fuse | L26 |
| `budget-accent` | a detached part narrower than **128 units** and under 6% of the canvas | L16 |
| `budget-closed-cut` | cuts open at 256px that do not own **two clearly ground pixels** at 16px | L15 |
| `budget-fused-parts` | separate parts at 256px that are fewer at 16px | L26, L58 |
| `budget-ideas` | more than **3** separate parts at 16px | L31 |
| `budget-tile` | a mark on a card spanning under **75%** of the card | L28 |

Widths are the widest disk that fits in the feature, rounded to 8 units. A
notch in the outer contour separates nothing and is left to the silhouette
test; a feature smaller than 1.5 output pixels² (0.5 for a separate part) is
treated as antialiasing. The share of the 16px footprint that is a colour
blend ("mush") is recorded in the JSON and never reported, because
antialiasing makes it high on good marks too (median 0.44 on the shipped
gallery).

## What it is not

Every finding is an **advisory**: a measurement, never a verdict. The budget
never gates `check` or `ship`, never changes an exit code, and never replaces
the six-axis human score. A cut under budget can be the right call — a
reviewer may accept a petal gap that merges at 16px because the petals read as
one gestalt — and the budget's job is to make that a decision instead of a
surprise.

## Calibration (2026-10-18)

Measured with the thresholds above; reproduce the gallery half with
`python scripts/calibrate_budget.py`.

**Documented first drafts that failed on legibility** (from their cases):

| Draft | What the case says failed | Budget |
|---|---|---|
| brick game, round 1 gap scene | mark ~65% of a dark card, 2px at 16px | `budget-cut`, `budget-accent` |
| brick game, round 1 control | same | `budget-tile` (60%) |
| brick game, round 1 brick-core | same | `budget-tile` (73%) |
| brick game, round 1 filling | same | `budget-cut`, `budget-fused-parts`, `budget-tile` |
| keyhole grid, punched hole | hole under 2px at 16px | `budget-cut`, `budget-accent`, `budget-ideas` |
| keyhole grid, wide punched hole | same | `budget-cut`, `budget-accent` |
| candidate shell, first hole | 216×260 hole with a 68-unit band became one light pixel | — **missed** |

Six of seven flagged. The miss is instructive: the hole was wide enough, and
what failed was the 68-unit *ring* around it merging with the hole on white —
a thin figure band, which the budget does not yet measure. The two finals
those cases shipped (the stud-core brick and the enlarged shell hole) measure
within budget.

**The 100 admitted gallery finals** (all shipped at legibility 4 or 5): at least
one finding on 43 — `budget-cut` 61 features, `budget-accent` 36,
`budget-closed-cut` 17, `budget-fused-parts` 14, `budget-gap` 6,
`budget-tile` 5. That is **not** a false-alarm rate. Inspected at 16px, the
flagged finals do lose what the budget says they lose (a koi's belly cut
closes, a caliper's dashed rails fuse into one band, a sleeping cat's face
turns to mush); reviewers accepted those losses. It does mean the budget
speaks often, which is why it advises rather than gates.

## Measuring whether it helps

No improvement is claimed yet: the budget shipped on 2026-10-18, and its
effect is only visible in cases recorded after it. Compare first-pass
legibility before and after with

```bash
iconflow case stats --until 2026-10-18
iconflow case stats --since 2026-10-19
```

and record in the case whether the budget was run on the finalists. Treat a
difference on fewer than about 20 later cases as noise.
