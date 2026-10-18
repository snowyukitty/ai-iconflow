---
slug: color-system-specimen-jar
date: 2026-10-18
project: local-first color-system generator website favicon
targets: web
essence: specimen
style_family: flat-geometric
signature_device: pigment specimen jar holding one hue tuned for light and dark, under one punched-through label
device_family: object-silhouette
device_detail: jar body split at the centre line into a deep and a lifted tint of one hue; a 384x192-unit label is cut through both halves; lid, neck, label and split snapped to the 64-unit grid
concept_lens: specific-object
cliche_avoided: color wheel, artist palette, swatch fan, eyedropper, paint drop, rainbow gradient, descending three-bar mark
status: shipped
scores_first: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=3
scores_final: legibility=5 distinctiveness=4 balance=4 color=4 scalability=5 craft=4
iterations: 2
---

## Summary
A color-system generator (one brand color in, light and dark role systems out) needed a favicon for light and dark tabs. Its existing three descending colored strokes was a bar chart. Eleven drafts across object, metaphor, verb and letterform lenses: paint chip (generic rounded rectangle), observatory dome (hard hat), tuning fork (Y glyph), pulled chips (Gantt/align), h fusion (letter), ringed planet (legible Saturn, too wide for 16px and off-category), and a labelled pigment jar. The jar won; its device-free control read as a generic jar or bin, so the punched label carries the noun, and splitting the contents into a deep and a lifted tint of one hue states the light/dark promise and keeps one half contrasting on either tab.

## What failed first
Round one (paint chip, observatory dome, tuning fork, pulled chips, h fusion,
inherited three-bar mark) produced no specific silhouette: a rounded rectangle,
a hard hat, a Y, a Gantt row, a letter and a bar chart. A ringed planet was the
most legible metaphor at 64px but its rotated ring left a 10x5px smudge at 16px
and named astronomy rather than color. The first jar master scored craft 3: the
lid sat 32 units off the pixel grid (96-256) and the real 16px ICO frame drew it
as a soft two-tone bar; label and body edges were also half-pixel. Snapping lid
(128-256), neck, label (320-704 x 576-768), body (192-832) and the tint split
(512) to 64-unit multiples made every edge crisp and lifted legibility and
scalability to 5.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] **Merged into L56.** Retire an inherited mark through the bake-off, not by assumption: put it in as a control. Three descending strokes rendered as a bar chart on the silhouette strip immediately.
- [x] **Merged into L49 as an alternative technique (one case).** A two-tint split of one hue (deep left, lifted right) holds a transparent favicon on both white and near-black tabs without a keyline, because each half carries contrast against one background.
- [x] **Promoted as L62.** Snap lid, label and split edges to the 64-unit grid after picking the winner: the same geometry 32 units off-grid rendered the 16px lid as a two-tone smear in the real ICO frame.
