from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from iconflow import review


def image_png(size, draw=None):
    with tempfile.SpooledTemporaryFile() as f:
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        if draw:
            draw(im)
        else:
            painter = ImageDraw.Draw(im)
            painter.rounded_rectangle(
                [max(1, size // 12), max(1, size // 12), size - max(2, size // 12), size - max(2, size // 12)],
                radius=max(1, size // 5),
                fill=(30, 130, 230, 255),
            )
            painter.rectangle(
                [size // 3, size // 3, max(size // 3 + 1, size * 2 // 3), max(size // 3 + 1, size * 2 // 3)],
                fill=(255, 255, 255, 255),
            )
        im.save(f, "PNG")
        f.seek(0)
        return f.read()


class FakeRasterizer:
    def __init__(self, color_scheme="light"):
        self.color_scheme = color_scheme

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, svg, size, bg="transparent"):
        return image_png(size)


class ReviewTests(unittest.TestCase):
    def test_visual_silhouette_preserves_internal_white_cut(self):
        def draw(im):
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([4, 4, 60, 60], radius=10, fill=(30, 130, 230, 255))
            d.rectangle([22, 22, 42, 42], fill=(255, 255, 255, 255))

        sil = review.visual_silhouette(image_png(64, draw))
        self.assertLess(sil.getpixel((8, 8))[0], 40)      # blue card becomes black.
        self.assertGreater(sil.getpixel((32, 32))[0], 240)  # white glyph stays a cut-out.

        alpha = review.alpha_silhouette(image_png(64, draw))
        self.assertLess(alpha.getpixel((32, 32))[0], 40)  # alpha footprint cannot see the cut-out.

    def test_contact_sheet_allocates_room_for_32px_zoom_and_new_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            out = Path(tmp) / "review.png"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with patch("iconflow.review.Rasterizer", FakeRasterizer):
                review.contact_sheet(master, out)
            with Image.open(out) as im:
                size = im.size
        self.assertEqual(size[1], 2390)
        self.assertGreater(size[0], 1800)

    def test_interactive_review_writes_self_contained_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            out = Path(tmp) / "review.html"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with patch("iconflow.review.Rasterizer", FakeRasterizer):
                review.interactive_review(
                    master,
                    out,
                    options=review.ReviewOptions(
                        name="Proof App",
                        user_job="ship one icon family",
                        essence="proof",
                        targets=("web", "electron", "tray"),
                        electron_radius=0.18,
                        warnings=("thin counter",),
                    ),
                )
            text = out.read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,", text)
        self.assertIn("Visual silhouette", text)
        self.assertIn("data-bg", text)
        self.assertIn("Review Lab", text)
        self.assertIn("Target contexts", text)
        self.assertIn("ship one icon family", text)
        self.assertIn("Export review.json", text)
        self.assertIn('"warnings": ["thin counter"]', text)
        self.assertIn('"build": {', text)
        self.assertIn('"electron_radius": 0.18', text)
        self.assertIn("--app-theme:#17181C", text)
        self.assertIn("Automated warning blocks ship", text)
        self.assertIn(
            hashlib.sha256('<svg viewBox="0 0 1024 1024"></svg>'.encode("utf-8")).hexdigest(),
            text,
        )
        self.assertIn('data-dark="data:image/png;base64,', text)
        self.assertNotIn("https://", text)


if __name__ == "__main__":
    unittest.main()
