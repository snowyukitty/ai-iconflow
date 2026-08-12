from __future__ import annotations

import json
import hashlib
import random
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from iconflow.config import load_config, load_review_receipt, svg_sha256


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
HTML_PAGES = (
    "index.html",
    "404.html",
    "gallery/index.html",
    "gallery/social-signals/index.html",
    "gallery/emoji-matrix/index.html",
    "gallery/emoji-matrix/all/index.html",
)

MATRIX_STYLE_ORDER = (
    "flat-geometric", "gradient-glow", "line-mark", "mascot", "duotone",
    "stencil-cut", "pixel-grid", "isometric", "cut-paper", "enamel",
    "blueprint", "stained-glass", "risograph", "clay", "woven",
    "glass-stack", "cel-shaded", "ink-brush", "chrome", "woodcut",
)
MATRIX_STYLES = set(MATRIX_STYLE_ORDER)


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
            "sitemap.xml",
            "_headers",
            "_redirects",
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
        self.assertIn('https://iconflow.pages.dev/', html)
        self.assertNotIn('https://ai-iconflow.pages.dev/', html)
        self.assertIn("Content-Security-Policy", (SITE / "_headers").read_text(encoding="utf-8"))

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

    def test_collection_routes_are_in_sitemap_and_gallery_navigation(self) -> None:
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        gallery = (SITE / "gallery" / "index.html").read_text(encoding="utf-8")
        for route in ("/gallery/social-signals/", "/gallery/emoji-matrix/", "/gallery/emoji-matrix/all/"):
            self.assertIn(f"https://iconflow.pages.dev{route}", sitemap)
            self.assertIn(route, gallery)
        self.assertIn("100 admitted cases", gallery)


if __name__ == "__main__":
    unittest.main()
