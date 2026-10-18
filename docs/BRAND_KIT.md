<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The brand kit — propagating a mark beyond the favicon

`iconflow ship` turns an approved `master.svg` into icons. A product's mark
lives in many more places: the site header, press-kit lockups, app-store and
directory tiles, Open Graph and social cards, the repository banner. L45 asks
that a new mark be promoted as **one source-bound transaction**; before 0.7
only the icon half of that transaction had a tool, and the rest was redrawn by
project scripts every time.

```bash
iconflow brand build --config iconflow.toml --review master-review.json   # the kit + manifest
iconflow brand build --config iconflow.toml --review master-review.json --ship  # icons too
iconflow brand sync  --manifest brand-kit --project ../my-site            # what is still old
```

## What it needs

`[brand]` in `iconflow.toml`:

```toml
[brand]
wordmark = "wordmark.svg"   # required: OUTLINED paths, fill="currentColor"
tagline  = "tagline.svg"    # optional, outlined, for the social cards
dark     = "#191A20"        # dark ground (default: build.theme_color)
light    = "#FFF4E8"        # light ground (default: white)
# ink_on_dark / ink_on_light   wordmark colour per ground (default: the other ground)
# output = "brand-kit"         wordmark_scale = 0.42   clear_space = 0.25
```

**The wordmark must be outlined.** A live `<text>` element renders with
whatever fonts the build machine has — a different wordmark on every machine —
and carries a font licence IconFlow cannot see, so `brand` refuses it. Outline
it in a type tool, or with

```bash
pip install "iconflow[brand]"            # adds fontTools, for this command only
iconflow brand outline --text "Acme" --font fonts/YourFont.ttf --weight 700 --out wordmark.svg
```

`outline` reads the font's own licence fields (name IDs 13/14) and its OS/2
embedding bits. It outlines a font whose licence it recognises as permissive
(SIL OFL, Apache, MIT, Ubuntu Font Licence, CC0, public domain, Bitstream
Vera) and refuses anything else, or anything marked *restricted*, unless you
record why your use is licensed with `--licence-ok "<licence and where it is
kept>"`. The note is written into the SVG. Layout is the font's advance widths
plus its legacy `kern` table — there is no shaping — so check the spacing
before the outline becomes the brand.

**The mark must be approved and clean.** `brand build` accepts exactly what
`ship` accepts: a ready receipt bound to the current source and contract, or
a source-bound approved `[review]`, and it re-runs the same automated audit
`ship` runs. A stale, below-floor or warned mark gets no kit.

**What the composition guarantees.** Every source is parsed and refused if it
carries active content, an event handler or an external reference — prefixed
or not (`<s:script>` is a script). A wordmark may not carry a `<style>`; a
master that does is embedded as an SVG image, so its selectors cannot repaint
the wordmark and the wordmark's cannot repaint it (its `prefers-color-scheme`
layer still works). An inlined source keeps its root's rendering attributes
(`stroke-width`, `opacity`, `clip-path`, ...) and has only its real id
references rewritten. The kit is never written through a symlink or junction.

## What it writes

| Path | What |
|---|---|
| `lockups/{horizontal,stacked}-on-{dark,light}.svg` | vector lockups, transparent, ink for that ground |
| `lockups/{horizontal,stacked}-on-{dark,light}.png` | the same on the ground, 512px tall |
| `tiles/tile-{dark,light}-{1024,512,192}.png` | the mark at 78% on a rounded tile |
| `social/og-1200x630.{svg,png}` | Open Graph / link previews |
| `social/github-social-1280x640.{svg,png}` | GitHub repository social preview |
| `social/banner-1500x500.{svg,png}` | profile / README banner |
| `guides/clear-space-and-minimum-size.png` | the clear-space rule drawn on the lockup, minimum sizes in real pixels |
| `mark/master.svg`, `mark/mark-1024.png` | the approved mark itself |
| `brand-sheet.png` | every surface on one sheet — **read it before publishing** |
| `brand-manifest.json` | every file and source by SHA-256, the approval, the retired marks |

Geometry: the clear-space unit *x* is `clear_space` × the mark's height on
every side; the horizontal wordmark is `wordmark_scale` × the mark's height,
centred on it. The minimum lockup height is the one at which the wordmark is
still 10px tall, and is recorded in the manifest.

Dark lockups render the mark with `prefers-color-scheme: dark`, so a source
with a dark-scheme layer shows it there.

## Propagation

`brand-manifest.json` records the kit, the hashes of every source and — only
when `--ship` built them in the same run — the icon outputs. An icon tree that
was already on disk may still hold the previous mark, so it is never assumed
current. When the mark changes, the previous mark's
files move to `retired` on the next build. `brand sync` then walks a consuming
project — skipping `.git`, `node_modules`, virtualenvs and build caches — and
reports, as `brand-stale` (exit 1), every file that still carries a retired
mark:

- an image or icon file byte-identical to a retired asset;
- an SVG whose normalized hash is a retired `master.svg`;
- a PNG or ICO inlined as a base64 data URL in HTML, CSS, JS/TS, JSON or
  Markdown (a `trayIcon.ts` module, a hard-coded favicon).

A file that is identical across marks (unchanged by the change) is never
called stale, a mark that was retired and later restored is current again,
and the scan never follows a symlink or junction out of the project. Matching is by bytes, so a retired mark that a project
re-encoded or resized itself is not found — re-export it from the kit
instead.

## Review

The kit is a transform of an approved mark, so it inherits that approval and
`brand` records it. The *lockup* is a new composition — the space between
mark and wordmark, the wordmark's weight against the mark's — and deserves its
own look: read `brand-sheet.png` and the clear-space guide at real size before
anything is published.
