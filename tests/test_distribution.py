import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.verify_distribution import main, verify


class DistributionVerificationTests(unittest.TestCase):
    def _wheel(self, names: list[str]) -> tuple[tempfile.TemporaryDirectory, Path]:
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "ai_iconflow-0.4.0-py3-none-any.whl"
        with zipfile.ZipFile(path, "w") as archive:
            for name in names:
                archive.writestr(name, b"content")
        return directory, path

    @staticmethod
    def _required() -> list[str]:
        return [
            "iconflow/__init__.py",
            "iconflow/resources/templates/master.svg",
            "iconflow/resources/presets/flat-geometric.svg",
            "iconflow/resources/docs/DESIGN_PLAYBOOK.md",
            "ai_iconflow-0.4.0.dist-info/METADATA",
            "ai_iconflow-0.4.0.dist-info/RECORD",
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


if __name__ == "__main__":
    unittest.main()
