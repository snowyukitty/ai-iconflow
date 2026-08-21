---
slug: yukoe-live-language-controls
date: 2026-08-10
project: Yukoe compact Live controls
targets: ui-buttons,tray-review
essence: switch
style_family: flat-geometric
signature_device: Language-punched voice ticket and phrasebook state family
device_family: object-silhouette
device_detail: A broad call wing marks on, a deep shut-mouth notch marks off, and an open or closed phrasebook carries translation state.
concept_lens: object-verb
cliche_avoided: generic speaker with slash; plain swap arrows
status: shipped
scores_first: legibility=3 distinctiveness=3 balance=4 color=5 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=5 color=5 scalability=4 craft=5
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
Six compact EN, Japanese, and automatic-translation state icons. The winning voice ticket keeps language identity punched through one silhouette while its edge performs the state change; the phrasebook pair uses open and closed posture without generic arrows.

## What failed first
The first TTS alternatives used a small megaphone handle or a listening-shell
curve; at 16px the handle muddied the silhouette and the shell resembled a
question mark. The first translation alternatives stacked relay cards, which
collapsed into generic overlapping rectangles. Moving state to the ticket's
outer edge and translation to an open/closed phrasebook fixed legibility and
distinctiveness. A fixed dark fill also vanished on the dark review row, so the
source preview gained a two-pole luminance gradient while the shipped UI uses
the SVG alpha as a `currentColor` mask.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For adjacent automation toggles, preserve one object silhouette per feature and express state through a large outer-edge verb; tiny overlays and slash badges disappear first at 16px.
