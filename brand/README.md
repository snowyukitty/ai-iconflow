# IconFlow identity

IconFlow turns app intent and one semantic SVG source into a reviewed,
target-ready icon family.

**One master. Every surface. Proven at 16px.**

## The mark

The identity is called **Proofed Flow**. It is a compact diagram of the product,
not a decoration added after the product:

| Element | Product meaning |
|---|---|
| Continuous warm-paper rail | One semantic SVG master through the whole workflow |
| Off-axis coral square | The opinionated `check` + visual review quality gate |
| Two-pixel counter | Proof that the signature survives at 16px |
| Stepped terminal | Browser rasterization and native-size platform outputs |
| Graphite app card | A calm, deterministic production surface |

The rail deliberately has no arrowhead. IconFlow is a controlled transformation,
not another generic automation or AI mark. The design avoids sparkles, robots,
brains, generic arrows/checks/bookmarks, and blue-purple gradients.

## Source files

- `master.svg` is the canonical full app/fav icon.
- `tray.svg` is the same semantic rail and proof gate without the app-card
  background. Its contrast halo works on light, dark, and neutral system bars;
  its alpha footprint remains meaningful as a macOS template image.
- `iconflow.toml` is the complete brief and relative-path build contract;
  `master-review.json` is the approved receipt bound to this exact source and
  target family.
- `tokens.css` contains the small brand token set.
- `build/` contains deterministic outputs generated from `master.svg` (with
  `tray.svg` used for tray targets when the build supports a target override).

`master.svg` exposes `iconflow-background`, `iconflow-mark`, `iconflow-rail`,
and `iconflow-signature`; `tray.svg` exposes the latter three. Consumers that
need the mark without its card should extract by ID rather than infer from color.

Reproduce the checked-in family through the same gate used by consuming
projects:

```bash
python -m iconflow ship --config brand/iconflow.toml \
  --review brand/master-review.json
```

## Palette

| Token | Value | Role |
|---|---|---|
| Graphite | `#191A20` | Primary production surface and precision |
| Signal Coral | `#FF5A4F` | Active proof gate and selection |
| Warm Paper | `#FFF4E8` | Human-authored master rail and review canvas |

Use Graphite as the dominant field, Warm Paper for the semantic rail, and
Signal Coral only for the proof event. Pass/warn/fail colors are QA states, not
brand colors. Do not expand the logo into a rainbow status indicator.

## Geometry and use

- Master grid: `1024 × 1024`.
- App card: `944 × 944`, 212-unit radius, 40-unit inset.
- Rail: 128 units, aligned to a 64-unit rhythm.
- Gate: `256 × 256`; counter: `128 × 128`, guaranteeing two clear pixels at
  16px before anti-aliasing.
- Minimum digital size: 16px for the complete card; 16px for `tray.svg` after
  inspecting the exact platform output.
- Clear space outside a standalone mark: at least one counter width.

Do not rotate the gate, add a sparkle, replace the terminal with an arrowhead,
or recolor the three elements independently. The slight positional asymmetry is
the signature; arbitrary visual effects weaken the product story.

## Voice

IconFlow is precise, opinionated, and calm. Prefer concrete proof language—
`16px`, `clean check`, `target-ready`, `one semantic source`—over vague claims
such as “magical,” “effortless,” or “AI-powered.”
