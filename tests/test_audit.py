# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""One audit for check, review and ship (iconflow/audit.py).

The regression this guards: on 2026-10-18 ``check --config`` passed a
full-bleed 3x3 grid while ``review`` and ``ship`` failed it on the maskable
audit, because ``check`` composed the maskable icon on white and the other two
on the configured background. Every test here runs the three commands on one
SVG and one config and fails if any two of them audit different inputs or
reach different findings.
"""
import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from iconflow import qa
from iconflow.audit import resolve_inputs
from iconflow.cli import main
from iconflow.config import config_review_contract_digest, load_config, svg_sha256

BUILD_MODULE = importlib.import_module("iconflow.build")
INK = "#11142A"
# A green that holds contrast on white and on ink, and whose maskable audit
# flips with the background: it fails on white and passes on ink.
LIME = (130, 200, 50, 255)


def grid_png(size: int) -> bytes:
    """A full-bleed 3x3 grid of lime cells on transparency, gutters ~6%."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    gutter = max(1, round(size * 0.0625))
    cell = (size - 2 * gutter) / 3
    for row in range(3):
        for column in range(3):
            x0 = round(column * (cell + gutter))
            y0 = round(row * (cell + gutter))
            draw.rectangle([x0, y0, round(x0 + cell) - 1, round(y0 + cell) - 1], fill=LIME)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def stub_plan():
    """A tiny real RenderPlan, so ship's plan seam can be stubbed without Chromium."""
    from iconflow.plan import RenderPlan

    return RenderPlan.create({"favicon.svg": b"<svg/>"}, inputs={}, parameters={}, toolchain={})


class GridRasterizer:
    def __init__(self, color_scheme="light", **_options):
        self.color_scheme = color_scheme

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, _svg, size, bg="transparent"):
        return grid_png(size)


GRID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
    '<rect width="1024" height="1024" fill="#c6f24e"/></svg>'
)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue()


class ProjectFixture(unittest.TestCase):
    targets = '["web", "tauri"]'
    extra_build = ""
    background = INK

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.master = self.dir / "master.svg"
        self.master.write_text(GRID_SVG, encoding="utf-8")
        self.config_path = self.dir / "iconflow.toml"
        self.write_config(status="pending")
        config = load_config(self.config_path)
        self.write_config(
            status="approved",
            source=svg_sha256(self.master),
            contract=config_review_contract_digest(config),
        )

    def write_config(self, *, status, source="", contract=""):
        self.config_path.write_text(f'''schema_version = 1
[project]
name = "Grid"
master = "master.svg"
output = "out"
[build]
targets = {self.targets}
theme_color = "{INK}"
background_color = "{self.background}"
{self.extra_build}
[review]
status = "{status}"
source_sha256 = "{source}"
contract_sha256 = "{contract}"
scores = {{ legibility = 4, distinctiveness = 4, balance = 4, color = 4, scalability = 4, craft = 4 }}
''', encoding="utf-8")

    def run_all_three(self):
        """Run check, review and ship; return per-command (check kwargs, envelope)."""
        real_check = qa.check
        seen: dict[str, list[dict]] = {}
        current = []

        def spy(master, **kwargs):
            kwargs.pop("rasterizer", None)
            current.append({"master": str(Path(master).resolve()), **kwargs})
            return real_check(master, **kwargs)

        results = {}
        with mock.patch("iconflow.qa.Rasterizer", GridRasterizer), \
             mock.patch("iconflow.qa.check", side_effect=spy), \
             mock.patch("iconflow.review.contact_sheet", return_value=self.dir / "r.png"), \
             mock.patch("iconflow.plan.compute_plan", return_value=stub_plan()), \
             mock.patch("iconflow.plan.write_plan", return_value=[]):
            for name, argv in (
                ("check", ["check", "--config", str(self.config_path)]),
                ("review", ["review", "--config", str(self.config_path),
                            "--out", str(self.dir / "r.png")]),
                ("ship", ["ship", "--config", str(self.config_path)]),
            ):
                current.clear()
                code, envelope, _ = run(argv)
                seen[name] = list(current)
                results[name] = (code, envelope)
        return seen, results


class SharedAuditTests(ProjectFixture):
    def test_check_review_and_ship_audit_identical_inputs(self):
        seen, results = self.run_all_three()
        self.assertEqual(len(seen["check"]), 1)
        self.assertEqual(seen["check"], seen["review"], "check and review audited different inputs")
        self.assertEqual(seen["check"], seen["ship"], "check and ship audited different inputs")
        # The 2026-10-18 bug: the maskable icon must be composed on the
        # configured background, not on white, in every command.
        self.assertEqual(seen["check"][0]["maskable_bg"], INK)
        audits = {name: envelope["outputs"].get("audit") for name, (_, envelope) in results.items()
                  if envelope["outputs"]}
        self.assertEqual(audits["check"], audits["review"])

    def test_check_review_and_ship_reach_identical_findings(self):
        _seen, results = self.run_all_three()
        findings = {
            name: [(w["code"], w["message"]) for w in envelope["warnings"]
                   if w["code"] != "qa-warnings"]
            for name, (_code, envelope) in results.items()
        }
        self.assertEqual(findings["check"], findings["review"])
        self.assertEqual(findings["check"], findings["ship"])
        exits = {name: code for name, (code, _envelope) in results.items()}
        self.assertEqual(len(set(exits.values())), 1, exits)

    def test_the_grid_fixture_is_sensitive_to_the_background(self):
        """Proves the tests above would have caught the 0.6 behaviour."""
        with mock.patch("iconflow.qa.Rasterizer", GridRasterizer):
            on_white = [w.code for w in qa.check(self.master, maskable_bg="#ffffff")]
            on_ink = [w.code for w in qa.check(self.master, maskable_bg=INK)]
        self.assertNotEqual(on_white, on_ink)

    def test_every_maskable_warning_names_its_inputs(self):
        with mock.patch("iconflow.qa.Rasterizer", GridRasterizer):
            warnings = qa.check(self.master, maskable_bg="#ffffff")
        maskable = [w for w in warnings if w.code == "maskable-detail"]
        self.assertTrue(maskable, [str(w) for w in warnings])
        message = str(maskable[0])
        self.assertIn("#FFFFFF", message)
        self.assertIn("scale 0.8", message)
        self.assertIn("maskable_scale", message)  # the concrete fix
        self.assertEqual(qa.warning_code(message), "maskable-detail")

    def test_overrides_beat_the_config_and_the_config_beats_defaults(self):
        config = load_config(self.config_path)
        inputs = resolve_inputs(config=config)
        self.assertEqual(inputs.background_color, INK)
        self.assertEqual(inputs.targets, ("web", "tauri"))
        self.assertTrue(inputs.maskable_audited)
        overridden = resolve_inputs(config=config, background_color="#ffffff", targets=["tauri"])
        self.assertEqual(overridden.background_color, "#ffffff")
        self.assertFalse(overridden.maskable_audited)
        bare = resolve_inputs(master=self.master)
        self.assertEqual((bare.background_color, bare.targets), ("#ffffff", ("web", "pwa")))


class LazyRendererTests(ProjectFixture):
    def test_an_audit_that_renders_nothing_never_starts_chromium(self):
        from iconflow.audit import run_audit

        started = []

        class Exploding:
            def __init__(self, **_):
                started.append(True)

            def __enter__(self):
                raise AssertionError("Chromium must not start")

        with mock.patch("iconflow.qa.Rasterizer", Exploding), \
             mock.patch("iconflow.qa.check", return_value=[]):
            result = run_audit(resolve_inputs(config=load_config(self.config_path)))
        self.assertEqual((result.warnings, started), ([], []))


class MaskableScaleTests(ProjectFixture):
    extra_build = "maskable_scale = 0.6"
    background = "#FFFFFF"  # where the default 0.8 composition fails this grid

    def test_the_default_composition_fails_on_this_background(self):
        with mock.patch("iconflow.qa.Rasterizer", GridRasterizer):
            codes = [w.code for w in qa.check(self.master, maskable_bg=self.background)]
        self.assertIn("maskable-detail", codes)

    def test_a_smaller_maskable_scale_passes_without_changing_the_mark(self):
        seen, results = self.run_all_three()
        self.assertEqual({call["maskable_scale"] for calls in seen.values() for call in calls}, {0.6})
        for name, (code, envelope) in results.items():
            codes = [w["code"] for w in envelope["warnings"]]
            self.assertNotIn("maskable-detail", codes, name)
        self.assertEqual(results["ship"][0], 0)

    def test_maskable_scale_is_bound_into_the_contract(self):
        config = load_config(self.config_path)
        self.assertEqual(config.build_contract()["maskable_scale"], 0.6)
        approved = config.review_contract_sha256
        self.config_path.write_text(
            self.config_path.read_text(encoding="utf-8").replace("0.6", "0.65"), encoding="utf-8",
        )
        self.assertNotEqual(config_review_contract_digest(load_config(self.config_path)), approved)


class DefaultContractTests(ProjectFixture):
    extra_build = "maskable_scale = 0.8"

    def test_an_explicit_default_scale_changes_no_contract(self):
        config = load_config(self.config_path)
        self.assertNotIn("maskable_scale", config.build_contract())
        self.assertNotIn("maskable_source_sha256", config.build_contract())


if __name__ == "__main__":
    unittest.main()
