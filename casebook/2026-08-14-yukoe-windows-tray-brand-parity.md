---
slug: yukoe-windows-tray-brand-parity
date: 2026-08-14
project: yukoe
targets: tray
essence: listen
style_family: kawaii-listening-mascot
signature_device: A full-color close crop restores the complete face while a linked negative-space variant remains available for monochrome templates.
device_family: mascot-single-trait
device_detail: The Windows 16 and 32 px assets keep deep-purple eyes and smile plus pink cheeks; the linked template source keeps broad transparent facial cuts.
concept_lens: identity-trait-plus-unexpected-crop
cliche_avoided: featureless status dot, generic monochrome mascot, microphone, waveform
status: shipped
scores_first: legibility=3 distinctiveness=4 balance=4 color=3 scalability=3 craft=4
scores_final: legibility=5 distinctiveness=5 balance=4 color=5 scalability=5 craft=4
iterations: 3
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
Four divergent crops and a three-finalist bake-off showed that the Windows tray needed the complete app-icon expression, while the alpha template needed a separate linked reduction. The face-forward crop won because it restored brand parity at exact 16 and 32 px without replacing the mascot.

## What failed first
The prior shared tray source cut the eyes and mouth completely out of the white
face so an alpha-derived template could retain an expression. On Windows those
cuts inherited the taskbar color: at 16 px the mascot lost its deep-purple eyes,
smile, and pink cheeks, and no longer matched the regular app icon. A first
dual-reduction finalist placed opaque facial islands inside larger transparent
counters; it looked right on white but the counters expanded into dark masks on
gray and dark taskbars. Keeping a close full-color Windows source beside the
linked negative-space template source restored the exact facial palette on all
three backgrounds without weakening either reduction.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] When a full-color Windows tray and an alpha-only menu-bar template demand incompatible pixel semantics, keep linked platform reductions from shared geometry instead of degrading the color asset with transparent facial holes.
