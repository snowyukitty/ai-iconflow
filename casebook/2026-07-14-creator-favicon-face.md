---
slug: creator-favicon-face
date: 2026-07-14
project: 
targets: 
essence: cute
style_family: 
signature_device: real hero-photo face in a rounded pink tile (home) + real emote faces per sub-page, chosen over a vector chibi redraw for maximum cuteness
device_family: 
device_detail: real hero-photo face in a rounded pink tile (home) + real emote faces per sub-page, chosen over a vector chibi redraw for maximum cuteness
concept_lens: 
cliche_avoided: vector mascot redraw that reads stiff/generic to the client; SVG-embedded raster favicon
status: shipped
scores_first: legibility=4 distinctiveness=5 balance=4 color=5 scalability=4 craft=4
scores_final: legibility=3 distinctiveness=4 balance=4 color=5 scalability=3 craft=4
iterations: 3
---

## Summary
<!-- One paragraph: the brief, the winning concept, why it won. -->

## What failed first
<!-- What the earlier passes got wrong and which change fixed it. This is the
     raw material for future lessons — be specific (axis, size, shape). -->

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For a creator whose own illustration/photo IS the draw, the client may prefer a real-photo face tile over any vector redraw, accepting 16px softness for warmth+recognizability; honor the identity owner's real art. TECH: an SVG favicon with an embedded raster <image> (data-uri) renders BROKEN in Chromium secure-static/<img> mode, so a photo favicon must ship as PNG/ICO (link the png, keep favicon.svg vector for the 200-check and the nav-brand logo); it cannot live inside favicon.svg.
