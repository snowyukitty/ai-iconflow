import base64
import io
import importlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

build_module = importlib.import_module("iconflow.build")


def png(size=64, color=(20, 120, 240, 255), *, sparse=False):
    with tempfile.SpooledTemporaryFile() as f:
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0) if sparse else color)
        if sparse:
            margin = max(1, size // 4)
            ImageDraw.Draw(im).ellipse(
                [margin, margin, size - margin - 1, size - margin - 1], fill=color
            )
        im.save(f, "PNG")
        f.seek(0)
        return f.read()


def png_image(data):
    return Image.open(io.BytesIO(data)).convert("RGBA")


def ico_entries(data):
    _reserved, _kind, count = struct.unpack("<HHH", data[:6])
    entries = []
    for index in range(count):
        start = 6 + index * 16
        width, height, _colors, _reserved, _planes, _bpp, length, offset = struct.unpack(
            "<BBBBHHII", data[start:start + 16]
        )
        entries.append((width or 256, height or 256, data[offset:offset + length]))
    return entries


def icns_entries(data):
    entries = []
    offset = 8
    while offset < len(data):
        kind = data[offset:offset + 4]
        length = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        entries.append((kind, data[offset + 8:offset + length]))
        offset += length
    return entries


class BuildTests(unittest.TestCase):
    def test_normalize_targets_rejects_unknown(self):
        with self.assertRaises(ValueError):
            build_module.normalize_targets(["web", "typo"])

    def test_normalize_targets_preserves_canonical_order(self):
        self.assertEqual(
            build_module.normalize_targets(["tray", "web"]),
            ["web", "tray"],
        )
        self.assertEqual(build_module.normalize_targets(["all"]), list(build_module.TARGETS))

    def test_windows_tiles_emit_expected_png_sizes(self):
        calls = []

        class Cache:
            def png(self, size):
                calls.append(size)
                return png(512)

        with tempfile.TemporaryDirectory() as tmp:
            produced = []
            build_module.build_windows_tiles(Cache(), Path(tmp), "#112233", produced)
            self.assertEqual(calls, [512])
            expected = {
                "mstile-70x70.png": (70, 70),
                "mstile-144x144.png": (144, 144),
                "mstile-150x150.png": (150, 150),
                "mstile-310x310.png": (310, 310),
                "mstile-310x150.png": (310, 150),
            }
            self.assertEqual(set(produced), set(expected))
            for name, size in expected.items():
                with Image.open(Path(tmp) / name) as im:
                    self.assertEqual(im.size, size)

    def test_tauri_matches_png_set_and_canonical_ico_order(self):
        class Cache:
            def png(self, size):
                return png(size)

            def many(self, sizes):
                return {size: self.png(size) for size in sizes}

        with tempfile.TemporaryDirectory() as tmp:
            produced = []
            build_module.build_tauri(Cache(), Path(tmp), produced)
            root = Path(tmp)
            expected_pngs = {
                "icons/32x32.png": (32, 32),
                "icons/64x64.png": (64, 64),
                "icons/128x128.png": (128, 128),
                "icons/128x128@2x.png": (256, 256),
                "icons/icon.png": (512, 512),
            }
            for name, expected_size in expected_pngs.items():
                with Image.open(root / name) as image:
                    self.assertEqual(image.size, expected_size)
            frames = ico_entries((root / "icons/icon.ico").read_bytes())

        self.assertEqual([width for width, _height, _png in frames], [32, 16, 24, 48, 64, 256])
        self.assertTrue(set(expected_pngs).issubset(produced))

    def test_electron_radius_is_applied_to_png_ico_and_icns_frames(self):
        class Cache:
            def png(self, size):
                return png(size)

        with tempfile.TemporaryDirectory() as tmp:
            produced = []
            build_module.build_electron(Cache(), Path(tmp), 0.18, produced)
            root = Path(tmp) / "build"
            top = png_image((root / "icon.png").read_bytes())
            ico = ico_entries((root / "icon.ico").read_bytes())
            icns = icns_entries((root / "icon.icns").read_bytes())

        self.assertEqual(top.getpixel((0, 0))[3], 0)
        self.assertEqual([width for width, _height, _data in ico], [32, 16, 24, 48, 64, 256])
        for width, height, frame in ico:
            image = png_image(frame)
            self.assertEqual(image.size, (width, height))
            self.assertEqual(image.getpixel((0, 0))[3], 0)
        for _kind, frame in icns:
            self.assertEqual(png_image(frame).getpixel((0, 0))[3], 0)
        self.assertEqual(produced, ["build/icon.png", "build/icon.ico", "build/icon.icns"])

    def test_preview_assets_are_exact_and_do_not_write(self):
        class Cache:
            def png(self, size):
                return png(size, sparse=True)

        assets = build_module.preview_assets(Cache(), "web", bg_color="#123456")
        self.assertEqual(set(assets), {
            "apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-512-maskable.png"
        })
        maskable = png_image(assets["icon-512-maskable.png"])
        self.assertEqual(maskable.size, (512, 512))
        self.assertEqual(maskable.getpixel((0, 0)), (18, 52, 86, 255))

    def test_tray_uses_explicit_semantic_cache_for_all_outputs_and_ts(self):
        class FullCardCache:
            def png(self, size):
                return png(size)

        class MarkCache:
            def png(self, size):
                return png(size, (220, 40, 60, 255), sparse=True)

        with tempfile.TemporaryDirectory() as tmp:
            produced = []
            build_module.build_tray(
                FullCardCache(), Path(tmp), True, produced, tray_cache=MarkCache()
            )
            root = Path(tmp) / "tray"
            color = png_image((root / "tray.png").read_bytes())
            template = png_image((root / "trayTemplate@2x.png").read_bytes())
            module = (root / "trayIcon.ts").read_text(encoding="utf-8")
            encoded = module.split("base64,", 1)[1].split('"', 1)[0]

        self.assertEqual(color.getpixel((0, 0))[3], 0)
        self.assertGreater(color.getpixel((16, 16))[3], 200)
        self.assertEqual(template.getpixel((0, 0))[3], 0)
        self.assertGreater(template.getpixel((16, 16))[3], 200)
        self.assertEqual(base64.b64decode(encoded), png(32, (220, 40, 60, 255), sparse=True))
        self.assertIn("tray/trayIcon.ts", produced)

    def test_build_accepts_dedicated_tray_svg(self):
        class FakeRasterizer:
            def __init__(self, color_scheme="light"):
                self.color_scheme = color_scheme

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, svg, size, bg="transparent"):
                return png(size, sparse=("tray-mark" in svg))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = root / "master.svg"
            tray = root / "tray.svg"
            master.write_text('<svg viewBox="0 0 10 10"></svg>', encoding="utf-8")
            tray.write_text('<svg id="tray-mark" viewBox="0 0 10 10"></svg>', encoding="utf-8")
            # Patch the imported submodule directly.  ``iconflow`` also exports
            # a convenience ``build`` callable, so dotted-string resolution is
            # ambiguous on Python 3.10 even though the submodule is loaded.
            with patch.object(build_module, "Rasterizer", FakeRasterizer):
                produced = build_module.build(
                    master, root / "out", targets=["tray"], tray_svg=tray
                )
            template = png_image((root / "out/tray/trayTemplate.png").read_bytes())
        self.assertGreater(template.getpixel((8, 8))[3], 200)
        self.assertIn("tray/trayTemplate.png", produced)

    def test_radius_and_colors_are_validated_before_build(self):
        with self.assertRaisesRegex(ValueError, r"\[0, 0.5\]"):
            build_module.electron_frames(object(), 0.75, [16])
        with self.assertRaisesRegex(ValueError, "fully opaque"):
            build_module.preview_assets(object(), "web", bg_color="#ffffff00")


if __name__ == "__main__":
    unittest.main()
