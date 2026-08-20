"""Repository-level contracts for the v0.5 adoption loop.

Light text checks on the PR Proof workflow/action (no PyYAML dependency), the
case PR template, the community-case fixture's genuine receipt binding, the
read-only receipt helper, and the action driver's fail-closed folding.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from iconflow.casebook import AXES
from iconflow.config import (
    config_review_contract_digest,
    load_config,
    load_review_receipt,
    svg_sha256,
)
from scripts.proof_receipt import evaluate, main as receipt_main


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "icon-proof.yml"
ACTION = ROOT / ".github" / "actions" / "proof" / "action.yml"
DRIVER = ROOT / ".github" / "actions" / "proof" / "proof.py"
CASE_TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE" / "case.md"
FIXTURE = ROOT / "examples" / "community-case"
PINNED_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)@([0-9a-f]{40})\s*(#.*)?$")


def _uses_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"^\s*-?\s*uses:", line)]


def _load_driver():
    spec = importlib.util.spec_from_file_location("iconflow_proof_driver", DRIVER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProofWorkflowContractTests(unittest.TestCase):
    def test_workflow_runs_on_pull_request_with_read_only_token_and_pinned_actions(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("on:\n  pull_request:\n    paths:", text)
        self.assertNotIn("pull_request_target", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertNotIn("${{ secrets.", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("uses: ./.github/actions/proof", text)
        for glob in ("**/*.svg", "**/iconflow.toml", "**/*-review.json", "**/master-review.json"):
            self.assertIn(f'"{glob}"', text)
        remote = [line for line in _uses_lines(text) if "./.github/" not in line]
        self.assertTrue(remote)
        for line in remote:
            self.assertRegex(line, PINNED_USES)

    def test_action_is_composite_pinned_json_only_and_secret_free(self):
        text = ACTION.read_text(encoding="utf-8")
        self.assertIn("using: composite", text)
        for name in ("install", "python-version", "configs", "changed-files", "artifact-name"):
            self.assertIsNotNone(re.search(rf"^  {re.escape(name)}:\n", text, flags=re.M), name)
        self.assertIn("ai-iconflow==0.5.0", text)
        self.assertIn("actions/cache@", text)
        self.assertIn("actions/upload-artifact@", text)
        self.assertIn("proof.py", text)
        self.assertIn("proof_receipt.py", text)
        self.assertNotIn("${{ secrets.", text)
        self.assertNotIn("GITHUB_TOKEN", text)
        self.assertNotIn("pull_request_target", text)
        lines = _uses_lines(text)
        self.assertGreaterEqual(len(lines), 3)
        for line in lines:
            self.assertRegex(line, PINNED_USES)
        # The driver consumes envelopes only: the three commands it shells out to.
        driver = DRIVER.read_text(encoding="utf-8")
        for needle in ('"check"', '"review"', '"--json"', "proof-receipt"):
            self.assertIn(needle, driver)

    def test_case_pr_template_lists_every_gate(self):
        text = CASE_TEMPLATE.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("- [ ]"), 15)
        for needle in (
            "`master.svg` is semantic",
            "`tray.svg` is included",
            "`iconflow check master.svg` is clean",
            "Review Lab receipt",
            "All six axes score >= 4",
            "Cliché avoided",
            "Signature device",
            "One reusable, testable lesson",
            "`iconflow case new ...`",
            "`iconflow case lint` is clean",
            "no traced, adapted, or copied third-party mark",
            "No private repository names, local paths",
        ):
            self.assertIn(needle, text, msg=needle)
        default = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        self.assertIn("?template=case.md", default)

    def test_adoption_docs_are_present_and_keep_the_gate(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for needle in ("## First 30 minutes", "uv tool install ai-iconflow", "pipx install ai-iconflow",
                       "iconflow demo", "not live yet", "## The case lane",
                       "What reviewers will and will not accept", "Never weaken a gate"):
            self.assertIn(needle, contributing, msg=needle)
        self.assertTrue((ROOT / "docs" / "PROOF_ACTION.md").is_file())
        seeds = (ROOT / "docs" / "ISSUE_SEEDS.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"^## \d+\. ", seeds, flags=re.M)), 6)
        skill = (ROOT / "skills" / "iconflow" / "SKILL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for text in (skill, agents):
            self.assertIn("uv tool install ai-iconflow", text)
            self.assertIn("pipx install ai-iconflow", text)
            self.assertIn("scripts/setup.ps1", text)
            self.assertIn("scripts/setup.sh", text)
            self.assertNotRegex(text, r"\bcd\s+<AI_PROJECTS>", msg="skill must not cd into a toolkit path")
        self.assertRegex(skill, r"Never `cd` into a hardcoded toolkit\s+path")
        examples = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        self.assertIn("community-case/", examples)


class CommunityCaseFixtureTests(unittest.TestCase):
    def test_fixture_receipt_is_bound_to_its_source_and_contract(self):
        config = load_config(FIXTURE / "iconflow.toml")
        receipt_path = FIXTURE / "master-review.json"
        raw = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["source_sha256"], svg_sha256(config.master_path))
        self.assertEqual(raw["contract_sha256"], config_review_contract_digest(config))
        receipt = load_review_receipt(receipt_path, config)
        self.assertEqual(receipt.project, "Keepsake Knot")
        self.assertEqual(receipt.targets, ("web",))
        for axis in AXES:
            self.assertGreaterEqual(receipt.scores[axis], 4, axis)
        self.assertEqual(config.output, "icon-out")  # gitignored everywhere in this repo
        self.assertTrue((FIXTURE / "README.md").is_file())
        self.assertFalse(config.tray_svg)

    def test_fixture_source_is_the_reviewed_theme_world(self):
        world = ROOT / "website" / "assets" / "worlds" / "keepsake-knot.svg"
        self.assertEqual(svg_sha256(world), svg_sha256(FIXTURE / "master.svg"))


class ProofReceiptHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "case"
        shutil.copytree(FIXTURE, self.dir)
        self.config = self.dir / "iconflow.toml"
        self.master = self.dir / "master.svg"
        self.receipt = self.dir / "master-review.json"

    def _codes(self, envelope, key="warnings"):
        return [item["code"] for item in envelope[key]]

    def test_reports_ok_for_the_untouched_fixture(self):
        envelope = evaluate(self.config, None)
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["exit_code"], 0)
        self.assertEqual(envelope["outputs"]["receipt_kind"], "review-lab")
        self.assertEqual(envelope["outputs"]["scores"]["color"], 5)
        self.assertEqual(envelope["schema"], 1)
        self.assertEqual(envelope["command"], "proof-receipt")

    def test_reports_stale_source_after_editing_the_svg(self):
        text = self.master.read_text(encoding="utf-8")
        self.master.write_text(text.replace("</svg>", "<!-- nudge --></svg>"), encoding="utf-8")
        envelope = evaluate(self.config, None)
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual(envelope["exit_code"], 1)
        self.assertEqual(self._codes(envelope), ["receipt-stale-source"])

    def test_reports_stale_contract_after_changing_a_visual_transform(self):
        text = self.config.read_text(encoding="utf-8")
        self.config.write_text(
            text.replace('theme_color = "#251D32"', 'theme_color = "#000000"'), encoding="utf-8"
        )
        envelope = evaluate(self.config, None)
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual(self._codes(envelope), ["receipt-stale-contract"])

    def test_reports_score_floor_and_not_ready(self):
        raw = json.loads(self.receipt.read_text(encoding="utf-8"))
        raw["scores"]["distinctiveness"] = 3
        self.receipt.write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(self._codes(evaluate(self.config, None)), ["score-below-floor"])
        raw["scores"]["distinctiveness"] = 4
        raw["status"] = "draft"
        self.receipt.write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(self._codes(evaluate(self.config, None)), ["receipt-not-ready"])

    def test_absent_receipt_blocks_the_family(self):
        self.receipt.unlink()
        envelope = evaluate(self.config, None)
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual(envelope["exit_code"], 1)
        self.assertEqual(self._codes(envelope), ["receipt-not-ready"])
        missing = evaluate(self.config, self.dir / "nope.json")
        self.assertEqual(missing["status"], "error")
        self.assertEqual(missing["exit_code"], 2)

    def test_approved_config_fallback_is_validated_too(self):
        envelope = evaluate(ROOT / "examples" / "iconflow-balloon" / "iconflow.toml", None, auto=False)
        self.assertEqual(envelope["status"], "ok", envelope)
        self.assertEqual(envelope["outputs"]["receipt_kind"], "config-fallback")

    def test_cli_json_mode_prints_exactly_one_envelope(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = receipt_main(["--config", str(self.config), "--json"])
        self.assertEqual(code, 0)
        envelope = json.loads(out.getvalue())
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(out.getvalue().strip().count("\n"), 0)


class ProofDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = _load_driver()

    @staticmethod
    def _env(status, **extra):
        base = {"schema": 1, "command": "check", "status": status,
                "exit_code": {"ok": 0, "blocked": 1, "error": 2}[status],
                "warnings": [], "advisories": [], "outputs": {}, "errors": []}
        base.update(extra)
        return base

    def test_decide_folds_fail_closed(self):
        ok = {"config": "a/iconflow.toml", "check": self._env("ok"), "review": self._env("ok"),
              "receipt": self._env("ok")}
        blocked = dict(ok, receipt=self._env("blocked", warnings=[{"code": "receipt-stale-source", "message": "m"}]))
        error = dict(ok, review=self._env("error", errors=[{"code": "envelope-unparseable", "message": "m"}]))
        self.assertEqual(self.driver.decide([ok]), "ok")
        self.assertEqual(self.driver.decide([ok, blocked]), "blocked")
        self.assertEqual(self.driver.decide([blocked, error]), "error")

    def test_summary_reports_codes_from_envelopes_only(self):
        result = {
            "config": "examples/community-case/iconflow.toml", "slug": "x", "artifacts": ["x/review.png"],
            "check": self._env("ok", advisories=[{"code": "tray-template-featureless", "message": "kept none"}]),
            "review": self._env("ok"),
            "receipt": self._env("blocked", warnings=[{"code": "receipt-stale-source", "message": "stale"}],
                                 outputs={"scores": {a: 4 for a in AXES}}),
        }
        text = self.driver.render_summary([result], overall="blocked", artifact_name="iconflow-proof")
        self.assertIn("| Config | check | review | receipt | scores | sheet |", text)
        self.assertIn("`receipt-stale-source`", text)
        self.assertIn("`tray-template-featureless`", text)
        self.assertIn("4/4/4/4/4/4", text)
        self.assertIn("BLOCKED", text)
        self.assertNotIn("approved", text.lower().replace("nothing is approved", ""))
        empty = self.driver.render_summary([], overall="ok", artifact_name="iconflow-proof")
        self.assertIn("nothing to prove", empty)

    def test_run_envelope_rejects_prose_and_accepts_one_object(self):
        good = self.driver.run_envelope(
            [sys.executable, "-c", "import json; print(json.dumps({'schema': 1, 'command': 'check', 'status': 'ok', 'exit_code': 0}))"],
            cwd=ROOT, expected_command="check",
        )
        self.assertEqual(good["status"], "ok")
        self.assertEqual(good["warnings"], [])
        bad = self.driver.run_envelope(
            [sys.executable, "-c", "print('OK - no automated warnings'); raise SystemExit(0)"],
            cwd=ROOT, expected_command="check",
        )
        self.assertEqual(bad["status"], "error")
        self.assertEqual(bad["exit_code"], 2)
        self.assertEqual(bad["errors"][0]["code"], "envelope-unparseable")
        # A prose prefix is a breach, not an advisory.
        prefixed = self.driver.run_envelope(
            [sys.executable, "-c", "import json; print('note'); print(json.dumps({'schema': 1, 'command': 'check', 'status': 'ok', 'exit_code': 0}))"],
            cwd=ROOT, expected_command="check",
        )
        self.assertEqual(prefixed["errors"][0]["code"], "envelope-unparseable")
        # status must agree with exit_code and with the process return code.
        lying = self.driver.run_envelope(
            [sys.executable, "-c", "import json; print(json.dumps({'schema': 1, 'command': 'check', 'status': 'ok', 'exit_code': 0})); raise SystemExit(1)"],
            cwd=ROOT, expected_command="check",
        )
        self.assertEqual(lying["status"], "error")
        self.assertEqual(lying["errors"][0]["code"], "envelope-invalid")
        wrong_cmd = self.driver.run_envelope(
            [sys.executable, "-c", "import json; print(json.dumps({'schema': 1, 'command': 'review', 'status': 'ok', 'exit_code': 0}))"],
            cwd=ROOT, expected_command="check",
        )
        self.assertEqual(wrong_cmd["errors"][0]["code"], "envelope-invalid")
        unknown = self.driver.run_envelope(
            [sys.executable, "-c", "import json; print(json.dumps({'schema': 1, 'command': 'check', 'status': 'weird', 'exit_code': 0}))"],
            cwd=ROOT, expected_command="check",
        )
        self.assertEqual(unknown["errors"][0]["code"], "envelope-invalid")
        self.assertEqual(self.driver.decide([{"check": {"status": "ok", "exit_code": 1}}]), "error")
        self.assertEqual(self.driver.decide([{"check": {"status": "ok", "exit_code": 0}, "review": {"status": "blocked", "exit_code": 1}, "receipt": {"status": "ok", "exit_code": 0}}]), "blocked")

    def test_discover_configs_filters_by_changed_files(self):
        all_configs = self.driver.discover_configs(ROOT, None, None)
        rel = {path.relative_to(ROOT).as_posix() for path in all_configs}
        self.assertIn("examples/community-case/iconflow.toml", rel)
        self.assertIn("brand/iconflow.toml", rel)
        only = self.driver.discover_configs(ROOT, None, ["examples/community-case/master.svg"])
        self.assertEqual([p.relative_to(ROOT).as_posix() for p in only], ["examples/community-case/iconflow.toml"])
        none = self.driver.discover_configs(ROOT, None, ["website/assets/worlds/keepsake-knot.svg"])
        self.assertEqual(none, [])
        explicit = self.driver.discover_configs(ROOT, "brand/iconflow.toml", ["unrelated.txt"])
        self.assertEqual([p.relative_to(ROOT).as_posix() for p in explicit], ["brand/iconflow.toml"])


if __name__ == "__main__":
    unittest.main()
