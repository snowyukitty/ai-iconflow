---
slug: iconflow-balloon-haypile-demo
date: 2026-08-20
project: IconFlow Balloon Haypile (examples demo)
targets: web,tauri,electron,tray
essence: lift
style_family: mascot
signature_device: a low-eared pika drifts with its hay store under one large three-gore balloon on a thick tether
device_family: character-silhouette
device_detail: 336x386 unit three-gore balloon with a 40-unit warm outline, tethered by a 72-unit cord, held 139 units clear of the ear
concept_lens: object-mascot
cliche_avoided: generic flow arrow / AI sparkles / robot or brain / blue-purple SaaS monogram
status: shipped
scores_first: legibility=3 distinctiveness=4 balance=3 color=4 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
<!-- One paragraph: the brief, the winning concept, why it won. -->
A demo variant of the IconFlow product mark, commissioned as "keep the mark we
like, but let the pika hold a balloon or a parachute so it feels like flow".
The brief kept the shipped Petal Haypile brief and swapped its essence from
`gather` to `lift`; the user job became "carry one design up to every platform
surface without redrawing it". Four concepts were drawn (three-gore balloon,
solid balloon, small carried parachute, overhead parachute canopy) and a second
round added a large tethered balloon. The winner is a single 336x386 unit
three-gore balloon on a thick tether, with the pika, its ears, the lagoon hay
cove and the full palette carried over unchanged. It won because it is the only
candidate whose *visual silhouette* changes: the shipped mark and every
small-accent variant black out to the same rounded blob, while balloon + tether
+ creature names a specific scene down to 48px.

## What failed first
<!-- What the earlier passes got wrong and which change fixed it. This is the
     raw material for future lessons — be specific (axis, size, shape). -->
Round 1 assumed the job was to swap one carried object for another and drew the
balloon into the pocket the three petals already occupied (about 240x250 units).
On the bake sheet it behaved exactly like the petals: fine at 128px, a coloured
speck at 16-24px, and invisible in the silhouette strip. The small carried
parachute (b) was worse — its 81-unit hem scallops mushed below 64px and the two
48-unit shroud lines fell under one output pixel, so it read as a mushroom near
the muzzle. The upper-right pocket is bounded by the core's shoulder at
(682, 391); every attempt to grow the balloon inside it closed the gap to that
shoulder to 28-70 units, well under the 128-unit two-pixel budget. The fix was
not geometry tuning: the composition had to be re-cut so the flying object
becomes the second mass, with the pika scaled to 0.65 and dropped, which bought
the balloon 336x386 units and a 139-unit clearance from the ear.

Round 2's first master then scored legibility 3, balance 3, scalability 3. Its
mark sat 54 units right of canvas centre, and its 28-unit warm outline — the
only thing separating a coral/gold/violet balloon from a graphite card in a
luminance silhouette — fragmented into dots by 48px and was gone by 32px.
Centring the mark group and taking the outline to 40 units lifted all three
axes to 4 without touching the concept.

The tray source failed twice, separately from the master. Built from the same
graphite-halo pattern as the shipped brand tray, `alpha` mode produced a
featureless two-lump blob and `contrast` mode produced speckle, because the
source is opaque everywhere its halo reaches. Punching the balloon's two gore
seams and the hay-cove seam as transparent cuts fixed the template and destroyed
the colour tray — the balloon read as a "0" and the cove was sliced off. Cutting
back to a single broad eye hole (86 local units, about one output pixel at 16px)
gave a template that keeps balloon, tether, body and face while the colour tray
returned to full brand fidelity.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A carried accent sized like the one it replaces inherits its 16px failure: three petals and a same-size balloon both vanish. Growing the carried object until it is the second mass of the composition is a concept change, not a polish step.
- [x] When a coloured accent is separated from the card only by a warm outline, that outline IS its silhouette. At 28 units the ring fragmented by 48px; 40 units carried it to 48px. Budget an outline that must survive as silhouette at two output pixels, not one.
- [x] Punching feature cuts into a tray source trades the colour asset for the template. Two gore seams plus a hay-cove seam made the macOS template legible and wrecked the 32px colour tray; one broad eye cut bought a readable template at no visible colour cost.
