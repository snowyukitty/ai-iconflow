---
slug: creator-favicon-confident
date: 2026-07-06
project: the creator fansite favicon
targets: web
essence: attitude
style_family: mascot
signature_device: a confident emote face in a safe rounded pink badge with sunglasses as the signature detail
cliche_avoided: generic rabbit emoji favicon, tiny text, oversized decorative star
scores_first: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
A revised website favicon for the creator fansite, responding to a request to use one of the artwork emotes as the identity mark. The winning concept uses a confident emote because the sunglasses remain readable at 16px and feel distinct from a generic rabbit or mascot favicon, while the rounded pink badge keeps it aligned with the site palette.

## What failed first
The first confident-expression candidate had the strongest tab-size expression, but the outside star and larger crop pushed too much visible detail outside the maskable safe-zone audit. Removing the star and shrinking the emote into a safer circular crop kept the sunglasses readable while clearing `iconflow check` with no warnings.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] When a raster emote has a strong expression, preserve the expression and shrink or remove outer props until the maskable audit passes.
