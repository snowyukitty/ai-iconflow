<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The Family tier — coherent, and still every member its own mark

A family of marks — a suite of app icons, a toolbar, a set of emotes — has to
pass two tests that pull in opposite directions. It must read as **one
family**, and no two members may be **the same mark** at 16px.

[`NEIGHBOURHOOD.md`](NEIGHBOURHOOD.md) built the instrument for the second
half of that sentence when it is asked about strangers: `shapefield`, a 16px
occupancy field and a distance between two of them. The Family tier asks the
same instrument about siblings, and it does not change the instrument. It
changes what is compared.

## Why the raw distance is the wrong number for siblings

Siblings share a **carrier**: the plate behind a suite of app icons, the head
behind a set of faces. The carrier is most of the ink, so it dominates the
normalised distance. Two emote faces on the same squircle head are 0.02 apart
however different their expressions — the raw number says *same shape*, and
for the head it is right. What tells siblings apart is the part they do not
share.

## The method

`iconflow/family.py`, on fields computed by `shapefield` exactly as
`neighbours` computes them:

1. **Coherence.** Two members whose raw fields are within **0.20** share a
   carrier. Linked members form carrier groups (connected components), found
   from the fields alone; nobody declares them. 0.20 is the neighbourhood's
   own "close" band — the distance at which a person may read two marks as
   the same silhouette. A member linked to no one stands alone; that is
   reported, not penalised (a thumbs-up in a set of faces belongs by its
   grammar, not its silhouette).
2. **The carrier.** A group of three or more has a carrier: the cell-wise
   median of its members' fields — the shape most of them share, robust to
   the one member whose party hat breaks the outline.
3. **Distinguishability.** Siblings are compared on their residual from the
   carrier, with the same normalised L1 the neighbourhood uses:

   ```
   residual(a, b) = |a − b| / (|a − carrier| + |b − carrier|)
   ```

   It is 0 when two members differ from the carrier in exactly the same way,
   and 1 when what sets each apart from the carrier is entirely its own.
4. **The gate.** Below **1/3**, two members share more than two thirds of
   what sets them apart from their carrier: one expression drawn twice.
   `iconflow family` reports them as `family-twins` and exits 1.

A group of only two has no carrier to speak of — its median is the midpoint,
and every residual is exactly 1 — so a pair falls back to the
neighbourhood's own rule: one shape when within the collision radius (0.12)
with the same topology.

## What is calibrated, and what is not

The collision radius was placed by measuring recorded casebook collisions.
**The twin floor was not**: no family has been recorded in the casebook yet.
1/3 is the line the sentence in step 4 explains, checked against one
reviewed set — the [IconFlow emotes](EMOTES.md) — where the first draft's
smile and wink, which differ by one closed eye, sat at 0.31 and every other
pair at 0.50 or more. A person reading the 22 px sheet agreed with the
number. When the same set grew to 55, the floor caught a second pair at 0.332
— an eye roll and a flushed face that differed mainly by pink cheeks, which
is to say by colour — and the sheet agreed again; the nearest distinct pair
then sat at 0.39. That is one family seen twice, not two families, so the
floor is still **provisional**: when a family is
recorded whose twins sit above it, or whose distinct members sit below it,
this section is where the evidence goes and the floor moves.

Coherence is measured, not judged. Being in one carrier group says the
members share a shape; whether they read as one family — weight, palette,
attitude — is still the human review.

## Using it

```sh
iconflow family "emotes/*.svg" --sheet family.png
iconflow family suite/*/master.svg --json
```

Members are paths or quoted globs. The sheet shows the closest pairs —
twins first, outlined in coral — each member at 22 px with its pixels shown,
both at true 28 px, and the 16×16 cells where the two differ. The number is
not the proof; the sheet is.
