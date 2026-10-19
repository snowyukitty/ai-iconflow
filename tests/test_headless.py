# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Headless review (iconflow/headless.py): evidence, axis walk, receipt.

The gate must not move: a headless receipt is bound to the same source and
contract hashes, needs every axis at 4/5 or better to be ready, and a second
opinion is recorded and compared but never substitutes for the gate.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from iconflow import headless
from iconflow.casebook import AXES
from iconflow.cli import DEMO_FILES, _resource, main
from iconflow.config import load_config, load_review_receipt

RATIONALE = [f"--rationale={axis}=read the {axis} strip on the sheet" for axis in AXES]
PASSING = "legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4"


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue()


def headless_budget():
    from iconflow.budget import Budget

    return Budget(source="master.svg", ground="transparent", cuts_256=1, cuts_16=1,
                  parts_256=1, parts_16=1)


def write_png(path, *_args, **_kwargs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (40, 40, 40)).save(path)
    return path


def stub_plan():
    """A tiny real RenderPlan, so ship's plan seam can be stubbed without Chromium."""
    from iconflow.plan import RenderPlan

    return RenderPlan.create({"favicon.svg": b"<svg/>"}, inputs={}, parameters={}, toolchain={})


class HeadlessFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "family"
        self.dir.mkdir()
        for name in DEMO_FILES:
            (self.dir / name).write_bytes(_resource("demo", name).read_bytes())
        self.config = self.dir / "iconflow.toml"
        self.evidence = self.dir / "evidence"
        for target, value in (
            ("iconflow.qa.tray_template_warnings", []),
            ("iconflow.budget.budget_svg", headless_budget()),
        ):
            patcher = mock.patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def render_evidence(self):
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch("iconflow.qa.tray_template_warnings", return_value=[]), \
             mock.patch("iconflow.plan.compute_plan", return_value=stub_plan()), \
             mock.patch("iconflow.review.contact_sheet",
                        side_effect=lambda master, out, **kw: write_png(out)), \
             mock.patch("iconflow.headless.target_sheet",
                        side_effect=lambda master, out, **kw: write_png(out)):
            return run(["review", "--config", str(self.config), "--evidence", str(self.evidence)])

    def score(self, *extra, scores=PASSING, name="agent-a", out="receipt.json"):
        return run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", scores, *RATIONALE, "--notes", "weakest: legibility; kept the cut",
            "--reviewer-name", name, "--out", str(self.dir / out), *extra,
        ])

    def test_evidence_then_score_then_ship(self):
        code, envelope, _ = self.render_evidence()
        self.assertEqual(code, 0, envelope)
        findings = json.loads((self.evidence / "findings.json").read_text(encoding="utf-8"))
        self.assertFalse(findings["interactive_lab"])
        self.assertEqual({"contact_sheet", "targets"}, set(findings["evidence"]))
        self.assertEqual([axis["axis"] for axis in findings["axes"]], list(AXES))
        # Envelope paths are absolute but unresolved (links are refused, not
        # followed), so compare canonical forms: 8.3 names, /private on macOS.
        self.assertEqual(os.path.realpath(envelope["outputs"]["findings"]),
                         os.path.realpath(self.evidence / "findings.json"))

        code, envelope, err = self.score()
        self.assertEqual(code, 0, envelope)
        self.assertIn("interactive Review Lab is not used", err)
        receipt = json.loads((self.dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "ready")
        self.assertIs(receipt["review_surface"]["interactive_lab"], False)
        self.assertEqual(set(receipt["rationale"]), set(AXES))
        self.assertEqual(receipt["reviewer"]["name"], "agent-a")

        loaded = load_review_receipt(self.dir / "receipt.json", load_config(self.config))
        self.assertEqual(loaded.review_surface["kind"], headless.SURFACE_KIND)

        build = __import__("importlib").import_module("iconflow.build")
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch("iconflow.plan.compute_plan", return_value=stub_plan()), \
             mock.patch("iconflow.plan.write_plan", return_value=[]):
            code, envelope, err = run([
                "ship", "--config", str(self.config), "--review", str(self.dir / "receipt.json"),
            ])
        self.assertEqual(code, 0, envelope)
        self.assertIn("Review Lab was not used", err)
        self.assertFalse(envelope["outputs"]["review_surface"]["interactive_lab"])

    def test_a_score_below_four_writes_a_blocked_receipt_ship_refuses(self):
        self.render_evidence()
        code, envelope, _ = self.score(scores=PASSING.replace("craft=4", "craft=3"))
        self.assertEqual(code, 1)
        self.assertEqual(envelope["warnings"][0]["code"], "score-below-floor")
        receipt = json.loads((self.dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "blocked")
        with self.assertRaises(Exception):
            load_review_receipt(self.dir / "receipt.json", load_config(self.config))

    def test_every_axis_needs_a_reason(self):
        self.render_evidence()
        code, envelope, _ = run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", PASSING, *RATIONALE[:-1], "--notes", "n",
            "--reviewer-name", "a", "--out", str(self.dir / "r.json"),
        ])
        self.assertEqual(code, 2)
        self.assertIn("craft", envelope["errors"][0]["message"])

    def test_stale_or_tampered_evidence_is_refused(self):
        self.render_evidence()
        sheet = self.evidence / "targets.png"
        sheet.write_bytes(sheet.read_bytes() + b"x")
        code, envelope, _ = self.score()
        self.assertEqual(code, 2)
        self.assertIn("changed after it was rendered", envelope["errors"][0]["message"])

        self.render_evidence()
        master = self.dir / "master.svg"
        master.write_text(master.read_text(encoding="utf-8") + "<!-- edit -->", encoding="utf-8")
        code, envelope, _ = self.score()
        self.assertEqual(code, 2)
        self.assertIn("different master SVG", envelope["errors"][0]["message"])

    def test_evidence_paths_outside_the_directory_are_refused(self):
        self.render_evidence()
        findings_path = self.evidence / "findings.json"
        findings = json.loads(findings_path.read_text(encoding="utf-8"))
        findings["evidence"]["targets"]["path"] = "../master.svg"
        findings_path.write_text(json.dumps(findings), encoding="utf-8")
        code, envelope, _ = self.score()
        self.assertEqual(code, 2)
        self.assertIn("outside", envelope["errors"][0]["message"])

    def test_second_opinion_is_recorded_and_never_gates(self):
        self.render_evidence()
        self.score(scores=PASSING.replace("legibility=4", "legibility=2"), name="agent-b",
                   out="opinion.json")
        code, envelope, _ = self.score("--second-opinion", str(self.dir / "opinion.json"))
        self.assertEqual(code, 0, envelope)
        self.assertEqual(envelope["advisories"][0]["code"], "second-opinion-dissent")
        receipt = json.loads((self.dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "ready")
        self.assertEqual(receipt["second_opinions"][0]["reviewer"]["name"], "agent-b")

    def test_a_second_opinion_from_the_same_reviewer_is_refused(self):
        self.render_evidence()
        self.score(name="agent-a", out="opinion.json")
        code, envelope, _ = self.score("--second-opinion", str(self.dir / "opinion.json"))
        self.assertEqual(code, 2)
        self.assertIn("different reviewer", envelope["errors"][0]["message"])


class OpinionComparisonTests(unittest.TestCase):
    def test_dissent_rules(self):
        primary = {axis: 4 for axis in AXES}
        self.assertEqual(headless.compare_opinion(primary, dict(primary)), [])
        notes = headless.compare_opinion(primary, {**primary, "craft": 3})
        self.assertEqual(len(notes), 1)
        self.assertIn("below the floor", notes[0])
        high = {**primary, "color": 2}
        self.assertTrue(headless.compare_opinion({**primary, "color": 5}, high))


if __name__ == "__main__":
    unittest.main()
