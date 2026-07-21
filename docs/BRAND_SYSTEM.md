# IconFlow brand system

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

## Mark anatomy: Flow Gate

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

Source anatomy in `brand/master.svg`:

```text
iconflow-background
iconflow-mark
  iconflow-rail
  iconflow-signature
```

`brand/tray.svg` is the mark-only, target-specific composition. It reuses the
same geometry and gate; it is not a second logo.

## Color

| Token | Value | Role |
|---|---:|---|
| Graphite | `#191A20` | primary field, text on light surfaces |
| Signal Coral | `#FF5A4F` | proof gate, active selection, primary action |
| Warm Paper | `#FFF4E8` | master rail, light proof surfaces |

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
- **Tray/menu bar:** use `brand/tray.svg`; the semantic rail and gate must
  survive monochrome template conversion.
- **Review artifacts:** keep evaluation backgrounds white, dark and neutral
  gray. Brand the header, stage rail, typography and decision gate only.
- **Documentation:** lead with the functional flow and actual 16px/review/build
  evidence. Do not use decorative mockups that hide the smallest outputs.

## Clear space and minimum size

- Keep at least one gate-counter width of clear space around the standalone
  mark in editorial layouts.
- Do not reproduce the full mark below 16px.
- At 16px, do not add text, shadows, extra nodes or a second accent.
- Never recolor the gate as generic success green; coral identifies IconFlow,
  while green communicates a transient pass state.

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
```

Every change to the master must repeat the IconFlow procedure: diverge when the
idea changes, compare finalists, check, visually inspect the review, build all
selected targets, and record the case.
