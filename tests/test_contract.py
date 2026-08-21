# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Agent Contract v1 (docs/AGENT_CONTRACT.md): envelopes, exit codes, demo.

Rendering is mocked wherever the contract shape is what matters; the demo
end-to-end test needs real Chromium and is gated like the other browser tests.
"""
import contextlib
import importlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from iconflow.casebook import AXES
from iconflow.cli import DEMO_FILES, _resource, main
from iconflow.config import (
    config_review_contract_digest, load_config, svg_sha256,
)
from iconflow.qa import Finding, warning_code

BUILD_MODULE = importlib.import_module("iconflow.build")


def _real(path) -> str:
    """Envelope paths are canonical; temp dirs may be symlinked (macOS) or 8.3 (Windows)."""
    return os.path.realpath(str(path))

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE_KEYS = [
    "schema", "command", "status", "exit_code", "warnings", "advisories",
    "outputs", "errors",
]
CLEAN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
    '<rect x="80" y="80" width="864" height="864" rx="200" fill="#1e82e6"/>'
    '<rect x="340" y="340" width="344" height="344" fill="#ffffff"/></svg>'
)
HAIRLINE_SVG = CLEAN_SVG.replace(
    "</svg>",
    '<path d="M200 200 L800 800" stroke="#000" stroke-width="1"/></svg>',
)


def _card_png(size: int) -> bytes:
    """A legible rounded card with a white counter: clean at every check."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    painter = ImageDraw.Draw(image)
    inset = max(1, size // 12)
    painter.rounded_rectangle(
        [inset, inset, size - inset - 1, size - inset - 1],
        radius=max(1, size // 5), fill=(30, 130, 230, 255),
    )
    third = size // 3
    painter.rectangle(
        [third, third, max(third + 1, size * 2 // 3), max(third + 1, size * 2 // 3)],
        fill=(255, 255, 255, 255),
    )
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class FakeRasterizer:
    def __init__(self, color_scheme="light"):
        self.color_scheme = color_scheme

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, _svg, size, bg="transparent"):
        return _card_png(size)


def run_json(argv: list[str]) -> tuple[int, dict, str]:
    """Run ``main`` in JSON mode; stdout must be exactly one JSON object."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    text = out.getvalue()
    envelope = json.loads(text)
    assert json.dumps(envelope) and text.strip() == json.dumps(envelope, ensure_ascii=False, indent=2)
    return code, envelope, err.getvalue()


class EnvelopeShapeTests(unittest.TestCase):
    def assert_envelope(self, envelope: dict, *, command: str, status: str, exit_code: int):
        self.assertEqual(list(envelope), ENVELOPE_KEYS)
        self.assertEqual(envelope["schema"], 1)
        self.assertEqual(envelope["command"], command)
        self.assertEqual(envelope["status"], status)
        self.assertEqual(envelope["exit_code"], exit_code)
        for key in ("warnings", "advisories", "errors"):
            for finding in envelope[key]:
                self.assertEqual(list(finding), ["code", "message"])
        if status != "error":
            self.assertEqual(envelope["errors"], [])

    def test_check_ok_envelope(self):
        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory) / "master.svg"
            master.write_text(CLEAN_SVG, encoding="utf-8")
            with mock.patch("iconflow.qa.Rasterizer", FakeRasterizer):
                code, envelope, err = run_json(["check", str(master), "--json"])
            expected_hash = svg_sha256(master)
        self.assertEqual(code, 0)
        self.assert_envelope(envelope, command="check", status="ok", exit_code=0)
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["advisories"], [])
        outputs = dict(envelope["outputs"])
        outputs["source"] = _real(outputs["source"])
        self.assertEqual(outputs, {
            "source": _real(master),
            "source_sha256": expected_hash,
            "tray_source": None,
        })
        self.assertIn("OK — no automated warnings", err)

    def test_check_blocked_envelope_carries_stable_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory) / "master.svg"
            master.write_text(HAIRLINE_SVG, encoding="utf-8")
            with mock.patch("iconflow.qa.Rasterizer", FakeRasterizer):
                code, envelope, err = run_json(["check", str(master), "--json"])
        self.assertEqual(code, 1)
        self.assert_envelope(envelope, command="check", status="blocked", exit_code=1)
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["stroke-floor"])
        self.assertIn("stroke-width=1 is very thin", envelope["warnings"][0]["message"])
        self.assertIn("1 warning(s)", err)

    def test_check_advisories_alone_do_not_block(self):
        advisory = Finding("tray-template-featureless", "template kept nothing")
        with tempfile.TemporaryDirectory() as directory:
            master = Path(directory) / "master.svg"
            master.write_text(CLEAN_SVG, encoding="utf-8")
            tray = Path(directory) / "tray.svg"
            tray.write_text(CLEAN_SVG, encoding="utf-8")
            with mock.patch("iconflow.qa.Rasterizer", FakeRasterizer), \
                 mock.patch("iconflow.qa.tray_template_warnings", return_value=[advisory]):
                code, envelope, _ = run_json([
                    "check", str(master), "--tray-svg", str(tray), "--json",
                ])
                human = io.StringIO()
                with contextlib.redirect_stdout(human):
                    human_code = main(["check", str(master), "--tray-svg", str(tray)])
            self.assertEqual(_real(envelope["outputs"]["tray_source"]), _real(tray))
        self.assertEqual(code, 0)
        self.assertEqual(human_code, 0)
        self.assertEqual(envelope["status"], "ok")
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(
            envelope["advisories"],
            [{"code": "tray-template-featureless", "message": "template kept nothing"}],
        )
        self.assertIn("tray template advisory", human.getvalue())

    def test_check_error_envelope_for_missing_file(self):
        code, envelope, err = run_json(["check", "does-not-exist.svg", "--json"])
        self.assertEqual(code, 2)
        self.assert_envelope(envelope, command="check", status="error", exit_code=2)
        self.assertEqual(envelope["errors"][0]["code"], "file-not-found")
        self.assertIn("file not found", err)

    def test_qa_findings_expose_the_documented_codes(self):
        self.assertEqual(warning_code(Finding("viewbox", "x")), "viewbox")
        self.assertEqual(
            warning_code("Low contrast on WHITE at 16px — mark may be invisible on light UI."),
            "contrast",
        )
        self.assertEqual(warning_code("unclassified prose"), "qa-warning")
        self.assertEqual(json.loads(json.dumps([Finding("contrast", "msg")])), ["msg"])

    def test_doctor_json_shape_without_browser(self):
        code, envelope, err = run_json(["doctor", "--no-browser", "--json"])
        self.assertEqual(code, 0)
        self.assert_envelope(envelope, command="doctor", status="ok", exit_code=0)
        outputs = envelope["outputs"]
        self.assertEqual(list(outputs), ["checks", "chromium"])
        self.assertEqual(outputs["chromium"], "SKIPPED")
        names = [check["name"] for check in outputs["checks"]]
        self.assertIn("Packaged resources", names)
        self.assertIn("Chromium runtime", names)
        for check in outputs["checks"]:
            self.assertEqual(list(check), ["name", "status", "detail", "fix"])
            self.assertIn(check["status"], {"PASS", "WARN", "FAIL"})
            self.assertIsNone(check["fix"])
        self.assertIn("IconFlow is ready", err)

    def test_doctor_fail_is_blocked_with_a_pasteable_fix(self):
        from iconflow.config import IconFlowConfig, write_config
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "iconflow.toml"
            write_config(IconFlowConfig(source=config_path, master="missing.svg"))
            code, envelope, _ = run_json([
                "doctor", "--config", str(config_path), "--no-browser", "--json",
            ])
        self.assertEqual(code, 1)
        self.assert_envelope(envelope, command="doctor", status="blocked", exit_code=1)
        failed = [c for c in envelope["outputs"]["checks"] if c["status"] == "FAIL"]
        self.assertEqual([c["name"] for c in failed], ["Master SVG"])
        self.assertIn("-m iconflow new", failed[0]["fix"])
        self.assertEqual(envelope["warnings"][0]["code"], "master-svg")

    def test_doctor_chromium_failure_names_the_exact_setup_command(self):
        import sys
        with mock.patch("playwright.sync_api.sync_playwright", side_effect=RuntimeError("no browser")):
            code, envelope, _ = run_json(["doctor", "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(envelope["outputs"]["chromium"], "FAIL")
        chromium = [c for c in envelope["outputs"]["checks"] if c["name"] == "Chromium runtime"][0]
        self.assertEqual(chromium["status"], "FAIL")
        self.assertTrue(chromium["fix"].endswith("-m iconflow setup"))
        self.assertIn(Path(sys.executable).name, chromium["fix"])

    def test_usage_errors_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["check", "master.svg", "--no-such-flag"])
        self.assertEqual(raised.exception.code, 2)


class DemoFamilyFixture(unittest.TestCase):
    """Copies the packaged demo family into a temp dir without rendering."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "family"
        self.dir.mkdir()
        for name in DEMO_FILES:
            (self.dir / name).write_bytes(_resource("demo", name).read_bytes())
        self.config = self.dir / "iconflow.toml"
        self.receipt = self.dir / "master-review.json"
        self.master = self.dir / "master.svg"

    def ship(self, *extra: str) -> tuple[int, dict, str]:
        return run_json([
            "ship", "--config", str(self.config), "--review", str(self.receipt), "--json", *extra,
        ])


class ShipEnvelopeTests(DemoFamilyFixture):
    def test_packaged_demo_family_is_complete_and_self_bound(self):
        for name in DEMO_FILES:
            self.assertTrue(_resource("demo", name).is_file(), name)
        config = load_config(self.config)
        self.assertNotIn("..", config.casebook)
        self.assertFalse(Path(config.master).is_absolute())
        self.assertEqual(config.review_source_sha256, svg_sha256(config.master_path))
        self.assertEqual(config.review_contract_sha256, config_review_contract_digest(config))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt["source_sha256"], config.review_source_sha256)
        self.assertEqual(receipt["contract_sha256"], config.review_contract_sha256)
        # The demo copies must stay byte-identical to the brand family.
        for name in DEMO_FILES:
            if name != "iconflow.toml":
                self.assertEqual(
                    (ROOT / "demo" / name).read_bytes(), (ROOT / "brand" / name).read_bytes(), name,
                )

    def test_stale_source_is_blocked_with_receipt_stale_source(self):
        self.master.write_text(
            self.master.read_text(encoding="utf-8").replace("</svg>", "<!-- edited --></svg>"),
            encoding="utf-8",
        )
        with mock.patch("iconflow.qa.check") as check:
            code, envelope, err = self.ship()
        self.assertEqual(code, 1)
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["receipt-stale-source"])
        self.assertEqual(envelope["outputs"], {})
        self.assertIn("stale", err)
        check.assert_not_called()

    def test_stale_contract_not_ready_and_score_floor_codes(self):
        cases = {
            "receipt-stale-contract": lambda: self.config.write_text(
                self.config.read_text(encoding="utf-8").replace(
                    'theme_color = "#191A20"', 'theme_color = "#102030"',
                ),
                encoding="utf-8",
            ),
            "receipt-not-ready": lambda: self._edit_receipt(status="blocked"),
            "score-below-floor": lambda: self._edit_receipt(
                scores={**{axis: 4 for axis in AXES}, "craft": 3},
            ),
        }
        for expected, mutate in cases.items():
            with self.subTest(code=expected):
                self.setUp()
                mutate()
                with mock.patch("iconflow.qa.check") as check:
                    code, envelope, _ = self.ship()
                self.assertEqual(code, 1)
                self.assertEqual(envelope["status"], "blocked")
                self.assertEqual([w["code"] for w in envelope["warnings"]], [expected])
                check.assert_not_called()

    def _edit_receipt(self, **fields):
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt.update(fields)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

    def test_qa_warnings_block_with_qa_warnings_and_finding_codes(self):
        finding = Finding("stroke-floor", "stroke-width=1 is very thin")
        with mock.patch("iconflow.qa.check", return_value=[finding]), \
             mock.patch.object(BUILD_MODULE, "build") as build:
            code, envelope, err = self.ship()
        self.assertEqual(code, 1)
        self.assertEqual(
            [w["code"] for w in envelope["warnings"]], ["qa-warnings", "stroke-floor"],
        )
        self.assertIn("SHIP BLOCKED", err)
        build.assert_not_called()

    def test_malformed_receipt_is_a_configuration_error(self):
        self.receipt.write_text("{not json", encoding="utf-8")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 2)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "config")
        self.assertEqual(envelope["warnings"], [])

    def test_successful_ship_reports_files_receipt_scores_and_packet(self):
        out = self.dir / "icon-out"
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch.object(BUILD_MODULE, "build", return_value=["favicon.svg", "tray/tray.png"]):
            code, envelope, err = self.ship("--out", str(out))
        self.assertEqual(code, 0)
        self.assertEqual(envelope["status"], "ok")
        outputs = envelope["outputs"]
        self.assertEqual(
            [_real(path) for path in outputs["files"]],
            [_real(out / "favicon.svg"), _real(out / "tray/tray.png")],
        )
        self.assertEqual(_real(outputs["receipt"]), _real(self.receipt))
        self.assertEqual(outputs["source_sha256"], svg_sha256(self.master))
        self.assertEqual(outputs["contract_sha256"], load_config(self.config).review_contract_sha256)
        self.assertEqual(outputs["scores"]["distinctiveness"], 5)
        self.assertEqual(list(outputs["toolchain"]), ["iconflow", "chromium", "pillow"])
        self.assertTrue(outputs["toolchain"]["iconflow"])
        self.assertIsNone(outputs["artifacts"])
        self.assertIsNone(outputs["reviewer"])
        self.assertIn("SHIP PASSED", err)

    def test_receipt_packet_fields_are_recorded_not_required(self):
        self._edit_receipt(
            toolchain={"iconflow": "0.5.0"},
            artifacts={"review_png_sha256": "ab" * 32},
            reviewer={"kind": "agent", "name": "fixture", "declared_at": "2026-08-21T00:00:00Z"},
            unknown_future_key={"ignored": True},
        )
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch.object(BUILD_MODULE, "build", return_value=[]):
            code, envelope, _ = self.ship()
        self.assertEqual(code, 0)
        self.assertEqual(envelope["outputs"]["artifacts"], {"review_png_sha256": "ab" * 32})
        self.assertEqual(envelope["outputs"]["reviewer"]["kind"], "agent")

        self._edit_receipt(reviewer="not an object")
        code, envelope, _ = self.ship()
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "config")


class ReviewEnvelopeTests(DemoFamilyFixture):
    def test_review_json_outputs_and_receipt_template_round_trip_into_ship(self):
        sheet = self.dir / "review.png"
        html = self.dir / "review.html"
        template = self.dir / "agent-receipt.json"
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch("iconflow.qa.tray_template_warnings", return_value=[]), \
             mock.patch("iconflow.review.contact_sheet", return_value=sheet), \
             mock.patch("iconflow.review.interactive_review", return_value=html):
            code, envelope, err = run_json([
                "review", "--config", str(self.config), "--out", str(sheet),
                "--html", str(html), "--receipt-template", str(template), "--json",
            ])
        self.assertEqual(code, 0)
        self.assertEqual(envelope["status"], "ok")
        config = load_config(self.config)
        outputs = dict(envelope["outputs"])
        for key in ("sheet", "html", "receipt_template"):
            outputs[key] = _real(outputs[key])
        self.assertEqual(outputs, {
            "sheet": _real(sheet),
            "html": _real(html),
            "receipt_template": _real(template),
            "source_sha256": config.review_source_sha256,
            "contract_sha256": config.review_contract_sha256,
            "targets": ["web", "tauri", "electron", "tray"],
        })
        self.assertIn("Review sheet ->", err)

        draft = json.loads(template.read_text(encoding="utf-8"))
        self.assertEqual(draft["status"], "unscored")
        self.assertEqual(draft["scores"], {})
        self.assertEqual(draft["contract_sha256"], config.review_contract_sha256)
        draft.update({"scores": {axis: 4 for axis in AXES}, "status": "ready", "notes": "agent"})
        template.write_text(json.dumps(draft), encoding="utf-8")
        with mock.patch("iconflow.qa.check", return_value=[]), \
             mock.patch.object(BUILD_MODULE, "build", return_value=[]):
            code, envelope, _ = run_json([
                "ship", "--config", str(self.config), "--review", str(template), "--json",
            ])
        self.assertEqual(code, 0)
        self.assertEqual(_real(envelope["outputs"]["receipt"]), _real(template))

    def test_review_with_qa_warnings_is_blocked_but_still_renders(self):
        sheet = self.dir / "review.png"
        warning = Finding("contrast", "Low contrast on WHITE at 16px — mark may be invisible on light UI.")
        with mock.patch("iconflow.qa.check", return_value=[warning]), \
             mock.patch("iconflow.qa.tray_template_warnings", return_value=[]), \
             mock.patch("iconflow.review.contact_sheet", return_value=sheet) as contact:
            code, envelope, _ = run_json([
                "review", "--config", str(self.config), "--out", str(sheet), "--json",
            ])
        self.assertEqual(code, 1)
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["contrast"])
        self.assertEqual(envelope["outputs"]["html"], None)
        self.assertEqual(envelope["outputs"]["receipt_template"], None)
        contact.assert_called_once()

    def test_review_config_error_envelope(self):
        code, envelope, _ = run_json(["review", "--config", str(self.dir / "nope.toml"), "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "config")


class DemoCommandTests(unittest.TestCase):
    def test_demo_refuses_an_existing_directory_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "taken"
            existing.mkdir()
            (existing / "keep.txt").write_text("user work", encoding="utf-8")
            code, envelope, err = run_json(["demo", "--out", str(existing), "--json"])
            self.assertEqual((existing / "keep.txt").read_text(encoding="utf-8"), "user work")
            self.assertFalse((existing / "master.svg").exists())
        self.assertEqual(code, 2)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["errors"][0]["code"], "usage")
        self.assertIn("--force", err)

    def test_demo_stops_at_the_first_failing_step_and_reports_it(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "demo"
            with mock.patch("iconflow.cli._cmd_doctor", side_effect=RuntimeError("no browser")):
                code, envelope, _ = run_json(["demo", "--out", str(out), "--json"])
            self.assertTrue((out / "master.svg").is_file())
        self.assertEqual(code, 2)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["outputs"]["steps"], [
            {"name": "doctor", "status": "error", "exit_code": 2},
        ])
        self.assertEqual(envelope["outputs"]["files"], [])
        self.assertEqual(envelope["errors"][0]["code"], "runtime")


@unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
class DemoEndToEndTests(unittest.TestCase):
    def test_demo_proves_the_engine_and_then_fails_closed_on_an_edited_master(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "iconflow-demo"
            code, envelope, err = run_json(["demo", "--out", str(out), "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual(envelope["status"], "ok")
            self.assertEqual(
                [step["name"] for step in envelope["outputs"]["steps"]],
                ["doctor", "check", "review", "ship"],
            )
            self.assertTrue(all(step["exit_code"] == 0 for step in envelope["outputs"]["steps"]))
            self.assertEqual(_real(envelope["outputs"]["out"]), _real(out))
            self.assertEqual(_real(envelope["outputs"]["receipt"]), _real(out / "master-review.json"))
            self.assertEqual(len(envelope["outputs"]["files"]), 23)
            self.assertTrue(all(Path(path).is_file() for path in envelope["outputs"]["files"]))
            self.assertTrue((out / "review.png").is_file())
            self.assertTrue((out / "review.html").is_file())
            self.assertTrue(all(envelope["outputs"]["artifacts"].values()))
            self.assertIn("DEMO PASSED", err)

            master = out / "master.svg"
            master.write_text(
                master.read_text(encoding="utf-8").replace("</svg>", "<!-- edited --></svg>"),
                encoding="utf-8",
            )
            code, envelope, _ = run_json([
                "ship", "--config", str(out / "iconflow.toml"),
                "--review", str(out / "master-review.json"), "--json",
            ])
            self.assertEqual(code, 1)
            self.assertEqual([w["code"] for w in envelope["warnings"]], ["receipt-stale-source"])

            # --force re-materializes the family over the edited copy, so it passes again.
            code, envelope, _ = run_json(["demo", "--out", str(out), "--force", "--json"])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()


class UsageErrorEnvelopeTests(unittest.TestCase):
    def test_usage_error_under_json_still_emits_one_envelope(self):
        import io
        import contextlib
        from iconflow.cli import main

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["check", "--json", "--no-such-flag"])
        self.assertEqual(code, 2)
        envelope = json.loads(out.getvalue())
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["command"], "check")
        self.assertEqual(envelope["exit_code"], 2)
        self.assertEqual(envelope["errors"][0]["code"], "usage")
        self.assertIn("usage", err.getvalue().lower())
        # Without --json argparse keeps its native behaviour.
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(io.StringIO()):
            main(["check", "--no-such-flag"])
        self.assertEqual(raised.exception.code, 2)
