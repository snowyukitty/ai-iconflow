# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Capture the Forge's own workbench, example design, as the /forge/ OG image.

Writes docs/assets/marketing/forge-1200x630.png and its byte-identical copy in
website/assets/marketing/. WebGL runs on SwiftShader so no GPU is needed.
"""
import functools, http.server, shutil, socket, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[3]
LAYOUT = r"""() => {
  const hide = (s) => document.querySelectorAll(s).forEach((e) => { e.style.display = 'none'; });
  hide('.site-header'); hide('.forge-intro'); hide('.forge-keys'); hide('.skip-link');
  hide('.forge-checks span'); hide('.forge-goal');
  const cards = document.querySelectorAll('.forge-panel > .forge-card');
  cards.forEach((c, i) => { if (i > 1) c.style.display = 'none'; });
  cards[1].style.order = '-1';
  document.querySelector('.forge-app').style.marginTop = '15px';
  document.querySelector('.forge-stage').style.height = '600px';
  const w = document.querySelector('.forge-stage-wrap'); w.style.position = 'relative'; w.style.top = '0';
  window.scrollTo(0, 0);
}"""
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "website")); h.log_message = lambda *a: None
h.extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}
httpd = socketserver.TCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    # section-shell is 1248 - 48 = 1200 wide at this viewport.
    pg = b.new_page(viewport={"width": 1248, "height": 630}, device_scale_factor=1)
    pg.goto(f"http://127.0.0.1:{port}/forge/")
    pg.wait_for_function("document.querySelector('[data-forge-score]').classList.contains('is-ready')")
    pg.evaluate(LAYOUT)
    pg.wait_for_timeout(2500)   # let new pieces finish dropping and the camera settle
    out = ROOT / "docs" / "assets" / "marketing" / "forge-1200x630.png"
    pg.screenshot(path=str(out), clip={"x": 24, "y": 0, "width": 1200, "height": 630})
    shutil.copyfile(out, ROOT / "website" / "assets" / "marketing" / out.name); print(out)
    b.close()
httpd.shutdown()
