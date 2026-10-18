---
slug: brick-rider-game-icon
date: 2026-10-03
project: Browser building game (installable PWA): lay bricks so a rolling core crosses gaps
targets: web
essence: carry
style_family: flat-geometric
signature_device: the round core character is the toy brick's second, oversized stud
device_family: object-silhouette
device_detail: one flat 180x76 stud plus a 226-radius cream core with two 92x124 eyes rising from the same brick, separated by a deliberate ~2px notch
concept_lens: identity-object
cliche_avoided: generic toy brick
status: shipped
scores_first: legibility=2 distinctiveness=3 balance=3 color=4 scalability=2 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
iterations: 4
---

## Summary
A theme-neutral icon shared by a public and an invite-only build of a brick-laying game. The user-job scene (a core hovering over a gap toward a hollow ghost brick) was faithful but failed twice: a round head resting centred on a block read as the generic user/avatar bust, and floating it above two blocks read as an org-chart node with eye-dots that fused into a minus sign at 16px. The shipped mark fuses the character into the object: one wide mint brick whose second stud is the big cream core with two well-separated eyes; a device-free control (no stud) read as a ball in a box, proving the flat stud carries the brick noun.

## What failed first
- **Round 1 (marks on a dark card, ~65% of the tile):** all four concepts
  (gap scene, its device-free control, brick-wearing-core, filling ghost brick)
  were a few pixels tall at 16px and the visual-silhouette strip was a plain
  rounded square (L8). Legibility 2, scalability 2. Fix: delete the card and go
  full-bleed with a 56-unit navy keyline drawn under the fills (L28/L29).
- **Round 2 (full-bleed gap scene):** a 64-unit `paint-order` keyline also
  stroked the ghost brick's inner counter and ate it to ~70 units. Fix: draw the
  keyline as a separate outer-contour layer so holes keep their full budget.
- **Round 3 (maskable):** the wide bridge scene put 11% of its detail outside
  the 40% safe circle; compacting it with rounded outer corners fixed `check`,
  but the core then rested centred on the left block and the visual silhouette
  became a user/avatar bust. Lifting the core above both blocks gave an
  org-chart triangle, and its eyes (≈80 units apart) fused into a minus sign at
  16px. Distinctiveness 3.
- **Round 4 (fusion):** making the core the brick's second stud produced one
  mass that read at 16px with two separate eye pixels. The narrow left stud read
  as a funnel (boat) at 128px; widening it to 180x76 restored the stud. A
  48–128px pip appeared where the stud almost met the core; moving the core
  right opened a deliberate ~2px notch. `check` clean, nearest neighbour crown
  at 0.206 against a 0.12 radius. Interactive Review Lab not opened (headless
  agent session); static sheet plus exact ICO/PNG targets inspected instead.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] **Promoted as L61; also evidence for L60.** A small round 'head' resting centred on a wider block becomes the user/avatar bust silhouette; offset the round mass to one end of the block or fuse it as part of the object before judging the scene.
- [x] **Promoted into L61 (the 128-unit eye gap).** Two eyes inside a small disc need a 128-unit gap between them; at 64-90 units they fuse at 16px and the face becomes a minus/no-entry sign.
- [x] **Merged into L59 (evidence).** A lone narrow top bump on a compact block reads as a funnel/chimney (L44); making it flat and wide (about 2.4:1) restored the toy-stud reading without adding a second idea.
