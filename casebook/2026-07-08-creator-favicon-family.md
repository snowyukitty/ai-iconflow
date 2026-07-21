---
slug: creator-favicon-family
date: 2026-07-08
project: the creator fansite per-page favicon family
targets: web
essence: cute
style_family: mascot
signature_device: one shared vector chibi persona face (scalloped bangs + twin black headdress bows as silhouette bumps); per-page expression + badge-hue swap
cliche_avoided: raster emote rescaled into a badge (16px mush); unrelated per-page glyphs (camera for IG, gamepad for game)
scores_first: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
Replaced the creator fansite's single raster-emote favicon with a five-page
family (home/game/artwork/IG-archive/404). Bake-off pitted a tighter raster
emote crop, a hand-drawn vector chibi persona face, and a bold kana letterform
against each other. The vector face won: at 16–32px it kept crisp structure
(dark bow-bumped hair cap, big eyes, blush) where the 112px raster emote
downsampled to mush, and its silhouette (head + twin headdress-bow bumps) was
ownable where the emote badge was a generic circle. The family swaps only the
expression (default / confident sunglasses / star eyes / closed eyes / sad+tears) and
badge hue (pink / sky / lavender / apricot / mauve) over shared geometry
single-sourced in a generator script kept in the consuming repo.

## What failed first
The first raster crop aimed at the face landed on mostly hair (small 112px
source, face low in frame) — a 3×3 crop-grid contact sheet fixed placement
faster than eyeballing single crops. The kana letterform finalist read as a
Latin "U + heart" at small sizes, not the intended kana — kanji/kana letterforms need their
identifying stroke exaggerated or they collapse into Latin lookalikes. First
vector pass shipped 16-unit mouth strokes on a 1024 grid; `check` flagged
them (craft 3→4 after thickening to 24). The 404 page's copy stars the rabbit
mascot, but the favicon stayed the sad-expression persona to keep one identity owner
across the family.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For a multi-page favicon family, differentiate pages by badge hue + expression on one shared vector mark - hue is the only channel that reliably reads at 16px; a vector redraw of key identity traits beats embedding the raster emote (promoted as L13)
