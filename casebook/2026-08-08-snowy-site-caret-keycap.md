---
slug: snowy-site-caret-keycap
date: 2026-08-08
project: snowy-twitch-bot
targets: web,pwa
essence: keystroke
style_family: flat-geometric
signature_device: a keycap drawn in perspective with a stepped front lip, its caret command prefix punched clean through so the glyph is part of the silhouette
device_family: object-silhouette
device_detail: 604-unit top face over a 904-unit base; caret as a 160-unit evenodd cut, not an overlaid glyph
concept_lens: object-keycap-vs-ownable-geometry-folded-paper-vs-object-chat-chip
cliche_avoided: the bare caret on a gradient tile (monogram trap); the project's own snow-fox mascot (that is the app icon); a snow peak or snowdrift horizon (already proven to collide with tent/mountain/roof on this project); terminal prompt, speech bubble, snowflake
status: shipped
scores_first: legibility=4 distinctiveness=3 balance=4 color=5 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=5 color=5 scalability=4 craft=4
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
The marketing site for snowy-twitch-bot needed its own favicon, explicitly only
*weakly* related to the Snowy identity — the snow-fox badge
([2026-07-18](2026-07-18-snowy-twitch-bot-fox-badge.md)) is the desktop app's
icon and the owner did not want the site wearing it too. That constraint turned
out to be the useful part of the brief: with the mascot off the table, the mark
had to come from what the site is actually *about*, which is the command scheme
— three prefixes (`<lang>:`, `^`, `^^`) chosen so the bot never collides with
the `!` bots a channel already runs. Six concepts were considered and three
reached a bake-off (a keycap, a folded-paper caret, a pointed chat chip). The
keycap won because it is the only one whose blacked-out silhouette names a
specific object while still being *about typing*: the caret is punched clean
through the cap, so the product's own glyph is part of the silhouette rather
than a chevron sitting on a tile.

## What failed first
Two of the four strongest-sounding directions were killed at concept stage by
this project's **own** earlier case: a snow peak / snowdrift horizon is a proven
tent-mountain-roof collision here (L9), and the owner had already rejected an
abstract letter-like mark in
[2026-07-11](2026-07-11-snowy-twitch-bot.md) — which is exactly what a bare
caret would have been (L21/L22). Reading the project's prior cases before
drawing saved two full bake-off rounds.

The first bake-off still failed, and all three candidates failed the same way:
each was a mark parked *inside* a tile, so at 16px the object shrank to a few
pixels of mush and only the tile colour survived. The cream-tiled candidate was
worse still — it vanished into a white tab and left a floating chevron, the
monogram trap made literal. Going full-bleed (the yorozora lesson) bought the
pixels back.

The second failure was subtler and is the one worth remembering. The full-bleed
cap was nearly square, so although it read fine in colour, its **alpha
footprint** was a rounded square with an up-chevron — i.e. a generic "scroll to
top" button (L9), which put distinctiveness at 3. Nothing about the glyph was
wrong; the container was. Widening the base to 904 units against a 604-unit top
face, so the cap is unmistakably drawn in perspective, made the footprint name a
keycap and lifted distinctiveness to 4 without touching the caret.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] When a project already has a mascot app icon, a sibling site favicon should be sourced from the site's SUBJECT, not a weaker variation of the mascot: the owner asked for a mark only weakly related to the brand, and the commands page's own caret prefix supplied a specific object (a keycap) that the mascot family could never have reached.
- [x] A full-bleed rounded object still reads as 'a rounded square' until it has a visible perspective taper. Widening the base to 904 against a 604 top face is the single change that turned the alpha footprint from a generic up-chevron button (an L9 collision) into a keycap, lifting distinctiveness 3 to 4 with no change to the glyph.
- [x] Prefer punching the glyph THROUGH the object over laying it on top: the cut version and the overlaid version were indistinguishable at 16px, but only the cut one put the glyph into the blacked-out silhouette, which is the axis the bake-off is judged on (L3).
