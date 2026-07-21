import contextlib
import hashlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from iconflow.casebook import AXES
from iconflow.cli import main
from iconflow.config import (
    ConfigError,
    IconFlowConfig,
    load_config,
    load_review_receipt,
    review_build_contract,
    validate_ship_scores,
    write_config,
)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    @staticmethod
    def _receipt_build(config):
        return review_build_contract(
            theme_color=config.theme_color,
            background_color=config.background_color,
            electron_radius=config.electron_radius,
            tray_template_mode=config.tray_template_mode,
            color_scheme=config.color_scheme,
            tray_source_sha256=None,
        )

    def test_config_roundtrip_preserves_brief_and_resolves_project_paths(self):
        path = self.dir / "project" / "iconflow.toml"
        source = IconFlowConfig(
            source=path,
            name="Flow Lab",
            master="brand/master.svg",
            output="icons",
            app_intent="Turn app intent into a proven icon family",
            user_job="Ship one source to every surface",
            essence="proof",
            personality=["precise", "editorial"],
            palette=["graphite", "signal-coral"],
            cliches=["AI sparkles", "generic checkmark"],
            signature_device="proof gate with pixel step",
            device_family="Proof Gate",
            device_detail="offset square crossed by a continuous rail",
            concept_lens="User Journey",
            targets=["web", "electron", "tray"],
            tray_svg="brand/tray.svg",
            tray_template_mode="contrast",
            review_status="approved",
            review_source_sha256="a" * 64,
            review_scores={axis: 4 for axis in AXES},
        )
        write_config(source)
        loaded = load_config(path)
        self.assertEqual(loaded.app_intent, source.app_intent)
        self.assertEqual(loaded.personality, ["precise", "editorial"])
        self.assertEqual(loaded.cliches, ["AI sparkles", "generic checkmark"])
        self.assertEqual(loaded.device_family, "proof-gate")
        self.assertEqual(loaded.concept_lens, "user-journey")
        self.assertEqual(loaded.targets, ["web", "electron", "tray"])
        self.assertEqual(loaded.tray_svg_path, (path.parent / "brand/tray.svg").resolve())
        self.assertEqual(loaded.tray_template_mode, "contrast")
        self.assertEqual(loaded.review_source_sha256, "a" * 64)
        self.assertEqual(loaded.master_path, (path.parent / "brand/master.svg").resolve())
        self.assertEqual(loaded.output_path, (path.parent / "icons").resolve())

    def test_config_refuses_overwrite_and_bad_target(self):
        path = self.dir / "iconflow.toml"
        write_config(IconFlowConfig(source=path))
        with self.assertRaises(ConfigError):
            write_config(IconFlowConfig(source=path))
        text = path.read_text(encoding="utf-8").replace(
            'targets = ["web"]', 'targets = ["web", "typo"]'
        )
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "unknown build target"):
            load_config(path)

        color_path = self.dir / "bad-color.toml"
        write_config(IconFlowConfig(source=color_path))
        color_path.write_text(
            color_path.read_text(encoding="utf-8").replace(
                'background_color = "#ffffff"',
                'background_color = "#ffffff00"',
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ConfigError, "fully opaque"):
            load_config(color_path)

    def test_ship_scores_require_every_axis_at_four_or_better(self):
        with self.assertRaisesRegex(ConfigError, "incomplete"):
            validate_ship_scores({"legibility": 4})
        scores = {axis: 4 for axis in AXES}
        scores["distinctiveness"] = 3
        with self.assertRaisesRegex(ConfigError, "distinctiveness=3"):
            validate_ship_scores(scores)
        validate_ship_scores({axis: 4 for axis in AXES})

    def test_review_receipt_is_bound_to_source_project_and_targets(self):
        master = self.dir / "master.svg"
        svg = '<svg viewBox="0 0 1024 1024"/>'
        master.write_text(svg, encoding="utf-8")
        config = IconFlowConfig(
            source=self.dir / "iconflow.toml",
            name="Proof App",
            master="master.svg",
            targets=["web", "tray"],
        )
        receipt_path = self.dir / "review.json"
        receipt = {
            "schema": 1,
            "source_sha256": hashlib.sha256(svg.encode("utf-8")).hexdigest(),
            "project": "Proof App",
            "targets": ["web", "tray"],
            "build": self._receipt_build(config),
            "warnings": [],
            "scores": {axis: 4 for axis in AXES},
            "notes": "The mark survives at 16px.",
            "status": "ready",
        }
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        loaded = load_review_receipt(receipt_path, config)
        self.assertEqual(loaded.targets, ("web", "tray"))
        self.assertEqual(loaded.scores["distinctiveness"], 4)

        receipt["targets"] = ["web"]
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "target mismatch"):
            load_review_receipt(receipt_path, config)

        receipt["targets"] = ["web", "tray"]
        receipt["build"]["electron_radius"] = 0.18
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "build contract mismatch"):
            load_review_receipt(receipt_path, config)

    def test_review_receipt_rejects_stale_source_and_warnings(self):
        master = self.dir / "master.svg"
        svg = '<svg viewBox="0 0 1024 1024"/>'
        master.write_text(svg, encoding="utf-8")
        config = IconFlowConfig(source=self.dir / "iconflow.toml", master="master.svg")
        path = self.dir / "review.json"
        value = {
            "schema": 1,
            "source_sha256": "0" * 64,
            "project": "App",
            "targets": ["web"],
            "build": self._receipt_build(config),
            "warnings": [],
            "scores": {axis: 4 for axis in AXES},
            "status": "ready",
        }
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "stale"):
            load_review_receipt(path, config)

        value["source_sha256"] = hashlib.sha256(svg.encode("utf-8")).hexdigest()
        value["warnings"] = ["unsafe detail"]
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "automated warnings"):
            load_review_receipt(path, config)

        del value["warnings"]
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "warnings must be an array"):
            load_review_receipt(path, config)

    def test_init_cli_writes_all_brief_sections(self):
        path = self.dir / "iconflow.toml"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main([
                "init", "--out", str(path), "--name", "Proof App",
                "--app-intent", "Prove icons", "--user-job", "Ship safely",
                "--essence", "proof", "--targets", "web,tray",
                "--palette", "graphite,coral", "--personality", "precise,warm",
                "--cliche", "sparkles", "--signature-device", "proof gate",
            ])
        self.assertEqual(code, 0)
        loaded = load_config(path)
        self.assertEqual(loaded.name, "Proof App")
        self.assertEqual(loaded.targets, ["web", "tray"])
        self.assertEqual(loaded.palette, ["graphite", "coral"])
        self.assertIn("Review Lab receipt", stdout.getvalue())

    def _ship_config(self, scores):
        master = self.dir / "master.svg"
        svg = '<svg viewBox="0 0 1024 1024"/>'
        master.write_text(svg, encoding="utf-8")
        path = self.dir / "iconflow.toml"
        write_config(IconFlowConfig(
            source=path,
            master="master.svg",
            output="icons",
            targets=["web"],
            review_status="approved",
            review_source_sha256=hashlib.sha256(svg.encode("utf-8")).hexdigest(),
            review_scores=scores,
        ))
        return path

    def test_ship_blocks_incomplete_scores_before_qa(self):
        path = self._ship_config({"legibility": 4})
        with mock.patch("iconflow.qa.check") as check, \
             contextlib.redirect_stderr(io.StringIO()):
            code = main(["ship", "--config", str(path)])
        self.assertEqual(code, 2)
        check.assert_not_called()

    def test_ship_requires_explicit_approval_without_receipt(self):
        path = self._ship_config({axis: 4 for axis in AXES})
        text = path.read_text(encoding="utf-8").replace(
            'status = "approved"', 'status = "pending"'
        )
        path.write_text(text, encoding="utf-8")
        with mock.patch("iconflow.qa.check") as check, \
             contextlib.redirect_stderr(io.StringIO()):
            code = main(["ship", "--config", str(path)])
        self.assertEqual(code, 2)
        check.assert_not_called()

    def test_approved_fallback_requires_bound_source_hash(self):
        path = self._ship_config({axis: 4 for axis in AXES})
        text = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(
            (self.dir / "master.svg").read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        text = text.replace(
            f'source_sha256 = "{digest}"',
            'source_sha256 = ""',
        )
        path.write_text(text, encoding="utf-8")
        with mock.patch("iconflow.qa.check") as check, \
             contextlib.redirect_stderr(io.StringIO()):
            code = main(["ship", "--config", str(path)])
        self.assertEqual(code, 2)
        check.assert_not_called()

    def test_ready_receipt_can_approve_and_bind_ship(self):
        path = self._ship_config({})
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                'status = "approved"', 'status = "pending"'
            ),
            encoding="utf-8",
        )
        master = self.dir / "master.svg"
        config = load_config(path)
        receipt = self.dir / "master-review.json"
        receipt.write_text(json.dumps({
            "schema": 1,
            "source_sha256": hashlib.sha256(
                master.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest(),
            "project": config.name,
            "targets": config.targets,
            "build": self._receipt_build(config),
            "warnings": [],
            "scores": {axis: 4 for axis in AXES},
            "notes": "reviewed",
            "status": "ready",
        }), encoding="utf-8")
        qa_module = importlib.import_module("iconflow.qa")
        build_module = importlib.import_module("iconflow.build")
        with mock.patch.object(qa_module, "check", return_value=[]), \
             mock.patch.object(build_module, "build", return_value=["favicon.svg"]) as build, \
             contextlib.redirect_stdout(io.StringIO()):
            code = main([
                "ship", "--config", str(path), "--review", str(receipt),
            ])
        self.assertEqual(code, 0)
        build.assert_called_once()

    def test_ship_blocks_automated_warning(self):
        path = self._ship_config({axis: 4 for axis in AXES})
        qa_module = importlib.import_module("iconflow.qa")
        build_module = importlib.import_module("iconflow.build")
        with mock.patch.object(qa_module, "check", return_value=["too generic"]), \
             mock.patch.object(build_module, "build") as build, \
             contextlib.redirect_stderr(io.StringIO()):
            code = main(["ship", "--config", str(path)])
        self.assertEqual(code, 1)
        build.assert_not_called()

    def test_ship_builds_only_after_both_gates_pass(self):
        path = self._ship_config({axis: 4 for axis in AXES})
        qa_module = importlib.import_module("iconflow.qa")
        build_module = importlib.import_module("iconflow.build")
        with mock.patch.object(qa_module, "check", return_value=[]), \
             mock.patch.object(build_module, "build", return_value=["favicon.svg"]) as build, \
             contextlib.redirect_stdout(io.StringIO()):
            code = main(["ship", "--config", str(path)])
        self.assertEqual(code, 0)
        build.assert_called_once()
        self.assertEqual(Path(build.call_args.args[0]), self.dir / "master.svg")
        self.assertEqual(Path(build.call_args.args[1]), self.dir / "icons")


if __name__ == "__main__":
    unittest.main()
