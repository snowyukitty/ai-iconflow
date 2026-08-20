import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from iconflow import qa


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
