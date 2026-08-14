---
slug: yukoe-settings-control-deck
date: 2026-08-14
project: Yukoe settings control deck
targets: ui-buttons,tray-review
essence: control
style_family: flat-geometric
signature_device: Semantic control objects with audible wings and closed-mouth shutters
device_family: semantic-pictogram
device_detail: Each state pair keeps one feature object; two broad outer wings mean on and one inward chevron means off.
concept_lens: object-verb
cliche_avoided: color-only toggles; tiny slash badges; unrelated control styles
status: shipped
scores_first: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=5 color=4 scalability=4 craft=5
iterations: 2
---

## Summary
A seventeen-icon live-control family and a new Settings control overview. Four translated-speech directions were compared; the caption wing won because its message tail and broad audible edge survived at 16 px while book seams and relay handles softened.

## What failed first
The phrasebook direction named the translation feature most literally, but its
center seam and page contours softened first at 16 px. The relay tag and
subtitle capsule stayed crisp but read as generic fast-forward and captions.
The winning caption wing kept a specific speech-tail silhouette, then moved all
state change to its outer acoustic edge. Raising the shared stroke from 84 to
88 units made the tail and off-state chevron survive the exact 16 px raster.
The source SVGs use a two-pole review gradient to pass light/dark inspection;
the app consumes the same alpha geometry as a `currentColor` mask so theme
contrast cannot become a hidden state signal.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For adjacent 16–20 px state controls, keep one semantic object per feature and change only a broad outer edge by at least two rendered pixels; theme color belongs to the consuming currentColor mask, not a color-only state cue.
