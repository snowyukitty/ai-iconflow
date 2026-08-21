---
slug: yukoe-automatic-speech-controls
date: 2026-08-14
project: Yukoe automatic speech controls
targets: web
essence: routing
style_family: flat-geometric
signature_device: Folded Folio: nameplate, folio, and phrasebook with stateful right-edge contours
device_family: ownable-geometry
device_detail: ON uses a broad call-wing, OFF a sealed-side notch, and BLOCKED a half-open fold; each changes the 16px outer silhouette by at least two pixels.
concept_lens: object-verb
cliche_avoided: color-only state / role badge / generic translation arrows
status: approved
scores_first: legibility=3 distinctiveness=4 balance=3 color=3 scalability=3 craft=3
scores_final: legibility=4 distinctiveness=5 balance=4 color=4 scalability=4 craft=4
iterations: 3
---

## Summary
A nine-state inline control family for Yukoe's automatic TTS matrix. Folded Folio won a four-concept divergence and three-finalist silhouette bake-off because concrete nameplate, page, and phrasebook objects remain distinct while the right edge communicates effective state without relying on color.

## What failed first
The first family reused one ticket-like outer contour and changed only interior
lines. At 16px, original and translation collapsed into the same mark, while
CSS masking discarded the SVG gradients and reduced every state to color. The
final pass assigned a concrete outer object to each content kind, moved state
to a 4–6px right-edge silhouette change, and added a dark keyline so the family
survives mid-gray as well as light and dark surfaces.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] At 16px, put state on the outer contour and content on one concrete interior object; a color-only fill cannot carry blocked versus off.
