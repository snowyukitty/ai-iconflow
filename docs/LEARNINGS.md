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
*Evidence:* [casebook/2026-06-19-tgs-planning-site.md](../casebook/2026-06-19-tgs-planning-site.md) — folded-map route beat
gamepad/ticket concepts. Folded into `CONCEPTING.md` worked example.

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

## L7 — A stale Windows icon is usually the cache, not the build
After rebuilding an exe/shortcut icon, Explorer often shows the old one.
Verify the file first (extract the embedded icon, or copy the exe to a fresh
name); only then clear `iconcache_*.db` / rerun `ie4uinit -ClearIconCache` or
recreate the shortcut.
*Evidence:* desktop-app deliveries. Folded into the iconflow skill's
delivery notes.

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
