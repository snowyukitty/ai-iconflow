# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Capture the real /xray/ page in the states the laptop screen shows.

1280x800 CSS at 2x = a 2560x1600 screen. The drop goes through the page's
real file input; the results are what the page rendered for that file.
"""
import functools, http.server, socket, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SITE = HERE.parents[3] / "website"
OUT = HERE / "screen"; OUT.mkdir(exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE)); h.log_message = lambda *a: None
httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
    pg.goto(f"http://127.0.0.1:{port}/xray/"); pg.wait_for_timeout(400)
    pg.add_style_tag(content=".skip-link{display:none!important}")   # a focus-only link, never on screen
    pg.mouse.move(5, 790)
    pg.screenshot(path=str(OUT / "a-idle.png"))
    pg.locator(".xray-drop").evaluate("e => e.classList.add('is-over')"); pg.screenshot(path=str(OUT / "b-over.png"))
    pg.locator(".xray-drop").evaluate("e => e.classList.remove('is-over')")
    pg.set_input_files("[data-xray-input]", str(HERE.parent / "assets" / "hairline.svg"))
    pg.wait_for_function("document.querySelector('[data-xray-headline]').textContent !== '—'")
    pg.wait_for_timeout(500); pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "c-full.png"), full_page=True)
    top = pg.evaluate("document.querySelector('[data-xray-results]').getBoundingClientRect().top + window.scrollY")
    drop = pg.evaluate("(() => { const r = document.querySelector('.xray-drop').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()")
    print("results_top_css", top, "drop_rect_css", drop, "headline", pg.inner_text("[data-xray-headline]"))
    (OUT / "meta.txt").write_text(f"results_top_css={top}\ndrop_rect_css={drop}\n")
    b.close()
httpd.shutdown()
