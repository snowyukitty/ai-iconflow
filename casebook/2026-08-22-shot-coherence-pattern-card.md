---
slug: shot-coherence-pattern-card
date: 2026-08-22
project: Production tool that keeps many separately generated video shots coherent
targets: web
essence: coherence
style_family: flat-geometric
signature_device: Container is the object: a punched pattern card - the loom's program - whose three punches sit on a twill diagonal so one geometry reads as weave binding points and as film perforations at once
device_family: container-as-object
device_detail: 992x848-unit full-bleed card on the 1024 grid; 280-unit bevelled bottom-left registration corner; three 150x215-unit perforation slots cut with fill-rule=evenodd, stepping down 170 units with 150-unit lateral gaps (2.3px at 16px)
concept_lens: system-abstract-the-machine-s-program-fused-with-object
cliche_avoided: clapperboard, film reel/spool, play triangle, camera/lens/aperture, AI sparkles, gradient blobs, AI chip/brain/node graph, literal thread-and-needle, bare monogram; and - the expensive one - the weaving shuttle itself
status: shipped
scores_first: legibility=2 distinctiveness=4 balance=3 color=4 scalability=2 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=5
iterations: 11
---

## Summary
<!-- One paragraph: the brief, the winning concept, why it won. -->
The product is a production tool for generated video; the
user's job is to keep one film coherent across dozens of separately generated
shots, and its name joins a film word to a weaving word. The one-word essence is
**coherence**. The owner's own hypothesis was interlacing - two sets of strands
crossing over-under into a woven frame whose crossing pattern doubles as film
perforations - offered explicitly as a starting point to beat. It was beaten.
The shipped mark is a **punched pattern card**: the Jacquard card is the loom's
*program*, the single artefact that makes thousands of separate threads produce
one coherent cloth, which is precisely what the product does with separately
generated shots. Three film-perforation slots are cut clean through a full-bleed
film-gold card on a twill diagonal, and the bottom-left corner is bevelled as a
registration cut. The dual reading the brief wanted survives intact and in one
geometry: the punches are simultaneously a weave's binding points and a film
strip's perforations, and it is the *diagonal stagger* - the twill line - that
keeps them from reading as a filmstrip. It won because it was the only candidate
in eleven rounds to clear both gates at once: an ownable, nameable silhouette and
open counters at 16px.

## What failed first
<!-- What the earlier passes got wrong and which change fixed it. This is the
     raw material for future lessons - be specific (axis, size, shape). -->
Nine of eleven bake-off rounds were failures, and legibility and distinctiveness
failed in alternation rather than together.

**The interlacing hypothesis died first, on distinctiveness.** A 2x2 woven frame
(bake1 c-interlace) and an asymmetric one-weft/two-warp lattice (bake2
e-interlace2) both rendered as a **hashtag** at every size; a single broad
crossing (bake4 m4-lock) rendered as a **plus/dagger**. Two crossing band systems
have no silhouette that is not already a system glyph.

**The weaving shuttle - the obvious object - died across four rounds, on
distinctiveness, and it died by changing its noun.** Plan view read as a
**hexagonal link**; with a bobbin post, a **power outlet**; with a pointed prow,
an **arrow**; as a hull, a **bucket**; as an open cradle, a **bowtie**; in side
view, a **smile**; with a yarn eye, a **price tag** (already spent on
bargain-hunter). The root cause is proportion, not styling: a real boat shuttle
is about 5:1, and every compression to something that fits a 1:1 tile renamed the
object. Decisive confirmation came from IconFlow's own
`gallery/cases/loom-shuttle` exemplar, which renders as an **eye** - a reading
that would have landed this mark squarely on the brief's banned lens/aperture
cliche. Killed per L9 rather than iterated.

**The braid family died on legibility.** A three-crossing horizontal plait
(bake4 m1) and vertical twists (bake4 g, bake5 p1-p4) produced the best visual
silhouettes of the whole exercise - genuinely woven, genuinely ownable - and then
turned to grey soup at 16px with every counter closed, even at 250-unit band
widths. Diagonal geometry spends its pixel budget on anti-aliasing (L17, L19);
the 128-unit counter budget cannot be met on a diagonal inside a 1024 grid.

**The "many strands become one cloth" topology died on collisions.** Converging
strands read as an **arrowhead** (bake1 b-fell); parallel strands under a solid
mass read as a **crown/fork** (bake6 q3); a squared serpentine weft read as the
**digit 2** (bake6 q1); a slab with a column of equal holes read as a
**filmstrip/SIM** (bake1 d); the same slab tapered read as a **building**
(bake6 q2).

**What fixed it** was two changes made together. First, orthogonal construction
with large `fill-rule="evenodd"` cuts - abandoning every diagonal band - which
lifted legibility and scalability from 2 to 4 by letting the counters sit on the
raster grid. Second, **staggering** the repeated element: three equal holes in a
row are a filmstrip, and the same three holes offset onto a diagonal are a twill
weave, which recovered distinctiveness without costing a single pixel. The
bevelled bottom-left corner was the last change, added for L29 (a full-bleed
container needs one measurable non-square feature); it was placed bottom-left
rather than top-right specifically so it would not read as a page dog-ear, and
diagonally clear of the punch line so the two devices never group.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] **Promoted as L59.** An object whose natural aspect ratio is 5:1 cannot be an icon: compressing a weaving shuttle to 2:1 changes the noun every time (cap, hexagonal link, power outlet, arrow, bucket, bowtie, smile, price tag). Check the object's real proportions against 1:1 before spending a bake-off on it.
- [x] **Merged into L40.** Interlace is a collision factory. Two crossing band systems land on a hashtag, a plus, a dagger or a chain link; braids and twists own a beautiful silhouette at 128px and close every counter at 16px because diagonal geometry cannot hold the 128-unit budget. If a brief asks for a weave, budget orthogonal construction from the start.
- [x] **Merged into L27 (generalized).** When a repeated-element idea (perforations, warp threads) must survive 16px, stagger it. A row of equal holes is a filmstrip; the same holes offset onto a diagonal read as a twill weave and stop colliding.
