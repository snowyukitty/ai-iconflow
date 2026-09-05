# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The neighbourhood: the shape field, the index, the query, and the gate.

The field and the query are exercised on synthetic masks and on fields read
back from the checked-in index, so the default matrix proves the claims
without a browser. The tests that render — that the metric separates the
casebook's recorded collisions, that the index rebuilds from source, that
`check` gates and does not gate — opt in with ``ICONFLOW_BROWSER_TESTS=1`` and
run in the ``chromium-integration`` job, because a guarded test nobody runs is
not a test.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from iconflow import neighbours, shapefield
from iconflow.findings import Finding

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "neighbourhood"
EXAMPLE = REPO / "examples" / "neighbourhood"
COLLISION = REPO / "iconflow" / "resources" / "collision"
INDEX = COLLISION / "index.json"

NEEDS_CHROMIUM = unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)


def _mask(draw) -> Image.Image:
    mask = Image.new("L", (shapefield.SAMPLE_SIZE, shapefield.SAMPLE_SIZE), 0)
    draw(ImageDraw.Draw(mask))
    return mask


def _png(draw, size=shapefield.SAMPLE_SIZE) -> bytes:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw(ImageDraw.Draw(image))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class _FakeRasterizer:
    """Renders nothing: a flat 64px disc, so declared files resolve without Chromium."""

    def render(self, svg_text: str, size: int, **_kwargs) -> bytes:
        return _png(lambda d: d.ellipse([8, 8, 55, 55], fill=(20, 20, 20, 255)), size)


def _entry(entry_id: str, field: shapefield.ShapeField, *, set_name="house",
           sha: str | None = None) -> neighbours.Entry:
    return neighbours.Entry(
        id=entry_id, set=set_name, title=entry_id.rsplit("/", 1)[-1],
        source=f"{entry_id}.svg", source_sha256=sha or ("0" * 63 + entry_id[-1]),
        field=field,
    )


class ShapeFieldTests(unittest.TestCase):
    """The descriptor: every field explainable, every value reproducible."""

    def test_a_full_cell_is_sixteen_sixteenths_and_a_quarter_cell_is_four(self):
        # A 4x4 block that is fully inked is 1.0; a 2x2 corner of it is 0.25.
        field = shapefield.field_from_mask(_mask(
            lambda d: (d.rectangle([0, 0, 3, 3], fill=255),
                       d.rectangle([4, 4, 5, 5], fill=255))
        ))
        self.assertEqual(field.cell(0, 0), 1.0)
        self.assertEqual(field.cell(1, 1), 0.25)
        self.assertEqual(field.cell(2, 2), 0.0)

    def test_topology_counts_pieces_and_holes_and_ignores_debris(self):
        ring = _mask(lambda d: (d.ellipse([8, 8, 55, 55], fill=255),
                                d.ellipse([22, 22, 41, 41], fill=0)))
        field = shapefield.field_from_mask(ring)
        self.assertEqual((field.components, field.holes), (1, 1))
        two = _mask(lambda d: (d.rectangle([4, 4, 24, 60], fill=255),
                               d.rectangle([40, 4, 60, 60], fill=255),
                               d.point((32, 32), fill=255)))  # one-pixel debris
        field = shapefield.field_from_mask(two)
        self.assertEqual((field.components, field.holes), (2, 0))

    def test_coverage_and_aspect_are_what_they_say(self):
        wide = _mask(lambda d: d.rectangle([0, 16, 63, 31], fill=255))
        field = shapefield.field_from_mask(wide)
        self.assertAlmostEqual(field.coverage, 0.25)
        self.assertEqual(field.aspect, 4.0)
        self.assertEqual(shapefield.field_from_mask(_mask(lambda d: None)).aspect, 0.0)

    def test_the_encoded_grid_round_trips_exactly(self):
        field = shapefield.field_from_mask(_mask(
            lambda d: d.ellipse([5, 9, 50, 58], fill=255)
        ))
        encoded = field.encode_grid()
        self.assertEqual(len(encoded), shapefield.GRID * shapefield.GRID)
        self.assertEqual(shapefield.decode_grid(encoded), field.grid)
        self.assertEqual(shapefield.ShapeField.from_dict(field.as_dict()), field)

    def test_a_mask_of_the_wrong_size_is_refused(self):
        with self.assertRaises(shapefield.ShapeFieldError):
            shapefield.field_from_mask(Image.new("L", (32, 32)))
        with self.assertRaises(shapefield.ShapeFieldError):
            shapefield.decode_grid("0" * 10)

    def test_a_card_is_fingerprinted_by_the_mark_punched_into_it(self):
        # Dark rounded card, light disc inside: the field is the disc, not
        # the card, and the transparent corners are never figure.
        card = _png(lambda d: (
            d.rounded_rectangle([0, 0, 63, 63], radius=14, fill=(30, 30, 40, 255)),
            d.ellipse([20, 20, 43, 43], fill=(240, 235, 225, 255)),
        ))
        field = shapefield.field_from_png(card)
        self.assertEqual((field.components, field.holes), (1, 0))
        self.assertLess(field.coverage, 0.2)
        self.assertEqual(field.cell(0, 0), 0.0)
        self.assertGreater(field.cell(8, 8), 0.9)

    def test_a_transparent_hole_inside_the_mark_is_not_the_outer_boundary(self):
        # Dark card, white square inside, transparent hole punched through the
        # square: the white ring lines the hole, not the rim, so it is the figure.
        card = _png(lambda d: (
            d.rectangle([0, 0, 63, 63], fill=(30, 30, 40, 255)),
            d.rectangle([16, 16, 47, 47], fill=(245, 245, 245, 255)),
            d.rectangle([24, 24, 39, 39], fill=(0, 0, 0, 0)),
        ))
        field = shapefield.field_from_png(card)
        self.assertEqual((field.components, field.holes), (1, 1))
        self.assertAlmostEqual(field.coverage, (32 * 32 - 16 * 16) / 4096, places=3)

    def test_a_plain_ink_mark_is_its_own_footprint(self):
        disc = _png(lambda d: d.ellipse([8, 8, 55, 55], fill=(20, 20, 20, 255)))
        light = _png(lambda d: d.ellipse([8, 8, 55, 55], fill=(250, 250, 250, 255)))
        self.assertEqual(shapefield.field_from_png(disc).grid,
                         shapefield.field_from_png(light).grid)

    def test_a_two_tone_object_whose_colours_both_reach_the_edge_is_one_shape(self):
        # Half dark, half light, side by side on transparency: neither class
        # is enclosed, so the figure is the whole object.
        flag = _png(lambda d: (
            d.rectangle([8, 16, 31, 47], fill=(30, 30, 30, 255)),
            d.rectangle([32, 16, 55, 47], fill=(230, 230, 230, 255)),
        ))
        field = shapefield.field_from_png(flag)
        self.assertEqual(field.components, 1)
        self.assertAlmostEqual(field.coverage, 48 * 32 / 4096, places=3)

    def test_distance_is_zero_for_a_twin_and_one_for_disjoint_ink(self):
        left = shapefield.field_from_mask(_mask(lambda d: d.rectangle([0, 0, 27, 63], fill=255)))
        right = shapefield.field_from_mask(_mask(lambda d: d.rectangle([36, 0, 63, 63], fill=255)))
        self.assertEqual(shapefield.separation(left, left).distance, 0.0)
        self.assertEqual(shapefield.separation(left, right).distance, 1.0)
        self.assertEqual(shapefield.grid_distance((0.0,) * 256, (0.0,) * 256), 0.0)

    def test_topology_is_reported_beside_the_distance_not_added_to_it(self):
        disc = shapefield.field_from_mask(_mask(lambda d: d.ellipse([8, 8, 55, 55], fill=255)))
        ring = shapefield.field_from_mask(_mask(
            lambda d: (d.ellipse([8, 8, 55, 55], fill=255), d.ellipse([28, 28, 35, 35], fill=0))
        ))
        sep = shapefield.separation(disc, ring)
        self.assertLess(sep.distance, 0.05)
        self.assertFalse(sep.same_topology)
        self.assertEqual(sep.holes, (0, 1))


class IndexTests(unittest.TestCase):
    """The checked-in index is content-addressed and dated by construction."""

    @classmethod
    def setUpClass(cls):
        cls.index = neighbours.parse_index(INDEX.read_text(encoding="utf-8"))

    def test_the_index_speaks_the_current_descriptor_and_both_halves_are_present(self):
        self.assertEqual(self.index.descriptor_version, shapefield.VERSION)
        self.assertGreaterEqual(len(self.index.by_set("collision")), 30)
        self.assertGreaterEqual(len(self.index.by_set("house")), 600)
        self.assertEqual(self.index.generator, "scripts/build_collision_index.py")

    def test_every_entry_still_hashes_to_its_source(self):
        """A source edited without rebuilding the index fails here, no browser needed."""
        sys.path.insert(0, str(REPO / "scripts"))
        try:
            import build_collision_index as generator
        finally:
            sys.path.pop(0)
        self.assertEqual(generator.check_sources(self.index), [])

    def test_the_committed_bytes_are_exactly_what_the_generator_writes(self):
        sys.path.insert(0, str(REPO / "scripts"))
        try:
            import build_collision_index as generator
        finally:
            sys.path.pop(0)
        self.assertEqual(
            generator.render_index(list(self.index.entries)),
            INDEX.read_text(encoding="utf-8"),
            "run python scripts/build_collision_index.py",
        )

    def test_every_collision_form_has_a_title_and_a_non_empty_field(self):
        for entry in self.index.by_set("collision"):
            with self.subTest(entry=entry.id):
                self.assertTrue(entry.title)
                self.assertFalse(entry.field.empty)
                self.assertTrue((REPO / entry.source).is_file())

    def test_an_index_from_another_descriptor_version_is_refused(self):
        data = json.loads(INDEX.read_text(encoding="utf-8"))
        data["descriptor"]["version"] = shapefield.VERSION + 1
        with self.assertRaises(neighbours.NeighbourError):
            neighbours.parse_index(json.dumps(data))

    def test_the_bundled_forms_are_plain_and_distinct(self):
        """The set is only useful if a bell is not already a cloud."""
        forms = self.index.by_set("collision")
        for entry in forms:
            for other in forms:
                if entry.id < other.id:
                    with self.subTest(pair=(entry.id, other.id)):
                        self.assertGreater(
                            shapefield.separation(entry.field, other.field).distance,
                            0.06,
                        )


class QueryTests(unittest.TestCase):
    """The gate's semantics on fields read from the index — no rendering."""

    @classmethod
    def setUpClass(cls):
        cls.index = neighbours.parse_index(INDEX.read_text(encoding="utf-8"))
        cls.bell = cls.index.get("collision/bell")
        cls.gear = cls.index.get("collision/gear")
        assert cls.bell and cls.gear

    def _candidate(self, like: neighbours.Entry) -> neighbours.Entry:
        return neighbours.Entry(
            id="candidate", set="candidate", title="Candidate", source="candidate.svg",
            source_sha256="f" * 64, field=like.field,
        )

    def test_the_bundled_corpus_never_gates(self):
        hood = neighbours.neighbourhood(self._candidate(self.bell), index=self.index)
        warnings, advisories = hood.findings()
        self.assertEqual(warnings, [])
        # The plain bell, and whichever house bells are bells at 16px too.
        self.assertEqual({a.code for a in advisories}, {"neighbour-familiar"})
        self.assertEqual(hood.familiar[0].entry.id, "collision/bell")
        self.assertTrue(any("collision/bell" in a for a in advisories))

    def test_a_declared_avoid_entry_gates_and_names_the_mark(self):
        avoid = [_entry("avoid/their-bell", self.bell.field, set_name="avoid", sha="a" * 64)]
        hood = neighbours.neighbourhood(self._candidate(self.bell), index=self.index, avoid=avoid)
        warnings, _ = hood.findings()
        self.assertEqual([w.code for w in warnings], ["neighbour-collision"])
        self.assertIn("avoid/their-bell", warnings[0])
        self.assertIn("distance 0.00", warnings[0])
        self.assertIsInstance(warnings[0], Finding)

    def test_a_promoted_bundled_entry_is_gated_once_not_also_advised(self):
        promoted = [neighbours.Entry(
            id=self.bell.id, set="avoid", title=self.bell.title, source=self.bell.source,
            source_sha256=self.bell.source_sha256, field=self.bell.field,
        )]
        hood = neighbours.neighbourhood(self._candidate(self.bell), index=self.index, avoid=promoted)
        warnings, advisories = hood.findings()
        self.assertEqual([w.code for w in warnings], ["neighbour-collision"])
        self.assertFalse(any("collision/bell" in a for a in advisories))
        self.assertNotIn("collision/bell", [n.entry.id for n in hood.familiar])

    def test_a_declared_family_is_excluded_from_the_gate_entirely(self):
        twin = _entry("avoid/twin", self.bell.field, set_name="avoid", sha="b" * 64)
        family = [_entry("family/twin", self.bell.field, set_name="family", sha="b" * 64)]
        hood = neighbours.neighbourhood(
            self._candidate(self.bell), index=self.index, avoid=[twin], family=family,
        )
        warnings, advisories = hood.findings()
        self.assertEqual(warnings, [])
        # The family names the twin, not the bundled bell, so the bell still advises.
        self.assertEqual({a.code for a in advisories}, {"neighbour-familiar"})
        self.assertEqual([n.entry.id for n in hood.family], ["family/twin"])
        self.assertNotIn("avoid/twin", [n.entry.id for n in hood.nearest])

    def test_a_byte_identical_avoid_file_under_another_name_still_gates(self):
        """Self-exclusion is by file, not by hash: a copy of the mark is a collision."""
        me = neighbours.Entry(
            id="candidate", set="candidate", title="me", source=str(REPO / "a" / "master.svg"),
            source_sha256=self.bell.source_sha256, field=self.bell.field,
        )
        copy = neighbours.Entry(
            id="avoid/their-copy", set="avoid", title="copy", source=str(REPO / "b" / "master.svg"),
            source_sha256=self.bell.source_sha256, field=self.bell.field,
        )
        same_file = neighbours.Entry(
            id="avoid/a", set="avoid", title="a", source=str(REPO / "a" / "master.svg"),
            source_sha256=self.bell.source_sha256, field=self.bell.field,
        )
        hood = neighbours.neighbourhood(me, index=self.index, avoid=[copy, same_file])
        self.assertEqual([n.entry.id for n in hood.collisions], ["avoid/their-copy"])

    def test_a_bundled_form_promoted_by_file_path_is_gated_once(self):
        by_path = neighbours.Entry(
            id="avoid/bell", set="avoid", title="Bell", source=str(COLLISION / "bell.svg"),
            source_sha256=self.bell.source_sha256, field=self.bell.field,
        )
        hood = neighbours.neighbourhood(self._candidate(self.bell), index=self.index, avoid=[by_path])
        warnings, advisories = hood.findings()
        self.assertEqual([w.code for w in warnings], ["neighbour-collision"])
        self.assertNotIn("collision/bell", [n.entry.id for n in hood.familiar])

    def test_the_same_portfolio_file_declared_three_times_is_not_a_rut(self):
        index = self.index
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "shipped" / "one"
            src.mkdir(parents=True)
            (src / "master.svg").write_bytes((COLLISION / "bell.svg").read_bytes())
            resolved = neighbours.resolve_set(
                [str(src / "master.svg"), "shipped/*/master.svg", "shipped/one/master.svg"],
                set_name="portfolio", base=Path(tmp), index=index,
                rasterizer=_FakeRasterizer(),
            )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].id, "portfolio/one")

    def test_declared_master_svg_files_get_distinct_ids_from_their_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("suite-a", "suite-b"):
                (Path(tmp) / name).mkdir()
                (Path(tmp) / name / "master.svg").write_bytes((COLLISION / "bell.svg").read_bytes())
            resolved = neighbours.resolve_set(
                ["*/master.svg"], set_name="family", base=Path(tmp),
                index=self.index, rasterizer=_FakeRasterizer(),
            )
        self.assertEqual([e.id for e in resolved], ["family/suite-a", "family/suite-b"])
        self.assertEqual({e.title for e in resolved}, {"Bell"})

    def test_the_candidate_itself_is_never_its_own_neighbour(self):
        me = neighbours.Entry(
            id="candidate", set="candidate", title="me", source="x.svg",
            source_sha256=self.bell.source_sha256, field=self.bell.field,
        )
        hood = neighbours.neighbourhood(me, index=self.index)
        self.assertNotIn("collision/bell", [n.entry.id for n in hood.nearest])
        self.assertNotIn("collision/bell", [n.entry.id for n in hood.familiar])
        self.assertEqual(hood.findings()[0], [])

    def test_three_portfolio_marks_inside_the_radius_are_a_rut(self):
        own = [_entry(f"portfolio/mark-{i}", self.bell.field, set_name="portfolio", sha=str(i) * 64)
               for i in range(3)]
        hood = neighbours.neighbourhood(self._candidate(self.bell), index=self.index, portfolio=own)
        codes = [a.code for a in hood.findings()[1]]
        self.assertIn("neighbour-house-rut", codes)
        two = neighbours.neighbourhood(self._candidate(self.bell), index=self.index, portfolio=own[:2])
        self.assertNotIn("neighbour-house-rut", [a.code for a in two.findings()[1]])

    def test_different_topology_keeps_a_close_pair_outside_the_radius(self):
        disc = shapefield.field_from_mask(_mask(lambda d: d.ellipse([8, 8, 55, 55], fill=255)))
        ring = shapefield.field_from_mask(_mask(
            lambda d: (d.ellipse([8, 8, 55, 55], fill=255), d.ellipse([28, 28, 35, 35], fill=0))
        ))
        candidate = _entry("candidate/disc", disc, set_name="candidate", sha="c" * 64)
        avoid = [_entry("avoid/ring", ring, set_name="avoid", sha="d" * 64)]
        hood = neighbours.neighbourhood(candidate, index=None, avoid=avoid)
        self.assertLess(hood.nearest[0].distance, hood.radius)
        self.assertFalse(hood.nearest[0].within(hood.radius))
        self.assertEqual(hood.findings(), ([], []))

    def test_nearest_lists_every_hit_inside_the_radius_even_past_k(self):
        twins = [_entry(f"avoid/twin-{i}", self.bell.field, set_name="avoid", sha=str(i) * 64)
                 for i in range(3)]
        hood = neighbours.neighbourhood(
            self._candidate(self.bell), index=None, avoid=twins, nearest=1,
        )
        self.assertEqual(len(hood.nearest), 3)
        self.assertTrue(all(n.within(hood.radius) for n in hood.nearest))
        far = neighbours.neighbourhood(self._candidate(self.gear), index=self.index, nearest=1)
        # Past k, only hits inside the radius may appear.
        self.assertTrue(all(n.within(far.radius) for n in far.nearest[1:]))

    def test_the_envelope_shape_is_stable(self):
        hood = neighbours.neighbourhood(self._candidate(self.gear), index=self.index)
        data = hood.as_dict()
        self.assertEqual(
            list(data), ["radius", "field", "nearest", "collisions", "familiar", "rut", "family"],
        )
        self.assertEqual(list(data["field"]), ["components", "holes", "coverage", "aspect"])
        self.assertEqual(
            list(data["nearest"][0]),
            ["id", "set", "title", "source", "distance", "same_topology", "components", "holes"],
        )

    def test_a_non_positive_or_non_finite_radius_is_refused(self):
        for radius in (0, -1, float("nan"), float("inf")):
            with self.subTest(radius=radius):
                with self.assertRaises(neighbours.NeighbourError):
                    neighbours.neighbourhood(self._candidate(self.bell), index=self.index,
                                             radius=radius)


class ConfigTests(unittest.TestCase):
    def test_a_project_that_declares_nothing_is_untouched(self):
        from iconflow.config import load_config

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "iconflow.toml"
            path.write_text('schema_version = 1\n[project]\nname = "Plain"\n', encoding="utf-8")
            config = load_config(path)
        self.assertFalse(config.neighbours_declared)
        self.assertEqual(config.neighbours_avoid, [])

    def test_an_empty_table_is_the_opt_in_and_a_round_trip_preserves_it_either_way(self):
        from iconflow.config import IconFlowConfig, config_text, load_config

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "iconflow.toml"
            path.write_text('schema_version = 1\n[neighbours]\n', encoding="utf-8")
            self.assertTrue(load_config(path).neighbours_declared)
            # A project that declared nothing stays undeclared after load -> write -> load.
            plain = Path(tmp) / "plain.toml"
            plain.write_text('schema_version = 1\n[project]\nname = "Old"\n', encoding="utf-8")
            plain.write_text(config_text(load_config(plain)), encoding="utf-8")
            self.assertFalse(load_config(plain).neighbours_declared)
            self.assertNotIn("[neighbours]", plain.read_text(encoding="utf-8"))
            # ...and a declared one keeps its table.
            path.write_text(config_text(IconFlowConfig(source=path, neighbours_declared=True)),
                            encoding="utf-8")
            fresh = load_config(path)
        self.assertTrue(fresh.neighbours_declared)
        self.assertEqual(fresh.neighbours_avoid, [])

    def test_init_writes_the_table_so_a_new_project_gets_the_advisories(self):
        import contextlib

        from iconflow.cli import main
        from iconflow.config import load_config

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "iconflow.toml"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["init", "--out", str(path), "--name", "Fresh"])
            self.assertEqual(code, 0)
            config = load_config(path)
        self.assertTrue(config.neighbours_declared)
        self.assertEqual(config.neighbours_avoid, [])

    def test_the_example_declares_the_collision_set_as_its_avoid_set(self):
        from iconflow.config import load_config

        config = load_config(EXAMPLE / "iconflow.toml")
        self.assertEqual(config.neighbours_avoid, ["@collision"])

    def test_a_glob_with_a_fixed_directory_after_the_wildcard_resolves(self):
        index = neighbours.parse_index(INDEX.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("alpha", "beta"):
                (root / name / "assets").mkdir(parents=True)
                (root / name / "assets" / "master.svg").write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"/>', encoding="utf-8",
                )
            found = neighbours._expand_spec("*/assets/master.svg", root)
            self.assertEqual([p.parent.parent.name for p in found], ["alpha", "beta"])
            with self.assertRaises(neighbours.NeighbourError):
                neighbours._expand_spec("nothing/*.svg", root)
            with self.assertRaises(neighbours.NeighbourError):
                neighbours.resolve_set(["nothing/*.svg"], set_name="avoid", base=root,
                                       index=index, rasterizer=None)

    def test_bundled_aliases_resolve_without_rendering(self):
        index = neighbours.parse_index(INDEX.read_text(encoding="utf-8"))
        whole = neighbours.resolve_set(["@collision"], set_name="avoid", base=REPO, index=index,
                                       rasterizer=None)
        self.assertEqual(len(whole), len(index.by_set("collision")))
        self.assertTrue(all(e.set == "avoid" for e in whole))
        one = neighbours.resolve_set(["@collision/bell"], set_name="family", base=REPO, index=index,
                                     rasterizer=None)
        self.assertEqual([e.id for e in one], ["collision/bell"])
        # Overlapping aliases name one mark once.
        twice = neighbours.resolve_set(["@collision", "@collision/bell"], set_name="avoid",
                                       base=REPO, index=index, rasterizer=None)
        self.assertEqual(len(twice), len(whole))
        with self.assertRaises(neighbours.NeighbourError):
            neighbours.resolve_set(["@collision/no-such-form"], set_name="avoid", base=REPO,
                                   index=index, rasterizer=None)
        with self.assertRaises(neighbours.NeighbourError):
            neighbours.resolve_set(["missing.svg"], set_name="avoid", base=REPO, index=index,
                                   rasterizer=None)


@NEEDS_CHROMIUM
class RenderedNeighbourhood(unittest.TestCase):
    """Chromium is the ground truth; prove the claims the docs make on real marks."""

    @classmethod
    def setUpClass(cls):
        from iconflow.rasterize import Rasterizer, load_svg

        cls.index = neighbours.parse_index(INDEX.read_text(encoding="utf-8"))
        cls.fields = {}
        with Rasterizer() as rasterizer:
            for path in sorted(FIXTURES.glob("*.svg")):
                cls.fields[path.stem] = shapefield.field_from_svg(load_svg(path), rasterizer)

    def _distance(self, fixture: str, form: str) -> shapefield.Separation:
        return shapefield.separation(self.fields[fixture], self.index.get(f"collision/{form}").field)

    def test_the_metric_separates_three_collisions_the_casebook_recorded(self):
        """docs/NEIGHBOURHOOD.md's calibration table, asserted."""
        for fixture, form in (
            ("interlace-frame", "hashtag"),      # cineloom: a 2x2 weave was a hashtag
            ("rising-blocks", "bar-chart"),      # lumendeck: rising panels were a bar chart
            ("monogram-h", "letter-h"),          # media-hub: a bold H on a tile is the letter H
        ):
            with self.subTest(pair=(fixture, form)):
                sep = self._distance(fixture, form)
                self.assertLessEqual(sep.distance, neighbours.COLLISION_RADIUS)
                self.assertTrue(sep.same_topology)

    def test_the_recorded_misses_are_misses_and_the_docs_say_so(self):
        """The three collisions the radius does not catch — pinned, not hidden."""
        for fixture, form, why in (
            ("stepped-stack", "bar-chart", "different topology"),
            ("lantern-ribs", "bell", "different topology"),
            ("curtain-two-panels", "pi", "mass"),
        ):
            with self.subTest(pair=(fixture, form)):
                sep = self._distance(fixture, form)
                self.assertFalse(
                    sep.distance <= neighbours.COLLISION_RADIUS and sep.same_topology,
                )
                if why == "different topology":
                    self.assertFalse(sep.same_topology)
                else:
                    self.assertGreater(sep.distance, neighbours.COLLISION_RADIUS)

    def test_the_redesigns_that_shipped_sit_outside_the_radius(self):
        for fixture, form in (
            ("pattern-card", "hashtag"),
            ("pattern-card", "filmstrip"),
            ("two-panels-rail", "bar-chart"),
            ("curtain-forked", "pi"),
        ):
            with self.subTest(pair=(fixture, form)):
                self.assertGreater(
                    self._distance(fixture, form).distance, neighbours.COLLISION_RADIUS * 1.5,
                )

    def test_the_index_rebuilds_from_source_within_one_pixel_per_cell(self):
        """Cross-platform reproducibility: the drift test scripts/… --check runs."""
        from iconflow.rasterize import Rasterizer

        sys.path.insert(0, str(REPO / "scripts"))
        try:
            import build_collision_index as generator
        finally:
            sys.path.pop(0)
        with Rasterizer() as rasterizer:
            fresh = generator.build(rasterizer)
        self.assertEqual(generator.check_fields(self.index, fresh), [])
        self.assertEqual({e.id for e in fresh}, {e.id for e in self.index.entries})

    def test_check_gates_the_example_first_draft_and_passes_its_master(self):
        import contextlib

        from iconflow.cli import main

        codes = {}
        for name in ("first-draft", "master"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = main(["check", str(EXAMPLE / f"{name}.svg"),
                             "--config", str(EXAMPLE / "iconflow.toml"), "--json"])
            codes[name] = (code, [w["code"] for w in json.loads(out.getvalue())["warnings"]])
        self.assertEqual(codes["first-draft"], (1, ["neighbour-collision"]))
        self.assertEqual(codes["master"], (0, []))

    def test_check_without_a_config_and_a_config_without_the_table_are_unaffected(self):
        """Bit-for-bit: the envelope of a project declaring nothing does not change."""
        import contextlib

        from iconflow.cli import main

        plain = EXAMPLE / "first-draft.svg"
        with tempfile.TemporaryDirectory() as tmp:
            toml = Path(tmp) / "iconflow.toml"
            toml.write_text(
                'schema_version = 1\n[project]\nname = "Plain"\nmaster = "'
                + plain.as_posix() + '"\n', encoding="utf-8",
            )
            envelopes = []
            for argv in (
                ["check", str(plain), "--json"],
                ["check", str(plain), "--config", str(toml), "--json"],
            ):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    code = main(argv)
                self.assertEqual(code, 0)
                envelopes.append(json.loads(out.getvalue()))
        self.assertEqual(envelopes[0], envelopes[1])
        self.assertEqual(envelopes[0]["advisories"], [])
        self.assertEqual(envelopes[0]["warnings"], [])

    def test_neighbours_json_names_the_collision_and_writes_the_sheet(self):
        import contextlib

        from iconflow.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "neighbours.png"
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = main([
                    "neighbours", str(EXAMPLE / "first-draft.svg"),
                    "--config", str(EXAMPLE / "iconflow.toml"),
                    "--sheet", str(sheet), "--json",
                ])
            envelope = json.loads(out.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(envelope["status"], "blocked")
            self.assertEqual([w["code"] for w in envelope["warnings"]], ["neighbour-collision"])
            self.assertIn("collision/bar-chart", envelope["outputs"]["collisions"])
            self.assertEqual(envelope["outputs"]["radius"], neighbours.COLLISION_RADIUS)
            self.assertTrue(sheet.is_file())
            with Image.open(sheet) as image:
                self.assertGreater(image.width, 600)

    def test_a_family_member_is_drawn_but_never_gated(self):
        import contextlib

        from iconflow.cli import main

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = main([
                "neighbours", str(EXAMPLE / "first-draft.svg"),
                "--avoid", str(COLLISION / "bar-chart.svg"),
                "--family", str(COLLISION / "bar-chart.svg"),
                "--json",
            ])
        envelope = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual([f["id"] for f in envelope["outputs"]["family"]], ["family/bar-chart"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
