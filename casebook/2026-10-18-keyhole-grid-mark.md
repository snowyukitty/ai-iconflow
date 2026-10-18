---
slug: keyhole-grid-mark
date: 2026-10-18
project: Brand mark and favicon for a local-first app that maps which device, identity and account unlocks which
targets: web,tauri
essence: map
style_family: flat-geometric
signature_device: 3x3 cell matrix whose centre column becomes one keyhole
device_family: negative-space-cut
device_detail: eight 224-unit cells on 64-unit gutters, tapered keyhole in the lower centre column, 32-unit ink keyline, outer corners rounded to 140 units for the maskable audit
concept_lens: object-metaphor
cliche_avoided: padlock, shield, plain key, letter monogram on a gradient tile
status: shipped
scores_first: legibility=3 distinctiveness=4 balance=4 color=4 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
iterations: 4
---

## Summary
A lime 3x3 grid whose lower centre column becomes one tapered keyhole, bonded
by an ink keyline, replaced an earlier key-with-matrix-bow mark for the same
product. The grid carries the "map" at 16px and the keyhole resolves from
24px. This record is published from the consuming project's own two cases
with a neutral label, and it is kept mostly for what the session showed about
IconFlow itself: three tool gaps that became the 0.7 shared audit, the
configurable maskable composition and the `android` target.

## What failed first
- **The maskable audit gave two answers.** `iconflow check --config` passed a
  draft with an 84-unit margin while `review` and `ship` failed it at 12% of
  detail outside the safe circle: `check` composed the maskable icon on white,
  `review`/`ship` on the configured ink `#11142A`. Re-checking against the ink
  background, the shipped geometry needed a 112-unit margin and 140-unit
  rounded outer corners. On 2026-10-18 the owner's original full-bleed draft
  failed at the default composition and passed unchanged at
  `maskable_scale = 0.7`: the corners had been rounded only to please the crop.
- **A punched keyhole through a merged centre block** left the hole under two
  pixels at 16px; a device-free 3x3 control read as a keypad or calendar, so
  the keyhole carries the identity. A narrower keyhole stem read as a pin.
- **Cell rhythm.** In the predecessor mark, 72-unit bars and 148-unit cells
  smeared at 32px; 64-unit bars and 160-unit cells on 64-unit multiples were
  crisp.
- **No Android target.** The agent hand-rendered an adaptive foreground
  pre-scaled into the 66/108 safe zone plus a legacy tile, then ran the Tauri
  CLI's icon command into a temporary folder so it could not overwrite
  IconFlow's desktop icons.
- **Brand propagation was manual.** Site header, press-kit lockups, app tiles,
  social cards and repository banners were all re-rendered by project scripts.
- **Review surface.** The interactive Review Lab could not be opened in the
  headless session; the receipt was scored from the static sheet and written
  by hand.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] **Promoted as L63 (mechanized).** Audit the maskable composition on the configured background: a full-bleed grid passed on white and failed at 12% on its own ink background. `check`, `review` and `ship` now share one audit.
- [x] **Promoted as L63 (mechanized).** A square full-bleed mark should not round its corners or shrink its cells to pass a circle crop; give the crop its own composition (`maskable_scale`, `maskable_svg`). The original draft passed at 0.7 unchanged.
- [x] **Promoted as L62.** Snapping bars and cells to 64-unit multiples made the 32px cells crisp where 72/148 units smeared.
- [ ] **Held for corroboration.** A keyhole inside a 3x3 grid is capped by the gutters: with 256-unit cells its head can be at most about 256 units across, so it resolves from 24px and reads as a stem at 16px; let the cell grid, not the nested device, carry the 16px identity. One case; promote when a second nested-device mark confirms it.
