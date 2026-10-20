# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Developer-experience seeds (docs/ISSUE_SEEDS.md) and target detection."""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from iconflow import cli
from iconflow.config import load_config
from iconflow.detect import detect_targets

ROOT = Path(__file__).resolve().parents[1]


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class SeedTests(unittest.TestCase):
    def test_help_ends_with_the_exit_code_matrix(self):
        code, out, _ = run(["--help"])
        self.assertEqual(code, 0)
        tail = out.strip().splitlines()[-4:]
        self.assertIn("exit codes", tail[0])
        self.assertTrue(tail[1].strip().startswith("0 "))
        self.assertTrue(tail[2].strip().startswith("1 "))
        self.assertTrue(tail[3].strip().startswith("2 "))

    def test_chromium_fix_is_specific_to_the_platform(self):
        self.assertIn("--with-deps", cli.chromium_fix("python", "linux"))
        self.assertIn("sudo", cli.chromium_fix("python", "linux"))
        for platform in ("win32", "darwin"):
            self.assertEqual(cli.chromium_fix("python", platform), "python -m iconflow setup")

    def test_PF13_fixes_are_lines_a_shell_can_run(self):
        import shlex

        linux = cli.chromium_fix("/usr/bin/python3", "linux")
        command, _, comment = linux.partition("  # ")
        self.assertEqual(shlex.split(command)[-1], "chromium")
        self.assertIn("sudo", comment)
        # POSIX: single quotes keep spaces and expansions literal.
        for path in ("/opt/my env/bin/python", "/home/a$b/python", "/x/it's/python"):
            with self.subTest(path=path):
                self.assertEqual(shlex.split(cli._shell_command(path, "darwin")), [path])
        self.assertEqual(cli._shell_command("/usr/bin/python3", "linux"), "/usr/bin/python3")
        # Windows: PowerShell single-quoted literals (no $ or backquote
        # expansion, '' for an apostrophe) and the call operator (IR11).
        self.assertEqual(cli._shell_command(r"C:\Program Files\Python\python.exe", "win32"),
                         "& 'C:\\Program Files\\Python\\python.exe'")
        self.assertEqual(cli._shell_command(r"C:\Python\python.exe", "win32"), r"C:\Python\python.exe")
        self.assertEqual(cli._shell_quote(r"C:\Users\a$b\My Env", "win32"), r"'C:\Users\a$b\My Env'")
        self.assertEqual(cli._shell_quote("C:\\x`y", "win32"), "'C:\\x`y'")
        self.assertEqual(cli._shell_quote(r"C:\it's", "win32"), r"'C:\it''s'")

    def test_path_hint_only_when_the_command_is_missing(self):
        self.assertIsNone(cli.path_hint("win32", which=lambda _name: "C:/bin/iconflow.exe"))
        hint = cli.path_hint("win32", which=lambda _name: None)
        self.assertIn("pipx ensurepath", hint["fix"])
        self.assertIn("uv tool update-shell", hint["fix"])

    def test_doctor_reports_the_path_hint_as_warn_never_fail(self):
        from unittest import mock

        with mock.patch("shutil.which", return_value=None):
            code, out, _ = run(["doctor", "--no-browser", "--json"])
        envelope = json.loads(out)
        hint = [c for c in envelope["outputs"]["checks"] if c["name"] == "iconflow command"]
        self.assertEqual(hint[0]["status"], "WARN")
        self.assertNotIn("iconflow-command", {w["code"] for w in envelope["warnings"]})

    def test_styles_json_example_in_examples_readme_runs(self):
        text = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
        snippet = re.search(r"```python\n(import json, subprocess.*?)```", text, re.S).group(1)
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            result = subprocess.run(
                [sys.executable, "-c", snippet], cwd=tmp, env=env,
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            made = sorted(p.name for p in (Path(tmp) / "work" / "my-app").glob("*.svg"))
        self.assertTrue(made)
        self.assertIn("flat-geometric.svg", made)

    def test_case_pr_template_names_how_to_prove_each_box(self):
        text = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE" / "case.md").read_text(encoding="utf-8")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("- [ ]"):
                self.assertTrue(lines[index + 1].strip().startswith("<!-- prove:"), line)


class DetectTests(unittest.TestCase):
    def project(self, files: dict[str, str]) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, body in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return root

    def targets(self, files):
        return [item.target for item in detect_targets(self.project(files))]

    def test_tauri_with_tray_and_android(self):
        self.assertEqual(self.targets({
            "src-tauri/tauri.conf.json": '{"app": {"trayIcon": {"iconPath": "icons/tray.png"}}}',
            "src-tauri/gen/android/app/build.gradle.kts": "",
            "package.json": '{"devDependencies": {"vite": "5"}}',
            "index.html": "<!doctype html>",
        }), ["web", "tauri", "tray", "android"])

    def test_electron_with_a_tray(self):
        self.assertEqual(self.targets({
            "package.json": '{"devDependencies": {"electron": "31", "electron-builder": "24"}}',
            "main.js": "const { Tray } = require('electron'); new Tray(icon)",
        }), ["electron", "tray"])

    def test_pwa_site(self):
        self.assertEqual(self.targets({
            "package.json": '{"dependencies": {"next": "14"}, "devDependencies": {"next-pwa": "5"}}',
            "public/manifest.json": "{}",
        }), ["web", "pwa"])

    def test_capacitor_android(self):
        self.assertIn("android", self.targets({"capacitor.config.ts": "export default {}"}))

    def test_nothing_detected_proposes_nothing(self):
        self.assertEqual(self.targets({"README.md": "hello"}), [])

    def test_init_auto_writes_the_detected_targets(self):
        root = self.project({"src-tauri/tauri.conf.json": "{}"})
        code, out, _ = run(["init", "--out", str(root / "iconflow.toml")])
        self.assertEqual(code, 0)
        self.assertIn("src-tauri/tauri.conf.json exists", out)
        self.assertEqual(load_config(root / "iconflow.toml").targets, ["tauri"])

    def test_init_without_evidence_keeps_the_old_web_default(self):
        root = self.project({})
        run(["init", "--out", str(root / "iconflow.toml")])
        self.assertEqual(load_config(root / "iconflow.toml").targets, ["web"])

    def test_explicit_targets_skip_detection(self):
        root = self.project({"src-tauri/tauri.conf.json": "{}"})
        run(["init", "--out", str(root / "iconflow.toml"), "--targets", "web,android"])
        self.assertEqual(load_config(root / "iconflow.toml").targets, ["web", "android"])


if __name__ == "__main__":
    unittest.main()
