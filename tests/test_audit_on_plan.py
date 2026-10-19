# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""0.9: the audit reads the render plan, in one render session per command.

Each test names the design-consult finding it closes (D01-D16, recorded in
docs/MILESTONE_v0.9.md). Everything here runs without Chromium except the two
classes marked NEEDS_CHROMIUM.
"""
import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from iconflow import qa
from iconflow.audit import AuditInputs, run_audit
from iconflow.casebook import AXES
from iconflow.cli import main
from iconflow.plan import (
    PlanError, RenderPlan, audit_frames, audit_maskable, capture_sources, compute_plan,
)
from iconflow.session import RenderSession, SessionRasterizer, scheme_rasterizer

NEEDS_CHROMIUM = unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
ROOT = Path(__file__).resolve().parents[1]
RATIONALE = [f"--rationale={axis}=read the {axis} strip on the sheet" for axis in AXES]
PASSING = "legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4"
MASTER = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
          '<circle cx="512" cy="512" r="400" fill="#1478F0"/></svg>\n')


def _png(size, color=(20, 120, 240, 255), *, disc=True):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if disc and size >= 4:
        margin = max(1, size // 8)
        ImageDraw.Draw(image).ellipse([margin, margin, size - margin - 1, size - margin - 1],
                                      fill=color)
    else:
        image.putpixel((size // 2, size // 2), color)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class Disc:
    """A renderer drawing a disc (or, with ``dot``, one pixel) at any size."""

    launches = 0
    renders = 0
    dot = False
    color = (20, 120, 240, 255)

    def __init__(self, color_scheme="light"):
        self.color_scheme = color_scheme

    def __enter__(self):
        Disc.launches += 1
        return self

    def __exit__(self, *exc):
        return None

    def render(self, svg, size, bg="transparent"):
        Disc.renders += 1
        return _png(size, Disc.color, disc=not Disc.dot)

    def render_rect(self, svg, width, height, bg="transparent"):
        Disc.renders += 1
        return _png(width, Disc.color)


def reset_disc():
    Disc.launches = Disc.renders = 0
    Disc.dot = False
    Disc.color = (20, 120, 240, 255)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue(), out.getvalue()


# ----------------------------------------------------------------- the session

class RenderSessionTests(unittest.TestCase):
    def setUp(self):
        reset_disc()

    def test_D05_one_request_renders_once_and_every_key_part_counts(self):
        with RenderSession(factory=Disc) as session:
            light = session.rasterizer("light")
            first = light.render("<svg/>", 16)
            self.assertIs(light.render("<svg/>", 16), first)
            self.assertEqual(Disc.renders, 1)
            light.render("<svg a='1'/>", 16)     # another SVG
            light.render("<svg/>", 32)           # another size
            light.render("<svg/>", 16, bg="#ffffff")  # another background
            light.render_rect("<svg/>", 16, 16)  # another operation
            session.rasterizer("dark").render("<svg/>", 16)  # another scheme
            self.assertEqual(Disc.renders, 6)
            # Two spellings of one colour are one request.
            light.render("<svg/>", 16, bg="#FFFFFF")
            self.assertEqual(Disc.renders, 6)

    def test_D05_a_warm_cache_refuses_what_a_cold_one_refuses(self):
        with RenderSession(factory=Disc) as session:
            light = session.rasterizer("light")
            light.render("<svg/>", 1)
            with self.assertRaises(ValueError):
                light.render("<svg/>", True)
            with self.assertRaises(ValueError):
                light.render("<svg/>", 16, bg="url(javascript:1)")

    def test_D10_a_failed_render_is_not_cached_and_a_failed_launch_is_not_retried(self):
        calls = []

        class Flaky(Disc):
            def render(self, svg, size, bg="transparent"):
                calls.append(size)
                if len(calls) == 1:
                    raise RuntimeError("renderer hiccup")
                return super().render(svg, size, bg)

        with RenderSession(factory=Flaky) as session:
            r = session.rasterizer("light")
            with self.assertRaises(RuntimeError):
                r.render("<svg/>", 16)
            r.render("<svg/>", 16)
            self.assertEqual(calls, [16, 16])

        starts = []

        class NoBrowser:
            def __init__(self, color_scheme="light"):
                starts.append(color_scheme)

            def __enter__(self):
                raise RuntimeError("Chromium is not installed")

        with RenderSession(factory=NoBrowser) as session:
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    session.rasterizer("light").render("<svg/>", 16)
        self.assertEqual(starts, ["light"])

    def test_D10_borrowed_rasterizers_never_close_and_the_owner_closes_newest_first(self):
        closed = []

        class Owned(Disc):
            def __exit__(self, *exc):
                closed.append(self.color_scheme)

        session = RenderSession(factory=Owned)
        light = session.rasterizer("light")
        with light as borrowed:  # a stage "owning" it must not close it
            borrowed.render("<svg/>", 16)
        session.rasterizer("dark").render("<svg/>", 16)
        self.assertEqual(closed, [])
        session.close()
        self.assertEqual(closed, ["dark", "light"])
        with self.assertRaises(RuntimeError):
            light.render("<svg/>", 64)

    def test_D10_nothing_starts_until_something_renders(self):
        with RenderSession(factory=Disc) as session:
            session.rasterizer("light")
            session.rasterizer("dark")
        self.assertEqual(Disc.launches, 0)

    def test_D10_past_the_budget_renders_are_returned_but_not_kept(self):
        with RenderSession(factory=Disc, budget_bytes=1) as session:
            r = session.rasterizer("light")
            r.render("<svg/>", 16)
            r.render("<svg/>", 16)
            self.assertEqual((Disc.renders, session.uncached, session.cached_bytes), (2, 2, 0))

    def test_a_second_scheme_borrows_the_first_ones_browser(self):
        made = []

        class Sharing(Disc):
            shares_browser = True

            def __init__(self, color_scheme="light", share=None):
                super().__init__(color_scheme)
                made.append((color_scheme, share))

        with RenderSession(factory=Sharing) as session:
            session.rasterizer("light").render("<svg/>", 16)
            session.rasterizer("dark").render("<svg/>", 16)
        self.assertEqual(made[0], ("light", None))
        self.assertEqual(made[1][0], "dark")
        self.assertIsInstance(made[1][1], Sharing)

    def test_scheme_rasterizer_only_lends_a_scheme_it_can_serve(self):
        with RenderSession(factory=Disc) as session:
            light = session.rasterizer("light")
            self.assertIsInstance(scheme_rasterizer(light, "dark"), SessionRasterizer)
            self.assertEqual(scheme_rasterizer(light, "dark").color_scheme, "dark")
        own = Disc("light")
        self.assertIs(scheme_rasterizer(own, "light"), own)
        self.assertIsNone(scheme_rasterizer(own, "dark"))
        self.assertIsNone(scheme_rasterizer(None, "light"))


# ------------------------------------------------------------- frame selectors

def _plan(files, *, master_sha="0" * 64, scheme="light", parameters=None):
    return RenderPlan.create(
        files,
        inputs={"master": {"path": "master.svg", "sha256": master_sha, "bytes_sha256": "0" * 64}},
        parameters={"color_scheme": scheme, **(parameters or {})}, toolchain={},
    )


class FrameSelectorTests(unittest.TestCase):
    def test_D03_untransformed_files_and_container_slots_are_read_with_their_origin(self):
        from iconflow import assemble

        ico = assemble.ico_bytes({16: _png(16), 32: _png(32), 48: _png(48)})
        plan = _plan({"favicon.ico": ico, "icon-512.png": _png(512)})
        frames = audit_frames(plan)
        self.assertEqual(sorted(frames), [16, 32, 48, 512])
        self.assertEqual(dict(frames[16].origin)["file"], "favicon.ico")
        self.assertEqual(dict(frames[16].origin)["slot"], 16)
        self.assertIsNone(dict(frames[512].origin)["slot"])

    def test_D03_transformed_outputs_never_stand_for_the_master(self):
        plan = _plan({
            "apple-touch-icon.png": _png(180), "build/icon.png": _png(1024),
            "emote/28.png": _png(28), "tray/tray@16.png": _png(16),
            "android/play-store-512.png": _png(512),
        })
        self.assertEqual(audit_frames(plan), {})

    def test_D03_a_frame_whose_pixels_are_not_its_size_is_refused(self):
        plan = _plan({"icon-512.png": _png(256)})
        with self.assertRaisesRegex(PlanError, "decodes to 256x256"):
            audit_frames(plan)

    def test_D03_two_representations_of_one_size_must_agree(self):
        plan = _plan({"icon-512.png": _png(512), "icons/icon.png": _png(512, (200, 0, 0, 255))})
        with self.assertRaisesRegex(PlanError, "two different 512px renders"):
            audit_frames(plan)

    def test_D03_the_maskable_file_is_the_only_maskable_evidence(self):
        self.assertIsNone(audit_maskable(_plan({"icon-512.png": _png(512)})))
        found = audit_maskable(_plan({"icon-512-maskable.png": _png(512)}))
        self.assertEqual(dict(found.origin)["file"], "icon-512-maskable.png")


# ---------------------------------------------------- the audit on the plan

class AuditOnPlanTests(unittest.TestCase):
    def setUp(self):
        reset_disc()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.master = Path(self.tmp.name) / "master.svg"
        self.master.write_bytes(MASTER.encode("utf-8"))

    def plan_for(self, targets=("web",), scheme="light"):
        with RenderSession(factory=Disc) as session:
            return compute_plan(self.master, list(targets), color_scheme=scheme,
                                rasterizer=session.rasterizer(scheme))

    def test_D04_findings_and_metrics_are_the_same_with_and_without_the_plan(self):
        for targets in (("web",), ("web", "tauri"), ("tauri",), ("emote",)):
            with self.subTest(targets=targets):
                plan = self.plan_for(targets)
                inputs = AuditInputs(master=self.master, targets=targets)
                with mock.patch("iconflow.qa.Rasterizer", Disc):
                    plain = run_audit(inputs)
                    planned = run_audit(inputs, plan=plan)
                self.assertEqual([str(w) for w in plain.warnings], [str(w) for w in planned.warnings])
                self.assertEqual(plain.metrics, planned.metrics)

    def test_D09_planned_probes_render_nothing_and_say_where_their_pixels_came_from(self):
        plan = self.plan_for(("web",))
        Disc.renders = Disc.launches = 0
        with mock.patch("iconflow.qa.Rasterizer", Disc):
            result = run_audit(AuditInputs(master=self.master, targets=("web",)), plan=plan)
        # 16, 32 and the maskable composition all ship in a web plan.
        self.assertEqual((Disc.launches, Disc.renders), (0, 0))
        self.assertTrue(result.audited)
        self.assertEqual({key: origin["file"] for key, origin in result.frames.items()},
                         {"master-16": "favicon.ico", "master-32": "favicon.ico",
                          "maskable-512": "icon-512-maskable.png"})

    def test_D09_an_emote_plan_has_no_counterpart_and_says_so(self):
        plan = self.plan_for(("emote",))
        with mock.patch("iconflow.qa.Rasterizer", Disc):
            result = run_audit(AuditInputs(master=self.master, targets=("emote",)), plan=plan)
        self.assertFalse(result.audited)
        self.assertEqual({origin["from"] for origin in result.frames.values()}, {"render"})
        self.assertEqual(result.frames["master-16"]["reason"], "no shipped frame at this size")

    def test_D01_a_plan_from_another_source_or_scheme_is_refused(self):
        plan = self.plan_for(("web",))
        self.master.write_bytes(MASTER.replace("400", "390").encode("utf-8"))
        with mock.patch("iconflow.qa.Rasterizer", Disc), \
                self.assertRaisesRegex(PlanError, "not rendered from the master"):
            run_audit(AuditInputs(master=self.master, targets=("web",)), plan=plan)
        self.master.write_bytes(MASTER.encode("utf-8"))
        with mock.patch("iconflow.qa.Rasterizer", Disc), \
                self.assertRaisesRegex(PlanError, "'light' scheme, not the 'dark'"):
            run_audit(AuditInputs(master=self.master, targets=("web",), color_scheme="dark"),
                      plan=plan)

    def test_D01_a_maskable_file_for_another_composition_is_refused(self):
        plan = self.plan_for(("web",))
        with mock.patch("iconflow.qa.Rasterizer", Disc), \
                self.assertRaisesRegex(PlanError, "another background"):
            run_audit(AuditInputs(master=self.master, targets=("web",),
                                  background_color="#101010"), plan=plan)

    def test_D01_the_audit_measures_the_captured_text_not_the_file(self):
        sources = capture_sources(self.master, ["web"])
        self.master.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>A</text></svg>',
                               encoding="utf-8")
        with mock.patch("iconflow.qa.Rasterizer", Disc):
            result = run_audit(AuditInputs(master=self.master, targets=("web",)), sources=sources)
        self.assertNotIn("distinctiveness-text", [w.code for w in result.warnings])


# ------------------------------------------------------------- commands

def write_project(directory: Path, *, targets='["web"]', extra="") -> Path:
    (directory / "master.svg").write_bytes(MASTER.encode("utf-8"))
    config = directory / "iconflow.toml"
    config.write_text(f'''schema_version = 1
[project]
name = "Disc"
master = "master.svg"
output = "out"
[build]
targets = {targets}
{extra}
''', encoding="utf-8")
    return config


def write_png(path, *_args, **_kwargs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (40, 40, 40)).save(path)
    return path


class CommandFixture(unittest.TestCase):
    """A real audit and a real plan, drawn by ``Disc`` through the one seam."""

    def setUp(self):
        reset_disc()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.config = write_project(self.dir)
        self.evidence = self.dir / "evidence"
        self.receipt = self.dir / "receipt.json"
        from iconflow.budget import Budget

        for target, kwargs in (
            ("iconflow.rasterize.Rasterizer", {"new": Disc}),
            ("iconflow.qa.Rasterizer", {"new": Disc}),
            ("iconflow.budget.budget_svg", {"return_value": Budget(
                source="master.svg", ground="transparent", cuts_256=1, cuts_16=1,
                parts_256=1, parts_16=1)}),
            ("iconflow.review.contact_sheet", {"side_effect": lambda master, out, **kw: write_png(out)}),
            ("iconflow.headless.target_sheet", {"side_effect": lambda master, out, **kw: write_png(out)}),
        ):
            patcher = mock.patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def review_and_score(self):
        code, envelope, err, _ = run(["review", "--config", str(self.config),
                                      "--evidence", str(self.evidence)])
        self.assertEqual(code, 0, (envelope, err))
        code, envelope, err, _ = run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "weakest: legibility; kept the disc",
            "--reviewer-name", "agent-a", "--out", str(self.receipt),
        ])
        self.assertEqual(code, 0, (envelope, err))
        return json.loads(self.receipt.read_text(encoding="utf-8"))

    def ship(self, *extra):
        return run(["ship", "--config", str(self.config), "--review", str(self.receipt), *extra])


class ReviewAndShipTests(CommandFixture):
    def test_D07_evidence_records_and_score_carries_what_was_audited(self):
        receipt = self.review_and_score()
        findings = json.loads((self.evidence / "findings.json").read_text(encoding="utf-8"))
        provenance = findings["audit_provenance"]
        self.assertTrue(provenance["audited"])
        self.assertEqual(provenance["plan"]["digest"], findings["plan"]["digest"])
        self.assertTrue(receipt["review_surface"]["audited_plan"])

    def test_D07_a_frame_record_that_is_not_the_saved_plans_is_refused(self):
        self.review_and_score()
        path = self.evidence / "findings.json"
        findings = json.loads(path.read_text(encoding="utf-8"))
        findings["audit_provenance"]["frames"]["master-16"]["sha256"] = "f" * 64
        path.write_text(json.dumps(findings), encoding="utf-8")
        code, envelope, err, _ = run([
            "score", "--config", str(self.config), "--evidence", str(self.evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "n", "--reviewer-name", "a",
            "--out", str(self.receipt),
        ])
        self.assertEqual(code, 2)
        self.assertIn("master-16 frame is not the one the saved plan holds", err)

    def test_D07_malformed_provenance_is_refused_and_absent_provenance_is_legacy(self):
        self.review_and_score()
        path = self.evidence / "findings.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        argv = ["score", "--config", str(self.config), "--evidence", str(self.evidence),
                "--scores", PASSING, *RATIONALE, "--notes", "n", "--reviewer-name", "a",
                "--out", str(self.receipt)]
        for broken in ({"schema": 2}, [], {"schema": 1, "frames": {}, "audited": True, "plan": None}):
            with self.subTest(broken=broken):
                path.write_text(json.dumps({**original, "audit_provenance": broken}), encoding="utf-8")
                self.assertEqual(run(argv)[0], 2)
        legacy = {key: value for key, value in original.items() if key != "audit_provenance"}
        path.write_text(json.dumps(legacy), encoding="utf-8")
        code, envelope, err, _ = run(argv)
        self.assertEqual(code, 0, (envelope, err))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertFalse(receipt["review_surface"]["audited_plan"])

    def test_D08_the_findings_digest_is_of_the_bytes_that_were_validated(self):
        receipt = self.review_and_score()
        raw = (self.evidence / "findings.json").read_bytes()
        self.assertEqual(receipt["review_surface"]["findings_sha256"], hashlib.sha256(raw).hexdigest())

    def test_D08_ship_reports_the_digest_of_the_receipt_it_validated(self):
        self.review_and_score()
        code, envelope, err, _ = self.ship()
        self.assertEqual(code, 0, (envelope, err))
        self.assertEqual(envelope["outputs"]["receipt_sha256"],
                         hashlib.sha256(self.receipt.read_bytes()).hexdigest())
        plan = envelope["outputs"]["plan"]
        self.assertTrue(plan["audited"])
        self.assertEqual(plan["audit_frames"]["master-16"]["file"], "favicon.ico")

    def test_D04_replay_audits_the_saved_pixels_not_a_new_render(self):
        """The new renderer would fail coverage; the reviewed bytes do not."""
        self.review_and_score()
        Disc.dot = True  # "another machine's renderer"
        code, envelope, _err, _ = run(["check", "--config", str(self.config)])
        self.assertEqual(code, 1)
        self.assertIn("coverage-16", [w["code"] for w in envelope["warnings"]])
        code, envelope, err, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 0, (envelope, err))
        self.assertEqual(envelope["outputs"]["plan"]["mode"], "replayed")
        self.assertTrue(envelope["outputs"]["plan"]["audited"])

    def test_D04_replaying_a_flat_web_plan_starts_no_browser(self):
        self.review_and_score()
        Disc.launches = Disc.renders = 0
        code, envelope, err, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 0, (envelope, err))
        self.assertEqual((Disc.launches, Disc.renders), (0, 0))

    def test_D02_rendered_ship_measures_its_new_pixels_and_qa_comes_first(self):
        self.review_and_score()
        Disc.dot = True
        with mock.patch("iconflow.plan.write_plan") as write:
            code, envelope, _err, _ = self.ship()
        self.assertEqual(code, 1)
        codes = [w["code"] for w in envelope["warnings"]]
        # Both the audit and the drift gate would refuse; QA is reported, alone.
        self.assertEqual(codes[0], "qa-warnings")
        self.assertNotIn("plan-drift", codes)
        write.assert_not_called()
        self.assertEqual(envelope["outputs"]["audit"]["targets"], ["web"])

    def test_D02_precedence_when_the_plan_cannot_be_made(self):
        self.review_and_score()
        cases = (
            (PlanError("a path named twice"), 1, "plan-replay"),
            (RuntimeError("Chromium went away"), 2, "runtime"),
        )
        for failure, exit_code, code_name in cases:
            with self.subTest(failure=failure), \
                    mock.patch("iconflow.plan.compute_plan", side_effect=failure), \
                    mock.patch("iconflow.plan.write_plan") as write:
                code, envelope, _err, _ = self.ship()
            self.assertEqual(code, exit_code)
            names = [item["code"] for item in envelope["warnings"] + envelope["errors"]]
            self.assertEqual(names, [code_name])
            write.assert_not_called()
        # ...and an audit warning still outranks a plan that cannot be made.
        with mock.patch("iconflow.plan.compute_plan", side_effect=PlanError("x")), \
                mock.patch("iconflow.qa.check", return_value=[qa.Finding("viewbox", "no viewBox")]):
            code, envelope, _err, _ = self.ship()
        self.assertEqual((code, envelope["warnings"][0]["code"]), (1, "qa-warnings"))

    def test_D02_a_replay_that_will_be_refused_is_never_measured(self):
        self.review_and_score()
        plan_json = self.evidence / "plan" / "plan.json"
        manifest = json.loads(plan_json.read_text(encoding="utf-8"))
        manifest["parameters"]["theme_color"] = "#123456"
        plan_json.write_text(json.dumps(manifest), encoding="utf-8")
        seen = []
        real = qa.check

        def spy(*args, **kwargs):
            seen.append(kwargs.get("plan"))
            return real(*args, **kwargs)

        with mock.patch("iconflow.qa.check", side_effect=spy):
            code, envelope, _err, _ = self.ship("--plan", str(self.evidence / "plan"))
        self.assertEqual(code, 1)
        self.assertEqual(seen, [None])
        self.assertEqual({w["code"] for w in envelope["warnings"]}, {"plan-replay"})

    def test_D01_a_source_edited_after_the_approval_check_is_refused(self):
        self.review_and_score()
        real = capture_sources

        def edit_then_capture(master, *args, **kwargs):
            Path(master).write_text(MASTER.replace("400", "380"), encoding="utf-8")
            return real(master, *args, **kwargs)

        with mock.patch("iconflow.plan.capture_sources", side_effect=edit_then_capture), \
                mock.patch("iconflow.plan.write_plan") as write:
            code, envelope, err, _ = self.ship()
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "source-changed")
        write.assert_not_called()

    def test_D01_a_source_edited_while_the_review_runs_writes_no_findings(self):
        def edit_while_drawing(master, out, **_kwargs):
            Path(master).write_text(MASTER.replace("400", "380"), encoding="utf-8")
            return write_png(out)

        with mock.patch("iconflow.review.contact_sheet", side_effect=edit_while_drawing):
            code, envelope, err, _ = run(["review", "--config", str(self.config),
                                          "--evidence", str(self.evidence)])
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "source-changed")
        self.assertFalse((self.evidence / "findings.json").exists())

    def test_D14_a_short_reason_fails_before_the_walk(self):
        code, envelope, err, _ = run(["review", "--config", str(self.config),
                                      "--evidence", str(self.evidence)])
        self.assertEqual(code, 0, (envelope, err))
        for argv, needle in (
            ([*RATIONALE[:-1], "--rationale=craft=short", "--notes", "n", "--reviewer-name", "a"],
             "craft"),
            ([*RATIONALE, "--notes", " ", "--reviewer-name", "a"], "--notes is required"),
            ([*RATIONALE, "--notes", "n", "--reviewer-name", " "], "--reviewer-name is required"),
        ):
            with self.subTest(needle=needle):
                out, err_stream = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err_stream):
                    code = main(["score", "--config", str(self.config), "--evidence",
                                 str(self.evidence), "--scores", PASSING, *argv,
                                 "--out", str(self.receipt)])
                self.assertEqual(code, 2)
                self.assertIn(needle, err_stream.getvalue())
                self.assertNotIn("legibility:", out.getvalue())
                self.assertFalse(self.receipt.exists())

    def test_D14_a_reason_without_scores_is_not_silently_dropped(self):
        run(["review", "--config", str(self.config), "--evidence", str(self.evidence)])
        code, envelope, err, _ = run(["score", "--config", str(self.config), "--evidence",
                                      str(self.evidence), *RATIONALE, "--notes", "n",
                                      "--reviewer-name", "a"])
        self.assertEqual(code, 2)
        self.assertIn("--rationale needs --scores", err)

    def test_a_renderer_error_is_an_exit_2_envelope_not_a_traceback(self):
        PlaywrightError = type("Error", (Exception,), {"__module__": "playwright._impl._errors"})
        with mock.patch("iconflow.cli._cmd_check", side_effect=PlaywrightError("browser crashed")):
            code, envelope, err, _ = run(["check", "--config", str(self.config)])
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "runtime"))
        self.assertIn("browser crashed", err)


class LabTests(CommandFixture):
    def lab(self, config=None):
        out = self.dir / "review.html"
        code, envelope, err, _ = run(["review", "--config", str(config or self.config),
                                      "--out", str(self.dir / "r.png"), "--html", str(out)])
        self.assertEqual(code, 0, (envelope, err))
        return out.read_text(encoding="utf-8"), envelope

    def test_D13_a_draft_is_keyed_by_contract_and_plan_not_by_source(self):
        page, envelope = self.lab()
        self.assertIn("iconflow-review-v2-${seed.contract_sha256}-${seed.plan ? seed.plan.digest", page)
        self.assertNotIn("iconflow-review-${seed.source_sha256}", page)

    def test_D13_a_stale_config_decision_is_not_prefilled(self):
        config = write_project(self.dir, extra='background_color = "#FFFFFF"')
        text = config.read_text(encoding="utf-8") + '''[review]
status = "approved"
source_sha256 = "%s"
contract_sha256 = "%s"
scores = { legibility = 5, distinctiveness = 5, balance = 5, color = 5, scalability = 5, craft = 5 }
''' % ("0" * 64, "0" * 64)
        config.write_text(text, encoding="utf-8")
        page, _ = self.lab(config)
        self.assertNotIn('value="5"', page)

    def test_D16_an_emote_lab_shows_the_emote_sizes_from_the_plan(self):
        config = write_project(self.dir, targets='["emote"]')
        page, _ = self.lab(config)
        self.assertIn("EMOTE", page)
        for size in (28, 56, 112):
            self.assertIn(f'alt="{size}px emote"', page)
        self.assertNotIn("No targets selected", page)

    def test_the_lab_exports_provenance_but_never_authority(self):
        page, _ = self.lab()
        self.assertIn('"kind": "review-lab"', page)
        self.assertIn("reviewerName", page)
        self.assertIn("declared_at", page)

    def test_a_lab_review_renders_each_frame_once_in_one_browser(self):
        seen = []

        class Counting(Disc):
            def render(self, svg, size, bg="transparent"):
                seen.append((hashlib.sha256(svg.encode()).hexdigest(), size, bg, self.color_scheme))
                return super().render(svg, size, bg)

        with mock.patch("iconflow.rasterize.Rasterizer", Counting), \
                mock.patch("iconflow.qa.Rasterizer", Counting), \
                mock.patch("iconflow.review.contact_sheet", side_effect=lambda m, out, **kw: write_png(out)):
            Disc.launches = 0
            self.lab(write_project(self.dir, targets='["web", "tauri", "electron"]'))
        self.assertEqual(len(seen), len(set(seen)), "a frame was rendered twice")
        self.assertLessEqual(Disc.launches, 2)  # one per scheme


# ----------------------------------------------------------- real Chromium

@NEEDS_CHROMIUM
class RealChromiumTests(unittest.TestCase):
    DEMO = ROOT / "demo"

    def test_D04_plan_and_render_findings_agree_under_chromium(self):
        for kwargs in (
            dict(master=self.DEMO / "master.svg", targets=("web", "tauri"), background_color="#FFF4E8"),
            dict(master=self.DEMO / "master.svg", targets=("web", "android"),
                 maskable_svg=self.DEMO / "maskable.svg", background_color="#FFF4E8"),
            dict(master=ROOT / "examples" / "detail-ladder" / "master.svg", targets=("web",)),
            dict(master=self.DEMO / "master.svg", targets=("web",), color_scheme="dark"),
        ):
            with self.subTest(kwargs=kwargs):
                inputs = AuditInputs(**kwargs)
                plain = run_audit(inputs)
                sources = capture_sources(inputs.master, inputs.targets,
                                          maskable_svg=inputs.maskable_svg)
                with RenderSession() as session:
                    r = session.rasterizer(inputs.color_scheme)
                    plan = compute_plan(inputs.master, list(inputs.targets),
                                        bg_color=inputs.background_color,
                                        color_scheme=inputs.color_scheme,
                                        maskable_svg=inputs.maskable_svg,
                                        rasterizer=r, sources=sources)
                    planned = run_audit(inputs, rasterizer=r, plan=plan, sources=sources)
                self.assertTrue(planned.audited)
                self.assertEqual([str(w) for w in plain.warnings], [str(w) for w in planned.warnings])
                self.assertEqual(plain.metrics, planned.metrics)

    def test_two_schemes_share_one_browser_and_keep_their_own_contexts(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><style>'
               'rect{fill:#000}@media (prefers-color-scheme: dark){rect{fill:#fff}}</style>'
               '<rect width="16" height="16"/></svg>')
        with RenderSession() as session:
            light = Image.open(io.BytesIO(session.rasterizer("light").render(svg, 4))).getpixel((1, 1))
            dark = Image.open(io.BytesIO(session.rasterizer("dark").render(svg, 4))).getpixel((1, 1))
            self.assertEqual(session.launches, 2)
        self.assertEqual(light[:3], (0, 0, 0))
        self.assertEqual(dark[:3], (255, 255, 255))



if __name__ == "__main__":
    unittest.main()
