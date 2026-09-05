<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->
# `neighbourhood/` — the collision the tool caught first

Two sources, one brief, one gate. Both are drawn after the record in
[`casebook/2026-08-04-lumendeck.md`](../../casebook/2026-08-04-lumendeck.md):
a display-brightness tool whose user job is *set one level across different
screens*. They are reconstructions of that case's first draft and shipped
mark, not the shipped files, and this directory exists to demonstrate one
mechanism — there is no receipt, no bake-off, and no case record here.

```bash
python -m iconflow neighbours examples/neighbourhood/first-draft.svg \
  --config examples/neighbourhood/iconflow.toml \
  --sheet work/neighbourhood/first-draft.png       # exit 1

python -m iconflow neighbours examples/neighbourhood/master.svg \
  --config examples/neighbourhood/iconflow.toml \
  --sheet work/neighbourhood/master.png            # exit 0
```

`iconflow.toml` declares `avoid = ["@collision"]`: this project chose to make
L9 a gate. Without that line the same hit is advice.

## What the first draft measured

`first-draft.svg` is three screens, each a little taller and brighter than the
last. Read as source it is a reasonable idea. At 16px it is a **bar chart**,
and the neighbourhood says so with a number and a name:

```
first-draft.svg at 16px: 3 piece(s), 0 hole(s), 31% of the canvas; radius 0.12
  ! 0.071  collision/bar-chart   Bar chart  (same topology)
    0.211  collision/crown       Crown      (different topology)
```

The proof sheet puts the two side by side at real 16px, and the figure
silhouettes are the same three bars. The casebook's own words for the same
moment were "in the silhouette strip it was indistinguishable from analytics
or signal strength — L9 in practice. Killed rather than iterated."

## Why the fix was a redesign, not a threshold

The tempting fix is `--radius 0.06`: the collision disappears and nothing else
changes. It is the wrong fix for the reason the collision exists. A row of
same-width blocks of rising height *is* a bar chart (L27); no styling survives
16px to say otherwise, so a narrower radius would only stop the tool from
saying what a viewer will still see.

`master.svg` keeps both ideas — screens, matched — and carries them
differently: a wide panel beside a tall one, bottoms aligned, standing on one
rail. The orientation contrast is what names the object as monitors rather than
as a chart; the rail is what turns two floating rectangles into one thing with
an ownable silhouette. The neighbourhood measures the redesign at **0.319**
from the bar chart — outside the radius by a factor of two and a half — and its
nearest neighbour of any kind is now a filmstrip at 0.220 with a different
topology. Nothing about the radius moved.

## Reading the sheet

- **Candidate row** — the mark under audit: pieces, holes, coverage.
- **Neighbour rows** — nearest first. Coral outline means inside the radius.
  `avoid` rows gate; `collision` and `house` rows advise; `family` rows are
  drawn so you can see the family, and never gate.
- **Three columns** — real 16px with pixels shown, real 32px the same way, and
  the 16×16 occupancy field the distance was summed over. If the fields look
  alike, the distance is telling you something you can see.

Full reference: `python -m iconflow docs NEIGHBOURHOOD`.
