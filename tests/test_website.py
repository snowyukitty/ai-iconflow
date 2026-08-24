# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
from __future__ import annotations

import hashlib
import json
import random
import tempfile
import re
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from iconflow.config import load_config, load_review_receipt, svg_sha256


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
CANONICAL_ORIGIN = "https://ai-iconflow.com"
NONCANONICAL_ORIGINS = (
    "https://iconflow.pages.dev",
    "https://iconflow.pages.dev",
    "https://www.ai-iconflow.com",
)
LEGACY_ORIGINS = NONCANONICAL_ORIGINS
# Hosts the site answers on but must never serve content from.
REDIRECT_ONLY_HOSTS = ("iconflow.pages.dev",)
TRANSLATED_ROUTES = (
    "index.html",
    "404.html",
    "getting-started/index.html",
    "how-icons-are-made/index.html",
    "archive/index.html",
)
# Deliberately spelled out rather than imported: the contract the site owes its
# visitors must not be defined by the script that generates it.
LANGUAGE_PREFIXES = ("es", "ja", "zh-hant", "zh-hans")
TRANSLATED_PAGES = tuple(
    f"{prefix}/{name}" for prefix in LANGUAGE_PREFIXES for name in TRANSLATED_ROUTES
)
HTML_PAGES = (
    "index.html",
    "404.html",
    "getting-started/index.html",
    "how-icons-are-made/index.html",
    "archive/index.html",
    "gallery/index.html",
    "gallery/social-signals/index.html",
    "gallery/emoji-matrix/index.html",
    "gallery/emoji-matrix/all/index.html",
    "reference/icon-sizes/index.html",
) + TRANSLATED_PAGES

MATRIX_STYLE_ORDER = (
    "flat-geometric", "gradient-glow", "line-mark", "mascot", "duotone",
    "stencil-cut", "pixel-grid", "isometric", "cut-paper", "enamel",
    "blueprint", "stained-glass", "risograph", "clay", "woven",
    "glass-stack", "cel-shaded", "ink-brush", "chrome", "woodcut",
)
MATRIX_STYLES = set(MATRIX_STYLE_ORDER)


def load_script(name: str, path: Path):
    """Import one of the repository's build scripts by path."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[cls.__module__],
    # so a script that defines one has to be registered before it executes.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"not a PNG: {path}")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


class _SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[tuple[str, str]] = []
        self.images_without_alt: list[str] = []
        self.images_without_dimensions: list[str] = []
        self.buttons_without_type: list[str] = []
        self.inline_styles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if element_id := values.get("id"):
            self.ids.add(element_id)
        for attribute in ("src", "href"):
            if value := values.get(attribute):
                self.references.append((attribute, value))
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src", "<unknown>"))
        if tag == "img" and ("width" not in values or "height" not in values):
            self.images_without_dimensions.append(values.get("src", "<unknown>"))
        if tag == "button" and "type" not in values:
            self.buttons_without_type.append(values.get("class", "<unknown>"))
        if "style" in values:
            self.inline_styles.append(values.get("style") or "")


class WebsiteContractTests(unittest.TestCase):
    def parse(self, name: str) -> _SiteParser:
        parser = _SiteParser()
        parser.feed((SITE / name).read_text(encoding="utf-8"))
        return parser

    def test_required_deploy_files_exist(self) -> None:
        for name in (
            "index.html",
            "404.html",
            "styles.css",
            "app.js",
            "site.webmanifest",
            "robots.txt",
            "llms.txt",
            "sitemap.xml",
            "_headers",
            "_redirects",
            "getting-started/index.html",
            "getting-started/getting-started.css",
            "how-icons-are-made/index.html",
            "how-icons-are-made/how-icons-are-made.css",
            "playground.js",
            "playground.css",
            "archive/index.html",
            "archive.js",
            "archive.css",
            "assets/archive/catalog.json",
            "gallery/index.html",
            "gallery/gallery.css",
            "gallery/gallery.js",
            "assets/gallery/catalog.json",
            "gallery/social-signals/index.html",
            "gallery/social-signals/social-signals.css",
            "gallery/social-signals/social-signals.js",
            "assets/gallery/social-signals/catalog.json",
            "gallery/emoji-matrix/index.html",
            "gallery/emoji-matrix/emoji-matrix.css",
            "gallery/emoji-matrix/emoji-matrix.js",
            "gallery/emoji-matrix/all/index.html",
            "gallery/emoji-matrix/all/matrix-overview.css",
            "gallery/emoji-matrix/all/matrix-overview.js",
            "assets/gallery/emoji-matrix/catalog.json",
            "assets/gallery/emoji-matrix/overview-2560.webp",
            "reference/icon-sizes/index.html",
            "reference/reference.css",
        ):
            with self.subTest(name=name):
                self.assertTrue((SITE / name).is_file())

    def test_html_local_references_and_fragments_resolve(self) -> None:
        for page in HTML_PAGES:
            parser = self.parse(page)
            for _, reference in parser.references:
                parsed = urlparse(reference)
                if parsed.scheme or parsed.netloc:
                    continue
                if reference.startswith("#"):
                    self.assertIn(reference[1:], parser.ids, f"{page}: {reference}")
                    continue
                target = parsed.path.lstrip("/")
                if not target:
                    target = "index.html"
                elif target.endswith("/"):
                    target += "index.html"
                elif (SITE / target).is_dir():
                    target = str(Path(target) / "index.html")
                self.assertTrue((SITE / target).is_file(), f"{page}: {reference}")

    def test_html_accessibility_basics(self) -> None:
        for page in HTML_PAGES:
            parser = self.parse(page)
            self.assertEqual([], parser.images_without_alt, page)
            self.assertEqual([], parser.buttons_without_type, page)
            self.assertEqual([], parser.inline_styles, page)

    def test_metadata_is_parseable_and_local_first(self) -> None:
        manifest = json.loads((SITE / "site.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual("IconFlow", manifest["name"])
        self.assertGreaterEqual(len(manifest["icons"]), 3)
        ET.parse(SITE / "sitemap.xml")

        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("cdn.", html)
        self.assertIn(f"{CANONICAL_ORIGIN}/", html)
        self.assertIn("Content-Security-Policy", (SITE / "_headers").read_text(encoding="utf-8"))

    def test_every_page_declares_only_the_canonical_origin(self) -> None:
        for page in HTML_PAGES:
            document = (SITE / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                for origin in NONCANONICAL_ORIGINS:
                    self.assertNotIn(f"{origin}/", document)
                canonicals = re.findall(
                    r'<link rel="canonical" href="([^"]+)"', document
                )
                open_graph = re.findall(
                    r'<meta property="og:url" content="([^"]+)"', document
                )
                # 404.html is intentionally excluded from indexing and declares neither.
                for url in canonicals + open_graph:
                    self.assertTrue(
                        url.startswith(f"{CANONICAL_ORIGIN}/"),
                        f"{page} points at {url}",
                    )
                self.assertLessEqual(len(canonicals), 1, f"{page} has two canonicals")

    def test_legacy_host_middleware_moves_visitors_to_the_canonical_origin(self) -> None:
        middleware = (SITE / "functions" / "_middleware.js").read_text(encoding="utf-8")
        # rel=canonical only advises crawlers; every internal link is
        # root-relative, so a visitor landing on a redirect-only host stays
        # there for the whole session unless the edge moves them.
        for host in REDIRECT_ONLY_HOSTS:
            self.assertIn(f'"{host}"', middleware)
        self.assertIn('CANONICAL_HOST = "ai-iconflow.com"', middleware)
        self.assertIn("301", middleware)
        self.assertIn("context.next()", middleware)

        redirect_shell = (ROOT / "website-redirect" / "_redirects").read_text(encoding="utf-8")
        self.assertIn(f"{CANONICAL_ORIGIN}/:splat 301", redirect_shell)
        # The shell's catch-all must never be served from the canonical host, or
        # the apex would redirect to itself. Keep the two trees distinguishable.
        self.assertFalse((SITE / "_redirects").read_text(encoding="utf-8").startswith("/*"))

    def test_csp_needs_no_inline_script_allowance(self) -> None:
        headers = (SITE / "_headers").read_text(encoding="utf-8")
        self.assertNotIn("'unsafe-inline'", headers)
        # Every executable script is an external file, so script-src 'self'
        # covers the site without granting any inline allowance. The two
        # application/ld+json blocks are data, not script: Chromium raises no
        # securitypolicyviolation for them under script-src 'self' and their
        # text stays readable from the DOM, so pinning their hashes bought
        # nothing and broke the CSP every time their URLs changed.
        self.assertNotIn("'sha256-", headers)
        self.assertNotIn("'nonce-", headers)

        inline = re.compile(r"<script(?![^>]*\bsrc=)([^>]*)>", re.I)
        for page in HTML_PAGES:
            document = (SITE / page).read_text(encoding="utf-8")
            for attrs in inline.findall(document):
                with self.subTest(page=page):
                    self.assertIn(
                        "application/ld+json",
                        attrs,
                        f"{page} has an executable inline script that CSP now blocks",
                    )

    def test_getting_started_is_the_canonical_agent_and_cli_onboarding(self) -> None:
        home = (SITE / "index.html").read_text(encoding="utf-8")
        guide = (SITE / "getting-started" / "index.html").read_text(encoding="utf-8")
        script = (SITE / "app.js").read_text(encoding="utf-8")
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        headers = (SITE / "_headers").read_text(encoding="utf-8")

        self.assertIn('/getting-started/', home)
        self.assertIn(f"{CANONICAL_ORIGIN}/getting-started/", guide)
        self.assertIn(f"{CANONICAL_ORIGIN}/getting-started/", sitemap)
        self.assertIn('/getting-started/index.html', headers)
        self.assertIn('data-copy-target="#install-windows"', guide)
        self.assertIn('data-copy-target="#install-posix"', guide)
        self.assertIn('data-copy-target="#agent-prompt"', guide)
        self.assertIn('scripts\\setup.ps1', guide)
        self.assertIn('scripts/setup.sh', guide)
        self.assertIn('AGENTS.md', guide)
        self.assertIn('iconflow review', guide)
        self.assertIn('iconflow ship', guide)
        self.assertIn('iconflow case new', guide)
        # `iconflow` has been on PyPI since 0.5.0 (2026-08-22). The page used to
        # warn that it was not; that warning is now false and must not return.
        self.assertIn('pip install iconflow', guide)
        self.assertNotIn('not published on PyPI yet', guide)
        # The clone lands in a directory named after the repository, not the
        # package; `cd iconflow` after cloning ai-iconflow is a broken command.
        self.assertNotIn("\ncd iconflow\n", guide)
        self.assertIn("querySelectorAll('[data-copy-command]')", script)
        self.assertIn('copyButton.dataset.copyTarget', script)
        structured_data = []
        for document in (home, guide):
            json_ld = document.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
            structured_data.append(json.loads(json_ld))

        homepage_types = {item["@type"] for item in structured_data[0]["@graph"]}
        self.assertEqual({"SoftwareApplication", "SoftwareSourceCode", "WebSite"},
                         homepage_types)
        self.assertEqual("TechArticle", structured_data[1]["@type"])
        # Free is stated as a fact about access, not dressed up as commerce.
        # Rating and price markup on a tool nobody has rated or sold would be
        # rich-result bait, which is exactly the kind of claim this site does
        # not make anywhere else either.
        self.assertNotIn("aggregateRating", home)
        self.assertNotIn('"offers"', home)
        self.assertIn('"isAccessibleForFree": true', home)
        self.assertNotIn("'unsafe-inline'", headers)

    def test_getting_started_keeps_a_static_performance_budget(self) -> None:
        guide_path = SITE / "getting-started" / "index.html"
        guide_css = SITE / "getting-started" / "getting-started.css"
        shared_css = SITE / "styles.css"
        shared_script = SITE / "app.js"
        guide = guide_path.read_text(encoding="utf-8")
        parser = self.parse("getting-started/index.html")

        self.assertLess(guide_path.stat().st_size, 25_000)
        self.assertLess(guide_css.stat().st_size + shared_css.stat().st_size, 60_000)
        self.assertLess(shared_script.stat().st_size, 8_000)
        self.assertEqual([], parser.images_without_dimensions)
        self.assertRegex(guide, r'<script src="/app\.js(\?v=[A-Za-z0-9]+)?" defer></script>')
        self.assertNotIn("fonts.googleapis.com", guide)
        self.assertNotIn("cdn.", guide)
        self.assertNotIn("<iframe", guide)

    def test_theme_worlds_are_source_bound(self) -> None:
        worlds = (
            "keepsake-knot",
            "catnap-focus",
            "trail-tail",
            "koi-return",
            "quiet-hero",
            "sky-courier",
            "co-op-lock",
            "forest-familiar",
            "boss-helm",
        )
        html = (SITE / "index.html").read_text(encoding="utf-8")
        for slug in worlds:
            with self.subTest(slug=slug):
                svg = SITE / "assets" / "worlds" / f"{slug}.svg"
                native = SITE / "assets" / "worlds" / f"{slug}-16.png"
                receipt = SITE / "assets" / "worlds" / f"{slug}-review.json"
                self.assertTrue(svg.is_file())
                self.assertTrue(native.is_file())
                self.assertTrue(receipt.is_file())
                self.assertIn(f"/assets/worlds/{slug}.svg", html)
                self.assertIn(f"/assets/worlds/{slug}-16.png", html)
                review = json.loads(receipt.read_text(encoding="utf-8"))
                self.assertEqual(review["source_sha256"], svg_sha256(svg))
                self.assertEqual("ready", review["status"])
                self.assertEqual([], review["warnings"])
                self.assertTrue(all(score >= 4 for score in review["scores"].values()))

    def test_gallery_100_case_admission_contract(self) -> None:
        record = json.loads(
            (SITE / "assets" / "gallery" / "catalog.json").read_text(encoding="utf-8")
        )
        cases = record["cases"]
        selection = record["selection"]
        self.assertEqual(100, record["case_count"])
        self.assertEqual(100, len(cases))
        self.assertEqual(
            {"candidate_count": 111, "admitted": 100, "rejected": 11},
            selection,
        )
        self.assertEqual(11, len(record["rejected"]))
        self.assertEqual(100, len({item["id"] for item in cases}))
        self.assertEqual(list(range(1, 101)), [item["number"] for item in cases])

        for item in cases:
            slug = item["id"]
            with self.subTest(case=slug):
                deploy = SITE / "assets" / "gallery" / slug
                source_case = ROOT / "gallery" / "cases" / slug
                paths = {
                    "svg": deploy / "master.svg",
                    "native": deploy / "16.png",
                    "proof": deploy / "128.png",
                    "large": deploy / "256.png",
                    "silhouette": deploy / "silhouette-128.png",
                    "receipt": deploy / "review.json",
                    "case": deploy / "case.md",
                    "config": source_case / "iconflow.toml",
                }
                for path in paths.values():
                    self.assertTrue(path.is_file(), path)
                self.assertEqual((16, 16), png_size(paths["native"]))
                self.assertEqual((128, 128), png_size(paths["proof"]))
                self.assertEqual((256, 256), png_size(paths["large"]))
                self.assertEqual((128, 128), png_size(paths["silhouette"]))

                review = json.loads(paths["receipt"].read_text(encoding="utf-8"))
                config = load_config(paths["config"])
                validated = load_review_receipt(paths["receipt"], config)
                source_hash = svg_sha256(paths["svg"])
                self.assertEqual(source_hash, item["source_sha256"])
                self.assertEqual(source_hash, review["source_sha256"])
                self.assertEqual(validated.contract_sha256, item["contract_sha256"])
                self.assertEqual(validated.contract_sha256, review["contract_sha256"])
                self.assertEqual(item["title"], review["project"])
                self.assertEqual(item["user_job"], review["user_job"])
                self.assertEqual(item["essence"], review["essence"])
                self.assertEqual(item["signature"], review["signature_device"])
                self.assertEqual(item["scores"], review["scores"])
                self.assertEqual(["web"], review["targets"])
                self.assertEqual("ready", review["status"])
                self.assertEqual([], review["warnings"])
                self.assertTrue(all(score >= 4 for score in review["scores"].values()))

                for field in ("world", "noun", "technique", "cliche", "signature"):
                    self.assertTrue(str(item[field]).strip())
                self.assertEqual(4, len(item["concepts"]))

        html = (SITE / "gallery" / "index.html").read_text(encoding="utf-8")
        script = (SITE / "gallery" / "gallery.js").read_text(encoding="utf-8")
        css = (SITE / "gallery" / "gallery.css").read_text(encoding="utf-8")
        redirects = (SITE / "_redirects").read_text(encoding="utf-8")
        self.assertIn("100 admitted cases", html)
        self.assertIn("item.assets.svg", script)
        self.assertIn("Actual 16×16", script)
        self.assertIn(".gallery-native img { width: 16px; height: 16px", css)
        self.assertIn(".case-pixel-proof img { width: 16px; height: 16px", css)
        self.assertIn("/imagination/ /gallery/ 301", redirects)

    def test_gallery_svg_sources_have_canonical_whitespace(self) -> None:
        for root in (ROOT / "gallery" / "cases", SITE / "assets" / "gallery"):
            for path in root.glob("*/master.svg"):
                with self.subTest(path=path.relative_to(ROOT)):
                    lines = path.read_text(encoding="utf-8").splitlines()
                    self.assertTrue(lines)
                    self.assertTrue(all(line == line.rstrip() for line in lines))

    def test_social_signals_admission_contract(self) -> None:
        record = json.loads(
            (SITE / "assets" / "gallery" / "social-signals" / "catalog.json").read_text(encoding="utf-8")
        )
        cases = record["cases"]
        self.assertEqual(20, record["generated_count"])
        self.assertEqual(20, record["admitted_count"])
        self.assertEqual(0, record["rejected_count"])
        self.assertEqual([], record["rejected"])
        self.assertEqual(20, len(cases))
        self.assertEqual(20, len({item["id"] for item in cases}))
        self.assertEqual(MATRIX_STYLES, {item["style"] for item in cases})
        self.assertEqual(20, len([item["style"] for item in cases]))
        self.assertEqual("iconflow-social-signals-2026-08-12-v1", record["seed"])
        expected_styles = list(MATRIX_STYLE_ORDER)
        random.Random(record["seed"]).shuffle(expected_styles)
        self.assertEqual(expected_styles, [item["style"] for item in cases])
        source_set = "\n".join(f"{item['id']}:{item['source_sha256']}" for item in cases) + "\n"
        self.assertEqual(hashlib.sha256(source_set.encode()).hexdigest(), record["source_set_sha256"])

        rejected = set(record["rejected"])
        for item in cases:
            slug = item["id"]
            with self.subTest(signal=slug):
                self.assertNotIn(slug, rejected)
                self.assertEqual(slug, Path(item["assets"]["svg"]).parent.name)
                deploy = SITE / "assets" / "gallery" / "social-signals" / slug
                source = ROOT / "gallery" / "social-signals" / "cases" / slug
                for name in ("master.svg", "16.png", "128.png", "silhouette-128.png", "review.json", "case.md"):
                    self.assertTrue((deploy / name).is_file(), deploy / name)
                svg_text = (deploy / "master.svg").read_text(encoding="utf-8")
                self.assertIn('viewBox="0 0 1024 1024"', svg_text)
                for forbidden in ("<script", "<image", "<foreignobject", "javascript:"):
                    self.assertNotIn(forbidden, svg_text.lower())
                svg_root = ET.fromstring(svg_text)
                for element in svg_root.iter():
                    for attribute, value in element.attrib.items():
                        if attribute.rsplit("}", 1)[-1] in {"href", "src"}:
                            self.assertFalse(value.lower().startswith(("http://", "https://", "//")))
                self.assertEqual((16, 16), png_size(deploy / "16.png"))
                self.assertEqual((128, 128), png_size(deploy / "128.png"))
                self.assertEqual((128, 128), png_size(deploy / "silhouette-128.png"))
                review = json.loads((deploy / "review.json").read_text(encoding="utf-8"))
                validated = load_review_receipt(deploy / "review.json", load_config(source / "iconflow.toml"))
                digest = svg_sha256(deploy / "master.svg")
                self.assertEqual(digest, item["source_sha256"])
                self.assertEqual(digest, review["source_sha256"])
                self.assertEqual(validated.contract_sha256, item["contract_sha256"])
                self.assertEqual("ready", review["status"])
                self.assertEqual([], review["warnings"])
                self.assertTrue(all(score >= 4 for score in review["scores"].values()))

        html = (SITE / "gallery" / "social-signals" / "index.html").read_text(encoding="utf-8")
        script = (SITE / "gallery" / "social-signals" / "social-signals.js").read_text(encoding="utf-8")
        css = (SITE / "gallery" / "social-signals" / "social-signals.css").read_text(encoding="utf-8")
        self.assertIn("independent clean-room", html.lower())
        self.assertIn("not affiliated with or endorsed", html)
        self.assertIn('loading="lazy"', script)
        self.assertIn('width="360" height="360"', script)
        self.assertIn(".signal-native img { width: 16px; height: 16px", css)
        self.assertIn("@media (max-width: 680px)", css)
        public_text = "\n".join((
            html, script,
            (SITE / "assets" / "gallery" / "social-signals" / "catalog.json").read_text(encoding="utf-8"),
        )).lower()
        for platform in (
            "facebook", "youtube", "instagram", "whatsapp", "tiktok", "wechat",
            "telegram", "messenger", "snapchat", "douyin", "kuaishou", "reddit",
            "pinterest", "linkedin", "discord", "threads", "twitch", "bluesky",
        ):
            self.assertNotIn(platform, public_text)

    def test_emoji_matrix_complete_cross_product_contract(self) -> None:
        root = SITE / "assets" / "gallery" / "emoji-matrix"
        record = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
        cells = record["cells"]
        emoji_ids = {item["id"] for item in record["emoji"]}
        styles = {item["id"] for item in record["styles"]}
        self.assertEqual(20, record["emoji_count"])
        self.assertEqual(20, record["style_count"])
        self.assertEqual(400, record["cell_count"])
        self.assertEqual(400, record["generated_count"])
        self.assertEqual(400, record["admitted_count"])
        self.assertEqual(0, record["rejected_count"])
        self.assertEqual([], record["rejected"])
        self.assertEqual(20, len(emoji_ids))
        self.assertEqual(MATRIX_STYLES, styles)
        self.assertEqual(400, len(cells))
        self.assertEqual(400, len({item["id"] for item in cells}))
        self.assertEqual(
            {(emoji_id, style) for emoji_id in emoji_ids for style in styles},
            {(item["emoji_id"], item["style"]) for item in cells},
        )
        source_set = "\n".join(f"{item['id']}:{item['source_sha256']}" for item in cells) + "\n"
        self.assertEqual(hashlib.sha256(source_set.encode()).hexdigest(), record["source_set_sha256"])
        rejected = set(record["rejected"])

        for item in cells:
            with self.subTest(cell=item["id"]):
                self.assertNotIn(item["id"], rejected)
                self.assertEqual(item["id"], f"{item['emoji_id']}--{item['style']}")
                deploy = root / item["emoji_id"] / item["style"]
                source = ROOT / "gallery" / "emoji-matrix" / "cases" / item["emoji_id"] / item["style"]
                for name in ("master.svg", "16.png", "128.png", "silhouette-128.png", "review.json"):
                    self.assertTrue((deploy / name).is_file(), deploy / name)
                svg_text = (deploy / "master.svg").read_text(encoding="utf-8")
                self.assertIn('viewBox="0 0 1024 1024"', svg_text)
                for forbidden in ("<script", "<image", "<foreignobject", "javascript:"):
                    self.assertNotIn(forbidden, svg_text.lower())
                svg_root = ET.fromstring(svg_text)
                for element in svg_root.iter():
                    for attribute, value in element.attrib.items():
                        if attribute.rsplit("}", 1)[-1] in {"href", "src"}:
                            self.assertFalse(value.lower().startswith(("http://", "https://", "//")))
                self.assertEqual((16, 16), png_size(deploy / "16.png"))
                self.assertEqual((128, 128), png_size(deploy / "128.png"))
                self.assertEqual((128, 128), png_size(deploy / "silhouette-128.png"))
                review = json.loads((deploy / "review.json").read_text(encoding="utf-8"))
                validated = load_review_receipt(deploy / "review.json", load_config(source / "iconflow.toml"))
                digest = svg_sha256(deploy / "master.svg")
                self.assertEqual(digest, item["source_sha256"])
                self.assertEqual(digest, review["source_sha256"])
                self.assertEqual(validated.contract_sha256, item["contract_sha256"])
                self.assertEqual("practice", review["specimen_status"])
                self.assertEqual("ready", review["status"])
                self.assertEqual([], review["warnings"])
                self.assertTrue(all(score >= 4 for score in review["scores"].values()))

        checks = json.loads((root / "check-results.json").read_text(encoding="utf-8"))
        self.assertEqual(400, checks["total"])
        self.assertEqual(400, checks["clean"])
        self.assertEqual(0, checks["failed"])
        self.assertEqual(400, len(checks["results"]))
        self.assertEqual(
            {item["id"]: item["source_sha256"] for item in cells},
            {item["id"]: item["source_sha256"] for item in checks["results"]},
        )
        self.assertTrue(all(item["warnings"] == [] for item in checks["results"]))
        self.assertEqual(record["source_set_sha256"], json.loads(
            (root / "review-decision.json").read_text(encoding="utf-8")
        )["source_set_sha256"])

        html = (SITE / "gallery" / "emoji-matrix" / "index.html").read_text(encoding="utf-8")
        script = (SITE / "gallery" / "emoji-matrix" / "emoji-matrix.js").read_text(encoding="utf-8")
        css = (SITE / "gallery" / "emoji-matrix" / "emoji-matrix.css").read_text(encoding="utf-8")
        self.assertIn("practice specimens", html)
        self.assertIn("history.replaceState", script)
        self.assertIn("hashchange", script)
        self.assertIn('loading="lazy"', script)
        self.assertIn("Pixel zoom · native 16px", script)
        self.assertIn(".matrix-native { width: 16px; height: 16px", css)
        self.assertIn("@media (max-width: 680px)", css)

    def test_emoji_matrix_complete_overview_contract(self) -> None:
        root = SITE / "assets" / "gallery" / "emoji-matrix"
        record = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
        overview = record["overview"]
        poster = SITE / overview["asset"].lstrip("/")
        self.assertEqual(2560, overview["width"])
        self.assertEqual(2560, overview["height"])
        self.assertEqual(128, overview["tile_width"])
        self.assertEqual(128, overview["tile_height"])
        self.assertTrue(poster.is_file())
        self.assertEqual(hashlib.sha256(poster.read_bytes()).hexdigest(), overview["sha256"])
        with Image.open(poster) as image:
            self.assertEqual((2560, 2560), image.size)
            self.assertEqual("WEBP", image.format)
        self.assertLess(poster.stat().st_size, 4 * 1024 * 1024)

        page_root = SITE / "gallery" / "emoji-matrix" / "all"
        html = (page_root / "index.html").read_text(encoding="utf-8")
        script = (page_root / "matrix-overview.js").read_text(encoding="utf-8")
        css = (page_root / "matrix-overview.css").read_text(encoding="utf-8")
        self.assertIn('data-matrix-poster', html)
        self.assertNotIn('class="comparison-frame reveal"', html)
        self.assertIn('width="2560" height="2560"', html)
        self.assertIn("complete field", html.lower())
        self.assertIn("practice specimen", html.lower())
        self.assertIn("role=\"gridcell\"", script)
        self.assertIn("ArrowLeft", script)
        self.assertIn("history.replaceState", script)
        self.assertIn("IntersectionObserver", script)
        self.assertIn('loading="lazy"', script)
        self.assertIn("item.assets.svg", script)
        self.assertIn("item.assets.native", script)
        self.assertIn("grid-template-columns: repeat(20", css)
        self.assertIn(".matrix-board { position: relative; grid-area: 2 / 2", css)
        self.assertIn(".row-axis { display: grid; grid-area: 2 / 1", css)
        self.assertIn(".inspector-native img,.focus-proof img { width: 16px; height: 16px", css)
        self.assertIn("@media (max-width: 760px)", css)
        self.assertIn("overflow-x: hidden", css)

    def test_living_archive_is_source_bound_and_mirrored_on_the_homepage(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("build_archive", ROOT / "scripts" / "build_archive.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(0, module.verify())
        catalog = json.loads((SITE / "assets" / "archive" / "catalog.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(catalog["counts"]["directions"], 100)
        production = [e for e in catalog["entries"] if e["status"] == "production"]
        self.assertEqual(1, len(production))
        # The published copy carries a provenance block the brand master does
        # not (docs/PROVENANCE.md); the binding is about the drawing, so compare
        # the mark itself.
        published = SITE / production[0]["svg"].lstrip("/")
        self.assertIn(module.PROVENANCE_MARK, published.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / "production.svg"
            bare.write_text(
                module.strip_provenance(published.read_text(encoding="utf-8")),
                encoding="utf-8", newline="\n",
            )
            self.assertEqual(svg_sha256(ROOT / "brand" / "master.svg"), svg_sha256(bare))
        for entry in random.Random(7).sample(catalog["entries"], 12):
            self.assertEqual((16, 16), png_size(SITE / entry["proof16"].lstrip("/")))
        home = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/archive/"', home)
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"{CANONICAL_ORIGIN}/archive/", sitemap)

    def test_collection_routes_are_in_sitemap_and_gallery_navigation(self) -> None:
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        gallery = (SITE / "gallery" / "index.html").read_text(encoding="utf-8")
        for route in ("/gallery/social-signals/", "/gallery/emoji-matrix/", "/gallery/emoji-matrix/all/"):
            self.assertIn(f"{CANONICAL_ORIGIN}{route}", sitemap)
            self.assertIn(route, gallery)
        self.assertIn("100 admitted cases", gallery)

    def test_reference_page_is_generated_from_the_build_code(self) -> None:
        """The published icon-size tables must match what the tool ships.

        The page exists to be quoted — by a developer in a hurry and by an
        answer engine that will not come back to check. So it is generated
        from ``iconflow.build`` rather than written, and a build change that
        has not been re-rendered fails here rather than being published as a
        confident, wrong table.
        """
        reference = load_script("build_reference", ROOT / "scripts" / "build_reference.py")
        published = (SITE / "reference" / "icon-sizes" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(reference.render(), published,
                         "run python scripts/build_reference.py")

        # Every target the CLI understands has a section a reader can link to.
        for target in reference.build.TARGETS:
            anchor = "web" if target == "pwa" else target
            with self.subTest(target=target):
                self.assertIn(f'id="{anchor}"', published)

        # The route earns its own crawl surface: sitemap entry, cache header,
        # inbound links, and an exemption from the training-crawler block that
        # covers the licensed corpus.
        self.assertIn(f"{CANONICAL_ORIGIN}/reference/icon-sizes/",
                      (SITE / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertIn("\n/reference/icon-sizes/\n"
                      "  Cache-Control: public, max-age=0, must-revalidate",
                      (SITE / "_headers").read_text(encoding="utf-8"))
        self.assertIn("Allow: /reference/", (SITE / "robots.txt").read_text(encoding="utf-8"))
        for page in ("index.html", "getting-started/index.html", "gallery/index.html"):
            with self.subTest(page=page):
                self.assertIn('href="/reference/icon-sizes/"',
                              (SITE / page).read_text(encoding="utf-8"))

    def test_structured_data_answers_the_questions_search_engines_ask(self) -> None:
        """Every indexed page carries parseable, self-consistent JSON-LD."""
        blocks = re.compile(
            r'<script type="application/ld\+json">(.*?)</script>', re.S)
        seen: dict[str, set[str]] = {}
        for page in HTML_PAGES:
            if page.endswith("404.html"):
                continue
            document = (SITE / page).read_text(encoding="utf-8")
            found = blocks.findall(document)
            with self.subTest(page=page):
                self.assertTrue(found, f"{page} publishes no structured data")
                types = set()
                for raw in found:
                    payload = json.loads(raw)
                    for node in payload.get("@graph", [payload]):
                        types.add(node["@type"])
                seen[page] = types

        # The homepage has to answer "what is this software" in machine terms:
        # category, platforms, price, where to install it from.
        self.assertLessEqual({"WebSite", "SoftwareSourceCode", "SoftwareApplication"},
                             seen["index.html"])
        # The reference page is written to be quoted, so it says what it is,
        # where it sits, and which questions it answers.
        self.assertLessEqual({"TechArticle", "FAQPage", "BreadcrumbList"},
                             seen["reference/icon-sizes/index.html"])
        for page in ("gallery/index.html", "gallery/social-signals/index.html",
                     "gallery/emoji-matrix/index.html",
                     "gallery/emoji-matrix/all/index.html"):
            with self.subTest(page=page):
                self.assertIn("CollectionPage", seen[page])

    def test_every_indexed_page_has_a_distinct_title_and_description(self) -> None:
        """Duplicate titles across a site are the cheapest ranking loss there is."""
        titles: dict[str, str] = {}
        descriptions: dict[str, str] = {}
        for page in HTML_PAGES:
            if page.endswith("404.html"):
                continue
            document = (SITE / page).read_text(encoding="utf-8")
            title = re.search(r"<title>(.*?)</title>", document, re.S)
            description = re.search(
                r'<meta name="description" content="([^"]*)"', document)
            with self.subTest(page=page):
                self.assertIsNotNone(title, f"{page} has no title")
                self.assertIsNotNone(description, f"{page} has no description")
                text = title.group(1).strip()
                # Long enough to describe the page, short enough to survive the
                # ~60-character truncation a result listing applies.
                self.assertGreater(len(text), 20, f"{page} title is too thin")
                self.assertNotIn(text, titles.values(),
                                 f"{page} repeats the title of {titles}")
                titles[page] = text
                summary = description.group(1).strip()
                self.assertGreater(len(summary), 60, f"{page} description is too thin")
                self.assertNotIn(summary, descriptions.values(),
                                 f"{page} repeats a description")
                descriptions[page] = summary


class InternationalisationContractTests(unittest.TestCase):
    """The five-language build: routes, hreflang, catalogs, and typography.

    The structural assertions read the deployed files directly rather than
    asking the builder, so a bug in ``scripts/build_i18n.py`` cannot certify
    its own output.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.i18n = load_script("build_i18n", ROOT / "scripts" / "build_i18n.py")

    def parse(self, page: str) -> _SiteParser:
        parser = _SiteParser()
        parser.feed((SITE / page).read_text(encoding="utf-8"))
        return parser

    def test_builder_verifies_its_own_output_is_current(self) -> None:
        # Catalogs complete, placeholders sound, every generated page and the
        # sitemap/_headers blocks byte-identical to a fresh render.
        self.assertEqual(0, self.i18n.verify())

    def test_every_language_ships_every_translated_page(self) -> None:
        for language in self.i18n.LANGUAGES:
            for page in self.i18n.PAGES:
                name = f"{language.directory}/{page.source}" if language.directory else page.source
                with self.subTest(language=language.code, page=page.source):
                    self.assertTrue((SITE / name).is_file(), name)

    def test_translated_pages_declare_their_language_and_the_full_hreflang_set(self) -> None:
        codes = [language.code for language in self.i18n.LANGUAGES]
        for language in self.i18n.LANGUAGES:
            for page in self.i18n.PAGES:
                name = f"{language.directory}/{page.source}" if language.directory else page.source
                document = (SITE / name).read_text(encoding="utf-8")
                with self.subTest(language=language.code, page=page.source):
                    self.assertIn(f'<html lang="{language.code}">', document)
                    if not page.changefreq:      # 404 is not indexed
                        continue
                    alternates = dict(re.findall(
                        r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', document))
                    self.assertEqual(codes + ["x-default"], list(alternates))
                    for other in self.i18n.LANGUAGES:
                        self.assertEqual(
                            self.i18n.language_url(other, page.route), alternates[other.code])
                    self.assertEqual(self.i18n.language_url(self.i18n.SOURCE_LANGUAGE, page.route),
                                     alternates["x-default"])
                    canonical = re.findall(r'<link rel="canonical" href="([^"]+)">', document)
                    self.assertEqual([self.i18n.language_url(language, page.route)], canonical)
                    self.assertIn(
                        f'<meta property="og:url" content="{self.i18n.language_url(language, page.route)}">',
                        document)

    def test_translated_pages_carry_no_untranslated_markers_or_placeholders(self) -> None:
        for language in self.i18n.LANGUAGES[1:]:
            for page in self.i18n.PAGES:
                document = (SITE / f"{language.directory}/{page.source}").read_text(encoding="utf-8")
                english = (SITE / page.source).read_text(encoding="utf-8")
                with self.subTest(language=language.code, page=page.source):
                    # The placeholder syntax the catalogs use must never reach HTML.
                    self.assertNotRegex(document, r"<(/?)\d+(/?)>")
                    self.assertNotIn("TODO", document)
                    # Runtime tokens survive exactly as often as in the English.
                    for token in ("{size}", "{count}"):
                        self.assertEqual(english.count(token), document.count(token), token)

    def test_translated_pages_keep_the_english_evidence(self) -> None:
        """Commands, file names, mark names and proofs are the artefact."""
        for language in self.i18n.LANGUAGES[1:]:
            home = (SITE / language.directory / "index.html").read_text(encoding="utf-8")
            archive = (SITE / language.directory / "archive" / "index.html").read_text(encoding="utf-8")
            guide = (SITE / language.directory / "getting-started" / "index.html").read_text(encoding="utf-8")
            with self.subTest(language=language.code):
                self.assertIn("Petal Haypile", home)
                self.assertIn("<code>check</code>", archive)
                self.assertIn("<code>ship</code>", archive)
                self.assertIn("scripts/setup.sh", guide)
                self.assertIn("iconflow review", guide)
                self.assertIn("master.svg", home)
                self.assertIn("/assets/proof/icon-16.png", home)
                # The 137 archive readings stay English until a later phase.
                self.assertIn('id="expanded-living-petal-haypile"', archive)
                # The hedge itself is translated; what must survive verbatim is
                # the command it warns about and the registry it names.
                self.assertIn("PyPI", guide)
                self.assertIn("<code>pip install iconflow</code>", guide)

    def test_translated_pages_link_inside_their_own_language(self) -> None:
        routes = {page.route for page in self.i18n.PAGES if page.linked}
        switcher = re.compile(r'<nav class="lang-switch".*?</nav>', re.S)
        for language in self.i18n.LANGUAGES[1:]:
            for page in self.i18n.PAGES:
                document = (SITE / language.directory / page.source).read_text(encoding="utf-8")
                parser = _SiteParser()
                # The switcher is the one place that must point at other languages.
                parser.feed(switcher.sub("", document))
                with self.subTest(language=language.code, page=page.source):
                    for _, reference in parser.references:
                        if not reference.startswith("/") or reference.startswith("//"):
                            continue
                        path = reference.split("#")[0].split("?")[0]
                        self.assertNotIn(
                            path, routes,
                            f"{language.code}/{page.source} still links at the English {path}")
                    self.assertIn(self.i18n.language_path(language, "/"), document)
                    # The gallery is English-only in this phase and must stay linked.
                    self.assertNotIn(f"{language.prefix}/gallery/", document)

    def test_language_switcher_is_on_every_page_and_marks_the_current_one(self) -> None:
        for language in self.i18n.LANGUAGES:
            for page in self.i18n.PAGES:
                name = f"{language.directory}/{page.source}" if language.directory else page.source
                document = (SITE / name).read_text(encoding="utf-8")
                with self.subTest(language=language.code, page=page.source):
                    switchers = re.findall(
                        r'<nav class="lang-switch" data-lang-switch aria-label="[^"]+">(.*?)</nav>',
                        document, re.S)
                    self.assertTrue(switchers, "no language switcher")
                    for switcher in switchers:
                        links = re.findall(r'href="([^"]+)"', switcher)
                        self.assertEqual(
                            [self.i18n.language_path(other, page.route) for other in self.i18n.LANGUAGES],
                            links)
                        self.assertEqual(1, switcher.count('aria-current="true"'))
                        current = re.search(r'href="([^"]+)"[^>]*aria-current="true"', switcher)
                        self.assertEqual(self.i18n.language_path(language, page.route), current.group(1))

    def test_sitemap_covers_every_language_url_with_alternates(self) -> None:
        namespaces = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9",
                      "x": "http://www.w3.org/1999/xhtml"}
        tree = ET.parse(SITE / "sitemap.xml")
        locations = [element.text for element in tree.iter(f"{{{namespaces['s']}}}loc")]
        expected = [self.i18n.language_url(language, page.route)
                    for page in self.i18n.PAGES if page.changefreq
                    for language in self.i18n.LANGUAGES]
        for url in expected:
            self.assertIn(url, locations)
        for route, _, _ in self.i18n.ENGLISH_ONLY:
            self.assertIn(f"{CANONICAL_ORIGIN}{route}", locations)
        self.assertEqual(len(expected) + len(self.i18n.ENGLISH_ONLY), len(locations))
        for url in tree.iter(f"{{{namespaces['s']}}}url"):
            alternates = url.findall(f"{{{namespaces['x']}}}link")
            location = url.find(f"{{{namespaces['s']}}}loc").text
            if any(location == f"{CANONICAL_ORIGIN}{route}" for route, _, _ in self.i18n.ENGLISH_ONLY):
                self.assertEqual([], alternates)
                continue
            self.assertEqual(len(self.i18n.LANGUAGES) + 1, len(alternates))

    def test_headers_revalidate_every_language_route(self) -> None:
        headers = (SITE / "_headers").read_text(encoding="utf-8")
        for language in self.i18n.LANGUAGES[1:]:
            for page in self.i18n.PAGES:
                with self.subTest(language=language.code, page=page.route):
                    self.assertIn(f"\n{self.i18n.language_path(language, page.route)}\n"
                                  "  Cache-Control: public, max-age=0, must-revalidate", headers)
        self.assertNotIn("'unsafe-inline'", headers)

    def test_cjk_typography_is_system_only_and_untracked(self) -> None:
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        for selector, face in ((":lang(ja)", "Hiragino Sans"),
                               (":lang(zh-Hant)", "PingFang TC"),
                               (":lang(zh-Hans)", "PingFang SC")):
            with self.subTest(selector=selector):
                self.assertIn(f"{selector} {{ --sans:", css)
                self.assertIn(face, css)
        # No webfont may be fetched: the CSP allows font-src 'self' only.
        self.assertNotIn("@font-face", css)
        self.assertNotIn("fonts.googleapis.com", css)
        self.assertNotIn("fonts.gstatic.com", css)
        # The display type is tracked tight for Latin; CJK must reset it.
        self.assertIn(":lang(ja) h1", css)
        self.assertIn("letter-spacing: 0", css)

    def test_page_copy_lives_in_the_markup_not_in_the_scripts(self) -> None:
        """Every visitor-facing script string reads a data-label with a fallback."""
        for name, labels in (
            ("app.js", ("labelClose", "labelOpen", "labelStaleTitle", "labelApprovedCopy",
                        "labelNative", "labelGate", "labelPixels", "labelVector",
                        "labelCopied", "labelSelected", "labelCopy")),
            ("archive.js", ("labelResume", "labelPause", "labelShown", "labelAxes")),
            ("playground.js", ("labelCardOn", "labelCardOff")),
        ):
            script = (SITE / name).read_text(encoding="utf-8")
            for label in labels:
                with self.subTest(script=name, label=label):
                    self.assertIn(label, script)
        home = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-label-open="Open navigation"', home)
        self.assertIn('data-label-rail="drag · 16px → source"', home)
        self.assertIn("content: attr(data-label-rail)", (SITE / "styles.css").read_text(encoding="utf-8"))

    def test_catalogs_are_complete_reviewed_and_free_of_english_leftovers(self) -> None:
        source = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))["strings"]
        for language in self.i18n.LANGUAGES[1:]:
            path = SITE / "i18n" / f"{language.code}.json"
            with self.subTest(language=language.code):
                self.assertTrue(path.is_file(), path)
                catalog = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(language.code, catalog["language"])
                strings = catalog["strings"]
                self.assertEqual(sorted(source), sorted(strings))
                self.assertTrue(all(value.strip() for value in strings.values()))
                # A catalog that simply echoes the English is not a translation.
                echoed = [key for key, value in strings.items()
                          if value == source[key]["text"] and len(source[key]["text"]) > 24]
                self.assertLess(len(echoed), 12, f"{language.code} echoes English: {echoed[:6]}")

    def test_evidence_survives_every_translation(self) -> None:
        """A name the visitor types, clicks, or verifies is not translatable."""
        source = json.loads((SITE / "i18n" / "en.json").read_text(encoding="utf-8"))["strings"]
        for language in self.i18n.LANGUAGES[1:]:
            strings = json.loads(
                (SITE / "i18n" / f"{language.code}.json").read_text(encoding="utf-8"))["strings"]
            for key, entry in source.items():
                lost = [name for name in self.i18n.EVIDENCE
                        if name in entry["text"] and name not in strings[key]]
                with self.subTest(language=language.code, key=key):
                    self.assertEqual([], lost, entry["text"][:70])

    def test_glossary_is_machine_readable_and_mostly_followed(self) -> None:
        """The terminology table in GLOSSARY.md is parsed, not just prose.

        Adherence is reported, never gated: inflection ("revisa" for
        "revisión"), gender agreement and compounds ("カラートレイ") all read as
        misses while being correct, so the number is a smell test, not a score.
        """
        glossary = self.i18n.load_glossary()
        source = self.i18n.extract(write=False)
        self.assertEqual({language.code for language in self.i18n.LANGUAGES[1:]}, set(glossary))
        for code, terms in glossary.items():
            with self.subTest(language=code):
                self.assertGreater(len(terms), 20, "the terminology table did not parse")
                self.assertIn("silhouette", terms)
                hit, total, _ = self.i18n.glossary_report(
                    source, self.i18n.load_catalog(code), terms)
                # Deliberately loose. Spanish inflection alone ("renderizado"
                # for "renderizar") costs ~10 points, so the floor catches a
                # term splitting in two, not a catalog being imperfect.
                self.assertGreater(hit / total, 0.75, f"{code} drifted from the glossary")

    def test_placeholder_contract_round_trips(self) -> None:
        unit = self.i18n.Unit()
        unit.add_text("clean ")
        unit.atomic_slot("<code>check</code>")
        unit.add_text(" and ")
        index = unit.open_slot('<a href="/x">')
        unit.add_text("ship")
        unit.close_slot(index, "</a>")
        self.assertEqual("clean <0/> and <1>ship</1>", unit.message)
        self.assertEqual("", unit.problem("<1>出荷</1>と <0/>"))
        self.assertEqual('<a href="/x">出荷</a>と <code>check</code>',
                         unit.render("<1>出荷</1>と <0/>"))
        self.assertIn("dropped", unit.problem("clean <0/>"))
        self.assertIn("self-closing", unit.problem("<0>x</0><1>y</1>"))
        self.assertIn("never closed", unit.problem("<0/><1>y"))
        self.assertIn("&lt;", unit.render("<0/> a < b <1>c</1>"))


if __name__ == "__main__":
    unittest.main()
