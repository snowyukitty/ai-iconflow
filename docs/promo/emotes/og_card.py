# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Capture the /emotes/ hero — headline, packs and both chat panes — as its OG image.

Writes docs/assets/marketing/emotes-1200x630.png and its byte-identical copy in
website/assets/marketing/.
"""
import functools, http.server, shutil, socket, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[3]
LAYOUT = r"""() => {
  document.querySelector('.site-header').style.display = 'none';
  document.querySelector('.skip-link').style.display = 'none';
  const hero = document.querySelector('.emo-hero');
  hero.style.paddingTop = '44px';
  hero.style.minHeight = '630px';
  document.querySelectorAll('img[loading]').forEach((i) => { i.loading = 'eager'; });
  window.scrollTo(0, 0);
}"""
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "website"))
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
httpd = socketserver.TCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch()
    # At 1200 wide the page keeps its own 24px gutters inside the card.
    pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
    pg.goto(f"http://127.0.0.1:{port}/emotes/", wait_until="networkidle")
    pg.evaluate(LAYOUT)
    pg.wait_for_timeout(800)
    out = ROOT / "docs" / "assets" / "marketing" / "emotes-1200x630.png"
    pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1200, "height": 630})
    shutil.copyfile(out, ROOT / "website" / "assets" / "marketing" / out.name); print(out)
    b.close()
httpd.shutdown()
