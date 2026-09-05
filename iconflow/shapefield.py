# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""A deterministic 16px shape descriptor, and a distance between two of them.

Distinctiveness in the abstract is not measurable. *Distinguishability against
a named set* is: "is this mark the same shape at 16px as that one" is a
well-posed question, and this module is the instrument that answers it. It has
no opinion about which answer is good. A collision gate, a family-coherence
gate, and a frame-survival gate can all be built on it; the semantics live in
the callers (:mod:`iconflow.neighbours` is the first).

**Sampling.** The source's ``glyph`` rung — what actually ships at 16px — is
rendered at :data:`SAMPLE_SIZE`, split into figure and ground with the same
Otsu policy the detail ladder uses (so a full-bleed card is fingerprinted by
the mark punched into it, not by its rounded square), and that binary mask is
area-averaged onto a :data:`GRID`×:data:`GRID` grid of occupancy fractions.
Each cell is a 4×4 block of the 64px mask, so a cell holds one of seventeen
values, 0/16 through 16/16: the grid is at once "what 16px shows" and robust to
a single anti-aliased pixel moving on a different renderer.

**Descriptor.** The grid, plus four scalars a person can explain in one
sentence each: how many separate pieces the figure is in, how many holes are
cut through it, what share of the canvas it covers, and how wide its bounding
box is relative to its height.

**Distance.** Normalised L1 over the grid — the share of all ink that is not
shared — with topology reported *beside* it rather than folded into it. Neither
position nor scale is normalised: every IconFlow master is drawn on the same
1024 grid inside the same safe area, so two fields are already comparable, and
a mark that shifts or shrinks at 16px is a different mark at 16px.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import io

from PIL import Image, ImageFilter

from . import ladder

#: Descriptor format version. Bumping it invalidates every stored field.
VERSION = 1
#: Cells per side of the occupancy grid — the size an icon is judged at.
GRID = 16
#: Pixel size the figure mask is taken at before it is averaged onto the grid.
SAMPLE_SIZE = 64
#: Sub-pixels per cell along one axis; every cell is BLOCK×BLOCK mask pixels.
BLOCK = SAMPLE_SIZE // GRID
#: Occupancy values are k/CELL_STEPS for integer k.
CELL_STEPS = BLOCK * BLOCK
#: A figure or ground region smaller than one grid cell (in 64px pixels) is
#: not a piece or a hole at 16px — it is anti-aliasing debris, or an accent
#: that has already failed the two-pixel rule (docs/LEARNINGS.md L16). Tying
#: the floor to the cell keeps topology at the grid's own resolution.
MIN_REGION = BLOCK * BLOCK
#: A hole must be at least this many 64px pixels wide to count. Two pixels at
#: 16px is the floor a negative-space cut has to own (docs/LEARNINGS.md L15),
#: which is eight here; a hole narrower than five is a hairline that one
#: renderer's anti-aliasing closes and another's leaves open.
MIN_HOLE_WIDTH = 5

#: Compact one-character-per-cell alphabet for stored grids: ``'0'`` is an
#: empty cell, ``'g'`` a full one, and each step between is one sub-pixel.
GRID_ALPHABET = "0123456789abcdefg"
assert len(GRID_ALPHABET) == CELL_STEPS + 1


class ShapeFieldError(ValueError):
    """Raised when an input cannot be turned into, or read as, a field."""


@dataclass(frozen=True)
class ShapeField:
    """What one mark is at 16px, reduced to numbers that compare."""

    #: Row-major occupancy fractions, ``GRID * GRID`` values in ``[0, 1]``.
    grid: tuple[float, ...]
    #: Separate pieces of figure (8-connected), ignoring debris.
    components: int
    #: Ground regions fully enclosed by figure (4-connected), ignoring debris.
    holes: int
    #: Share of the sampled canvas that is figure.
    coverage: float
    #: Figure bounding-box width divided by height; 0 for an empty field.
    aspect: float

    def __post_init__(self) -> None:
        if len(self.grid) != GRID * GRID:
            raise ShapeFieldError(f"a field has {GRID * GRID} cells, got {len(self.grid)}")

    @property
    def empty(self) -> bool:
        return not any(self.grid)

    def cell(self, x: int, y: int) -> float:
        return self.grid[y * GRID + x]

    def encode_grid(self) -> str:
        """The grid as a ``GRID*GRID``-character string, one cell per character."""
        return "".join(
            GRID_ALPHABET[int(round(value * CELL_STEPS))] for value in self.grid
        )

    def as_dict(self) -> dict:
        return {
            "grid": self.encode_grid(),
            "components": self.components,
            "holes": self.holes,
            "coverage": round(self.coverage, 4),
            "aspect": round(self.aspect, 3),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShapeField":
        try:
            grid = decode_grid(data["grid"])
            return cls(
                grid=grid,
                components=int(data["components"]),
                holes=int(data["holes"]),
                coverage=float(data["coverage"]),
                aspect=float(data["aspect"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ShapeFieldError(f"malformed shape field: {exc}") from exc

    def image(self, scale: int = 1) -> Image.Image:
        """The grid as a greyscale picture: what 16px shows, ink dark."""
        picture = Image.new("L", (GRID, GRID))
        picture.putdata([int(round(255 - value * 255)) for value in self.grid])
        if scale > 1:
            picture = picture.resize((GRID * scale, GRID * scale), Image.NEAREST)
        return picture

    def silhouette(self, scale: int = 1, threshold: float = 0.5) -> Image.Image:
        """The grid as a binary silhouette, ink where a cell is mostly figure."""
        picture = Image.new("L", (GRID, GRID))
        picture.putdata([0 if value >= threshold else 255 for value in self.grid])
        if scale > 1:
            picture = picture.resize((GRID * scale, GRID * scale), Image.NEAREST)
        return picture


def decode_grid(encoded: str) -> tuple[float, ...]:
    if not isinstance(encoded, str) or len(encoded) != GRID * GRID:
        raise ShapeFieldError(
            f"encoded grid must be {GRID * GRID} characters, got "
            f"{len(encoded) if isinstance(encoded, str) else type(encoded).__name__}"
        )
    values = []
    for char in encoded:
        step = GRID_ALPHABET.find(char)
        if step < 0:
            raise ShapeFieldError(f"encoded grid has an unknown cell {char!r}")
        values.append(step / CELL_STEPS)
    return tuple(values)


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------


def _pixels(image: Image.Image):
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def _label_regions(
    solid: list[bool], width: int, height: int, *, eight: bool,
) -> list[list[int]]:
    """Connected regions of ``True`` pixels, each as a list of flat indices."""
    seen = [False] * (width * height)
    regions: list[list[int]] = []
    if eight:
        steps = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
    else:
        steps = ((0, -1), (-1, 0), (1, 0), (0, 1))
    for start in range(width * height):
        if seen[start] or not solid[start]:
            continue
        seen[start] = True
        queue: deque[int] = deque([start])
        region: list[int] = []
        while queue:
            index = queue.popleft()
            region.append(index)
            x, y = index % width, index // width
            for dx, dy in steps:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    neighbour = ny * width + nx
                    if solid[neighbour] and not seen[neighbour]:
                        seen[neighbour] = True
                        queue.append(neighbour)
        regions.append(region)
    return regions


def _exterior_ground(solid: list[bool], width: int, height: int) -> list[bool]:
    """Non-solid pixels connected (4-way) to the canvas border."""
    outside = [False] * (width * height)
    queue: deque[int] = deque()
    for index in range(width * height):
        x, y = index % width, index // width
        on_border = x == 0 or y == 0 or x == width - 1 or y == height - 1
        if on_border and not solid[index]:
            outside[index] = True
            queue.append(index)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                neighbour = ny * width + nx
                if not solid[neighbour] and not outside[neighbour]:
                    outside[neighbour] = True
                    queue.append(neighbour)
    return outside


def topology_bucket(field: ShapeField) -> tuple[int, int]:
    """The (pieces, holes) class the distance is reported beside: 1/2/3+ and 0/1/2+."""
    return _bucket_components(field.components), _bucket_holes(field.holes)


def field_from_mask(mask: Image.Image) -> ShapeField:
    """Reduce a binary figure mask (mode ``L``, 255 = figure) to a field."""
    if mask.size != (SAMPLE_SIZE, SAMPLE_SIZE):
        raise ShapeFieldError(
            f"figure mask must be {SAMPLE_SIZE}x{SAMPLE_SIZE}, got {mask.size}"
        )
    figure = [value >= 128 for value in _pixels(mask.convert("L"))]
    width = height = SAMPLE_SIZE

    grid = []
    for cy in range(GRID):
        for cx in range(GRID):
            count = 0
            for y in range(cy * BLOCK, (cy + 1) * BLOCK):
                row = y * width
                for x in range(cx * BLOCK, (cx + 1) * BLOCK):
                    if figure[row + x]:
                        count += 1
            grid.append(count / CELL_STEPS)

    # Figure pieces are 8-connected (a diagonal join is still one object);
    # ground is 4-connected (a diagonal gap does not let a hole leak out).
    pieces = [r for r in _label_regions(figure, width, height, eight=True)
              if len(r) >= MIN_REGION]
    # Holes are counted on ground that survives an erosion of two pixels, so
    # a slit narrower than MIN_HOLE_WIDTH — invisible at 16px, and flipped
    # open or shut by a renderer's anti-aliasing — is not a hole.
    ground_image = Image.new("L", (width, height))
    ground_image.putdata([0 if value else 255 for value in figure])
    deep = [value >= 128 for value in _pixels(
        ground_image.filter(ImageFilter.MinFilter(MIN_HOLE_WIDTH))
    )]
    holes = 0
    for region in _label_regions(deep, width, height, eight=False):
        if len(region) < MIN_REGION:
            continue
        touches_border = any(
            index % width in (0, width - 1) or index // width in (0, height - 1)
            for index in region
        )
        if not touches_border:
            holes += 1

    ink = sum(figure)
    if ink:
        xs = [index % width for index, on in enumerate(figure) if on]
        ys = [index // width for index, on in enumerate(figure) if on]
        aspect = (max(xs) - min(xs) + 1) / (max(ys) - min(ys) + 1)
    else:
        aspect = 0.0
    # Rounded here, not only when serialised, so a field is equal to itself
    # after a trip through the index.
    return ShapeField(
        grid=tuple(grid),
        components=len(pieces),
        holes=holes,
        coverage=round(ink / (width * height), 4),
        aspect=round(aspect, 3),
    )


#: Alpha at or above this is footprint — the same floor the ladder uses.
FOOTPRINT_ALPHA = 24
#: Alpha at or above this is solid: the pixels whose colour decides polarity.
SOLID_ALPHA = 128
#: A luminance class is only the figure when it holds at least this share of
#: the footprint. A smaller enclosed class is an accent, not the mark.
MIN_FIGURE_SHARE = 0.10
#: ...and touches at most this share of the footprint's outer boundary. A class
#: that reaches the edge is part of the outline, not something punched into it.
MAX_FIGURE_EDGE = 0.05
#: A footprint this large is a container — a card or a badge — and a mark on
#: it may lean on the rim a little (an accent breaking the card edge, the
#: anti-aliased corner of a full-bleed cut) and still be the thing punched in.
CARD_COVERAGE = 0.75
CARD_FIGURE_EDGE = 0.20


def figure_of(image: Image.Image) -> Image.Image:
    """The recognisable shape of one render, as a binary mask (255 = figure).

    The ladder splits figure from ground by Otsu's threshold and keeps the
    minority side; that is right for comparing rungs of *one* source, where
    polarity only has to be consistent. Comparing *different* sources needs
    the polarity to be right, so the field is stricter in three ways:

    * A transparent pixel is never figure. The rounded corners of a card, the
      air around a mark, are ground whatever grey they composite to.
    * The luminance split is taken over the footprint alone, and one class is
      the figure only if the footprint *encloses* it — it holds at least
      :data:`MIN_FIGURE_SHARE` of the footprint and reaches at most
      :data:`MAX_FIGURE_EDGE` of the footprint's outer boundary (a looser
      :data:`CARD_FIGURE_EDGE` when the footprint is a card or badge covering
      :data:`CARD_COVERAGE` of the canvas). That is the mark punched into a
      card, or the cloth inside its keyline.
    * Otherwise the footprint itself is the figure: a plain ink mark, a
      two-tone object whose colours both reach the edge, a card with nothing
      enclosed. What a viewer sees at 16px is the outline, so that is what is
      compared.
    """
    if image.size != (SAMPLE_SIZE, SAMPLE_SIZE):
        raise ShapeFieldError(
            f"field renders must be {SAMPLE_SIZE}px, got {image.size}"
        )
    width, height = image.size
    alpha = list(_pixels(image.getchannel("A")))
    luma = list(_pixels(image.convert("RGB").convert("L")))
    footprint = [a >= FOOTPRINT_ALPHA for a in alpha]
    # Polarity is decided on solid pixels only. The anti-aliased rim of a card
    # carries whatever colour the renderer un-premultiplied there, and a ring
    # of light rim pixels must not make a light mark look as if it reached
    # the edge.
    solid = [a >= SOLID_ALPHA for a in alpha]
    opaque = [luma[i] for i, on in enumerate(solid) if on]
    if not any(footprint):
        return Image.new("L", image.size, 0)
    if not opaque:
        mask = Image.new("L", image.size)
        mask.putdata([255 if on else 0 for on in footprint])
        return mask

    histogram = [0] * 256
    for value in opaque:
        histogram[value] += 1
    threshold = ladder.otsu_threshold(histogram)
    dark = [on and luma[i] <= threshold for i, on in enumerate(solid)]
    light = [on and luma[i] > threshold for i, on in enumerate(solid)]

    # The *outer* boundary: solid pixels touching ground that reaches the
    # canvas edge. A transparent hole punched through the middle of a mark is
    # not the outside, and a class lining that hole must not be counted as
    # reaching the rim.
    outside = _exterior_ground(solid, width, height)
    edge = [
        on and (
            x == 0 or y == 0 or x == width - 1 or y == height - 1
            or outside[i - 1] or outside[i + 1]
            or outside[i - width] or outside[i + width]
        )
        for i, on in enumerate(solid)
        for x, y in ((i % width, i // width),)
    ]
    edge_total = sum(edge) or 1
    solid_total = sum(solid)
    is_card = solid_total / (width * height) >= CARD_COVERAGE
    max_reach = CARD_FIGURE_EDGE if is_card else MAX_FIGURE_EDGE

    def enclosed(cls: list[bool]) -> bool:
        share = sum(cls) / solid_total
        reach = sum(1 for i, on in enumerate(cls) if on and edge[i]) / edge_total
        return share >= MIN_FIGURE_SHARE and reach <= max_reach

    candidates = [cls for cls in (dark, light) if enclosed(cls)]
    figure = candidates[0] if len(candidates) == 1 else footprint
    mask = Image.new("L", image.size)
    mask.putdata([255 if on else 0 for on in figure])
    return mask


def field_from_png(png: bytes) -> ShapeField:
    """Fingerprint one ``SAMPLE_SIZE`` render — see :func:`figure_of`."""
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    return field_from_mask(figure_of(image))


def field_from_svg(svg_text: str, rasterizer) -> ShapeField:
    """Fingerprint the ``glyph`` rung of a source — what ships at 16px.

    A flat source has one rung and reduces to itself, so this costs a laddered
    and an unladdered master exactly the same: one render.
    """
    glyph = ladder.RungSource(svg_text).rung("glyph")
    return field_from_png(rasterizer.render(glyph, SAMPLE_SIZE))


# --------------------------------------------------------------------------
# Distance
# --------------------------------------------------------------------------


def _bucket_components(count: int) -> int:
    return min(max(count, 1), 3)


def _bucket_holes(count: int) -> int:
    return min(max(count, 0), 2)


@dataclass(frozen=True)
class Separation:
    """How far apart two fields are, and whether they are even the same kind."""

    #: Share of all occupancy that the two grids do not share: 0 is identical,
    #: 1 is disjoint. Bray–Curtis on the occupancy grids.
    distance: float
    #: True when both fields have the same number of pieces (1, 2, 3+) and the
    #: same number of holes (0, 1, 2+). Reported beside the distance, never
    #: added to it: a ring and a disc can be grid-close and still be two
    #: different objects, and that is a fact to show, not a number to weight.
    same_topology: bool
    components: tuple[int, int]
    holes: tuple[int, int]

    def as_dict(self) -> dict:
        return {
            "distance": round(self.distance, 4),
            "same_topology": self.same_topology,
            "components": list(self.components),
            "holes": list(self.holes),
        }


def grid_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Normalised L1: what share of the combined ink is not shared."""
    total = sum(a) + sum(b)
    if total <= 0:
        return 0.0
    return sum(abs(x - y) for x, y in zip(a, b)) / total


def separation(a: ShapeField, b: ShapeField) -> Separation:
    return Separation(
        distance=grid_distance(a.grid, b.grid),
        same_topology=(
            _bucket_components(a.components) == _bucket_components(b.components)
            and _bucket_holes(a.holes) == _bucket_holes(b.holes)
        ),
        components=(a.components, b.components),
        holes=(a.holes, b.holes),
    )
