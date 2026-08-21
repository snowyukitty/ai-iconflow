---
slug: iconflow-canopy-haypile-demo
date: 2026-08-20
project: IconFlow Canopy Haypile (examples demo)
targets: web,tauri,electron,tray
essence: descend
style_family: mascot
signature_device: a low-eared pika descends with its hay store under a deep three-panel canopy on two unequal risers
device_family: character-silhouette
device_detail: 492x234 unit canopy, 36-unit warm panel seams, 68-unit hem scallops, 130 units of clear air above the ears, two 64-unit risers of unequal length
concept_lens: object-mascot
cliche_avoided: generic flow arrow / AI sparkles / umbrella / blue-purple SaaS monogram
status: shipped
scores_first: legibility=3 distinctiveness=3 balance=4 color=4 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
iterations: 3
---

## Summary
<!-- One paragraph: the brief, the winning concept, why it won. -->
The sibling demo to [Balloon Haypile](2026-08-20-iconflow-balloon-haypile-demo.md):
the same request named two objects, "a balloon or a parachute", so the canopy
line was carried through to a shipped mark of its own. Essence `descend`, user
job "bring one design safely down onto every platform surface". The pika, its
ears, the lagoon hay cove and the full palette are unchanged; the three carried
petals become a three-panel canopy overhead on two unequal risers. It ships
alongside the balloon rather than instead of it: its visual silhouette survives
one size step further down (48px, against the balloon's 64px) because a panelled
dome carries more warm-paper mass than a balloon's outline ring, while the
balloon reads as one bolder single idea.

## What failed first
<!-- What the earlier passes got wrong and which change fixed it. This is the
     raw material for future lessons — be specific (axis, size, shape). -->
P1 lost distinctiveness to a silhouette collision. Its canopy was a shallow
solid dome (492x234 with 52-unit hem scallops) sitting close over the pika, and
blacked out it named a mushroom, an umbrella or a table lamp before it named a
parachute. The risers started inboard of the hem ends and ran only about 150
units, so the attachment was hidden under the canopy outline and the two lines
read as a single stem.

P2 fixed the noun with two changes: 36-unit warm panel seams drawn over the
gores, so the canopy reads as separate fabric panels instead of a cap, and
68-unit hem scallops. The risers moved out to the hem ends and were given
unequal lengths and angles, which reads as drift as well as suspension.

P3 fixed the relationship. P2 still had only 115 units between the scallop
bottoms and the ear tops, and at 128px the pika looked like it was wearing the
canopy. Raising the canopy and dropping the pika to scale 0.63 opened 130 units
of clear air, which is what makes the two risers legible as the only thing
joining canopy to load.

The tray then failed on its own terms, twice. Reusing the shipped brand tray's
single-pass graphite strokes shrank every warm shape by half the stroke width,
so the 64-unit risers became dark bars and the head lost most of its warm area
on a light bar. Redrawing the halo as a wider graphite pass with the master's
exact geometry restored on top fixed it. The first eye cut was also both too
large (92 local units, about two output pixels at 16px) and placed on the seam
where the muzzle stub meets the head, where it read as a bite out of the
contour rather than an eye; 62 units moved 44 units inboard reads correctly.

Known limitation, recorded rather than hidden: in the 16px tray reduction the
warm risers merge with the warm head, so the tray drifts toward reading as a
hot-air balloon. The master, every web/desktop target and the 32px tray keep the
parachute reading.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A dome over a body is an umbrella, a mushroom or a table lamp until two things are true: the canopy is panelled so it reads as fabric rather than a solid cap, and there is at least two output pixels of clear air between hem and load. Air is what separates hanging-from from wearing.
- [x] Shroud lines are the noun. A single central stem makes an umbrella; two unequal risers converging from the hem's outer ends onto an off-centre load make a parachute and read as drift at the same time.
- [x] In a tray source, a single graphite stroke is not a halo - it eats the shape it is meant to protect, because a centred stroke shrinks the fill by half its width. Draw the halo as a wider stroke first, then restore the master's exact geometry on top, so the tray is the same mark wearing a ring rather than a thinner mark.
- [x] Place a template's transparent feature cut away from any join between two shapes. On the muzzle-to-head seam a 62-unit eye hole read as a bite taken out of the contour; the same hole moved 44 units inboard read as an eye.
