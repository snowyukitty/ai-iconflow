# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Regressions for the independent review of the render plan (P01-P13).

Each test names the finding it closes; docs/MILESTONE_v0.8.md lists them.
"""
import importlib
import io
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from iconflow import assemble, review
from iconflow import plan as plan_module
from iconflow.plan import PlanError, compute_plan, export_plan, load_plan, write_plan

build_module = importlib.import_module("iconflow.build")


def _png(size, color=(20, 120, 240, 255)):
    out = io.BytesIO()
    Image.new("RGBA", (size, size), color).save(out, "PNG")
    return out.getvalue()


class Counting:
    """A renderer that counts its renders and can change colour between sessions."""

    renders = 0
    color = (20, 120, 240, 255)

    def __init__(self, color_scheme="light"):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, svg, size, bg="transparent"):
        Counting.renders += 1
        return _png(size, Counting.color)


class Fixture(unittest.TestCase):
    def setUp(self):
        Counting.renders = 0
        Counting.color = (20, 120, 240, 255)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.master = self.root / "master.svg"
        self.master.write_text('<svg viewBox="0 0 10 10"></svg>', encoding="utf-8")
        for module in (build_module, review):
            patcher = mock.patch.object(module, "Rasterizer", Counting)
            patcher.start()
            self.addCleanup(patcher.stop)

    def plan(self, targets=("web", "tauri"), **kw):
        return compute_plan(self.master, targets, **kw)


class SurfaceTests(Fixture):
    def test_P01_the_review_sheet_shows_the_plans_frames_not_new_renders(self):
        plan = self.plan()
        Counting.color = (200, 30, 30, 255)  # a second session would draw red
        before = Counting.renders
        review.contact_sheet(self.master, self.root / "sheet.png", plan=plan)
        self.assertEqual(Counting.renders, before)  # every size it shows ships
        self.assertEqual(sorted(plan.master_frames())[:3], [16, 24, 32])


class WriteTests(Fixture):
    def test_P02_a_planned_file_never_replaces_a_directory(self):
        out = self.root / "out"
        (out / "favicon.svg").mkdir(parents=True)
        (out / "favicon.svg" / "notes.txt").write_text("mine", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not a file"):
            write_plan(self.plan(), out)
        self.assertEqual((out / "favicon.svg" / "notes.txt").read_text(encoding="utf-8"), "mine")
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["favicon.svg"])

    def test_P03_a_failed_restore_keeps_the_original(self):
        plan = self.plan()
        out = self.root / "out"
        out.mkdir()
        (out / "favicon.svg").write_bytes(b"precious")
        real = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] >= 4:  # backup + install favicon.svg, back up favicon.ico, then all fail
                raise OSError("disk gone")
            return real(src, dst)

        with mock.patch.object(plan_module.os, "replace", flaky), \
                self.assertRaisesRegex(OSError, "originals are kept in"):
            write_plan(plan, out)
        kept = list(out.glob(".iconflow-staging-*/backup/favicon.svg"))
        self.assertEqual([p.read_bytes() for p in kept], [b"precious"])

    def test_P12_a_staging_failure_does_not_leave_a_new_output_directory(self):
        out = self.root / "new" / "nested" / "out"
        with mock.patch.object(plan_module.tempfile, "mkdtemp", side_effect=OSError("no space")), \
                self.assertRaises(OSError):
            write_plan(self.plan(), out)
        self.assertFalse((self.root / "new").exists())


class ExportTests(Fixture):
    def test_P04_export_refuses_a_directory_that_is_not_a_saved_plan(self):
        target = self.root / "evidence" / "plan"
        target.mkdir(parents=True)
        (target / "notes.md").write_text("mine", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "not a saved plan"):
            export_plan(self.plan(), target)
        self.assertTrue((target / "notes.md").is_file())

    def test_P04_a_previous_export_is_replaced_whole(self):
        target = self.root / "plan"
        export_plan(self.plan(), target)
        Counting.color = (200, 30, 30, 255)
        second = self.plan()
        export_plan(second, target)
        self.assertEqual(load_plan(target).artifact_digest, second.artifact_digest)
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith(".")], [])


class SecondPassTests(Fixture):
    """The verification pass: P04, P07, P09 and P12 completed; N01-N03."""

    def test_P04_a_stray_file_inside_a_previous_export_is_never_deleted(self):
        target = self.root / "plan"
        export_plan(self.plan(), target)
        (target / "files" / "private-notes.txt").write_text("mine", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "not a saved plan"):
            export_plan(self.plan(), target)
        self.assertEqual((target / "files" / "private-notes.txt").read_text(encoding="utf-8"), "mine")

    def test_P07_a_hard_link_is_the_same_snapshot(self):
        linked = self.root / "tray.svg"
        linked.write_text('<svg viewBox="0 0 10 10" id="tray-mark"></svg>', encoding="utf-8")
        alias = self.root / "maskable.svg"
        try:
            os.link(linked, alias)
        except (OSError, NotImplementedError):
            self.skipTest("hard links unavailable")
        with mock.patch.object(plan_module, "snapshot", wraps=plan_module.snapshot) as spy:
            compute_plan(self.master, ["web", "tray"], tray_svg=linked, maskable_svg=alias,
                         tray_template_mode="alpha")
        self.assertEqual(spy.call_count, 2)

    def test_P09_nesting_is_bounded(self):
        target = self.root / "plan"
        export_plan(self.plan(), target)
        deep = target / "files"
        for index in range(plan_module.MAX_PLAN_DEPTH + 2):
            deep = deep / f"d{index}"
        deep.mkdir(parents=True)
        with self.assertRaisesRegex(PlanError, "deeper"):
            load_plan(target)

    def test_P12_a_failed_mkdir_leaves_no_ancestor_behind(self):
        out = self.root / "a" / "b" / "c"
        real = Path.mkdir

        def half(path, *args, **kwargs):
            if path == out:
                real(self.root / "a", exist_ok=True)
                raise OSError("disk full")
            return real(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", half), self.assertRaises(OSError):
            write_plan(self.plan(), out)
        self.assertFalse((self.root / "a").exists())


class PlateEdgeTests(unittest.TestCase):
    def _png(self, draw_fn, ground=(25, 26, 32, 255)):
        from PIL import ImageDraw

        size = 256
        image = Image.new("RGBA", (size, size), ground)
        draw_fn(ImageDraw.Draw(image))
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()

    def test_N01_two_capsules_with_the_same_counter_are_different_marks(self):
        from iconflow import qa

        def capsule(horizontal):
            def draw(d):
                box = [38, 98, 218, 158] if horizontal else [98, 38, 158, 218]
                d.rounded_rectangle(box, radius=26, fill=(255, 244, 232, 255))
                d.ellipse([113, 113, 143, 143], fill=(25, 26, 32, 255))
            return draw

        found = qa.maskable_identity_findings(self._png(capsule(True)), self._png(capsule(False)),
                                              source_label="maskable.svg")
        self.assertEqual([f.code for f in found], ["maskable-drift"])

    def test_N02_tiny_and_narrow_shapes_do_not_crash(self):
        from iconflow import qa

        tiny = self._png(lambda d: d.rectangle([127, 127, 128, 128], fill=(255, 255, 255, 255)))
        narrow = self._png(lambda d: d.rectangle([120, 10, 120, 240], fill=(255, 255, 255, 255)))
        for png in (tiny, narrow):
            qa._figure_candidates(png)  # must not raise
            qa.maskable_identity_findings(png, png, source_label="x")


class ImportTests(Fixture):
    def saved(self):
        target = self.root / "plan"
        export_plan(self.plan(), target)
        return target

    def edit_manifest(self, target, change):
        path = target / "plan.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        change(manifest)
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_P05_edited_settings_change_the_provenance(self):
        target = self.saved()
        self.edit_manifest(target, lambda m: m["parameters"].update(optimize_png=False))
        with self.assertRaisesRegex(PlanError, "settings"):
            load_plan(target)

    def test_P08_malformed_nested_records_and_containers_are_plan_errors(self):
        target = self.saved()
        self.edit_manifest(target, lambda m: m["inputs"].update(master=None))
        with self.assertRaisesRegex(PlanError, "master"):
            load_plan(target)
        with self.assertRaises(PlanError):
            plan_module.content_sha256("favicon.ico", b"\0\0\1\0\5\0")  # 5 entries, none present

    def test_P09_nothing_but_the_manifest_and_files_at_the_root(self):
        target = self.saved()
        (target / "extra.txt").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "exactly"):
            load_plan(target)

    def test_P13_newline_and_control_characters_are_not_paths(self):
        for hostile in ("icon.png\n", "icon\t.png", "a/\nb.png"):
            with self.assertRaises(PlanError, msg=repr(hostile)):
                plan_module._relative(hostile)


class ContainerTests(unittest.TestCase):
    def test_P06_every_ico_slot_counts(self):
        blue16, red16, blue32 = _png(16), _png(16, (255, 0, 0, 255)), _png(32)
        two = assemble.ico_bytes({16: blue16, 32: blue32})
        # Hand-pack three slots, two of them 16px: a dictionary would lose one.
        payloads = [red16, blue16, blue32]
        header = bytearray(struct.pack("<HHH", 0, 1, 3))
        offset = 6 + 16 * 3
        for size, payload in zip((16, 16, 32), payloads):
            header += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(payload), offset)
            offset += len(payload)
        three = bytes(header) + b"".join(payloads)
        self.assertNotEqual(plan_module.content_sha256("a.ico", two),
                            plan_module.content_sha256("a.ico", three))
        with self.assertRaisesRegex(ValueError, "repeated"):
            assemble.ico_frames(three)

    def test_P06_icns_length_and_unknown_chunks(self):
        icns = assemble.icns_bytes({16: _png(16)})
        with self.assertRaises(ValueError):
            assemble.icns_entries(icns + b"junk")  # declared length no longer matches
        extra = icns[:4] + struct.pack(">I", len(icns) + 12) + icns[8:] + b"zzzz" + struct.pack(">I", 12) + b"abcd"
        self.assertEqual([t for t, _ in assemble.icns_entries(extra)], [b"icp4", b"zzzz"])
        with self.assertRaises(ValueError):
            assemble.icns_frames(extra)
        self.assertNotEqual(plan_module.content_sha256("a.icns", icns),
                            plan_module.content_sha256("a.icns", extra))


class SnapshotTests(Fixture):
    def test_P07_one_file_in_two_roles_is_read_once(self):
        linked = self.root / "linked.svg"
        linked.write_text('<svg viewBox="0 0 10 10" id="tray-mark"></svg>', encoding="utf-8")
        with mock.patch.object(plan_module, "snapshot", wraps=plan_module.snapshot) as spy:
            plan = compute_plan(self.master, ["web", "tray"], tray_svg=linked, maskable_svg=linked,
                                tray_template_mode="alpha")
        self.assertEqual(spy.call_count, 2)  # master + linked, not master + linked twice
        self.assertEqual(plan.inputs["tray"]["sha256"], plan.inputs["maskable"]["sha256"])


if __name__ == "__main__":
    unittest.main()
