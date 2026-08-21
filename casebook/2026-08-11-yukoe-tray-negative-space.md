---
slug: yukoe-tray-negative-space
date: 2026-08-11
project: yukoe
targets: tray
essence: listen
style_family: kawaii-template-mark
signature_device: A pink listening ear plus transparent facial cuts inside the snow-puff silhouette.
device_family: mascot-single-trait
device_detail: Two large transparent eyes and one smile stay open in both the 16 px color tray asset and alpha-derived template.
concept_lens: identity-mascot-plus-verb
cliche_avoided: featureless status dot, disconnected tray glyph, microphone, waveform
status: shipped
scores_first: legibility=1 distinctiveness=3 balance=4 color=3 scalability=1 craft=2
scores_final: legibility=5 distinctiveness=5 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
The existing tray mark collapsed into a purple dot because its same-color face disappeared and its alpha template had no negative-space expression. Four directions were considered: face cuts, an inner-ear cut, a profile notch, and a voice-mouth cut; three SVG finalists were rendered side by side. The face-cut version won because it stayed warm and recognizable at 16 px while preserving the pink listening ear and the master icon silhouette.

## What failed first
The shipped tray SVG drew its eyes and mouth with the same purple fill as the
body. The color raster therefore lost the face, while alpha template extraction
flattened every foreground shape into one featureless blob; legibility and
scalability both scored 1 at 16 px. In the bake-off, the inner-ear candidate
added too much detail at that size and the wide-cut candidate felt mechanical.
Making the friendly face three large transparent openings fixed both render
paths at once without changing the app icon or weakening the pink ear cue.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For alpha-derived tray mascots, cut essential facial features out of the silhouette instead of drawing them in the same foreground color; test the real 16 px output before shipping.
