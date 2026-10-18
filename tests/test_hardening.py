# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Regressions for the independent review of the 0.7 branch (2026-10-19).

A sealed review by a different product (Codex, via Agent Task Delegation)
returned REQUEST_CHANGES with fourteen defects. Each test names the finding it
guards (R01-R14) so the next reader can trace why the behaviour exists.
"""
import contextlib
import importlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from iconflow import brand, qa
from iconflow.cli import DEMO_FILES, _resource, main
from iconflow.config import ConfigError, load_config, load_review_receipt
from iconflow.findings import Finding

build = importlib.import_module("iconflow.build")


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue()


def png(size, shape="square"):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    box = [size // 5, size // 5, size - size // 5, size - size // 5]
    if shape == "square":
        draw.rectangle(box, fill=(20, 30, 60, 255))
    else:
        draw.ellipse([size // 3, size // 8, size - size // 3, size - size // 8], fill=(20, 30, 60, 255))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class DemoProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        for name in DEMO_FILES:
            (self.dir / name).write_bytes(_resource("demo", name).read_bytes())
        (self.dir / "wordmark.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">'
            '<rect width="400" height="100" fill="currentColor"/></svg>', encoding="utf-8")
        self.config = self.dir / "iconflow.toml"
        text = self.config.read_text(encoding="utf-8")
        self.config.write_text(text.replace("[review]", '[brand]\nwordmark = "wordmark.svg"\n\n[review]'),
                               encoding="utf-8")
        tray = mock.patch("iconflow.qa.tray_template_warnings", return_value=[])
        tray.start()
        self.addCleanup(tray.stop)


class GateTests(DemoProject):
    def test_R01_brand_build_runs_the_same_automated_gate_as_ship(self):
        warned = [Finding("stroke-floor", "stroke-width=1 is very thin")]
        with mock.patch("iconflow.qa.check", return_value=warned):
            code, envelope, _ = run(["brand", "build", "--config", str(self.config),
                                     "--review", str(self.dir / "master-review.json")])
        self.assertEqual(code, 1)
        self.assertIn("qa-warnings", {w["code"] for w in envelope["warnings"]})
        self.assertFalse((self.dir / "brand-kit").exists())

    def test_R13_malformed_second_opinions_are_refused_before_any_build(self):
        receipt = json.loads((self.dir / "master-review.json").read_text(encoding="utf-8"))
        receipt["second_opinions"] = [{"reviewer": {"name": "x"}, "scores": {"legibility": "3"}}]
        path = self.dir / "bad.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "second_opinions"):
            load_review_receipt(path, load_config(self.config))


class CompositionContractTests(unittest.TestCase):
    def test_R02_the_bound_scale_is_the_rendered_scale(self):
        self.assertEqual(build.validate_maskable_scale(0.80151), 0.8015)
        self.assertEqual(build.validate_maskable_scale(0.80152), 0.8015)

    def test_R03_a_maskable_link_to_the_master_is_still_a_link(self):
        class Rasterizer:
            def __init__(self, **_):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, _svg, size, bg="transparent"):
                return png(size)

        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            master.write_text('<svg viewBox="0 0 10 10"></svg>', encoding="utf-8")
            with mock.patch.object(build, "Rasterizer", Rasterizer), \
                 mock.patch.object(build, "maskable_png", wraps=build.maskable_png) as spy:
                build.build(master, Path(tmp) / "out", ["web"], maskable_svg=master)
        kwargs = spy.call_args.kwargs
        self.assertIsNotNone(kwargs["maskable_cache"])  # linked: scale 1.0, as QA assumed

    def test_R04_a_linked_source_must_be_the_mark_at_androids_sizes_too(self):
        class Rasterizer:
            def __init__(self, **_):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, svg, size, bg="transparent"):
                # The linked source shows the mark at 512 and another shape small.
                return png(size, "circle" if "linked" in svg and size < 400 else "square")

        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            linked = Path(tmp) / "maskable.svg"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            linked.write_text('<svg id="linked" viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with mock.patch("iconflow.qa.Rasterizer", Rasterizer):
                codes = [w.code for w in qa.check(master, maskable_svg=linked, android=True)]
        self.assertIn("maskable-drift", codes)


class SvgSafetyTests(unittest.TestCase):
    PREFIXED = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                '<s:script xmlns:s="http://www.w3.org/2000/svg">alert(1)</s:script></svg>')

    def test_R05_a_namespace_prefix_does_not_hide_a_script(self):
        self.assertEqual([w.code for w in qa._renderer_safety_warnings(self.PREFIXED)], ["svg-safety"])
        with self.assertRaises(brand.BrandError):
            brand.validate_wordmark(self.PREFIXED, "wordmark")
        handler = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:e="x" viewBox="0 0 1 1"><rect e:onload="x()"/></svg>'
        with self.assertRaises(brand.BrandError):
            brand.validate_wordmark(handler, "wordmark")

    def test_R10_a_wordmark_stylesheet_is_refused_and_a_master_stylesheet_is_isolated(self):
        styled = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                  '<style>path{fill:red!important}</style><path d="M0 0h10v10z"/></svg>')
        with self.assertRaisesRegex(brand.BrandError, "style"):
            brand.validate_wordmark(styled, "wordmark")
        nested = brand._nest(styled, x=0, y=0, width=10, height=10, prefix="mark-")
        self.assertEqual(brand._local(nested.tag), "image")
        self.assertTrue(nested.get("href").startswith("data:image/svg+xml;base64,"))

    def test_R11_root_rendering_attributes_survive_nesting(self):
        master = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" stroke-width="48" '
                  'stroke-linecap="round" opacity="0.8" width="10" height="10"><path d="M0 0L10 10"/></svg>')
        nested = brand._nest(master, x=5, y=5, width=20, height=20, prefix="mark-")
        self.assertEqual(nested.get("stroke-width"), "48")
        self.assertEqual(nested.get("stroke-linecap"), "round")
        self.assertEqual(nested.get("opacity"), "0.8")
        self.assertEqual(nested.get("width"), "20")

    def test_R12_an_id_that_looks_like_a_colour_does_not_corrupt_colours(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
               '<linearGradient id="fff"/><rect fill="#fff"/><rect fill="url(#fff)"/></svg>')
        nested = brand._nest(svg, x=0, y=0, width=10, height=10, prefix="mark-")
        fills = [el.get("fill") for el in nested.iter() if el.get("fill")]
        self.assertEqual(fills, ["#fff", "url(#mark-fff)"])


class FilesystemTests(DemoProject):
    def _link(self, target: Path, link: Path):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable here")

    def test_R06_the_brand_kit_never_writes_through_a_link(self):
        outside = self.dir / "outside"
        outside.mkdir()
        kit = self.dir / "brand-kit"
        kit.mkdir()
        self._link(outside, kit / "lockups")
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch("iconflow.rasterize.Rasterizer"):
            code, envelope, _ = run(["brand", "build", "--config", str(self.config),
                                     "--review", str(self.dir / "master-review.json")])
        self.assertEqual(code, 2)
        self.assertEqual(list(outside.iterdir()), [])

    def test_R09_sync_does_not_read_through_links(self):
        secret = self.dir / "elsewhere.png"
        secret.write_bytes(png(8))
        project = self.dir / "site"
        project.mkdir()
        self._link(secret, project / "icon.png")
        manifest = {"schema": 1, "mark_sha256": "1" * 64, "files": [], "ship_outputs": [],
                    "retired": [{"mark_sha256": "0" * 64, "files": [
                        {"path": "x.png", "sha256": brand._sha256_bytes(secret.read_bytes())}]}]}
        hits, _current, scanned = brand.sync_report(project, [manifest])
        self.assertEqual((hits, scanned), ([], 0))


class PropagationTests(unittest.TestCase):
    def test_R14_a_restored_mark_is_current_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect/></svg>'
            (project / "logo.svg").write_text(svg, encoding="utf-8")
            from iconflow.config import svg_sha256

            digest = svg_sha256(project / "logo.svg")
            manifest = {"schema": 1, "mark_sha256": digest, "files": [], "ship_outputs": [],
                        "retired": [{"mark_sha256": "2" * 64, "files": []},
                                    {"mark_sha256": digest, "files": []}]}
            hits, _current, _scanned = brand.sync_report(project, [manifest])
        self.assertEqual(hits, [])


class EvidenceTests(unittest.TestCase):
    def test_R08_an_empty_evidence_bundle_cannot_be_scored(self):
        from iconflow import headless

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / headless.FINDINGS_FILE).write_text(json.dumps({
                "schema": 1, "source_sha256": "a" * 64, "contract_sha256": "b" * 64,
                "evidence": {}, "warnings": [], "advisories": [],
            }), encoding="utf-8")
            with self.assertRaisesRegex(headless.HeadlessError, "required evidence"):
                headless.load_evidence(directory, source_sha256="a" * 64, contract_sha256="b" * 64)


class SecondPassTests(DemoProject):
    """Regressions for the verification review of the fixes (R04-R09, N01-N04)."""

    def _link(self, target: Path, link: Path):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable here")

    def test_R04_every_android_native_size_is_audited(self):
        self.assertIn(165, build.android_native_sizes(None, linked=True))
        self.assertEqual(build.android_native_sizes(None, linked=True), (330, 248, 165, 124, 82))
        seen = []

        class Rasterizer:
            def __init__(self, **_):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, svg, size, bg="transparent"):
                seen.append(size)
                return png(size, "circle" if "linked" in svg and size == 165 else "square")

        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp) / "master.svg"
            linked = Path(tmp) / "maskable.svg"
            master.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            linked.write_text('<svg id="linked" viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            with mock.patch("iconflow.qa.Rasterizer", Rasterizer):
                android = [w.code for w in qa.check(master, maskable_svg=linked, android=True)]
                web_only = [w.code for w in qa.check(master, maskable_svg=linked)]
        self.assertIn("maskable-drift", android)
        self.assertNotIn("maskable-drift", web_only)      # N01: web never renders 165px

    def test_R05_any_xml_prefix_is_seen_through(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
               '<s\u00b7:script xmlns:s\u00b7="http://www.w3.org/2000/svg">x</s\u00b7:script></svg>')
        self.assertEqual([w.code for w in qa._renderer_safety_warnings(svg)], ["svg-safety"])

    def test_R06_outline_refuses_a_junction_higher_up(self):
        outside = self.dir / "outside"
        outside.mkdir()
        self._link(outside, self.dir / "jump")
        code, envelope, _ = run(["brand", "outline", "--text", "A", "--font", "missing.ttf",
                                 "--out", str(self.dir / "jump" / "sub" / "w.svg")])
        # Refused for the link before the font is even opened.
        self.assertEqual(code, 2)
        self.assertEqual(list(outside.iterdir()), [])

    def test_R07_N02_only_this_runs_ship_files_are_current_and_history_is_kept(self):
        out = self.dir / "icons"
        (out / "icons").mkdir(parents=True)
        (out / "icons" / "32x32.png").write_bytes(png(32))          # an earlier target's residue
        (out / "favicon.ico").write_bytes(b"ico-of-this-mark")
        spec = brand.spec_from_config(load_config(self.config))
        with mock.patch("iconflow.rasterize.Rasterizer") as fake:
            fake.return_value.__enter__.return_value.render.side_effect = lambda s, n, bg="transparent": png(n)
            fake.return_value.__enter__.return_value.render_rect.side_effect = (
                lambda s, w, h, bg="transparent": png(max(w, h)))
            first = brand.build_kit(spec, approval={}, ship_output=out, shipped=["favicon.ico"])
            manifest = json.loads(first.manifest.read_text(encoding="utf-8"))
            self.assertEqual([e["path"] for e in manifest["ship_outputs"]], ["favicon.ico"])
            brand.build_kit(spec, approval={})                       # same mark, no ship
            again = json.loads(first.manifest.read_text(encoding="utf-8"))
        self.assertEqual([e["path"] for e in again["ship_outputs"]], ["favicon.ico"])

    def test_R09_an_evidence_sheet_that_is_a_link_is_refused(self):
        from iconflow import headless

        evidence = self.dir / "evidence"
        evidence.mkdir()
        outside = self.dir / "outside.png"
        outside.write_bytes(png(8))
        (evidence / "contact-sheet.png").write_bytes(png(8))
        self._link(outside, evidence / "targets.png")
        (evidence / headless.FINDINGS_FILE).write_text(json.dumps({
            "schema": 1, "source_sha256": "a" * 64, "contract_sha256": "b" * 64,
            "warnings": [], "advisories": [],
            "evidence": {
                "contact_sheet": {"path": "contact-sheet.png",
                                  "sha256": brand._sha256_bytes(png(8))},
                "targets": {"path": "targets.png", "sha256": brand._sha256_bytes(png(8))},
            },
        }), encoding="utf-8")
        with self.assertRaisesRegex(headless.HeadlessError, "link"):
            headless.load_evidence(evidence, source_sha256="a" * 64, contract_sha256="b" * 64)

    def test_N03_an_uppercase_url_reference_follows_its_renamed_id(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
               '<linearGradient id="g"/><rect fill="URL(#g)"/></svg>')
        nested = brand._nest(svg, x=0, y=0, width=10, height=10, prefix="mark-")
        self.assertIn("#mark-g", [el.get("fill") for el in nested.iter() if el.get("fill")][0])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFOs only")
    def test_N04_the_scanner_never_opens_a_fifo(self):
        project = self.dir / "fifo-site"
        project.mkdir()
        os.mkfifo(project / "logo.png")
        hits, _current, scanned = brand.sync_report(project, [{"files": [], "retired": []}])
        self.assertEqual((hits, scanned), ([], 0))


if __name__ == "__main__":
    unittest.main()
