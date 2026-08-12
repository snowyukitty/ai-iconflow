---
slug: yukoe-msix-assets
date: 2026-08-12
project: multilingual desktop companion
targets: msix-store
essence: listen
style_family: kawaii-listening-mascot
signature_device: An oversized pink listening ear changes the silhouette of a round white puff.
device_family: mascot-single-trait
device_detail: The exact 44, 50, and 150 px Store rasters preserve the ear spiral, face, outline, and transparent safe area.
concept_lens: identity-mascot-plus-verb
cliche_avoided: plain speech bubble, microphone, waveform, globe, bare monogram
status: shipped
scores_first: legibility=5 distinctiveness=5 balance=4 color=5 scalability=5 craft=4
scores_final: legibility=5 distinctiveness=5 balance=4 color=5 scalability=5 craft=4
iterations: 1
---

## Summary
Extended an already reviewed listening-puff master into exact Microsoft Store MSIX logo slots. Direct SVG renders retained the brand silhouette and remained readable on light, dark, and gray contexts.

## What failed first
No visual axis fell below the ship gate because the source was an already
reviewed master. The first render used generic size-suffixed filenames, which
did not match the MSIX manifest contract; renaming the exact 44, 50, and 150 px
RGBA outputs to their required Store asset names fixed the packaging failure.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For Store package assets, render each manifest slot at its exact pixel dimensions from the reviewed vector master and inspect the actual rasters; generic downscaling assumptions can hide small-size failures.
