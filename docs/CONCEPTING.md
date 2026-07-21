# Concepting — how to make an icon DISTINCTIVE (有特色)

Legibility gets you a usable icon. **Distinctiveness gets you a memorable one.**
This is the stage most AI-made icons skip, so they all look the same (a gear, a
sparkle, a blue gradient). Do not skip it. Diverge first, then converge with a
silhouette-driven bake-off.

> A distinctive mark = **one specific idea + one signature device, with a
> silhouette unlike anyone else's.** Not more detail — a sharper idea.

## Distinctiveness = specificity (read this first)

The single strongest predictor of a memorable icon in this system's canon is
that **the mark IS a specific, ownable thing** — a price tag, a cut gem, a
folded route map, a maneki-neko, an F built out of stacked plates. Its
blacked-out silhouette names an object, not a category. The weakest icons are
the opposite: **a bare letter or a generic shape parked on a gradient tile**,
with a small corner accent doing the "distinctiveness." Those pass every
mechanical check and still feel dead, because the silhouette says nothing.

> **The monogram trap.** A bare initial on a gradient square (a plain S, H, A +
> corner dot) is where mediocre icons live. A letter earns its place *only when
> it fuses into the object* — fado's "F" is literally stacked plates
> ([case](../casebook/2026-07-16-fado-website.md)). If you can lift the letter
> off the tile and the tile is still "just a gradient square," you have a
> monogram, not a mark. Fuse it or drop it.

Before you diverge, study **[What good looks like](#what-good-looks-like--the-exemplar-gallery)**
below — it is the vocabulary of moves that actually shipped well here.

---

## Step 1 — Diverge: generate 4+ concepts through different lenses

For the same brief, sketch (in words, then SVG thumbnails) at least four ideas
coming from *different* lenses. The point is range, not polish.

| Lens | Question | Example (a "focus timer" app) |
|---|---|---|
| **Object** | the literal thing | an hourglass |
| **Metaphor** | what it's *like* | a target / a single seed sprouting |
| **Verb** | the core action | a shrinking ring (time draining) |
| **Letterform fusion** | the initial *built out of* the object | an "F" whose stem and arms are stacked plates (fado) |
| **System/abstract** | a pattern that encodes it | concentric arcs = sessions |
| **Negative space / dual** | two readings in one shape | a clock face that's also a play ► |

Aim for 4 genuinely different directions. If two concepts share a silhouette,
they count as one — push for spread.

> The letterform lens is **fusion**, not "type a letter on a tile." If the
> initial is not *made of* the metaphor's geometry, it is the monogram trap
> above — treat it as a cliché to escape, not a concept.

---

## Step 2 — Apply the cliché filter

List the obvious icon for the category, then **cross it out and go one step
further**. These are the marks everyone already uses — start past them:

| Category | Overused (avoid as-is) | Push toward |
|---|---|---|
| **Any app (the lazy default)** | **the initial letter on a gradient tile — a bare S / H / A monogram + corner dot** | **fuse the letter INTO an object (fado's plate-F), or drop the letter for a specific object silhouette** |
| AI / ML | brain, robot head, ✦ sparkles, neural nodes, blue→purple gradient | a specific transformation, a letterform *fusion*, an unexpected ownable color |
| Chat / social | plain speech bubble | a bubble that *is* the monogram, or two forms interlocking |
| Finance | coin, $, up-arrow chart | a precise geometric motif, a unique chart silhouette |
| Notes / productivity | check, pencil, notepad | a structural metaphor (layers, a knot, a thread) |
| Dev tools | terminal `>`, `{ }`, gear | one signature glyph + ownable angle (cf. Stripe slashes) |
| Security | shield, padlock | the *action* of protecting, negative-space keyhole twist |
| Music / audio | eighth note, waveform | a custom waveform-as-letter, a single bold form |
| Bookmark / save | ribbon bookmark | a fold, a pin, a corner-turn unique to you |
| Mascot / pet | generic animal silhouette; adjacent mascot when the site is actually about a creator/person | the exact identity owner first, then a specific pose/expression + ownable palette |

If your concept is the "avoid" cell, it is not done.

---

## Step 3 — Add ONE signature device

Distinctiveness usually comes from a single deliberate move, not many. Pick one:

- **Dual reading / negative space** — encode a second meaning (FedEx arrow,
  Amazon a→z smile). The strongest, hardest, most memorable.
- **Ownable geometry** — a recurring angle, a consistent corner radius DNA, a
  signature cut. Repeat it so the brand "owns" that shape.
- **Letterform fusion** — the brand initial *is* the object.
- **Unexpected crop / scale** — zoom in past the obvious framing.
- **Ownable color pairing** — one specific, slightly-unexpected combination
  (not default blue). Color is half of recognition.
- **A single accent** — one dot/spark/cut in a deliberate spot that becomes a tag.

One signature device, executed cleanly, beats three competing ones.

For a creator who also has a mascot, test the identity boundary before the
bake-off: use the person's real crop, frame, expression, or built-in accessory.
A generic animal-ear silhouette may look cuter while silently changing *who*
the icon represents. If a face reads but its rounded tile does not, try an
ownable frame silhouette before adding another accessory.

---

## Step 4 — Converge: the silhouette + bake-off

Four hard tests decide it:

1. **Name-the-thing test (specificity gate).** Look at the blacked-out
   silhouette and say, in one noun, what object it is. If the honest answer is
   "the letter S" or "a rounded square with a glyph in it," the concept has no
   specificity — send it back to Step 1. A passing answer is a concrete thing:
   "a price tag," "a cut gem," "a folded map," "a cat." This gate is what
   separates the canon from the monogram trap; apply it *before* you fall for a
   nice gradient.
2. **Silhouette test.** Black out the mark. The `review` sheet now shows two
   versions: **alpha footprint** (outer/container shape) and **visual silhouette**
   (what the user actually sees, including white glyphs as negative space on an
   opaque card). The `compare` sheet's shape column uses the visual silhouette.
   If the pure visual shape is still recognisable *and* unlike a plain
   square/circle/teardrop, it has character. If the silhouette is generic, the
   color/gradient is doing all the work and it will blend in. Fix the *shape*.
3. **Maskable test.** Review the adaptive crop row. Essential glyph/detail must
   sit inside the central 40% safe-zone circle; full-bleed background color may
   extend to the edges, but idea-carrying detail should not.
4. **Row test.** Imagine it in a row of 8 competitor favicons/dock icons. Does it
   stand out in under a second? If not, sharpen the idea or the signature device.

Then run a real bake-off on your 2–3 finalists:

```bash
python -m iconflow compare a.svg b.svg c.svg --out bake.png
# Read bake.png: pick the most DISTINCTIVE that still reads at 16px & in shape.
```

Promote the winner to `master.svg`, then continue the normal
review-and-refine loop (`docs/REVIEW_CHECKLIST.md`).

---

## Worked example - event strategy website

Brief: a static Tokyo Game Show 2026 planning website that needs a favicon and
a Windows desktop shortcut. The obvious category marks were a gamepad, pixel
alien, controller button, expo badge, or tiny `TGS` lettering. Those all describe
"game show" generically, but they do not describe why the site exists.

The stronger one-word essence was **route**: the page is a practical plan for
tickets, lodging, team outreach, and on-site decisions. The concept set explored
three different silhouettes:

| Concept | Lens | Why it lost or won |
|---|---|---|
| ticket with route slash | Object + verb | Readable, but the silhouette was still close to a generic notched ticket. |
| five-day gate | System/abstract | Encoded the 5-day event, but collapsed into a plain `T`/gate shape at small sizes. |
| folded map with T-shaped route | Metaphor + letterform fusion | Won: the folded-map silhouette stayed distinctive, while the route doubled as a `T`. |

The winning refinement removed fold seam lines and other internal detail, enlarged
the mark, and kept only one foreground idea: a white T-shaped route with one
amber checkpoint inside a red folded map. The site title can carry "Tokyo Game
Show"; the icon carries the planning job.

Lessons to reuse:

- For content-heavy guides, choose the **user's job** (route, decide, compare,
  scout) over the category noun (game, conference, travel).
- If a proper name is long, do not force it into the 16px mark. Fuse one initial
  or idea into the geometry and let the page title/shortcut label carry the text.
- In the bake-off, prefer the candidate whose black silhouette is ownable, even
  when another candidate looks more literal in color at 128px.
- After choosing the winner, simplify once more for 16px: remove seam lines,
  tiny labels, secondary rails, and decorative dots unless they are the single
  signature accent.

---

## What good looks like — the exemplar gallery

These shipped marks are the house standard for distinctiveness. Every one BE a
specific object; none is a bare letter on a tile. Steal the *move*, not the
subject. Read the linked case for the full reasoning.

| Mark | Essence | Cliché escaped | Signature move | Why the silhouette is specific |
|---|---|---|---|---|
| **fado** ([case](../casebook/2026-07-16-fado-website.md)) | table | script "F" on wine-red; wine glass | **letterform fusion** — the F *is* stacked plates | reads as tableware, not a letter |
| **Bargain Hunter** ([case](../casebook/2026-07-16-bargain-hunter.md)) | deal | magnifier (collides w/ Search), cart | **container = object** — a price tag w/ a punched string-hole | tag shape = "price/deal" at 16px |
| **Snowy Repo Quest** ([case](../casebook/2026-07-16-snowy-repo-quest.md)) | quest | "S" monogram, compass, map pin | **faceted geometry** — a cut gem, one repeated cut angle | jewel facets = loot/reward |
| **CareerCat** ([case](../casebook/2026-07-16-career-cat.md)) | fortune | briefcase, ladder, generic cat | **mascot + one identity trait** — maneki-neko gold bell | "this cat," not any pet |
| **Tokyo Game Show** ([case](../casebook/2026-06-19-tgs-planning-site.md)) | route | gamepad, ticket, "TGS" text | **metaphor + letterform** — folded map whose route is a "T" | a folded map, not a game glyph |

More from the same canon (external repos, same principle — the silhouette is a
thing, not a letter):

- **Discord Message Extractor** — a faint message *stream* resolving into one
  bright pulled record + a cyan spark (verb: *extract*, drawn as a scene).
- **TwitchWatcher** — a flame with a **negative-space play triangle** cut into
  it (watch-streak = flame + play, one dominant shape, second idea in the cut).
- **Steam 餘額助手** — a ticket/voucher whose interior negative space is a bold
  arrow + a green check node (balance, redeemed).
- **Snowdrift** — a gold drawer/folder with a drift peak; the peaked tab is the
  ownable protrusion off an otherwise plain card (cf. L8).
- **Yonago Internet Plan** — a network **route node**: a Y-junction of fat rails
  into one amber hub (the user's job — a route — not "wifi bars").
- **Game Hype Radar** — a bold radar **sweep sector** with one gold blip; the
  swept wedge is a specific instrument, not a generic circle.

The through-line: pick the **user's job or the domain object**, then draw it as
its own silhouette. When you reach for a letter, fuse it (fado) or don't use it.

## Distinctiveness vs. legibility (resolve the tension)
They pull against each other: a dual-reading mark can get busy; a super-legible
mark can get generic. The resolution is almost always **simplify the execution,
sharpen the idea** — remove detail until only the one distinctive idea remains.
If you must trade, never ship something illegible at 16px; find a *different*
distinctive idea that survives small instead of keeping a clever-but-muddy one.

## Record your reasoning
In the final report, state: the brief's one-word essence, the cliché you avoided,
the signature device you chose, and why the winning silhouette is distinctive.
That makes the "特色" auditable instead of accidental.
