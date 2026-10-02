# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Render film.html frame by frame at 3840x2160 / 24 fps, then encode with the mix.

    python capture.py --stills 1.4 3 5 9 15 ...    # key frames only, for review
    python capture.py                               # every frame -> 4K master + 1080p
"""
import argparse
import functools
import http.server
import shutil
import socket
import socketserver
import subprocess
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "work" / "promo-xray"
FPS = 24

ap = argparse.ArgumentParser()
ap.add_argument("--stills", nargs="*", type=float)
ap.add_argument("--scale", type=float, default=2.0, help="device scale: 2 = 3840x2160")
ap.add_argument("--mix", default=str(WORK / "audio" / "mix-v3.wav"))
ap.add_argument("--out", default=str(WORK / "render" / "iconflow-16px-xray-4k.mp4"))
args = ap.parse_args()

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
handler.log_message = lambda *a: None
httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=args.scale)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"http://127.0.0.1:{port}/docs/promo/xray-film/film.html")
    pg.evaluate("window.ready")
    duration = pg.evaluate("window.DURATION")
    stage = pg.locator("#stage")
    if args.stills is not None:
        out = HERE / "stills"; out.mkdir(exist_ok=True)
        for t in args.stills:
            pg.evaluate(f"window.render({t})")
            stage.screenshot(path=str(out / f"t{t:05.2f}.png"))
        print("stills ->", out)
    else:
        frames = WORK / "frames-v3"
        shutil.rmtree(frames, ignore_errors=True); frames.mkdir(parents=True)
        total = int(round(duration * FPS))
        for i in range(total):
            pg.evaluate(f"window.render({i / FPS})")
            stage.screenshot(path=str(frames / f"{i:05d}.png"))
            if i % 120 == 0:
                print(f"frame {i}/{total}", flush=True)
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
        common = ["-framerate", str(FPS), "-i", str(frames / "%05d.png"), "-i", args.mix,
                  "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart"]
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *common,
                        "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                        "-tune", "grain", str(out)], check=True)
        hd = out.with_name(out.stem.replace("-4k", "") + "-1080p.mp4")
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *common,
                        "-vf", "scale=1920:1080:flags=lanczos",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-tune", "grain", str(hd)], check=True)
        print(f"{total} frames -> {out} and {hd}")
    print("page errors:", errors)
    b.close()
httpd.shutdown()
