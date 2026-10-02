# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Render screen.html at 24 fps (2560x1600) for the laptop shot's screen."""
import functools, http.server, socket, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "work" / "promo-xray" / "screen5-seq"; OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE)); h.log_message = lambda *a: None
httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
    pg.goto(f"http://127.0.0.1:{port}/screen.html"); pg.evaluate("window.ready")
    for f in range(240):
        pg.evaluate(f"window.render({f / 24})"); pg.locator("#s").screenshot(path=str(OUT / f"{f:04d}.png"))
    b.close()
httpd.shutdown()
print("240 frames ->", OUT)
