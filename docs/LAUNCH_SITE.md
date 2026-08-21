<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Launch site brief

Status: implemented in `website/`; the homepage, nine source-bound Theme Worlds,
proofed 100-case Gallery at `/gallery/`, and the agent-first onboarding guide at
`/getting-started/` are deployed. The canonical host became
[`ai-iconflow.com`](https://ai-iconflow.com/) on 2026-08-15, replacing
`iconflow.pages.dev`, which stays reachable as the Pages default host.
`iconflow.pages.dev` and `www.ai-iconflow.com` are permanent 301 redirects to
the apex. This document remains the acceptance boundary for future
promotional-site changes.

## Positioning

IconFlow is a **proof-driven, agent-native icon production system**. It should
not be presented as another prompt gallery, stock-icon library, or instant image
generator.

Primary line:

> **One master. Every surface. Proven at 16px.**

Hero support:

> IconFlow guides agents and designers from competing concepts to an editable
> semantic SVG, native-size proof, and platform-ready favicon, PWA, desktop, and
> tray assets. Stale or sub-4/5 reviews cannot ship.

The defensible market position is the decision workflow between generation and
conversion:

```text
product intent
→ competing concepts
→ silhouette decision
→ native 16px inspection
→ exact target transforms
→ source-bound approval
→ platform assets
→ casebook learning
```

Generators make options. Converters make files. IconFlow makes the design
decision visible, repeatable, and auditable.

## Content principles

1. Lead with real evidence: SVG sources, native PNG pixels, target transforms,
   review receipts, and case deltas.
2. Keep two axes separate:
   - **Technique family** is how the icon is constructed.
   - **Product world + user job** is what the icon serves and why it exists.
3. Never use an unreviewed preset scaffold as a finished identity example.
4. Never claim all-platform or mobile coverage. Current language is favicon,
   PWA, Tauri/Electron desktop, and tray/menu bar.
5. Show known limits beside strengths: Chromium is a one-time download; Tauri
   mobile sets and Apple Icon Composer files are not currently generated.

## Navigation and homepage sequence

Primary navigation: `Product · Proof · Styles · Cases · Docs · GitHub`

| Section | Job | Required evidence |
|---|---|---|
| Hero | State the outcome in one glance | current brand mark animation built from the approved brand SVG; source-install CTA |
| An icon is not finished at 1024px | Expose the failure IconFlow solves | true 256→16px before/after, color, silhouette, and pixel zoom |
| The Flow | Make the workflow memorable | `Brief → Explore → Compare → Inspect → Ship → Learn`, one real artifact per step |
| Interactive Proof Lab | Let visitors inspect instead of trust claims | size, surface, view, target, and receipt-staleness controls |
| Technique families | Prove the catalog is structural | six featured families plus a link to all twenty; same-object comparison |
| Many worlds | Show range without becoming a gallery | six to eight editorial case studies with user job and design reasoning |
| Evidence, not vibes | Quantify the learning loop | dated case count, sample size, first→final rubric means, review iterations |
| Outputs | Show the practical result | one source fanning out to the exact checked-in file tree |
| Local and explicit | Build trust | offline render/build boundary, no API key, security model, known limits |
| Quick start | Convert interest into use | source install, setup, styles, init, compare, review, ship |

Homepage style copy:

> **Twenty visual languages. One small-size contract.**
> Not twenty filters. Each family changes how shape, depth, counters, and
> monochrome reduction work—then proves the result at native size.

> **One pipeline. Many worlds.**
> Relationships, companions, stories, games, and tools each begin with a user
> job, escape the obvious cliché, and earn their silhouette.

## Interactive Proof Lab

Version one is static-first: it reads pre-rendered, reviewed assets and JSON. It
must not accept arbitrary uploads or run a public renderer.

Controls:

- size: 16, 32, 128, 256;
- surface: white, neutral gray, graphite;
- view: color, visual silhouette, alpha footprint, nearest-neighbor pixel zoom;
- target: browser, maskable PWA, Electron corner, tray, macOS template;
- receipt: mutate one public demo input and show `receipt stale — ship blocked`.

Native 16px PNGs and their nearest-neighbor zooms are separate assets. CSS
interpolation must never be presented as pixel proof.

## Case-card contract

Every public showcase card includes:

- user job and one-word essence;
- technique family;
- cliché avoided;
- signature device;
- 128px and native 16px renders;
- visual silhouette;
- at least one exact target context;
- first→final scores and iteration count;
- source-bound receipt, case record, and editable source links when public.

Three controlled comparisons prevent the site from looking like a cheap AI
gallery:

1. one object across six structural languages;
2. one technique across six product worlds;
3. six to eight complete case stories with the failed first reading and repair.

## Visual and motion system

Use the existing brand system: Graphite `#191A20`, Warm Paper `#FFF4E8`, Signal
Coral `#FF5A4F`, system grotesk, tabular mono, grid, proof gate, pixel steps, and
master rail. The site should feel like a design proof laboratory.

Motion is limited to semantic transformations: rail flow, silhouette removal,
pixel inspection, platform crops, and receipt invalidation. Do not use generic
blue-purple gradients, sparkles, floating 3D blobs, fake dashboards, autoplay
carousels, or decorative AI motion. Respect `prefers-reduced-motion` and make
every control keyboard reachable.

## Routes and discoverability

Core routes:

- `/`
- `/getting-started/`
- `/gallery/`
- `/styles`
- `/proof`
- `/cases`
- `/favicon-generator-from-svg`
- `/tauri-icon-generator`
- `/electron-icon-generator`
- `/pwa-maskable-icon`
- `/tray-icon-template`

Each platform page needs unique limits, a real command, an exact output tree,
and a proof artifact. It must not be a keyword-swapped thin page.

Suggested metadata:

- title: `IconFlow — Design, review, and ship platform-ready icons`
- description: `Turn one semantic SVG into reviewed favicon, PWA, Tauri,
  Electron, and tray assets—with native 16px proof and a fail-closed quality
  gate.`

Use `SoftwareSourceCode` and `WebSite` structured data. Do not invent ratings,
reviews, prices, users, or performance claims.

## Asset inventory

Ready now:

- `docs/assets/hero-flow.svg`;
- `docs/assets/concept-bake.png`;
- `docs/assets/review-proof.png`;
- `docs/assets/style-gallery.png`;
- `docs/assets/social-preview.svg` and `.png`;
- approved brand master, tray source, receipt, and checked-in build;
- casebook records and reproducible statistics.

Required before site launch:

- nine flagship case bundles from `SHOWCASE_PLAN.md`;
- same-object/six-techniques and same-technique/six-worlds comparison strips;
- two or three genuine first-pass→repair specimens;
- an app-card→linked-tray case;
- a dated stats snapshot generated during the site build;
- 1200×630, 1280×640, 1080×1080, and 1080×1920 share frames;
- per-case open-graph cards with icon, 16px proof, device, and score delta.

The Gallery edition is governed by [`GALLERY.md`](GALLERY.md): 100 admitted
cases selected from 111 generated candidates, each with source, native proof,
silhouette, current receipt, and case record.

## Sixty-second launch video

| Time | Shot |
|---:|---|
| 0–5s | `Looks polished at 1024. Dies at 16.` with a real first-pass failure |
| 5–13s | brief opens into four concept lenses |
| 13–21s | three finalists enter the bake-off; color disappears; silhouette wins |
| 21–33s | 16px pixel zoom, maskable crop, Electron corner, tray template |
| 33–41s | six axes pass; a source change makes the receipt stale and blocks ship |
| 41–51s | one semantic SVG fans out to exact platform assets |
| 51–58s | controlled montage of twenty techniques across many worlds |
| 58–60s | `One master. Every surface. Proven at 16px.` |

Video tools may create environments and transitions. Approved icon pixels,
Review Lab UI, receipts, and output files must be composited from exact project
assets and must never be regenerated or beautified by a video model. Produce a
4K 16:9 master with the essential action inside a central 9:16 safe region.

## Website acceptance gate

- Every shown icon is source-linked, check-clean, reviewed, and case-recorded.
- All proof interactions have keyboard and reduced-motion behavior.
- Performance budgets and responsive layout are verified before publication.
- Claims match current output targets and dated casebook evidence.
- The site contains no arbitrary upload surface, secrets, private project data,
  third-party IP imitation, or unlicensed artwork.
- Repository publication, domain, analytics, and deployment remain explicit
  owner decisions.
