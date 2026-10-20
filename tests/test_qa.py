# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from iconflow import qa


class _NoRender:
    """A transparent render at every size: the static probes alone speak."""

    color_scheme = "light"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, _svg, size, bg="transparent"):
        out = io.BytesIO()
        Image.new("RGBA", (size, size), (0, 0, 0, 0)).save(out, "PNG")
        return out.getvalue()


#: Spellings whose parse was compared with Chromium's own (F6-02).
VIEWBOX_SPELLINGS = (
    "0 0 24+24", "0 0 24 24", " 0,0,1024,512 ", "0 0 1.024e3 5.12e2", "1e999 0 24 24",
    "0 0 24 24,", "0 0 1. 2", "0,,0 1 1", "0 0 1024", "0 0 24-24", ".5.5 1 1",
    "0 0 1024.", "0\t0\n24 24", "0 0 1e 2", "0 0 24 24 5", "+0 -0 +1e+1 1E1",
    # Blink keeps 32-bit floats (F7-01): rounding, range, and plain fractions.
    "0 0 100000000+100000001", "1e39 0 24 24", "0 0 3.4e38 3.4e38", "0 0 0.1 0.3",
    "0 0 1e-50 1",
    # Blink sums digits step by step in 32-bit floats, and refuses an exponent
    # above 38 before applying it (F8-01).
    "0 0 199999989+200000000", "0.1e39 0 24 24", "0 0 1.5e-45 1", "0 0 16777217 16777216",
    "0 0 123456789.123 1", "0 0 0.30000001 0.3", "0 0 3.40282347e38 1", "0 0 1ex 1",
    "0 0 9999999999999999999999999999999999999999 1", "0 0 .000001e-38 1",
    # An exponent that overflows to -inf while it is summed (F9-01).
    "1e-9999999999999999999999999999999999999999 0 24 24",
)


@unittest.skipUnless(__import__("os").environ.get("ICONFLOW_BROWSER_TESTS") == "1",
                     "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium")
class ViewBoxOracleTests(unittest.TestCase):
    def test_F6_02_viewbox_numbers_agree_with_chromium(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                for value in VIEWBOX_SPELLINGS:
                    page.set_content(f'<svg id="s" xmlns="http://www.w3.org/2000/svg" viewBox="{value}"></svg>')
                    box = page.evaluate(
                        "() => { const b = document.getElementById('s').viewBox.baseVal;"
                        " return [b.x, b.y, b.width, b.height]; }")
                    ours = qa._viewbox_numbers(value)
                    with self.subTest(value=value):
                        # Chromium leaves an unusable value as 0 0 0 0.
                        self.assertEqual(ours if ours is not None else [0, 0, 0, 0], box)
            finally:
                browser.close()

    def test_F9_01_random_spellings_agree_with_chromium(self):
        import random

        from playwright.sync_api import sync_playwright

        rng = random.Random(7)
        pieces = ["0", "1", "24", "1024", "199999989", "16777217", "3.4e38", "1e-45", ".5", "5.",
                  "1e", "e5", "+", "-", ",", " ", "\t", ".", "1e39", "0.1e39",
                  "1e-999999999999999999999999", "x", "m", "9" * 41, "0.30000001"]
        values = ["".join(rng.choice(pieces) for _ in range(rng.randint(1, 9))) for _ in range(400)]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                boxes = browser.new_page().evaluate("""(values) => values.map(v => {
                    const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    s.setAttribute('viewBox', v);
                    const b = s.viewBox.baseVal;
                    return [b.x, b.y, b.width, b.height];
                })""", values)
            finally:
                browser.close()
        for value, box in zip(values, boxes):
            ours = qa._viewbox_numbers(value)
            with self.subTest(value=value):
                self.assertEqual(ours if ours is not None else [0, 0, 0, 0], box)


class QaTests(unittest.TestCase):
    def test_detail_outside_safe_zone_detects_edge_detail(self):
        centered = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
        ImageDraw.Draw(centered).rectangle([52, 52, 76, 76], fill=(0, 0, 0, 255))

        edge = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
        ImageDraw.Draw(edge).rectangle([92, 92, 110, 110], fill=(0, 0, 0, 255))

        self.assertLess(qa._detail_outside_safe_zone(centered), 0.05)
        self.assertGreater(qa._detail_outside_safe_zone(edge), 0.20)

    def test_maskable_audit_ignores_only_large_container_outer_edge(self):
        card = Image.new("RGBA", (128, 128), (245, 241, 232, 255))
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle([16, 16, 112, 112], radius=20, fill=(23, 24, 28, 255))
        draw.rectangle([52, 52, 76, 76], fill=(255, 91, 61, 255))
        self.assertLess(qa._detail_outside_safe_zone(card), 0.05)

        draw.rectangle([94, 94, 106, 106], fill=(255, 91, 61, 255))
        self.assertGreater(qa._detail_outside_safe_zone(card), 0.08)

    def test_renderer_safety_warnings_cover_active_and_external_content(self):
        active = qa._renderer_safety_warnings(
            '<svg><script>Math.random()</script><image href="https://example.com/a.png"/></svg>'
        )
        self.assertEqual(len(active), 2)
        self.assertIn("deterministic", active[0])
        self.assertIn("external resource", active[1])
        self.assertEqual(
            qa._renderer_safety_warnings(
                '<svg><style>.mark{fill:url("#g")}</style><defs>'
                '<linearGradient id="g"/></defs><use href="#shape"/></svg>'
            ),
            [],
        )
        self.assertTrue(qa._renderer_safety_warnings(
            '<svg><style>@import "https://example.com/icon.css";</style></svg>'
        ))
        for reference in (
            '<image href="http://example.com/a.png"/>',
            '<image href="https://example.com/a.png"/>',
            '<image href="file:///private/icon.png"/>',
            '<use xlink:href="//example.com/shape.svg#mark"/>',
            '<style>.mark{fill:url(file:///private/paint.svg)}</style>',
        ):
            with self.subTest(reference=reference):
                warnings = qa._renderer_safety_warnings(f"<svg>{reference}</svg>")
                self.assertTrue(any("external resource" in item for item in warnings))

        self.assertEqual(
            qa._renderer_safety_warnings(
                '<svg><image href="data:image/png;base64,AA=="/>'
                '<use href="#local"/><style>.x{fill:url(data:image/png;base64,AA==)}</style></svg>'
            ),
            [],
        )

    def test_distinctiveness_flags_live_text_monogram(self):
        # A live <text> glyph is the mechanically-detectable monogram trap.
        text_warnings = qa._distinctiveness_warnings(
            '<svg viewBox="0 0 1024 1024"><rect width="1024" height="1024" rx="225" '
            'fill="#8b5cf6"/><text x="512" y="512" font-size="620">S</text></svg>'
        )
        self.assertEqual(len(text_warnings), 1)
        self.assertIn("monogram trap", text_warnings[0])
        # <tspan> is caught too.
        self.assertTrue(qa._distinctiveness_warnings("<svg><text><tspan>H</tspan></text></svg>"))

    def test_distinctiveness_ignores_path_only_marks(self):
        # A path-drawn mark — even a path letter — must NOT be flagged, because it
        # is raster-indistinguishable from a good abstract mark. Only live text is.
        self.assertEqual(
            qa._distinctiveness_warnings(
                '<svg viewBox="0 0 1024 1024"><path d="M300 268 h124 v172 h176 v-172 '
                'h124 v488 h-124 v-188 h-176 v188 h-124 z" fill="#fff"/></svg>'
            ),
            [],
        )
        # A <textPath> reference or the word "context" in a comment is not a glyph.
        self.assertEqual(
            qa._distinctiveness_warnings('<svg><!-- richer context --><path d="M0 0"/></svg>'),
            [],
        )

    def test_check_audits_canonical_final_maskable_asset(self):
        def image_png(size):
            image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            if size < 512:
                margin = max(1, size // 4)
                draw.rectangle(
                    [margin, margin, size - margin, size - margin], fill=(0, 0, 0, 255)
                )
            else:
                draw.rectangle([420, 420, 470, 470], fill=(0, 0, 0, 255))
            out = io.BytesIO()
            image.save(out, "PNG")
            return out.getvalue()

        class FakeRasterizer:
            def __init__(self, **options):
                self.options = options

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, _svg, size, bg="transparent"):
                return image_png(size)

        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with patch("iconflow.qa.Rasterizer", FakeRasterizer):
                warnings = qa.check(master)
            with patch("iconflow.qa.Rasterizer", side_effect=AssertionError("must reuse caller")):
                reused_warnings = qa.check(master, rasterizer=FakeRasterizer())
        self.assertTrue(any("Final maskable asset audit" in warning for warning in warnings))
        self.assertEqual(warnings, reused_warnings)

    def test_PF10_the_root_viewbox_is_read_the_way_chromium_reads_it(self):
        cases = {
            '<svg viewBox="0 0 1024 1024"/>': (1024.0, 1024.0),
            '<svg viewBox="0,0,1024,512"/>': (1024.0, 512.0),
            '<svg viewBox="0 0 1.024e3 5.12e2"/>': (1024.0, 512.0),
            '<svg viewBox=" 0 0 1024, 1024 "/>': (1024.0, 1024.0),
            # A sign starts the next number with no separator (F6-02).
            '<svg viewBox="0 0 24+24"/>': (24.0, 24.0),
        }
        for text, size in cases.items():
            with self.subTest(text=text):
                self.assertEqual(qa._root_viewbox(text)[1], size)
        # Not the icon's viewBox: a nested one, a lowercase name, an unusable value.
        self.assertEqual(qa._root_viewbox('<svg><svg viewBox="0 0 9 9"/></svg>'), (None, None))
        # The renderer inlines the SVG in HTML, which reads the name in any case (IR07).
        self.assertEqual(qa._root_viewbox('<svg viewbox="0 0 9 9"/>'), ("0 0 9 9", (9.0, 9.0)))
        for value in ("0 0 -5 10", "0 0 0 0", "a b c d", "0 0 1024", "1e999 0 24 24",
                      "0 0 1. 2", "0 0 24 24,"):
            with self.subTest(value=value):
                self.assertEqual(qa._root_viewbox(f'<svg viewBox="{value}"/>'), (value, None))

    def test_F7_01_sizes_are_compared_as_chromium_stores_them(self):
        # 100000000 and 100000001 are one 32-bit float: square to Chromium.
        found = qa.check("master.svg", rasterizer=_NoRender(), maskable=False,
                         text='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100000000+100000001"/>')
        self.assertFalse(any(f.code == "viewbox" for f in found), found)
        for refused in ("1e39 0 24 24", "0.1e39 0 24 24"):
            found = qa.check("master.svg", rasterizer=_NoRender(), maskable=False,
                             text=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{refused}"/>')
            self.assertTrue(any(f.startswith("SVG has no viewBox Chromium can use") for f in found))
        # An exponent summed past the float range is -inf: the origin is 0 (F9-01).
        found = qa.check("master.svg", rasterizer=_NoRender(), maskable=False,
                         text='<svg xmlns="http://www.w3.org/2000/svg" '
                              'viewBox="1e-9999999999999999999999999999999999999999 0 24 24"/>')
        self.assertFalse(any(f.code == "viewbox" for f in found), found)
        # Summed in 32-bit floats, 199999989 is 200000000 (F8-01).
        found = qa.check("master.svg", rasterizer=_NoRender(), maskable=False,
                         text='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 199999989+200000000"/>')
        self.assertFalse(any(f.code == "viewbox" for f in found), found)

    def test_F9_01_the_viewbox_parser_never_raises(self):
        import random

        rng = random.Random(1001)
        alphabet = "0123456789+-.eExm, \t"
        for _ in range(5000):
            value = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
            if rng.random() < 0.3:
                value = value.replace("e", "e" + "9" * rng.randint(1, 60), 1)
            with self.subTest(value=value):
                result = qa._viewbox_numbers(value)
                self.assertTrue(result is None or (len(result) == 4 and all(
                    __import__("math").isfinite(n) for n in result)))

    def test_PF10_a_non_square_root_cannot_hide_behind_its_syntax(self):
        for text in ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0,0,1024,512"/>',
                     '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1.024e3 512"/>'):
            with self.subTest(text=text):
                found = qa.check("master.svg", text=text, rasterizer=_NoRender(), maskable=False)
                self.assertIn("viewbox", [f.code for f in found])
                self.assertTrue(any("not square" in f for f in found))
        found = qa.check("master.svg", rasterizer=_NoRender(), maskable=False,
                         text='<svg xmlns="http://www.w3.org/2000/svg"><svg viewBox="0 0 9 9"/></svg>')
        self.assertTrue(any(f.startswith("SVG has no viewBox") for f in found))
        found = qa.check("master.svg", rasterizer=_NoRender(), maskable=False,
                         text='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 -1 1"/>')
        self.assertTrue(any(f.startswith("SVG has no viewBox Chromium can use") for f in found))
        self.assertEqual(qa.warning_code(found[0]), "viewbox")

    def test_check_rejects_translucent_maskable_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fully opaque"):
                qa.check(master, maskable_bg="#ffffff00")

    def _tray_rasterizer(self, *, features: bool, cut: bool):
        """A fake tray source: a warm disc, optionally striped, optionally punched."""

        def tray_png(size):
            image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.ellipse([4, 4, size - 5, size - 5], fill=(255, 244, 232, 255))
            if features:
                for index, x in enumerate(range(8, size - 8, 4)):
                    fill = (255, 90, 79, 255) if index % 2 else (132, 94, 194, 255)
                    draw.rectangle([x, 8, x + 1, size - 9], fill=fill)
            if cut:
                draw.ellipse([13, 13, 19, 19], fill=(0, 0, 0, 0))
            out = io.BytesIO()
            image.save(out, "PNG")
            return out.getvalue()

        class FakeRasterizer:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, _svg, size, bg="transparent"):
                return tray_png(size)

        return FakeRasterizer

    def _tray_source(self, tmp):
        source = Path(tmp) / "tray.svg"
        source.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
        return source

    def test_tray_audit_flags_a_template_that_lost_every_feature(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._tray_source(tmp)
            fake = self._tray_rasterizer(features=True, cut=False)
            with patch("iconflow.qa.Rasterizer", fake):
                warnings = qa.tray_template_warnings(source, template_mode="alpha")
        self.assertEqual(len(warnings), 1)
        self.assertIn("featureless silhouette", warnings[0])

    def test_tray_audit_accepts_a_broad_transparent_cut(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._tray_source(tmp)
            fake = self._tray_rasterizer(features=True, cut=True)
            with patch("iconflow.qa.Rasterizer", fake):
                warnings = qa.tray_template_warnings(source, template_mode="alpha")
        self.assertEqual(warnings, [])

    def test_tray_audit_ignores_a_source_with_no_interior_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._tray_source(tmp)
            fake = self._tray_rasterizer(features=False, cut=False)
            with patch("iconflow.qa.Rasterizer", fake):
                warnings = qa.tray_template_warnings(source, template_mode="alpha")
        self.assertEqual(warnings, [])

    def test_tray_audit_reuses_a_caller_supplied_rasterizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._tray_source(tmp)
            fake = self._tray_rasterizer(features=True, cut=False)
            with patch("iconflow.qa.Rasterizer", side_effect=AssertionError("must reuse caller")):
                warnings = qa.tray_template_warnings(
                    source, template_mode="alpha", rasterizer=fake(),
                )
        self.assertEqual(len(warnings), 1)

    def test_tray_audit_rejects_an_unknown_template_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._tray_source(tmp)
            with self.assertRaisesRegex(ValueError, "template mode"):
                qa.tray_template_warnings(source, template_mode="silhouette")

    def test_enclosed_transparent_pixels_ignores_background(self):
        image = Image.new("L", (16, 16), 0)
        ImageDraw.Draw(image).rectangle([3, 3, 12, 12], fill=255)
        self.assertEqual(qa._enclosed_transparent_pixels(image), 0)
        ImageDraw.Draw(image).rectangle([6, 6, 8, 8], fill=0)
        self.assertEqual(qa._enclosed_transparent_pixels(image), 9)


if __name__ == "__main__":
    unittest.main()
