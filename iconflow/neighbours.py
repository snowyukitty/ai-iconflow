# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The neighbourhood — which known marks a candidate is the same shape as at 16px.

"Is this mark distinctive?" is ill-posed, and the casebook is full of the
misses a human eye let through: a two-panel curtain that was the pi symbol, an
interlace that landed on a hashtag, a row of rising blocks that was a bar chart
whatever the designer meant. "Is this mark distinguishable at 16px from *these
specific other marks*?" is well-posed, and this module answers it with the
instrument in :mod:`iconflow.shapefield` and a corpus IconFlow already owns.

The corpus has two halves, both pre-indexed and checked in:

* the **collision set** — deliberately plain renditions of the forms every
  operating system already owns (gear, bell, folder, bar chart, ``+ ✓ # π``,
  a few letterforms), drawn in ``iconflow/resources/collision/``;
* the **house corpus** — IconFlow's own published marks.

A project adds its own sets in ``iconflow.toml``:

* ``avoid`` — the marks this product must not resemble. The only set that
  **gates**: a hit is ``neighbour-collision`` and names the mark it hit.
* ``family`` — marks that are *supposed* to be close. Excluded from every
  finding.
* ``portfolio`` — the marks this product's owner already shipped. Three or more
  within the radius is ``neighbour-house-rut``, the house-cliché signal made
  quantitative.

A hit against the bundled corpus is ``neighbour-familiar`` and **never gates**:
if IconFlow's own marks could block a build, every user would be gated by
IconFlow's house style. The house corpus is a mirror, not a wall.

This is not a trademark or clearance check and must never be read as one.
Shape distance at 16px is not a legal opinion. It does not measure
distinctiveness either; the human ≥4/5 gate stays exactly where it is.
"""
from __future__ import annotations

import fnmatch
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import agentkit, shapefield
from .findings import Finding

#: Two fields at or below this distance, with matching topology, are the
#: same shape at 16px. Calibrated on the casebook's recorded collisions —
#: interlace/hashtag 0.065, rising blocks/bar chart 0.071, bold H on a tile /
#: letter H 0.104 — and on the closest pair of *distinct* generic forms in the
#: collision set, monitor/speech bubble at 0.080, which is a real ambiguity at
#: 16px. The nearest recorded *miss* is a rejected draft at 0.170 with a
#: different topology; the redesigns that shipped sit at 0.319 and beyond. See
#: docs/NEIGHBOURHOOD.md for the full table, including what the radius misses.
COLLISION_RADIUS = 0.12
#: Portfolio marks within the radius before the rut advisory fires.
RUT_COUNT = 3
#: Nearest neighbours reported and drawn, whether or not any is within radius.
NEAREST = 6

INDEX_FILE = "index.json"
INDEX_SCHEMA = 1
#: The two bundled halves of the corpus, by set name.
BUNDLED_SETS = ("collision", "house")
_ALIAS_RE = re.compile(r"^@(collision|house)(?:/(.+))?$")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


class NeighbourError(ValueError):
    """Raised when the index or a declared set cannot be used."""


@dataclass(frozen=True)
class Entry:
    """One known mark: where it came from and what it is at 16px."""

    id: str
    set: str
    title: str
    source: str
    source_sha256: str
    field: shapefield.ShapeField
    #: Source text when the entry was rendered in this process (a declared
    #: file) or can be re-read from a checkout; lets the proof sheet draw it.
    svg: str | None = None
    #: ``"bundled"`` for an index entry or an alias into one — whose `source`
    #: is repository-relative and must never be resolved against the working
    #: directory — and ``"file"`` for a declared file the caller rendered.
    origin: str = "file"

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "set": self.set,
            "title": self.title,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "field": self.field.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entry":
        try:
            return cls(
                id=str(data["id"]),
                set=str(data["set"]),
                title=str(data.get("title", "")),
                source=str(data["source"]),
                source_sha256=str(data["source_sha256"]),
                field=shapefield.ShapeField.from_dict(data["field"]),
                origin="bundled",
            )
        except (KeyError, TypeError, ValueError, shapefield.ShapeFieldError) as exc:
            raise NeighbourError(f"malformed index entry: {exc}") from exc


@dataclass(frozen=True)
class Index:
    """The checked-in, content-addressed corpus of fields."""

    entries: tuple[Entry, ...]
    descriptor_version: int
    generator: str

    def by_set(self, name: str) -> list[Entry]:
        return [entry for entry in self.entries if entry.set == name]

    def get(self, entry_id: str) -> Entry | None:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None


def index_dict(entries: list[Entry], *, generator: str) -> dict:
    """The exact JSON object the generator writes; sorted so it diffs cleanly."""
    return {
        "schema": INDEX_SCHEMA,
        "descriptor": {
            "version": shapefield.VERSION,
            "grid": shapefield.GRID,
            "sample_size": shapefield.SAMPLE_SIZE,
        },
        "generator": generator,
        "entries": [entry.as_dict() for entry in sorted(entries, key=lambda e: e.id)],
    }


def parse_index(text: str) -> Index:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NeighbourError(f"index is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != INDEX_SCHEMA:
        raise NeighbourError(f"index schema must be {INDEX_SCHEMA}")
    descriptor = data.get("descriptor") or {}
    version = descriptor.get("version")
    if version != shapefield.VERSION:
        raise NeighbourError(
            f"index was built with descriptor version {version!r}; this IconFlow "
            f"speaks version {shapefield.VERSION}. Rebuild it with "
            "scripts/build_collision_index.py"
        )
    if (descriptor.get("grid"), descriptor.get("sample_size")) != (
        shapefield.GRID, shapefield.SAMPLE_SIZE,
    ):
        raise NeighbourError("index sampling parameters do not match this IconFlow")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise NeighbourError("index entries must be a list")
    parsed = tuple(Entry.from_dict(item) for item in entries)
    seen: set[str] = set()
    for entry in parsed:
        if entry.id in seen:
            raise NeighbourError(f"index lists {entry.id!r} twice")
        seen.add(entry.id)
    return Index(parsed, int(version), str(data.get("generator", "")))


def load_index() -> Index:
    """The packaged index, resolved the same way every other resource is."""
    try:
        text = agentkit.resource("collision", INDEX_FILE).read_text(encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as exc:
        raise NeighbourError(f"the neighbourhood index is unavailable: {exc}") from exc
    return parse_index(text)


# --------------------------------------------------------------------------
# Declared sets
# --------------------------------------------------------------------------


def svg_title(svg_text: str, fallback: str) -> str:
    match = _TITLE_RE.search(svg_text)
    if not match:
        return fallback
    title = " ".join(match.group(1).split())
    return title or fallback


def entry_from_svg(path: Path, *, set_name: str, rasterizer,
                   entry_id: str | None = None) -> Entry:
    """Render one declared source and fingerprint it."""
    from .config import svg_sha256
    from .rasterize import load_svg

    text = load_svg(path)
    # Every IconFlow project calls its source master.svg, so the directory is
    # the name that tells one declared mark from another.
    stem = path.parent.name if path.name.lower() == "master.svg" and path.parent.name else path.stem
    return Entry(
        id=entry_id or f"{set_name}/{stem}",
        set=set_name,
        title=svg_title(text, stem),
        source=str(path),
        source_sha256=svg_sha256(path),
        field=shapefield.field_from_svg(text, rasterizer),
        svg=text,
    )


def _is_glob(part: str) -> bool:
    return any(char in part for char in "*?[")


def _expand_spec(spec: str, base: Path) -> list[Path]:
    """One path or glob, resolved from `base`, to the SVG files it names.

    A glob that matches nothing is an error, not an empty set: a declared
    `avoid` that silently resolved to nothing would be a gate that quietly
    stopped gating.
    """
    candidate = Path(spec).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    if _is_glob(spec):
        parts = candidate.parts
        first = next(i for i, part in enumerate(parts) if _is_glob(part))
        root = Path(*parts[:first]) if first else Path(".")
        pattern = "/".join(parts[first:])
        matches = sorted(
            p for p in root.glob(pattern) if p.is_file() and p.suffix.lower() == ".svg"
        )
        if not matches:
            raise NeighbourError(f"declared glob matches no SVG: {spec} (from {base})")
        return matches
    if not candidate.is_file():
        raise NeighbourError(f"declared mark not found: {candidate}")
    return [candidate]


def resolve_set(specs, *, set_name: str, base: Path, index: Index,
                rasterizer) -> list[Entry]:
    """Turn one declared list into entries, rendering only what needs rendering.

    Each item is either a file path or glob (rendered now, relative to `base`)
    or an alias into the bundled index — ``@collision``, ``@house``, or one
    entry such as ``@collision/bell`` — which costs nothing.
    """
    entries: list[Entry] = []
    # One mark, one entry: overlapping globs, a repeated path, or an alias
    # beside the set it belongs to must not gate twice or count twice.
    seen_sources: set[str] = set()
    used_ids: set[str] = set()

    def unique(entry_id: str) -> str:
        if entry_id not in used_ids:
            used_ids.add(entry_id)
            return entry_id
        suffix = 2
        while f"{entry_id}~{suffix}" in used_ids:
            suffix += 1
        used_ids.add(f"{entry_id}~{suffix}")
        return f"{entry_id}~{suffix}"

    for spec in specs:
        spec = str(spec).strip()
        if not spec:
            continue
        alias = _ALIAS_RE.match(spec)
        if alias:
            bundled, member = alias.group(1), alias.group(2)
            if member is None:
                chosen = index.by_set(bundled)
            else:
                chosen = [e for e in index.by_set(bundled)
                          if fnmatch.fnmatchcase(e.id, f"{bundled}/{member}")]
                if not chosen:
                    raise NeighbourError(
                        f"{spec!r} names nothing in the bundled {bundled} set"
                    )
            for entry in chosen:
                key = identity(entry)
                if key in seen_sources:
                    continue
                seen_sources.add(key)
                entries.append(Entry(
                    id=unique(entry.id), set=set_name, title=entry.title,
                    source=entry.source, source_sha256=entry.source_sha256,
                    field=entry.field, origin="bundled",
                ))
            continue
        for path in _expand_spec(spec, base):
            key = _same_file_key(str(path))
            if key in seen_sources:
                continue
            seen_sources.add(key)
            entry = entry_from_svg(path, set_name=set_name, rasterizer=rasterizer)
            if entry.id in used_ids:
                entry = Entry(
                    id=unique(entry.id), set=entry.set, title=entry.title,
                    source=entry.source, source_sha256=entry.source_sha256,
                    field=entry.field, svg=entry.svg,
                )
            else:
                used_ids.add(entry.id)
            entries.append(entry)
    return entries


# --------------------------------------------------------------------------
# The query
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Neighbour:
    entry: Entry
    separation: shapefield.Separation

    @property
    def distance(self) -> float:
        return self.separation.distance

    def within(self, radius: float) -> bool:
        return self.distance <= radius and self.separation.same_topology

    def as_dict(self) -> dict:
        return {
            "id": self.entry.id,
            "set": self.entry.set,
            "title": self.entry.title,
            "source": self.entry.source,
            **self.separation.as_dict(),
        }


@dataclass
class Neighbourhood:
    """Everything the gate, the envelope, and the sheet need about one candidate."""

    candidate: Entry
    radius: float
    nearest: list[Neighbour] = field(default_factory=list)
    collisions: list[Neighbour] = field(default_factory=list)
    familiar: list[Neighbour] = field(default_factory=list)
    rut: list[Neighbour] = field(default_factory=list)
    family: list[Neighbour] = field(default_factory=list)

    def findings(self) -> tuple[list[Finding], list[Finding]]:
        """(gating warnings, advisories) with the stable contract codes."""
        warnings: list[Finding] = []
        advisories: list[Finding] = []
        for hit in self.collisions:
            warnings.append(Finding(
                "neighbour-collision",
                f"At 16px this mark is the same shape as {hit.entry.title} "
                f"({hit.entry.id}; distance {hit.distance:.2f}, radius {self.radius:.2f}, "
                "same topology), which this project declared it must not resemble. "
                "Redesign the silhouette rather than the radius: the collision "
                "is in the shape, and no styling survives 16px to correct it.",
            ))
        for hit in self.familiar:
            if hit.entry.set == "collision":
                advisories.append(Finding(
                    "neighbour-familiar",
                    f"At 16px this mark reads as a {hit.entry.title.lower()} "
                    f"({hit.entry.id}; distance {hit.distance:.2f}, radius "
                    f"{self.radius:.2f}). That is a generic form every system already "
                    "owns: docs/LEARNINGS.md L9 says kill the concept at bake-off, "
                    "because small sizes strip the styling and leave the borrowed "
                    "meaning. Advisory — add \"@collision\" to [neighbours] avoid to "
                    "make it gate.",
                ))
            else:
                advisories.append(Finding(
                    "neighbour-familiar",
                    f"At 16px this mark sits within the collision radius of IconFlow's "
                    f"{hit.entry.id} — {hit.entry.title} (distance {hit.distance:.2f}, "
                    f"radius {self.radius:.2f}). Advisory: the house corpus is a mirror, "
                    "not a wall. Look at the two side by side before deciding.",
                ))
        if len(self.rut) >= RUT_COUNT:
            names = ", ".join(f"{hit.entry.id} ({hit.distance:.2f})" for hit in self.rut)
            advisories.append(Finding(
                "neighbour-house-rut",
                f"{len(self.rut)} of this portfolio's previous marks sit within the "
                f"collision radius ({self.radius:.2f}): {names}. This silhouette is a "
                "route the house has already taken; the house-cliché signal "
                "`case stats` estimates from device families, measured on pixels. "
                "Advisory: a family resemblance may be wanted. A rut is not.",
            ))
        return warnings, advisories

    def as_dict(self) -> dict:
        return {
            "radius": self.radius,
            "field": {
                key: value for key, value in self.candidate.field.as_dict().items()
                if key != "grid"
            },
            "nearest": [n.as_dict() for n in self.nearest],
            "collisions": [n.entry.id for n in self.collisions],
            "familiar": [n.entry.id for n in self.familiar],
            "rut": [n.entry.id for n in self.rut],
            "family": [n.as_dict() for n in self.family],
        }


def neighbourhood(candidate: Entry, *, index: Index | None,
                  avoid: list[Entry] = (), family: list[Entry] = (),
                  portfolio: list[Entry] = (),
                  radius: float = COLLISION_RADIUS,
                  nearest: int = NEAREST) -> Neighbourhood:
    """Rank every known mark against the candidate and sort them into findings.

    The candidate is never its own neighbour: a bundled entry with the
    candidate's source hash (a house mark being re-audited) is skipped, and a
    declared file is skipped when it *is* the candidate's file — by path, not
    by hash, because a byte-identical copy under another name in `avoid` is
    exactly the collision the set exists to catch. A `family` entry is skipped
    in every set it also appears in — that is what "excluded from the gate
    entirely" means.
    """
    if not math.isfinite(radius) or radius <= 0:
        raise NeighbourError("the collision radius must be a positive finite number")
    family_keys = {identity(e) for e in family} | {e.id for e in family}
    self_key = identity(candidate)
    # A bundled entry the project also lists in `avoid` — by alias, or by the
    # path of the very same file — is gated there; reporting it as merely
    # familiar as well would advise the user to do what they have already done.
    promoted = {identity(e) for e in avoid} | {e.id for e in avoid}

    def rank(entries, *, bundled: bool) -> list[Neighbour]:
        ranked = []
        for entry in entries:
            key = identity(entry)
            # The candidate is never its own neighbour, and "its own" means the
            # same file: a byte-identical copy under another path is a
            # neighbour at distance zero, which is the finding, not noise.
            if key == self_key or key in family_keys or entry.id in family_keys:
                continue
            if bundled and (key in promoted or entry.id in promoted):
                continue
            ranked.append(
                Neighbour(entry, shapefield.separation(candidate.field, entry.field))
            )
        ranked.sort(key=lambda n: (n.distance, n.entry.id))
        return ranked

    bundled = rank(index.entries, bundled=True) if index else []
    avoided = rank(avoid, bundled=False)
    owned = rank(portfolio, bundled=False)
    everything = sorted(bundled + avoided + owned, key=lambda n: (n.distance, n.entry.id))
    shown = everything[:nearest]
    for hit in everything[nearest:]:
        if hit.within(radius):
            shown.append(hit)
    return Neighbourhood(
        candidate=candidate,
        radius=radius,
        nearest=shown,
        collisions=[n for n in avoided if n.within(radius)],
        familiar=[n for n in bundled if n.within(radius)],
        rut=[n for n in owned if n.within(radius)],
        family=[
            Neighbour(entry, shapefield.separation(candidate.field, entry.field))
            for entry in family
            if identity(entry) != self_key
        ],
    )


def _same_file_key(source: str) -> str:
    """One string per file on disk, so two spellings of a path compare equal."""
    try:
        return str(Path(source).expanduser().resolve())
    except OSError:
        return source


def bundled_source_path(entry: Entry) -> Path | None:
    """Where a bundled entry's source lives on *this* machine, if anywhere.

    Index sources are repository-relative. In a checkout that is a real file;
    from a wheel only the collision set travels, under the packaged resource
    root. Resolving here — never against the working directory — is what
    gives an alias a corpus identity that does not depend on where the
    command was typed.
    """
    checkout = agentkit.checkout_root()
    if checkout is not None:
        path = checkout / entry.source
        if path.is_file():
            return path
    if entry.set == "collision" or entry.source.startswith("iconflow/resources/collision/"):
        try:
            packaged = agentkit.resource("collision", entry.source.rsplit("/", 1)[-1])
        except (RuntimeError, ValueError):
            return None
        if getattr(packaged, "is_file", lambda: False)():
            return Path(str(packaged))
    return None


def identity(entry: Entry) -> str:
    """The key two entries share when they are the same file.

    A declared file is its resolved path. A bundled entry is the resolved path
    of its source when this machine has it, else its bundled id — so an alias
    beside the real file behind it is one mark, and a candidate is skipped
    only when it *is* the indexed file, not when it merely has its bytes.
    """
    if entry.origin == "bundled":
        located = bundled_source_path(entry)
        return str(located.resolve()) if located is not None else f"@{entry.id}"
    return _same_file_key(entry.source)
