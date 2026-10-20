# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
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
        # "all" is the app-icon set; an emote pack is only built when named.
        self.assertEqual(build_module.normalize_targets(["all"]), list(build_module.APP_TARGETS))
        self.assertNotIn("emote", build_module.normalize_targets(["all"]))
        self.assertEqual(build_module.normalize_targets(["emote", "web"]), ["web", "emote"])

    def test_emote_target_renders_each_platform_size_natively(self):
        calls = []

        class Cache:
            def png(self, size):
                calls.append(size)
                return png(size)

        assets = build_module.preview_assets(Cache(), "emote")
        self.assertEqual(sorted(calls), [28, 56, 112, 128])
        self.assertEqual(set(assets), {"emote/28.png", "emote/56.png", "emote/112.png", "emote/128.png"})

    def test_emote_over_its_upload_limit_fails_the_build(self):
        class Heavy:
            def png(self, size):
                return b"\x89PNG" + b"0" * (build_module.EMOTE_BUDGETS[size] + 1)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "upload limit"):
                build_module.build_emote(Heavy(), Path(tmp), [])
            self.assertFalse((Path(tmp) / "emote").exists())

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

    def test_output_tree_rejects_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "not-a-directory"
            file_path.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                build_module._validate_output_tree(file_path)

            output = Path(tmp) / "output"
            output.mkdir()
            target = Path(tmp) / "outside.txt"
            target.write_text("keep", encoding="utf-8")
            link = output / "favicon.ico"
            try:
                link.symlink_to(target)
            except (NotImplementedError, OSError):
                self.skipTest("symlink creation is unavailable on this platform")
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                build_module._validate_output_tree(output)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def _link_dir(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError):
            try:
                import _winapi

                _winapi.CreateJunction(str(target), str(link))
            except (ImportError, OSError, AttributeError):
                self.skipTest("no directory links on this platform")

    def test_PF02_build_refuses_a_link_above_its_output(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project" / "src").mkdir(parents=True)
            (root / "outside").mkdir()
            self._link_dir(root / "project" / "dist", root / "outside")
            # A literal "~" directory the project carries: the writer does not
            # expand it, so neither does the check (IR02).
            self._link_dir(root / "project" / "~", root / "outside")
            # Another spelling of an ancestor of the project (IR01).
            self._link_dir(root / "alias", root / "project")
            here = os.getcwd()
            os.chdir(root / "project")
            try:
                for out in ("dist/icons", "src/../dist/icons", "~/icons",
                            str(root / "alias" / "src" / ".." / "dist" / "icons")):
                    with self.subTest(out=out), \
                            self.assertRaisesRegex(ValueError, "link or junction"):
                        build_module.build("missing.svg", out, ["web"])
                self.assertIsNone(build_module.output_link("plain/icons"))
                self.assertIsNone(build_module.output_link("../outside/icons"))
                self.assertIsNone(build_module.output_link(str(root / "alias" / "src" / "icons")))
                if os.name == "nt":
                    # The extended-length spelling of the same path (VR01).
                    extended = "\\\\?\\" + str(root / "project" / "dist" / "icons")
                    self.assertIsNotNone(build_module.output_link(extended))
                    self.assertIsNone(build_module.output_link(
                        "\\\\?\\" + str(root / "project" / "src" / "icons")))
                # A file where a directory must be: no link below it, and no
                # exception from the check itself (VR02).
                (root / "project" / "blocked").write_text("x", encoding="utf-8")
                self.assertIsNone(build_module.output_link("blocked/icons/deeper"))

                # The 0.7 single-target writers check the same ancestry (IR03).
                class Cache:
                    def png(self, size):
                        return png(size)

                    def many(self, sizes):
                        return {size: self.png(size) for size in sizes}

                produced = []
                with self.assertRaisesRegex(ValueError, "link or junction"):
                    build_module.build_tauri(Cache(), Path("dist/icons"), produced)
                self.assertEqual(produced, [])
            finally:
                os.chdir(here)
            self.assertEqual(list((root / "outside").iterdir()), [])

    def test_VR05_the_output_check_is_linear_in_the_path_depth(self):
        import os

        calls = {"link": 0, "realpath": 0}
        real_link, real_realpath = build_module._is_link_or_reparse_point, os.path.realpath

        def counted_link(path):
            calls["link"] += 1
            return real_link(path)

        def counted_realpath(path, *args, **kwargs):
            calls["realpath"] += 1
            return real_realpath(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            measured = {}
            for depth in (20, 40):
                calls.update(link=0, realpath=0)
                deep = Path(tmp, f"tree{depth}", *[f"d{i}" for i in range(depth)])
                deep.mkdir(parents=True)  # every component exists
                with patch.object(build_module, "_is_link_or_reparse_point", counted_link), \
                        patch("os.path.realpath", counted_realpath):
                    self.assertIsNone(build_module.output_link(deep, base=tmp))
                measured[depth] = dict(calls)
        # One check per component below the base: twenty more, twenty more.
        self.assertEqual(measured[40]["link"] - measured[20]["link"], 20)
        # Nothing is re-resolved per component.
        self.assertEqual(measured[20]["realpath"], measured[40]["realpath"])

    def test_TV02_a_link_outside_that_leads_through_the_projects_own_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "real").mkdir(parents=True)
            (Path(tmp) / "outside").mkdir()
            self._link_dir(project / "dist", Path(tmp) / "outside")
            # Outside the project, the caller's own aliases: one into the
            # project's linked dist, one into an ordinary folder.
            self._link_dir(Path(tmp) / "to_dist", project / "dist")
            self._link_dir(Path(tmp) / "to_real", project / "real")
            self.assertIsNotNone(build_module.output_link(Path(tmp) / "to_dist" / "icons", base=project))
            self.assertIsNone(build_module.output_link(Path(tmp) / "to_real" / "icons", base=project))

    @unittest.skipIf(__import__("os").name == "nt", "POSIX resolves a link before the '..' after it")
    def test_FV04_a_build_writes_where_the_kernel_resolves_its_path(self):
        class Cache:
            def png(self, size):
                return png(size)

            def many(self, sizes):
                return {size: self.png(size) for size in sizes}

        class FakeRasterizer:
            def __init__(self, color_scheme="light"):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, svg, size, bg="transparent"):
                return png(size)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "safe" / "site" / "assets").mkdir(parents=True)
            (root / "jump").symlink_to(root / "safe" / "site" / "assets", target_is_directory=True)
            master = root / "master.svg"
            master.write_text('<svg viewBox="0 0 10 10"></svg>', encoding="utf-8")
            # A lexical collapse would write to root/icons; the kernel writes
            # to safe/site/icons, as 0.10.0 did (TV03).
            build_module.build_tauri(Cache(), root / "jump" / ".." / "legacy", [])
            with patch.object(build_module, "Rasterizer", FakeRasterizer):
                build_module.build(master, root / "jump" / ".." / "icons", ["tauri"])
            self.assertTrue((root / "safe" / "site" / "icons" / "icons" / "32x32.png").is_file())
            self.assertTrue((root / "safe" / "site" / "legacy" / "icons" / "32x32.png").is_file())
            # Nothing is written where a lexical collapse points (0.10.0 left
            # an empty folder there too; no file has ever landed in it).
            for collapsed in (root / "icons", root / "legacy"):
                self.assertEqual([p for p in collapsed.rglob("*") if p.is_file()], [])

    @unittest.skipIf(__import__("os").name == "nt", "POSIX resolves a link before the '..' after it")
    def test_TV03_a_trusted_alias_then_dotdot_resolves_as_the_kernel_does(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            (root / "safe" / "site" / "assets").mkdir(parents=True)
            (root / "jump").symlink_to(root / "safe" / "site" / "assets", target_is_directory=True)
            # /tmp/jump/../icons is /tmp/safe/site/icons to the kernel: no
            # project link on the way, accepted, and written where the kernel says.
            self.assertIsNone(build_module.output_link(root / "jump" / ".." / "icons",
                                                       base=root / "project"))
            # The same alias inside the project is the project's own link.
            (root / "project" / "jump").symlink_to(root / "safe" / "site" / "assets",
                                                   target_is_directory=True)
            here = os.getcwd()
            os.chdir(root / "project")
            try:
                self.assertIsNotNone(build_module.output_link("jump/../icons"))
            finally:
                os.chdir(here)

    @unittest.skipUnless(__import__("os").name == "nt", "a subst drive")
    def test_TV01_a_drive_whose_root_is_the_project_is_recognised(self):
        import os
        import string
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "real").mkdir(parents=True)
            (Path(tmp) / "outside").mkdir()
            self._link_dir(project / "dist", Path(tmp) / "outside")
            free = [c for c in reversed(string.ascii_uppercase) if not os.path.exists(f"{c}:\\")]
            if not free:
                self.skipTest("no free drive letter")
            letter = free[0]
            if subprocess.run(["subst", f"{letter}:", str(project)], capture_output=True).returncode:
                self.skipTest("subst is unavailable")
            try:
                self.assertIsNotNone(build_module.output_link(f"{letter}:\\dist\\icons", base=project))
                self.assertIsNone(build_module.output_link(f"{letter}:\\real\\icons", base=project))
            finally:
                subprocess.run(["subst", f"{letter}:", "/D"], capture_output=True)
            # A drive mapped to a folder *inside* the project (FV01).
            (project / "sub").mkdir()
            self._link_dir(project / "sub" / "dist", Path(tmp) / "outside")
            if subprocess.run(["subst", f"{letter}:", str(project / "sub")], capture_output=True).returncode:
                self.skipTest("subst is unavailable")
            try:
                self.assertIsNotNone(build_module.output_link(f"{letter}:\\dist\\icons", base=project))
                self.assertIsNone(build_module.output_link(f"{letter}:\\icons", base=project))
            finally:
                subprocess.run(["subst", f"{letter}:", "/D"], capture_output=True)

    @unittest.skipUnless(__import__("os").name == "nt", "Windows reparse-point limit")
    def test_FV03_a_long_chain_the_os_accepts_is_followed_and_a_loop_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            (root / "end").mkdir()
            previous = root / "end"
            for index in range(45):  # past Linux's 40, within Windows' 63
                link = root / f"hop{index}"
                self._link_dir(link, previous)
                previous = link
            self.assertIsNone(build_module.output_link(previous / "icons", base=root / "project"))
            # Two links that name each other: bounded, refused, never a hang.
            import _winapi

            (root / "loop_b").mkdir()  # a junction's target must exist when made
            _winapi.CreateJunction(str(root / "loop_b"), str(root / "loop_a"))
            (root / "loop_b").rmdir()
            _winapi.CreateJunction(str(root / "loop_a"), str(root / "loop_b"))
            with self.assertRaisesRegex(OSError, "too many links"):
                build_module.output_link(root / "loop_a" / "icons", base=root / "project")

    def test_SV03_a_base_reached_through_a_link_is_still_trusted(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "p"
            (project / "src").mkdir(parents=True)
            (Path(tmp) / "outside").mkdir()
            self._link_dir(project / "current", project)  # the base spelled through a link
            self._link_dir(project / "dist", Path(tmp) / "outside")
            base = project / "current"
            self.assertIsNone(build_module.output_link(base / "icons", base=base))
            self.assertIsNotNone(build_module.output_link(base / "dist" / "icons", base=base))
            if os.name != "nt":
                # FV02: the kernel follows "current" before the "..", so this
                # reaches p/../p/dist — the project's dist link.
                self.assertIsNotNone(build_module.output_link(
                    Path(str(base), "..", "p", "dist", "icons"), base=base))
                self.assertIsNone(build_module.output_link(
                    Path(str(base), "..", "p", "src", "icons"), base=base))

    @unittest.skipUnless(__import__("os").name == "nt", "Windows drive-relative paths")
    def test_SV04_a_drive_relative_output_without_links_is_accepted(self):
        import os

        here = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                drive = Path(tmp).drive
                self.assertIsNone(build_module.output_link(f"{drive}icons"))
                os.mkdir("project")
                self._link_dir(Path(tmp, "project", "dist"), Path(tmp))
                os.chdir("project")
                self.assertIsNotNone(build_module.output_link(f"{drive}dist\\icons"))
            finally:
                os.chdir(here)

    def test_single_target_writers_refuse_a_linked_tree(self):
        # build() validated its tree; the 0.7 writers (build_tauri and its
        # siblings) wrote through a link the project carried (PO01).
        class Cache:
            def png(self, size):
                return png(size)

            def many(self, sizes):
                return {size: self.png(size) for size in sizes}

        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside"
            outside.mkdir()
            output = Path(tmp) / "output"
            output.mkdir()
            try:
                (output / "icons").symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("symlink creation is unavailable on this platform")
            produced = []
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                build_module.build_tauri(Cache(), output, produced)
            self.assertEqual(produced, [])
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
