# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The brand kit (iconflow/brand.py): composition, manifest, propagation, outline."""
import base64
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from iconflow import brand
from iconflow.cli import DEMO_FILES, _resource, main

WORDMARK = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">'
    '<defs><linearGradient id="g"><stop offset="0" stop-color="#000"/></linearGradient></defs>'
    '<rect x="0" y="10" width="400" height="80" fill="currentColor"/>'
    '<rect id="dot" x="10" y="10" width="10" height="10" fill="url(#g)"/></svg>'
)


def fake_png(width, height=None):
    image = Image.new("RGBA", (width, height or width), (40, 120, 200, 255))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class FakeRasterizer:
    def __init__(self, color_scheme="light", **_):
        self.color_scheme = color_scheme

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, _svg, size, bg="transparent"):
        return fake_png(size)

    def render_rect(self, _svg, width, height, bg="transparent"):
        return fake_png(width, height)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue()


class CompositionTests(unittest.TestCase):
    def test_lockups_keep_the_clear_space_unit_around_the_content(self):
        layout = brand.lockup_layout("horizontal", 4.0, mark=512)
        unit = 512 * brand.DEFAULT_CLEAR_SPACE
        self.assertEqual(layout.mark, (unit, unit, 512))
        self.assertAlmostEqual(layout.height, 512 + 2 * unit)
        x, y, w, h = layout.wordmark
        self.assertAlmostEqual(h, 512 * brand.DEFAULT_WORDMARK_SCALE)
        self.assertAlmostEqual(x + w + unit, layout.width)
        self.assertAlmostEqual(y + h / 2, unit + 256)   # centred on the mark
        stacked = brand.lockup_layout("stacked", 4.0, mark=512)
        self.assertGreater(stacked.height, stacked.width / 2)

    def test_live_text_in_a_wordmark_is_refused(self):
        with self.assertRaisesRegex(brand.BrandError, "Outline it"):
            brand.validate_wordmark('<svg viewBox="0 0 10 10"><text>Hi</text></svg>', "wordmark")

    def test_nested_sources_get_prefixed_ids_so_they_cannot_collide(self):
        svg, _layout = brand.lockup_svg(
            WORDMARK.replace("currentColor", "#123"), WORDMARK, kind="horizontal",
            ink="#FFFFFF", background=None,
            spec=brand.BrandSpec("X", Path("m.svg"), Path("w.svg"), None,
                                 "#000000", "#FFFFFF", "#FFFFFF", "#000000", Path("out")),
        )
        self.assertIn('id="mark-g"', svg)
        self.assertIn('id="word-g"', svg)
        self.assertIn("url(#word-g)", svg)
        self.assertIn('color="#FFFFFF"', svg)
        self.assertNotIn('id="g"', svg)

    def test_contrast_ratio_matches_wcag(self):
        self.assertAlmostEqual(brand._contrast("#000000", "#FFFFFF"), 21.0, places=1)


class KitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        for name in DEMO_FILES:
            (self.dir / name).write_bytes(_resource("demo", name).read_bytes())
        (self.dir / "wordmark.svg").write_text(WORDMARK, encoding="utf-8")
        config = self.dir / "iconflow.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "[review]", '[brand]\nwordmark = "wordmark.svg"\nlight = "#FFF4E8"\n\n[review]'),
            encoding="utf-8",
        )
        self.config = config

    def build(self):
        with mock.patch("iconflow.rasterize.Rasterizer", FakeRasterizer):
            return run(["brand", "build", "--config", str(self.config),
                        "--review", str(self.dir / "master-review.json")])

    def test_kit_is_written_and_every_file_is_hash_recorded(self):
        code, envelope, _ = self.build()
        self.assertEqual(code, 0, envelope)
        manifest = json.loads((self.dir / "brand-kit" / brand.MANIFEST).read_text(encoding="utf-8"))
        paths = {entry["path"] for entry in manifest["files"]}
        for expected in ("lockups/horizontal-on-dark.svg", "lockups/stacked-on-light.png",
                         "tiles/tile-dark-1024.png", "social/og-1200x630.png",
                         "social/github-social-1280x640.svg", "social/banner-1500x500.png",
                         "guides/clear-space-and-minimum-size.png", "mark/master.svg"):
            self.assertIn(expected, paths)
        for entry in manifest["files"]:
            data = (self.dir / "brand-kit" / entry["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], entry["path"])
        self.assertEqual(manifest["approval"]["scores"]["distinctiveness"], 5)
        self.assertEqual(manifest["retired"], [])

    def test_an_unapproved_mark_gets_no_brand_kit(self):
        master = self.dir / "master.svg"
        master.write_text(master.read_text(encoding="utf-8") + "<!-- edit -->", encoding="utf-8")
        code, envelope, _ = self.build()
        self.assertEqual(code, 1)
        self.assertEqual(envelope["warnings"][0]["code"], "receipt-stale-source")
        self.assertFalse((self.dir / "brand-kit").exists())

    def test_a_new_mark_retires_the_old_hashes_and_sync_finds_them(self):
        self.build()
        kit = self.dir / "brand-kit"
        old = json.loads((kit / brand.MANIFEST).read_text(encoding="utf-8"))
        old_tile = (kit / "tiles" / "tile-dark-192.png").read_bytes()
        # A consuming project still carrying the old tile, inline and as a file.
        project = self.dir / "site"
        (project / "public").mkdir(parents=True)
        (project / "public" / "tile.png").write_bytes(old_tile)
        (project / "app.ts").write_text(
            'export const ICON = "data:image/png;base64,' + base64.b64encode(old_tile).decode() + '";',
            encoding="utf-8")
        (project / "node_modules").mkdir()
        (project / "node_modules" / "copy.png").write_bytes(old_tile)
        # The mark changes and is re-approved through the config fallback.
        manifest = dict(old)
        manifest["mark_sha256"] = "0" * 64           # pretend the previous build was another mark
        (kit / brand.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        with mock.patch("iconflow.rasterize.Rasterizer", FakeRasterizer):
            code, envelope, _ = run(["brand", "build", "--config", str(self.config),
                                     "--review", str(self.dir / "master-review.json")])
        self.assertEqual(code, 0)
        new = json.loads((kit / brand.MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(new["retired"][0]["mark_sha256"], "0" * 64)
        # Fake renders are identical across marks, so mark one asset as changed.
        (kit / "tiles" / "tile-dark-192.png").write_bytes(fake_png(193))
        new["files"] = [e for e in new["files"] if e["path"] != "tiles/tile-dark-192.png"]
        (kit / brand.MANIFEST).write_text(json.dumps(new), encoding="utf-8")
        code, envelope, _ = run(["brand", "sync", "--manifest", str(kit), "--project", str(project)])
        self.assertEqual(code, 1)
        stale = {(hit["path"], hit["where"]) for hit in envelope["outputs"]["stale"]}
        self.assertEqual(stale, {("public/tile.png", "file"), ("app.ts", "data-url")})
        self.assertTrue(all(w["code"] == "brand-stale" for w in envelope["warnings"]))


class OutlineTests(unittest.TestCase):
    def font(self, path: Path, licence: str):
        try:
            from fontTools.fontBuilder import FontBuilder
            from fontTools.pens.ttGlyphPen import TTGlyphPen
        except ImportError:
            self.skipTest("fontTools is not installed (pip install iconflow[brand])")
        builder = FontBuilder(1000, isTTF=True)
        builder.setupGlyphOrder([".notdef", "A"])
        builder.setupCharacterMap({ord("A"): "A"})
        pen = TTGlyphPen(None)
        pen.moveTo((50, 0))
        pen.lineTo((450, 0))
        pen.lineTo((250, 700))
        pen.closePath()
        glyph = pen.glyph()
        builder.setupGlyf({".notdef": TTGlyphPen(None).glyph(), "A": glyph})
        builder.setupHorizontalMetrics({".notdef": (500, 0), "A": (500, 50)})
        builder.setupHorizontalHeader(ascent=800, descent=-200)
        builder.setupNameTable({"familyName": "Test", "styleName": "Bold",
                                "licenseDescription": licence})
        builder.setupOS2()
        builder.setupPost()
        builder.save(str(path))

    def test_an_ofl_font_outlines_to_a_currentcolor_wordmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.ttf"
            self.font(path, "This Font Software is licensed under the SIL Open Font License, Version 1.1.")
            svg, licence = brand.outline_wordmark("AA", path)
        self.assertIn('fill="currentColor"', svg)
        self.assertIn("viewBox=", svg)
        self.assertTrue(licence["permissive"])
        brand.validate_wordmark(svg, "wordmark")

    def test_an_unknown_licence_is_refused_unless_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.ttf"
            self.font(path, "All rights reserved.")
            with self.assertRaisesRegex(brand.BrandError, "licence-ok"):
                brand.outline_wordmark("A", path)
            svg, licence = brand.outline_wordmark("A", path, licence_ok="studio licence #42")
        self.assertIn("licence-ok: studio licence #42", svg)
        self.assertEqual(licence["licence_ok"], "studio licence #42")


if __name__ == "__main__":
    unittest.main()
