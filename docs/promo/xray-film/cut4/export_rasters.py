# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Export the real rasters the 3D shots are built from.

The X-ray draws an icon into a canvas with high-quality smoothing; the same
call produces these PNGs, so every block colour in the film is a pixel the
tool would show.
"""
import base64
import functools
import http.server
import socket
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FILM = HERE.parent
OUT = HERE / "tex"
OUT.mkdir(exist_ok=True)
JOBS = [("hairline", [2048, 32, 16]), ("fixed-card", [2048, 16]), ("fixed-tray", [32, 16]), ("iconflow-mark", [1024])]

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FILM)); h.log_message = lambda *a: None
httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), h)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(f"http://127.0.0.1:{port}/cut4/")
    for name, sizes in JOBS:
        for size in sizes:
            data = pg.evaluate("""async ([src, size]) => {
              const img = new Image(); img.src = src; await img.decode();
              const c = document.createElement('canvas'); c.width = c.height = size;
              const x = c.getContext('2d'); x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
              x.drawImage(img, 0, 0, size, size); return c.toDataURL('image/png').split(',')[1];
            }""", [f"/assets/{name}.svg", size])
            (OUT / f"{name}-{size}.png").write_bytes(base64.b64decode(data))
            print("wrote", f"{name}-{size}.png")
    b.close()
httpd.shutdown()
