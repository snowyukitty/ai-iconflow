import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from iconflow.styles import PRESETS
from scripts.verify_distribution import main, verify


ROOT = Path(__file__).resolve().parents[1]


class DistributionVerificationTests(unittest.TestCase):
    @staticmethod
    def _metadata() -> bytes:
        return b"\n".join(
            [
                b"Metadata-Version: 2.4",
                b"Name: ai-iconflow",
                b"License-Expression: Apache-2.0",
                b"License-File: LICENSE",
                b"License-File: NOTICE",
                b"License-File: TRADEMARKS.md",
                b"License-File: THIRD_PARTY_NOTICES.md",
            ]
        )

    def _wheel(
        self, names: list[str], *, metadata: bytes | None = None
    ) -> tuple[tempfile.TemporaryDirectory, Path]:
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "ai_iconflow-0.4.0-py3-none-any.whl"
        metadata = self._metadata() if metadata is None else metadata
        with zipfile.ZipFile(path, "w") as archive:
            for name in names:
                content = metadata if name.endswith("/METADATA") else b"content"
                archive.writestr(name, content)
        return directory, path

    @staticmethod
    def _required() -> list[str]:
        return [
            "iconflow/__init__.py",
            "iconflow/styles.py",
            "iconflow/resources/templates/master.svg",
            "iconflow/resources/docs/DESIGN_PLAYBOOK.md",
            "iconflow/resources/docs/STYLE_CATALOG.md",
            "iconflow/resources/docs/assets/style-gallery.png",
            *(f"iconflow/resources/presets/{preset}.svg" for preset in PRESETS),
            "ai_iconflow-0.4.0.dist-info/METADATA",
            "ai_iconflow-0.4.0.dist-info/RECORD",
            "ai_iconflow-0.4.0.dist-info/licenses/LICENSE",
            "ai_iconflow-0.4.0.dist-info/licenses/NOTICE",
            "ai_iconflow-0.4.0.dist-info/licenses/TRADEMARKS.md",
            "ai_iconflow-0.4.0.dist-info/licenses/THIRD_PARTY_NOTICES.md",
        ]

    def test_accepts_minimal_expected_wheel(self):
        directory, path = self._wheel(self._required())
        self.addCleanup(directory.cleanup)
        with contextlib.redirect_stdout(io.StringIO()):
            verify(path)

    def test_main_expands_wildcards_for_powershell(self):
        directory, path = self._wheel(self._required())
        self.addCleanup(directory.cleanup)
        with contextlib.redirect_stdout(io.StringIO()):
            code = main([str(path.parent / "*.whl")])
        self.assertEqual(code, 0)

    def test_rejects_traversal_and_generated_or_sensitive_members(self):
        for unsafe in ("../secret.txt", "work/review.png", "iconflow/private.pem"):
            with self.subTest(unsafe=unsafe):
                directory, path = self._wheel(self._required() + [unsafe])
                self.addCleanup(directory.cleanup)
                with self.assertRaisesRegex(ValueError, "unsafe|sensitive/generated"):
                    verify(path)

    def test_rejects_missing_wheel_metadata(self):
        names = [name for name in self._required() if not name.endswith("/RECORD")]
        directory, path = self._wheel(names)
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(ValueError, "METADATA and RECORD"):
            verify(path)

    def test_rejects_missing_legal_file(self):
        names = [name for name in self._required() if not name.endswith("/NOTICE")]
        directory, path = self._wheel(names)
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(ValueError, "legal file NOTICE"):
            verify(path)

    def test_rejects_wrong_license_expression(self):
        directory, path = self._wheel(
            self._required(),
            metadata=self._metadata().replace(b"Apache-2.0", b"MIT"),
        )
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(ValueError, "Apache-2.0 package metadata"):
            verify(path)

    def test_setup_scripts_install_the_open_skill_for_supported_clients(self):
        powershell = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")
        posix = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
        for skill_home in (".codex", ".claude", ".agents", ".copilot"):
            with self.subTest(skill_home=skill_home):
                self.assertIn(skill_home, powershell)
                self.assertIn(skill_home, posix)
        self.assertIn('python3 -m venv "$repo_root/.venv"', posix)
        self.assertIn('"$runner" -m iconflow setup', posix)
        self.assertNotIn(b"\r\n", (ROOT / "scripts" / "setup.sh").read_bytes())

        skill = (ROOT / "skills" / "iconflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: iconflow\n"))
        self.assertIn("license: Apache-2.0", skill)
        self.assertIn("compatibility:", skill)
        self.assertIn('version: "0.4.0"', skill)


if __name__ == "__main__":
    unittest.main()
