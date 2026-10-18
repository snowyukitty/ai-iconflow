# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The 16px legibility budget (iconflow/budget.py).

Synthetic marks are drawn on the 1024 grid with Pillow and reduced to the
256px analysis render and the 16px render, so every threshold is tested in
grid units without a browser.
"""
import io
import unittest

from PIL import Image, ImageDraw

from iconflow import budget

INK = (24, 30, 60, 255)
CARD = (20, 35, 53, 255)
PAPER = (250, 244, 232, 255)


def renders(draw_fn, *, background=(0, 0, 0, 0)):
    image = Image.new("RGBA", (1024, 1024), background)
    draw_fn(ImageDraw.Draw(image))
    out = []
    for size in (256, 16):
        buffer = io.BytesIO()
        image.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA").save(buffer, "PNG")
        out.append(buffer.getvalue())
    return out


def codes(result):
    return sorted({finding.code for finding in result.findings()})


class BudgetTests(unittest.TestCase):
    def test_a_well_budgeted_mark_is_within_budget(self):
        def mark(d):
            d.rectangle([128, 128, 896, 896], fill=INK)
            d.rectangle([384, 384, 640, 640], fill=(0, 0, 0, 0))   # a 256-unit cut
        result = budget.measure(*renders(mark))
        self.assertEqual(codes(result), [])
        self.assertEqual((result.cuts_256, result.cuts_16), (1, 1))

    def test_a_narrow_cut_is_measured_in_grid_units(self):
        def mark(d):
            d.rectangle([128, 128, 896, 896], fill=INK)
            d.rectangle([476, 256, 548, 768], fill=(0, 0, 0, 0))   # a 72-unit slit
        result = budget.measure(*renders(mark))
        cuts = [f for f in result.features if f.kind == "cut"]
        self.assertTrue(cuts, result.as_dict())
        self.assertLess(abs(cuts[0].width_units - 72), 17)
        self.assertIn("budget-cut", codes(result))
        self.assertIn("(L15)", str(result.findings()[0]))

    def test_two_parts_with_a_hairline_gap_fuse(self):
        def mark(d):
            d.rectangle([128, 256, 496, 768], fill=INK)
            d.rectangle([528, 256, 896, 768], fill=INK)            # 32-unit gap
        result = budget.measure(*renders(mark))
        self.assertIn("budget-gap", codes(result))
        self.assertIn("budget-fused-parts", codes(result))
        self.assertEqual(result.parts_256, 2)

    def test_a_two_pixel_gap_survives(self):
        def mark(d):
            d.rectangle([128, 256, 448, 768], fill=INK)
            d.rectangle([576, 256, 896, 768], fill=INK)            # 128-unit gap
        result = budget.measure(*renders(mark))
        self.assertNotIn("budget-gap", codes(result))
        self.assertEqual(result.parts_16, 2)

    def test_a_thin_detached_accent_is_flagged(self):
        def mark(d):
            d.rectangle([128, 128, 704, 896], fill=INK)
            d.rectangle([832, 160, 888, 216], fill=(240, 90, 60, 255))  # 56-unit accent
        result = budget.measure(*renders(mark))
        self.assertIn("budget-accent", codes(result))

    def test_a_mark_inside_a_tile_reports_its_share(self):
        def mark(d):
            d.rounded_rectangle([0, 0, 1023, 1023], radius=200, fill=CARD)
            d.ellipse([352, 352, 672, 672], fill=PAPER)            # spans ~31%
        result = budget.measure(*renders(mark))
        self.assertEqual(result.ground, "#142335")
        self.assertLess(result.tile_share, budget.TILE_SHARE_FLOOR)
        self.assertIn("budget-tile", codes(result))

    def test_measurement_is_advisory_and_serialisable(self):
        def mark(d):
            d.rectangle([128, 256, 496, 768], fill=INK)
            d.rectangle([528, 256, 896, 768], fill=INK)
        payload = budget.measure(*renders(mark), source="x.svg").as_dict()
        self.assertEqual(payload["budget_units"], 128)
        self.assertTrue(all(f["code"].startswith("budget-") for f in payload["findings"]))

    def test_the_analysis_size_is_enforced(self):
        small = renders(lambda d: d.rectangle([0, 0, 10, 10], fill=INK))[1]
        with self.assertRaises(ValueError):
            budget.measure(small, small)


class BudgetCommandTests(unittest.TestCase):
    def test_budget_json_envelope_is_advisory_only(self):
        import contextlib
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock

        from iconflow.cli import main

        def mark(d):
            d.rectangle([128, 256, 496, 768], fill=INK)
            d.rectangle([528, 256, 896, 768], fill=INK)
        big, small = renders(mark)

        class Fake:
            def __init__(self, **_):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def render(self, _svg, size, bg="transparent"):
                return big if size == 256 else small

        with tempfile.TemporaryDirectory() as tmp:
            svg = Path(tmp) / "a.svg"
            svg.write_text('<svg viewBox="0 0 1024 1024"></svg>', encoding="utf-8")
            out = io.StringIO()
            with mock.patch("iconflow.rasterize.Rasterizer", Fake),                  contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = main(["budget", str(svg), "--sheet", str(Path(tmp) / "b.png"), "--json"])
            envelope = json.loads(out.getvalue())
            self.assertTrue((Path(tmp) / "b.png").is_file())
        self.assertEqual(code, 0)
        self.assertEqual(envelope["warnings"], [])
        self.assertIn("budget-gap", {a["code"] for a in envelope["advisories"]})
        self.assertEqual(envelope["outputs"]["candidates"][0]["parts"]["at_256"], 2)


if __name__ == "__main__":
    unittest.main()
