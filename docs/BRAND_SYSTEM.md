# IconFlow brand system

> **Temporary product-mark status (2026-08-14):** the owner selected
> **Petal Haypile** from Round 3 as the current product logo while the permanent
> identity decision remains open. `brand/master.svg`, `brand/tray.svg`, and the
> website mark now use the low-eared pika carrying three petals. The Flow Gate
> material below remains historical design rationale and a controlled technique
> specimen; it is not the current product mark. This temporary promotion is
> intentionally reversible.

IconFlow is an agent-native icon production system. Its identity is derived
from the product job—turn app intent into a proven, target-ready icon family—
not from generic AI imagery.

## Positioning

**Product name:** IconFlow  
**Package name:** `ai-iconflow`  
**Essence:** proof  
**Personality:** precise, opinionated, calm  
**Primary line:** **One master. Every surface. Proven at 16px.**

Use `AI-authored` or `agent-native` as a descriptor when useful. Do not put
`AI` into the mark or represent it with brains, robots, sparkles, magic wands,
neural nodes, or the default blue-purple gradient.

## Current mark anatomy: Petal Haypile

The temporary mark keeps one specific living subject rather than a diagram:

| Part | Product reading |
|---|---|
| Low paired ears and broad warm body | one memorable semantic source |
| Lagoon hay cove | careful gathering and provision |
| Three carried petals | a related output family with distinct target character |
| Graphite field | continuity with the established product surface |

Current source anatomy in `brand/master.svg`:

```text
iconflow-background
iconflow-mark
  iconflow-core
  iconflow-signature
```

`brand/tray.svg` reuses that geometry without the app card and adds a graphite
contrast halo for light system bars. Its alpha footprint preserves the pika and
right-side petal punctuation as a monochrome template.

## Historical mark anatomy: Flow Gate

The mark is one controlled transformation:

| Part | Product meaning |
|---|---|
| Warm-paper master rail | one semantic SVG source |
| Off-axis coral proof gate | automated check + human review |
| Two-step terminal | native 16/32px raster proof and target outputs |
| Graphite field | deterministic production surface |

The rail—not the app-card container—is the recognisable shape. Its stepped
lower terminal gives the visual silhouette an asymmetric feature, while the
gate counter stays 128 units wide on the 1024 grid so it remains two deliberate
pixels at 16px.

Historical Flow Gate source anatomy:

```text
iconflow-background
iconflow-mark
  iconflow-rail
  iconflow-signature
```

The historical Flow Gate tray was likewise a linked mark-only composition. Its
case evidence remains in `casebook/2026-07-13-iconflow-brand.md`.

## Color

| Token | Value | Role |
|---|---:|---|
| Graphite | `#191A20` | primary field, text on light surfaces |
| Signal Coral | `#FF5A4F` | proof gate, active selection, primary action |
| Warm Paper | `#FFF4E8` | master rail, light proof surfaces |
| Lagoon | `#59C7C1` | current temporary mark's hay cove |
| Petal Gold | `#F2B84B` | current carried-petal accent |
| Petal Violet | `#845EC2` | current carried-petal accent |

QA colors (`pass`, `warning`, `failure`) are semantic interface states, not
brand colors. Keep neutral review cells genuinely neutral so the product chrome
does not bias color evaluation.

## Typography

- Product/UI: a clear system grotesk (`Inter`, `ui-sans-serif`, `Segoe UI`,
  platform fallback). The offline artifact must never depend on a web font.
- Measurements, hashes, pixel sizes and rubric values: tabular system mono
  (`ui-monospace`, `SFMono-Regular`, `Consolas`, fallback).
- Write the name as `IconFlow`. Use lowercase `iconflow` only for the command.

## Product visual language

- **Proof gate:** square aperture/counter for selected, inspected or approved
  states.
- **Pixel step:** section divider, progress terminal and small-size proof cue.
- **Adaptive frames:** circle, squircle and rounded masks for target contexts.
- **Master rail:** a continuous route through the product stages:
  `Brief → Explore → Compare → Inspect → Ship → Learn`.
- **Living case loop:** reserved for casebook/evolution diagrams. Never turn it
  into a sync/recycle primary mark.

Use these devices structurally. A coral line or rounded card by itself is not
the brand.

## Target use

- **Favicon/app:** use `brand/master.svg`; keep the full graphite container.
- **Tray/menu bar:** use `brand/tray.svg`; the pika body and right-side petals
  must survive monochrome template conversion.
- **Review artifacts:** keep evaluation backgrounds white, dark and neutral
  gray. Brand the header, stage rail, typography and decision gate only.
- **Documentation:** lead with the functional flow and actual 16px/review/build
  evidence. Do not use decorative mockups that hide the smallest outputs.

## Clear space and minimum size

- Keep at least one ear width of clear space around the standalone mark in
  editorial layouts.
- Do not reproduce the full mark below 16px.
- At 16px, do not add text, shadows, extra nodes or a second accent.
- Do not reorder or independently recolor the three carried petals during the
  temporary-mark period; they are one signature group.

## Assets

```text
brand/master.svg          editable app/favicon source of truth
brand/tray.svg            mark-only tray/menu-bar source
brand/iconflow.toml       portable product brief and build contract
brand/master-review.json  source/target-bound approved decision receipt
brand/build/              deterministic web/Tauri/Electron/tray outputs
docs/assets/hero-flow.svg functional product overview
docs/assets/concept-bake.png concept comparison evidence
docs/assets/review-proof.png final small-size and mask proof
docs/assets/social-preview.svg editable GitHub social-preview source
docs/assets/social-preview.png 1280×640 rendered social-preview candidate
```

Regenerate the social preview with
`python scripts/render_social_preview.py`, inspect the PNG, and upload it only
after repository-settings approval. It composes the already approved mark; it
does not replace or modify the app-icon source.

Copyright permission for these repository assets is provided under
Apache-2.0, but that license does not grant permission to use the IconFlow name,
logo, or visual identity to brand or endorse a third-party product, service, or
modified distribution. Follow [`TRADEMARKS.md`](../TRADEMARKS.md) whenever the
mark appears outside the official project.

Every change to the master must repeat the IconFlow procedure: diverge when the
idea changes, compare finalists, check, visually inspect the review, build all
selected targets, and record the case.
