---
slug: local-shopping-watch-tray
date: 2026-07-29
project: Local Shopping Watch Tray
targets: tray
essence: sentinel
style_family: flat-geometric
signature_device: an asymmetric lowered noren panel marks a watched price crossing its threshold
device_family: object-silhouette
device_detail: a two-pixel-safe lowered right curtain panel within one continuous Japanese shop-curtain silhouette
concept_lens: object-metaphor
cliche_avoided: shopping cart, notification bell, magnifier/radar, generic price tag, bare J monogram
status: shipped
scores_first: legibility=4 distinctiveness=4 balance=4 color=3 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=5 color=5 scalability=5 craft=5
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
The brief was a Windows tray companion for local shopping-watch health
and control. The noren, lantern, and binocular concepts were compared; the noren
won because its Japanese-market shop silhouette was specific to the product, and
the lowered right curtain panel expressed a watched price crossing its threshold.

## What failed first
The first color version scored 3 on color and failed the automated mid-gray
background check. Adding a 40-unit warm-paper stroke around the single silhouette
restored contrast on light, dark, and mid-gray taskbars without closing the two
panel gaps at 16 px.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A transparent tray mark that must survive light and dark taskbars can use a subpixel warm-neutral edge around one bold object silhouette; solve cross-background contrast without adding a full tile.
