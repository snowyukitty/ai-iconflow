---
slug: snowy-twitch-bot-fox-badge
date: 2026-07-18
project: snowy-twitch-bot
targets: web,pwa,tray,electron
essence: companion
style_family: mascot
signature_device: single-ear ownable color accent (left ear brand periwinkle, right ear ice-blue) on a closed-happy-eye fox badge face
device_family: ownable-geometry
device_detail: asymmetric two-tone ear fill, no extra decorative marks
concept_lens: object-mascot-vs-metaphor-chat-bubble-chin-vs-unexpected-crop-peeking-over-snowdrift
cliche_avoided: generic animal silhouette / an unrelated cute mascot bolted onto a creator brand; also avoided re-using the previous abstract S-ribbon initial the owner explicitly disliked
status: shipped
scores_first: legibility=3 distinctiveness=3 balance=4 color=4 scalability=3 craft=3
scores_final: legibility=4 distinctiveness=4 balance=5 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
Replaced the 2026-07-11 abstract S-ribbon icon (casebook/2026-07-11-snowy-twitch-bot.md) after the owner (snowy_smile) said it read as a plain letter and did not represent their identity or the brand.json snow-fox mascot. Three lenses reached the bake-off: a fox head tapering into a speech-bubble chin (dual reading), a symmetric front-face fox badge matching the existing persona.json kaomoji expression (=^-w-^=), and a fox peeking over a snowdrift horizon (unexpected crop). The bubble-chin concept blurred into an unreadable blob at 16px and the peeking concept collided with a generic tent/mountain silhouette at small sizes, so the front-face badge won. Its first pass used two tiny snow-dust dots as the signature accent, which failed the two-pixel-at-16px bar (L16); replacing them with a single whole ear filled in an ownable ice-blue accent (asymmetric vs. the brand-periwinkle left ear) fixed distinctiveness and scalability together.

## What failed first
The bubble-chin concept (fox head tapering into a speech-bubble tail) scored
legibility=3 in the bake-off: at 16px the tapered chin and the closed eyes
merged into one soft white blob with a single dark speck, so the "dual
reading" never resolved into either "fox" or "chat bubble". The
peeking-over-snowdrift concept was even weaker at small sizes — its two
triangular ear tips above a flat horizon line reads as a generic
tent/mountain/roof pictogram (an L9-style silhouette collision), not a fox,
so it was dropped before a full review pass. The front-face badge that won
still needed one correction after `check`/`review`: its first signature
device was two small circles (r=22, r=14 on the 1024 grid) dusted near the
right ear tip. At 16px those are sub-pixel — they either vanished or read as
stray noise next to the ear, which is exactly the failure L16 predicts for
an accent under ~128 units. Swapping the whole right-ear fill to a single
saturated ice-blue (`#9DE7F0`) against the brand-periwinkle left ear turned
the same "one asymmetric accent" idea into a shape large enough (the full
ear triangle, well over 128 units) to survive 16px, lifting distinctiveness
and scalability from 3 to 4 without touching legibility, balance, or color.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] When a prior icon is rejected specifically for feeling abstract/unrelated to the owner's identity, do not re-run the same abstract-mark playbook with a different shape — run the mascot/character style family directly against the owner's own established identity signals (their persona kaomoji, self-chosen mascot field) before diverging into other lenses. (Covered by L10's identity-owner rule.)
- [x] A tiny multi-dot decorative accent (e.g. tack-on snow dust) is a common first-draft mistake for a snow-themed accent; a single whole-shape color swap (e.g. one ear tinted differently) survives 16px far more reliably than 2-3 small dots of the same total ink. (Covered by L16 and reinforced by L20.)
