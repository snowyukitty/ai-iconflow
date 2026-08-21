---
slug: iconflow-style-catalog
date: 2026-08-12
project: IconFlow
targets: docs,cli,web,pwa,electron,tray
essence: vocabulary
style_family: style-system
signature_device: one house rail compared across fourteen structurally distinct technique grammars
device_family: ownable-geometry
device_detail: shared rail with per-family 16px and tray contracts
concept_lens: style-system
cliche_avoided: color-only preset packs; stroke-weight inflation; tiny decorative detail
status: shipped
scores_first: legibility=3 distinctiveness=4 balance=4 color=4 scalability=3 craft=3
scores_final: legibility=4 distinctiveness=4 balance=4 color=4 scalability=5 craft=4
iterations: 3
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
A clean-room catalog applies fourteen structurally different visual grammars to one house rail, making style choice concrete while preserving tiny-size and tray constraints.

## What failed first
The first `pixel-grid` draft placed decorative pixels inside the outer 8% of the
canvas, so the maskable safe-zone check failed. Removing those nonessential edge
pixels restored scalability without weakening the 16 px silhouette. The first
`stencil-cut` draft also painted a dark plate below nominal cutouts; alpha
inspection showed that the holes were opaque. Making the plate transparent
turned the gaps into real negative space for light, dark, and template contexts.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] A preset family needs a unique structural model, not only a palette or stroke change.
- [x] Adaptive safe zones take priority over decorative pixels near the canvas edge.
- [x] Transparency must be verified through the alpha channel rather than inferred from dark-looking holes.
- [x] Tray behavior belongs in per-style guidance because full-card treatments do not reduce uniformly.
