<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->
# `detail-ladder/` — one source, three size regimes

`master.svg` is a kiln: a domed body, an offset chimney, one broad stoke mouth.
It exists to be *read as source*, so open it before running anything. Every
group says which rungs it belongs to, and the comments say why.

```bash
python -m iconflow ladder examples/detail-ladder/master.svg \
  --sheet work/detail-ladder/ladder.png
python -m iconflow check examples/detail-ladder/master.svg
```

## What each rung carries

| Rung | Elements | Why there |
|---|---|---|
| `glyph` (≤48px) | dome, chimney, plinth, stoke mouth | the whole outer contour, plus the one counter that survives 16px |
| `mark` (49–256px) | the ember in the mouth | at 49px there is room to say the kiln is *lit*; at 16px there is not |
| `plate` (≥257px) | brick coursing, joints, rim light, ember core, spark | material — none of it touches the contour |

Run the audit and the three rungs measure 38.0% / 42.4% / 43.3% visible ink:
detail genuinely appears as the size grows, and the outer footprint is
identical (100%) across every step. That is the shape of a healthy ladder.

## The mistake this example made first

The `mark` rung originally carried a **chimney collar** — a band of dark clay
laid across the chimney. It looked like a joint, and it was: from 49px up it
cut the chimney off the dome, so the outer contour said one thing at 16px and
another at 64px. A rung above `glyph` is only allowed to work *inside* the
contour, and this one was redrawing it.

Nothing subjective caught it. The same-mark overlay on the proof sheet painted
the collar coral — the colour reserved for geometry the smaller rung has that
the larger one does not — and `glyph → mark` visible-shape agreement sat at 88%
instead of the 89% it reaches without it. The collar was removed rather than
tuned, because the rule it broke is not a threshold:

> **The ladder grows inward.** Every trait that defines the outer contour
> belongs on the `glyph` rung. The rungs above it own what happens inside it.

## Reading the proof sheet

Three bands, three different questions:

1. **delivered** — every size rendered from its own rung. If nothing changes
   left to right, the ladder is annotated but idle.
2. **the three rungs at 256px** — the drawings compared with resolution removed.
3. **same-mark overlay** — grey is the larger rung, black is what survives to
   the smaller one, coral is a broken ladder.

## What it deliberately is not

Not a bake-off winner and not a shipped identity: there is no `iconflow.toml`,
no receipt, and no case record here, because this directory exists to
demonstrate one mechanism rather than to prove the gated loop. For that, read
`../iconflow-balloon/` and `../iconflow-parachute/`, which go end to end.

Full reference: `python -m iconflow docs DETAIL_LADDER`.
