---
slug: yonago-koyomi-favicon
date: 2026-08-15
project: yonago-koyomi
targets: web
essence: keep-the-day
style_family: flat-geometric
signature_device: one day-page hinged left and lifting right off a tear-off calendar block, the gap between them a widening wedge rather than a slot
device_family: object-silhouette
device_detail: The counter is 46 units at the hinge and 78 at the free end, and the page overhangs the block's right edge by 28 units; the page's top-right corner is a long cut diagonal, which is the single feature that separates it from a folder tab.
concept_lens: specific-object
cliche_avoided: square calendar grid page with a date number and two ring binders — the silhouette of every OS calendar app
status: shipped
scores_first: legibility=4 distinctiveness=3 balance=3 color=5 scalability=4 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 3
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary

よなご暦 is a chronological local information service for one Japanese city:
news, events and municipal notices on a single time axis (いま / これから /
今年). The user job is "tell me what is happening in my town, and let me trust
the date", so the mark had to say *calendar* without borrowing the OS calendar
silhouette — a grid page with a date number and two ring binders, which every
operating system already owns.

The winning object is a **日めくり**, a Japanese tear-off day calendar: one
solid indigo block of remaining days with today's page lifting off it in
vermilion. It won because it is a specific object rather than a category
symbol, it carries the product's core idea (a day is taken off the stack and
becomes part of the record) in its geometry, and its silhouette — a block with
a full-width lifting band and a cut corner — collides with nothing.

Palette is the site's own: indigo `#1f3a64` dominant, vermilion `#b23a2e`
reserved for *today* exactly as it is in the product's CSS.

## What failed first

Six drafts across three bake-offs, and the first five all failed on the
**name-the-thing test** rather than on any mechanical check.

- **A — ragged tear edge across the top.** Three large teeth were needed for
  the perforation to survive 16px, and at that scale three teeth read as a
  **crown or castle battlement**. The right noun at 1024 became the wrong noun
  at 128. Rejected on distinctiveness, not legibility.
- **C — stepped stack (the year accumulating).** The staircase silhouette read
  as a **bar chart**, i.e. analytics. Rejected outright.
- **B / B2 — a curved page peeling off the top-left.** At 128px the curved
  vermilion form perched on a dark box read as a **chef's or Santa hat**; B2's
  angular version read as a hook. Both also sat small in the frame, wasting
  ~40% of the tile.
- **B3 — page curling forward over the block.** A uniform coloured bar across
  the top with a step at one end is *exactly* a folder tab. Clean, legible, and
  the wrong application.
- **B6 — corner already torn away.** The missing corner was ~330 units, which
  sounded generous, but against a full-bleed block the alpha silhouette
  collapsed to a **plain black square** — L8's filled-tile failure.

B4 was promoted because its silhouette was the only one that stayed ownable
without naming a wrong object. Two review passes then fixed:

1. **Craft (3→4).** The page outline stepped right, up, then left again,
   leaving a 16-unit doubled-back spike. It was invisible in the SVG source and
   invisible at 16px, but showed as a distinct pip on the page's edge at 128px
   and 256px in both the alpha footprint and the visual silhouette. Rewriting
   the outline strictly clockwise removed it.
2. **Balance (3→4) and distinctiveness (3→4).** The mark was enlarged to spend
   the tile, and — the change that actually mattered — the gap between page and
   block was converted from a **uniform slot** into a **wedge** (46 units at the
   hinge, 78 at the free end), with the page overhanging the block's right edge
   by 28 units. A uniform slot reads as two stacked bars; a wedge reads as
   something opening.

## Lessons

- [x] A coloured band resting on a dark block almost always reads as a folder
      tab or a card header; what converts it into a lifting page is a
      WEDGE-shaped counter plus an angled corner, because folder tabs are
      uniform-height and never cut at an angle.
- [x] Perforation, serration and other repeated-tooth edges need so much width
      per tooth to survive 16px that only 3–5 teeth fit — and 3–5 large teeth
      read as a crown, a fort, or a saw, never as "torn". If an edge must say
      *torn*, use ONE large irregular event, not a repeated pattern.
- [x] A doubled-back segment in a path (right, up, left) is invisible in the
      source and at 16px, but renders as a visible pip from ~128px up. Check the
      alpha footprint and visual silhouette strips at 128/256px specifically for
      spikes before scoring craft; the automated `check` does not catch it.
