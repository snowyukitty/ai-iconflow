import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import xml.etree.ElementTree as ET

from iconflow.cli import _version_at_least, main
from iconflow.config import IconFlowConfig, write_config
from iconflow.styles import STYLE_CATALOG


class CliTests(unittest.TestCase):
    def test_version_floor_comparison_handles_short_and_qualified_versions(self):
        self.assertTrue(_version_at_least("10", (10, 0)))
        self.assertTrue(_version_at_least("12.2.0.post1", (10, 0)))
        self.assertTrue(_version_at_least("1.40.0", (1, 40)))
        self.assertFalse(_version_at_least("9.5.0", (10, 0)))
        self.assertFalse(_version_at_least("unknown", (1, 40)))

    def test_version_matches_release(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), "IconFlow 0.4.0")

    def test_build_rejects_unknown_target_before_rendering(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["build", "missing.svg", "--targets", "typo"])
        self.assertEqual(code, 2)
        self.assertIn("unknown target", err.getvalue())

    def test_compare_requires_at_least_two_candidates(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["compare", "one.svg"])
        self.assertEqual(code, 2)
        self.assertIn("at least two", err.getvalue())

    def test_manifest_extra_requires_key_value(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["build", "missing.svg", "--manifest-extra", "bad"])
        self.assertEqual(code, 2)
        self.assertIn("KEY=VALUE", err.getvalue())

    def test_new_reads_packaged_preset_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "nested" / "master.svg"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["new", "flat-geometric", "--out", str(destination)])
            self.assertEqual(code, 0)
            self.assertIn("<svg", destination.read_text(encoding="utf-8"))

    def test_style_catalog_has_distinct_parseable_packaged_scaffolds(self):
        self.assertEqual(len(STYLE_CATALOG), 20)
        self.assertEqual(
            len({style.slug for style in STYLE_CATALOG}),
            len(STYLE_CATALOG),
        )
        self.assertEqual(
            len({style.structural_model for style in STYLE_CATALOG}),
            len(STYLE_CATALOG),
        )
        root = Path(__file__).resolve().parent.parent / "templates" / "presets"
        for style in STYLE_CATALOG:
            source = root / f"{style.slug}.svg"
            self.assertTrue(source.is_file(), style.slug)
            self.assertEqual(ET.parse(source).getroot().tag, "{http://www.w3.org/2000/svg}svg")

    def test_styles_json_is_machine_readable(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["styles", "--json"])
        self.assertEqual(code, 0)
        catalog = json.loads(out.getvalue())
        self.assertEqual(len(catalog), len(STYLE_CATALOG))
        self.assertEqual(catalog[0]["slug"], STYLE_CATALOG[0].slug)
        self.assertTrue(all(item["small_size_rule"] for item in catalog))
        self.assertTrue(all(item["tray_strategy"] for item in catalog))

    def test_styles_gallery_uses_every_packaged_scaffold(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "styles.png"
            with mock.patch(
                "iconflow.review.style_gallery", return_value=destination
            ) as gallery, contextlib.redirect_stdout(io.StringIO()):
                code = main(["styles", "--gallery", str(destination)])
        self.assertEqual(code, 0)
        sources, output = gallery.call_args.args
        self.assertEqual(len(sources), len(STYLE_CATALOG))
        self.assertEqual(output, destination)
        self.assertTrue(all("<svg" in svg for _style, svg in sources))

    def test_styles_gallery_refuses_silent_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "styles.png"
            destination.write_bytes(b"user work")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = main(["styles", "--gallery", str(destination)])
            preserved = destination.read_bytes()
        self.assertEqual(code, 2)
        self.assertEqual(preserved, b"user work")
        self.assertIn("--force", error.getvalue())

    def test_new_refuses_silent_overwrite_unless_forced(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "master.svg"
            destination.write_text("user work", encoding="utf-8")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                code = main(["new", "flat-geometric", "--out", str(destination)])
            self.assertEqual(code, 2)
            self.assertEqual(destination.read_text(encoding="utf-8"), "user work")
            self.assertIn("--force", error.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                code = main([
                    "new", "flat-geometric", "--out", str(destination), "--force",
                ])
            self.assertEqual(code, 0)
            self.assertIn("<svg", destination.read_text(encoding="utf-8"))

    def test_new_refuses_symlink_even_when_forced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "outside.svg"
            target.write_text("keep", encoding="utf-8")
            link = root / "master.svg"
            try:
                link.symlink_to(target)
            except (NotImplementedError, OSError):
                self.skipTest("symlink creation is unavailable on this platform")
            with contextlib.redirect_stderr(io.StringIO()):
                code = main([
                    "new", "flat-geometric", "--out", str(link), "--force",
                ])
            self.assertEqual(code, 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_doctor_without_browser_is_non_mutating_and_passes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["doctor", "--no-browser"])
        self.assertEqual(code, 0)
        self.assertIn("Packaged resources", out.getvalue())
        self.assertIn("IconFlow is ready", out.getvalue())

    def test_doctor_reports_missing_project_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "iconflow.toml"
            write_config(IconFlowConfig(
                source=config_path,
                master="missing.svg",
                tray_svg="missing-tray.svg",
                targets=["web", "tray"],
            ))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = main([
                    "doctor", "--config", str(config_path), "--no-browser",
                ])
        self.assertEqual(code, 1)
        self.assertIn("FAIL Master SVG", out.getvalue())
        self.assertIn("FAIL Semantic tray SVG", out.getvalue())

    def test_build_forwards_semantic_tray_options(self):
        build_module = importlib.import_module("iconflow.build")
        with mock.patch.object(build_module, "build", return_value=[]) as build, \
             contextlib.redirect_stdout(io.StringIO()):
            code = main([
                "build", "master.svg", "--targets", "tray",
                "--tray-svg", "tray.svg", "--tray-template-mode", "contrast",
            ])
        self.assertEqual(code, 0)
        self.assertEqual(build.call_args.kwargs["tray_svg"], "tray.svg")
        self.assertEqual(build.call_args.kwargs["tray_template_mode"], "contrast")

    def test_shortcut_forwards_content_addressed_delivery_mode(self):
        shortcut_module = importlib.import_module("iconflow.shortcut")
        with mock.patch.object(
            shortcut_module,
            "create_shortcut",
            return_value=["ICON shortcut-icon-deadbeefcafe.ico", "OK app.lnk"],
        ) as create_shortcut, contextlib.redirect_stdout(io.StringIO()):
            code = main([
                "shortcut", "--target", "app.exe", "--name", "Proof App",
                "--icon", "icon.ico", "--content-address-icon",
            ])

        self.assertEqual(code, 0)
        self.assertTrue(create_shortcut.call_args.kwargs["content_address_icon"])
        self.assertFalse(create_shortcut.call_args.kwargs["verify"])

    def test_review_config_populates_target_aware_review_lab(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            master = root / "master.svg"
            tray = root / "tray.svg"
            master.write_text('<svg viewBox="0 0 1024 1024"/>', encoding="utf-8")
            tray.write_text('<svg viewBox="0 0 1024 1024"/>', encoding="utf-8")
            config_path = root / "iconflow.toml"
            write_config(IconFlowConfig(
                source=config_path,
                name="Proof App",
                master="master.svg",
                user_job="prove one family",
                essence="proof",
                personality=["precise", "calm"],
                cliches=["sparkle"],
                signature_device="flow gate",
                targets=["web", "electron", "tray"],
                electron_radius=0.18,
                tray_svg="tray.svg",
                tray_template_mode="alpha",
            ))
            image_out = root / "review.png"
            html_out = root / "review.html"
            with mock.patch("iconflow.qa.check", return_value=["thin counter"]), \
                 mock.patch("iconflow.review.contact_sheet", return_value=image_out), \
                 mock.patch("iconflow.review.interactive_review", return_value=html_out) as lab, \
                 contextlib.redirect_stdout(io.StringIO()):
                code = main([
                    "review", "--config", str(config_path),
                    "--out", str(image_out), "--html", str(html_out),
                ])
        # Review rendered, but automated QA warnings gate it (exit 1).
        self.assertEqual(code, 1)
        options = lab.call_args.kwargs["options"]
        self.assertEqual(options.name, "Proof App")
        self.assertEqual(options.targets, ("web", "electron", "tray"))
        self.assertEqual(options.electron_radius, 0.18)
        self.assertEqual(Path(options.tray_svg).resolve(), Path(tray).resolve())
        self.assertEqual(options.tray_template_mode, "alpha")
        self.assertEqual(options.warnings, ("thin counter",))

    def test_case_atlas_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "nested" / "atlas.html"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main([
                    "case", "atlas", "--dir", directory, "--out", str(destination),
                ])
            self.assertEqual(code, 0)
            self.assertTrue(destination.is_file())
            self.assertIn("0 case(s)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
