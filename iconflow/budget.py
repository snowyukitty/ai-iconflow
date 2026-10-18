# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The 16px pixel budget, measured before the bake-off.

Legibility is the casebook's weakest first-pass axis, and its most repeated
lessons are budget rules a designer applies by eye and then discovers in
review: a signature cut needs two output pixels (L15), every idea-carrying
accent and separating gap needs about 128 units on the 1024 grid (L16, L20,
L26), a mark drawn inside a tile cannot afford either (L28), and 16px has
room for one idea (L31). This module measures those things on a candidate so
the designer is told *before* review:

* every enclosed **cut** narrower than two output pixels (L15);
* every **gap separating two parts** narrower than one output pixel, which
  fuses at 16px (L26 asks for two; under one is where it stops being a gap);
* every **detached accent** narrower than two output pixels (L16);
* **survival**: how many cuts are open at 256px and how many still own two
  clear pixels at 16px, how many parts there are at 256px and how many are
  still separate at 16px;
* how much of its **tile** a mark drawn on a card spans (L28), and how many
  separate parts compete at 16px (L31).

It also records **mush** — the share of the 16px footprint that is a blend of
colours — but never reports it: antialiasing makes it high on good marks too.

Every finding is advisory and states a measurement, not a verdict. The budget
never gates and never replaces the human score. Thresholds are grid units on
a 1024 viewBox (64 units is one output pixel at 16px); the calibration they
were checked against is in ``docs/LEGIBILITY_BUDGET.md``.
"""
from __future__ import annotations

import io
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import ladder
from .findings import Finding

#: Analysis render: 1024 grid units / 256 px = 4 units per pixel.
ANALYSIS_SIZE = 256
UNITS_PER_PX = 1024 / ANALYSIS_SIZE
#: One output pixel at 16px, in grid units.
OUTPUT_PX_UNITS = 64
#: The L15/L16/L20/L26 budget: two output pixels.
BUDGET_UNITS = 2 * OUTPUT_PX_UNITS
#: Below one output pixel a separating gap is not a gap at all: it fuses.
FUSE_UNITS = OUTPUT_PX_UNITS
#: A region must cover this much (output pixels squared) to count as a
#: feature; smaller slivers are antialiasing.
MIN_FEATURE_OUTPUT_PX2 = 1.5
#: A separate part counts from half an output pixel: a speck that small is
#: exactly the accent L16 warns about, not antialiasing.
MIN_PART_OUTPUT_PX2 = 0.5
#: Colours closer than this (RGB distance) are one class.
COLOUR_MERGE = 48
MAX_CLASSES = 6
#: A part this small (share of canvas) narrower than the budget is an accent.
ACCENT_MAX_SHARE = 0.06
#: More separate parts than this at 16px compete for one idea (L31).
MAX_PARTS_16 = 3
#: A mark on a card spanning less than this share of the card has margin it
#: could spend on its budget (L28).
TILE_SHARE_FLOOR = 0.75
#: Opaque share of the canvas above which the ground is a card.
CARD_SHARE = 0.75


@dataclass
class Feature:
    kind: str            # "cut" (enclosed), "gap" (between parts) or "accent"
    width_units: int
    area_output_px2: float
    centre: tuple[float, float]   # 0..1 canvas coordinates

    @property
    def width_px16(self) -> float:
        return self.width_units / OUTPUT_PX_UNITS

    def as_dict(self) -> dict:
        return {
            "kind": self.kind, "width_units": self.width_units,
            "width_px16": round(self.width_px16, 2),
            "area_px16": round(self.area_output_px2, 2),
            "centre": [round(self.centre[0], 3), round(self.centre[1], 3)],
        }


@dataclass
class Budget:
    """What one candidate spends of its 16px budget."""

    source: str
    ground: str                      # "transparent" or the card colour hex
    features: list[Feature] = field(default_factory=list)
    cuts_256: int = 0
    cuts_16: int = 0
    parts_256: int = 0
    parts_16: int = 0
    mush_16: float = 0.0
    tile_share: float | None = None

    def findings(self) -> list[Finding]:
        found: list[Finding] = []
        for feature in sorted(self.features, key=lambda f: f.width_units):
            where = _where(feature.centre)
            if feature.kind == "cut":
                found.append(Finding(
                    "budget-cut",
                    f"A cut {where} is {feature.width_units} units wide "
                    f"({feature.width_px16:.1f}px at 16px); a signature cut needs {BUDGET_UNITS} "
                    "units to stay two clear pixels (L15). Widen it, or carry the idea elsewhere.",
                ))
            elif feature.kind == "gap":
                found.append(Finding(
                    "budget-gap",
                    f"The gap separating two parts {where} is {feature.width_units} units "
                    f"({feature.width_px16:.1f}px at 16px), under one output pixel: they fuse. "
                    f"Budget it at {BUDGET_UNITS} units (L26), or join the parts on purpose (L58).",
                ))
            else:
                found.append(Finding(
                    "budget-accent",
                    f"A detached accent {where} is {feature.width_units} units across "
                    f"({feature.width_px16:.1f}px at 16px); L16 asks for {BUDGET_UNITS} so it "
                    "stays two deliberate pixels. Enlarge it, or remove it if it is decoration.",
                ))
        if self.cuts_256 > self.cuts_16:
            found.append(Finding(
                "budget-closed-cut",
                f"{self.cuts_256} enclosed cut(s) at 256px, {self.cuts_16} still owning two clear "
                f"pixels at 16px: {self.cuts_256 - self.cuts_16} close. A signature cut must own "
                "two pixels at 16px (L15): enlarge it, or open it to the outer edge.",
            ))
        if self.parts_256 > 1 and self.parts_16 < self.parts_256:
            found.append(Finding(
                "budget-fused-parts",
                f"{self.parts_256} separate parts at 256px are {self.parts_16} at 16px. Budget "
                f"every separating gap at {BUDGET_UNITS} units (L26), or make them one "
                "silhouette on purpose (L58).",
            ))
        if self.parts_16 > MAX_PARTS_16:
            found.append(Finding(
                "budget-ideas",
                f"{self.parts_16} separate parts compete at 16px. A 16px icon has room for "
                "one idea (L31): carry the second meaning in negative space or the wordmark.",
            ))
        if self.tile_share is not None and self.tile_share < TILE_SHARE_FLOOR:
            spare = int(round((1 - self.tile_share) * 1024 / 2))
            found.append(Finding(
                "budget-tile",
                f"The mark spans {self.tile_share:.0%} of its card; about {spare} units per "
                "side are spent on the card. Full-bleed the mark first (L28) — that margin is "
                "the budget its cuts and gaps need.",
            ))
        return found

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "ground": self.ground,
            "budget_units": BUDGET_UNITS,
            "features": [feature.as_dict() for feature in self.features],
            "cuts": {"at_256": self.cuts_256, "open_at_16": self.cuts_16},
            "parts": {"at_256": self.parts_256, "separate_at_16": self.parts_16},
            "mush_16": round(self.mush_16, 4),
            "tile_share": None if self.tile_share is None else round(self.tile_share, 4),
            "findings": [{"code": f.code, "message": str(f)} for f in self.findings()],
        }

    def summary(self) -> str:
        line = (
            f"cuts {self.cuts_16}/{self.cuts_256} open · parts {self.parts_16}/{self.parts_256}"
        )
        narrowest = min((f.width_units for f in self.features if f.kind != "accent"), default=None)
        if narrowest is not None:
            line += f" · narrowest {narrowest}u"
        if self.tile_share is not None:
            line += f" · tile {self.tile_share:.0%}"
        return line


def _where(centre: tuple[float, float]) -> str:
    x, y = centre
    horizontal = "left" if x < 0.36 else "right" if x > 0.64 else "centre"
    vertical = "top" if y < 0.36 else "bottom" if y > 0.64 else "middle"
    if horizontal == "centre" and vertical == "middle":
        return "at the centre"
    if horizontal == "centre":
        return f"at the {vertical}"
    if vertical == "middle":
        return f"at the {horizontal}"
    return f"at the {vertical} {horizontal}"


# --------------------------------------------------------------------------
# Raster helpers (pure Python; 256x256 is small enough)
# --------------------------------------------------------------------------


def _pixels(image: Image.Image):
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def _distance(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _classes(image: Image.Image) -> tuple[list[int], list[tuple[int, int, int]], int]:
    """Assign every pixel to a colour class; class 0 is transparency.

    Returns (labels, palette, ground): ``palette[k-1]`` is class k's colour and
    ``ground`` is the class the mark is read against — transparency, or the
    card when one opaque class holds most of the canvas and spans nearly all
    of it.
    """
    rgba = _pixels(image)
    opaque = [(r, g, b) for r, g, b, a in rgba if a >= 128]
    palette: list[tuple[int, int, int]] = []
    if opaque:
        sample = Image.new("RGB", (len(opaque), 1))
        sample.putdata(opaque)
        quantised = sample.quantize(colors=MAX_CLASSES * 2, method=Image.Quantize.MEDIANCUT)
        raw = quantised.getpalette()[: MAX_CLASSES * 2 * 3]
        for _count, index in sorted(quantised.getcolors(), reverse=True):
            colour = tuple(raw[index * 3: index * 3 + 3])
            if all(_distance(colour, other) > COLOUR_MERGE for other in palette):
                palette.append(colour)
            if len(palette) == MAX_CLASSES:
                break
    labels = []
    for r, g, b, a in rgba:
        if a < 128 or not palette:
            labels.append(0)
            continue
        labels.append(1 + min(range(len(palette)), key=lambda k: _distance((r, g, b), palette[k])))
    width, height = image.size
    canvas = width * height
    ground = 0
    areas = {k: labels.count(k) for k in range(1, len(palette) + 1)}
    if areas and sum(areas.values()) / canvas >= CARD_SHARE:
        card = max(areas, key=areas.get)
        if areas[card] / canvas >= 0.45:
            xs = [i % width for i, value in enumerate(labels) if value == card]
            ys = [i // width for i, value in enumerate(labels) if value == card]
            if min(max(xs) - min(xs), max(ys) - min(ys)) + 1 >= 0.85 * width:
                ground = card
    return labels, palette, ground


def _chamfer(mask: list[bool], width: int, height: int, *, outside_member: bool) -> list[float]:
    """Distance (px) from each member pixel to the nearest non-member (3-4 chamfer)."""
    big = float(10 ** 9)
    edge = big if outside_member else 0.0
    dist = [big if m else 0.0 for m in mask]
    for y in range(height):
        row = y * width
        for x in range(width):
            i = row + x
            if not dist[i]:
                continue
            best = dist[i]
            best = min(best, (dist[i - 1] if x else edge) + 3)
            if y:
                up = i - width
                best = min(best, dist[up] + 3,
                           (dist[up - 1] if x else edge) + 4,
                           (dist[up + 1] if x < width - 1 else edge) + 4)
            else:
                best = min(best, edge + 3)
            dist[i] = best
    for y in range(height - 1, -1, -1):
        row = y * width
        for x in range(width - 1, -1, -1):
            i = row + x
            if not dist[i]:
                continue
            best = dist[i]
            best = min(best, (dist[i + 1] if x < width - 1 else edge) + 3)
            if y < height - 1:
                down = i + width
                best = min(best, dist[down] + 3,
                           (dist[down + 1] if x < width - 1 else edge) + 4,
                           (dist[down - 1] if x else edge) + 4)
            else:
                best = min(best, edge + 3)
            dist[i] = best
    return [value / 3 for value in dist]


def _components(mask: list[bool], width: int, height: int, *, eight: bool) -> list[list[int]]:
    seen = [False] * len(mask)
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
    if eight:
        steps += ((1, 1), (-1, -1), (1, -1), (-1, 1))
    regions = []
    for start, on in enumerate(mask):
        if not on or seen[start]:
            continue
        seen[start] = True
        queue = deque([start])
        region = []
        while queue:
            index = queue.popleft()
            region.append(index)
            x, y = index % width, index // width
            for dx, dy in steps:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    j = ny * width + nx
                    if mask[j] and not seen[j]:
                        seen[j] = True
                        queue.append(j)
        regions.append(region)
    return regions


def _touches_border(region: list[int], width: int, height: int) -> bool:
    return any(i % width in (0, width - 1) or i // width in (0, height - 1) for i in region)


def _thin_parts(mask: list[bool], width: int, height: int, radius_px: float, *,
                outside_member: bool) -> tuple[list[bool], list[float]]:
    """Pixels of ``mask`` that no disk of ``radius_px`` inside the mask covers.

    A morphological opening by a disk from two distance transforms: the core
    is every pixel at least ``radius_px`` inside, and the opened set is every
    pixel within ``radius_px`` of the core.
    """
    dist = _chamfer(mask, width, height, outside_member=outside_member)
    core = [d >= radius_px for d in dist]
    to_core = _chamfer([not c for c in core], width, height, outside_member=True)
    thin = [m and not (c or t <= radius_px) for m, c, t in zip(mask, core, to_core)]
    return thin, dist


def _centre(region: list[int], width: int, height: int) -> tuple[float, float]:
    return (
        sum(i % width for i in region) / len(region) / width,
        sum(i // width for i in region) / len(region) / height,
    )


def _units(radius_px: float) -> int:
    """A feature width in grid units from its inscribed radius, to 8 units."""
    return int(round(2 * radius_px * UNITS_PER_PX / 8) * 8)


# --------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------


def measure(png_256: bytes, png_16: bytes, *, source: str = "") -> Budget:
    """Measure one candidate from its 256px and 16px renders.

    Only statements that can be checked against the renders are made: a
    feature's width in grid units, how many cuts and parts exist at 256px and
    how many survive at 16px. Which of them matter is the designer's call.
    """
    big = Image.open(io.BytesIO(png_256)).convert("RGBA")
    small = Image.open(io.BytesIO(png_16)).convert("RGBA")
    if big.size != (ANALYSIS_SIZE, ANALYSIS_SIZE):
        raise ValueError(f"budget analysis needs a {ANALYSIS_SIZE}px render, got {big.size}")
    width, height = big.size
    canvas = width * height
    labels, palette, ground = _classes(big)
    ground_name = "transparent" if ground == 0 else "#{:02X}{:02X}{:02X}".format(*palette[ground - 1])
    budget = Budget(source=source, ground=ground_name)
    radius = BUDGET_UNITS / UNITS_PER_PX / 2
    output_px2 = (ANALYSIS_SIZE / 16) ** 2
    min_area = MIN_FEATURE_OUTPUT_PX2 * output_px2

    ground_mask = [label == ground for label in labels]
    # The figure is what is neither ground nor the transparency around a card.
    figure = [not g and (ground == 0 or label != 0) for g, label in zip(ground_mask, labels)]
    parts = [r for r in _components(figure, width, height, eight=True)
             if len(r) >= MIN_PART_OUTPUT_PX2 * output_px2]
    budget.parts_256 = len(parts)
    part_of = [-1] * canvas
    for index, region in enumerate(parts):
        for i in region:
            part_of[i] = index

    # Enclosed cuts: ground the canvas border cannot reach.
    region_of = [-1] * canvas
    enclosed: set[int] = set()
    for index, region in enumerate(_components(ground_mask, width, height, eight=False)):
        for i in region:
            region_of[i] = index
        if len(region) >= min_area and not _touches_border(region, width, height):
            enclosed.add(index)
    budget.cuts_256 = len(enclosed)

    # Thin ground: a cut under the two-pixel budget (L15), or a gap between
    # two parts under one pixel, which fuses (L26). A notch in the outer
    # contour separates nothing and is left to the silhouette test.
    thin, dist = _thin_parts(ground_mask, width, height, radius, outside_member=(ground == 0))
    reach = int(round(radius)) + 2
    for region in _components(thin, width, height, eight=True):
        if len(region) < min_area:
            continue
        units = _units(max(dist[i] for i in region))
        is_cut = any(region_of[i] in enclosed for i in region)
        touching: set[int] = set()
        for i in region[:: max(1, len(region) // 200)]:
            x, y = i % width, i // width
            for dy in range(-reach, reach + 1, 3):
                ny = y + dy
                if not 0 <= ny < height:
                    continue
                for dx in range(-reach, reach + 1, 3):
                    nx = x + dx
                    if 0 <= nx < width and part_of[ny * width + nx] >= 0:
                        touching.add(part_of[ny * width + nx])
        if is_cut and units < BUDGET_UNITS:
            budget.features.append(Feature(
                "cut", units, len(region) / output_px2, _centre(region, width, height)))
        elif not is_cut and len(touching) >= 2 and units < FUSE_UNITS:
            budget.features.append(Feature(
                "gap", units, len(region) / output_px2, _centre(region, width, height)))

    # Detached accents under the budget (L16).
    if len(parts) > 1:
        figure_dist = _chamfer(figure, width, height, outside_member=False)
        for region in parts:
            units = _units(max(figure_dist[i] for i in region))
            if len(region) / canvas <= ACCENT_MAX_SHARE and units < BUDGET_UNITS:
                budget.features.append(Feature(
                    "accent", units, len(region) / output_px2, _centre(region, width, height)))

    # Survival at 16px. A cut is open only where it owns at least two clearly
    # ground pixels (L15): an antialiased grey pixel is not an opening.
    small_px = _pixels(small)
    s_width, s_height = small.size
    ground_colour = palette[ground - 1] if ground else None

    def clearly_ground(pixel) -> bool:
        r, g, b, a = pixel
        if ground_colour is None:
            return a < 64
        return a >= 192 and _distance((r, g, b), ground_colour) <= COLOUR_MERGE * 0.66

    def is_figure(pixel) -> bool:
        r, g, b, a = pixel
        if ground_colour is None:
            return a >= 128
        return a >= 128 and _distance((r, g, b), ground_colour) > COLOUR_MERGE

    clear16 = [clearly_ground(p) for p in small_px]
    budget.cuts_16 = sum(
        1 for region in _components(clear16, s_width, s_height, eight=False)
        if len(region) >= 2 and not _touches_border(region, s_width, s_height)
    )
    budget.parts_16 = sum(
        1 for region in _components([is_figure(p) for p in small_px], s_width, s_height, eight=True)
        if len(region) >= 2
    )

    # Mush is recorded, never reported (see the module docstring).
    footprint = mushy = 0
    for r, g, b, a in small_px:
        if a < 24:
            continue
        footprint += 1
        if a < 200 or (palette and min(_distance((r, g, b), c) for c in palette) > COLOUR_MERGE):
            mushy += 1
    budget.mush_16 = mushy / footprint if footprint else 0.0

    # Tile share: how much of its card the mark spans (L28).
    if ground:
        opaque = [i for i, label in enumerate(labels) if label != 0]
        xs = [i % width for i, on in enumerate(figure) if on]
        ys = [i // width for i, on in enumerate(figure) if on]
        if xs:
            card_span = max(
                max(i % width for i in opaque) - min(i % width for i in opaque),
                max(i // width for i in opaque) - min(i // width for i in opaque),
            ) + 1
            budget.tile_share = (max(max(xs) - min(xs), max(ys) - min(ys)) + 1) / card_span
    return budget


def budget_svg(svg_text: str, rasterizer, *, source: str = "") -> Budget:
    """Measure the glyph rung — what ships at 16px — of one SVG source."""
    glyph = ladder.RungSource(svg_text).rung("glyph")
    return measure(
        rasterizer.render(glyph, ANALYSIS_SIZE), rasterizer.render(glyph, 16), source=source,
    )


def budget_sheet(entries: list[tuple[str, bytes, bytes, Budget]], out) -> Path:
    """Draw each candidate at 256px with its narrow features ringed, beside its
    16px render enlarged, so the designer sees where the budget is short."""
    from PIL import ImageDraw

    from .review import _font

    cell, zoom, pad = ANALYSIS_SIZE, ANALYSIS_SIZE, 20
    width = pad + len(entries) * (cell + zoom + 3 * pad)
    height = 60 + cell + 150
    sheet = Image.new("RGB", (max(width, 640), height), (23, 24, 28))
    draw = ImageDraw.Draw(sheet)
    title, small = _font(18), _font(13)
    draw.text((pad, 14), "IconFlow legibility budget — narrow features ringed; 16px enlarged",
              font=title, fill=(245, 241, 232))
    x = pad
    for name, png256, png16, budget in entries:
        y = 50
        big = Image.open(io.BytesIO(png256)).convert("RGBA")
        base = Image.new("RGBA", big.size, (255, 255, 255, 255))
        base.alpha_composite(big)
        ring = ImageDraw.Draw(base)
        for feature in budget.features:
            cx, cy = feature.centre[0] * cell, feature.centre[1] * cell
            r = 14
            colour = (255, 91, 61, 255) if feature.kind != "accent" else (244, 189, 86, 255)
            ring.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=3)
            ring.text((cx + r + 2, cy - 8), f"{feature.width_units}u", fill=colour, font=small)
        sheet.paste(base.convert("RGB"), (x, y))
        pixel = Image.open(io.BytesIO(png16)).convert("RGBA").resize((zoom, zoom), Image.Resampling.NEAREST)
        back = Image.new("RGBA", pixel.size, (255, 255, 255, 255))
        back.alpha_composite(pixel)
        sheet.paste(back.convert("RGB"), (x + cell + pad, y))
        draw.text((x, y + cell + 8), name, font=title, fill=(245, 241, 232))
        draw.text((x, y + cell + 34), budget.summary(), font=small, fill=(169, 171, 180))
        codes = sorted({f.code for f in budget.findings()})
        draw.text((x, y + cell + 54), ", ".join(codes) or "within budget", font=small,
                  fill=(255, 91, 61) if codes else (95, 208, 138))
        x += cell + zoom + 3 * pad
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
