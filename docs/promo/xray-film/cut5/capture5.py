# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Composite cut 5: CG and plate frames under type, then encode with the mix.

    python capture5.py --res 960 --scale 1 --out preview.mp4          # animatic
    python capture5.py --res 3840 --scale 2                           # 4K master + 1080p
    python capture5.py --res 960 --stills 2 5 9 14 20 26 32 35 40     # review stills
"""
import argparse, functools, http.server, shutil, socket, socketserver, subprocess, threading
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / "work" / "promo-xray"
ap = argparse.ArgumentParser()
ap.add_argument("--res", default="960"); ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--stills", nargs="*", type=float)
ap.add_argument("--no-grain", action="store_true", help="web master: leave grain to the AV1 encoder's film-grain synthesis")
ap.add_argument("--mix", default=str(WORK / "audio" / "mix-v5.wav"))
ap.add_argument("--out", default=str(WORK / "render" / "iconflow-film-cut5-4k.mp4"))
a = ap.parse_args()

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)); h.log_message = lambda *x: None
httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), h); threading.Thread(target=httpd.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=a.scale)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(f"window.__SRC = {{cg: '/work/promo-xray/cg5', res: '{a.res}', grain: {'false' if a.no_grain else 'true'}}};")
    pg.goto(f"http://127.0.0.1:{port}/docs/promo/xray-film/cut5/film5.html"); pg.evaluate("window.ready")
    dur, fps = pg.evaluate("window.DURATION"), 24
    stage = pg.locator("#stage")
    if a.stills is not None:
        out = HERE / "stills5"; out.mkdir(exist_ok=True)
        for t in a.stills:
            pg.evaluate(f"window.render({t})"); stage.screenshot(path=str(out / f"t{t:05.2f}.png"))
        print("stills ->", out)
    else:
        frames = WORK / f"frames-cut5-{a.res}{'-clean' if a.no_grain else ''}"; shutil.rmtree(frames, ignore_errors=True); frames.mkdir(parents=True)
        total = int(round(dur * fps))
        for i in range(total):
            pg.evaluate(f"window.render({i / fps})"); stage.screenshot(path=str(frames / f"{i:05d}.png"))
            if i % 120 == 0: print(f"frame {i}/{total}", flush=True)
        out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
        common = ["-framerate", str(fps), "-i", str(frames / "%05d.png"), "-i", a.mix, "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart"]
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *common, "-c:v", "libx264", "-preset", "slow", "-crf", "14" if a.scale > 1 else "18", "-pix_fmt", "yuv420p", "-tune", "film", str(out)], check=True)
        if a.scale > 1:
            hd = out.with_name(out.stem.replace("-4k", "") + "-1080p.mp4")
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *common, "-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-tune", "film", str(hd)], check=True)
        print(f"{total} frames -> {out}")
    print("page errors:", errs); b.close()
httpd.shutdown()
