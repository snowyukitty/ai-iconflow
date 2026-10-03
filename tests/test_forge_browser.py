# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The Icon Forge, driven in Chromium under the site's production CSP.

`tests/test_website.py` checks the Forge's files; this drives the page: the
first visit, undo, share links, export and re-import, the project kit, the
finalists, the phone layout and the no-WebGL fallback. The server sends the
exact Content-Security-Policy from `website/_headers`, so a script, style or
image the CSP would block in production fails here first.

Opt in with ``ICONFLOW_BROWSER_TESTS=1``; it runs in the ``chromium-integration``
CI job beside the other rendering tests.
"""
from __future__ import annotations

import functools
import http.server
import io
import os
import re
import socket
import sys
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
NEEDS_CHROMIUM = unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
# SwiftShader gives headless Chromium a WebGL context without a GPU.
WEBGL_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
MASTER_SVG = "decodeURIComponent(document.querySelector('[data-forge-master]').src.split(',')[1])"


def production_csp() -> str:
    headers = (SITE / "_headers").read_text(encoding="utf-8")
    policy = re.search(r"Content-Security-Policy: (.+)", headers).group(1)
    # A local http:// origin cannot be upgraded; everything else is verbatim.
    return policy.replace(" upgrade-insecure-requests", "").rstrip("; ")


class _Handler(http.server.SimpleHTTPRequestHandler):
    csp = ""
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", self.csp)
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args) -> None:
        pass


@NEEDS_CHROMIUM
class ForgeInTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from playwright.sync_api import sync_playwright

        _Handler.csp = production_csp()
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        cls.httpd = http.server.ThreadingHTTPServer(
            ("127.0.0.1", port), functools.partial(_Handler, directory=str(SITE)))
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=WEBGL_ARGS)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright.stop()
        cls.httpd.shutdown()

    def open(self, **context):
        """A fresh page on /forge/ with storage cleared, collecting every problem."""
        ctx = self.browser.new_context(**({"viewport": {"width": 1440, "height": 900}} | context))
        self.addCleanup(ctx.close)
        page = ctx.new_page()
        problems: list[str] = []
        page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type in ("error", "warning") and problems.append(f"{m.type}: {m.text}"))
        page.on("requestfailed", lambda r: problems.append(f"requestfailed: {r.url}"))
        page.goto(f"{self.base}/forge/")
        page.evaluate("() => localStorage.clear()")
        page.goto(f"{self.base}/forge/")
        page.wait_for_function("() => document.querySelectorAll('[data-forge-checks] li').length >= 6")
        # ...and for the workbench to settle one way or the other, so a fast
        # test never closes the page while scene.js is still loading.
        page.wait_for_function(
            "() => document.querySelector('[data-forge-stage] canvas')"
            " || !document.querySelector('[data-forge-nogl]').hidden")
        self.addCleanup(lambda: self.assertEqual([], problems))
        return page

    def layers(self, page) -> int:
        return page.locator("[data-forge-layers] li").count()

    def test_first_visit_is_a_worked_example_that_passes_every_check(self) -> None:
        page = self.open()
        self.assertEqual("Ready for the real review", page.locator("[data-forge-score-text]").inner_text())
        self.assertEqual(6, page.locator("[data-forge-checks] li.is-pass").count())
        has_webgl = page.evaluate("() => !!document.createElement('canvas').getContext('webgl2')")
        if has_webgl:
            self.assertTrue(page.locator("[data-forge-nogl]").is_hidden())
            self.assertEqual(1, page.locator("[data-forge-stage] canvas").count())
        # The neighbourhood panel names real generic forms with distances.
        captions = page.locator("[data-near-caption]").all_inner_texts()
        self.assertTrue(all(re.search(r"· 0\.\d\d$", c) for c in captions), captions)

    def test_edits_undo_and_redo(self) -> None:
        page = self.open()
        start = self.layers(page)
        page.click("[data-add=arc]")
        page.click("[data-add=circle]")
        page.click("[data-action=cut]")
        page.keyboard.press("ArrowLeft")
        self.assertEqual(start + 2, self.layers(page))
        self.assertIn("mask=", page.evaluate(MASTER_SVG))
        for _ in range(4):
            page.keyboard.press("Control+z")
        self.assertEqual(start, self.layers(page))
        for _ in range(4):
            page.keyboard.press("Control+Shift+z")
        self.assertEqual(start + 2, self.layers(page))

    def test_share_link_and_export_round_trip_the_design(self) -> None:
        page = self.open()
        page.select_option("[data-forge-example]", "relay")
        page.wait_for_timeout(300)
        svg = page.evaluate(MASTER_SVG)
        page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.base)
        page.click("[data-action=share]")
        link = page.evaluate("navigator.clipboard.readText()")
        self.assertRegex(link, r"/forge/#d=[\w-]+$")
        other = page.context.new_page()
        other.goto(link)
        other.wait_for_timeout(800)
        self.assertEqual(svg, other.evaluate(MASTER_SVG))

        with page.expect_download() as download:
            page.click("[data-action=export]")
        exported = Path(download.value.path())
        self.assertIn('id="iconflow-forge"', exported.read_text(encoding="utf-8"))
        page.click("[data-action=clear]")
        self.assertEqual(0, self.layers(page))
        page.set_input_files("[data-forge-import]", str(exported))
        page.wait_for_timeout(300)
        self.assertEqual(svg, page.evaluate(MASTER_SVG))

    def test_project_kit_is_a_folder_the_cli_can_run(self) -> None:
        page = self.open()
        page.select_option("[data-forge-brief]", "focus")
        page.locator("[data-slot='0'] [data-slot-action=keep]").click()
        page.select_option("[data-forge-example]", "tide")
        page.locator("[data-slot='1'] [data-slot-action=keep]").click()
        page.fill("[data-forge-name]", "Calm Weather")
        with page.expect_download() as download:
            page.click("[data-action=kit]")
        self.assertEqual("calm-weather.zip", download.value.suggested_filename)
        archive = zipfile.ZipFile(io.BytesIO(Path(download.value.path()).read_bytes()))
        self.assertIsNone(archive.testzip())
        self.assertEqual(
            {"calm-weather/iconflow.toml", "calm-weather/master.svg", "calm-weather/README.md",
             "calm-weather/finalists/a.svg", "calm-weather/finalists/b.svg"},
            set(archive.namelist()))
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        config = tomllib.loads(archive.read("calm-weather/iconflow.toml").decode("utf-8"))
        self.assertEqual("calm-weather", config["project"]["name"])
        self.assertEqual("master.svg", config["project"]["master"])
        self.assertEqual(["@collision"], config["neighbours"]["avoid"])
        self.assertTrue(config["brief"]["app_intent"].startswith("A focus timer."))
        readme = archive.read("calm-weather/README.md").decode("utf-8")
        self.assertIn("iconflow compare finalists/a.svg finalists/b.svg", readme)
        self.assertIn("iconflow check master.svg --config iconflow.toml", readme)

    def test_a_menu_bar_brief_ships_its_own_tray_drawing(self) -> None:
        page = self.open()
        page.select_option("[data-forge-brief]", "tray")
        page.select_option("[data-forge-example]", "dial")
        with page.expect_download() as download:
            page.click("[data-action=kit]")
        archive = zipfile.ZipFile(io.BytesIO(Path(download.value.path()).read_bytes()))
        self.assertIn("my-icon/tray.svg", archive.namelist())
        config = archive.read("my-icon/iconflow.toml").decode("utf-8")
        self.assertIn('targets = ["web", "tray"]', config)
        self.assertIn('tray_svg = "tray.svg"', config)
        self.assertIn("--tray-svg tray.svg", archive.read("my-icon/README.md").decode("utf-8"))
        # The tray drawing is the mark alone: no card shape in it.
        tray = archive.read("my-icon/tray.svg").decode("utf-8")
        self.assertNotIn('rx="224"', tray)

    def test_mirror_adds_a_twin_across_the_centre_line(self) -> None:
        page = self.open()
        page.click("[data-action=clear]")
        page.click("[data-add=wedge]")
        page.keyboard.press("e")                     # turn 15°
        for _ in range(8):
            page.keyboard.press("ArrowLeft")         # x 512 -> 384
        page.keyboard.press("m")
        svg = page.evaluate(MASTER_SVG)
        self.assertIn('translate(384 512) rotate(15)', svg)
        self.assertIn('translate(640 512) rotate(345)', svg)

    def test_finalists_call_out_one_idea_in_two_colours(self) -> None:
        page = self.open()
        verdict = page.locator("[data-forge-bake-verdict]")
        for name, slot in (("relay", 0), ("tide", 1)):
            page.select_option("[data-forge-example]", name)
            page.locator(f"[data-slot='{slot}'] [data-slot-action=keep]").click()
        page.wait_for_function("() => document.querySelector('[data-forge-bake-verdict]').classList.contains('is-pass')")
        page.locator("[data-slot='2'] [data-slot-action=keep]").click()   # tide again
        page.wait_for_function("() => document.querySelector('[data-forge-bake-verdict]').classList.contains('is-warn')")
        self.assertIn("B and C are one shape at 16px", verdict.inner_text())
        page.reload()
        page.wait_for_timeout(800)
        self.assertEqual(3, page.locator(".forge-slots li:not(.is-empty)").count())

    def test_a_phone_gets_the_whole_page_without_sideways_scroll(self) -> None:
        page = self.open(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        self.assertEqual(0, overflow)

    def test_without_webgl_the_panel_still_builds(self) -> None:
        browser = self.playwright.chromium.launch(args=["--disable-3d-apis", "--disable-webgl"])
        self.addCleanup(browser.close)
        page = browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{self.base}/forge/")
        page.wait_for_function("() => document.querySelectorAll('[data-forge-checks] li').length >= 6")
        self.assertTrue(page.locator("[data-forge-nogl]").is_visible())
        before = self.layers(page)
        page.click("[data-add=wedge]")
        self.assertEqual(before + 1, self.layers(page))
        page.locator("[data-forge-layers] li button").last.click()
        self.assertTrue(page.locator("[data-forge-fields]").is_visible())
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
