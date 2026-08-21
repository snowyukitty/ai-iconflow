# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from iconflow.rasterize import Rasterizer


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


if __name__ == "__main__":
    unittest.main()
