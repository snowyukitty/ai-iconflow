import tempfile
import unittest
from pathlib import Path

from iconflow.casebook import (
    AXES, DISTILL_THRESHOLD, atlas_html, format_stats, lint_case, load_casebook,
    new_case, parse_case, parse_scores, stats, write_atlas,
)


def _make_case(directory, slug, device="letterform fusion", first=None,
               final=None, lessons=None, iterations=2, date="2026-01-01"):
    return new_case(
        directory, slug, essence="save", style_family="flat-geometric",
        signature_device=device,
        scores_first=first or {"legibility": 3, "distinctiveness": 4},
        scores_final=final or {"legibility": 4, "distinctiveness": 5},
        lessons=lessons or [], iterations=iterations, date=date,
    )


class CasebookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_parse_scores_accepts_space_and_comma(self):
        self.assertEqual(parse_scores("legibility = 3, craft=5 color = 4"),
                         {"legibility": 3, "craft": 5, "color": 4})

    def test_parse_scores_rejects_typos_duplicates_and_out_of_range(self):
        for raw in ("legibility=4 typo", "legibility=4 legibility=5", "craft=6"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_scores(raw)

    def test_new_case_roundtrips_through_parse(self):
        path = _make_case(self.dir, "My App!", lessons=["thin strokes die at 16px"])
        self.assertEqual(path.name, "2026-01-01-my-app.md")
        case = parse_case(path)
        self.assertEqual(case.essence, "save")
        self.assertEqual(case.signature_device, "letterform fusion")
        self.assertEqual(case.scores_first["legibility"], 3)
        self.assertEqual(case.scores_final["distinctiveness"], 5)
        self.assertEqual(case.iterations, 2)
        self.assertEqual(case.undistilled, ["thin strokes die at 16px"])
        self.assertEqual(case.device_family, "")
        self.assertEqual(case.device_detail, "letterform fusion")
        self.assertEqual(case.status, "shipped")

    def test_new_case_rejects_unknown_axis_and_duplicates(self):
        with self.assertRaises(ValueError):
            _make_case(self.dir, "bad", first={"nope": 3})
        _make_case(self.dir, "dupe")
        with self.assertRaises(ValueError):
            _make_case(self.dir, "dupe")

    def test_new_case_rejects_noncanonical_or_traversing_date(self):
        for date in ("2026-1-01", "../2026-01-01", "2026-02-30"):
            with self.subTest(date=date), self.assertRaises(ValueError):
                _make_case(self.dir, "bad-date", date=date)

    def test_new_taxonomy_roundtrips_normalized(self):
        path = new_case(
            self.dir, "taxonomy", date="2026-01-02",
            device_family="Negative Space", device_detail="  Offset   proof gate ",
            concept_lens="User Journey", status="approved",
        )
        case = parse_case(path)
        self.assertEqual(case.device_family, "negative-space")
        self.assertEqual(case.device_detail, "Offset proof gate")
        self.assertEqual(case.concept_lens, "user-journey")
        self.assertEqual(case.status, "approved")
        self.assertFalse([issue for issue in lint_case(path) if issue.severity == "error"])

    def test_distilled_checkbox_is_not_counted_as_undistilled(self):
        path = _make_case(self.dir, "app", lessons=["rule one"])
        text = path.read_text(encoding="utf-8").replace("- [ ] rule one", "- [x] rule one")
        path.write_text(text, encoding="utf-8")
        case = parse_case(path)
        self.assertEqual(case.undistilled, [])
        self.assertEqual(case.lessons, [(True, "rule one")])

    def test_stats_flags_weakest_axis_and_distill_threshold(self):
        for i in range(DISTILL_THRESHOLD):
            _make_case(self.dir, f"app-{i}", lessons=[f"lesson {i}"],
                       first={"legibility": 4, "scalability": 2})
        s = stats(load_casebook(self.dir))
        self.assertEqual(s["cases"], DISTILL_THRESHOLD)
        self.assertEqual(s["weakest_axis"], "scalability")
        self.assertEqual(len(s["undistilled"]), DISTILL_THRESHOLD)
        report = "\n".join(format_stats(s))
        self.assertIn("DISTILL NOW", report)
        self.assertIn("EVOLUTION TARGET", report)
        self.assertIn("n=3", report)

    def test_stats_reports_tied_weakest_axes_and_normalized_families(self):
        complete = {axis: 4 for axis in AXES}
        complete["legibility"] = complete["craft"] = 2
        new_case(
            self.dir, "tied", date="2026-01-02", style_family="Flat Geometric",
            device_family="Proof Gate", concept_lens="Workflow",
            scores_first=complete, scores_final={axis: 4 for axis in AXES},
        )
        aggregate = stats(load_casebook(self.dir))
        self.assertEqual(aggregate["weakest_axes"], ["legibility", "craft"])
        report = "\n".join(format_stats(aggregate))
        self.assertIn("tied as the weakest", report)
        self.assertIn("device families: proof-gate x1", report)
        self.assertIn("style families: flat-geometric x1", report)

    def test_stats_warns_on_house_cliche(self):
        for i in range(4):
            _make_case(self.dir, f"app-{i}", device="letterform fusion")
        report = "\n".join(format_stats(stats(load_casebook(self.dir))))
        self.assertIn("HOUSE-CLICHE WARNING", report)

    def test_stats_no_house_cliche_when_devices_vary(self):
        devices = ["negative space", "ownable geometry", "letterform fusion", "single accent"]
        for i, device in enumerate(devices):
            _make_case(self.dir, f"app-{i}", device=device)
        report = "\n".join(format_stats(stats(load_casebook(self.dir))))
        self.assertNotIn("HOUSE-CLICHE WARNING", report)

    def test_readme_is_ignored_by_loader(self):
        (self.dir / "README.md").write_text("# not a case", encoding="utf-8")
        _make_case(self.dir, "app")
        self.assertEqual(len(load_casebook(self.dir)), 1)

    def test_empty_casebook_stats(self):
        report = "\n".join(format_stats(stats(load_casebook(self.dir))))
        self.assertIn("0 case(s)", report)
        self.assertIn("iconflow case new", report)

    def test_atlas_empty_casebook_is_self_contained_and_writes_parent(self):
        destination = self.dir / "reports" / "atlas.html"
        result = write_atlas(self.dir, destination)
        self.assertEqual(result, destination.resolve())
        document = destination.read_text(encoding="utf-8")
        self.assertIn("No cases yet", document)
        self.assertIn("0 case(s)", document)
        self.assertIn("<style>", document)
        self.assertNotIn("https://", document)
        self.assertNotIn("http://", document)

    def test_atlas_escapes_user_data_and_shows_scores_taxonomy_and_lessons(self):
        first = {axis: 3 for axis in AXES}
        final = {axis: 4 for axis in AXES}
        path = new_case(
            self.dir, "hostile", date="2026-01-03",
            project='<script>alert("project")</script>', essence="proof & flow",
            targets='web,<img src=x onerror="bad">',
            device_family="Proof Gate", device_detail="rail < gate",
            concept_lens="User Journey", status="shipped",
            cliche_avoided="sparkles & robots", scores_first=first,
            scores_final=final, lessons=['never trust <script>alert("lesson")</script>'],
        )
        case = parse_case(path)
        document = atlas_html([case], title="Atlas <proof>")
        self.assertIn("Atlas &lt;proof&gt;", document)
        self.assertIn("&lt;script&gt;alert(&quot;project&quot;)&lt;/script&gt;", document)
        self.assertIn("never trust &lt;script&gt;", document)
        self.assertNotIn("<script", document.lower())
        self.assertNotIn("<img", document.lower())
        self.assertNotIn("onerror=\"bad\"", document)
        self.assertIn("proof &amp; flow", document)
        self.assertIn("Six-axis movement", document)
        self.assertIn("Device families", document)
        self.assertIn("proof-gate", document)
        self.assertIn("user-journey", document)
        self.assertIn("delta-up", document)
        self.assertIn("Undistilled lessons", document)


if __name__ == "__main__":
    unittest.main()
