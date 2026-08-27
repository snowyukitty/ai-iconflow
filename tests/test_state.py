# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The self-audit, and the documents it exists to keep honest.

Nothing here reaches the network. The point of `scripts/state.py` is to report
what it could not check rather than guess, so the tests that matter most are
the ones proving an unavailable probe degrades to UNKNOWN instead of PASS.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SelfAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = load("state")

    def test_offline_run_reports_generated_artifacts_and_nothing_it_cannot_see(self) -> None:
        checks = self.state.collect(offline=True)
        by_key = {check.key: check for check in checks}

        # The generated site artifacts are checkable with no network at
        # all, and they are the ones a contributor breaks by hand-editing.
        for key in (
            "generated.i18n",
            "generated.archive",
            "generated.reference",
            "generated.tray_reference",
        ):
            with self.subTest(key=key):
                self.assertIn(key, by_key)
                self.assertEqual(self.state.PASS, by_key[key].state,
                                 by_key[key].detail)

        # Everything that needs the network says so, rather than passing.
        for key in ("deploy", "dist", "repo"):
            with self.subTest(key=key):
                self.assertEqual(self.state.UNKNOWN, by_key[key].state)

    def test_every_check_carries_a_readable_answer(self) -> None:
        for check in self.state.collect(offline=True):
            with self.subTest(key=check.key):
                self.assertIn(check.state, self.state.MARK)
                self.assertTrue(check.title.strip())
                self.assertTrue(check.detail.strip())
                self.assertTrue(check.section.strip())

    def test_a_failure_blocks_and_an_open_gate_does_not(self) -> None:
        """Gates are decisions waiting on a person; they must never gate CI."""
        Check = self.state.Check
        gates = [Check("g", "Gate", self.state.GATE, "waiting on the owner", "S"),
                 Check("u", "Unknown", self.state.UNKNOWN, "could not check", "S")]
        counts = self.state.summarise(gates)
        self.assertEqual(0, counts[self.state.FAIL])

        counts = self.state.summarise(
            gates + [Check("f", "Broken", self.state.FAIL, "drifted", "S")])
        self.assertEqual(1, counts[self.state.FAIL])

    def test_unknown_is_never_rendered_as_a_pass(self) -> None:
        """The whole design rests on this: no tick may mean 'I did not look'."""
        self.assertNotEqual(self.state.MARK[self.state.UNKNOWN],
                            self.state.MARK[self.state.PASS])
        self.assertNotEqual(self.state.MARK[self.state.GATE],
                            self.state.MARK[self.state.PASS])

    def test_json_envelope_follows_the_agent_contract(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "state.py"), "--offline", "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=300, check=False,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr[-2000:])
        # docs/AGENT_CONTRACT.md: stdout carries exactly one JSON object.
        envelope = json.loads(result.stdout)
        for key in ("schema", "command", "status", "exit_code",
                    "warnings", "advisories", "outputs", "errors"):
            self.assertIn(key, envelope)
        self.assertEqual("state", envelope["command"])
        self.assertEqual(envelope["exit_code"], result.returncode)
        self.assertIn(envelope["status"], ("ok", "blocked"))
        self.assertTrue(envelope["outputs"]["checks"])


class GeneratedDocumentTests(unittest.TestCase):
    """A generated document must say so, or someone will edit it by hand."""

    def test_state_report_is_present_and_marked_generated(self) -> None:
        report = DOCS / "STATE.md"
        self.assertTrue(report.is_file(), "run python scripts/state.py --write")
        text = report.read_text(encoding="utf-8")
        self.assertIn("Generated file. Do not edit.", text)
        self.assertIn("scripts/state.py --write", text)
        # Its currency is deliberately not asserted: the report stamps the
        # moment it observed the world, so a fresh render always differs. What
        # must hold is that it was produced by the script and says when.
        self.assertRegex(text, r"Observed \d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")

    def test_hand_maintained_docs_do_not_restate_machine_checkable_facts(self) -> None:
        """The bug this whole file exists for.

        `LAUNCH_READINESS.md` spent three days asserting the PyPI name was
        still free, after 0.5.0 had been published from this repository. The
        fix is not vigilance — it is that a document written by hand must
        defer to the report, and must not carry a claim a probe can settle.
        """
        readiness = (DOCS / "LAUNCH_READINESS.md").read_text(encoding="utf-8")
        self.assertIn("STATE.md", readiness,
                      "LAUNCH_READINESS.md must point at the generated report")

        # Structural, not a word-list. Grepping for the specific sentences that
        # went stale would flag the document *quoting* its own old error, which
        # is the useful part. A task checkbox is the real tell: it asserts a
        # condition as of whenever someone last looked, and nothing re-checks
        # it. The dated history table says the same things without going stale,
        # because an event stays true and a condition does not.
        boxes = re.findall(r"^\s*[-*]\s*\[[ xX]\]", readiness, re.M)
        self.assertEqual(
            [], boxes,
            f"{len(boxes)} status checkbox(es) are back in LAUNCH_READINESS.md; "
            "live state belongs in STATE.md, history in the dated table")


if __name__ == "__main__":
    unittest.main()
