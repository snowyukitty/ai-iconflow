---
slug: iconflow-emote-family
date: 2026-10-05
project: IconFlow's own public-domain chat emote set (55 members)
targets: emote
essence: react
style_family: mascot
signature_device: every face sits on the squircle app-icon card IconFlow ships
device_family: semantic-style-grammar
device_detail: 832-unit rx-300 card with a 52-unit ink rim; 84-unit features; drops, hats, bursts and a Z deliberately break the outline
concept_lens: clean-room-user-job
cliche_avoided: round yellow vendor faces, sticker borders, single-feature variants
status: reviewed
scores_first: legibility=4 distinctiveness=3 balance=4 color=4 scalability=3 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
iterations: 3
---

## Summary
A set of 24 chat reactions had to read as one family and still give every member its own expression at the 22 and 28 pixels chat uses, on white and dark at once. Two directions were probed on the hardest four members (joy, sob, heart eyes, thumbs up); the rounded-square card won over a round sticker head because it held on both grounds and owned a silhouette no vendor face has. iconflow family then held the set together: it found the 16 faces' shared card from their fields and gated siblings on what the card does not explain.

## What failed first

**Probe — sticker head rejected.** A round head with a white sticker border
popped on dark chat but its border vanished on white, so the face shrank, and
at 22 px it read as any vendor's emoji. The squircle card with a 52-unit ink
rim held on both grounds. The probe's thumbs-up was also wrong: a vertical
thumb centred on a fist with knuckle lines on the right reads as a raised
index finger ("one"). The shipped thumb rises from the fist's left side.

**Pass 1 — distinctiveness 3, scalability 3, craft 3.** Four members failed
by eye on the 22/28 px chat sheet: the heart was clipped by the canvas
(craft); folded hands read as a pencil or a candle (distinctiveness); the
party popper's confetti broke into specks at 22 px (scalability); the
mind-blown burst read as a crown, which is in the generic collision set.
Each was redrawn: a heart that fits, two palms with a centre seam and cuffs,
a broad cone with three bold confetti pieces, an irregular burst.

**Pass 2 — one twin.** `iconflow family` measured the set. Raw 16 px
distances put every face within 0.15 of every other and near the generic
rounded square — the card is most of the ink. On the residual from the
faces' shared card, smile/wink sat at 0.31, under the 1/3 floor, with the
next pair at 0.51. The 22 px sheet agreed: the only difference was one closed
eye. The wink was redrawn with a squeezed chevron eye *and* an open lopsided
grin; the set then had no twins, closest pair cool/eye roll at 0.50.

**Pass 3 — growing to 55.** At the owner's request the set grew by 31: 16
faces, 6 hands and 9 symbols. By eye on the chat sheet, five failed first:
the halo hid behind the head, the handshake was three small pills, the
melting face read as a tombstone, the flexed arm as a snake, and the raised
hands were clipped by the canvas. All were redrawn. The family check then
found one twin: the first *flushed* was the eye roll with pink cheeks
(0.332). Redrawn with raised brows and a wobbling mouth, it cleared the floor;
the nearest pair of the 55 is eye roll / nerd at 0.39, down from 0.50 at 24
members. Two members tripped the maskable safe-zone audit by a point or two
and were pulled in.

**Pass 4 — the hands, after owner feedback.** The owner judged the hands
weaker than the faces. Measured at 28 px they were: half the faces' mass
(0.34 against 0.65), half again the ink share (0.51 against 0.34), and four
broke into three or four pieces, because every finger carried its own rim.
All ten were rebuilt with the faces' construction — one silhouette, one
outer rim, creases inside — and fingers at least 120 units wide: mass 0.50,
ink 0.37, no thin parts, every hand clean under `check`, no twins. The OK
hand now even joins the faces' carrier group. Two first attempts failed by
eye and were redrawn: folded hands with thumbs read as a metronome, and a
union of two clapping palms read as an apple until the front palm kept its
own outline.

**Review status.** Every member passes `iconflow check` with no warning. The
scores above are the agent's review on the chat sheets; the owner has not yet
scored the set, so the case is `reviewed`, not `approved`.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] In a family on a shared carrier, compare siblings on their residual from the carrier, never on raw distance: the carrier is most of the ink, so two different faces on one head are 0.02 apart.
- [x] Never let one feature carry the whole difference between two siblings: a wink that is a smile with one eye closed differs by two pixels at 22px. Change at least two features, or the silhouette.
- [ ] A probe on the hardest few members (the most confusable pair, the colour detail, the one non-face) decides a family's grammar faster than drawing all of it.
- [ ] A family's nearest pair moves closer as it grows (0.50 at 24 members, 0.39 at 55): budget new members against the twin floor, and redraw the closest pair before adding the next member.
- [x] A mark built from parts is one silhouette with one outline: outline the union once and draw the joins as creases. Separately rimmed fingers made the hands half as heavy and half again as inky as the faces at 28px.
