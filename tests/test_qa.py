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
        self.assertTrue(any("Final maskable asset audit" in warning for warning in warnings))

    def test_check_rejects_translucent_maskable_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fully opaque"):
                qa.check(master, maskable_bg="#ffffff00")


if __name__ == "__main__":
    unittest.main()
