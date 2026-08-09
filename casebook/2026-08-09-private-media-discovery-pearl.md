---
slug: private-media-discovery-pearl
date: 2026-08-09
project: Private media discovery hub
targets: web,electron,tray
essence: reveal
style_family: flat-geometric
signature_device: one off-centre gold pearl suspended in the broad opening of a front-facing oyster
device_family: object-silhouette
device_detail: scalloped rose oyster, 136-unit pearl, and a 128-unit-minimum open counter
concept_lens: object-metaphor
cliche_avoided: bare monogram, rounded gradient tile, play/film/eye glyphs, literal category imagery, ticket, blossom, sibling fan mark
status: shipped
scores_first: legibility=4 distinctiveness=3 balance=3 color=4 scalability=4 craft=3
scores_final: legibility=4 distinctiveness=5 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
A privacy-sensitive, local-first discovery hub needed an ownable reveal mark
across web, desktop, and tray targets. Five concept lenses explored a lacquer
comb, pearl oyster, loosened sash, wooden-sandal route, and animation drum. A
front-facing oyster holding one off-centre pearl won because it converts the
user job into a specific object silhouette without literal category symbols or
repeating sibling marks.

## What failed first
The comb finalist read as a mushroom or jellyfish at both 128px and 16px. The
first oyster used a side-hinged near-circle; its seam and pearl collapsed into
lips, an eye, or a toy-ball symbol, leaving distinctiveness, balance, and craft
at 3. Reframing the same metaphor straight-on created two broad shell masses,
a 128-unit-minimum open counter, asymmetric crown scallops, and one 136-unit
off-centre pearl. The noun test became “oyster” while all three visual beats
survived favicon and monochrome tray sizes.

## Review fallback
A managed local-browser policy blocked the interactive Review Lab. It was not
bypassed: the static sheet and exact target assets were inspected at real
sizes, all six scores and notes were recorded in the full source-hash-bound
approved fallback, and gated `ship` re-ran QA before writing output. The
interactive check remained explicitly recorded as blocked.

## Delivery correction
The desktop initially retained a previous mark because its shortcut reused a
canonical `.ico` path. Installing a content-addressed icon alias, recreating
the shortcut, reading `IconLocation` back, and comparing the alias bytes with
the verified build made the delivered state auditable without relying on a
visual cache refresh alone.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] If an object metaphor names a stronger unrelated object at 128px or 16px, change the viewpoint before adding detail; viewpoint determines the silhouette and counter geometry.
- [x] If policy blocks the interactive Review Lab, preserve the gate with the static sheet, exact target assets, complete scores and notes, and a source-hash-bound approved fallback; report the blocked check honestly.
- [x] A content-addressed Windows shortcut icon path plus read-back verification is stronger delivery evidence than cache clearing or inspecting only the canonical source file.
