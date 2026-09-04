# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The detail ladder: reduction, the shipped CSS layer, and the same-mark gate.

The reduction tests need no browser. The two that do are the ones that matter
most: that structural reduction and the ``@media`` layer produce *the same
pixels* at every size, and that a broken ladder is actually blocked.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from iconflow import ladder

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "detail-ladder" / "master.svg"
FLAT = REPO / "demo" / "master.svg"

LADDERED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" fill="#1b6"/>
<g data-lod="glyph mark plate"><rect x="20" y="20" width="60" height="60" fill="#fff"/></g>
<rect data-lod="mark plate" x="4" y="4" width="16" height="16" fill="#f00"/>
<rect data-lod="plate" x="80" y="80" width="16" height="16" fill="#00f"/>
</svg>"""

FLAT_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' \
           '<rect width="100" height="100" fill="#1b6"/></svg>'


class Rungs(unittest.TestCase):
    def test_every_built_size_maps_to_exactly_one_rung(self):
        self.assertEqual(ladder.rung_for_size(1), "glyph")
        self.assertEqual(ladder.rung_for_size(ladder.GLYPH_MAX), "glyph")
        self.assertEqual(ladder.rung_for_size(ladder.GLYPH_MAX + 1), "mark")
        self.assertEqual(ladder.rung_for_size(ladder.MARK_MAX), "mark")
        self.assertEqual(ladder.rung_for_size(ladder.MARK_MAX + 1), "plate")
        self.assertEqual(ladder.rung_for_size(1024), "plate")

    def test_a_bad_size_is_refused_rather_than_bucketed(self):
        for value in (0, -8, True, 2.5, "32"):
            with self.assertRaises(ladder.LadderError):
                ladder.rung_for_size(value)

    def test_unknown_rung_names_are_refused_with_the_valid_set(self):
        with self.assertRaises(ladder.LadderError) as caught:
            ladder.parse_rungs("glyph huge")
        self.assertIn("huge", str(caught.exception))
        self.assertIn("plate", str(caught.exception))

    def test_rung_lists_accept_spaces_or_commas_and_any_case(self):
        self.assertEqual(ladder.parse_rungs("Mark, PLATE"), frozenset({"mark", "plate"}))


class Reduction(unittest.TestCase):
    def test_a_flat_source_is_returned_byte_for_byte(self):
        for rung in ladder.RUNGS:
            self.assertEqual(ladder.reduce_svg(FLAT_SVG, rung), FLAT_SVG)

    def test_each_rung_keeps_only_what_it_was_promised(self):
        glyph = ladder.reduce_svg(LADDERED, "glyph")
        mark = ladder.reduce_svg(LADDERED, "mark")
        plate = ladder.reduce_svg(LADDERED, "plate")
        self.assertNotIn("#f00", glyph)
        self.assertNotIn("#00f", glyph)
        self.assertIn("#f00", mark)
        self.assertNotIn("#00f", mark)
        self.assertIn("#00f", plate)
        # The unannotated background belongs to every rung.
        for text in (glyph, mark, plate):
            self.assertIn("#1b6", text)

    def test_a_reduced_source_carries_no_ladder_metadata(self):
        for rung in ladder.RUNGS:
            reduced = ladder.reduce_svg(ladder.with_media_layer(LADDERED), rung)
            self.assertNotIn("data-lod", reduced)
            self.assertNotIn(ladder.LADDER_MARKER_VALUE, reduced)

    def test_annotating_the_root_is_refused_instead_of_erasing_the_icon(self):
        rooted = LADDERED.replace("<svg ", '<svg data-lod="plate" ', 1)
        with self.assertRaises(ladder.LadderError):
            ladder.reduce_svg(rooted, "glyph")


class MediaLayer(unittest.TestCase):
    def test_a_flat_source_gains_no_stylesheet(self):
        self.assertEqual(ladder.with_media_layer(FLAT_SVG), FLAT_SVG)

    def test_the_layer_is_inserted_once_and_only_once(self):
        once = ladder.with_media_layer(LADDERED)
        self.assertEqual(once.count(ladder.LADDER_MARKER_VALUE), 1)
        self.assertEqual(ladder.with_media_layer(once), once)

    def test_the_document_may_mention_the_marker_in_its_own_prose(self):
        # The guard reads the marker as an attribute, not as a word: a source
        # whose <title> says "detail-ladder" still gets its stylesheet.
        described = LADDERED.replace(
            "<svg xmlns", '<svg data-note="x" xmlns', 1
        ).replace("<rect width", "<title>a detail-ladder study</title><rect width", 1)
        self.assertFalse(ladder.has_media_layer(described))
        self.assertTrue(ladder.has_media_layer(ladder.with_media_layer(described)))

    def test_the_author_bytes_survive_around_the_inserted_layer(self):
        layered = ladder.with_media_layer(LADDERED)
        head, _, tail = layered.partition("</style>")
        self.assertTrue(head.startswith('<svg xmlns="http://www.w3.org/2000/svg"'))
        self.assertIn('<rect data-lod="mark plate" x="4"', tail)

    def test_a_renderer_that_ignores_media_queries_falls_back_to_the_plate(self):
        # The only rule outside a media block keeps the plate rung, so the
        # worst case is the complete artwork rather than an empty icon.
        first_rule = ladder.LADDER_CSS.split("@media", 1)[0]
        self.assertIn('[data-lod]:not([data-lod~="plate"]){display:none}', first_rule)


class Invariant(unittest.TestCase):
    """The measurement layer, exercised on synthetic PNGs (no browser)."""

    @staticmethod
    def _png(draw) -> bytes:
        import io

        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw(ImageDraw.Draw(image))
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        return buffer.getvalue()

    def test_identical_rungs_are_a_perfect_match(self):
        png = self._png(lambda d: d.rectangle([16, 16, 48, 48], fill=(240, 60, 40, 255)))
        step = ladder.compare_rungs(png, png, smaller="glyph", larger="plate")
        self.assertEqual(step["footprint_containment"], 1.0)
        self.assertEqual(step["footprint_iou"], 1.0)
        self.assertEqual(step["visible_iou"], 1.0)
        self.assertEqual(step["centroid_drift"], 0.0)

    def test_a_rung_that_draws_somewhere_else_is_blocked(self):
        small = self._png(lambda d: d.rectangle([2, 2, 20, 20], fill=(240, 60, 40, 255)))
        large = self._png(lambda d: d.rectangle([40, 40, 62, 62], fill=(240, 60, 40, 255)))
        findings, steps = ladder.identity_findings({"glyph": small, "plate": large})
        codes = {f.code for f in findings}
        self.assertIn("ladder-silhouette", codes)
        self.assertIn("ladder-centroid", codes)
        self.assertEqual(len(steps), 1)

    def test_a_rung_with_its_own_palette_is_blocked(self):
        blue = self._png(lambda d: d.ellipse([8, 8, 56, 56], fill=(40, 110, 220, 255)))
        red = self._png(lambda d: d.ellipse([8, 8, 56, 56], fill=(220, 70, 40, 255)))
        findings, _ = ladder.identity_findings({"glyph": blue, "plate": red})
        self.assertIn("ladder-hue", {f.code for f in findings})

    def test_an_empty_rung_is_named_rather_than_silently_shipped(self):
        blank = self._png(lambda d: None)
        drawn = self._png(lambda d: d.ellipse([8, 8, 56, 56], fill=(40, 110, 220, 255)))
        findings, _ = ladder.identity_findings({"glyph": blank, "plate": drawn})
        self.assertIn("ladder-empty-rung", {f.code for f in findings})

    def test_rungs_measured_at_different_sizes_are_refused(self):
        import io

        from PIL import Image

        def sized(side):
            buffer = io.BytesIO()
            Image.new("RGBA", (side, side), (10, 10, 10, 255)).save(buffer, "PNG")
            return buffer.getvalue()

        with self.assertRaises(ladder.LadderError):
            ladder.compare_rungs(sized(32), sized(64), smaller="glyph", larger="plate")

    def test_a_source_with_no_glyph_rung_is_named(self):
        missing = LADDERED.replace('data-lod="glyph mark plate"', 'data-lod="mark plate"')
        codes = {f.code for f in ladder.annotation_findings(missing)}
        self.assertIn("ladder-annotation", codes)
        self.assertFalse(ladder.annotation_findings(LADDERED))
        self.assertFalse(ladder.annotation_findings(FLAT_SVG))


class RenderedLadder(unittest.TestCase):
    """Chromium is the ground truth for both mechanisms, so prove they agree."""

    @classmethod
    def setUpClass(cls):
        try:
            from iconflow.rasterize import Rasterizer
        except ImportError:  # pragma: no cover
            raise unittest.SkipTest("Playwright is not installed")
        cls.Rasterizer = Rasterizer

    def test_structural_reduction_and_the_css_layer_render_the_same_pixels(self):
        from iconflow.rasterize import load_svg

        svg = load_svg(EXAMPLE)
        layered = ladder.with_media_layer(svg)
        source = ladder.RungSource(svg)
        boundaries = (
            16,
            ladder.GLYPH_MAX,
            ladder.GLYPH_MAX + 1,
            ladder.MARK_MAX,
            ladder.MARK_MAX + 1,
            512,
        )
        with self.Rasterizer() as rasterizer:
            for size in boundaries:
                with self.subTest(size=size):
                    self.assertEqual(
                        source.render(rasterizer, size),
                        rasterizer.render(layered, size),
                        f"the shipped vector and the built raster disagree at {size}px",
                    )

    def test_the_worked_example_passes_its_own_gate(self):
        report = ladder.ladder_report(EXAMPLE)
        self.assertTrue(report["ladder"])
        self.assertEqual(report["rungs"], list(ladder.RUNGS))
        self.assertEqual(report["findings"], [])
        # The example exists to show detail appearing, so it must actually appear.
        visible = {m["rung"]: m["visible"] for m in report["measures"]}
        self.assertLess(visible["glyph"], visible["mark"])
        self.assertLess(visible["mark"], visible["plate"])

    def test_a_flat_master_reports_no_ladder_and_no_findings(self):
        report = ladder.ladder_report(FLAT)
        self.assertFalse(report["ladder"])
        self.assertEqual(report["rungs"], [])
        self.assertEqual(report["steps"], [])
        self.assertEqual(report["findings"], [])


class GateIntegration(unittest.TestCase):
    def test_check_runs_the_invariant_and_blocks_a_broken_ladder(self):
        import tempfile

        from iconflow.qa import check

        broken = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
<rect width="1024" height="1024" rx="228" fill="#1E1B22"/>
<g data-lod="glyph"><circle cx="300" cy="300" r="180" fill="#F0DFC6"/></g>
<g data-lod="mark plate"><rect x="560" y="560" width="360" height="360" fill="#F0DFC6"/></g>
</svg>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.svg"
            path.write_text(broken, encoding="utf-8")
            codes = {w.code for w in check(path, maskable=False)}
        self.assertIn("ladder-silhouette", codes)

    def test_the_16px_stroke_floor_ignores_strokes_that_never_reach_16px(self):
        import tempfile

        from iconflow.qa import check

        # A hairline that exists only on the plate rung cannot vanish at 16px.
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
<g data-lod="glyph mark plate"><circle cx="512" cy="512" r="380" fill="#2B6FE0"/></g>
<g data-lod="plate"><path d="M240 512H784" stroke="#ffffff" stroke-width="8"/></g>
</svg>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hairline.svg"
            path.write_text(svg, encoding="utf-8")
            codes = {w.code for w in check(path, maskable=False)}
        self.assertNotIn("stroke-floor", codes)

    def test_a_real_build_puts_plate_detail_only_in_plate_sized_files(self):
        """The end-to-end claim: the ladder reaches the files that ship."""
        import tempfile

        from PIL import Image

        from iconflow.build import build

        # #FFB067 is the example's ember core, drawn on the plate rung alone.
        target = (255, 176, 103)

        def carries_plate_detail(path: Path) -> bool:
            with Image.open(path) as image:
                pixels = image.convert("RGB")
                data = (
                    pixels.get_flattened_data()
                    if hasattr(pixels, "get_flattened_data") else pixels.getdata()
                )
                return any(
                    all(abs(channel - want) < 6 for channel, want in zip(rgb, target))
                    for rgb in data
                )

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(EXAMPLE, out, targets=("web", "tauri"), name="Kiln")
            below = ["icons/32x32.png", "icons/64x64.png", "icons/128x128.png",
                     "icons/128x128@2x.png", "icon-192.png"]
            for name in below:
                with self.subTest(file=name):
                    self.assertFalse(
                        carries_plate_detail(out / name),
                        f"{name} is at or below {ladder.MARK_MAX}px and must not "
                        "carry plate-rung detail",
                    )
            for name in ("icon-512.png", "icons/icon.png"):
                with self.subTest(file=name):
                    self.assertTrue(
                        carries_plate_detail(out / name),
                        f"{name} is above {ladder.MARK_MAX}px and should carry the "
                        "plate rung",
                    )
            favicon = (out / "favicon.svg").read_text(encoding="utf-8")
            self.assertTrue(ladder.has_media_layer(favicon))

    def test_the_built_favicon_carries_the_layer_only_when_the_source_uses_it(self):
        import tempfile

        from iconflow.build import write_favicon_svg
        from iconflow.rasterize import load_svg

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            flat_src = root / "flat.svg"
            flat_src.write_text(FLAT_SVG, encoding="utf-8")
            flat_out = root / "flat-favicon.svg"
            self.assertFalse(write_favicon_svg(load_svg(flat_src), flat_src, flat_out))
            self.assertEqual(flat_out.read_bytes(), flat_src.read_bytes())

            lad_src = root / "lad.svg"
            lad_src.write_text(LADDERED, encoding="utf-8")
            lad_out = root / "lad-favicon.svg"
            self.assertTrue(write_favicon_svg(load_svg(lad_src), lad_src, lad_out))
            self.assertTrue(ladder.has_media_layer(lad_out.read_text(encoding="utf-8")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
