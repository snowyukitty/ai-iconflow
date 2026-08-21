---
slug: 2026-08-06-yorozora-node-graph
date: 2026-08-06
project: yorozora (yorozora.com)
targets: web
essence: connect
style_family: flat-geometric
signature_device: the three terminals of 万 become graph nodes, so one drawing reads as a constellation and as a node graph
device_family: ownable-geometry
device_detail: Sunflower tile, charcoal glyph, terracotta nodes. Nodes are mid-tone rather than light: a cream fill punches visible holes through the strokes below 32px and fragments the character, while terracotta merges into the terminals and leaves 万 intact.
concept_lens: negative-space-dual-reading
cliche_avoided: gear/wrench IT support, glowing AI brain, circuit-board texture, chat bubble, generic star field
status: shipped
scores_first: legibility=3 distinctiveness=5 balance=4 color=5 scalability=3 craft=3
scores_final: legibility=4 distinctiveness=5 balance=4 color=5 scalability=4 craft=4
iterations: 3
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
The site moved to a warm-paper neo-brutalist design system, and the owner asked
for a mark carrying AI/IT alongside the existing 万事屋 idea and the name's
second reading 夜露空 (night-dew sky). The fusion that made all three one
drawing: a constellation is also a node graph. The three terminals of 万 became
graph nodes, so the mark reads as the yorozuya character, as stars in a night
sky, and as the graph algorithms this business actually teaches. Sunflower tile,
charcoal glyph, terracotta nodes — the new palette in miniature, and a yellow
favicon is rare enough to own a tab row.

## What failed first
Two separate failures.

**Cream nodes fragmented the glyph.** Filling the graph nodes with the light
paper tone read beautifully at 128px and punched three visible holes through the
strokes at 16-32px, breaking 万 into disconnected pieces. Terracotta — a
mid-tone against both the sunflower field and the charcoal stroke — reads as a
node above 48px and merges into the terminal below it. Legibility 3 -> 4.

**The brutalist card could not be maskable.** The first three passes carried the
design system's signature ink frame and 6px hard offset shadow. Every one failed
the maskable audit (9%, then 8% after shrinking the glyph, then 14% and a second
warning after enlarging the frame). The geometry is decisive: a square frame's
corner sits at sqrt(2) x its half-width, so fitting a 40% safe circle needs the
frame at ~57% of the tile, by which point it is a small box floating in a field
rather than a card. Dropping the frame and the shadow cleared the audit outright
and made the glyph bigger, which lifted 16px legibility as a bonus.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A bordered neo-brutalist card cannot pass a maskable safe-zone audit at any usable size: a square frame's corner sits at 1.41x its half-width, so to fit a 40% safe circle the frame must shrink to 57% of the tile and stops reading as a card. Ship the palette and the glyph in the mark, and leave the ink frame and offset shadow to the interface.
