---
description: Design, review at 16px, and ship a distinctive icon family for this project
argument-hint: "[what the app does, in one line]"
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
Design and ship this project's icon family with IconFlow, following the
`iconflow` skill's procedure exactly. Do not skip divergence and do not skip
looking at the rendered pixels — those two steps are the difference between a
distinctive mark and another gradient tile with a letter on it.

**Brief:** $ARGUMENTS

If that is empty, derive the brief from this repository — its README, package
metadata, routes, and existing theme colors — and state the app intent and user
job you inferred before you start drawing.

**Run the skill's full procedure**, in order:

1. Resolve the runner (`iconflow --version`; run `/iconflow:setup` first if it
   is missing), then read the rules distilled from every previously shipped
   icon: `iconflow docs LEARNINGS`.
2. `iconflow init --out iconflow.toml` and record the real brief — app intent,
   user job, one-word essence, the project's existing brand color, personality,
   clichés to avoid, signature-device hypothesis, and exact targets.
3. Diverge: 4+ concepts through different lenses (`iconflow docs CONCEPTING`),
   apply the cliché filter, add ONE signature device, draft 2–3 finalist SVGs.
4. Bake off with `iconflow compare ... --out work/<slug>/bake.png` and **read
   that PNG**. Apply the name-the-thing test at 128px and 16px.
5. Author `master.svg` (`iconflow docs SVG_TECHNIQUES`); add a mark-only
   `tray.svg` if this project ships a tray or menu-bar icon.
6. `iconflow check master.svg` until clean, then
   `iconflow review --config iconflow.toml --out work/<slug>/review.png --html work/<slug>/review.html`
   and **read that sheet**. Score the six axes against
   `iconflow docs REVIEW_CHECKLIST`; distinctiveness below 4/5 is a hard stop.
   Iterate — usually two or three passes.
7. `iconflow ship --config iconflow.toml --review master-review.json`.
8. Record the case (`iconflow case new ...`, then `case lint`) so the next icon
   starts from this one's evidence.

**Report** the cliché you avoided, the signature device you chose, the final
six scores, and the files produced.
