<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The Neighbourhood — distinguishability against a named set

Which known marks is this one the same shape as at 16px? Asked of a named set, that question has an answer.

Distinctiveness is a ship gate: nothing leaves below 4/5 on it. It is also
one of the two worst first-pass axes across the whole casebook, and it is
judged entirely by a human eye — because `iconflow/qa.py` reasoned, correctly,
that distinctiveness *in the abstract* is not mechanically separable from a
good mark. A path-drawn "H" and an ownable route node are raster-identical.

So the tool flagged a live `<text>` monogram and went silent, and the casebook
filled up with what a person squinting at a bake sheet let through: a
two-panel curtain that *was* the pi symbol; a lantern that read as a stack of
pancakes; an interlace that landed on a hashtag; a row of rising blocks that
was a bar chart whatever the designer meant. L9 already tells a human to kill
silhouette collisions with system icons and typographic glyphs at bake-off.
Nothing helped them do it.

## The reframe

"Is this mark distinctive?" is ill-posed. "Is this mark distinguishable at 16px
from *these specific other marks*?" is well-posed, deterministic, and checkable
— and it is exactly the question L9 asks a human to answer by eye. IconFlow can
answer it because it owns a set: the marks it has published, and the generic
forms every operating system already owns.

Two things this is **not**, said in the same breath as the feature:

- **It is not a trademark or clearance check and never implies one.** Shape
  distance at 16px is not a legal opinion. `TRADEMARKS.md` and the archive
  already disclaim clearance; a tool that let someone believe otherwise would
  be worse than no tool.
- **It does not measure distinctiveness.** It measures *shape collision at 16px
  against a named set*. The human ≥4/5 gate stays exactly where it is, and a
  clean neighbourhood is not a score.

Nor does it rank "good" icons. Ranking taste is how a design tool becomes a
slot machine.

---

## The instrument: `iconflow/shapefield.py`

A deterministic 16px shape descriptor and a distance, with no opinion about
which answer is good. Two later milestones will use the same instrument
inverted — a family must be coherent *and* mutually distinguishable; a frame
must survive a platform crop — so it carries no collision semantics.

**Sampling.** The source's `glyph` rung (what actually ships at 16px) is
rendered at 64px and split into figure and ground; the binary figure mask is
then area-averaged onto a **16×16 grid of occupancy fractions**. Every cell is
a 4×4 block of the mask, so it holds one of seventeen values, 0/16 through
16/16. The grid is simultaneously "what 16px shows" and robust to a single
anti-aliased pixel landing differently on another renderer — which matters,
because the corpus index is checked in and a user's machine has to reproduce
comparisons against it.

**Figure.** The ladder's Otsu split, made stricter in three ways, because the
ladder compares rungs of *one* source (polarity only has to be consistent)
and the field compares *different* sources (polarity has to be right):

1. a transparent pixel is never figure — the rounded corners of a card are
   ground whatever grey they composite to;
2. the luminance split is taken over the footprint alone, and one side is the
   figure only if the footprint *encloses* it: at least 10% of the solid
   pixels, touching at most 5% of the outer boundary (20% on a card or badge
   covering three quarters of the canvas, whose mark may lean on the rim);
3. otherwise the footprint itself is the figure.

So a full-bleed card is fingerprinted by the mark punched into it, a keylined
cloth by the cloth inside the keyline, and a plain ink object, a two-tone flag
whose colours both reach the edge, or a card with nothing enclosed by its
outline — which is what a viewer sees at 16px.

**Descriptor** = the grid plus four scalars, each explainable in one sentence:
how many separate pieces the figure is in, how many holes are cut through it,
what share of the canvas it covers, and its bounding-box width over height.
Pieces and holes are counted on the 64px mask. A region smaller than one
grid cell (sixteen pixels) is not a piece: at 16px it is at most a smear. A
hole narrower than five pixels is not a hole: L15 says a cut must own two
pixels at 16px, and a hairline slit is exactly what one renderer's
anti-aliasing closes and another's leaves open.

**Distance** = normalised L1 over the grid — the share of all ink the two
grids do not share; 0 is identical, 1 is disjoint — with topology reported
*beside* it rather than folded into it: two fields are "the same topology"
when they have the same number of pieces (1, 2, 3+) and holes (0, 1, 2+). A
ring and a disc can be grid-close and still be two objects; that is a fact to
show, not a number to weight. Neither position nor scale is normalised: every
IconFlow master is drawn on the same 1024 grid inside the same safe area, so
two fields are already comparable, and a mark that shifts or shrinks at 16px
*is* a different mark at 16px.

## Calibrated on ground truth, not taste

The casebook records real collisions in prose. They were reconstructed as
fixtures (`tests/fixtures/neighbourhood/`), and the radius was placed by
measuring them — not chosen and justified afterwards.

| Casebook | Rejected draft → generic form | Distance | Topology | Inside 0.12? |
|---|---|---|---:|---|
| cineloom | 2×2 woven frame → hashtag | 0.065 | same | **yes** |
| lumendeck | three rising panels → bar chart | 0.071 | same | **yes** |
| media-hub | bold H on a tile → letter H | 0.104 | same | **yes** |
| yonago | stepped stack → bar chart | 0.170 | different | no |
| night-market | ribbed lantern → bell | 0.271 | different | no |
| night-market | two curtain panels → pi | 0.311 | same | no |

| Casebook | Shipped redesign → the form it escaped | Distance | Topology |
|---|---|---:|---|
| cineloom | punched pattern card → hashtag / filmstrip | 0.443 / 0.396 | different / same |
| lumendeck | landscape + portrait panel on a rail → bar chart | 0.319 | same |
| night-market | forked single curtain → pi | 0.319 | different |

Inside the collision set itself, the closest pair of *distinct* generic forms
is monitor / speech bubble at 0.080, then rounded square / disc at 0.088 and
heart / shield at 0.096 — and at 16px those *are* real ambiguities, which is
the instrument telling the truth rather than a flaw in it.

So the **collision radius is 0.12**: above the three recorded collisions and
the genuine 16px ambiguities, and below every shipped redesign — the nearest
of those sits at 0.319. The nearest recorded *miss*, the rejected stepped
stack, sits at 0.170 with a different topology. Two marks at or below 0.12
with the same topology are one shape at 16px; a pair with different topology
is never a collision, whatever its distance.

### What the radius misses, and why it is not raised

Three of the six recorded collisions sit outside it, and the table says so.

- **The curtain that was pi.** A person reads *bar over two legs* across any
  stroke weight; the grid measures ink, and two 300-unit cloth panels are
  five times the mass of pi's 120-unit legs. Re-drawn with the panels placed
  exactly on pi's legs, the pair reaches 0.149 only when the panels are as thin
  as the glyph's strokes. This is a structural resemblance the occupancy grid
  does not see, and it is the strongest argument that the human name-the-thing
  test stays.
- **The lantern that was a bell.** The ribs cut the oval into four pieces, so
  the topology differs, and the bell's flared lip is not in the oval at all.
  The reading a person had was "pancakes, and the outline is a bell"; the
  grid only ever had the pancakes.
- **The stepped stack.** A solid staircase against three separate bars: 0.170
  with a different topology. Close, and correctly not called the same shape.

Raising the radius cannot catch all three. The stepped stack and the lantern
differ in topology, which the gate treats as a separator whatever the
distance. The curtain matches pi's topology, so a radius of 0.32 *would*
catch it — and would call the lumendeck redesign (0.319 from the bar chart,
same topology) a collision in the same breath; the other redesigns stay
clear on distance or topology. A radius that cannot tell a rejected draft
from the mark that replaced it is not a radius. The misses are recorded here
instead. If the instrument ever gains a structural component, this table is
the test it has to pass.

---

## The corpus: `iconflow/neighbours.py` and the index

**Two halves.** IconFlow's own published marks were one half; the other was
missing. It is now drawn: `iconflow/resources/collision/` holds deliberately
plain paths for the ubiquitous forms — gear, magnifier, house, folder, heart,
bell, bar chart, filmstrip, price tag, `+ ✓ ← # π`, a few letterforms, and the
readings the casebook actually met (crown, arch, table, chain link, eye,
rounded square, disc, sunburst, monitor, calendar). They are generic renditions
of generic forms, nobody's icon set, and CC0. Drawing them rather than typing
glyphs also removes the font problem `qa.py` already names: a path renders the
same on every machine.

**The index** (`iconflow/resources/collision/index.json`) is built by
`scripts/build_collision_index.py`, checked in, and content-addressed: every
entry carries the SHA-256 of the source it was fingerprinted from, and the
house half holds *fields only* — a 16×16 grid and four scalars per mark, never
the artwork. It is drift-tested exactly the way the icon-size reference page
is: the browser-free matrix fails when any source no longer hashes to what the
index recorded or the committed bytes differ from what the generator would
write; the Chromium job rebuilds every field and fails when a cell moves by
more than two anti-aliased pixels or a field drifts more than 0.03 in
aggregate (a quarter of the radius). Topology classes are compared too, but
counted rather than failed one by one: a counter one cell wide is open on one
platform's anti-aliasing and shut on another's, so a handful of flips is the
instrument, and only more than 1% of entries flipping says the index is from
a different instrument. The first Linux run of that job found exactly this —
one hole in 748 entries, and one source that rendered through fonts — which
is why holes narrower than five pixels are no longer holes and sources with
live `<text>` are not indexed. The index in this repository was built on
Windows; the Linux job is where the tolerance is tested. A generated table
nobody can date is the thing this project exists not to ship.

**Pluggable, and the user's sets outrank IconFlow's.** `iconflow.toml` gains:

```toml
[neighbours]
avoid = ["../brand/other-app/master.svg", "competitors/*.svg", "@collision"]
family = ["../suite/*/master.svg"]
portfolio = ["../shipped/**/master.svg"]
```

Paths and globs resolve from the file; a glob that matches nothing is an
error, because an `avoid` that silently resolved to nothing would be a gate
that quietly stopped gating. `@collision` and `@house` name the bundled sets
in full; `@collision/bell` names one form. A declared `master.svg` is named by
its directory. Only the candidate and the declared *files* are rendered — the
corpus is pre-indexed — so the audit costs a handful of renders, the way the
ladder's invariant costs three, and they are rendered in the project's
`color_scheme`, the same one the build ships.

## The gate, and how it is split

| Code | Against | Gates? | Fires when |
|---|---|---|---|
| `neighbour-collision` | the project's `avoid` set | **yes** | a declared mark is at or below the radius with the same topology. The message names the mark. |
| `neighbour-familiar` | the bundled collision set and house corpus | no | the same, against the bundled halves. A generic-form hit quotes L9; a house hit says the house corpus is a mirror, not a wall. |
| `neighbour-house-rut` | the project's `portfolio` set | no | three or more of the owner's previous marks sit within the radius — the "house cliché" signal `case stats` estimates from device families, measured on pixels. |

`family` is excluded from every finding: a mark that is *supposed* to be
close is never a collision and never a rut. A bundled entry that a project
promotes into `avoid` is gated there and not also advised. The candidate's own
source, if it happens to be in a set, is never its own neighbour.

**The bundled corpus never blocks a build.** If a match against IconFlow's own
house marks could gate, every user would be gated by IconFlow's house style.
A generic-form hit is the exception a project chooses: one line,
`avoid = ["@collision"]`, makes L9 a gate rather than advice. A fresh
`iconflow init` writes an empty `[neighbours]` table, which is the opt-in for
the advisories; a project with no table at all renders nothing extra and sees
no new finding, byte for byte.

`check --config iconflow.toml`, `review --config`, and `ship` all run the audit
when the table is present, and a collision blocks `ship` through the same
`qa-warnings` door as every other check warning.

## Show, do not score

A distance of 0.11 is useless alone; the value is the picture.

```bash
python -m iconflow neighbours master.svg --config iconflow.toml \
  --sheet work/<slug>/neighbours.png
```

One row per mark — the candidate first, then its nearest neighbours in order,
then the declared family — and three columns: the real 16px render with its
pixels shown, the 32px render the same way, and the 16×16 occupancy field the
distance was actually summed over. Every neighbour carries its distance and topology; a
row inside the radius is outlined in coral. A bundled mark is rendered live
when its source is in the checkout and still hashes to what the index
recorded; from a wheel install its stored field stands in, labelled *from the
index* — which is honest, because the field *is* what 16px shows.

`review --config` writes the same sheet as `<sheet>-neighbours.png` beside its
contact sheet whenever the project declares the table, so the mandatory review
step cannot miss it. It is not a new `review` output key: that envelope is
frozen at `schema: 1`. `neighbours --json` carries the structure instead
(`docs/AGENT_CONTRACT.md`), with the same exit-code contract as every gated
command: 0 clean, 1 a collision against `avoid`, 2 a usage or runtime failure.

## Working with it

1. Run `neighbours` on every bake-off finalist, not just the winner, and read
   the sheet beside `bake.png`. A finalist inside the radius of a generic form
   is L9's kill, made visible.
2. Declare what the product must not resemble in `avoid`: its own other icons,
   the marks beside it in an app grid, a competitor's mark. That is the only
   set that gates, because it is the only set whose meaning the project owns.
3. Treat a `neighbour-familiar` hit as a question, not a verdict. Look at the
   two side by side. If the candidate is the same shape as a bell, the answer
   is a redesign — never a wider radius. The worked example in
   `examples/neighbourhood/` records exactly that decision.
4. Keep the human gate. A clean neighbourhood says the mark is not one of
   these; only a person can say it is *something*.

---

Related: [`LEARNINGS.md`](LEARNINGS.md) L9, L21, L22 and L27 for the readings
this measures; [`DETAIL_LADDER.md`](DETAIL_LADDER.md) for the figure/ground
split it inherits; [`AGENT_CONTRACT.md`](AGENT_CONTRACT.md) for the
`neighbours` envelope and codes; [`REVIEW_CHECKLIST.md`](REVIEW_CHECKLIST.md)
axis 2, which still decides whether it ships.
