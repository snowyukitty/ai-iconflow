---
slug: waywake-wake-sail
date: 2026-10-05
project: Desktop seafaring life-sim game (Godot, Windows): plan a voyage with a small crew and see where you have sailed
targets: electron
essence: wake
style_family: flat-geometric
signature_device: the wake is the sail: one amber sail streams back past the stern and leaves the tile edge as the wake
device_family: object-silhouette
device_detail: side-view ink hull with a raked bow under a single amber sail whose foot runs aft and exits the left tile edge as a 190-unit wake band; 88-unit sail-hull gap
concept_lens: object-metaphor
cliche_avoided: anchor, ship's wheel, compass rose, pirate flag, sailing-ship clip art, letter W
status: shipped
scores_first: legibility=4 distinctiveness=3 balance=4 color=4 scalability=4 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4
iterations: 2
---

## Summary
A Windows desktop icon for a quiet, lantern-lit seafaring life-sim whose signature
device in-game is the "wake line", an amber trail on a night chart recording routes
actually sailed. The brief's hypothesis was a small hull trailing a curved amber wake
across a night-sea tile. It failed: every vessel-plus-trail layout named a tool. The
shipped mark fuses the trail into the boat: a single lantern-amber sail whose foot runs
aft past the stern and leaves the tile's left edge as the wake, over a pale side-view
hull with a raked bow, on a deep night-sea rounded tile. A device-free control (the
same boat with an ordinary ink sail) read as a generic sailboat, and the neighbourhood
instrument fingerprinted it as a plain filled tile. That proves the sail-into-wake
fusion carries the identity. The winner's nearest neighbour sits at 0.31 (radius 0.12);
a generic sailboat drawn into the project's avoid set sits at 0.37. The Review Lab was
not operated (headless session): the static sheet plus the exact ICO frames 16-256 on
white, gray and near-black were inspected and recorded as a source-bound approved fallback.

## What failed first
- **Round 1 (hypothesis, tile):** a pale top-down hull with an amber ribbon trailing to
  the lower-left read as a **paintbrush** at 128px (pointed pale tip = bristles, narrower
  amber band = handle). The Kelvin V version read as a drafting compass or a figure with
  legs, and a chart-card version was busy and still a pen. Visual-silhouette strip was
  the bare tile for all of them (L8).
- **Round 2 (viewpoint changes):** diverging wake arms became a **rocket/shuttlecock**,
  a wake widened to 2.5x the beam became a **broom**, and a perspective wedge toward the
  viewer became a **vase/lamp**.
- **Round 3:** a larger top-down boat with a deck inset plus twin wake arms was a
  **rocket with exhaust**; a side-view hull with a lantern mast was a **joystick**.
- **Round 4 (fusion):** the sail-into-wake shape was the first concept to name a specific
  thing (a sailboat whose sail streams into the sea). Wake bleeding off the tile edge beat
  a wake tapering inside the tile, which collapsed back toward a generic lateen sailboat.
- **Review pass 1:** the hull was a symmetric trapezoid with a curved top and read as a
  white **bowl** at 256px (distinctiveness 3, craft 3). A straight sheer rising to a
  raked, pointed bow fixed it; `check` was clean on both passes.
- **Delivery note:** the `electron` target writes into `<output>/build/`, so a config
  output that already ends in `build` nests the files one level deeper.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] **Promoted as L60.** A small pointed vessel trailing one long band reads as a tool (paintbrush, rocket exhaust, broom, comet) at every angle; when the identity is a trail, fuse the trail into a part of the vessel that already names it (the sail) instead of attaching it behind.
- [x] **Merged into L59 (evidence).** A side-view hull drawn as a symmetric trapezoid with a curved top reads as a bowl at 256px; a straight sheer rising to a raked, pointed bow restores the boat noun without adding detail.
