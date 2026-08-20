# The IconFlow Design Playbook

This is the brain of IconFlow. The build engine is mechanical; **quality comes
from here.** Read this before authoring an icon. You (the AI agent) are the
designer — you will hand-author an SVG master, render it small, critique it, and
iterate until it scores well on the rubric.

> Core belief: a great app/favicon/tray icon is **one bold idea, drawn on a
> grid, that survives being shrunk to 16×16.** Everything below serves that.

---

## 0. The loop (never skip the middle steps)

```
docs/LEARNINGS.md + iconflow case stats   (what past icons taught the system)
  ▼
brief + iconflow.toml                     (intent + exact target contract)
  │  DIVERGE (docs/CONCEPTING.md): 4+ concepts via different lenses,
  │          apply the cliché filter, add ONE signature device
  ▼
2–3 finalist SVG thumbnails
  │  python -m iconflow compare a.svg b.svg c.svg   → bake.png (LOOK)
  │  silhouette test + row test → pick the most DISTINCTIVE that reads small
  ▼
master.svg (1024 grid)
  │  python -m iconflow check master.svg      (automated red flags)
  │  python -m iconflow review --config iconflow.toml --html review.html
  │  LOOK at the static proof + target-aware Review Lab
  │  score against REVIEW_CHECKLIST.md and export master-review.json
  ├── < 4/5 on any axis → revise the SVG, render again
  └── all ≥ 4/5 → python -m iconflow ship --config iconflow.toml \
                    --review master-review.json
                    │
                    ▼
                  python -m iconflow case new ...   (record the case —
                  closes the self-evolution loop, docs/EVOLUTION.md)
```

**Two steps are mandatory and most-often skipped:**
- **Diverge before you commit** (§Concepting). Skipping it is why most AI icons
  look generic — they lock onto the first obvious metaphor. Distinctiveness is a
  *process*, not luck. See `docs/CONCEPTING.md`.
- **Render-and-review.** An icon that looks great at 1024 routinely dies at
  16px, and a mark that looks distinctive in color is often a generic silhouette.
  You cannot judge an icon at the size you draw it. Always `Read` `review.png`
  (and `bake.png`) before declaring done. Use `--html review.html` for the
  target-aware Review Lab: inspect pixel zoom, adaptive crops, platform
  transforms, and light/dark contexts there before scoring and exporting the
  source-bound receipt.

---

## 1. Brief: extract these five things first

1. **What is it?** (app / website favicon / system-tray app) → drives the
   format set and whether the semantic master needs a mark-only target variant.
2. **One-word essence.** A bookmark manager → "save". A career app → "rise". A
   route planner → "wayfinding"; creator brand → "persona". If you
   can't name the essence in one word, the icon
   will be muddled.
3. **Brand color.** Pull from the existing UI if there is one (check the repo's
   CSS/theme). Otherwise pick one confident hue. Icons are not multi-color
   illustrations — 1 dominant color + 1 accent is the ceiling for most.
4. **Personality.** Pick a lane: *geometric/precise*, *soft/friendly*,
   *premium/glow*, *playful/mascot*. This selects a style family (§3).
5. **Where it lives small.** Favicon → 16px tab. Tray → 16px on a busy taskbar,
   often monochrome. App → 32–48px in a dock/Start menu, plus 1024 in stores.

---

## 2. The grid & geometry (non-negotiable structure)

Author on a **1024×1024** canvas (`viewBox="0 0 1024 1024"`). It downsamples
cleanly to every target and matches Tauri/Electron masters.

- **Safe area / live area.** Keep the mark inside the centre **~80%** (≈100px
  padding on a 1024 grid). For **maskable** PWA / Android adaptive icons the OS
  may crop to a circle — keep anything essential inside the centre **~66%**.
- **Keyline shapes.** Don't free-float the artwork. Size it against standard
  keylines so a family of icons feels consistent (Material/Streamline practice):
  - circle Ø ≈ 800 (of 1024)  ·  square ≈ 760  ·  portrait rect ≈ 640×880  ·
    landscape rect ≈ 880×640. Use these as the bounding envelope of the mark.
- **Optical, not mathematical, centering.** Triangles, arrows and asymmetric
  marks must be nudged so they *look* centered (a pure-math center looks
  top/left-heavy). Trust the contact sheet over the coordinates.
- **Position before rotation at favicon scale.** A small tilted gate, counter,
  or badge spends its scarce pixels on diagonal anti-aliasing. Express subtle
  asymmetry by offsetting raster-aligned geometry first; rotate only if the
  16px pixel zoom still shows the intended counter as deliberate pixels.
- **Corner radius for the container.** If the icon sits on a rounded square
  (app-icon style), use a **squircle/superellipse** feel: radius ≈ **18–22%** of
  the side. iOS uses a true squircle; a 22% rounded-rect is a good SVG proxy.
- **Stroke weight.** On a 1024 grid, line marks read best at **stroke ≈ 32–56**
  (≈ 3–5% of the side). Thinner than ~24 (≈2.3%) and it vanishes at 16px. Use
  `stroke-linecap="round"` and `stroke-linejoin="round"` unless you want a
  technical look. Keep stroke weight uniform across the whole mark.
- **Budget the first draft in final pixels.** At 16px, **64 SVG units ≈ one
  output pixel**. Before drawing a finalist, annotate every idea-carrying
  accent/cut with a two-pixel budget (≈128 units) and every required separation
  with at least a one-pixel budget (≈64 units). If the concept cannot afford
  those pixels while staying inside its keyline, reject it before the bake-off
  instead of repairing legibility/scalability after review.
- **On a coloured card, budget the outline as a silhouette line.** The
  visual-silhouette strip judges luminance, so a coloured element on a coloured
  card blacks out with it and only its light outline survives. That outline is
  what the distinctiveness gate sees: give it two output pixels at the smallest
  size where the element must still be nameable (a 28-unit ring clears `check`'s
  2.3% stroke floor and still fragments by 48px; 40 units holds). The stroke
  floor is a vanishing test, not a silhouette test. (L47.)
- **Spend the whole tile before tuning anything else.** If the budget above
  doesn't fit, the fix is almost never thinner margins or thicker strokes — it
  is deleting the background tile so the object *is* the icon. A mark drawn
  inside a tile pays for that margin twice, in the container and again in every
  counter it can no longer afford; going full-bleed typically returns 250–300
  units of grid. Then re-check §6's silhouette question: a full-bleed container
  whose outline runs parallel to the canvas is back to being a rounded square,
  so give it one measurable non-square feature — a perspective taper of roughly
  **1.5× base-to-top** reads at 32px, a 1.1× taper does not. (L28, L29.)
- **Topology before styling for routing marks.** If the object says that
  several inputs merge into one route, sketch that connectivity graph first and
  require every claimed input to visibly join the trunk in the blacked-out
  16/32px silhouette. A floating plug or detached lane can pass mechanical QA
  while telling the wrong product story; treat it as a craft failure, not a
  decorative gap.

---

## 3. Style families (pick ONE per icon)

Each maps to a preset you can start from: `python -m iconflow new <preset>`.
Use `python -m iconflow styles` for the packaged source of truth and
`python -m iconflow styles --gallery style-gallery.png` to inspect native 16px
proof. The full selection rules and clean-room research record live in
[`STYLE_CATALOG.md`](STYLE_CATALOG.md).

| Family | Preset | Use when | Signature techniques |
|---|---|---|---|
| **Gradient-glow** | `gradient-glow` | premium apps and modern SaaS favicons | masked shape + blurred ellipses behind it for inner glow, 2-stop diagonal gradient, optional display-p3 |
| **Flat geometric** | `flat-geometric` | tools, dashboards, dev apps | solid fills, 1 accent, squircle bg, bold negative-space glyph |
| **Line mark** | `line-mark` | minimal/editorial sites, icon SYSTEMS | uniform stroke, one counter-defined noun, and a single accent on transparent; gait or species must live in the contour |
| **Mascot / character** | `mascot` | consumer brands with an identity-owned character | hand-built paths, warm palette, and a thick outline whose outer silhouette identifies the species or character before facial detail |
| **Duotone cut** | `duotone-cut` | design tools and data products | one identifiable primary mass split by one large secondary plane |
| **Stencil cut** | `stencil-cut` | security, industrial, and print-led identities | one solid plate with bold transparent semantic cuts |
| **Pixel grid** | `pixel-grid` | games, terminal tools, intentional retro systems | 16px-first integer blocks, stepped corners, pixel parity |
| **Isometric** | `isometric` | storage, 3D, infrastructure, spatial products | two or three projected faces with explicit value steps |
| **Cut paper** | `cut-paper` | publishing, education, friendly productivity | broad offset layers and hard-edged depth without blur |
| **Enamel pin** | `enamel-pin` | community, events, collectible identities | dark material boundary, inset color, one bounded highlight |
| **Blueprint** | `blueprint` | engineering, architecture, CAD, systems | primary technical contour plus sparse subordinate guides |
| **Stained glass** | `stained-glass` | expressive creative, cultural, music products | three or four large panes separated by heavy leading that remains visibly distinct from the support field at 16px |
| **Risograph** | `risograph` | indie publishing, events, experimental tools | two controlled spot-color plates around a stable shared core |
| **Clay** | `clay` | friendly consumer, learning, creative tools | chunky volume, one explicit shadow edge, one highlight |
| **Cel shaded** | `cel-shaded` | games, animation, fandom, energetic consumer products | decisive ink contour plus one hard-edged shadow plane |
| **Chrome** | `chrome` | music, games, creator tools, high-energy premium products | solid contour plus six explicit hard value bands, each at least two output pixels wide; damage is a signature only when it removes contour mass; this discrete-band construction is the deliberate exception to the usual 2-stop gradient rule |
| **Ink brush** | `ink-brush` | editorial, culture, craft, wellness, expressive creators | one tapered calligraphic mass plus one broad edge-open dry cut |
| **Woodcut** | `woodcut` | animals, folklore, craft, culture, story-led products | closed relief mass plus a few broad, edge-open carved recesses |
| **Glass stack** | `glass-stack` | collaboration, spatial, media, modern cross-platform products | crisp translucent panes around one opaque semantic skeleton |
| **Woven** | `woven` | relationships, networks, exchange, communities | broad interlaced bands with explicit knockout gaps; both routes must remain separately traceable at 16px |

Mixing families produces mush. If a brand needs both (e.g. a glossy mascot),
commit to one as the base and borrow at most one technique from another.
Weight, fill, and palette are parameters inside a family; they do not count as
new styles by themselves.

**Material-layer gate.** Before approving a material family, hide the optical
effect—glass transparency, carved texture, brush distress, chrome reflection,
or pane color. The remaining opaque skeleton, raised field, main brush mass, or
solid contour must still name the same object at 16px. Material can enrich the
noun; it cannot be responsible for the noun.

---

## 4. Color

- **Dominant + accent.** One hue carries the icon; a second (often analogous or
  a brighter tint) adds a highlight. A third color must earn its place.
- **Gradients:** 2 stops, short angular travel (top-left → bottom-right). Keep
  both stops in the same hue family or one step apart — rainbow gradients muddy
  when small. The glow style adds *lightness* via blurred light ellipses, not
  extra hues.
- **Contrast both ways.** The mark must hold up on **white** (light UI/tab) and
  **#0b0d12** (dark UI/taskbar). If a dark mark dies on dark backgrounds, give it
  a light container or a subtle outline. The `check` command flags this.
- **display-p3** (optional, premium): provide an sRGB fallback then the P3
  variant (see SVG_TECHNIQUES.md). The
  build flattens to sRGB anyway, so P3 is a progressive enhancement for the live
  `favicon.svg` only.
- **Dark-mode favicon.svg:** an SVG can adapt with
  `@media (prefers-color-scheme: dark)` inside an inline `<style>`. Great for
  tab favicons; raster outputs bake the light variant.

---

## 5. The 16px test (the icon's real exam)

Before anything else feels done, judge the **16px and 32px** cells and the pixel
zoom in `review.png`:

- Is there **one** readable shape, or does it turn to grey soup? If soup →
  remove detail, increase weight, simplify silhouette.
- Are counters (holes in letters, gaps in the mark) still open, or filled in?
- Does a thin stroke disappear? Thicken it or switch to a filled glyph.
- Is the silhouette **distinctive** — could you tell it apart from a competitor
  in a row of tabs? Generic gear/rocket/checkmarks fail this.
- Run the **name-the-thing test at both 128px and 16px**. If the chosen view of
  an object names a stronger unrelated noun at either size, change the
  viewpoint before adding seams, highlights, or labels. Viewpoint is part of
  the concept because it determines the silhouette and counter geometry.
- Run a **punctuation collision test** on detached accents. A near-vertical cut
  aligned above a round dot/hinge groups into `!` at 16px even when both devices
  look intentional at 128px. Strip color and compare centerlines; offset them by
  at least two output pixels (about 128 units), change the cut angle, or remove
  one device.
- For a transparent tray/menu-bar target, test the 16px color mark on white,
  **#808080**, and **#0b0d12**. If one background swallows the silhouette, keep
  the single shape and add a contrasting **32–48-unit** edge (0.5–0.75 rendered
  pixel at 16px); then re-check that every semantic counter or panel gap still
  resolves to at least two clear pixels. Do not solve it with a full tile unless
  the product calls for one.
- Run a **suspension collision test** on anything carried from above. A dome
  over a body is an umbrella, a mushroom, or a table lamp until the canopy is
  panelled, at least two output pixels (about 128 units) of clear air separate
  hem from load, and the suspension reads as two unequal lines from the hem's
  outer ends rather than one central stem. All three are geometry; none of them
  can be added later with color. (L50.)
- If that tray target belongs to an established mascot or brand mark, preserve
  its palette and signature trait in color, and tighten the framing before
  recoloring it for presence. For the alpha-derived template, cut essential
  facial features, counters, and seams out of the silhouette instead of drawing
  them in the foreground color. Cut **exactly one** — every hole that rescues the
  template also removes color from the asset the taskbar shows — and keep it away
  from any join between two shapes, where a hole reads as a bite out of the
  contour. Inspect both actual 16px assets; passing only the color or only the
  template reduction is not enough. `iconflow check <master> --tray-svg <tray.svg>`
  audits the two reductions the build emits and reports a template that kept none
  of the color mark's features. (L48.)
- For raster/emote-based favicons, check 16px legibility and the maskable row as
  one decision. If scaling the face up triggers a safe-zone warning, preserve the
  strongest expression and shrink or remove peripheral props (stars, ears, labels)
  before pushing detail farther outward.
- For creator avatar favicons, do not preserve the full body just because it is
  semantically complete. Crop toward the face and one built-in identity trait
  before adding external accents; at 16px the expression carries the brand.
- If a creator face is readable but still trapped in a generic circle or
  rounded tile, spend the next pass on an identity-owned frame or unexpected
  crop before adding more facial detail. The frame must survive the visual
  silhouette strip. Do not borrow generic species ears when they could switch
  the reading from the person to an adjacent mascot.
- For a multi-page family, lock the shared face/frame paths in one generator.
  Vary one page hue that reads at 16px and one expression that resolves from
  roughly 32px; extra page-symbol badges weaken both identity and scalability.
- Treat shadows, glows, and outer accents as real visible footprint. If the
  maskable row or `check` warns, remove outer effects first, then shrink or
  reposition the signature detail inside the safe area.
- If the signature device is a negative-space notch, dovetail, or counter, give
  its narrow dimension roughly **128 units on the 1024 grid** and confirm at
  least two clear pixels remain in the 16px pixel zoom. A one-pixel gap is
  anti-aliasing, not an ownable device; choose another concept if the cut cannot
  grow without breaking the outer silhouette.
- If one detached accent explains the action or state, give its shortest dimension
  roughly **128 units** as well and verify two intentional pixels at 16px. Enlarge
  a semantic accent instead of adding a label; delete it if it is merely decoration.
  Keep at least one clear rendered pixel between the accent and the primary
  glyph—if they merge, the glyph's first reading must remain pure and the accent
  has failed.
- For a compact noun-plus-action utility mark, test the action accent on a
  **side edge before the top edge**. At 16px, a top accent on an otherwise
  nameable object readily becomes a chimney, antenna, or upload arrow and
  replaces the noun. Black out the finalist and require the accent to extend at
  least two rendered pixels laterally beyond the primary mass while the remaining
  contour still names the same object. If it only works above the object, return
  to divergence instead of explaining the shape with color or a label.
- For adjacent automation toggles, review the whole on/off family as a monochrome
  16px row. Keep one object silhouette per feature, but make the state change alter
  the object's **outer contour** by at least two rendered pixels (about 128 units on
  the 1024 grid). If the pair differs only by color, a tiny badge, an interior dot,
  or a slash that disappears at 16px, the state system fails even when each icon is
  individually recognisable.

Design *down*: get it perfect at 16–32px, then add only the richness that 256px+
can afford (subtle gradients, glow, inner shadows). Don't design a detailed
1024 illustration and hope it survives.

---

## 6. Anti-patterns (auto-fail)

- Photographic / many-stop gradients that turn to mud when small.
- Hairline strokes (<2.5% of side) and tiny text/letters inside the mark.
- Off-center marks that ignore optical balance.
- Edge-to-edge artwork with no safe area (gets clipped by mask/rounding).
- Five colors fighting. Drop-shadows that imply a light source the rest ignores.
- Reusing a stock glyph everyone uses (plain gear, plain rocket) → not distinctive.
- **A bare initial letter (or generic shape) on a gradient tile** — the "S / H /
  A monogram + corner dot" default. It passes every mechanical `check` and still
  reads as generic, because the blacked-out silhouette names nothing. Fuse the
  letter *into* an object (fado's plate-F) or drop it for a specific object
  silhouette. See `CONCEPTING.md` "Distinctiveness = specificity" and its
  exemplar gallery. This is the single most common way an AI icon looks
  competent and forgettable at once.
- For creator/mascot brands, using the cutest adjacent mascot when the site is
  about the creator/character → semantically wrong identity, even if cute.
- Painting the identifying trait inside an unchanged generic silhouette: eyes
  do not rescue a round animal head, a visor does not create an original
  character, and a colored slash does not break a horn. Make the trait remove,
  add, or redirect at least two pixels of outer contour at 16px.
- Transparent Apple touch icon (iOS fills the gaps black) — the build flattens it.
- Treating one literal full-card composition as a universal tray/menu-bar mark.
  Keep one semantic source, but expose the recognisable foreground group (or a
  geometry-linked `tray.svg`) so monochrome conversion does not collapse into a
  featureless square.
- **Two opaque foreground elements that cross or overlap** — a line *through* a
  glyph, a badge straddling a mark, a pulse over a play triangle. They look clever
  at 1024 but fuse into one muddy blob below ~32px and the user reads it as
  "blurry / unclear". Keep ONE dominant foreground shape; carry the second idea in
  **negative space, nesting, or a small corner accent** instead. If a concept only
  works because two shapes overlap, it will fail the 16px test — pick a different
  signature device that survives small (this is the distinctiveness-vs-legibility
  trade in §Concepting: simplify the execution, keep the idea).
- A vertical slit/cut centered over a detached circular accent. At 16px it is an
  exclamation mark before it is your intended object; offset or redesign the
  pair during the bake-off, not after color polish.

---

## 7. Self-critique prompt (run this in your head every iteration)

> "Cover the polished 256px version. Looking first at 128px, then only at the
> 16px and 32px cells on white and on dark: **in one noun, what object is this?**
> Did the noun change with scale or viewpoint? Does any cut-plus-dot pair become
> punctuation? If the honest answer is 'the
> letter X' or 'a rounded square,' the mark has no specificity — fix the *idea*
> (see `CONCEPTING.md`), not the polish. Otherwise: can I name it in under a
> second? Is it the same idea on both backgrounds? Is it distinct from a generic
> icon? What single change raises the weakest axis on the rubric?" Make that one
> change, re-render, repeat.

When all rubric axes are ≥4/5 and `check` is clean, build the targets.
See `REVIEW_CHECKLIST.md` for the scored rubric and `OUTPUT_TARGETS.md` for what
files each project type needs.
