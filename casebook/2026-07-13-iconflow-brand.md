---
slug: iconflow-brand
date: 2026-07-13
project: IconFlow product identity
targets: web,tauri,electron,tray
essence: proof
style_family: flat-geometric
signature_device: continuous master rail through an off-axis square proof gate, resolving into a pixel-step terminal
device_family: ownable-geometry
device_detail: orthogonal master rail, 256-unit proof gate, 128-unit counter, two-step raster terminal
concept_lens: verb-system
cliche_avoided: AI sparkle / robot / brain / generic arrow / check / bookmark / blue-purple gradient
status: shipped
scores_first: legibility=3 distinctiveness=4 balance=4 color=5 scalability=3 craft=4
scores_final: legibility=4 distinctiveness=4 balance=4 color=5 scalability=5 craft=5
iterations: 2
---

## Summary
IconFlow needed a product mark tied to its actual job: turning app intent and one semantic SVG into a proven, target-ready icon family. Five lenses produced three SVG finalists. Flow Gate won because its interrupted rail and stepped silhouette stayed more ownable than the generic aperture and conventional F monogram; a 64-unit refinement pass made the proof counter deliberate at 16px. The final 23-file family was shipped through IconFlow's own approved `brand/iconflow.toml`, including the dedicated semantic tray source.

## What failed first

- In pass 1 the 224-unit gate was rotated eight degrees. At 16px its counter
  blurred into the coral edge and the gate read as a decorative red fleck
  (legibility 3, scalability 3), even though the large render looked refined.
- The fix was one structural change: remove the rotation, express the gate's
  asymmetry through its position, align the rail and gate to a 64-unit rhythm,
  enlarge the gate to 256 units, and make its counter exactly 128 units. The
  pixel zoom then showed a deliberate four-pixel gate with a two-pixel counter.
- Rendering the full app card as a macOS template initially risked reducing the
  identity to its rounded-square alpha footprint. The shipped family adds
  semantic IDs to `master.svg` and a check-clean `tray.svg` whose transparent
  alpha retains the rail, open gate, and stepped terminal.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] Encode off-axis proof geometry through position, not a small rotation: align its counter to the raster rhythm so it remains two deliberate pixels at 16px.
- [x] A full-card app master needs semantic groups or a mark-only tray source; template conversion must preserve the product mark rather than the card alpha.
