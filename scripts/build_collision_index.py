# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Build the neighbourhood index from the marks IconFlow already owns.

The index at ``iconflow/resources/collision/index.json`` is a checked-in,
content-addressed table: every entry carries the SHA-256 of the source it was
fingerprinted from, and the whole file is regenerated from source rather than
edited. A generated table nobody can date is the thing this project exists not
to ship, so ``--check`` fails until the committed index matches a fresh build.

Two halves are indexed:

* ``collision`` — the plain generic forms in ``iconflow/resources/collision/``;
* ``house`` — IconFlow's own published marks: the website corpus, the
  showcase, the brand mark, the worked examples, and the technique scaffolds.

Only the collision SVGs travel in the wheel. The house half is present as
fields alone: a 16×16 occupancy grid and four scalars, not the artwork.

Usage::

    python scripts/build_collision_index.py            # write the index
    python scripts/build_collision_index.py --check    # fail if it is stale
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from iconflow import neighbours, shapefield  # noqa: E402
from iconflow.config import svg_sha256  # noqa: E402
from iconflow.qa import _LIVE_TEXT_RE  # noqa: E402
from iconflow.rasterize import Rasterizer, load_svg  # noqa: E402

INDEX = ROOT / "iconflow" / "resources" / "collision" / neighbours.INDEX_FILE
GENERATOR = "scripts/build_collision_index.py"

#: (set, id prefix, glob) — every file the index covers, in a fixed order.
SOURCES: tuple[tuple[str, str, str], ...] = (
    ("collision", "", "iconflow/resources/collision/*.svg"),
    ("house", "gallery", "website/assets/gallery/*/master.svg"),
    ("house", "emoji-matrix", "website/assets/gallery/emoji-matrix/*/*/master.svg"),
    ("house", "social-signals", "website/assets/gallery/social-signals/*/master.svg"),
    ("house", "archive", "website/assets/archive/*/*.svg"),
    ("house", "worlds", "website/assets/worlds/*.svg"),
    ("house", "styles", "website/assets/styles/*.svg"),
    ("house", "site", "website/assets/*.svg"),
    ("house", "showcase", "showcase/*/master.svg"),
    ("house", "brand", "brand/master.svg"),
    ("house", "examples", "examples/*/master.svg"),
    ("house", "presets", "templates/presets/*.svg"),
    ("house", "templates", "templates/master.svg"),
)

#: Two bounds decide whether a rebuilt field still *is* the committed one.
#: Per cell: a renderer on another platform may move up to two anti-aliased
#: pixels of a 4x4 block (2/16 = 0.125) before the cell is called different.
#: In aggregate: the normalised distance between the two fields must stay
#: below a quarter of the collision radius, because a per-cell bound alone
#: does not bound the sum — a hairline shifted one pixel everywhere moves
#: every cell a little and the whole grid a lot. Topology is compared in the
#: buckets the gate uses (1/2/3+ pieces, 0/1/2+ holes), which is the only
#: form of it that can change a verdict.
CELL_TOLERANCE = 2 / shapefield.CELL_STEPS + 1e-9
FIELD_TOLERANCE = 0.03
#: Topology classes are renderer-sensitive at the margin — a counter that is
#: one cell wide on one platform's anti-aliasing and closed on another's —
#: so a fresh build is allowed to flip this share of entries and still be the
#: same index. A larger shift is systematic (a changed floor, a changed
#: renderer) and means the index must be rebuilt.
TOPOLOGY_FLIP_SHARE = 0.01


def entry_id(set_name: str, prefix: str, path: Path) -> str:
    relative = path.relative_to(ROOT)
    if set_name == "collision":
        return f"collision/{path.stem}"
    if path.name == "master.svg":
        name = path.parent.name
    else:
        name = path.stem
    if prefix == "archive":
        name = f"{path.parent.name}/{name}"
    elif prefix == "emoji-matrix":
        name = f"{path.parent.parent.name}/{name}"
    return f"house/{prefix}/{name}" if prefix else f"house/{relative.as_posix()}"


def sources() -> list[tuple[str, str, Path]]:
    """Every indexable source, in a fixed order.

    A source with a live ``<text>`` element is skipped: it renders through
    whichever fonts the build machine has, so no two machines would agree on
    its field — the same reason ``qa.py`` flags it. The base template is the
    one such file in the corpus.
    """
    found: list[tuple[str, str, Path]] = []
    seen: set[Path] = set()
    for set_name, prefix, pattern in SOURCES:
        for path in sorted(ROOT.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            if _LIVE_TEXT_RE.search(path.read_text(encoding="utf-8", errors="replace")):
                continue
            found.append((set_name, prefix, path))
    return found


def build(rasterizer: Rasterizer) -> list[neighbours.Entry]:
    entries: list[neighbours.Entry] = []
    for set_name, prefix, path in sources():
        text = load_svg(path)
        entries.append(neighbours.Entry(
            id=entry_id(set_name, prefix, path),
            set=set_name,
            title=neighbours.svg_title(text, path.parent.name if path.name == "master.svg" else path.stem),
            source=path.relative_to(ROOT).as_posix(),
            source_sha256=svg_sha256(path),
            field=shapefield.field_from_svg(text, rasterizer),
        ))
    ids = [entry.id for entry in entries]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SystemExit(f"duplicate index ids: {', '.join(duplicates)}")
    return entries


def render_index(entries: list[neighbours.Entry]) -> str:
    return json.dumps(
        neighbours.index_dict(entries, generator=GENERATOR),
        ensure_ascii=False, indent=1,
    ) + "\n"


def check_sources(index: neighbours.Index) -> list[str]:
    """Browser-free drift check: every entry's source still hashes the same.

    This is the half of ``--check`` the default test matrix can run. A source
    edited without rebuilding the index is caught here; a renderer that draws
    the same source differently is caught by :func:`check_fields`.
    """
    problems: list[str] = []
    expected = {entry_id(s, p, path): path for s, p, path in sources()}
    listed = {entry.id: entry for entry in index.entries}
    for missing in sorted(set(expected) - set(listed)):
        problems.append(f"{missing}: source exists but is not in the index")
    for extra in sorted(set(listed) - set(expected)):
        problems.append(f"{extra}: in the index but its source is gone")
    for entry_id_, path in sorted(expected.items()):
        entry = listed.get(entry_id_)
        if entry is None:
            continue
        if entry.source != path.relative_to(ROOT).as_posix():
            problems.append(f"{entry_id_}: source path changed")
        if entry.source_sha256 != svg_sha256(path):
            problems.append(f"{entry_id_}: source changed since the index was built")
    return problems


def topology_flips(index: neighbours.Index, fresh: list[neighbours.Entry]) -> list[str]:
    """Entries whose topology class a fresh build disagrees with — notes, not failures."""
    listed = {entry.id: entry for entry in index.entries}
    flips: list[str] = []
    for entry in fresh:
        old = listed.get(entry.id)
        if old is None:
            continue
        if shapefield.topology_bucket(old.field) != shapefield.topology_bucket(entry.field):
            flips.append(
                f"{entry.id}: topology class differs on this renderer "
                f"({old.field.components}c/{old.field.holes}h -> "
                f"{entry.field.components}c/{entry.field.holes}h)"
            )
    return flips


def check_fields(index: neighbours.Index, fresh: list[neighbours.Entry]) -> list[str]:
    """Rendered drift check: a fresh build reproduces every field within tolerance.

    Per-cell and aggregate drift are hard bounds. Topology-class flips are
    counted rather than failed one by one: at the margin they are a property
    of the instrument on different anti-aliasing, and only a systematic share
    of them says the index is stale.
    """
    problems: list[str] = []
    listed = {entry.id: entry for entry in index.entries}
    for entry in fresh:
        old = listed.get(entry.id)
        if old is None:
            continue
        worst = max(abs(a - b) for a, b in zip(old.field.grid, entry.field.grid))
        if worst > CELL_TOLERANCE:
            problems.append(f"{entry.id}: a grid cell moved by {worst:.3f}")
        drift = shapefield.grid_distance(old.field.grid, entry.field.grid)
        if drift > FIELD_TOLERANCE:
            problems.append(f"{entry.id}: the field drifted {drift:.3f} in aggregate")
    flips = topology_flips(index, fresh)
    if fresh and len(flips) / len(fresh) > TOPOLOGY_FLIP_SHARE:
        problems.append(
            f"{len(flips)} of {len(fresh)} entries changed topology class "
            f"(more than {TOPOLOGY_FLIP_SHARE:.0%}): the index is from a different "
            "instrument, not a different renderer"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--check", action="store_true",
                        help="rebuild in memory and fail if the committed index drifted")
    parser.add_argument("--sources-only", action="store_true",
                        help="with --check: verify source hashes without rendering")
    args = parser.parse_args(argv)

    if args.check:
        index = neighbours.parse_index(INDEX.read_text(encoding="utf-8"))
        problems = check_sources(index)
        if not args.sources_only and not problems:
            with Rasterizer() as rasterizer:
                fresh = build(rasterizer)
            for note in topology_flips(index, fresh):
                print(f"  ~ {note}")
            problems += check_fields(index, fresh)
        if problems:
            for problem in problems:
                print(f"  ! {problem}")
            print(f"neighbourhood index is stale: run python {GENERATOR}")
            return 1
        print(f"neighbourhood index OK: {len(index.entries)} entries match their sources")
        return 0

    with Rasterizer() as rasterizer:
        entries = build(rasterizer)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(render_index(entries), encoding="utf-8", newline="\n")
    by_set = {name: sum(1 for e in entries if e.set == name) for name in neighbours.BUNDLED_SETS}
    print(f"wrote {INDEX.relative_to(ROOT).as_posix()}: "
          + ", ".join(f"{count} {name}" for name, count in by_set.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
