---
slug: private-media-route-fan
date: 2026-08-09
project: Private media route finder
targets: web,electron,tray
essence: reveal
style_family: flat-geometric
signature_device: a full-bleed coral folding fan with one broad off-axis missing leaf
device_family: object-silhouette
device_detail: violet hinge, 128-unit-minimum reveal slit, and a 42-unit contrast edge
concept_lens: object-metaphor
cliche_avoided: bare monogram, play button, film reel, eye, keyhole, literal category imagery, sibling ticket mark
status: shipped
scores_first: legibility=4 distinctiveness=3 balance=3 color=3 scalability=4 craft=3
scores_final: legibility=4 distinctiveness=5 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
A privacy-sensitive source-routing tool needed an ownable reveal mark across
web, desktop, and tray targets. A folding fan won the silhouette bake-off
because it names a specific object without literal category imagery. One broad
missing leaf and a violet hinge make the object recognisable at favicon size
and in the transparent tray treatment.

## What failed first
The first finalist put a nearly centred reveal slit directly above the round
hinge. At 16/32px those otherwise valid devices grouped into an exclamation
mark, dropping distinctiveness, balance, and craft to 3. Moving the slit more
than two output pixels off the hinge centerline restored the folding-fan read.
The first coral endpoint was also too quiet on mid-gray, while its darker edge
made the narrow leaf recede on the monochrome target. A 42-unit plum edge and
a brighter coral endpoint cleared QA across the exact web, desktop, maskable,
and tray renders.

## Delivery correction
Rebuilding the `.ico`, recreating the `.lnk`, and clearing Explorer's cache did
not refresh the desktop while `IconLocation` still reused the canonical icon
path. A content-addressed `shortcut-icon-<sha12>.ico` alias changed that path;
after shortcut recreation, read-back metadata and a Shell extraction from the
actual `.lnk` both confirmed the new pixels.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] When a broad negative-space cut ends near a detached circular hinge, test the pair as punctuation at 16px; offset their centerlines by at least two output pixels before polishing.
- [x] Recreating a Windows `.lnk` is not a cache bust when `IconLocation` keeps the same `.ico` path; install a content-addressed alias, read the shortcut back, and verify the Shell-resolved result.
