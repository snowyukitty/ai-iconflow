<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The Detail Ladder — designing bigger without designing twice

One source, three size regimes. Detail that only exists where there is room for it.

Every rule this toolkit has ever distilled is a compression rule. Survive 16px.
Own two pixels. One idea per icon. Fifty-six lessons and a casebook of shipped
marks all push the same direction, and that is why the marks are good.

It is also the ceiling. The drawing that wins a 16px bake-off is, at 1024px, an
under-drawn 16px icon: flat where a store plate wants material, empty where a
dock icon has room for a second reading. Until now IconFlow had no way to say
*this detail exists only when there is room for it* — so the only honest answer
to "can we design a bigger icon?" was "draw a second file and hope the two stay
the same logo."

The ladder is the answer that does not fork the source.

---

## The three rungs

| Rung | Sizes | Budget | Where it is seen |
|---|---|---|---|
| `glyph` | ≤ 48px | One idea. The whole outer contour. | favicon, tab, tray, list row |
| `mark` | 49–256px | A second reading inside that contour. | app grid, dock, PWA icon |
| `plate` | ≥ 257px | Material, depth, surface. | store listing, splash, about box, print |

The boundaries are not taste. They are where IconFlow's own output sizes fall:
`favicon.ico` packs 16/32/48, the PWA and Tauri sets live between 64 and 256,
and 512/1024 are the sizes a person looks *at* rather than past.

## The grammar

A group lists the rungs it belongs to. Anything without the attribute belongs
to every rung, which is why every master authored before this feature existed
renders byte-for-byte as it always did — the ladder is opt-in and costs a flat
source nothing.

```svg
<g data-lod="glyph mark plate"> the one idea, and the whole silhouette </g>
<g data-lod="mark plate">       the second reading                    </g>
<g data-lod="plate">            material: coursing, rim light, glow    </g>
```

Rung names are space- or comma-separated, case-insensitive. An unknown name is
an error, not a silent no-op. `data-lod` on the root `<svg>` is refused: it
would reduce the whole icon to nothing.

## The one rule: **the ladder grows inward**

Every trait that defines the *outer contour* belongs on the `glyph` rung. The
rungs above it own what happens *inside* that contour.

This is not a style preference, it is what makes the ladder safe. A viewer who
sees your icon at 512px and later at 16px must meet the same object. Silhouette
is how recognition survives scale — so a chimney, a notch, a broken horn, an
escaped accent all belong at the bottom of the ladder, where they are load
bearing. Brick coursing, a rim light, an ember glow do not: they are what the
extra pixels are *for*.

The worked example in `examples/detail-ladder/` had a chimney collar on the
`mark` rung in its first draft — dark clay laid across the chimney, which from
49px up read as a joint and cut the chimney off the dome. The outer contour
said one thing at 16px and another at 64px. The same-mark overlay painted it
coral and it was removed rather than tuned. That is the rule earning its keep.

## Two mechanisms, one result

**Rasters are reduced structurally.** Before the renderer sees anything,
`ladder.reduce_svg` deletes the subtrees that do not belong to the rung the
requested size falls in. Deterministic, browser-independent, testable without
Chromium. Every size IconFlow builds — every ICO frame, every PNG, the maskable
asset, the tray template — comes from its own rung.

**The shipped vector carries a stylesheet.** `favicon.svg` is a single file a
browser draws at 16px in a tab and at 512px in a preview, so it cannot be
pre-reduced. `build` writes it with a generated `@media` layer whose queries key
off the size the SVG is actually *drawn* at:

```css
[data-lod]:not([data-lod~="plate"]){display:none}
@media (max-width:256px){ /* keep mark, drop plate-only */ }
@media (max-width:48px){  /* keep glyph, drop the rest   */ }
```

The rule outside any media block is deliberate: a renderer that ignores media
queries keeps the `plate` rung — the complete artwork, which is exactly what
IconFlow shipped before the ladder existed. The worst case is the old
behaviour, never a blank icon.

**And the two agree.** `tests/test_ladder.py` renders both paths at 16, 48, 49,
256, 257 and 512px and asserts the PNG bytes are *identical*. A vector favicon
that quietly disagreed with the PNGs it ships beside would be worse than no
feature at all, so it is a test, not a claim.

## The gate: the same-mark invariant

Adding detail must never become redrawing the logo. `check` renders the three
rungs at one comparison size and measures each adjacent step. It runs
automatically, and only for a source that opted into the ladder — a flat icon
has one rung and nothing to stay consistent with.

It measures two silhouettes, because an icon has two and a ladder can break
either. The **footprint** is the alpha channel: the space the icon occupies.
The **visible shape** is what a person recognises — found by splitting the
render at the luminance boundary the drawing itself implies (Otsu) and keeping
the minority side. On a transparent mark the two agree; on a full-bleed card
the footprint is only the rounded square, and just the visible shape can tell a
kiln from a teapot. Gating on alpha alone would pass anything at all on a card.

| Code | Fires when | What it means |
|---|---|---|
| `ladder-annotation` | no element reaches the `glyph` rung, or a rung name is unknown | nothing is named as surviving to 16px |
| `ladder-empty-rung` | a rung draws nothing visible | that rung would ship a blank icon |
| `ladder-footprint` | outer footprints of two rungs overlap < 62% | a rung changed the outer contour: the ladder grew outward |
| `ladder-silhouette` | visible shapes of two rungs overlap < 62% | at that distance a viewer meets two different objects |
| `ladder-centroid` | optical centre moves > 5% of the canvas | added detail is pulling the mark off its own balance point |
| `ladder-hue` | dominant hue shifts > 15° | a rung carrying its own palette reads as a second logo |
| `ladder-subtraction` | a rung's footprint is < 98% inside the rung above it | a mask, clip or blend makes removal do something other than remove |

Every threshold is a CLI flag on `iconflow ladder`, so a family with a reason
can move one deliberately instead of quietly ignoring the finding. The centroid
ceiling is 5% because 5% of the canvas is 0.8px at 16px: below that a shifted
optical centre is invisible, above it the small and large icons visibly sit
differently.

## Working with it

```bash
# audit the ladder and read the visual proof
python -m iconflow ladder master.svg --sheet work/<slug>/ladder.png

# machine-readable, for CI and agents (docs/AGENT_CONTRACT.md envelope)
python -m iconflow ladder master.svg --json
```

The proof sheet has three bands, and they answer three different questions:

1. **delivered** — every size rendered from its own rung. Detail should
   *appear* as the size grows. If nothing changes across the strip, the ladder
   is annotated but not doing anything.
2. **the three rungs at one size** — what each rung actually draws, with the
   size difference removed so you are comparing drawings, not resolutions.
3. **same-mark overlay** — grey is the larger rung, black is what survives to
   the smaller one, and every coral pixel is geometry the smaller rung has that
   the larger one does not. Coral is the picture of a broken ladder.

`ladder` exits 0 when clean, 1 when the invariant is broken, 2 on a usage or
runtime failure — the same contract as every other gated command.

## How to author one

1. **Draw the glyph rung first, alone, and finish it.** It is a complete icon
   and must pass every existing rule on its own: `check`, the 16px pixel
   budget, the silhouette test, the bake-off. If it is not shippable by itself,
   the rungs above it are decoration on a weak mark.
2. **Add the `mark` rung only where 49px buys you something.** One second
   reading. Usually a state, a material cue, or the thing the object is *for*.
3. **Add the `plate` rung last, and only inward.** Surface, coursing, glow,
   rim light — no new contour, no new hue, no new noun.
4. **Read the sheet, not the numbers.** The invariant catches the failures that
   are mechanical. Whether the plate rung is *worth* drawing is still a human
   call, scored on the same six axes as everything else.

## What this milestone deliberately does not do

The ladder makes an icon *richer* at large sizes. It does not yet make it
*wider*: the renderer is still square by construction, so non-square
large-format slots — a 1200×630 social card, a 1024×500 Play feature graphic, a
splash screen, a print plate at a physical size and DPI — remain out of scope.
Those need a composition model (where the mark sits in a frame, with what
margin, against what field), not a detail model, and mixing the two would blur
both. The frame tier is the next rung of this sub-project, and the ladder is
what it will place inside its frames.

---

Related: [`SVG_TECHNIQUES.md`](SVG_TECHNIQUES.md) for what to draw at each rung,
[`REVIEW_CHECKLIST.md`](REVIEW_CHECKLIST.md) for the six axes that still decide
whether it ships, and [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md) for the `ladder`
envelope and exit codes.
