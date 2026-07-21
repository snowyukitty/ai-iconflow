from pathlib import Path
import struct
import tempfile
import unittest

from PIL import Image, ImageDraw

from iconflow import assemble


def png(size=16, color=(10, 20, 30, 255)):
    with tempfile.SpooledTemporaryFile() as out:
        Image.new("RGBA", (size, size), color).save(out, "PNG")
        out.seek(0)
        return out.read()


def open_png(data):
    with tempfile.SpooledTemporaryFile() as f:
        f.write(data)
        f.seek(0)
        return Image.open(f).convert("RGBA")


class AssembleTests(unittest.TestCase):
    def test_write_ico_packs_png_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "icon.ico"
            assemble.write_ico({16: png(16), 256: png(256)}, out)
            data = out.read_bytes()

        reserved, kind, count = struct.unpack("<HHH", data[:6])
        self.assertEqual((reserved, kind, count), (0, 1, 2))
        first_width = data[6]
        second_width = data[22]
        self.assertEqual(first_width, 16)
        self.assertEqual(second_width, 0)  # ICO stores 256 as 0.

    def test_write_ico_honors_explicit_platform_order(self):
        order = (32, 16, 24, 48, 64, 256)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "icon.ico"
            assemble.write_ico({size: png(size) for size in order}, out, order=order)
            data = out.read_bytes()
        dimensions = [data[6 + index * 16] or 256 for index in range(len(order))]
        self.assertEqual(dimensions, list(order))

    def test_container_writers_reject_mislabeled_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "keyed as 16px"):
                assemble.write_ico({16: png(32)}, Path(tmp) / "bad.ico")
            with self.assertRaisesRegex(ValueError, "unsupported ICNS"):
                assemble.write_icns({24: png(24)}, Path(tmp) / "bad.icns")

    def test_contain_on_canvas_preserves_requested_size(self):
        out = assemble.contain_on_canvas(png(32), 310, 150, "#123456", 0.5)
        with tempfile.SpooledTemporaryFile() as f:
            f.write(out)
            f.seek(0)
            with Image.open(f) as im:
                self.assertEqual(im.size, (310, 150))

    def test_round_corners_validates_radius_and_clips_pixels(self):
        with self.assertRaisesRegex(ValueError, r"\[0, 0.5\]"):
            assemble.round_corners(png(32), 0.51)
        rounded = open_png(assemble.round_corners(png(32), 0.18))
        self.assertEqual(rounded.getpixel((0, 0))[3], 0)
        self.assertEqual(rounded.getpixel((16, 16))[3], 255)

    def test_maskable_asset_is_opaque_and_uses_canonical_padding(self):
        source = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        ImageDraw.Draw(source).rectangle([0, 0, 99, 99], fill=(255, 0, 0, 255))
        with tempfile.SpooledTemporaryFile() as f:
            source.save(f, "PNG")
            f.seek(0)
            result = open_png(assemble.maskable_asset(f.read(), "#112233"))
        self.assertEqual(result.getpixel((0, 0)), (17, 34, 51, 255))
        self.assertEqual(result.getpixel((50, 50)), (255, 0, 0, 255))
        self.assertEqual(result.getchannel("A").getextrema(), (255, 255))

    def test_padding_preserves_semitransparent_alpha_without_squaring_it(self):
        source = png(20, (10, 20, 30, 128))
        padded = open_png(assemble.pad(source, 0.10))
        self.assertEqual(padded.getpixel((10, 10))[3], 128)

    def test_template_auto_extracts_mark_instead_of_full_card_alpha(self):
        card = Image.new("RGBA", (32, 32), (20, 80, 140, 255))
        ImageDraw.Draw(card).polygon(
            [(10, 8), (24, 16), (10, 24), (14, 16)], fill=(255, 210, 40, 255)
        )
        with tempfile.SpooledTemporaryFile() as f:
            card.save(f, "PNG")
            f.seek(0)
            source = f.read()
        automatic = open_png(assemble.to_template(source))
        legacy = open_png(assemble.to_template(source, "alpha"))
        self.assertEqual(automatic.getpixel((0, 0))[3], 0)
        self.assertGreater(automatic.getpixel((20, 16))[3], 200)
        self.assertEqual(legacy.getpixel((0, 0))[3], 255)
        self.assertEqual(automatic.getpixel((20, 16))[:3], (0, 0, 0))

    def test_template_auto_requires_semantic_source_when_card_has_no_mark(self):
        with self.assertRaisesRegex(ValueError, "dedicated tray SVG"):
            assemble.to_template(png(32))

    def test_opaque_color_rejects_alpha(self):
        with self.assertRaisesRegex(ValueError, "fully opaque"):
            assemble.opaque_color("#ffffff00")


if __name__ == "__main__":
    unittest.main()
