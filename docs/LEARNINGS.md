# Learnings — distilled rules from shipped icons

Read this **before designing** (it is step 0 of the procedure in `AGENTS.md`).
Each rule was earned from a real case in `casebook/` — this file is the
distilled form of that experience. Add to it via the protocol in
`docs/EVOLUTION.md`; never remove a rule without recording why.

Format: **statement → why → evidence**. Rules also folded into an
authoritative doc say where.

---

## L1 — One dominant foreground shape; never cross two opaque elements
Two opaque foreground elements that overlap (a line *through* a glyph, a badge
straddling a mark) look clever at 1024 but fuse into one muddy blob below
~32px. Carry the second idea in negative space, nesting, or a small corner
accent.
*Why:* below 32px anti-aliasing merges adjacent opaque shapes; the user reads
"blurry", not "clever".
*Evidence:* early tray/app icon sessions. Folded into `DESIGN_PLAYBOOK.md` §6.

## L2 — Choose the user's *job*, not the category noun
For content/guide sites, an icon about what the user is trying to *do*
(route, decide, compare, scout) beats the category object (game, conference,
travel). Category nouns are where clichés live.
For a privacy-sensitive product, that verb is also the safest public design
brief: preserve the geometry, scores, failed readings, and target evidence, but
record the public case under a neutral product label without sensitive category
nouns, private repository names, or local paths.
*Evidence:* [casebook/2026-06-19-tgs-planning-site.md](../casebook/2026-06-19-tgs-planning-site.md) — folded-map route beat
gamepad/ticket concepts;
[private route finder](../casebook/2026-08-09-private-media-route-fan.md) and
[private discovery hub](../casebook/2026-08-09-private-media-discovery-pearl.md)
show the privacy-safe form. Folded into `CONCEPTING.md` and `EVOLUTION.md`.

## L3 — Judge the bake-off by silhouette, not by 128px color
Prefer the candidate whose blacked-out visual silhouette is ownable, even when
another candidate looks more literal and attractive in color at 128px. Color
is easy to like and easy to forget; shape is what a favicon row remembers.
*Evidence:* [casebook/2026-06-19-tgs-planning-site.md](../casebook/2026-06-19-tgs-planning-site.md). Enforced by the
visual-silhouette strip in `iconflow review`/`compare`.

## L4 — After picking the winner, simplify once more for 16px
Remove seam lines, tiny labels, secondary rails and decorative dots unless one
of them *is* the signature accent. The winning concept usually still carries
draft detail it no longer needs.
*Evidence:* [casebook/2026-06-19-tgs-planning-site.md](../casebook/2026-06-19-tgs-planning-site.md).

## L5 — Don't force a long proper name into the mark
If the name is long, fuse ONE initial or idea into the geometry and let the
page title / shortcut label carry the text. Tiny lettering inside a 16px mark
is unreadable and generic at once.
*Evidence:* [casebook/2026-06-19-tgs-planning-site.md](../casebook/2026-06-19-tgs-planning-site.md). Folded into
`CONCEPTING.md`.

## L6 — Pillow ICO: pack from the largest frame
When packing a multi-size `.ico` with Pillow, the base image must be the
**largest** frame — Pillow silently drops requested sizes larger than the
base, yielding a 16px-only icon that looks fine until Windows scales it.
*Evidence:* bookmark-manager icon regression. Mechanized in
`iconflow/assemble.py` (`write_ico`).

## L7 — Version Windows shortcut icon paths; verify what the shell resolves
After rebuilding an exe/shortcut icon, Explorer often shows the old one. Verify
the source bytes first, but do not assume recreating a `.lnk` is a cache bust:
if `IconLocation` still names the same canonical `.ico`, the shell can keep the
old pixels. Copy the verified icon to
`shortcut-icon-<first-12-sha256>.ico`, recreate the shortcut against that path,
read `IconLocation` back, and inspect or extract the icon resolved from the
actual shortcut. Cache deletion is a secondary recovery step, not the proof.
When scripting the digest, feature-detect `Get-FileHash` or use .NET SHA-256;
not every Windows PowerShell host exposes the same cmdlets.
*Evidence:* [private route finder](../casebook/2026-08-09-private-media-route-fan.md)
and [private discovery hub](../casebook/2026-08-09-private-media-discovery-pearl.md).
Mechanized by `iconflow shortcut --content-address-icon`; folded into
`OUTPUT_TARGETS.md` and the iconflow skill's delivery notes.

## L8 — On a full-background app TILE, distinctiveness lives in the mark, not the silhouette
When the icon is an opaque rounded-square tile (app/Tauri/Electron), the alpha
footprint *and* the blacked-out visual silhouette are both just the rounded
square — the silhouette test cannot gate distinctiveness. So the visible mark
must itself carry an ownable shape. If the mark grows to nearly fill the tile,
its edges run parallel to the tile and it reads as a plain filled square; keep a
clear background margin (mark ≲ ~65% of the tile) and give it one bold
protruding/asymmetric feature (a tail, a notch, an off-axis element) so the
*visible* shape is recognisable.
*Why:* a mark whose bounding box matches the tile has no shape of its own; the
eye sees "filled tile", not "speech bubble".
*Evidence:* [casebook/2026-07-03-streamscribe.md](../casebook/2026-07-03-streamscribe.md) — shrinking the bubble off the
tile edges + enlarging the tail lifted distinctiveness 3→4 (and balance 4→5).

## L9 — Kill silhouette collisions with universal system icons at bake-off
Before falling in love with a concept, name what its *silhouette* already means
on every OS: circle+tail = search/magnifier, gear = settings, house = home,
bell = notifications, triangle = play. If your mark's outline matches one, no
styling (color, gradient, an attached block) will rescue it — small sizes strip
the styling and leave the borrowed meaning. Kill the concept, don't iterate it.
*Why:* users read icon silhouettes before color or detail; a collided silhouette
answers "what is this?" with the *wrong app*.
*Evidence:* [casebook/2026-07-03-mobile-tether-hub.md](../casebook/2026-07-03-mobile-tether-hub.md) — a data-gauge ring whose
end became a cable+plug read as a magnifying glass at every rendered size; the
letterform concept shipped instead.

## L10 — For creator/mascot brands, choose the identity owner before the cute object
If a creator has both a person/character identity and a separate mascot, do not
default to the cutest adjacent mascot for the favicon. Pick the identity the
site is actually representing, then simplify it for small sizes. A semantically
wrong cute mark can feel careless even when it is visually on-brand.
*Why:* favicons are identity anchors; users and creators read them as "who this
site is about" before they read the page title.
*Evidence:* [casebook/2026-07-06-creator-favicon.md](../casebook/2026-07-06-creator-favicon.md) — a generic bunny emoji or
the strongest bunny-ear silhouette risked reading as a bunny mascot, while the
shipped mark used the chibi persona emote face with one heart tag.
[casebook/2026-07-14-creator-window-favicon-family.md](../casebook/2026-07-14-creator-window-favicon-family.md)
rejected tall rabbit ears again: a pointed chapel-window frame supplied the
ownable silhouette, while the real white bunny hairpin remained an accessory
inside the person's portrait rather than turning the portrait into the mascot.

**Sibling marks:** when the mascot is already spent on one surface (the desktop
app icon), do not give a second surface a weaker variation of it. Source that
mark from what the surface is *about* — the page's own subject will hand you a
specific object the mascot family could never reach, and the two marks then read
as a family with distinct jobs rather than as one icon and its understudy.
*Evidence:* [casebook/2026-08-08-snowy-site-caret-keycap.md](../casebook/2026-08-08-snowy-site-caret-keycap.md) —
the owner asked for a site favicon only *weakly* related to the brand; with the
snow-fox off the table, the commands page's own caret prefix produced a keycap.

## L11 — Raster-source favicons need direct raster packaging plus both small-size tests
When the identity source is a raster emote, avatar, or photo, do not wrap it in
an SVG `<image>` and assume that every browser favicon path will decode the
embedded bytes. A Chromium favicon/static-render path can display that wrapper
as broken even when the SVG opens elsewhere. Link a real PNG/ICO set directly;
keep `favicon.svg` only when it is an independent vector alternative.

Do not fix 16px legibility only by scaling the raster face outward. A bigger crop
may make the tab icon clearer while pushing essential detail outside the
adaptive-icon safe zone.
If the emote's expression is already strong, preserve that expression and shrink
or remove outer props (stars, ears, labels, badges) before enlarging the face.
For creator avatar favicons, first tighten the crop around the expression and
one built-in identity trait (hair flower, glasses, face shape) before adding any
external accent; the external accent often steals pixels from the face at 16px.
Iterate the crop, badge, and single accent with `check` plus the maskable preview
before building.
*Why:* raster emotes carry detail at the edges, and adaptive crops punish those
edges even when the small favicon row looks better. Avatar faces also become
pink/skin-tone mush at 16px when the whole figure is preserved for semantic
completeness instead of cropped for expression.
*Evidence:* [casebook/2026-07-06-creator-favicon.md](../casebook/2026-07-06-creator-favicon.md) — enlarging the
a love emote improved perceived tab size but triggered the maskable audit;
the safe rounded badge shipped instead. [casebook/2026-07-06-creator-favicon-confident.md](../casebook/2026-07-06-creator-favicon-confident.md)
kept a confident sunglasses expression, but removed the outside star and
shrunk the crop to clear the maskable audit. [casebook/2026-07-07-hitohira-hana-favicon.md](../casebook/2026-07-07-hitohira-hana-favicon.md)
replaced a full-avatar crop plus petal accent with a closer face crop and built-in
hair-flower detail to raise 16px legibility.
[casebook/2026-07-14-creator-favicon-face.md](../casebook/2026-07-14-creator-favicon-face.md)
confirmed the packaging boundary: the identity owner preferred the warmer real
face even with softer 16px pixels, but Chromium rejected a raster data URI
embedded inside SVG, so the face had to ship through PNG/ICO links.

## L12 — Treat shadows and outer effects as real maskable footprint
Drop shadows, glows, and far-edge accents can make a 16px favicon look richer,
but they also expand the visible footprint that maskable audits and adaptive
crops must preserve. Remove or minimize outer effects before final review unless
the effect is essential to the mark; keep the signature device inside the safe
area instead of relying on edge decoration.
*Why:* adaptive icons crop by visible detail, not by the designer's intent, and
blurred effects can push an otherwise centered mark outside the safe zone.
*Evidence:* [casebook/2026-07-07-codex-handbook.md](../casebook/2026-07-07-codex-handbook.md) — removing a drop shadow and
shrinking the folded corner cleared the maskable warning without reducing
16px legibility. Folded into `DESIGN_PLAYBOOK.md` §5.

## L13 — Multi-page favicon families: one shared vector mark, differentiated by hue + expression
When a site needs a distinct favicon per page, do not design N unrelated icons
(camera for the photo page, gamepad for the game page — those collide with
system icons per L9 and shatter brand recognition). Keep ONE shared mark and
vary exactly two channels: the badge/background hue (the only channel that
reliably reads at 16px) and one expressive detail (face expression, accent
glyph) that reads from ~32px up. If the shared mark descends from a raster
emote/avatar, redraw it as vector — pick 2–3 identity traits (bangs shape,
signature accessory, blush) and rebuild them as flat shapes; a 112px raster
downsampled to 16px is mush no matter how well it is cropped (L11's ceiling).
Single-source the shared geometry in a generator script kept in the consuming
repo so variants cannot drift.
*Why:* tab rows are scanned by color first, shape second, detail last; and
vector shapes let you place pixel-scale contrast deliberately where a
downsampled raster averages it away.
*Evidence:* [casebook/2026-07-08-creator-favicon-family.md](../casebook/2026-07-08-creator-favicon-family.md) — the vector chibi
redraw beat both a tighter raster crop (16px mush, generic-circle silhouette)
and a kana letterform (read as Latin "U" at small sizes); five hue+expression
variants ship from one generator.
[casebook/2026-07-14-creator-study-favicon.md](../casebook/2026-07-14-creator-study-favicon.md)
extended that family with exactly one study hue and one focused expression.
[casebook/2026-07-14-creator-window-favicon-family.md](../casebook/2026-07-14-creator-window-favicon-family.md)
kept the same rule while upgrading the shared geometry to an ownable pointed
window silhouette; all five subpages still vary only hue and expression.

## L14 — A literal "trace" mark (ECG / waveform / line chart) must reduce to ONE bold feature for 16px
A data-trace metaphor (heartbeat ECG, audio waveform, line graph) is the obvious
pull for monitor / analytics / vitals apps, but every extra vertex is a detail
that fuses into a faint squiggle below ~24px. Keep exactly ONE bold feature — a
single tall peak/spike — and carry the "it's a trace/heartbeat" read through
asymmetry plus ONE detached accent (a leading node), not through additional peaks
or a full P-QRS-T shape.
*Why:* legibility is the persistent weakest first-pass axis, and multi-vertex
line marks are its most common cause — they look rich at 128px and vanish at
16px. Corollary of §5's 16px test and L1 (one dominant shape).
*Evidence:* [casebook/2026-07-09-pc-vitals.md](../casebook/2026-07-09-pc-vitals.md) — a full ECG trace scored
legibility 3 (16px squiggle); reducing to one peak + one undershoot + a detached
live-cursor node lifted it to 4. The busier node+arcs alternative collided with
sound/broadcast (L9).

## L15 — A signature negative-space cut must own at least two pixels at 16px
If a dual-reading mark depends on one notch, dovetail, or handoff cut, make the
cut's narrow dimension roughly **128 units or more on the 1024 grid**, then verify
that it remains at least two clear pixels wide in the 16px pixel zoom. A one-pixel
gap is anti-aliasing, not a signature device. If enlarging the cut breaks the
outer form, switch concepts instead of restoring tiny detail.
*Why:* negative space is an excellent way to keep one dominant foreground shape,
but only when its second reading survives the product's smallest rendered size.
*Evidence:* [casebook/2026-07-11-snowy-twitch-bot.md](../casebook/2026-07-11-snowy-twitch-bot.md) — the enlarged dovetail
handoff cut lifted distinctiveness 3→4 while preserving legibility 4. Folded into
`DESIGN_PLAYBOOK.md` §5.

## L16 — A detached functional accent must own two pixels, stay detached, and explain the verb
A single detached accent can carry the action in an otherwise static mechanical
mark — an escaped keycap makes a clamp read as "release" — but its shortest
dimension should be roughly **128 units or more on the 1024 grid** so it remains
two deliberate pixels at 16px. If the accent is only decorative, remove it; if it
is semantic, enlarge it rather than adding text or a second symbol. Preserve at
least one clear rendered pixel between it and the primary glyph; a merged accent
must not corrupt the glyph's first reading.
*Why:* a one-pixel accent looks like raster noise and cannot communicate motion or
state, while a two-pixel accent survives as a deliberate cue without making the
dominant silhouette busy.
*Evidence:* [casebook/2026-07-12-ctrl-rescue.md](../casebook/2026-07-12-ctrl-rescue.md) — enlarging the escaped amber
keycap from 116 to 128 units made the release cue stable at 16px and lifted
legibility, balance, scalability, and craft. Folded into `DESIGN_PLAYBOOK.md` §5.
[casebook/2026-07-13-media-hub.md](../casebook/2026-07-13-media-hub.md) — keeping the corner hub-node off the H
preserved the letter at 16px; the earlier masked glow fused its silhouette into
a C-shaped blob.
**Correction (owner review 2026-07-16):** this case is now the canonical example
of the *monogram trap* (L22), not a mark to emulate. Keeping the node off the H
is still correct *mechanically*, but a bold H on a gradient tile is exactly the
generic result the owner rejects — mechanical compliance is a floor, not
distinctiveness. Treat media-hub as a cautionary contrast to fado, not a model.

## L17 — Express small asymmetry through position before rotation
When a proof gate, badge, or counter is only a few pixels wide at the final
size, keep its critical edges on the raster rhythm and create character through
an off-axis **position**. A slight rotation that looks refined at 1024 often
spends the 16px counter on diagonal anti-aliasing. Rotate only if the pixel zoom
still shows every essential gap as two deliberate pixels.
*Why:* legibility and scalability are tied as the weakest first-pass axes;
subtle rotation consumes both without adding a new recognisable silhouette.
*Evidence:* [casebook/2026-07-13-iconflow-brand.md](../casebook/2026-07-13-iconflow-brand.md) — replacing an 8°,
224-unit gate with an offset, axis-aligned 256-unit gate and 128-unit counter
lifted legibility 3→4 and scalability 3→5. Folded into
`DESIGN_PLAYBOOK.md` §2/§5.

## L18 — A semantic master may need a geometry-linked target composition
“One master” means one recognisable geometry and source of truth, not one
literal full-card composition forced onto every surface. Give background,
mark, and signature stable semantic groups; when a 16px monochrome tray target
cannot preserve the app card's hierarchy, keep a mark-only `tray.svg` that
reuses the same core paths. Review and QA must inspect the exact transformed
bytes that the build emits.
*Why:* converting a full opaque card's alpha directly to a macOS template yields
a featureless black square, while separately redrawing a tray logo allows the
identity to drift.
*Evidence:* [casebook/2026-07-13-iconflow-brand.md](../casebook/2026-07-13-iconflow-brand.md) — semantic groups plus the
geometry-linked tray source preserved the rail, gate, and stepped terminal in
both color and template output. Folded into `SVG_TECHNIQUES.md` §11 and
mechanized through `preview_assets`, `tray_svg`, and fail-closed template
extraction.

## L19 — Continuous dual-flow marks need post-bake stroke mass for 16px counters
An elegant dual-flow S/ribbon that wins silhouette bake-off can still fail first-pass legibility/scalability if stroke mass is tuned at 128px. After choosing the continuous dual-flow concept, enlarge envelope + stroke until the 16/32 pixel-zoom still shows open counters on both lobes — before shipping.
*Why:* thin continuous curves anti-alias into a flat blob at favicon size even when the black silhouette concept is correct.
*Evidence:* [casebook/2026-07-20-xrl-screening-favicon.md](../casebook/2026-07-20-xrl-screening-favicon.md) — first-pass S scored legibility/scalability 3; raising stroke ~128→148 and expanding the path envelope lifted both to 5.

## L20 — Allocate the 16px pixel budget before authoring the first finalist
On the 1024 grid, treat 64 units as roughly one output pixel. Before drawing,
give every idea-carrying accent or negative-space cut at least two pixels
(≈128 units) and every required separation at least one pixel (≈64 units). If
the concept cannot meet that budget inside its keyline, discard it before the
bake-off rather than using review to discover that its signature vanished.
*Why:* legibility and scalability remain tied as the weakest first-pass axes
across the casebook; the repeated failure is budgeting shapes at 128px and only
later discovering their 16px pixel cost.
*Evidence:* [casebook/2026-07-11-snowy-twitch-bot.md](../casebook/2026-07-11-snowy-twitch-bot.md),
[casebook/2026-07-12-ctrl-rescue.md](../casebook/2026-07-12-ctrl-rescue.md),
[casebook/2026-07-18-snowy-twitch-bot-fox-badge.md](../casebook/2026-07-18-snowy-twitch-bot-fox-badge.md),
and [casebook/2026-07-20-btrw-browser-proxy.md](../casebook/2026-07-20-btrw-browser-proxy.md).
[casebook/2026-07-24-jp-auction-opportunity-desk.md](../casebook/2026-07-24-jp-auction-opportunity-desk.md)
confirmed the preventive form of this rule: a 136-unit hourglass waist and
132-unit semantic accent cleared legibility and scalability on the first
16px review pass.
Folded into `DESIGN_PLAYBOOK.md` §2.

## L21 — Distinctiveness is specificity: make the mark a specific object, not a letter on a tile
The strongest icons in the canon each BE a specific, ownable thing whose
blacked-out silhouette names an object — a price tag, a cut gem, a folded map, a
maneki-neko, an "F" made of plates. The weakest are a bare initial or generic
shape on a gradient tile with a corner accent: they pass every mechanical check
and still read as generic, because the silhouette says nothing. Run the
**name-the-thing test** (CONCEPTING §4): if the honest one-noun answer is "the
letter X" or "a rounded square," the concept has no specificity — fix the idea,
not the polish.
*Why:* users read silhouettes before color or detail; a silhouette that names an
object is remembered, a letter-on-a-tile is not.
*Evidence:* owner-curated canon —
[fado](../casebook/2026-07-16-fado-website.md) (plate-F),
[bargain-hunter](../casebook/2026-07-16-bargain-hunter.md) (price tag),
[snowy-repo-quest](../casebook/2026-07-16-snowy-repo-quest.md) (gem),
[career-cat](../casebook/2026-07-16-career-cat.md) (maneki-neko),
[tgs-planning-site](../casebook/2026-06-19-tgs-planning-site.md) (folded map).
Confirmed again by a later gateway-site case (kept out of this repo), where a
bold access-ticket silhouette beat both a monogram initial and decorative
seasonal motifs that died at 16px.
Folded into `CONCEPTING.md` ("Distinctiveness = specificity" + exemplar gallery),
`DESIGN_PLAYBOOK.md` §6/§7, `REVIEW_CHECKLIST.md` axis 2, and an advisory
`iconflow/qa.py` generic-silhouette warning.

## L22 — A letter earns a favicon only by fusing into the object; a bare monogram scores ≤3
A brand initial is legitimate only when it is *built out of* the metaphor's
geometry (fado's "F" is stacked plates). A plain letter set on a gradient square
is the monogram trap: legible but generic. Score it ≤3 on distinctiveness and
fix the shape/idea, never ship it as-is.
*Why:* legibility and distinctiveness are different axes; a bare monogram buys
the first and forfeits the second, which is why it clears `check` yet feels dead.
*Evidence:* [fado](../casebook/2026-07-16-fado-website.md) (plate-F reads as
tableware, memorable) vs. [media-hub](../casebook/2026-07-13-media-hub.md)
(bold-H-on-gradient-tile — mechanically clean, distinctiveness 4 in its own
record, yet the owner's canonical example of a mediocre monogram; see the L16
correction). Folded into `CONCEPTING.md`'s lens table and cliché filter, and
`SVG_TECHNIQUES.md` §7 (letter mark demoted to fallback).

## L23 — Feed the evolution loop a success canon, not only failures
`case stats` can only learn from what the casebook holds. When the casebook is
built almost entirely from iterated/repaired sessions, the system optimizes for
passing its own mechanical gates and never learns what *excellent* looks like — it
even recorded a mediocre monogram (media-hub, distinctiveness 4) as a shipped
success. Periodically record the owner's best shipped marks as **reference
exemplars** so the gallery, the rubric bar, and the stats all measure against real
quality, not just against the last bug.
*Why:* a self-evolving system converges on whatever its evidence rewards; with no
positive exemplars it converges on "passes check," not "compelling."
*Evidence:* the 2026-07-16 gold cases (fado, bargain-hunter, snowy-repo-quest,
career-cat) were added retroactively to rebalance a casebook that was dominated by
creator-favicon and repair-driven cases. Folded into `EVOLUTION.md` §1 (RECORD
also means record exemplars) and `CONCEPTING.md`'s gallery.

## L24 — For routing objects, semantic topology must be continuous in the silhouette
When a mark promises that several inputs converge into one route, every claimed
input must visibly join the shared trunk in the blacked-out silhouette. A
floating connector can remain legible and mechanically clean at 16px while
still contradicting the product model. Draw the connectivity graph before
polishing color; then verify the same connections at 16/32px.
*Why:* topology is the meaning of a routing mark. A disconnected shape is a
semantic craft failure, not a cosmetic gap that color or outlines can repair.
*Evidence:* [casebook/2026-07-22-ai-agent-entrypoint-guide.md](../casebook/2026-07-22-ai-agent-entrypoint-guide.md) — a three-head
splitter passed automated QA but left the centre head floating until a
raster-aligned centre rail joined it to the trunk. Folded into
`DESIGN_PLAYBOOK.md` §2.

## L25 — A gradient shared across differently-sized shapes says "different", not "same"
A single `linearGradient` in `userSpaceOnUse` spanning two shapes is a tempting
way to draw "these are held at one level": the band lands at the same absolute
height on both. Rendered, the taller shape reaches into a different part of the
ramp and comes out a visibly different tone — so the device draws exactly the
opposite of its intended meaning, and at 16px the shape that reaches the dark
end reads as *unlit*. Express sameness by making the shapes **look identical**
(one gradient definition applied per-shape in object-bounding-box space), not by
running one ramp through them.
*Why:* the eye compares the two fills directly; it does not reconstruct the
canvas-space geometry that made them differ.
*Evidence:* [casebook/2026-08-04-lumendeck.md](../casebook/2026-08-04-lumendeck.md) — the shared-ramp pair was
killed at bake-off in favour of identical per-shape ramps.

## L26 — If a mark needs three elements, budget every semantic gap at 128 units first
Three elements can be affordable at 16px, but only if each gap between them is
about **128 units on the 1024 grid** (two clear rendered pixels). Decide that
before committing to the third element: a first pass with a 72-unit gap fused
its shapes into one blob at 16px and read as "blurry". If two gaps cannot both
afford 128 units inside the safe area, it is a two-element concept — shrink the
idea rather than the gaps.
*Why:* below two pixels a gap is anti-aliasing, and anti-aliasing is what the
eye reads as low quality.
*Evidence:* [casebook/2026-08-04-lumendeck.md](../casebook/2026-08-04-lumendeck.md) — widening both gaps to exactly
128 units is what made a three-element mark legible at 16px. Extends
`DESIGN_PLAYBOOK.md` §5's rule for negative-space devices to inter-element gaps.

## L27 — A row of same-width blocks of rising height is a bar chart, whatever you meant
Any stepped row of equal-width rectangles collides with analytics, signal
strength and equaliser icons — the silhouette borrows that meaning and no
styling recovers it (this is L9 applied to the most common abstract layout).
When rectangles must read as *screens*, use **orientation contrast**: a
landscape rectangle beside a portrait one is unmistakably monitors and matches
no system icon.
*Evidence:* [casebook/2026-08-04-lumendeck.md](../casebook/2026-08-04-lumendeck.md) — the stepped three-panel
concept was killed on the silhouette strip; the landscape+portrait pair shipped.

## L28 — Spend the whole tile: full-bleed the mark before you tune anything else
A mark drawn *inside* a tile pays for the margin twice — once in the container
and once in every counter, gap and cut it can no longer afford. When a concept
reads at 128px and mushes at 16px, the first move is not thicker strokes or
fewer elements: it is deleting the background tile and letting the object BE
the icon. Going full-bleed typically returns 250–300 units of grid, which is
exactly the budget L20/L26 ask for.
*Why:* legibility is the casebook's chronically weakest first-pass axis, and its
most common single cause is a mark sized to look comfortable on a 1024 canvas
instead of sized to spend it.
*Evidence:* [casebook/2026-08-05-yorozora-seal.md](../casebook/2026-08-05-yorozora-seal.md) — a 744-unit tile left
~28 units between strokes (0.4px at 16px); full-bleed bought ~280 units and paid
for heavier strokes *and* 64+ unit counters.
[casebook/2026-08-08-snowy-site-caret-keycap.md](../casebook/2026-08-08-snowy-site-caret-keycap.md) — an
independent confirmation: all three first-round concepts were marks inside
tiles and all three mushed at 16px; the same three ideas full-bleed were
immediately legible. Folded into `DESIGN_PLAYBOOK.md` §2.

## L29 — A full-bleed container still needs one non-square feature, or its footprint is just a rounded square
Full-bleed solves the pixel budget (L28) but re-opens L8: if the object's outline
runs parallel to the canvas, the alpha footprint is a rounded square and the
silhouette gates cannot see the object at all. Give the container **one
measurable departure from the square** — a perspective taper, an asymmetric
corner, a protruding tail. A taper needs to be big to read: a base roughly
**1.5× the top edge** (904 vs 604 units) is visible at 32px; 760 vs 700 is not.
*Why:* "full-bleed" and "distinctive" are different problems, and passing the
first makes it easy to believe you passed the second.
*Evidence:* [casebook/2026-08-08-snowy-site-caret-keycap.md](../casebook/2026-08-08-snowy-site-caret-keycap.md) —
the near-square full-bleed cap scored distinctiveness 3 because its footprint
read as a generic up-chevron button (L9); widening the base to 904 against a
604 top face named a keycap and lifted it to 4 with no change to the glyph.

## L30 — Punch the glyph through the object; do not lay it on top
When an opaque object carries a glyph, cutting the glyph clean through it
(`fill-rule="evenodd"`) rather than painting it on the surface costs nothing at
16px and buys the whole silhouette axis: an overlaid glyph is invisible once the
mark is blacked out, while a cut one is part of the shape the bake-off actually
judges (L3). It also keeps the mark to one dominant foreground shape (L1), and
the cut adapts to whatever the page behind it is.
*Why:* the overlaid and cut versions look identical in colour, so the choice
feels cosmetic — but only one of them survives the test that decides the
concept.
*Evidence:* [casebook/2026-08-08-snowy-site-caret-keycap.md](../casebook/2026-08-08-snowy-site-caret-keycap.md) —
the two versions were indistinguishable at 16px; the cut version put the caret
into both silhouette rows and won the bake-off on that alone.

## L31 — A 16px icon has room for exactly one idea
When a brand's full meaning has two parts, draw the one that names the business
and let the wordmark, the name story, or the page copy carry the other. A second
meaning bolted onto a working mark reliably costs the first one: it either
detaches, unbalances the primary glyph, or only reads at a size where the icon
was never in trouble.
*Why:* every additional idea competes for the same ~16 pixels the first idea
already needed.
*Evidence:* [casebook/2026-08-05-yorozora-seal.md](../casebook/2026-08-05-yorozora-seal.md) — three variants
adding "open sky" to a working 万 seal each broke it (a lidded box at 16px, a
detached floating 一, a chamfer that only read by shortening the 一); the
single-idea champion shipped unchanged.

## L32 — A bordered card cannot pass a maskable safe-zone audit; leave the frame to the interface
A square frame's corner sits at **1.41× its half-width**, so fitting it inside a
40% safe circle forces the frame down to ~57% of the tile — by which point it no
longer reads as a card. Neo-brutalist ink borders and offset shadows belong to
the UI, not the icon: ship the palette and the glyph in the mark. This is the
maskable-geometry counterpart to L12 (outer effects are real footprint).
*Why:* adaptive icons crop by geometry, and the corner of a frame is the
farthest-out part of the drawing.
*Evidence:* [casebook/2026-08-06-yorozora-node-graph.md](../casebook/2026-08-06-yorozora-node-graph.md).
[casebook/2026-08-08-snowy-site-caret-keycap.md](../casebook/2026-08-08-snowy-site-caret-keycap.md) applied it
preventively — the site it serves is neo-brutalist ink-on-paper, and the favicon
carries the palette while the ink frame and offset shadow stay in the CSS.

## L33 — A vertical cut above a detached round accent reads as punctuation
A near-vertical negative-space cut and a detached circular accent can each be
valid devices, yet their alignment groups them into an exclamation mark at
16px. Strip color, inspect the 16px silhouette, and compare their centerlines
before polishing. Offset the cut by at least two output pixels (about 128 units
on the 1024 grid), change its angle, or remove one device.
*Why:* Gestalt grouping wins before object recognition at favicon size; a
familiar punctuation mark is a stronger reading than the intended object.
*Evidence:* [casebook/2026-08-09-private-media-route-fan.md](../casebook/2026-08-09-private-media-route-fan.md).
Folded into `DESIGN_PLAYBOOK.md` §5 and `CONCEPTING.md` §4.

## L34 — Viewpoint is part of the concept, not a finishing choice
Run the name-the-thing test at both 128px and 16px. If an object metaphor names
a stronger unrelated noun from the chosen angle, reframe or rotate the object
before adding detail. A viewpoint change can create the broad masses and open
counters small sizes need; extra seams and highlights usually reinforce the
wrong reading.
*Why:* an object's silhouette is determined as much by viewpoint as by contour,
and icon scale removes the detail that might have disambiguated a weak angle.
*Evidence:* [casebook/2026-08-09-private-media-discovery-pearl.md](../casebook/2026-08-09-private-media-discovery-pearl.md).
Folded into `DESIGN_PLAYBOOK.md` §5 and `CONCEPTING.md` §4.

## L35 — A blocked Review Lab changes the evidence path, not the quality gate
If a managed browser refuses a local Review Lab, do not bypass the policy and
do not treat the missing interactive view as approval. Inspect the static sheet
plus every exact target asset at actual 16/32px sizes, record all six scores and
notes in the source-bound approved fallback, and let `ship` re-run QA and verify
the digest. Report the interactive check as blocked.
*Why:* the fallback remains auditable only when it is bound to the reviewed SVG
and preserves the same ≥4/5 rubric floor; otherwise a browser limitation becomes
an undocumented gate bypass.
*Evidence:* [casebook/2026-08-09-private-media-discovery-pearl.md](../casebook/2026-08-09-private-media-discovery-pearl.md).
Folded into `WORKFLOW.md`, `REVIEW_CHECKLIST.md`, and the iconflow skill.
