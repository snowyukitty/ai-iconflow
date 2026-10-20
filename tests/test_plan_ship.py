# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Review, score and ship over one render plan (R16), end to end.

The renderer is a deterministic stand-in whose colour a test can change
between review and ship — the "Chromium upgraded under an approval" case the
plan exists to catch.
"""
import contextlib
import importlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from iconflow.casebook import AXES
from iconflow.cli import DEMO_FILES, _resource, main

build_module = importlib.import_module("iconflow.build")
RATIONALE = [f"--rationale={axis}=read the {axis} strip on the sheet" for axis in AXES]
PASSING = "legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4"


class Renderer:
    """A disc on transparency, in a colour the test controls."""

    color = (20, 120, 240, 255)
    renders = 0

    def __init__(self, color_scheme="light"):
        self.color_scheme = color_scheme

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, svg, size, bg="transparent"):
        Renderer.renders += 1
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        margin = max(1, size // 5)
        ImageDraw.Draw(image).ellipse([margin, margin, size - margin - 1, size - margin - 1],
                                      fill=Renderer.color)
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()


def clean_check(master, **kwargs):
    """``qa.check`` finding nothing, but recording the provenance a real audit
    records on a plan (0.9), so evidence validation sees a real record."""
    plan, provenance = kwargs.get("plan"), kwargs.get("provenance")
    if plan is not None and provenance is not None:
        from iconflow.plan import audit_origins

        maskable = kwargs.get("maskable", True)
        provenance.update(audit_origins(
            plan, maskable=maskable, linked=maskable and kwargs.get("maskable_svg") is not None))
    return []


def write_png(path, *_args, **_kwargs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (40, 40, 40)).save(path)
    return path


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue()


def link_dir(link, target):
    """A directory link the platform can make: a symlink, or on Windows a junction."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    try:
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
    except (ImportError, OSError, AttributeError):
        raise unittest.SkipTest("no directory links on this platform") from None


class PlanShipTests(unittest.TestCase):
    def setUp(self):
        Renderer.color = (20, 120, 240, 255)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "family"
        self.dir.mkdir()
        for name in DEMO_FILES:
            (self.dir / name).write_bytes(_resource("demo", name).read_bytes())
        self.config = self.dir / "iconflow.toml"
        self.evidence = self.dir / "evidence"
        self.receipt = self.dir / "receipt.json"
        from iconflow.budget import Budget

        for target, kwargs in (
            ("iconflow.qa.check", {"side_effect": clean_check}),
            ("iconflow.qa.tray_template_warnings", {"return_value": []}),
            ("iconflow.budget.budget_svg", {"return_value": Budget(
                source="master.svg", ground="transparent", cuts_256=1, cuts_16=1,
                parts_256=1, parts_16=1)}),
            ("iconflow.review.contact_sheet", {"side_effect": lambda master, out, **kw: write_png(out)}),
            ("iconflow.headless.target_sheet", {"side_effect": lambda master, out, **kw: write_png(out)}),
        ):
            patcher = mock.patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        # build() and a command's render session reach the renderer through
        # different seams (0.9); substitute both.
        for patcher in (mock.patch.object(build_module, "Rasterizer", Renderer),
                        mock.patch("iconflow.rasterize.Rasterizer", Renderer)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def review_and_score(self):
        code, envelope, err = run(["review", "--config", str(self.config), "--evidence", str(self.evidence)])
        self.assertEqual(code, 0, (envelope, err))
        code, envelope, err = run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "weakest: legibility; kept the cut",
            "--reviewer-name", "agent-a", "--out", str(self.receipt),
        ])
        self.assertEqual(code, 0, (envelope, err))
        return json.loads(self.receipt.read_text(encoding="utf-8"))

    def ship(self, *extra):
        return run(["ship", "--config", str(self.config), "--review", str(self.receipt), *extra])

    def output_dir(self):
        from iconflow.config import load_config

        return load_config(self.config).output_path

    def test_score_binds_the_evidence_plan_and_ship_verifies_it(self):
        receipt = self.review_and_score()
        findings = json.loads((self.evidence / "findings.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["plan"], findings["plan"])
        self.assertTrue((self.evidence / "plan" / "plan.json").is_file())
        code, envelope, err = self.ship()
        self.assertEqual(code, 0, (envelope, err))
        plan = envelope["outputs"]["plan"]
        self.assertEqual((plan["verified"], plan["bytes_verified"], plan["mode"]), (True, True, "rendered"))
        self.assertEqual(plan["digest"], receipt["plan"]["digest"])
        self.assertIn("Render plan verified", err + "")

    def test_changed_pixels_under_the_same_approval_are_blocked(self):
        self.review_and_score()
        Renderer.color = (200, 30, 30, 255)  # "the renderer was upgraded"
        shutil.rmtree(self.output_dir(), ignore_errors=True)
        code, envelope, err = self.ship()
        self.assertEqual(code, 1)
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["plan-drift"])
        self.assertIn("not the pixels that were reviewed", err)
        self.assertFalse(self.output_dir().exists())

    def test_ship_plan_publishes_the_reviewed_bytes_without_rendering(self):
        self.review_and_score()
        Renderer.color = (200, 30, 30, 255)
        before = Renderer.renders
        code, envelope, err = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 0, (envelope, err))
        self.assertEqual(Renderer.renders, before)
        self.assertEqual(envelope["outputs"]["plan"]["mode"], "replayed")
        manifest = json.loads((self.evidence / "plan" / "plan.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            self.assertEqual((self.output_dir() / entry["path"]).read_bytes(),
                             (self.evidence / "plan" / "files" / entry["path"]).read_bytes())

    def test_a_tampered_plan_is_refused_by_score_and_by_ship(self):
        self.review_and_score()
        victim = next((self.evidence / "plan" / "files").rglob("*.png"))
        victim.write_bytes(victim.read_bytes() + b"\0")
        code, envelope, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1)
        self.assertEqual(envelope["warnings"][0]["code"], "plan-replay")
        code, envelope, _ = run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "weakest: legibility; kept the cut",
            "--reviewer-name", "agent-a", "--out", str(self.dir / "again.json"),
        ])
        self.assertEqual(code, 2)
        self.assertIn("render plan", envelope["errors"][0]["message"])

    def test_a_receipt_without_a_plan_still_ships_and_says_so(self):
        receipt = self.review_and_score()
        receipt.pop("plan")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 0, envelope)
        self.assertIn("plan-unbound", [a["code"] for a in envelope["advisories"]])
        self.assertIsNone(envelope["outputs"]["plan"]["verified"])
        code, envelope, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1)
        self.assertIn("no plan", envelope["warnings"][0]["message"])

    def test_a_malformed_plan_binding_is_a_configuration_error(self):
        receipt = self.review_and_score()
        receipt["plan"]["digest"] = "0" * 64
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "config")

    def test_a_plan_for_other_settings_cannot_be_replayed(self):
        self.review_and_score()
        text = self.config.read_text(encoding="utf-8")
        self.config.write_text(text.replace("optimize_png = true", "optimize_png = false"), encoding="utf-8")
        code, envelope, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1)
        self.assertIn("other settings", " ".join(w["message"] for w in envelope["warnings"]))

    def test_PF01_a_self_contradicting_binding_cannot_replay(self):
        # Shape-valid: one file's content identity changed and the aggregate
        # recomputed, the byte and provenance digests left as approved.
        from iconflow.plan import _listing_digest

        receipt = self.review_and_score()
        files = receipt["plan"]["files"]
        files[sorted(files)[0]]["content"] = "a" * 64
        receipt["plan"]["digest"] = _listing_digest(
            "content", {path: entry["content"] for path, entry in files.items()})
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        shutil.rmtree(self.output_dir(), ignore_errors=True)
        code, envelope, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1, envelope)
        self.assertEqual({w["code"] for w in envelope["warnings"]}, {"plan-replay"})
        self.assertIn("content", envelope["warnings"][0]["message"])
        self.assertFalse(self.output_dir().exists())

    def test_PF01_a_contradicting_per_file_hash_cannot_replay(self):
        receipt = self.review_and_score()
        files = receipt["plan"]["files"]
        files[sorted(files)[0]]["sha256"] = "b" * 64
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        shutil.rmtree(self.output_dir(), ignore_errors=True)
        code, envelope, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1, envelope)
        self.assertIn("per-file byte hashes", " ".join(w["message"] for w in envelope["warnings"]))
        self.assertFalse(self.output_dir().exists())

    def test_PF02_a_linked_folder_above_the_output_is_refused(self):
        import os

        self.review_and_score()
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        link_dir(self.dir / "linked", outside)
        text = self.config.read_text(encoding="utf-8")
        for configured in ("ghost/../linked/icons", "linked/icons"):
            self.config.write_text(text.replace('output = "build"', f'output = "{configured}"'),
                                   encoding="utf-8")
            code, envelope, _ = self.ship()
            self.assertEqual(code, 2, (configured, envelope))
        code, envelope, _ = self.ship()
        self.assertEqual(code, 2, envelope)
        # Where write_plan's own refusal of a linked output always was (IR04).
        self.assertEqual(envelope["errors"][0]["code"], "runtime")
        self.assertIn("link or junction", envelope["errors"][0]["message"])
        self.assertEqual(list(outside.iterdir()), [])
        # ...so it never hides a gate: drifted pixels are still plan-drift.
        Renderer.color = (200, 30, 30, 255)
        code, envelope, _ = self.ship()
        self.assertEqual(code, 1, envelope)
        self.assertEqual(envelope["warnings"][0]["code"], "plan-drift")
        Renderer.color = (20, 120, 240, 255)
        self.assertEqual(list(outside.iterdir()), [])
        # An output the check cannot inspect is held the same way (VR02).
        with mock.patch.object(build_module, "output_link", side_effect=PermissionError("denied")):
            Renderer.color = (200, 30, 30, 255)
            code, envelope, _ = self.ship()
            self.assertEqual((code, envelope["warnings"][0]["code"]), (1, "plan-drift"))
            self.assertIn("audit", envelope["outputs"])
            Renderer.color = (20, 120, 240, 255)
            code, envelope, _ = self.ship()
            self.assertEqual((code, envelope["errors"][0]["code"]), (2, "runtime"))
            self.assertIn("cannot be checked", envelope["errors"][0]["message"])
        # --out, from the working directory, and '..' cannot walk around it —
        # not through a missing folder, not through a file standing where a
        # folder would be: the path checked is the path written (SV01).
        (self.dir / "blocked").write_text("x", encoding="utf-8")
        here = os.getcwd()
        os.chdir(self.dir)
        try:
            for out in ("linked/icons", "build/../linked/icons", "ghost/../linked/icons",
                        "blocked/../linked/icons"):
                with self.subTest(out=out):
                    code, envelope, _ = self.ship("--out", out)
                    self.assertEqual(code, 2, envelope)
            # An ordinary folder next door, reached through '..', still ships.
            code, envelope, _ = self.ship("--out", "../family/plain")
            self.assertEqual(code, 0, envelope)
        finally:
            os.chdir(here)
        self.assertEqual(list(outside.iterdir()), [])

    def test_F6_01_a_link_the_repository_carries_beside_the_config_is_refused(self):
        # repo/.git, repo/family/iconflow.toml, repo/dist -> outside: the
        # config's folder is not the whole project.
        self.review_and_score()
        repo = Path(self.tmp.name)
        (repo / ".git").mkdir()
        outside = repo.parent / f"{repo.name}-outside"
        outside.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        link_dir(repo / "dist", outside)
        (repo / "plain").mkdir()
        text = self.config.read_text(encoding="utf-8")
        self.config.write_text(text.replace('output = "build"', 'output = "../dist/icons"'),
                               encoding="utf-8")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 2, envelope)
        self.assertIn("link or junction", envelope["errors"][0]["message"])
        self.assertEqual(list(outside.iterdir()), [])
        # An ordinary sibling folder of the repository still ships.
        self.config.write_text(text.replace('output = "build"', 'output = "../plain/icons"'),
                               encoding="utf-8")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 0, envelope)

    def test_P05_a_plan_edited_to_match_new_settings_is_still_refused(self):
        self.review_and_score()
        text = self.config.read_text(encoding="utf-8")
        self.config.write_text(text.replace("optimize_png = true", "optimize_png = false"), encoding="utf-8")
        manifest_path = self.evidence / "plan" / "plan.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["parameters"]["optimize_png"] = False
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        code, envelope, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1)
        self.assertEqual(envelope["warnings"][0]["code"], "plan-replay")

    def test_P10_a_null_plan_is_not_an_unbound_receipt(self):
        receipt = self.review_and_score()
        receipt["plan"] = None
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "config")

    def test_P11_a_blocked_ship_still_reports_what_differed(self):
        self.review_and_score()
        Renderer.color = (200, 30, 30, 255)
        code, envelope, _ = self.ship()
        self.assertEqual(code, 1)
        plan = envelope["outputs"]["plan"]
        self.assertEqual((plan["verified"], plan["bytes_verified"], plan["mode"]), (False, False, "rendered"))
        # The whole list, not the first eight; a colour change leaves the
        # alpha-only tray templates alone, and they are not reported.
        self.assertGreater(len(plan["drift"]), 8)
        self.assertIn("icon-512.png", plan["drift"])
        self.assertNotIn("tray/trayTemplate.png", plan["drift"])

    def test_a_second_opinion_over_other_pixels_is_refused(self):
        receipt = self.review_and_score()
        other = dict(receipt, reviewer={"kind": "agent", "name": "agent-b"})
        other["plan"] = dict(receipt["plan"], digest="f" * 64)
        (self.dir / "other.json").write_text(json.dumps(other), encoding="utf-8")
        code, envelope, _ = run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "weakest: legibility; kept the cut",
            "--reviewer-name", "agent-a", "--out", str(self.dir / "with-opinion.json"),
            "--second-opinion", str(self.dir / "other.json"),
        ])
        self.assertEqual(code, 2)
        self.assertIn("different pixels", envelope["errors"][0]["message"])


if __name__ == "__main__":
    unittest.main()
