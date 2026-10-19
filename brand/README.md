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

## Wordmark and kit (2026-10-19)

`wordmark.svg` is **IconFlow** in Inter Bold, outlined at −0.02em by
`iconflow brand outline`; `tagline.svg` is the brand line in Inter Medium at
0em. Both are paths only — no live text, no font on the machine that renders
them — and each records its font and licence in a comment.

| | |
|---|---|
| Font | Inter 4.1 (font version 4.001), [rsms/inter release v4.1](https://github.com/rsms/inter/releases/tag/v4.1) |
| Licence | SIL Open Font License 1.1 (`LICENSE.txt` in the release) |
| `Inter-4.1.zip` | SHA-256 `9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e` |
| `extras/ttf/Inter-Bold.ttf` | SHA-256 `288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f` |
| `extras/ttf/Inter-Medium.ttf` | SHA-256 `97ad806f526e41546d46365bb3a393145f75b7b1568913db74549ad8b8dba872` |

`iconflow brand build --config brand/iconflow.toml --review brand/master-review.json`
writes the kit (lockups, tiles, Open Graph, GitHub and banner cards) to
`work/brand-kit/`, which is not committed: it is rebuilt from these sources.
Two builds give byte-identical PNGs. The GitHub repository's social preview is
the kit's `social/github-social-1280x640.png`, committed as
`docs/assets/github-social-preview.png`. The website's link-preview image is
a separate, richer card (`scripts/render_social_preview.py`).

`maskable.svg` (also 2026-10-19) is the master's own paths on a full-bleed
graphite field, so the card fills Android and PWA launcher shapes instead of
sitting inside a paper ring.

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
