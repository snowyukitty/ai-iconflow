import hashlib
import tempfile
import unittest
from pathlib import Path

from iconflow.shortcut import install_content_addressed_icon


class ContentAddressedIconTests(unittest.TestCase):
    def test_installs_digest_named_alias_beside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "icon.ico"
            payload = b"first-icon-bytes"
            source.write_bytes(payload)

            installed = install_content_addressed_icon(source)

            digest = hashlib.sha256(payload).hexdigest()[:12]
            self.assertEqual(installed.name, f"shortcut-icon-{digest}.ico")
            self.assertTrue(installed.parent.samefile(source.parent))
            self.assertEqual(installed.read_bytes(), payload)

    def test_reuses_same_alias_and_changes_path_when_bytes_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "icon.ico"
            source.write_bytes(b"version-one")
            first = install_content_addressed_icon(source)
            first_mtime = first.stat().st_mtime_ns

            self.assertEqual(install_content_addressed_icon(source), first)
            self.assertEqual(first.stat().st_mtime_ns, first_mtime)

            source.write_bytes(b"version-two")
            second = install_content_addressed_icon(source)
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b"version-one")
            self.assertEqual(second.read_bytes(), b"version-two")

    def test_missing_source_fails_before_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                install_content_addressed_icon(Path(tmp) / "missing.ico")


if __name__ == "__main__":
    unittest.main()
