# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The Family tier: a set of marks must be coherent *and* mutually distinguishable.

:mod:`iconflow.neighbours` asks whether one mark is the same shape as marks it
must not resemble. A family asks the opposite question of its own members:
they are *supposed* to look related, and still no two may be the same mark at
16px. Both answers come from the same instrument, :mod:`iconflow.shapefield`,
unchanged — this module only decides what to compare.

**Coherence.** Members whose raw 16px fields are within :data:`COHERENCE` of
each other share a *carrier*: the squircle head of a set of emotes, the plate
of a suite of app icons. Linked members form carrier groups (connected
components), found from the fields alone; a member linked to no one stands
alone, which is a fact to report, not a defect.

**Distinguishability.** Inside a group the shared carrier dominates the raw
distance — two faces on the same head are 0.02 apart however different their
expressions, because the head is most of the ink. So siblings are compared on
their *residual*: each field's difference from the group's carrier, the
cell-wise median of its members. The distance is the same normalised L1 the
neighbourhood uses, taken over what is not shared::

    residual(a, b) = |a - b| / (|a - carrier| + |b - carrier|)

It lies in [0, 1]. Below :data:`TWIN_FLOOR` two members share more than two
thirds of what sets them apart from their carrier — one expression drawn
twice — and the family is gated. A group of two has no carrier to speak of (its
median is the midpoint, and every residual is 1), so a pair falls back to the
neighbourhood's own rule: within :data:`neighbours.COLLISION_RADIUS` with the
same topology.

The floor is provisional. The collision radius was calibrated on recorded
casebook collisions; no family has been recorded yet, so 1/3 is the
explainable line above, checked against one reviewed set (the IconFlow emotes,
where it separates the near-twin smile/wink from every other pair by a clear
margin). docs/FAMILY.md records it as such.
"""
from __future__ import annotations

import itertools
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from . import neighbours, shapefield
from .findings import Finding

#: Raw 16px distance within which two members share a carrier.
COHERENCE = 0.20
#: Residual distance below which two siblings are one mark drawn twice.
TWIN_FLOOR = 1 / 3
#: Closest pairs reported and drawn, whether or not any is a twin.
NEAREST = 8


class FamilyError(ValueError):
    """Raised when the declared members cannot form a family."""


@dataclass(frozen=True)
class Pair:
    a: neighbours.Entry
    b: neighbours.Entry
    raw: shapefield.Separation
    #: Residual distance from the shared carrier, or None for a group of two.
    residual: float | None
    group: int

    @property
    def twin(self) -> bool:
        if self.residual is None:
            return self.raw.distance <= neighbours.COLLISION_RADIUS and self.raw.same_topology
        return self.residual < TWIN_FLOOR

    @property
    def score(self) -> float:
        """The number a pair is ranked by: its residual, or its raw distance."""
        return self.residual if self.residual is not None else self.raw.distance

    def as_dict(self) -> dict:
        return {
            "a": self.a.id,
            "b": self.b.id,
            "group": self.group,
            "residual": None if self.residual is None else round(self.residual, 4),
            "raw": self.raw.as_dict(),
            "twin": self.twin,
        }


@dataclass
class Family:
    members: list[neighbours.Entry]
    groups: list[list[neighbours.Entry]]
    pairs: list[Pair] = field(default_factory=list)

    @property
    def twins(self) -> list[Pair]:
        return [pair for pair in self.pairs if pair.twin]

    @property
    def loners(self) -> list[neighbours.Entry]:
        return [group[0] for group in self.groups if len(group) == 1]

    def nearest(self, count: int = NEAREST) -> list[Pair]:
        ranked = sorted(self.pairs, key=lambda p: p.score)
        twins = [p for p in ranked if p.twin]
        rest = [p for p in ranked if not p.twin]
        return twins + rest[: max(0, count - len(twins))]

    def findings(self) -> list[Finding]:
        return [
            Finding(
                "family-twins",
                f"{pair.a.title} and {pair.b.title} are one mark at 16px "
                + (f"(residual {pair.residual:.2f} from their shared carrier, floor {TWIN_FLOOR:.2f})"
                   if pair.residual is not None else
                   f"(distance {pair.raw.distance:.2f}, radius {neighbours.COLLISION_RADIUS:.2f}, same topology)")
                + ". Change what tells them apart, not their colour.",
            )
            for pair in self.twins
        ]

    def as_dict(self) -> dict:
        return {
            "coherence": COHERENCE,
            "twin_floor": round(TWIN_FLOOR, 4),
            "members": [
                {"id": m.id, "title": m.title, "source": m.source, "source_sha256": m.source_sha256,
                 "field": {k: v for k, v in m.field.as_dict().items() if k != "grid"}}
                for m in self.members
            ],
            "groups": [[m.id for m in group] for group in self.groups],
            "nearest": [pair.as_dict() for pair in self.nearest()],
            "twins": [[pair.a.id, pair.b.id] for pair in self.twins],
        }


def carrier_groups(members: list[neighbours.Entry]) -> list[list[neighbours.Entry]]:
    """Connected components of 'raw distance <= COHERENCE', largest first."""
    parent = list(range(len(members)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in itertools.combinations(range(len(members)), 2):
        if shapefield.grid_distance(members[i].field.grid, members[j].field.grid) <= COHERENCE:
            parent[root(i)] = root(j)
    groups: dict[int, list[neighbours.Entry]] = {}
    for i, member in enumerate(members):
        groups.setdefault(root(i), []).append(member)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0].id))


def carrier(group: list[neighbours.Entry]) -> tuple[float, ...]:
    """The shape a group shares: the cell-wise median of its members' fields."""
    return tuple(statistics.median(m.field.grid[i] for m in group)
                 for i in range(shapefield.GRID * shapefield.GRID))


def residual_distance(a: shapefield.ShapeField, b: shapefield.ShapeField,
                      shared: tuple[float, ...]) -> float:
    off_a = sum(abs(x - c) for x, c in zip(a.grid, shared))
    off_b = sum(abs(y - c) for y, c in zip(b.grid, shared))
    if off_a + off_b <= 0:
        return 0.0
    return sum(abs(x - y) for x, y in zip(a.grid, b.grid)) / (off_a + off_b)


def assess(members: list[neighbours.Entry]) -> Family:
    """Group the members by carrier and compare every pair of siblings."""
    if len(members) < 2:
        raise FamilyError("a family needs at least two members")
    groups = carrier_groups(members)
    family = Family(members=members, groups=groups)
    for index, group in enumerate(groups):
        shared = carrier(group) if len(group) >= 3 else None
        for a, b in itertools.combinations(group, 2):
            family.pairs.append(Pair(
                a=a, b=b, raw=shapefield.separation(a.field, b.field),
                residual=residual_distance(a.field, b.field, shared) if shared else None,
                group=index,
            ))
    return family


def resolve_members(specs: list[str], base: Path) -> list[Path]:
    """Paths and globs to unique SVG files, in a stable order."""
    paths: list[Path] = []
    seen: set[str] = set()
    for spec in specs:
        try:
            found = neighbours._expand_spec(spec, base)
        except neighbours.NeighbourError as exc:
            raise FamilyError(str(exc)) from exc
        for path in found:
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                paths.append(path)
    return paths


def family_sheet(family: Family, out: str | Path, *, rasterizer=None) -> Path:
    """The picture behind the numbers: each closest pair, side by side.

    One row per pair: both members at 22px with their pixels shown (where
    chat apps draw emotes and toolbars draw icons), both at true 28px size,
    and the 16x16 cells where their fields differ — the part that tells the
    two apart. A twin's row is outlined in coral.
    """
    import io

    from PIL import Image, ImageDraw

    from . import review
    from .rasterize import Rasterizer

    pairs = family.nearest()
    zoom, cell, row_h = 4, 88, 116
    label_w = 330
    width = review._PAD * 2 + label_w + 5 * (cell + review._GAP)
    height = 46 + 26 + len(pairs) * row_h + review._PAD
    sheet = Image.new("RGBA", (width, height), review._SHEET_BG)
    draw = ImageDraw.Draw(sheet)
    title, small = review._font(18), review._font(14)
    draw.rounded_rectangle([review._PAD, 10, review._PAD + 28, 38], radius=8, fill=review._SIGNAL)
    groups = sum(1 for g in family.groups if len(g) > 1)
    draw.text((review._PAD + 40, 8),
              f"IconFlow family — {len(family.members)} members, {groups} carrier group(s), "
              f"twin floor {TWIN_FLOOR:.2f}", font=title, fill=review._TXT)
    x0 = review._PAD + label_w
    for i, heading in enumerate(("A at 22px", "B at 22px", "A 28px", "B 28px", "where they differ")):
        draw.text((x0 + i * (cell + review._GAP), 46), heading, font=small, fill=review._LABEL)

    def pictures(active) -> dict[str, tuple]:
        out_pics = {}
        for entry in {e.id: e for p in pairs for e in (p.a, p.b)}.values():
            at22 = Image.open(io.BytesIO(active.render(entry.svg, 22))).convert("RGBA")
            at28 = Image.open(io.BytesIO(active.render(entry.svg, 28))).convert("RGBA")
            out_pics[entry.id] = (at22.resize((22 * zoom, 22 * zoom), Image.NEAREST), at28)
        return out_pics

    if rasterizer is None:
        with Rasterizer() as owned:
            pics = pictures(owned)
    else:
        pics = pictures(rasterizer)

    y = 72
    for pair in pairs:
        outline = review._NEAR if pair.twin else (70, 72, 80, 255)
        label = (f"residual {pair.residual:.2f}" if pair.residual is not None
                 else f"distance {pair.raw.distance:.2f} (pair group)")
        draw.text((review._PAD, y + 18), f"{pair.a.title}  /  {pair.b.title}"[:44], font=small, fill=review._TXT)
        draw.text((review._PAD, y + 42), label + ("  — TWINS" if pair.twin else ""), font=small,
                  fill=review._NEAR if pair.twin else review._LABEL)
        draw.text((review._PAD, y + 62), f"raw 16px {pair.raw.distance:.2f}", font=small, fill=review._LABEL)
        a22, a28 = pics[pair.a.id]
        b22, b28 = pics[pair.b.id]
        for column, picture in enumerate((a22, b22, a28, b28)):
            x = x0 + column * (cell + review._GAP)
            card = Image.new("RGBA", (cell, cell), "#ffffff")
            offset = ((cell - picture.width) // 2, (cell - picture.height) // 2)
            card.alpha_composite(picture, offset)
            sheet.alpha_composite(card, (x, y))
            draw.rectangle([x - 1, y - 1, x + cell, y + cell], outline=outline, width=2 if pair.twin else 1)
        diff = Image.new("L", (shapefield.GRID, shapefield.GRID))
        diff.putdata([int(255 - min(1.0, abs(p - q)) * 255) for p, q in zip(pair.a.field.grid, pair.b.field.grid)])
        diff = diff.resize((cell, cell), Image.NEAREST).convert("RGBA")
        x = x0 + 4 * (cell + review._GAP)
        sheet.alpha_composite(diff, (x, y))
        draw.rectangle([x - 1, y - 1, x + cell, y + cell], outline=outline, width=2 if pair.twin else 1)
        y += row_h
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)
    return out


def audit(paths: list[Path], *, rasterizer=None) -> Family:
    """Render and fingerprint every member, then assess the family."""
    from .rasterize import Rasterizer

    def entries(active) -> list[neighbours.Entry]:
        return [neighbours.entry_from_svg(path, set_name="family", rasterizer=active) for path in paths]

    if rasterizer is None:
        with Rasterizer() as owned:
            return assess(entries(owned))
    return assess(entries(rasterizer))
