---
slug: 2026-08-05-yorozora-seal
date: 2026-08-05
project: yorozora (yorozora.com)
targets: web
essence: ask
style_family: flat-geometric
signature_device: full-bleed carved hanko whose negative-space 万 is the entire visible mark
device_family: object-silhouette
device_detail: The seal is drawn edge-to-edge with four slightly different corner radii and a 1-2 unit wobble per side, so it reads as carved stone at 128px+ while staying a solid confident block at 16px; the 万 counters are budgeted at 64+ units so they survive downsampling.
concept_lens: object-metaphor
cliche_avoided: gear/wrench IT support, glowing AI brain, chat bubble, torii gate, bare kanji floating on a gradient tile
status: shipped
scores_first: legibility=2 distinctiveness=4 balance=3 color=5 scalability=2 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
Favicon for a Japanese "digital yorozuya" — one front door where a nervous
senior asks about a phone and a company asks about AI automation. The user's
job is *ask*, so the mark had to feel like a place you bring a problem to, not
a category noun (support, code, AI). Four concepts were baked: a carved seal, a
tool-chest drawer pulled open, the bare brush glyph 万, and a drawer-plus-seal
fusion. The full-bleed carved seal won: at 16px it is a confident vermilion
block in a tab row with a still-readable 万, and it is the same object the site
already stamps beside its logo, its founder signature and its closing CTA.

## What failed first
Pass 1 legibility 2/5, scalability 2/5. The seal was drawn on the standard ~760
keyline inside a 1024 canvas, which left a 744-unit tile to hold three strokes
and two counters. At stroke 116 the clear space between the top bar and the
horizontal of the 横折鉤 was about 28 units — 0.4px at 16px — so the glyph fused
into a pink smudge. The two drawer concepts failed differently: their
silhouettes read as a generic box/card at every size below 48px, and the
drawer-plus-seal fusion violated the one-dominant-shape rule.

The fix was not a heavier stroke, which would have made the fusion worse. It
was going **full-bleed**: dropping the tile margin recovered ~280 units, which
paid for stroke 152 *and* 100+ unit counters at the same time. Legibility and
scalability both moved 2→4 in one pass.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A kanji-in-a-tile mark lives or dies on the counter budget, not the stroke weight: the first seal draft used a 744-unit tile with 116 strokes, leaving only ~28 units of clear space between strokes (0.4px at 16px) and fusing into a smudge. Going full-bleed bought ~280 units of tile, which paid for both heavier strokes AND 64+ unit counters.
- [x] A second meaning can be too expensive to draw. After shipping, the brand's
      full meaning was confirmed as 万 (anything) + そら (open sky). Three
      sky-carrying variants were baked against the champion: a top stroke
      breaking out of the frame (read as a lidded box at 16px), an open field
      above the character (the 一 detached into a floating line), and a
      chamfered top corner (elegant at 128px, but the chamfer only reads at
      16px if it is large enough to force shortening the 一, unbalancing the
      glyph). Kept the original. The rule: when a mark must carry two ideas,
      draw the one that names the business and let the wordmark, the name story
      or the copy carry the other — a 16px icon has room for one idea.
