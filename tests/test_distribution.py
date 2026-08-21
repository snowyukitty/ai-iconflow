# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from iconflow.styles import PRESETS
from scripts.verify_distribution import DEMO_FILES, main, verify


ROOT = Path(__file__).resolve().parents[1]


class DistributionVerificationTests(unittest.TestCase):
    @staticmethod
    def _metadata() -> bytes:
        from scripts.verify_distribution import LEGAL_FILES, LICENSE_EXPRESSION

        return b"\n".join(
            [
                b"Metadata-Version: 2.4",
                b"Name: ai-iconflow",
                f"License-Expression: {LICENSE_EXPRESSION}".encode(),
                *(f"License-File: {name}".encode() for name in LEGAL_FILES),
            ]
        )

    def _wheel(
        self, names: list[str], *, metadata: bytes | None = None
    ) -> tuple[tempfile.TemporaryDirectory, Path]:
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "ai_iconflow-0.5.0-py3-none-any.whl"
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
            "iconflow/resources/docs/AGENT_CONTRACT.md",
            "iconflow/resources/docs/STYLE_CATALOG.md",
            "iconflow/resources/docs/assets/style-gallery.png",
            *(f"iconflow/resources/presets/{preset}.svg" for preset in PRESETS),
            *(f"iconflow/resources/demo/{name}" for name in DEMO_FILES),
            "iconflow/resources/skill/SKILL.md",
            "iconflow/resources/skill/agents/openai.yaml",
            "iconflow/resources/skill/LICENSE",
            "iconflow/resources/docs/LICENSE",
            "iconflow/resources/templates/LICENSE",
            "ai_iconflow-0.5.0.dist-info/METADATA",
            "ai_iconflow-0.5.0.dist-info/RECORD",
            "ai_iconflow-0.5.0.dist-info/licenses/LICENSE",
            "ai_iconflow-0.5.0.dist-info/licenses/NOTICE",
            "ai_iconflow-0.5.0.dist-info/licenses/TRADEMARKS.md",
            "ai_iconflow-0.5.0.dist-info/licenses/THIRD_PARTY_NOTICES.md",
            "ai_iconflow-0.5.0.dist-info/licenses/LICENSES.md",
            "ai_iconflow-0.5.0.dist-info/licenses/licenses/CC0-1.0.txt",
            "ai_iconflow-0.5.0.dist-info/licenses/licenses/CC-BY-SA-4.0.txt",
            "ai_iconflow-0.5.0.dist-info/licenses/licenses/CC-BY-4.0.txt",
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
        """The declared expression has to name every licence the wheel ships."""
        directory, path = self._wheel(
            self._required(),
            metadata=self._metadata().replace(
                b"Apache-2.0 AND CC0-1.0", b"MIT AND CC0-1.0"
            ),
        )
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(ValueError, "licence metadata"):
            verify(path)

    def test_rejects_dropping_a_licence_from_the_expression(self):
        """A wheel carrying CC BY-SA docs may not claim to be Apache-2.0 only."""
        directory, path = self._wheel(
            self._required(),
            metadata=self._metadata().replace(
                b"Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND CC-BY-4.0",
                b"Apache-2.0",
            ),
        )
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(ValueError, "licence metadata"):
            verify(path)

    def test_setup_scripts_delegate_skill_deployment_to_the_cli(self):
        """One installer, so a wheel and a checkout deploy identical files.

        The discovery roots used to be duplicated in two shell scripts, which is
        exactly where they drift; `iconflow skill install` now owns them and the
        scripts must not name a path of their own.
        """
        powershell = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")
        posix = (ROOT / "scripts" / "setup.sh").read_text(encoding="utf-8")
        self.assertIn("-m iconflow skill install", powershell)
        self.assertIn("-m iconflow skill install", posix)
        for skill_home in (".claude", ".agents", ".copilot", ".codex"):
            with self.subTest(skill_home=skill_home):
                self.assertNotIn(f"{skill_home}\\skills", powershell)
                self.assertNotIn(f"{skill_home}/skills", posix)
        self.assertIn('python3 -m venv "$repo_root/.venv"', posix)
        self.assertIn('"$runner" -m iconflow setup', posix)
        self.assertNotIn(b"\r\n", (ROOT / "scripts" / "setup.sh").read_bytes())

        skill = (ROOT / "skills" / "iconflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: iconflow\n"))
        self.assertIn("license: CC-BY-SA-4.0", skill)
        self.assertIn("compatibility:", skill)
        self.assertIn('version: "0.5.0"', skill)


if __name__ == "__main__":
    unittest.main()
