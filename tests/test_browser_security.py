# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
import os
import threading
import unittest
from functools import partial
from http.server import (
    BaseHTTPRequestHandler,
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path

from iconflow.rasterize import Rasterizer
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
class BrowserSecurityIntegrationTests(unittest.TestCase):
    def test_external_svg_resources_never_reach_the_network(self):
        requests: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(204)
                self.end_headers()

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            f'<style>@import url("http://127.0.0.1:{port}/style.css");</style>'
            f'<image href="http://127.0.0.1:{port}/pixel.png" width="32" height="32"/>'
            f'<script>fetch("http://127.0.0.1:{port}/script")</script>'
            '<rect width="32" height="32" fill="#ff5b3d"/></svg>'
        )
        try:
            with Rasterizer() as renderer:
                rendered = renderer.render(svg, 32)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertTrue(rendered.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(requests, [])

    def test_animation_is_frozen_to_repeatable_pixels(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect x="0" width="8" height="32" fill="#ff5b3d">'
            '<animate attributeName="x" from="0" to="24" dur="0.01s" '
            'repeatCount="indefinite"/></rect></svg>'
        )
        with Rasterizer() as renderer:
            first = renderer.render(svg, 32)
            second = renderer.render(svg, 32)
        self.assertEqual(first, second)


@unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
class WebsiteLayoutIntegrationTests(unittest.TestCase):
    def test_tray_reference_never_overflows_the_viewport(self):
        """A wide command or output table must scroll itself, not the page."""

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(QuietHandler, directory=str(ROOT / "website")),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}/reference/tray-icons/"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    for width in (320, 390, 768, 1440):
                        with self.subTest(width=width):
                            page = browser.new_page(
                                viewport={"width": width, "height": 900}
                            )
                            page.goto(url, wait_until="networkidle")
                            metrics = page.evaluate(
                                "({client: document.documentElement.clientWidth, "
                                "scroll: document.documentElement.scrollWidth})"
                            )
                            self.assertEqual(metrics["client"], metrics["scroll"])
                            page.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
