# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Rasters for cut 5, drawn with the same canvas call the X-ray uses.

Every tile face is a gallery master rendered at 1024 px. Every block and every
small-size file is the master at that exact size.
"""
import base64, functools, http.server, socket, socketserver, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "tex"; OUT.mkdir(exist_ok=True)
GRID = ["sky-courier", "forest-familiar", "co-op-lock", "record-sleeve", "tomato-pincushion", "boss-helm",
        "keepsake-knot", "octopus-curl", "save-cartridge", "catnap-focus", "quiet-hero", "sunflower-disc",
        "storm-parasol", "folded-map-folio", "mech-pauldron", "accordion-bellows"]
ROW = ["save-cartridge", "octopus-curl", "quiet-hero", "boss-helm", "record-sleeve"]
JOBS = ([(g, [1024]) for g in GRID] + [(r, [2048, 16]) for r in ROW]
        + [("quiet-hero-tray", [32, 16]), ("iconflow-mark", [1024])])

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE)); h.log_message = lambda *a: None
httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto(f"http://127.0.0.1:{port}/")
    for name, sizes in JOBS:
        for size in sizes:
            data = pg.evaluate("""async ([src, size]) => {
              const img = new Image(); img.src = src; await img.decode();
              const c = document.createElement('canvas'); c.width = c.height = size;
              const x = c.getContext('2d'); x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
              x.drawImage(img, 0, 0, size, size); return c.toDataURL('image/png').split(',')[1];
            }""", [f"/assets/{name}.svg", size])
            (OUT / f"{name}-{size}.png").write_bytes(base64.b64decode(data))
    b.close()
httpd.shutdown()
print("rasters ->", OUT, len(list(OUT.iterdir())))
