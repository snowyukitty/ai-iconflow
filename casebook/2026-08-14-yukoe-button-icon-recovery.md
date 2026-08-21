---
slug: yukoe-button-icon-recovery
date: 2026-08-14
project: Yukoe button icon recovery
targets: ui-buttons,tray-review
essence: clarity
style_family: line-mark
signature_device: Familiar semantic nouns followed by one dedicated state rail
device_family: semantic-style-grammar
device_detail: Each noun stays inside a stable left field; ON bows outward, OFF closes inward, and BLOCKED becomes two still bars in a separated right rail.
concept_lens: object-verb
cliche_avoided: tag and ticket blobs; color-only state; tiny badges; crossed slash overlays
status: shipped
scores_first: legibility=5 distinctiveness=4 balance=5 color=3 scalability=5 craft=5
scores_final: legibility=5 distinctiveness=4 balance=5 color=4 scalability=5 craft=5
iterations: 2
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
## Summary
A compact button-family repair that replaced filled Folded Folio blobs with familiar line nouns and one shared state rail. The semantic-rail direction beat cut-caption, folded-folio, and caption-pair concepts because it preserved feature recognition at 18 px while keeping effective state geometric.

## What failed first
The shipped Folded Folio adaptation removed the reviewed dark keyline and filled
every 18–20 px control with its state color. Names, original speech, translated
speech, and language controls therefore read first as unrelated tickets, tags,
or blobs; the neighboring outline utility icons made the mismatch stronger.
Restoring the keyline improved contrast but did not fix the wrong nouns. A
four-direction bake-off showed that the line-mark semantic rail preserved the
feature noun at 16 px. Its first review then scored color 3 because the dark
core disappeared on dark and mid-gray proof rows; a neutral 120-unit under-keyline
raised color to 4 without changing the currentColor UI geometry.

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
- [x] For dense UI controls, preserve the familiar feature noun in a stable line field and place state in a separate, two-pixel rail; forcing the whole control into an ownable filled silhouette can make neighboring actions read as unrelated objects.
