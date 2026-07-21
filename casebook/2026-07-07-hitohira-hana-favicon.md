---
slug: hitohira-hana-favicon
date: 2026-07-07
project: Hitohira Hana static site
targets: web,pwa
essence: identity
style_family: mascot
signature_device: Hana avatar face close-crop with the hair flower as the signature detail inside a soft rose ring
cliche_avoided: generic tulip emoji favicon or detached flower mark
scores_first: legibility=3 distinctiveness=4 balance=4 color=5 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
Replaced the generic flower emoji favicon direction with Hana's own avatar identity. The first crop kept too much outer decoration, so the final crop moves the face closer, keeps the hair flower visible, and uses only a soft rose ring for contrast across light and dark tab backgrounds.

## What failed first
The first pass kept the whole avatar plus an external petal accent. At 16px the
face collapsed into a pale pink blur and the accent competed with the identity
instead of helping it. Moving the raster avatar closer to the camera, removing
the external accent, and keeping only a soft rose ring made the eyes, glasses,
and hair flower read sooner while preserving the maskable crop.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For creator avatar favicons, tighten the crop around the expression before adding external accents; the creator face and one built-in trait should carry identity at 16px.
