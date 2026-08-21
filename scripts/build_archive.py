# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Build the public Living Archive from the identity-exploration rounds.

The exploration itself lives in the gitignored ``work/iconflow-logo-refresh``
tree. This script promotes the authored SVG directions into tracked website
assets (``website/assets/archive``), renders an exact 16px proof for each one,
writes ``catalog.json``, regenerates ``website/archive/index.html`` and the
marquee/finalist blocks on the homepage between marker comments.

Run it from the repository root::

    .venv\\Scripts\\python.exe scripts/build_archive.py            # rebuild
    .venv\\Scripts\\python.exe scripts/build_archive.py --verify-only

``--verify-only`` rechecks the tracked catalog, assets, and generated HTML
without touching ``work/``; it is what a clean clone can run.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "iconflow-logo-refresh"
ASSETS = ROOT / "website" / "assets" / "archive"
CATALOG = ASSETS / "catalog.json"
ARCHIVE_PAGE = ROOT / "website" / "archive" / "index.html"
HOME_PAGE = ROOT / "website" / "index.html"
SELECTION = WORK / "selection-catalog.json"

# Public round order. ``dir`` is relative to WORK; ``extra`` adds second-pass
# redraws that live in a subdirectory and get a suffix so slugs stay unique.
ROUNDS = [
    {"id": "machines", "label": "Proof machines", "dir": ".", "docs": ["concepts.md"],
     "lede": "Ten measurement, press, and proofing objects: the first attempt to draw proof at the last sixteen pixels."},
    {"id": "living-care", "label": "Living care", "dir": "round-2-heart-animals", "docs": ["concepts.md"],
     "extra": {"dir": "selection", "suffix": "-refined", "note": "Second-pass redraw of a Living-care direction."},
     "lede": "A living noun first, a caring action second, and IconFlow rigor hidden in the reduction quality."},
    {"id": "expanded-living", "label": "Expanded living", "dir": "round-3-expanded-living", "docs": ["concepts.md"],
     "lede": "Makers, collectors, guides, shelters, and structural hearts; one behaviour changes the outer silhouette."},
    {"id": "hidden-brand", "label": "Hidden brand", "dir": "round-4-hidden-brand", "docs": ["concept-synthesis.md"],
     "lede": "The animal's real anatomy performs the product truth: a repeated master, a continuous route, a held proof."},
    {"id": "orchard-garden", "label": "Orchard & garden", "dir": "round-5-orchard-garden", "docs": ["concepts.md"],
     "lede": "Fruits and vegetables whose crowns, peels, pods, and seams carry one family from one source."},
    {"id": "canopy-cargo", "label": "Canopy cargo", "dir": "round-6-canopy-cargo", "docs": ["concepts.md"],
     "extra": {"dir": "finalists", "suffix": "-finalist", "note": "Finalist redraw under the same leaf canopy."},
     "lede": "One approved leaf canopy, seven different payloads, and the question of what the cargo says about craft."},
    {"id": "organic-neko", "label": "Organic neko", "dir": "round-8-organic-neko", "docs": ["concepts.md"],
     "lede": "A cat, a tomato, and a leaf drawn as one gesture; motion from anatomy, never from cords."},
]

# Directions that passed the complete draft-local target gate, or were promoted.
# Scores are legibility / distinctiveness / balance / color / scalability / craft.
PROMOTED = {
    "organic-neko/taildraft-pounce": {"status": "promoted", "scores": [4, 5, 4, 5, 4, 4],
                                      "name": "Tailwind Chomp", "note": "Promoted locally from the organic-neko round."},
    "expanded-living/petal-haypile": {"status": "production", "scores": [4, 5, 4, 5, 4, 4],
                                      "source": ROOT / "brand" / "master.svg",
                                      "note": "The temporary IconFlow product mark since 2026-08-14: a low-eared pika returns to its hay store carrying three oversized petals."},
}

# Hand-written readings for redraws whose concept notes live elsewhere.
STORIES = {
    "living-care/frill-friend-refined": "An axolotl whose external gills become six fat crown leaves; the strongest original-character and illustration-family potential of the round.",
    "living-care/mender-cat-refined": "A curled cat holds one repair patch between its paws; the warmest direct story of caring for and repairing the source.",
    "living-care/acorn-mouse-refined": "A dormouse ear and tail break through an acorn cup, redrawn so the cup and the animal read as one silhouette.",
    "living-care/otter-embrace-refined": "A supine sea otter cups one coral heart-pebble; redrawn with a broader paddle tail and a single held stone.",
    "living-care/heart-curl-fox-refined": "A sleeping fox wraps one enormous tail around a teal heart-leaf; redrawn, then set aside because the fox named a fox brand before IconFlow.",
    "living-care/heartwing-moth-refined": "Two broad moth wings close into one heart-shaped night companion; redrawn, then set aside because it named a heart before a moth.",
    "living-care/hoopoe-gift-refined": "A fan-crested hoopoe leans toward a nest opening; the crest and bill create an unmistakable silhouette.",
    "canopy-cargo/tomato-proof-chute-finalist": "A plump tomato hangs under the leaf canopy with one broad square edge bay cut into the fruit: an integrated 16px proof cue, not an icon inside an icon.",
    "canopy-cargo/watermelon-gondola-finalist": "A watermelon wedge becomes the gondola under the leaf canopy; rind and two broad seeds keep the fruit noun while the scene reads as a ferry.",
    "canopy-cargo/neko-parachute-finalist": "A compact cat hangs below the canopy; ears own the noun and a single curled tail carries the motion.",
    "hidden-brand/fiddle-fin": "An organic F rhythm that still reads bird-and-fern first.",
}
SELECTION_ROUND = {2: "living-care", 3: "expanded-living", 4: "hidden-brand", 5: "orchard-garden", 6: "canopy-cargo"}
SELECTION_SOURCE_OVERRIDES = {"round-6-canopy-cargo/master.svg": "canopy-cargo/tomato-proof-chute-finalist"}

MARQUEE_START = "<!-- archive-marquee:start -->"
MARQUEE_END = "<!-- archive-marquee:end -->"
FINALISTS_START = "<!-- archive-finalists:start -->"
FINALISTS_END = "<!-- archive-finalists:end -->"


def letters(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def strip_prefix(stem: str) -> str:
    return re.sub(r"^[a-z]{1,2}-", "", stem)


def title_from_slug(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.split("-"))


def clean_markdown(text: str) -> str:
    text = re.sub(r"\*\*|`", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_stories(round_dir: Path, docs: list[str]) -> dict[str, str]:
    """Map letters-only name -> one-line story, from the round's concept notes."""
    stories: dict[str, str] = {}
    for name in docs:
        path = round_dir / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        # "1. **Name** — story" or "1. **Name — lens.** story" (may span lines)
        for match in re.finditer(r"^\s*\d+\.\s+\*\*(?P<name>[^*]+?)\*\*\s*(?P<body>.+?)(?=^\s*\d+\.\s+\*\*|^##|\Z)",
                                 text, flags=re.S | re.M):
            raw_name = match.group("name")
            raw_name = raw_name.split(" — ")[0]
            story = clean_markdown(match.group("body"))
            story = re.sub(r"^[—–-]\s*", "", story)
            stories.setdefault(letters(raw_name), story)
        # "- Name — story;"
        for match in re.finditer(r"^- (?P<name>[A-Z][A-Za-z' ]+?) — (?P<body>.+?);?$", text, flags=re.M):
            stories.setdefault(letters(match.group("name")), clean_markdown(match.group("body")))
    return stories


def first_sentences(story: str, limit: int = 190) -> str:
    story = story.strip()
    if not story:
        return ""
    # Drop trailing "Risk:" clauses; keep the reading, not the worry.
    story = re.split(r"\s(?:Risk|Open cost)\s*:", story)[0].strip()
    if len(story) <= limit:
        return story.rstrip(";") + ("" if story.endswith(".") else ".")
    cut = story[:limit]
    cut = cut[: max(cut.rfind(". "), cut.rfind("; "), cut.rfind(", "))] if any(s in cut for s in (". ", "; ", ", ")) else cut
    return cut.rstrip(" ,;.") + "."


def load_selection() -> dict[str, dict]:
    if not SELECTION.is_file():
        return {}
    data = json.loads(SELECTION.read_text(encoding="utf-8"))
    gated: dict[str, dict] = {}
    for entry in data.get("finalists", []):
        source = entry["source"]
        if source in SELECTION_SOURCE_OVERRIDES:
            key = SELECTION_SOURCE_OVERRIDES[source]
        else:
            round_id = SELECTION_ROUND[entry["round"]]
            stem = Path(source).stem
            suffix = "-refined" if "/selection/" in source else ""
            key = f"{round_id}/{strip_prefix(stem)}{suffix}"
        scores = entry["scores"]
        gated[key] = {"status": "gated", "name": entry["name"],
                      "scores": [scores[k] for k in ("legibility", "distinctiveness", "balance", "color", "scalability", "craft")]}
    return gated


def collect() -> list[dict]:
    from iconflow.rasterize import load_svg

    gated = load_selection()
    entries: list[dict] = []
    for round_index, spec in enumerate(ROUNDS, start=1):
        round_dir = WORK / spec["dir"]
        stories = parse_stories(round_dir, spec["docs"])
        sources = [(p, "", "") for p in sorted(round_dir.glob("*.svg")) if p.name not in ("master.svg", "tray.svg")]
        if spec["id"] == "organic-neko" and (round_dir / "master.svg").is_file():
            pass  # the promoted master is the taildraft-pounce redraw; keep the first-pass source for the grid
        extra = spec.get("extra")
        if extra:
            for p in sorted((round_dir / extra["dir"]).glob("*.svg")):
                if p.name not in ("master.svg", "tray.svg"):
                    sources.append((p, extra["suffix"], extra["note"]))
        for path, suffix, note in sources:
            slug = strip_prefix(path.stem) + suffix
            key = f"{spec['id']}/{slug}"
            name = title_from_slug(strip_prefix(path.stem))
            story = stories.get(letters(name), "")

            meta = {"status": "study", "scores": None}
            if key in gated:
                meta = dict(gated[key])
                name = meta.pop("name", name)
            if key in PROMOTED:
                meta = dict(PROMOTED[key])
                name = meta.pop("name", name)
                note = meta.pop("note", note)
                path = meta.pop("source", path)
            if key in STORIES:
                story = STORIES[key]
            elif not story and note:
                story = note
            if key in PROMOTED and note:
                story = note
            if story:
                story = story[0].upper() + story[1:]
            svg = load_svg(path)  # validates size/structure like every other IconFlow input
            entries.append({
                "id": key.replace("/", "-"),
                "round": spec["id"],
                "roundIndex": round_index,
                "roundLabel": spec["label"],
                "slug": slug,
                "name": name,
                "story": first_sentences(story) if story else "",
                "status": meta["status"],
                "scores": meta.get("scores"),
                "svg": f"/assets/archive/{spec['id']}/{slug}.svg",
                "proof16": f"/assets/archive/{spec['id']}/{slug}-16.png",
                "_source": path,
                "_svg_text": svg,
            })
    # Disambiguate a refined redraw only when its round still holds the original name.
    seen: dict[tuple[str, str], int] = {}
    for entry in entries:
        seen[(entry["round"], entry["name"])] = seen.get((entry["round"], entry["name"]), 0) + 1
    for entry in entries:
        if seen[(entry["round"], entry["name"])] > 1 and entry["slug"].endswith("-refined"):
            entry["name"] += " (refined)"
    return entries


# Provenance stamped into every published study. Two outcomes and both are
# useful: a copy that keeps it identifies itself, and a copy that strips it has
# removed an attribution notice deliberately. See docs/PROVENANCE.md.
PROVENANCE_MARK = "iconflow:provenance"
LICENSE_URI = "http://creativecommons.org/licenses/by-nc-nd/4.0/"


def provenance_block(entry: dict) -> str:
    """RDF metadata naming the work, its author, licence, and canonical URL."""

    return (
        f'  <metadata id="{PROVENANCE_MARK}">\n'
        '    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:cc="http://creativecommons.org/ns#">\n'
        f'      <cc:Work rdf:about="https://ai-iconflow.com/archive/#{esc(entry["id"])}">\n'
        f'        <dc:title>{esc(entry["name"])}</dc:title>\n'
        '        <dc:creator><cc:Agent><dc:title>snowyukitty</dc:title></cc:Agent></dc:creator>\n'
        '        <dc:source>https://ai-iconflow.com/archive/</dc:source>\n'
        '        <dc:rights>Copyright 2026 snowyukitty. IconFlow Living Archive.</dc:rights>\n'
        f'        <cc:license rdf:resource="{LICENSE_URI}"/>\n'
        '      </cc:Work>\n'
        '    </rdf:RDF>\n'
        '  </metadata>\n'
    )


def strip_provenance(svg: str) -> str:
    """Inverse of :func:`stamp_provenance`.

    The production entry is hash-bound to ``brand/master.svg`` so the site can
    never show a mark the brand receipt did not approve. That binding is about
    the drawing, not the licence block, so a comparison strips this first.
    """

    start = svg.find(f'<metadata id="{PROVENANCE_MARK}"')
    if start == -1:
        return svg
    end = svg.find("</metadata>", start)
    if end == -1:
        raise ValueError("unterminated provenance metadata")
    end += len("</metadata>")
    head = svg[:start].rstrip(" ")
    tail = svg[end:].lstrip("\n")
    return f"{head}{tail}"


def stamp_provenance(svg: str, entry: dict) -> str:
    """Insert the provenance block right after the opening <svg> element.

    Idempotent, and it never touches geometry, so the rendered pixels and every
    proof already published stay byte-identical.
    """

    if PROVENANCE_MARK in svg:
        return svg
    opening = svg.find(">", svg.find("<svg"))
    if opening == -1:
        raise ValueError(f"{entry['slug']}: no <svg> element to stamp")
    head, rest = svg[: opening + 1], svg[opening + 1 :]
    return f"{head}\n{provenance_block(entry)}{rest.lstrip(chr(10))}"


def render_assets(entries: list[dict]) -> None:
    from iconflow.rasterize import Rasterizer

    with Rasterizer() as rasterizer:
        for entry in entries:
            out_dir = ASSETS / entry["round"]
            out_dir.mkdir(parents=True, exist_ok=True)
            svg_out = out_dir / f"{entry['slug']}.svg"
            stamped = stamp_provenance(
                entry["_svg_text"].replace("\r\n", "\n"), entry
            )
            svg_out.write_text(stamped, encoding="utf-8", newline="\n")
            png = rasterizer.render(entry["_svg_text"], 16, bg="transparent")
            (out_dir / f"{entry['slug']}-16.png").write_bytes(png)


def write_catalog(entries: list[dict]) -> dict:
    public = [{k: v for k, v in e.items() if not k.startswith("_")} for e in entries]
    rounds = [{"id": r["id"], "label": r["label"], "lede": r["lede"],
               "count": sum(1 for e in entries if e["round"] == r["id"])} for r in ROUNDS]
    catalog = {
        "schema": 1,
        "title": "IconFlow living archive",
        "note": "Identity-exploration directions authored with IconFlow. 'gated' passed the complete draft-local target gate; 'study' directions were drawn, rendered, and compared but not promoted. None of this is a claim of trademark clearance.",
        "counts": {"directions": len(public),
                   "gated": sum(1 for e in public if e["status"] in ("gated", "promoted", "production")),
                   "rounds": len(rounds)},
        "rounds": rounds,
        "entries": public,
    }
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return catalog


# ---------------------------------------------------------------- HTML pieces

def esc(text: str) -> str:
    return html.escape(text, quote=True)


def marquee_html(catalog: dict) -> str:
    import random

    # Deterministic shuffle so every row mixes rounds and the first visible
    # tiles are not the monochrome machines; the seed keeps rebuilds stable.
    entries = list(catalog["entries"])
    random.Random(20260821).shuffle(entries)
    rows: list[list[dict]] = [[], [], []]
    for index, entry in enumerate(entries):
        rows[index % 3].append(entry)
    out = [MARQUEE_START]
    for row_index, row in enumerate(rows, start=1):
        loading = "eager" if row_index == 1 else "lazy"
        tiles = "".join(
            f'<a class="archive-tile" href="/archive/#{esc(e["id"])}" aria-label="{esc(e["name"])} — open in the archive with its exact 16px proof">'
            f'<img src="{esc(e["svg"])}" width="84" height="84" alt="" loading="{loading}" decoding="async"></a>'
            for e in row
        )
        # One track per row; archive.js clones it for the seamless loop, and the
        # animation only runs under html.js, so the static page stays honest.
        out.append(f'<div class="archive-row archive-row-{row_index}"><div class="archive-track">{tiles}</div></div>')
    out.append(MARQUEE_END)
    return "\n".join(out)


def finalists_html(catalog: dict) -> str:
    picks = [e for e in catalog["entries"] if e["status"] in ("production", "gated", "promoted")]
    order = {"production": 0, "gated": 1, "promoted": 1}
    picks.sort(key=lambda e: (order[e["status"]], e["roundIndex"], e["name"]))
    cards = []
    for e in picks:
        scores = "/".join(str(s) for s in e["scores"]) if e["scores"] else ""
        badge = {"production": "current mark, temporary", "gated": "passed review", "promoted": "promoted"}[e["status"]]
        cards.append(
            f'<a class="finalist-card finalist-{esc(e["status"])}" href="/archive/#{esc(e["id"])}">'
            f'<img src="{esc(e["svg"])}" width="128" height="128" alt="{esc(e["name"])}" loading="lazy">'
            f'<span class="finalist-name">{esc(e["name"])}</span>'
            f'<span class="finalist-meta"><span>{esc(e["roundLabel"])}</span><span>{esc(badge)} · {esc(scores)}</span></span></a>'
        )
    counts = catalog["counts"]
    tally = (f'<p class="archive-tally">{counts["directions"]} directions · {counts["rounds"]} rounds · '
             f'{counts["gated"]} passed review or were promoted, including the current temporary mark</p>')
    return "\n".join([FINALISTS_START, tally, '<div class="finalist-strip">', *cards, "</div>", FINALISTS_END])


def splice(document: str, start: str, end: str, block: str) -> str:
    head, rest = document.split(start, 1)
    _, tail = rest.split(end, 1)
    return head + block + tail


HERO_PICKS = [
    "hidden-brand-leaf-ferry", "orchard-garden-pea-pod-parade", "living-care-koi-heart-refined", "expanded-living-mandarin-sail",
    "orchard-garden-citrus-peelway", "hidden-brand-beak-ledger", "living-care-mender-cat-refined", "organic-neko-taildraft-pounce",
    "orchard-garden-mangosteen-keeper", "hidden-brand-otter-proof", "expanded-living-fairy-scoop", "canopy-cargo-neko-parachute-finalist",
    "orchard-garden-radish-route", "expanded-living-deep-canopy", "living-care-frill-friend-refined", "expanded-living-petal-haypile",
]


def hero_mosaic_html(catalog: dict) -> str:
    by_id = {e["id"]: e for e in catalog["entries"]}
    tiles = []
    for index, pick in enumerate(HERO_PICKS, start=1):
        e = by_id.get(pick)
        if not e:
            continue
        tiles.append(f'<a class="hero-mosaic-tile tile-{index}" href="#{esc(e["id"])}" tabindex="-1">'
                     f'<img src="{esc(e["svg"])}" width="120" height="120" alt="" loading="lazy"></a>')
    return "\n".join(tiles)


def archive_page(catalog: dict) -> str:
    rounds = catalog["rounds"]
    entries = catalog["entries"]
    chips = ['<button type="button" class="chip is-active" data-filter="all" aria-pressed="true">All</button>',
             '<button type="button" class="chip" data-filter="gated" aria-pressed="false">Passed review</button>']
    chips += [f'<button type="button" class="chip" data-filter="{esc(r["id"])}" aria-pressed="false">{esc(r["label"])}</button>' for r in rounds]
    cards = []
    for e in entries:
        scores = "/".join(str(s) for s in e["scores"]) if e["scores"] else ""
        status_label = {"production": "Current mark (temporary)", "gated": "Passed review", "promoted": "Promoted locally", "study": "Study"}[e["status"]]
        gated_attr = "true" if e["status"] != "study" else "false"
        story = f'<p>{esc(e["story"])}</p>' if e["story"] else ""
        score_html = f'<span class="card-scores" title="legibility / distinctiveness / balance / color / scalability / craft">{esc(scores)}</span>' if scores else ""
        cards.append(
            f'<article class="archive-card status-{esc(e["status"])}" id="{esc(e["id"])}" data-round="{esc(e["round"])}" data-gated="{gated_attr}" tabindex="0" role="button" aria-haspopup="dialog" aria-label="{esc(e["name"])} — open details">'
            f'<div class="card-visual"><img src="{esc(e["svg"])}" width="160" height="160" alt="{esc(e["name"])}" loading="lazy"></div>'
            f'<div class="card-copy"><span class="card-round">{esc(e["roundLabel"])}</span><h3>{esc(e["name"])}</h3>{story}'
            f'<div class="card-foot"><span class="card-status">{esc(status_label)}</span>{score_html}'
            f'<span class="card-native"><img src="{esc(e["proof16"])}" width="16" height="16" alt="">16px</span>'
            f'<a class="card-source" href="{esc(e["svg"])}">SVG</a></div></div></article>'
        )
    round_sections = []
    for r in rounds:
        round_sections.append(
            f'<section class="archive-round" data-round-section="{esc(r["id"])}"><div class="round-head">'
            f'<h2>{esc(r["label"])}</h2><p>{esc(r["lede"])}</p><span>{r["count"]} directions</span></div>'
            f'<div class="archive-grid">' + "".join(c for c, e in zip(cards, entries) if e["round"] == r["id"]) + "</div></section>"
        )
    counts = catalog["counts"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IconFlow Living Archive — {counts["directions"]} identity directions</title>
  <meta name="description" content="Every identity direction IconFlow drew while searching for its own mark: {counts["directions"]} original SVG studies across {counts["rounds"]} rounds, with exact 16px proofs, gated finalists, and the temporary product mark.">
  <meta name="theme-color" content="#191a20">
  <meta name="color-scheme" content="dark">
  <meta property="og:type" content="website">
  <meta property="og:title" content="IconFlow Living Archive">
  <meta property="og:description" content="{counts["directions"]} original identity directions, {counts["gated"]} gated, one temporary mark — all drawn, rendered, and compared with the IconFlow method.">
  <meta property="og:url" content="https://ai-iconflow.com/archive/">
  <meta property="og:image" content="https://ai-iconflow.com/assets/social-preview.png?v=petal">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="https://ai-iconflow.com/archive/">
  <!-- i18n:alternates -->
  <!-- /i18n:alternates -->
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <link rel="stylesheet" href="/styles.css?v=20260821c">
  <link rel="stylesheet" href="/archive.css?v=20260821c">
  <script type="application/ld+json">
  {{
   "@context": "https://schema.org",
   "@type": "CollectionPage",
   "name": "IconFlow Living Archive",
   "url": "https://ai-iconflow.com/archive/",
   "description": "Original identity directions drawn with the IconFlow method, with exact 16px proofs.",
   "isPartOf": {{ "@id": "https://ai-iconflow.com/#website" }}
  }}
  </script>
  <script src="/app.js?v=20260821c" defer></script>
  <script src="/archive.js?v=20260821c" defer></script>
</head>
<body class="archive-body">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header" data-header>
    <a class="brand" href="/" aria-label="IconFlow home">
      <img src="/assets/iconflow-mark.svg" width="34" height="34" alt="">
      <span>IconFlow</span>
    </a>
    <button class="menu-button" type="button" aria-expanded="false" aria-controls="site-nav" data-menu data-label-open="Open navigation" data-label-close="Close navigation">
      <span class="sr-only">Toggle navigation</span>
      <span></span><span></span>
    </button>
    <nav id="site-nav" class="site-nav" aria-label="Primary navigation">
      <a href="#finalists">Passed review</a>
      <a href="#rounds">Rounds</a>
      <a href="/gallery/">Gallery</a>
      <a href="/how-icons-are-made/">Method</a>
      <a href="/getting-started/">Get started</a>
      <a href="https://github.com/snowyukitty/ai-iconflow" target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
    </nav>
    <!-- i18n:switch --><!-- /i18n:switch -->
  </header>

  <main id="main">
    <section class="archive-hero section-shell">
      <div class="archive-hero-copy reveal">
        <p class="eyebrow"><span class="status-dot"></span> The living archive · identity exploration</p>
        <h1>{counts["directions"]} marks.<br>One method.<br><em>Every pixel kept.</em></h1>
        <p class="hero-lede">While IconFlow looked for its own logo it drew {counts["directions"]} original directions across {counts["rounds"]} rounds — machines, companions, hidden-brand anatomy, an orchard, a canopy, a cat. Each one was rendered by the same engine, compared at native size, and either passed review or was kept as an honest study. Nothing here is a stock asset; nothing here claims trademark clearance.</p>
        <dl class="hero-stats" aria-label="Archive facts">
          <div><dt>{counts["directions"]}</dt><dd>directions drawn</dd></div>
          <div><dt>{counts["gated"]}</dt><dd>passed review</dd></div>
          <div><dt>1</dt><dd>temporary product mark</dd></div>
        </dl>
      </div>
      <div class="archive-hero-visual reveal" aria-hidden="true">
{hero_mosaic_html(catalog)}
      </div>
      <div class="archive-filters reveal" role="group" aria-label="Filter the archive">
        {"".join(chips)}
        <span class="filter-count" data-filter-count aria-live="polite" data-label-shown="{{count}} shown">{counts["directions"]} shown</span>
      </div>
    </section>

    <section id="finalists" class="section-shell archive-finalists reveal">
      <div class="round-head"><h2>The ones that passed review, and the current mark</h2><p>Each of these passed the complete draft-local target gate: clean <code>check</code>, static review, exact color tray and alpha template, a receipt bound to the SVG hash, and <code>ship</code> with every rubric axis at 4/5 or better (legibility / distinctiveness / balance / color / scalability / craft).</p></div>
{finalists_html(catalog).replace(FINALISTS_START, "").replace(FINALISTS_END, "")}
    </section>

    <div id="rounds" class="section-shell archive-rounds">
{"".join(round_sections)}
    </div>

    <section class="section-shell archive-foot reveal">
      <p>Want your own? The <a href="/#remix">Remix Lab</a> lets you bend the current mark in the browser; <a href="/getting-started/">Getting started</a> runs the whole gated loop on your machine; <a href="/how-icons-are-made/">How icons are made</a> explains every stage these marks went through.</p>
    </section>
  </main>

  <dialog class="archive-dialog" data-archive-dialog>
    <form method="dialog"><button type="submit" aria-label="Close">Close <span aria-hidden="true">×</span></button></form>
    <div class="dialog-body">
      <div class="dialog-visual"><img data-dialog-img src="/assets/iconflow-mark.svg" width="320" height="320" alt=""></div>
      <div class="dialog-copy">
        <span class="card-round" data-dialog-round></span>
        <h2 data-dialog-name></h2>
        <p data-dialog-story></p>
        <p class="dialog-meta"><span data-dialog-status></span> <span data-dialog-scores data-label-axes="(legibility / distinctiveness / balance / color / scalability / craft)"></span></p>
        <p class="dialog-native"><img data-dialog-proof src="/assets/proof/icon-16.png?v=petal" width="16" height="16" alt="">exact 16px · <a data-dialog-source href="/assets/iconflow-mark.svg">download the SVG</a></p>
      </div>
    </div>
  </dialog>

  <footer class="site-footer section-shell">
    <div class="footer-brand"><img src="/assets/iconflow-mark.svg" width="40" height="40" alt=""><div><strong>IconFlow</strong><span>One master. Every surface.</span></div></div>
    <p>Apache-2.0 code · archive artwork is IconFlow identity material, subject to the trademark policy.</p>
    <nav aria-label="Footer navigation"><a href="/">Home</a><a href="/gallery/">Gallery</a><a href="/how-icons-are-made/">How it's made</a><a href="https://github.com/snowyukitty/ai-iconflow/blob/main/TRADEMARKS.md">Trademark</a><a href="https://github.com/snowyukitty/ai-iconflow">Source</a></nav>
    <!-- i18n:switch --><!-- /i18n:switch -->
  </footer>
</body>
</html>
"""


def write_html(catalog: dict) -> None:
    ARCHIVE_PAGE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PAGE.write_text(archive_page(catalog), encoding="utf-8", newline="\n")
    home = HOME_PAGE.read_text(encoding="utf-8")
    home = splice(home, MARQUEE_START, MARQUEE_END, marquee_html(catalog))
    home = splice(home, FINALISTS_START, FINALISTS_END, finalists_html(catalog))
    HOME_PAGE.write_text(home, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------- verify

def verify() -> int:
    problems: list[str] = []
    if not CATALOG.is_file():
        print("archive catalog missing", file=sys.stderr)
        return 1
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = catalog["entries"]
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        problems.append("duplicate ids in catalog")
    for e in entries:
        for key in ("svg", "proof16"):
            path = ROOT / "website" / e[key].lstrip("/")
            if not path.is_file():
                problems.append(f"missing {e[key]}")
            elif key == "svg" and PROVENANCE_MARK not in path.read_text(encoding="utf-8"):
                # A published study without its licence metadata is a study that
                # cannot identify itself once copied (docs/PROVENANCE.md).
                problems.append(f"{e['id']} is missing its provenance metadata")
        if e["status"] != "study" and (not e["scores"] or len(e["scores"]) != 6 or min(e["scores"]) < 4):
            problems.append(f"{e['id']} is {e['status']} without six scores >= 4")
        if e["status"] not in ("study", "gated", "promoted", "production"):
            problems.append(f"{e['id']} has unknown status {e['status']}")
    if catalog["counts"]["directions"] != len(entries):
        problems.append("counts.directions disagrees with entries")
    if sum(1 for e in entries if e["status"] == "production") != 1:
        problems.append("exactly one production entry expected")
    home = HOME_PAGE.read_text(encoding="utf-8")
    if MARQUEE_START not in home or FINALISTS_START not in home:
        problems.append("homepage markers missing")
    else:
        marquee = home.split(MARQUEE_START, 1)[1].split(MARQUEE_END, 1)[0]
        for e in entries:
            if marquee.count(f'href="/archive/#{e["id"]}"') != 1:
                problems.append(f"{e['id']} not in homepage marquee exactly once")
    page = ARCHIVE_PAGE.read_text(encoding="utf-8") if ARCHIVE_PAGE.is_file() else ""
    for e in entries:
        if f'id="{e["id"]}"' not in page:
            problems.append(f"{e['id']} missing from archive page")
    for problem in problems[:40]:
        print("archive verify:", problem, file=sys.stderr)
    if problems:
        print(f"archive verify: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"archive verify: OK — {len(entries)} directions, {catalog['counts']['gated']} gated/promoted, {catalog['counts']['rounds']} rounds")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verify-only", action="store_true", help="check tracked outputs without reading work/")
    args = parser.parse_args()
    if args.verify_only:
        return verify()
    if not WORK.is_dir():
        print(f"exploration archive not found at {WORK}", file=sys.stderr)
        return 1
    entries = collect()
    render_assets(entries)
    catalog = write_catalog(entries)
    write_html(catalog)
    print(f"archive: {len(entries)} directions -> {ASSETS.relative_to(ROOT)}, {ARCHIVE_PAGE.relative_to(ROOT)}, homepage blocks")
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
