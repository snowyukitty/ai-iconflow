---
slug: creator-favicon
date: 2026-07-06
project: the creator fansite favicon
targets: web
essence: affection
style_family: mascot
signature_device: a love emote face in a rounded pink badge with one heart tag
cliche_avoided: generic rabbit emoji favicon, generic bunny head, tiny text
scores_first: legibility=3 distinctiveness=4 balance=4 color=5 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
A website favicon for the creator fansite. The winning concept uses the chibi persona emote rather than a generic rabbit emoji or a bunny mascot mark, keeping the face and heart tag recognizable at tab size while matching the site's pink identity.

## What failed first
The first instinct was a generic rabbit emoji favicon, which was legible but
failed the creator/mascot naming boundary and had no distinct ownership. In the
IconFlow bake-off, `yay-badge` produced the strongest bunny-ear silhouette but
risked reading as the a bunny mascot instead of the chibi persona. `confident sunglasses`
was clearer at 16px, but the meme expression felt less warm for the site.

The selected `love-heart` direction kept the person-side emote and a single
heart tag. A later attempt enlarged the face to improve 16px legibility, but it
triggered the maskable safe-zone warning because the detail filled too much of
the adaptive crop. Reverting to the safe version preserved maskability while
still replacing the old generic favicon with a warmer creator-specific mark.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For creator fansites, favicon identity should preserve the creator/character boundary; a cute mascot shortcut can be semantically wrong even when it looks on-brand.
- [x] If a raster emote is used inside an SVG favicon, do the maskable audit before enlarging the face; a bigger crop can improve 16px legibility while breaking adaptive-icon safety.
