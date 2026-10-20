# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from iconflow import rasterize


class SvgInputSafetyTests(unittest.TestCase):
    def _write(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.svg"
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def test_load_svg_accepts_namespaced_svg_and_strips_xml_declaration(self):
        path = self._write(
            '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16"><path d="M0 0h16v16H0z"/></svg>'
        )
        loaded = rasterize.load_svg(path)
        self.assertTrue(loaded.startswith("<svg"))
        self.assertNotIn("<?xml", loaded)

    def test_load_svg_normalizes_line_endings_for_cross_platform_hashes(self):
        source = '<svg xmlns="http://www.w3.org/2000/svg">\n  <path/>\n</svg>\n'
        expected = rasterize._validated_svg_text(source)
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                path = self._write(source.replace("\n", newline))
                self.assertEqual(expected, rasterize.load_svg(path))

    def test_load_svg_rejects_doctype_and_entity_declarations(self):
        for declaration in (
            '<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"/>',
            '<!DOCTYPE svg [<!ENTITY x "expanded">]><svg>&x;</svg>',
        ):
            with self.subTest(declaration=declaration[:20]):
                with self.assertRaisesRegex(ValueError, "DOCTYPE or ENTITY"):
                    rasterize.load_svg(self._write(declaration))

    def test_load_svg_rejects_non_svg_root_and_malformed_xml(self):
        with self.assertRaisesRegex(ValueError, "root must be <svg>"):
            rasterize.load_svg(self._write("<html><svg/></html>"))
        with self.assertRaisesRegex(ValueError, "well-formed XML"):
            rasterize.load_svg(self._write("<svg><path></svg>"))

    def test_complexity_guards_cover_bytes_elements_and_depth(self):
        with mock.patch.object(rasterize, "MAX_SVG_BYTES", 20):
            with self.assertRaisesRegex(ValueError, "safety limit"):
                rasterize.load_svg(self._write('<svg viewBox="0 0 16 16"/>'))

        with mock.patch.object(rasterize, "MAX_SVG_ELEMENTS", 2):
            with self.assertRaisesRegex(ValueError, "element safety limit"):
                rasterize.load_svg(self._write("<svg><g><path/></g></svg>"))

        with mock.patch.object(rasterize, "MAX_SVG_DEPTH", 2):
            with self.assertRaisesRegex(ValueError, "nesting safety limit"):
                rasterize.load_svg(self._write("<svg><g><path/></g></svg>"))

    def test_direct_render_input_is_validated_before_browser_use(self):
        renderer = rasterize.Rasterizer()
        renderer._page = mock.Mock()
        with self.assertRaisesRegex(ValueError, "document root"):
            renderer.render("<html/>", 16)
        renderer._page.set_viewport_size.assert_not_called()


class LazyRasterizerOwnershipTest(unittest.TestCase):
    def test_PF09_the_entered_context_manager_is_the_one_exited(self):
        events = []

        class Renderer:
            def render(self, svg_text, size, bg="transparent"):
                events.append("render")
                return b"png"

        class Owner:
            def __init__(self, color_scheme="light"):
                events.append(("open", color_scheme))

            def __enter__(self):
                return Renderer()  # a distinct object, with no __exit__ of its own

            def __exit__(self, *exc):
                events.append("close")

        from iconflow.rasterize import LazyRasterizer

        with LazyRasterizer("dark", factory=Owner) as lazy:
            self.assertEqual(lazy.render("<svg/>", 16), b"png")
            self.assertEqual(lazy.render("<svg/>", 32), b"png")
        self.assertEqual(events, [("open", "dark"), "render", "render", "close"])
        lazy.__exit__(None, None, None)  # exiting again closes nothing twice
        self.assertEqual(events.count("close"), 1)

    def test_IR12_a_failing_render_keeps_its_error_over_a_failing_cleanup(self):
        from iconflow.rasterize import LazyRasterizer

        class Broken:
            def render(self, *args, **kwargs):
                raise ValueError("the render failed")

        def owner_with(cleanup_error):
            class Owner:
                closed = 0

                def __init__(self, color_scheme="light"):
                    pass

                def __enter__(self):
                    return Broken()

                def __exit__(self, *exc):
                    Owner.closed += 1
                    if cleanup_error:
                        raise RuntimeError("cleanup failed")

            return Owner

        owner = owner_with(cleanup_error=True)
        with self.assertRaisesRegex(ValueError, "the render failed"):
            with LazyRasterizer(factory=owner) as lazy:
                lazy.render("<svg/>", 16)
        self.assertEqual(owner.closed, 1)
        # Cleanup failing alone is still reported.
        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            with LazyRasterizer(factory=owner_with(cleanup_error=True)) as lazy:
                lazy._session()


if __name__ == "__main__":
    unittest.main()
