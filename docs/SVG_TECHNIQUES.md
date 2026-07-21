# SVG Techniques — copy-paste building blocks

Reusable, browser-tested snippets for hand-authoring an icon master. All assume
`viewBox="0 0 1024 1024"`. Combine, don't free-hand from scratch.

---

## 1. Squircle / superellipse container (app-icon base)

A 22%-radius rounded square is a good iOS-squircle proxy. Put the brand fill on
it, then draw the glyph on top.

```svg
<rect x="0" y="0" width="1024" height="1024" rx="225" ry="225" fill="url(#bg)"/>
```

For a truer squircle, use a path (flatter sides, rounder corners):

```svg
<path d="M512 16C 180 16 16 180 16 512S 180 1008 512 1008 1008 844 1008 512 844 16 512 16Z" fill="url(#bg)"/>
```

---

## 2. Brand gradient (2-stop diagonal — the workhorse)

```svg
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#8b5cf6"/>
    <stop offset="1" stop-color="#6d28d9"/>
  </linearGradient>
</defs>
```

Radial highlight (fake top-light, very subtle — keep opacity low):

```svg
<radialGradient id="sheen" cx="0.3" cy="0.25" r="0.9">
  <stop offset="0" stop-color="#ffffff" stop-opacity="0.35"/>
  <stop offset="0.6" stop-color="#ffffff" stop-opacity="0"/>
</radialGradient>
<rect width="1024" height="1024" rx="225" fill="url(#sheen)"/>
```

---

## 3. Masked inner glow

The premium look = a crisp masked shape with **blurred light/dark ellipses
behind it** for an inner glow, instead of flat fills. Pattern:

```svg
<defs>
  <filter id="blur" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="40"/>
  </filter>
  <mask id="shapeMask">
    <!-- WHITE = visible. Draw your silhouette here in white. -->
    <path d="...your mark outline..." fill="#fff"/>
  </mask>
</defs>

<!-- base fill -->
<g mask="url(#shapeMask)">
  <rect width="1024" height="1024" fill="#7e14ff"/>
  <!-- light blobs lift one edge -->
  <ellipse cx="300" cy="260" rx="220" ry="120" fill="#ede6ff" filter="url(#blur)"/>
  <!-- darker blobs deepen the opposite edge -->
  <ellipse cx="780" cy="820" rx="260" ry="160" fill="#4c0fb0" filter="url(#blur)"/>
  <!-- an accent-hue blob adds life -->
  <ellipse cx="820" cy="300" rx="120" ry="180" fill="#47bfff" filter="url(#blur)"/>
</g>
```

Everything outside the mask is clipped, so the blurs read as glow *inside* the
shape. Tune blob position, size, and color on the contact sheet; the technique
is useful only when the underlying silhouette already passes without color.

---

## 4. display-p3 with sRGB fallback (premium live favicon.svg)

Browsers that understand `color()` use the wider gamut; others use the first
declaration. The raster build flattens to sRGB regardless.

```svg
<path d="..." style="fill:#863bff;fill:color(display-p3 .5252 .23 1);fill-opacity:1"/>
```

---

## 5. Dark-mode-aware favicon.svg

```svg
<style>
  .fg { fill: #0b0d12; }            /* light UI */
  @media (prefers-color-scheme: dark) { .fg { fill: #f5f5f7; } }
</style>
<path class="fg" d="..."/>
```

---

## 6. Uniform line mark (system-icon / minimal-site style)

Use `fill:none`, one accent stroke, round caps/joins, and a uniform width. On a
1024 grid use stroke 40–56.

```svg
<g fill="none" stroke="#aa3bff" stroke-width="48"
   stroke-linecap="round" stroke-linejoin="round">
  <circle cx="512" cy="430" r="210"/>
  <path d="M512 660 V900"/>
</g>
```

To build a whole icon set, define each glyph as a `<symbol>` with its own
viewBox in one sprite `icons.svg`, then `<use href="#name-icon"/>`; this keeps
geometry and stroke DNA consistent.

---

## 7. Monogram / letter mark — FALLBACK ONLY, must fuse

> A bare letter on a gradient tile is the **monogram trap** (see `CONCEPTING.md`,
> "Distinctiveness = specificity"): legible but generic, and it scores ≤3 on
> distinctiveness. Reach for a letter *only* when it fuses into the object
> (fado's F = stacked plates, §10) or as a deliberate last resort when no object
> metaphor exists at all. Prefer an ownable object silhouette (§12).

If you do use a letter, make it bold, keep counters open at 16px, and give the
letter or its container an ownable twist instead of shipping a plain glyph on a
plain square:

```svg
<rect width="1024" height="1024" rx="225" fill="url(#bg)"/>
<text x="512" y="512" font-family="Inter, Arial, sans-serif" font-weight="800"
      font-size="620" fill="#fff" text-anchor="middle"
      dominant-baseline="central">A</text>
```

Note: `<text>` renders via the build browser's fonts. For a guaranteed-stable
result across machines, convert the glyph to a `<path>` once you're happy with it
(it will then be machine-independent). Better still, redraw the letter *as* the
metaphor's geometry — see §10 (letterform fusion) and §12.

---

## 8. Mascot / character

Hand-built paths with a **thick dark outline** (so the face survives shrinking),
warm 2–3 color palette, and large simple eyes. Build order: container/background
→ silhouette → outline stroke → interior color blocks → 2–3 expression details.
Keep the face occupying the keyline circle; don't add fur texture or fine
whiskers thinner than ~9 units — they vanish. See `templates/presets/mascot.svg`
for a complete, working starting point.

---

## 9. Negative-space glyph (memorable, scalable)

Cut the icon OUT of a solid shape rather than drawing it on top — strong
silhouettes that stay crisp. Use `fill-rule="evenodd"` or a mask:

```svg
<path fill-rule="evenodd"
      d="M112 112 h800 v800 h-800 Z   M512 300 L700 700 H324 Z"/>
```
(outer square minus an inner triangle → triangle-shaped hole.)

---

## 10. Signature devices (for distinctiveness — see CONCEPTING.md)

**Dual reading via a single negative-space cut** — make the gap mean something
(an arrow hidden between two forms, a letter inside a shape):

```svg
<!-- a 'play' triangle that is also the counter of a 'D' monogram -->
<path fill="#111" fill-rule="evenodd"
      d="M240 200 h300 a284 284 0 0 1 0 568 H240 Z
         M360 360 V632 L600 496 Z"/>
```

**Letterform fusion** — the brand initial *is* the object. Build the letter from
the metaphor's geometry rather than typing text:

```svg
<!-- an 'S' whose terminals are two arrowheads (flow/exchange) -->
<path fill="none" stroke="#10b981" stroke-width="120" stroke-linecap="round"
      d="M680 360 a160 160 0 0 0 -320 0 a160 160 0 0 0 160 160 a160 160 0 0 1 160 160 a160 160 0 0 1 -320 0"/>
```

**Ownable geometry / repeated angle** — pick ONE angle (e.g. 23°) or one corner
radius and repeat it across every element so the brand "owns" that shape DNA
(cf. Stripe's parallel slashes). Keep the angle identical everywhere.

**Single accent tag** — one deliberate dot/spark/notch in a fixed spot becomes a
recognisable signature; use exactly one, in the accent hue.

Run the silhouette test (`iconflow review`) on any of these: if the blacked-out
shape stays distinctive, the device is working.

## 11. Semantic master layers and target variants

One source of truth does not mean one literal composition on every surface. A
full app tile and a 16px monochrome menu-bar mark have different constraints.
Give important groups stable IDs so the build/review pipeline can select the
right semantic role without duplicating the design:

```svg
<g id="iconflow-background">...</g>
<g id="iconflow-mark">
  <path id="iconflow-core" d="..."/>
  <path id="iconflow-signature" d="..."/>
</g>
```

- `background` may fill an app tile but should not become the macOS template
  silhouette.
- `mark` carries recognition and should survive monochrome conversion.
- `signature` is the one functional cut/accent that distinguishes the mark.
- When automatic extraction cannot preserve the intended hierarchy, keep a
  small `tray.svg` variant next to `master.svg`; it must reuse the same core
  geometry rather than becoming a second logo.

Always review the transformed target bytes. Judging the raw master alone cannot
catch a lost tray counter, an incorrect maskable composition, or platform-only
corner processing.

## 12. Ownable object starters (the specificity toolkit)

Each of these is **one dominant object shape** distilled from a shipped exemplar
(see `CONCEPTING.md`'s gallery). Run the name-the-thing test on the black
silhouette before adding color — if it already reads as the object, you are past
the monogram trap.

**Price tag with a punched string-hole** (Bargain Hunter) — the container *is*
the object; the hole is a `fill-rule:evenodd` cut, so it stays one shape:

```svg
<path fill="url(#bg)" fill-rule="evenodd"
      d="M512 168 L792 384 V740 a72 72 0 0 1 -72 72 H304 a72 72 0 0 1 -72 -72 V384 Z
         M512 322 a58 58 0 1 0 0.1 0 Z"/>
```

**Faceted gem** (Snowy Repo Quest) — repeat ONE cut angle and outline every
facet so it reads as a cut crystal, not a random polygon cluster:

```svg
<g stroke="#0e3b37" stroke-width="14" stroke-linejoin="round">
  <polygon points="300,470 392,300 444,470" fill="#2a8079"/>
  <polygon points="392,300 632,300 580,470 444,470" fill="#d8a24a"/>
  <polygon points="632,300 724,470 580,470" fill="#16514c"/>
  <polygon points="300,470 444,470 512,800" fill="#2a8079"/>
  <polygon points="444,470 580,470 512,800" fill="#236f68"/>
  <polygon points="580,470 724,470 512,800" fill="#16514c"/>
</g>
```

**Folded map / voucher card** (Tokyo Game Show, Steam) — the dipped top/bottom
edge at each fold seam is the ownable outline; carry the idea as one bold path
on top (here a T-route), not extra seam lines:

```svg
<path fill="url(#mapGrad)"
      d="M214 246L374 196L512 256L650 196L810 246C832 253 848 274 848 297V746
         C848 775 820 797 792 788L650 744L512 806L374 744L232 788C204 797 176 775 176 746
         V297C176 274 192 253 214 246Z"/>
<path d="M312 390H712" stroke="#fffaf0" stroke-width="96" stroke-linecap="round"/>
<path d="M512 390V656" stroke="#fffaf0" stroke-width="96" stroke-linecap="round"/>
<circle cx="512" cy="656" r="72" fill="#fffaf0"/>
<circle cx="512" cy="656" r="39" fill="#d5962f"/>
```

**Radar sweep sector** (Game Hype Radar) — a filled wedge is a specific
instrument where a plain ring is generic; add exactly one accent blip:

```svg
<circle cx="512" cy="512" r="322" fill="none" stroke="#7fd8c8" stroke-width="30" opacity="0.32"/>
<path d="M512 512 L512 180 A332 332 0 0 1 828 408 Z" fill="url(#sweep)"/>
<circle cx="512" cy="512" r="48" fill="#c7f2e8"/>
<circle cx="716" cy="286" r="78" fill="url(#blip)"/>
```

## Rendering note
Every snippet is rendered by a network-isolated headless Chromium session,
including `<filter>`, gradients, masks and `prefers-color-scheme`. Use the
target-aware Review Lab to inspect post-processing as well as the raw render.
