---
slug: career-cat
date: 2026-07-16
project: CareerCat — job/career companion app
targets: web,tray
essence: fortune
style_family: mascot
signature_device: maneki-neko cat face with one gold bell collar as the single identity trait, on a lucky-red tile
device_family: mascot-single-trait
device_detail: round white cat face, pink inner ears, dot eyes, red nose, gold bell + collar arc; authored on a 64-unit grid
concept_lens: object-mascot
cliche_avoided: briefcase, ladder, upward career arrow, generic cat silhouette with no identity trait
status: shipped
scores_first: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 1
---

## Summary
CareerCat is a job/career companion. The category clichés are a briefcase, a
ladder, or an upward arrow — and a plain cat would be a *generic* animal. The
shipped mark is a **maneki-neko** (beckoning-fortune cat) face on a lucky-red
tile, carried by exactly one ownable identity trait: the gold bell on a collar
arc. That single trait turns "a cat" into "this cat" and ties the mark to the
essence (fortune / good luck in the job hunt) without any literal career prop.

*Owner-curated reference exemplar. Retro-recorded from the shipped SVG to seed
the success canon; scores are the owner's judgement of the final mark.*

## What failed first
No failed pass to report; recorded as a positive standard — with one honest
craft caveat.

- Why it works: one identity trait (the gold bell collar) does the
  distinctiveness work; the rest of the face is deliberately minimal so it holds
  at 16px. Contrast with a generic cat silhouette, which reads as *any* pet app.
- Honest caveat: this master is authored on a **64-unit** viewBox, not the
  playbook's 1024 grid. It ships fine, but small-grid authoring caps how much
  richness it can gain at 512px+ and forces sub-pixel coordinates the renderer
  must round. A 1024-grid redraw would future-proof it.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A mascot needs exactly one ownable identity trait or it reads as a generic animal: the maneki-neko's gold bell collar makes it 'this cat'. Keep the one trait, cut everything else for 16px.
- [x] Author even mascots on the 1024 grid: CareerCat ships on a 64-unit viewBox, which caps how much craft/richness it can gain at 512px+ without a redraw.
