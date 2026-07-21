---
slug: codex-handbook
date: 2026-07-07
project: codex-handbook
targets: web,pwa,shortcut
essence: decide
style_family: flat-geometric
signature_device: folded guide-card corner plus negative-space C route
cliche_avoided: AI brain, robot head, sparkles, terminal chevron, blue-purple gradient
scores_first: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=4 craft=4
iterations: 2
---

## Summary
Codex Handbook needed a favicon and shortcut icon for a calm technical learning
site. The winning concept was a folded guide-card with a negative-space C-shaped
route and one amber checkpoint. It won over a bookmark and a tilted document
stack because its silhouette stayed legible at 16px while avoiding generic AI,
terminal, or documentation icons.

## What failed first
The first folded-card pass used a drop shadow and placed the folded corner too
close to the outer edge. Legibility was acceptable, but `iconflow check` flagged
maskable safe-zone risk because the visible footprint extended too far outward.
Removing the shadow and shrinking the card into the safe area fixed the audit
without losing the folded-corner signature device.

## Lessons
- [x] For technical handbook sites, choose the learner job of deciding/navigating over generic AI or terminal symbols; remove shadows before maskable review because they inflate the visible footprint.
