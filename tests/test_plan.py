# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The render plan (R16): one immutable set of bytes from review to ship."""
import importlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from iconflow import plan as plan_module
from iconflow.plan import PlanError, compare, compute_plan, export_plan, load_plan, write_plan

build_module = importlib.import_module("iconflow.build")


def _png(size, color=(20, 120, 240, 255), *, sparse=False, optimize=False):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0) if sparse else color)
    if sparse:
        margin = max(1, size // 4)
        ImageDraw.Draw(image).ellipse([margin, margin, size - margin - 1, size - margin - 1], fill=color)
    out = io.BytesIO()
    image.save(out, "PNG", optimize=optimize)
    return out.getvalue()


class FakeRasterizer:
    """Deterministic stand-in for Chromium: colour follows a marker in the SVG."""

    renders = 0

    def __init__(self, color_scheme="light"):
        self.color_scheme = color_scheme

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, svg, size, bg="transparent"):
        FakeRasterizer.renders += 1
        color = (200, 30, 30, 255) if "red" in svg else (20, 120, 240, 255)
        return _png(size, color, sparse="tray-mark" in svg)


class PlanTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.master = self.root / "master.svg"
        self.master.write_text('<svg viewBox="0 0 10 10"></svg>', encoding="utf-8")
        self.tray = self.root / "tray.svg"
        self.tray.write_text('<svg id="tray-mark" viewBox="0 0 10 10"></svg>', encoding="utf-8")
        patcher = patch.object(build_module, "Rasterizer", FakeRasterizer)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def plan(self, **kw):
        kw.setdefault("targets", ["web", "tauri", "electron", "tray", "android"])
        kw.setdefault("tray_svg", self.tray)
        return compute_plan(self.master, **kw)


class ComputeTests(PlanTestCase):
    def test_build_writes_exactly_the_plan(self):
        plan = self.plan()
        out = self.root / "out"
        produced = build_module.build(self.master, out, targets=["web", "tauri", "electron", "tray", "android"],
                                      tray_svg=self.tray)
        self.assertEqual(produced, plan.produced)
        for record in plan.files:
            self.assertEqual((out / record.path).read_bytes(), record.data, record.path)

    def test_plan_is_immutable(self):
        plan = self.plan()
        with self.assertRaises(Exception):
            plan.files[0].data = b""  # frozen record
        with self.assertRaises(TypeError):
            plan.parameters["targets"] = ["web"]  # read-only mapping
        self.assertIsInstance(plan.files, tuple)

    def test_sources_are_snapshotted_once(self):
        plan = self.plan(targets=["web"])
        favicon = plan.file("favicon.svg")
        self.master.write_text('<svg viewBox="0 0 10 10" class="red"></svg>', encoding="utf-8")
        self.assertEqual(plan.file("favicon.svg"), favicon)
        self.assertEqual(plan.inputs["master"]["sha256"],
                         plan_module._sha256(b'<svg viewBox="0 0 10 10"></svg>'))

    def test_unused_optional_sources_are_not_read(self):
        plan = self.plan(targets=["web"], tray_svg=self.root / "missing.svg")
        self.assertNotIn("tray", plan.inputs)

    def test_failed_target_leaves_existing_output_untouched(self):
        out = self.root / "out"
        out.mkdir()
        (out / "favicon.ico").write_bytes(b"previous")
        (out / "keep.txt").write_text("mine", encoding="utf-8")
        # A full card with no tray source: the template cannot be derived, late.
        with self.assertRaises(ValueError):
            build_module.build(self.master, out, targets=["web", "tray"])
        self.assertEqual((out / "favicon.ico").read_bytes(), b"previous")
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["favicon.ico", "keep.txt"])

    def test_failed_build_does_not_create_the_output_directory(self):
        out = self.root / "absent"
        with self.assertRaises(ValueError):
            build_module.build(self.master, out, targets=["tray"])
        self.assertFalse(out.exists())

    def test_windows_tile_preview_matches_build_default_colour(self):
        from iconflow import htmlhead

        plan = self.plan(targets=["web"], theme_color="#112233", bg_color="#ffffff",
                         web_options=htmlhead.WebMetaOptions(windows_tiles=True))

        class Cache:
            svg = '<svg viewBox="0 0 10 10"></svg>'

            def png(self, size):
                return FakeRasterizer().render(self.svg, size)

        preview = build_module.preview_assets(Cache(), "web", windows_tiles=True,
                                              theme_color="#112233", bg_color="#ffffff")
        self.assertEqual(preview["mstile-150x150.png"], plan.file("mstile-150x150.png"))


class IdentityTests(PlanTestCase):
    def test_lossless_reencode_keeps_content_but_not_bytes(self):
        a, b = _png(32), _png(32, optimize=True)
        self.assertNotEqual(a, b)
        self.assertEqual(plan_module.content_sha256("x.png", a), plan_module.content_sha256("x.png", b))

    def test_one_pixel_changes_content(self):
        a = _png(32)
        image = Image.open(io.BytesIO(a)).convert("RGBA")
        image.putpixel((3, 3), (0, 0, 0, 255))
        out = io.BytesIO()
        image.save(out, "PNG")
        self.assertNotEqual(plan_module.content_sha256("x.png", a),
                            plan_module.content_sha256("x.png", out.getvalue()))

    def test_container_frames_are_each_identified(self):
        from iconflow import assemble

        frames = {16: _png(16), 32: _png(32)}
        base = plan_module.content_sha256("a.ico", assemble.ico_bytes(frames))
        changed = plan_module.content_sha256("a.ico", assemble.ico_bytes({**frames, 16: _png(16, (1, 2, 3, 255))}))
        reordered = plan_module.content_sha256("a.ico", assemble.ico_bytes(frames, order=[32, 16]))
        self.assertNotEqual(base, changed)
        self.assertNotEqual(base, reordered)
        icns = assemble.icns_bytes({16: _png(16), 32: _png(32)})
        self.assertEqual(sorted(assemble.icns_frames(icns)), [16, 32])

    def test_text_newlines_are_not_content(self):
        self.assertEqual(plan_module.content_sha256("site.webmanifest", b"{\r\n}"),
                         plan_module.content_sha256("site.webmanifest", b"{\n}"))

    def test_digest_is_independent_of_produced_order(self):
        plan = self.plan(targets=["web"])
        files = {r.path: r.data for r in plan.files}
        reversed_plan = plan_module.RenderPlan.create(
            dict(reversed(list(files.items()))), inputs={}, parameters={}, toolchain={},
        )
        self.assertEqual(plan.digest, reversed_plan.digest)
        self.assertNotEqual(plan.produced, reversed_plan.produced)


class CompareTests(PlanTestCase):
    def test_matrix(self):
        plan = self.plan(targets=["web"])
        self.assertIsNone(compare(None, plan).verified)
        same = compare(plan.binding(), plan)
        self.assertTrue(same.verified)
        self.assertTrue(same.bytes_verified)
        self.master.write_text('<svg viewBox="0 0 10 10" class="red"></svg>', encoding="utf-8")
        drift = compare(plan.binding(), self.plan(targets=["web"]))
        self.assertFalse(drift.verified)
        self.assertIn("icon-512.png", drift.changed)
        more = compare(plan.binding(), self.plan(targets=["web", "tauri"]))
        self.assertIn("icons/icon.icns", more.added)
        fewer = compare(self.plan(targets=["web", "tauri"]).binding(), self.plan(targets=["web"]))
        self.assertIn("icons/icon.icns", fewer.removed)

    def test_reencoded_bytes_verify_content_but_not_bytes(self):
        plan = self.plan(targets=["web"])
        files = {r.path: r.data for r in plan.files}
        files["icon-512.png"] = _png(512)  # the plan's is optimised: same pixels, other bytes
        reencoded = plan_module.RenderPlan.create(files, inputs={}, parameters={}, toolchain={})
        check = compare(plan.binding(), reencoded)
        self.assertTrue(check.verified)
        self.assertFalse(check.bytes_verified)

    def test_binding_shape_is_validated(self):
        binding = self.plan(targets=["web"]).binding()
        plan_module.validate_binding(json.loads(json.dumps(binding)))
        forged = json.loads(json.dumps(binding))
        forged["files"]["icon-512.png"]["content"] = "0" * 64
        with self.assertRaisesRegex(PlanError, "does not match"):
            plan_module.validate_binding(forged)
        for broken in ({}, {**binding, "schema": 2}, {**binding, "files": {}},
                       {**binding, "files": {"../x.png": {"content": "0" * 64, "sha256": "0" * 64}}}):
            with self.assertRaises(PlanError):
                plan_module.validate_binding(broken)


class ImportTests(PlanTestCase):
    def saved(self):
        plan = self.plan(targets=["web", "tauri"])
        directory = self.root / "plan"
        export_plan(plan, directory)
        return plan, directory

    def test_round_trip(self):
        plan, directory = self.saved()
        loaded = load_plan(directory)
        self.assertEqual(loaded.artifact_digest, plan.artifact_digest)
        self.assertEqual(loaded.produced, plan.produced)

    def test_changed_payload_is_refused_even_with_its_hash_updated(self):
        plan, directory = self.saved()
        target = directory / "files" / "icon-512.png"
        forged = _png(512, (1, 2, 3, 255))
        target.write_bytes(forged)
        with self.assertRaisesRegex(PlanError, "changed after"):
            load_plan(directory)
        manifest = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            if entry["path"] == "icon-512.png":
                entry["sha256"] = plan_module._sha256(forged)
                entry["bytes"] = len(forged)
        (directory / "plan.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "content identity"):
            load_plan(directory)

    def test_extra_missing_duplicate_and_hostile_entries(self):
        plan, directory = self.saved()
        (directory / "files" / "extra.png").write_bytes(_png(8))
        with self.assertRaisesRegex(PlanError, "does not name"):
            load_plan(directory)
        (directory / "files" / "extra.png").unlink()
        (directory / "files" / "favicon.ico").unlink()
        with self.assertRaisesRegex(PlanError, "missing"):
            load_plan(directory)
        _plan, directory = self.saved()
        text = (directory / "plan.json").read_text(encoding="utf-8")
        (directory / "plan.json").write_text(text.replace('"schema": 1', '"schema": 1, "schema": 1', 1),
                                             encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "repeats a key"):
            load_plan(directory)
        for hostile in ("../evil.png", "/abs.png", "C:/x.png", "a\\b.png", "con.png", "a:b.png", "./x.png"):
            with self.assertRaises(PlanError, msg=hostile):
                plan_module._relative(hostile)

    def test_link_inside_the_plan_is_refused(self):
        _plan, directory = self.saved()
        outside = self.root / "outside.png"
        outside.write_bytes(_png(8))
        try:
            os.symlink(outside, directory / "files" / "link.png")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(PlanError, "link"):
            load_plan(directory)


class WriteTests(PlanTestCase):
    def test_commit_failure_restores_replaced_files(self):
        plan = self.plan(targets=["web"])
        out = self.root / "out"
        out.mkdir()
        (out / "favicon.ico").write_bytes(b"previous-ico")
        (out / "favicon.svg").write_bytes(b"previous-svg")
        real = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 6:
                raise OSError("disk full")
            return real(src, dst)

        with patch.object(plan_module.os, "replace", flaky), self.assertRaises(OSError):
            write_plan(plan, out)
        self.assertEqual((out / "favicon.ico").read_bytes(), b"previous-ico")
        self.assertEqual((out / "favicon.svg").read_bytes(), b"previous-svg")
        self.assertFalse((out / "apple-touch-icon.png").exists())
        self.assertEqual([p.name for p in out.iterdir() if p.name.startswith(".iconflow-staging")], [])


if __name__ == "__main__":
    unittest.main()
