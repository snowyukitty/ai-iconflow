# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The Family tier (iconflow/family.py) and the emote set it holds together.

The arithmetic runs on synthetic fields, so it needs no browser. The tests that
render — the shipped emotes form one carrier group with no twins, and every
member passes `check` — opt in with ``ICONFLOW_BROWSER_TESTS=1`` and run in
the ``chromium-integration`` job.
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from iconflow import family, neighbours, shapefield

ROOT = Path(__file__).resolve().parents[1]
EMOTES = ROOT / "emotes"
NEEDS_CHROMIUM = unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
N = shapefield.GRID


def field(cells: set[tuple[int, int]], components: int = 1, holes: int = 0) -> shapefield.ShapeField:
    grid = tuple(1.0 if (x, y) in cells else 0.0 for y in range(N) for x in range(N))
    return shapefield.ShapeField(grid=grid, components=components, holes=holes, coverage=len(cells) / N / N, aspect=1.0)


def entry(name: str, f: shapefield.ShapeField) -> neighbours.Entry:
    return neighbours.Entry(id=f"family/{name}", set="family", title=name, source=f"{name}.svg",
                            source_sha256="0" * 64, field=f)


# A 12x12 "head" with features punched into it, the way a face on a card is
# fingerprinted: the carrier is ink, the expression is where ink is missing.
HEAD = {(x, y) for x in range(2, 14) for y in range(2, 14)}


def face(*holes: tuple[int, int]) -> shapefield.ShapeField:
    return field(HEAD - set(holes))


class ResidualArithmetic(unittest.TestCase):
    def test_identical_members_are_zero_and_disjoint_differences_are_one(self) -> None:
        carrier = face().grid
        a = face((4, 5), (9, 5))
        self.assertEqual(0.0, family.residual_distance(a, a, carrier))
        b = face((6, 10), (7, 10))
        self.assertAlmostEqual(1.0, family.residual_distance(a, b, carrier))

    def test_residual_is_bounded_by_the_triangle_inequality(self) -> None:
        carrier = face().grid
        a = face((4, 5), (9, 5), (6, 10))
        b = face((4, 5), (9, 6), (7, 10))
        value = family.residual_distance(a, b, carrier)
        self.assertGreater(value, 0.0)
        self.assertLessEqual(value, 1.0)

    def test_siblings_on_one_carrier_are_compared_on_what_they_do_not_share(self) -> None:
        # Raw distance is tiny because the head is most of the ink...
        smile = face((4, 5), (9, 5), (5, 10), (6, 11), (7, 11), (8, 11), (9, 10))
        wink = face((4, 5), (5, 10), (6, 11), (7, 11), (8, 11), (9, 10))   # one eye fewer
        shock = face((4, 4), (9, 4), (6, 9), (7, 9), (6, 10), (7, 10))
        sleepy = face((3, 6), (4, 6), (9, 6), (10, 6), (7, 11))
        members = [entry(n, f) for n, f in (("smile", smile), ("wink", wink), ("shock", shock), ("sleepy", sleepy))]
        self.assertLess(shapefield.grid_distance(smile.grid, wink.grid), 0.05)
        result = family.assess(members)
        # ...so they form one carrier group, and the near-twin is caught on
        # its residual while the genuinely different faces are not.
        self.assertEqual(1, len(result.groups))
        twins = {frozenset((p.a.title, p.b.title)) for p in result.twins}
        self.assertEqual({frozenset(("smile", "wink"))}, twins)
        self.assertEqual("family-twins", result.findings()[0].code)

    def test_members_with_nothing_in_common_stand_alone(self) -> None:
        heart = field({(x, y) for x in range(3, 13) for y in range(3, 9)})
        thumb = field({(x, y) for x in range(5, 8) for y in range(1, 15)})
        result = family.assess([entry("heart", heart), entry("thumb", thumb)])
        self.assertEqual(2, len(result.groups))
        self.assertEqual({"heart", "thumb"}, {m.title for m in result.loners})
        self.assertEqual([], result.pairs)
        self.assertEqual([], result.twins)

    def test_a_pair_group_falls_back_to_the_neighbourhood_radius(self) -> None:
        # Two members alone in a group have no carrier: residual is undefined,
        # so the pair is judged on its raw distance and topology.
        a = field({(x, y) for x in range(2, 14) for y in range(2, 14)})
        b = field({(x, y) for x in range(2, 14) for y in range(2, 13)})
        result = family.assess([entry("a", a), entry("b", b)])
        (pair,) = result.pairs
        self.assertIsNone(pair.residual)
        self.assertTrue(pair.twin)
        self.assertIn("radius", result.findings()[0])

    def test_one_member_is_not_a_family(self) -> None:
        with self.assertRaises(family.FamilyError):
            family.assess([entry("solo", face())])

    def test_the_envelope_names_groups_pairs_and_twins(self) -> None:
        result = family.assess([entry(n, face((4, i), (9, i))) for n, i in (("a", 4), ("b", 6), ("c", 9))])
        payload = result.as_dict()
        self.assertEqual({"coherence", "twin_floor", "members", "groups", "nearest", "twins"}, set(payload))
        self.assertNotIn("grid", payload["members"][0]["field"])
        json.dumps(payload)


class EmoteSet(unittest.TestCase):
    """The shipped set: catalogued, public domain, titled, one grammar."""

    def test_catalog_lists_exactly_the_shipped_sources(self) -> None:
        catalog = json.loads((EMOTES / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual("CC0-1.0", catalog["license"])
        slugs = [e["slug"] for e in catalog["emotes"]]
        self.assertGreaterEqual(len(slugs), 50)
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(sorted(slugs), sorted(p.stem for p in EMOTES.glob("*.svg")))
        self.assertEqual({"face", "hand", "symbol"}, {e["kind"] for e in catalog["emotes"]})
        # Grouped on the page: every face, then every hand, then every symbol.
        kinds = [e["kind"] for e in catalog["emotes"]]
        self.assertEqual(kinds, sorted(kinds, key=["face", "hand", "symbol"].index))
        for item in catalog["emotes"]:
            with self.subTest(slug=item["slug"]):
                self.assertTrue((ROOT / item["source"]).is_file())
                self.assertRegex(item["meaning"], r"^U\+[0-9A-F]{4,5}$")

    def test_every_emote_is_public_domain_titled_and_on_the_1024_grid(self) -> None:
        for path in sorted(EMOTES.glob("*.svg")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(emote=path.stem):
                self.assertTrue(text.startswith("<!-- SPDX-License-Identifier: CC0-1.0"))
                self.assertIn('viewBox="0 0 1024 1024"', text)
                self.assertRegex(text, r"<title>[^<]+</title>")
                self.assertNotIn("<text", text)       # no font-dependent glyphs
                self.assertNotIn("<image", text)      # nothing raster or external

    def test_faces_share_the_card_carrier_and_the_grammar_weights(self) -> None:
        # The one face drawn without the card: its joke is the card itself
        # melting, so it keeps the card's top corners and lets the rest run.
        melted = {"melting"}
        catalog = json.loads((EMOTES / "catalog.json").read_text(encoding="utf-8"))
        for item in catalog["emotes"]:
            text = (ROOT / item["source"]).read_text(encoding="utf-8")
            with self.subTest(slug=item["slug"]):
                if item["kind"] == "face" and item["slug"] not in melted:
                    self.assertIn('x="96" y="104" width="832" height="832" rx="300"', text)
                self.assertRegex(text, r'stroke="#191a20" stroke-width="52"')


@NEEDS_CHROMIUM
class EmoteFamilyRendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from iconflow.rasterize import Rasterizer

        cls.rasterizer = Rasterizer().__enter__()
        cls.paths = sorted(EMOTES.glob("*.svg"))
        cls.result = family.audit(cls.paths, rasterizer=cls.rasterizer)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.rasterizer.__exit__(None, None, None)

    def test_the_faces_share_one_carrier_group_and_no_two_members_are_twins(self) -> None:
        catalog = json.loads((EMOTES / "catalog.json").read_text(encoding="utf-8"))
        faces = {e["slug"] for e in catalog["emotes"] if e["kind"] == "face"}
        largest = {Path(m.source).stem for m in self.result.groups[0]}
        # Every face is on the card. A symbol drawn on the same card (the
        # check mark) may join them; that is the carrier being found, not noise.
        self.assertLessEqual(faces, largest)
        self.assertEqual([], [(p.a.title, p.b.title) for p in self.result.twins])

    def test_every_member_passes_check(self) -> None:
        from iconflow import qa

        for path in self.paths:
            with self.subTest(emote=path.stem):
                self.assertEqual([], [str(f) for f in qa.check(path, rasterizer=self.rasterizer)])

    def test_the_sheet_draws_the_closest_pairs(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as scratch:
            out = family.family_sheet(self.result, Path(scratch) / "family.png", rasterizer=self.rasterizer)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
