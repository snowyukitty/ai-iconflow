---
slug: quota-lighthouse
date: 2026-07-28
project: Quota Lighthouse
targets: web,electron,tray
essence: guidance
style_family: flat-geometric
signature_device: wave-notched lighthouse base
device_family: object-silhouette
device_detail: A chunky harbor lighthouse with a 132-unit rising-wave counter and one warm quota window; tray variant shares the geometry and adds a 56-unit contrast keyline
concept_lens: object-metaphor
cliche_avoided: generic dashboard gauge; AI sparkle or robot; stock lighthouse clip-art
status: shipped
scores_first: legibility=4 distinctiveness=4 balance=5 color=3 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=5 color=5 scalability=4 craft=5
iterations: 2
---

## Summary
A calm local quota cockpit needed a specific object that survived both an Electron tile and a 16 px system tray. A wave-notched lighthouse beat twin-window and beam-gate alternatives because its silhouette still named the product on the smallest row.

## What failed first
The 16 px Windows tray render kept the lighthouse silhouette, but its harbor-navy
fill nearly disappeared on a dark taskbar, so color/contrast scored 3. A 56-unit
warm-paper keyline on the geometry-linked tray source left the light-background
read unchanged, restored a deliberate one-pixel boundary on dark, and remained
compatible with monochrome macOS template recoloring.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For a dark desktop mark that must work on both light and dark taskbars, add one geometry-linked light keyline to the tray source instead of changing the app mark or adding a second glyph.
