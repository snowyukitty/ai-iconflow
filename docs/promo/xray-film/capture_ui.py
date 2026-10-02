# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Capture real 16px X-ray UI pieces as film plates, at 3x density for a 4K master.

Every plate is a screenshot of the real /xray/ page after a real file went
through its file input, and the verdicts it printed are logged here.
"""
import functools
import http.server
import socket
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SITE = HERE.parents[2] / "website"
OUT = HERE / "plates"
OUT.mkdir(exist_ok=True)

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
handler.log_message = lambda *a: None
httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=3)
    pg.goto(f"http://127.0.0.1:{port}/xray/")
    pg.wait_for_timeout(300)
    pg.locator(".xray-drop").screenshot(path=str(OUT / "drop.png"))
    pg.locator(".xray-drop").evaluate("e => e.classList.add('is-over')")
    pg.locator(".xray-drop").screenshot(path=str(OUT / "drop-over.png"))
    pg.locator(".xray-drop").evaluate("e => e.classList.remove('is-over')")
    for name in ("hairline", "fixed-card", "fixed-tray"):
        pg.set_input_files("[data-xray-input]", str(HERE / "assets" / f"{name}.svg"))
        pg.wait_for_function("document.querySelector('[data-xray-headline]').textContent !== '—'")
        pg.wait_for_timeout(300)
        verdicts = pg.eval_on_selector_all(".xray-verdict strong", "els => els.map(e => e.textContent)")
        print(name, "->", pg.inner_text("[data-xray-headline]"), verdicts)
        pg.locator(".xray-headline").screenshot(path=str(OUT / f"{name}-headline.png"))
        for i, panel in enumerate(pg.locator(".xray-panel").all(), 1):
            panel.screenshot(path=str(OUT / f"{name}-panel-{i}.png"))
        for i, card in enumerate(pg.locator(".xray-verdict").all(), 1):
            card.screenshot(path=str(OUT / f"{name}-verdict-{i}.png"))
        pg.locator(".xray-verdicts").screenshot(path=str(OUT / f"{name}-verdicts.png"))
        pg.evaluate("document.querySelector('[data-xray-headline]').textContent = '—'")
    b.close()
httpd.shutdown()
print("plates:", len(list(OUT.iterdir())))
