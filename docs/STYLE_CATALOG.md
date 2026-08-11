# Style catalog

IconFlow includes fourteen small-size-first **technique scaffolds**. They are
execution grammars around the same house rail, not finished logos and not a
substitute for product concepting. Replace the rail with one specific object
whose silhouette names the consuming product's job, add one signature device,
then complete the normal bake-off, check, review, receipt, and casebook loop.

![Fourteen IconFlow technique scaffolds rendered at 128px and 16px](assets/style-gallery.png)

List the same source-of-truth metadata from any installed wheel, or regenerate
the gallery from the packaged SVGs:

```bash
iconflow styles
iconflow styles --json
iconflow styles --gallery style-gallery.png
iconflow new stencil-cut --out master.svg
```

`styles --gallery` uses the same network-isolated Chromium renderer as the
build. Every tile contains a large render plus native 16px proof on light and
dark surfaces. It does not synthesize or download artwork.

## Choose by structure, not decoration

| Family | Preset | Structural move | 16px survival rule | Tray / monochrome strategy |
|---|---|---|---|---|
| Flat geometric | `flat-geometric` | solid primitives and negative space | merge tiny booleans; keep cuts two pixels wide | extract or author a mark-only silhouette |
| Gradient glow | `gradient-glow` | restrained light clipped inside one opaque core | the core must read with every glow removed | dedicated solid tray source |
| Line mark | `line-mark` | one uniform contour and contrast halo | optically expand one weight; never cross strokes | review the same contour at exact tray sizes |
| Soft mascot | `mascot` | identity-owned character silhouette | two expression details and one identity trait at most | simplified face or mark-only tray source |
| Duotone cut | `duotone-cut` | primary mass split by one large plane | primary plane must identify the object alone | primary plane becomes the mono source |
| Stencil cut | `stencil-cut` | one plate whose holes carry the object | holes and bridges stay two pixels wide | invert and test the same plate on every tray surface |
| Pixel grid | `pixel-grid` | integer blocks and stepped corners | design on the 16px grid first; preserve pixel parity | grid-snapped one-color sprite |
| Isometric | `isometric` | two or three explicit projected faces | drop micro-edges; retain two essential faces | separate front-facing silhouette |
| Cut paper | `cut-paper` | broad hard-edged offset layers | remove offsets smaller than one deliberate pixel | collapse layers to the outer silhouette |
| Enamel pin | `enamel-pin` | metal boundary plus inset color | protect a two-pixel boundary; omit micro-shine | outer metal contour becomes the tray silhouette |
| Blueprint | `blueprint` | technical contour, sparse guides, explicit nodes | construction lines remain subordinate to the core | ship the primary contour without guides |
| Stained glass | `stained-glass` | large panes separated by heavy leading | use at most four panes; every separator must resolve | dedicated leading-and-outer mono source |
| Risograph | `risograph` | two controlled spot-color plates and shared core | registration offset resolves as one pixel, not blur | shared core only, never the offset plates |
| Clay | `clay` | chunky volume with explicit shadow and highlight shapes | one shadow edge and one highlight at most | flat base-volume silhouette |

The catalog treats weight, fill, and color as **axes inside a family**, not
independent art styles. A thin outline and a bold outline do not count twice.
Likewise, a recolor is not a new preset.

## Fast routing

- Start with `flat-geometric`, `line-mark`, or `blueprint` when precision and
  restraint are product traits.
- Start with `mascot`, `cut-paper`, `enamel-pin`, or `clay` when warmth and
  tactility are part of the identity.
- Start with `pixel-grid`, `risograph`, or `stained-glass` only when that visual
  language belongs to the product—not because it makes a gallery look varied.
- Use `gradient-glow`, `duotone-cut`, or `isometric` for depth, but prove that
  the unlit primary silhouette still names the right object.
- Prefer `stencil-cut` for a mark that must travel between color app surfaces
  and strong monochrome contexts.

An app-card style and a tray mark may share geometry without sharing a literal
composition. If color planes, material effects, a full-card alpha shape, or
character details carry meaning, author a linked `tray.svg`; do not ask an
automatic monochrome conversion to invent semantics.

## Shared small-size contract

1. Design the semantic object and its critical counter at 16px before adding
   material, facets, offsets, or guides.
2. Keep critical strokes, holes, bridges, and detached gaps at roughly two
   rendered pixels. A one-pixel detail is allowed only when it is non-semantic,
   grid-aligned, and visibly intentional in the pixel zoom.
3. Use explicit level-of-detail decisions. Do not scale store-size decoration
   down and hope antialiasing will simplify it.
4. Adjacent planes must differ in value, not hue alone. The primary object must
   survive with gradients, blend modes, shadows, and highlights removed.
5. Keep every essential feature inside the maskable safe zone. Decorative edge
   pixels are the first thing to delete.
6. Inspect native 16px pixels on white, `#808080`, and `#0b0d12`, plus visual
   negative space and platform crops. A polished 128px source is not evidence.
7. A preset is ready to use only as a starting point. A real icon still needs
   four concepts, a finalist bake-off, `check`, `review`, six scores of at least
   4/5, a source-bound receipt, and a linted case.

## Research and clean-room provenance

The catalog was developed from general principles studied across public icon
systems, then drawn clean-room from IconFlow's own geometry. **No third-party
SVG path, source code, image, font, palette, wording, brand mark, or distinctive
trade dress is included in these presets or the gallery.** Repository licenses
below describe the research sources, not dependencies or relicensing of their
artwork. Recheck each upstream before any future asset use.

Sources were verified from their official repositories on **2026-08-12**:

| Upstream research source | Verified license signal | General lesson studied; no assets copied |
|---|---|---|
| [Google Material Symbols / Icons](https://github.com/google/material-design-icons) | Apache-2.0 | optical-size axes, keyline discipline, and designed 20/24px masters |
| [Microsoft Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons) | MIT | filled/regular families, platform packaging, and direction metadata |
| [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji) | MIT | one semantic subject expressed as 3D, color, flat, and high-contrast families |
| [Tabler Icons](https://github.com/tabler/tabler-icons) | MIT | a consistent 24px grid and explicit stroke grammar |
| [Phosphor Icons Core](https://github.com/phosphor-icons/core) | MIT | weight and duotone as controlled axes rather than unrelated styles |
| [Lucide](https://github.com/lucide-icons/lucide) | ISC | community consistency and the deliberate exclusion of brand logos |
| [Iconoir](https://github.com/iconoir-icons/iconoir) | MIT | a broad vocabulary constrained to one 24px construction system |
| [Heroicons](https://github.com/tailwindlabs/heroicons) | MIT | distinct 16, 20, and 24px solid/outline deliverables instead of blind scaling |
| [Pixelarticons](https://github.com/halfmage/pixelarticons) | MIT for the public repository | strict integer-grid paths and no-antialiasing intent; paid assets were not accessed |
| [IconPark](https://github.com/bytedance/IconPark) | Apache-2.0; archived 2025-12-08 | transforming one semantic source into outline, filled, two-tone, and multicolor themes; historical reference only |
| [Papirus](https://github.com/PapirusDevelopmentTeam/papirus-icon-theme) | GPL-3.0 | explicit 16/22/24/32/48/64 masters, color-scheme variants, and tray-specific reality |
| [OpenMoji](https://github.com/hfg-gmuend/openmoji) | graphics CC BY-SA 4.0; code LGPL-3.0 | published palette/templates, family-wide consistency, and attribution boundaries |
| [Noto Emoji](https://github.com/googlefonts/noto-emoji) | emoji fonts OFL-1.1; tools and most images Apache-2.0; flags vary | color and monochrome semantic reduction plus mixed-license provenance |
| [jdecked Twemoji](https://github.com/jdecked/twemoji) | code MIT; graphics CC BY 4.0 | closed color shapes and explicit code/art license separation |
| [Game Icons](https://github.com/game-icons/icons) | CC BY | foreground/background silhouette systems and per-author attribution needs |
| [Simple Icons](https://github.com/simple-icons/simple-icons) | repository CC0; individual marks retain separate trademark/license concerns | monochrome reduction and why repository license alone does not clear brand rights |
| [Remix Icon](https://github.com/Remix-Design/RemixIcon/blob/master/License) | custom Remix Icon License v1.0 (January 2026) | a current licensing warning: its icons may not be used as app identities or competing icon libraries |

The Remix Icon and Simple Icons rows are intentionally cautionary. They show
why a remembered license, a repository badge, or a permissive collection-level
license is not enough to clear identity artwork. IconFlow uses neither source's
assets.
