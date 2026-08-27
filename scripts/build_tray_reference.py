# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Generate the macOS tray-icon failure guide and its visual evidence.

The page at ``/reference/tray-icons/`` answers one narrow, costly question:
why an otherwise good app icon becomes a black block in the macOS menu bar.
Its comparison images are not marketing mock-ups. They are produced by
``iconflow.assemble.to_template`` from IconFlow's own shipped app and tray
sources, and ``--check`` binds both the prose and every PNG to that code path.

Usage::

    python scripts/build_tray_reference.py
    python scripts/build_tray_reference.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for path in (ROOT, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import iconflow  # noqa: E402
from iconflow import assemble  # noqa: E402
from build_reference import (  # noqa: E402
    _refuse_bare_at,
    code_block,
    table,
    text,
    tray_rows,
)

SITE = ROOT / "website"
PAGE = SITE / "reference" / "tray-icons" / "index.html"
ASSET_DIR = SITE / "assets" / "reference" / "tray-icons"
ORIGIN = "https://ai-iconflow.com"
ROUTE = "/reference/tray-icons/"
ASSET_VERSION = "20260827a"

APP_SOURCE = ROOT / "brand" / "build" / "icons" / "32x32.png"
TRAY_SOURCE = ROOT / "brand" / "build" / "tray" / "tray.png"
SHIPPED_TEMPLATE = ROOT / "brand" / "build" / "tray" / "trayTemplate@2x.png"

TITLE = "macOS menu bar icon black square — template images fixed"
DESCRIPTION = (
    "Why a macOS menu bar icon turns into a black square, how template images "
    "use alpha, the exact 16px and 32px files Electron needs, and how IconFlow "
    "audits a dedicated tray.svg before shipping."
)

FAQ = [
    (
        "Why is my macOS menu bar icon a black square?",
        "A macOS template image discards colour and uses the source alpha as "
        "its shape. If the source is an opaque app-icon card, that alpha says "
        "the entire card is the icon, so the system tints a solid block. Use a "
        "sparse, transparent tray drawing instead.",
    ),
    (
        "What is a macOS template image?",
        "It is a black-and-transparent image that macOS recolours for the "
        "current menu-bar appearance. Black supplies the shape, transparency "
        "removes the background, and intermediate alpha supplies opacity.",
    ),
    (
        "What tray icon sizes should Electron ship on macOS?",
        "Electron recommends a 16 by 16 pixel Template image at standard "
        "density and a matching 32 by 32 pixel retina file. IconFlow writes "
        "trayTemplate.png and trayTemplate@2x.png, plus colour equivalents.",
    ),
    (
        "Does the word Template need to be in the filename?",
        "For Electron's automatic macOS template handling, yes. The base file "
        "name must end in Template and the retina pair must keep the same base "
        "name before @2x. IconFlow emits those names exactly.",
    ),
    (
        "Can I reuse the full app icon in the menu bar?",
        "Usually not. App icons are cards designed for large launch surfaces; "
        "menu-bar icons are tiny, transparent silhouettes. IconFlow can derive "
        "a contrast mask from an opaque card as a fallback, but a simplified "
        "tray.svg is more legible and preserves intent.",
    ),
    (
        "What do IconFlow's auto, alpha and contrast modes do?",
        "Alpha preserves the source alpha, which is correct for a genuinely "
        "transparent tray mark. Contrast derives transparency from the "
        "difference between the mark and its background. Auto keeps alpha for "
        "a sparse source and switches to contrast for a full-card source.",
    ),
    (
        "How do I test a menu-bar icon on light and dark backgrounds?",
        "Inspect the actual 16 pixel template in both contexts. The system "
        "tints the same alpha mask dark on a light bar and light on a dark bar; "
        "do not maintain separate coloured artwork for the two appearances.",
    ),
    (
        "Does the icon replace an accessible menu title?",
        "No. A graphic is not an accessible name. Give the menu-bar control a "
        "real title or label; SwiftUI's MenuBarExtra title is used for "
        "accessibility even when the visible control uses an image.",
    ),
]


def artifacts() -> dict[str, bytes]:
    """Return every evidence PNG, derived from real project outputs."""
    app = APP_SOURCE.read_bytes()
    tray = TRAY_SOURCE.read_bytes()
    tray_template = assemble.to_template(tray, "auto")
    shipped = SHIPPED_TEMPLATE.read_bytes()
    if tray_template != shipped:
        raise SystemExit(
            "brand/build/tray/trayTemplate@2x.png no longer matches "
            "assemble.to_template(tray.png, 'auto'); rebuild the brand target"
        )
    return {
        "full-card.png": app,
        "full-card-alpha-template.png": assemble.to_template(app, "alpha"),
        "full-card-auto-template.png": assemble.to_template(app, "auto"),
        "tray-color.png": tray,
        "tray-auto-template.png": tray_template,
    }


def evidence_hash(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, payload in sorted(files.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
    return digest.hexdigest()[:12]


def faq_markup() -> str:
    return "\n".join(
        f'     <details class="ref-faq-item">\n'
        f"      <summary>{text(question)}</summary>\n"
        f"      <p>{text(answer)}</p>\n"
        f"     </details>"
        for question, answer in FAQ
    )


def structured_data() -> str:
    graph = [
        {
            "@type": "TechArticle",
            "@id": f"{ORIGIN}{ROUTE}#article",
            "headline": "Why macOS menu bar icons become black squares",
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
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Icon size reference",
                    "item": f"{ORIGIN}/reference/icon-sizes/",
                },
                {"@type": "ListItem", "position": 3, "name": "Tray icons"},
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
    return "\n".join(
        "  " + line for line in json.dumps(payload, ensure_ascii=False, indent=2).splitlines()
    )


AUDIT_COMMAND = (
    "iconflow check master.svg \\\n"
    "  --tray-svg tray.svg \\\n"
    "  --tray-template-mode auto\n"
    "iconflow review --config iconflow.toml --html review.html\n"
    "iconflow ship --config iconflow.toml --review master-review.json"
)


def render(files: dict[str, bytes] | None = None) -> str:
    files = files or artifacts()
    binding = evidence_hash(files)
    at_2x = text("trayTemplate@2x.png")

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
  <meta property="og:title" content="Your menu bar icon is not a tiny app icon">
  <meta property="og:description" content="See the black-square failure, the automatic recovery, and the dedicated tray mark — all generated by the real IconFlow template code.">
  <meta property="og:url" content="{ORIGIN}{ROUTE}">
  <meta property="og:image" content="{ORIGIN}/assets/marketing/tray-template-1200x630.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="A full app-icon card becomes a black block when converted by alpha alone; a dedicated tray source remains a clear silhouette on light and dark menu bars.">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{ORIGIN}/assets/marketing/tray-template-1200x630.png">
  <meta name="twitter:image:alt" content="A full app-icon card becomes a black block when converted by alpha alone; a dedicated tray source remains a clear silhouette on light and dark menu bars.">
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
    <nav id="site-nav" class="site-nav" aria-label="Primary navigation"><a href="#failure">Failure</a><a href="#template">Template</a><a href="#files">Files</a><a href="#audit">Audit</a><a href="/reference/icon-sizes/">All sizes</a></nav>
  </header>

  <main id="main">
    <nav class="ref-breadcrumb section-shell" aria-label="Breadcrumb">
      <a href="/">IconFlow</a> <span aria-hidden="true">/</span> <a href="/reference/icon-sizes/">Reference</a> <span aria-hidden="true">/</span> <span>Tray icons</span>
    </nav>

    <section class="ref-hero ref-hero-tray section-shell">
      <div class="ref-hero-copy">
        <p class="section-kicker">macOS menu bar · source-bound reference</p>
        <h1>Your tray icon<br>is not a tiny<br><em>app icon.</em></h1>
        <p class="ref-lede">A macOS template image throws colour away and keeps alpha. Feed it an opaque app-icon card and the card becomes the shape: a black block. The reliable fix is a separate, transparent <code>tray.svg</code> designed to survive at 16 pixels.</p>
        <p class="ref-meta">IconFlow {escape(iconflow.__version__)} · evidence <code>sha256:{binding}</code></p>
      </div>
      <aside class="tray-hero-proof" aria-label="The same icon source shown as a failed and a corrected macOS template">
        <div class="tray-hero-source">
          <span>app icon source</span>
          <img src="/assets/reference/tray-icons/full-card.png" width="32" height="32" alt="IconFlow's full colour app icon">
        </div>
        <span class="tray-proof-arrow" aria-hidden="true">→</span>
        <div class="tray-hero-result tray-hero-result-bad">
          <span>alpha only</span>
          <img src="/assets/reference/tray-icons/full-card-alpha-template.png" width="32" height="32" alt="The opaque app icon converted into an unreadable dark card">
        </div>
        <span class="tray-proof-arrow" aria-hidden="true">→</span>
        <div class="tray-hero-result tray-hero-result-good">
          <span>dedicated tray mark</span>
          <img src="/assets/reference/tray-icons/tray-auto-template.png" width="32" height="32" alt="The transparent tray drawing converted into a clear menu bar silhouette">
        </div>
      </aside>
    </section>

    <section class="ref-section section-shell" id="failure">
      <p class="section-kicker">The failure, reproduced</p>
      <h2>Alpha is geometry.</h2>
      <p>Template images are black plus transparency. macOS supplies the visible colour for the current appearance; the source alpha supplies the silhouette. That is why this failure looks mysterious in a colour editor and obvious once the alpha channel is treated as the drawing.</p>
      <div class="tray-story" aria-label="Three real IconFlow template conversion outcomes">
        <article class="tray-story-card tray-story-fail">
          <p class="tray-story-index">01 · failure</p>
          <h3>Full card + <code>alpha</code></h3>
          <div class="tray-contexts" aria-label="Failed template on light and dark menu bars">
            <span class="tray-context tray-context-light"><img src="/assets/reference/tray-icons/full-card-alpha-template.png" width="32" height="32" alt="Dark rounded block on a light menu bar"></span>
            <span class="tray-context tray-context-dark"><img src="/assets/reference/tray-icons/full-card-alpha-template.png" width="32" height="32" alt="Light rounded block on a dark menu bar"></span>
          </div>
          <p>The opaque card survives as one large shape. Colour detail disappears.</p>
        </article>
        <article class="tray-story-card">
          <p class="tray-story-index">02 · recovery</p>
          <h3>Full card + <code>auto</code></h3>
          <div class="tray-contexts" aria-label="Contrast-derived template on light and dark menu bars">
            <span class="tray-context tray-context-light"><img src="/assets/reference/tray-icons/full-card-auto-template.png" width="32" height="32" alt="Contrast-derived IconFlow mark on a light menu bar"></span>
            <span class="tray-context tray-context-dark"><img src="/assets/reference/tray-icons/full-card-auto-template.png" width="32" height="32" alt="Contrast-derived IconFlow mark on a dark menu bar"></span>
          </div>
          <p><code>auto</code> detects card-like coverage and derives alpha from edge contrast.</p>
        </article>
        <article class="tray-story-card tray-story-best">
          <p class="tray-story-index">03 · preferred</p>
          <h3><code>tray.svg</code> + <code>auto</code></h3>
          <div class="tray-contexts" aria-label="Dedicated tray template on light and dark menu bars">
            <span class="tray-context tray-context-light"><img src="/assets/reference/tray-icons/tray-auto-template.png" width="32" height="32" alt="Dedicated IconFlow tray mark on a light menu bar"></span>
            <span class="tray-context tray-context-dark"><img src="/assets/reference/tray-icons/tray-auto-template.png" width="32" height="32" alt="Dedicated IconFlow tray mark on a dark menu bar"></span>
          </div>
          <p>A sparse source keeps intentional transparency and a legible silhouette.</p>
        </article>
      </div>
      <p class="ref-evidence-note">These are not illustrative redraws. The five PNGs on this page are rebuilt from <code>brand/build</code> by <code>iconflow.assemble.to_template</code>; CI compares every byte.</p>
    </section>

    <section class="ref-section section-shell" id="template">
      <h2>Three rules for a durable template</h2>
      <div class="tray-rules">
        <article><span>01</span><h3>Draw the silhouette</h3><p>Use one sparse mark with real transparency around it. At 16 pixels, enclosed holes and separated strokes matter more than colour.</p></article>
        <article><span>02</span><h3>Let macOS tint it</h3><p>Ship black plus alpha, then inspect the same mask on light and dark menu bars. Do not bake a light-mode or dark-mode colour into the source.</p></article>
        <article><span>03</span><h3>Name the retina pair</h3><p>Electron recognizes the template convention from filenames: <code>trayTemplate.png</code> and <code>{at_2x}</code>.</p></article>
      </div>
      <p class="ref-callout"><strong>Accessibility is separate.</strong> Keep a real title or label on the menu-bar control. SwiftUI uses the <code>MenuBarExtra</code> title for accessibility even when the visible control is an image.</p>
    </section>

    <section class="ref-section section-shell" id="files">
      <h2>The exact files IconFlow writes</h2>
      <p>The colour pair is useful on platforms that accept it. The Template pair is the macOS contract: 16 pixels at standard density and 32 pixels for retina. The optional TypeScript module embeds the same source bytes for Electron projects that prefer an inline asset.</p>
{table("iconflow ship --targets tray", tray_rows())}
      <p class="ref-evidence-note">The table is read from the same <code>preview_assets</code> path as a real build. If a filename or size changes, this generator cannot silently keep the old answer.</p>
    </section>

    <section class="ref-section section-shell" id="audit">
      <h2>Audit the tray source before ship</h2>
      <p>A separate source does not guarantee a useful template. Interior colour structure can still collapse into one featureless alpha shape. IconFlow renders the linked tray source through the selected conversion mode and reports when none of its meaningful interior features survive.</p>
      <div class="tray-audit-grid">
        <div>
          {code_block(AUDIT_COMMAND)}
          <p class="ref-evidence-note"><code>check</code> is the early diagnostic. The final <code>ship</code> still re-runs automated QA and requires a current, source-hash-bound review receipt with every human score at least 4 out of 5.</p>
        </div>
        <div class="tray-mode-card">
          <h3>Choose the conversion deliberately</h3>
          <dl>
            <dt><code>auto</code></dt><dd>Preserve sparse alpha; derive contrast for a full card. Recommended default.</dd>
            <dt><code>alpha</code></dt><dd>Trust source transparency exactly. Best for a purpose-built tray source.</dd>
            <dt><code>contrast</code></dt><dd>Always derive the mark from its difference against the background.</dd>
          </dl>
        </div>
      </div>
    </section>

    <section class="ref-section section-shell" id="sources">
      <h2>Primary platform sources</h2>
      <p>This guide binds IconFlow behaviour to the platform contracts rather than repeating folklore.</p>
      <ul class="tray-sources">
        <li><a href="https://developer.apple.com/documentation/appkit/nsimage/istemplate">Apple · NSImage.isTemplate</a><span>Black plus clear pixels; alpha controls opacity; the system processes the appearance.</span></li>
        <li><a href="https://developer.apple.com/documentation/swiftui/menubarextra">Apple · MenuBarExtra</a><span>Persistent menu-bar controls and the accessibility role of the title.</span></li>
        <li><a href="https://www.electronjs.org/docs/latest/api/tray/">Electron · Tray</a><span>Template filenames and the recommended 16-pixel / 32-pixel retina pair.</span></li>
        <li><a href="https://www.electronjs.org/docs/latest/api/native-image">Electron · nativeImage</a><span>Template-image loading and retina naming behaviour.</span></li>
      </ul>
    </section>

    <section class="ref-section section-shell" id="faq">
      <h2>Questions people ask</h2>
      <div class="ref-faq">
{faq_markup()}
      </div>
    </section>

    <section class="ref-cta section-shell">
      <div><p class="section-kicker">One source for each job.</p><h2>App card.<br>Tray silhouette.<br>One proven family.</h2></div>
      <div>
        <p>Keep the visual relationship, change the geometry for the surface, and let the same review receipt prove both sources.</p>
        <div class="ref-actions"><a class="button button-primary" href="/getting-started/">Build your icon family <span aria-hidden="true">→</span></a><a class="button button-quiet" href="/reference/icon-sizes/">Every platform size</a></div>
      </div>
    </section>
  </main>

  <footer class="site-footer section-shell">
    <div class="footer-brand"><img src="/assets/iconflow-mark.svg" width="40" height="40" alt=""><div><strong>IconFlow</strong><span>One master. Every surface.</span></div></div>
    <p>Generated from <code>iconflow.assemble.to_template</code>. If the conversion changes, this page or CI changes with it.</p>
    <nav aria-label="Footer navigation"><a href="/">Home</a><a href="/getting-started/">Guide</a><a href="/reference/icon-sizes/">Icon sizes</a><a href="/gallery/">Gallery</a><a href="/archive/">Archive</a><a href="https://github.com/snowyukitty/ai-iconflow">Source</a></nav>
  </footer>
</body>
</html>
""")


def verify() -> int:
    files = artifacts()
    expected_page = render(files)
    stale: list[str] = []
    current_page = PAGE.read_text(encoding="utf-8") if PAGE.is_file() else ""
    if current_page != expected_page:
        stale.append(str(PAGE.relative_to(ROOT)))
    for name, expected in files.items():
        path = ASSET_DIR / name
        if not path.is_file() or path.read_bytes() != expected:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        print("tray reference verify: STALE — run python scripts/build_tray_reference.py")
        for path in stale:
            print(f"  {path}")
        return 1
    print(
        f"tray reference verify: OK · {len(files)} evidence PNGs · "
        f"sha256:{evidence_hash(files)} · IconFlow {iconflow.__version__}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the page or evidence is stale")
    args = parser.parse_args()
    if args.check:
        return verify()

    files = artifacts()
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(render(files), encoding="utf-8", newline="\n")
    for name, payload in files.items():
        (ASSET_DIR / name).write_bytes(payload)
    print(f"wrote {PAGE.relative_to(ROOT)}")
    print(
        f"wrote {len(files)} evidence PNGs · sha256:{evidence_hash(files)} · "
        "source-bound to assemble.to_template"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
