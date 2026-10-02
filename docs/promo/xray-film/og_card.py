# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Save the X-ray's own result card for the hairline sample as the /xray/ OG image."""
import functools, http.server, socket, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[3]
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "website")); h.log_message = lambda *a: None
httpd = socketserver.TCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(f"http://127.0.0.1:{port}/xray/")
    pg.get_by_role("button", name="Hairline dashboard").click()
    pg.wait_for_function("document.querySelector('[data-xray-headline]').textContent !== '—'")
    with pg.expect_download() as d:
        pg.get_by_role("button", name="Save result card (PNG)").click()
    out = ROOT / "docs" / "assets" / "marketing" / "xray-1200x630.png"
    d.value.save_as(str(out)); print(out)
    b.close()
httpd.shutdown()
