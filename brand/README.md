# IconFlow identity

IconFlow turns app intent and one semantic SVG source into a reviewed,
target-ready icon family.

**One master. Every surface. Proven at 16px.**

## Current temporary mark

The owner selected **Petal Haypile** from the Round 3 living exploration as the
temporary IconFlow product logo on 2026-08-14. A low-eared pika returns to its
hay store carrying three oversized petals. The mark brings the living, gentle,
slightly unexpected character of the Round 3 family into the product surface.

This is an explicit temporary promotion, not a permanent identity conclusion.
The earlier Flow Gate remains part of IconFlow's historical case evidence and
same-object technique demonstrations.

| Element | Product reading |
|---|---|
| Low paired ears and broad warm body | one specific, memorable living source |
| Lagoon hay cove | careful provision and a gathered family |
| Three carried petals | related outputs with distinct target character |
| Graphite app card | continuity with the existing product surface |

## Source files

- `master.svg` is the canonical full app/favicon source.
- `tray.svg` is a geometry-linked transparent variant with a graphite contrast
  halo so the warm pika survives light, dark, and neutral system bars, and one
  broad transparent eye cut so the macOS alpha template keeps a face instead of
  a featureless lozenge (`docs/LEARNINGS.md` L48).
- `iconflow.toml` is the complete brief and target build contract.
- `master-review.json` is the source/target-bound review receipt.
- `build/` contains deterministic web, Tauri, Electron, and tray outputs.

Reproduce the checked-in family through the same quality gate used by consuming
projects:

```powershell
.venv\Scripts\python.exe -m iconflow ship --config brand\iconflow.toml --review brand\master-review.json
```

## Palette

| Token | Value | Role |
|---|---:|---|
| Graphite | `#191A20` | app card and tray contrast halo |
| Warm Paper | `#FFF4E8` | pika body and semantic separation |
| Lagoon | `#59C7C1` | hay store |
| Petal Coral | `#FF5A4F` | first carried petal |
| Petal Gold | `#F2B84B` | second carried petal |
| Petal Violet | `#845EC2` | third carried petal |

Keep the source geometry editable and rebuild outputs rather than hand-editing
generated PNG, ICO, ICNS, or manifest assets.
