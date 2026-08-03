---
slug: lumendeck
date: 2026-08-04
project: LumenDeck (Windows tray app, DDC/CI monitor control)
targets: electron, tray
essence: level
style_family: flat-geometric
signature_device: two panels of different orientation standing on one shared rail, lit by identical per-shape ramps
device_family: ownable-geometry
device_detail: A wide landscape panel beside a tall portrait panel, bottoms aligned, both standing on a single rail that turns them into one object. Both semantic gaps are 128 units so neither closes at 16px. Identical per-shape gradients, deliberately NOT a shared canvas-space gradient.
concept_lens: verb-system
cliche_avoided: sun/sunburst (which was literally the app's placeholder icon), lightbulb, half-filled contrast circle, a lone monitor rectangle colliding with Windows Display Settings
status: shipped
scores_first: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=5
iterations: 2
---

## Summary

LumenDeck sets brightness, contrast and colour temperature on every attached
monitor. Its job is not "adjust a screen" - it is *level the screens*, because
different panels need different numbers to emit the same light. The app shipped
with a runtime-drawn sun as a placeholder, which is the single most generic
brightness glyph there is.

The mark is a wide landscape panel beside a tall portrait panel, bottoms
aligned, both standing on one rail. The orientation contrast is what names the
object as monitors rather than as a chart; the rail turns two floating
rectangles into one thing with an ownable silhouette. Both are lit by identical
gradients, so shapes that differ read as *identically lit* - the product in one
image.

Three bake-off rounds. What lost, and why, mattered more than what won.

## What failed first

**A stepped row of three same-width panels read as a bar chart.** In the
silhouette strip it was indistinguishable from analytics or signal strength -
[[L9]] in practice. Killed rather than iterated.

**A warm/cool pair (one amber panel, one blue) had no silhouette at all.** Two
identical rounded squares; the whole idea lived in colour, which the silhouette
test strips away. It also broke the one-dominant-colour rule.

**The concept's own signature device drew the opposite of its meaning.** The
first execution ran a single `linearGradient` in `userSpaceOnUse` across both
panels, so the light band would sit at the same absolute height on both -
literally "one level across different screens". Rendered, the taller panel
reaches into a different part of the ramp and comes out a visibly different
tone. At 128px the two panels look *mismatched*; at 16px the tall one reads as
unlit. A device intended to say "matched" was drawing "not matched". Replacing
it with identical per-shape ramps fixed both the meaning and the legibility.

**A "level notch" cut into the taller panel was invisible at every rendered
size** despite looking deliberate at 1024 - it never reached the ~128-unit
minimum for a semantic cut.

**The rail's first geometry left only a 72-unit gap** between the panels and the
rail, about 1.1px at 16px, so they fused. Widening both gaps to exactly 128
units is what let the three-element mark stay readable at 16px, which is the
whole reason a three-element mark was affordable at all.

## Lessons

- [x] A gradient shared across shapes in `userSpaceOnUse` renders different-sized
      shapes in different tones, so a device meant to say "these are matched"
      draws the opposite. Sameness is expressed by making the shapes *look*
      identical, not by running one ramp through them.
- [x] When a mark needs three elements to be specific, the gaps are the design.
      Budget every semantic gap at 128 units on the 1024 grid before adding the
      third element - if two of them cannot both afford it, the concept is a
      two-element concept.
- [x] A row of same-width blocks of increasing height is a bar chart, whatever
      the blocks are meant to be. Orientation contrast (landscape beside
      portrait) is what makes rectangles read as screens.
