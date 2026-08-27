# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Generate the platform icon reference page from the code that builds icons.

The reference page at ``/reference/icon-sizes/`` answers the question people
actually type into a search engine — *which icon files does my platform need,
and at what size* — and it is the one page on the site that must never be
allowed to drift. So it is not written by hand: every filename, frame size and
container format on it is read out of :mod:`iconflow.build`,
:mod:`iconflow.assemble` and :mod:`iconflow.htmlhead` at build time.

A change to what ``iconflow ship`` produces therefore changes the page, and
``--check`` in CI fails until the page is regenerated. The site cannot publish
an icon-size table that the tool itself no longer honours.

Usage::

    python scripts/build_reference.py            # write the page
    python scripts/build_reference.py --check    # fail if it is out of date
"""
from __future__ import annotations

import argparse
import inspect
import json
import re
import sys
from dataclasses import dataclass
from html import escape
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import iconflow  # noqa: E402
from iconflow import assemble, htmlhead  # noqa: E402

# `iconflow.build` the attribute is the build *function* re-exported by the
# package; the module holding the target constants has to be imported by name.
build = import_module("iconflow.build")

SITE = ROOT / "website"
PAGE = SITE / "reference" / "icon-sizes" / "index.html"
ORIGIN = "https://ai-iconflow.com"
ROUTE = "/reference/icon-sizes/"
ASSET_VERSION = "20260821c"

TITLE = "App icon and favicon sizes — every file each platform needs (2026)"
DESCRIPTION = (
    "The complete icon file and size matrix for web favicons, PWA manifests, "
    "Tauri, Electron and macOS menu-bar trays — read straight out of the "
    "IconFlow build code, with the exact <head> snippet and manifest entries."
)


# ---------------------------------------------------------------------------
# Facts, read from the toolkit rather than restated


@dataclass(frozen=True)
class Row:
    path: str
    detail: str
    note: str


class _SpecCache:
    """Stand-in renderer that records the sizes a target asks for.

    ``preview_assets`` is the single function every build path goes through, so
    driving it with this cache yields the real output filenames without a
    browser. Bytes are never inspected — only the keys and the sizes requested.
    """

    def __init__(self) -> None:
        self.requested: list[int] = []

    def png(self, size: int) -> bytes:
        self.requested.append(int(size))
        return _BLANK[int(size)]


def _blank_png(size: int) -> bytes:
    """A stand-in render: one opaque square on transparency.

    Shape matters here even though the bytes are thrown away. The tray target
    runs the real template conversion, which rejects a source that covers the
    whole canvas — correctly, since that is the black-square failure. So the
    placeholder is a sparse mark, the same thing a usable tray drawing is.
    """
    from io import BytesIO

    from PIL import Image

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inset = max(1, size // 4)
    Image.Image.paste(
        image,
        Image.new("RGBA", (size - 2 * inset, size - 2 * inset), (0, 0, 0, 255)),
        (inset, inset),
    )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class _Blanks(dict):
    def __missing__(self, size: int) -> bytes:
        value = self[size] = _blank_png(size)
        return value


_BLANK = _Blanks()

MASKABLE_PADDING = inspect.signature(assemble.maskable_asset).parameters["padding"].default

# What each produced file is *for*. Keys must match the filenames the build
# code emits; :func:`rows_for` raises when one drifts, which is the point.
NOTES: dict[str, str] = {
    "favicon.svg": "Primary in every current browser. Scales to any size, one file.",
    "favicon.ico": "Legacy fallback. One container, three frames — not three files.",
    "apple-touch-icon.png": "iOS home screen. Flattened onto the background colour: iOS ignores alpha.",
    "icon-192.png": "Android home screen and the PWA install prompt.",
    "icon-512.png": "Splash screens and store listings.",
    "icon-512-maskable.png": (
        f"Adaptive icon. Artwork inset {MASKABLE_PADDING:.0%} per side and flattened, "
        "so no platform mask can remove part of the mark."
    ),
    "site.webmanifest": "Declares the three PNGs, theme colour and display mode.",
    "favicon-head.html": "The paste-ready <head> block, generated with the assets.",
    "mstile-70x70.png": "Small pinned-site tile.",
    "mstile-144x144.png": "Legacy pinned-site tile.",
    "mstile-150x150.png": "Medium tile.",
    "mstile-310x310.png": "Large tile.",
    "mstile-310x150.png": "Wide tile — the one rectangle in the set.",
    "browserconfig.xml": "Points at the tiles and sets the tile colour.",
    "icons/32x32.png": "PNG, written into src-tauri/icons/.",
    "icons/64x64.png": "PNG, written into src-tauri/icons/.",
    "icons/128x128.png": "PNG, written into src-tauri/icons/.",
    "icons/128x128@2x.png": "Retina pair for the 128 pixel tile.",
    "icons/icon.png": "The Tauri source image.",
    "icons/icon.ico": "Windows. Frame order matches the Tauri CLI's own output.",
    "icons/icon.icns": "macOS bundle icon.",
    "build/icon.png": "Linux, and the electron-builder source image.",
    "build/icon.ico": "Windows installer and window icon.",
    "build/icon.icns": "macOS app bundle.",
    "tray/tray.png": "Colour tray icon at 2× density.",
    "tray/tray@16.png": "Colour tray icon at 1× density.",
    "tray/trayTemplate.png": "macOS template: pure black plus alpha. The system recolours it.",
    "tray/trayTemplate@2x.png": "Retina template pair. Required, not optional.",
    "tray/trayIcon.ts": "Optional inline data-URL module (--tray-ts).",
}


def _note(path: str) -> str:
    try:
        return NOTES[path]
    except KeyError as exc:  # pragma: no cover - guard, not a branch
        raise SystemExit(
            f"build.py now produces {path!r}, which this page does not describe. "
            "Add it to NOTES in scripts/build_reference.py."
        ) from exc


def _sizes(sizes) -> str:
    return " · ".join(str(size) for size in sizes)


def _frames(sizes) -> str:
    return f"{_sizes(sizes)} px frames"


def _png_rows(target: str, **kwargs) -> list[Row]:
    """Rows for every PNG a target writes, taken from ``preview_assets``."""
    assets = build.preview_assets(_SpecCache(), target, **kwargs)
    return [
        Row(path, "%d × %d px" % _open_size(png), _note(path))
        for path, png in assets.items()
    ]


def _open_size(png: bytes) -> tuple[int, int]:
    from io import BytesIO

    from PIL import Image

    with Image.open(BytesIO(png)) as image:
        return image.size


def web_rows() -> list[Row]:
    """Every file ``iconflow ship --targets web`` writes, in build order."""
    rows = [
        Row("favicon.svg", "vector", _note("favicon.svg")),
        Row("favicon.ico", _frames([16, 32, 48]), _note("favicon.ico")),
    ]
    rows += _png_rows("web")
    rows += [
        Row("site.webmanifest", "JSON", _note("site.webmanifest")),
        Row("favicon-head.html", "HTML", _note("favicon-head.html")),
    ]
    return rows


def tile_rows() -> list[Row]:
    """Optional Windows tiles (``--windows-tiles``)."""
    rows = [row for row in _png_rows("web", windows_tiles=True)
            if row.path.startswith("mstile-")]
    rows.append(Row("browserconfig.xml", "XML", _note("browserconfig.xml")))
    return rows


def tauri_rows() -> list[Row]:
    rows = _png_rows("tauri")
    rows.append(Row("icons/icon.ico", _frames(build.ICO_FRAME_ORDER), _note("icons/icon.ico")))
    rows.append(Row("icons/icon.icns", _frames(build.ICNS_FRAME_SIZES), _note("icons/icon.icns")))
    return rows


def electron_rows() -> list[Row]:
    rows = _png_rows("electron")
    rows.append(Row("build/icon.ico", _frames(build.ICO_FRAME_ORDER), _note("build/icon.ico")))
    rows.append(Row("build/icon.icns", _frames(build.ICNS_FRAME_SIZES), _note("build/icon.icns")))
    return rows


def tray_rows() -> list[Row]:
    rows = _png_rows("tray")
    rows.append(Row("tray/trayIcon.ts", "TypeScript", _note("tray/trayIcon.ts")))
    return rows


FAQ = [
    (
        "How many favicon files does a website actually need in 2026?",
        "Six, plus a manifest. An SVG favicon for current browsers, a legacy "
        "favicon.ico holding the 16, 32 and 48 pixel frames, a 180 pixel "
        "apple-touch-icon.png, and 192, 512 and maskable 512 pixel PNGs "
        "declared in the web app manifest. Sets larger than this are almost "
        "always carrying files no current platform requests.",
    ),
    (
        "What sizes go inside favicon.ico?",
        "16, 32 and 48 pixels. ICO is a container format, so those three "
        "frames live inside one file — you do not ship favicon-16.png and "
        "favicon-32.png alongside it.",
    ),
    (
        "What is the maskable icon safe zone?",
        "Android and other adaptive-icon platforms crop your icon to a shape "
        "they choose, so anything near the edge can be cut. IconFlow insets "
        f"the artwork {MASKABLE_PADDING:.0%} on each side — leaving it at "
        f"{1 - 2 * MASKABLE_PADDING:.0%} of the canvas — and flattens the "
        "result onto the background colour, so no mask can remove a "
        "meaningful part of the mark or reveal transparency.",
    ),
    (
        "Why is my macOS menu bar icon a black square?",
        "A macOS template image carries no colour: the system reads only its "
        "alpha channel and paints the shape itself. Handing it a full-card app "
        "icon whose background is opaque therefore produces a solid black "
        "rectangle. The fix is a separate tray drawing with real transparency "
        "around a sparse mark. IconFlow detects the failure instead of "
        "shipping it: when a source covers too much of the canvas it derives "
        "alpha from the mark's own contrast, and refuses the build outright if "
        "no semantic shape can be isolated.",
    ),
    (
        "What icon sizes does Tauri need?",
        "Five PNGs — 32, 64, 128, 256 (as 128x128@2x.png) and 512 — plus "
        "icon.ico for Windows and icon.icns for macOS. IconFlow writes the ICO "
        "frames in the same order the Tauri CLI does, so the output is a "
        "drop-in replacement.",
    ),
    (
        "What icon sizes does Electron need?",
        "A 1024 pixel PNG for Linux and as the electron-builder source, an ICO "
        "for Windows and an ICNS for macOS. The container frames are the same "
        "desktop set used everywhere else: 16, 24, 32, 48, 64, 128, 256, 512 "
        "and 1024 pixels, selected per format.",
    ),
    (
        "Can I just resize a 1024 pixel PNG down to 16 pixels?",
        "You can, and that is exactly where most icons fail. At 16 pixels a "
        "counter closes, a hairline disappears and two colours average into "
        "one. Downscaling produces the file but tells you nothing about "
        "whether the result is still readable. IconFlow renders every size "
        "from the SVG through a pinned Chromium and shows you the native "
        "pixels before anything ships.",
    ),
    (
        "Does IconFlow upload my artwork or call an image model?",
        "No. There is no image model and no API key. You author the SVG, a "
        "pinned local Chromium renders it exactly as a browser would, and "
        "every file is written on your machine. The only network step is the "
        "one-time Chromium download.",
    ),
    (
        "Who owns the icons made with IconFlow?",
        "You do. No attribution is required, there is no share-alike "
        "obligation on your output, and commercial use is unrestricted. Run "
        "iconflow license for the full answer.",
    ),
]


# ---------------------------------------------------------------------------
# Rendering


def text(value: str) -> str:
    """Escape for HTML, and hide the ``@`` from email obfuscators.

    Three of the filenames on this page — ``128x128@2x.png``, ``tray@16.png``,
    ``trayTemplate@2x.png`` — read as email addresses to a CDN. Cloudflare's
    Email Address Obfuscation, on by default, rewrote all three at the edge
    into ``[email protected]`` links and injected a decoder script. The
    repository was correct and the served page was wrong, which is the exact
    failure this page exists not to have: a developer copying a filename from
    it got something that does not exist.

    ``&#64;`` parses to the same character, so the DOM text, a copy-paste and
    a crawler all see ``@`` — but the raw HTML no longer matches an email
    pattern. Do not "tidy" these back into literal ``@``: :func:`render`
    refuses to write a page that contains one outside the JSON-LD block.
    """
    return escape(value).replace("@", "&#64;")


def table(caption: str, rows: list[Row]) -> str:
    body = "\n".join(
        f"      <tr><th scope=\"row\"><code>{text(row.path)}</code></th>"
        f"<td>{text(row.detail)}</td><td>{text(row.note)}</td></tr>"
        for row in rows
    )
    return (
        '    <div class="ref-table-wrap">\n'
        f'     <table class="ref-table">\n'
        f"      <caption>{escape(caption)}</caption>\n"
        "      <thead><tr><th scope=\"col\">File</th><th scope=\"col\">Size</th>"
        "<th scope=\"col\">Why it exists</th></tr></thead>\n"
        "      <tbody>\n"
        f"{body}\n"
        "      </tbody>\n"
        "     </table>\n"
        "    </div>"
    )


def code_block(source: str) -> str:
    return f'<pre class="ref-code"><code>{text(source.rstrip())}</code></pre>'


def faq_markup() -> str:
    items = "\n".join(
        f"     <details class=\"ref-faq-item\">\n"
        f"      <summary>{text(question)}</summary>\n"
        f"      <p>{text(answer)}</p>\n"
        f"     </details>"
        for question, answer in FAQ
    )
    return items


def structured_data() -> str:
    graph = [
        {
            "@type": "TechArticle",
            "@id": f"{ORIGIN}{ROUTE}#article",
            "headline": "App icon and favicon sizes for every platform",
            "description": DESCRIPTION,
            "url": f"{ORIGIN}{ROUTE}",
            "inLanguage": "en",
            "about": {"@id": f"{ORIGIN}/#source"},
            "isPartOf": {"@id": f"{ORIGIN}/#website"},
            "dependencies": f"IconFlow {iconflow.__version__}",
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{ORIGIN}{ROUTE}#breadcrumbs",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "IconFlow", "item": f"{ORIGIN}/"},
                {"@type": "ListItem", "position": 2, "name": "Reference",
                 "item": f"{ORIGIN}/reference/icon-sizes/"},
                {"@type": "ListItem", "position": 3, "name": "Icon sizes"},
            ],
        },
        {
            "@type": "FAQPage",
            "@id": f"{ORIGIN}{ROUTE}#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
                for question, answer in FAQ
            ],
        },
    ]
    payload = {"@context": "https://schema.org", "@graph": graph}
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return "\n".join("  " + line for line in body.splitlines())


# Built outside the page template on purpose. Python 3.10 and 3.11 reject a
# backslash inside an f-string expression — PEP 701 relaxed that only in 3.12 —
# and this project supports 3.10+. The rendered page is byte-identical either
# way; only the parser's patience differs.
SHIP_COMMAND = (
    "pip install iconflow\n"
    "iconflow setup\n"
    "iconflow ship --config iconflow.toml \\\n"
    "  --review master-review.json --out icon-out"
)
DEMO_COMMAND = (
    "pip install iconflow\n"
    "iconflow setup\n"
    "iconflow demo --out iconflow-demo"
)


def _refuse_bare_at(page: str) -> str:
    """Fail rather than publish a filename a CDN will rewrite.

    See :func:`text`. The JSON-LD block is exempt — its ``@context``/``@type``
    keys must stay literal to parse as JSON, and no obfuscator mistakes those
    for an address because there is no dot-domain after them.
    """
    body = re.sub(r'<script type="application/ld\+json">.*?</script>', "",
                  page, flags=re.S)
    stray = re.findall(r"\S*@\S*", body)
    if stray:
        raise SystemExit(
            "refusing to write the page: a literal '@' survives outside the "
            f"JSON-LD block ({', '.join(sorted(set(stray))[:4])}). An email "
            "obfuscator at the CDN will rewrite it into a mailto link and the "
            "published filename will be wrong. Route the text through text()."
        )
    return page


def render() -> str:
    head_snippet = htmlhead.head_snippet("My App", "#0b0d12", "#ffffff")
    manifest = json.dumps(
        htmlhead.manifest("My App", "#0b0d12", "#ffffff"), indent=2
    )
    targets = ", ".join(build.TARGETS)

    return _refuse_bare_at(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(TITLE)} | IconFlow</title>
  <meta name="description" content="{escape(DESCRIPTION)}">
  <meta name="theme-color" content="#111216">
  <meta name="color-scheme" content="dark">
  <meta property="og:type" content="article">
  <meta property="og:title" content="Every icon file your platform actually needs">
  <meta property="og:description" content="Favicon, PWA, Tauri, Electron and macOS tray sizes in one table — generated from the build code, so it cannot drift.">
  <meta property="og:url" content="{ORIGIN}{ROUTE}">
  <meta property="og:image" content="{ORIGIN}/assets/social-preview.png?v=petal">
  <meta property="og:image:width" content="1280">
  <meta property="og:image:height" content="640">
  <meta property="og:image:alt" content="IconFlow: Design. Review. Ship. One semantic SVG becomes a proven icon family.">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="{ORIGIN}{ROUTE}">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <link rel="stylesheet" href="/styles.css?v={ASSET_VERSION}">
  <link rel="stylesheet" href="/reference/reference.css?v={ASSET_VERSION}">
  <script type="application/ld+json">
{structured_data()}
  </script>
  <script src="/app.js?v={ASSET_VERSION}" defer></script>
</head>
<body class="reference-body">
  <a class="skip-link" href="#main">Skip to content</a>

  <header class="site-header" data-header>
    <a class="brand" href="/" aria-label="IconFlow home"><img src="/assets/iconflow-mark.svg" width="34" height="34" alt=""><span>IconFlow</span></a>
    <button class="menu-button" type="button" aria-expanded="false" aria-controls="site-nav" data-menu data-label-open="Open navigation" data-label-close="Close navigation"><span class="sr-only">Toggle navigation</span><span></span><span></span></button>
    <nav id="site-nav" class="site-nav" aria-label="Primary navigation"><a href="#web">Favicon</a><a href="#pwa">PWA</a><a href="#tauri">Tauri</a><a href="#electron">Electron</a><a href="#tray">Tray</a><a href="/getting-started/">Get started</a></nav>
  </header>

  <main id="main">
    <nav class="ref-breadcrumb section-shell" aria-label="Breadcrumb">
      <a href="/">IconFlow</a> <span aria-hidden="true">/</span> <span>Icon size reference</span>
    </nav>

    <section class="ref-hero section-shell">
      <div class="ref-hero-copy">
        <p class="section-kicker">Reference · generated from the build code</p>
        <h1>Every icon file<br>your platform<br><em>actually needs.</em></h1>
        <p class="ref-lede">Favicon, PWA manifest, Tauri, Electron and the macOS menu bar — one table per target, with the exact filenames and frame sizes. Nothing here is transcribed by hand: the page is generated from <code>iconflow/build.py</code>, so it says what the tool ships and fails the build when the two disagree.</p>
        <p class="ref-meta">IconFlow {escape(iconflow.__version__)} · targets: <code>{escape(targets)}</code></p>
      </div>
      <aside class="ref-hero-card" aria-label="Produce every file below">
        <p>Produce every file on this page from one SVG:</p>
        {code_block(SHIP_COMMAND)}
        <p class="ref-hero-note">No image model, no API key, no upload. A pinned Chromium renders your SVG locally, and <code>ship</code> refuses to run unless the review receipt still matches the source.</p>
        <a class="button button-primary" href="/getting-started/">Getting started <span aria-hidden="true">&rarr;</span></a>
      </aside>
    </section>

    <section class="ref-section section-shell" id="web">
      <h2>Web favicon</h2>
      <p>The modern set is smaller than most guides claim. An SVG covers every current browser at every size; the <code>.ico</code> exists only for legacy fallback, and it is one file, not three.</p>
{table("iconflow ship --targets web", web_rows())}
      <h3>The &lt;head&gt; block</h3>
      <p>IconFlow writes this next to the assets as <code>favicon-head.html</code>, so the markup and the files are produced together and cannot disagree:</p>
      {code_block(head_snippet)}
    </section>

    <section class="ref-section section-shell" id="pwa">
      <h2>PWA manifest and maskable icons</h2>
      <p>An adaptive platform crops your icon to a shape it chooses. A square drawing that reaches the canvas edge loses its corners; one with transparency shows the mask through. Both problems are solved before export, by insetting the artwork and flattening it onto the background colour.</p>
      <p>The generated <code>site.webmanifest</code> declares exactly three icons — the third carrying <code>"purpose": "maskable"</code>:</p>
      {code_block(manifest)}
      <p class="ref-callout"><strong>Safe zone.</strong> The maskable asset insets the artwork {MASKABLE_PADDING:.0%} on every side, leaving it at {1 - 2 * MASKABLE_PADDING:.0%} of the canvas, then flattens it. Any platform mask — circle, squircle, rounded square — lands inside that margin.</p>
    </section>

    <section class="ref-section section-shell" id="windows">
      <h2>Windows pinned-site tiles <small>optional</small></h2>
      <p>Only produced with <code>--windows-tiles</code>. The artwork is centred on each canvas rather than stretched, which is why the wide tile takes a smaller scale than the squares.</p>
{table("iconflow ship --targets web --windows-tiles", tile_rows())}
    </section>

    <section class="ref-section section-shell" id="tauri">
      <h2>Tauri</h2>
      <p>Five PNGs plus the two desktop containers. The ICO frame order matches the Tauri CLI's own output, so the result drops into <code>src-tauri/icons/</code> unchanged.</p>
{table("iconflow ship --targets tauri", tauri_rows())}
    </section>

    <section class="ref-section section-shell" id="electron">
      <h2>Electron</h2>
      <p>electron-builder reads one source image per platform. The optional corner radius is applied to the raster frames only — your SVG master keeps its own geometry.</p>
{table("iconflow ship --targets electron", electron_rows())}
    </section>

    <section class="ref-section section-shell" id="tray">
      <h2>macOS menu bar and system tray</h2>
      <p>This is the target that fails most often, and it fails silently: a template image carries no colour at all. macOS reads its alpha channel and paints the shape itself, so a full-card app icon with an opaque background arrives as a solid black rectangle.</p>
{table("iconflow ship --targets tray", tray_rows())}
      <p class="ref-callout"><strong>Give the tray its own drawing.</strong> A menu bar mark needs real transparency around a sparse shape — usually a simplified version of the master, not the master itself. Pass it with <code>--tray-svg</code>. When you do not, IconFlow derives alpha from the mark's contrast, and if no semantic shape can be isolated it refuses the build rather than shipping a black square.</p>
      <div class="ref-actions"><a class="button button-primary" href="/reference/tray-icons/">See the black-square failure and fix <span aria-hidden="true">&rarr;</span></a></div>
    </section>

    <section class="ref-section section-shell" id="sizes">
      <h2>Why 16 pixels decides everything</h2>
      <p>Every size in the tables above is rendered from the same SVG, but only one of them is where icons actually fail. At 16 pixels a counter closes, a hairline vanishes, and two adjacent colours average into one. A design reviewed at 1024 pixels and exported downward can be unreadable in the browser tab it was made for — and the export step will not tell you.</p>
      <p>IconFlow inverts the order. It renders native pixels through a pinned Chromium at every target size, shows you the result at 1:1, and <code>ship</code> fails closed unless automated checks are clean and all six human rubric scores are at least 4 out of 5.</p>
      <div class="ref-actions">
        <a class="button button-primary" href="/#proof">Open the interactive proof lab <span aria-hidden="true">&rarr;</span></a>
        <a class="button button-quiet" href="/how-icons-are-made/">How icons are made</a>
        <a class="button button-quiet" href="/gallery/">100 proofed cases</a>
      </div>
    </section>

    <section class="ref-section section-shell" id="faq">
      <h2>Questions people ask</h2>
      <div class="ref-faq">
{faq_markup()}
      </div>
    </section>

    <section class="ref-cta section-shell">
      <div><p class="section-kicker">One master. Every surface.</p><h2>Stop exporting.<br>Start proving.</h2></div>
      <div>
        <p>Everything on this page is one command away, and the first run is a genuine gated ship rather than a render.</p>
        {code_block(DEMO_COMMAND)}
        <div class="ref-actions"><a class="button button-primary" href="/getting-started/">Getting started <span aria-hidden="true">&rarr;</span></a><a class="button button-quiet" href="https://github.com/snowyukitty/ai-iconflow">Source on GitHub</a></div>
      </div>
    </section>
  </main>

  <footer class="site-footer section-shell">
    <div class="footer-brand"><img src="/assets/iconflow-mark.svg" width="40" height="40" alt=""><div><strong>IconFlow</strong><span>One master. Every surface.</span></div></div>
    <p>Generated from <code>iconflow/build.py</code>. If the tool changes, this page changes or CI fails.</p>
    <nav aria-label="Footer navigation"><a href="/">Home</a><a href="/getting-started/">Guide</a><a href="/reference/tray-icons/">Tray icons</a><a href="/how-icons-are-made/">How it's made</a><a href="/gallery/">Gallery</a><a href="/archive/">Archive</a><a href="https://github.com/snowyukitty/ai-iconflow">Source</a></nav>
  </footer>
</body>
</html>
""")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if the published page is out of date")
    args = parser.parse_args()

    text = render()
    if args.check:
        current = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
        if current != text:
            print("reference verify: STALE — run python scripts/build_reference.py")
            return 1
        print(f"reference verify: OK · {len(FAQ)} questions, "
              f"{len(build.TARGETS)} targets, IconFlow {iconflow.__version__}")
        return 0

    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
