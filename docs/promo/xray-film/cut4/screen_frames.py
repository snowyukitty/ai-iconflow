# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Compose the laptop-screen sequence from the real page states.

The page itself is never redrawn: frames are crops of the real screenshots,
with a cursor and the dragged file on top, and a real scroll to the results.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SCR = HERE / "screen"
OUT = HERE.parents[3] / "work" / "promo-xray" / "screen-seq"
OUT.mkdir(parents=True, exist_ok=True)
FONT = HERE.parents[3] / "work" / "tools" / "fonts" / "extras" / "ttf" / "Inter-Medium.ttf"
FPS, DUR, W, H, DPR = 24, 8.0, 2560, 1600, 2

meta = dict(l.split("=", 1) for l in (SCR / "meta.txt").read_text().splitlines() if l)
RESULTS_TOP = float(meta["results_top_css"])
dl, dt, dw, dh = [float(v) for v in meta["drop_rect_css"].strip("[]").split(",")]

idle = Image.open(SCR / "a-idle.png").convert("RGB")
over = Image.open(SCR / "b-over.png").convert("RGB")
full = Image.open(SCR / "c-full.png").convert("RGB")
icon = Image.open(HERE / "tex" / "hairline-2048.png").convert("RGBA").resize((330, 330), Image.LANCZOS)
font = ImageFont.truetype(str(FONT), 44)


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def inout(x): return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, k): return a + (b - a) * k


def file_card():
    card = Image.new("RGBA", (450, 495), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, 449, 494), radius=50, fill=(43, 45, 54, 245), outline=(255, 255, 255, 40), width=3)
    card.alpha_composite(icon, (60, 38))
    d.text((225, 428), "dashboard.svg", font=font, fill=(240, 240, 240, 255), anchor="mm")
    return card


def cursor():
    c = Image.new("RGBA", (60, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(c)  # drawn at 60x80, shown at 1.5x
    pts = [(4, 4), (4, 62), (18, 49), (28, 72), (38, 67), (28, 45), (46, 45)]
    d.polygon(pts, fill=(0, 0, 0, 255)); d.polygon([(x + (1 if x < 20 else 0), y) for x, y in pts], fill=(0, 0, 0, 255))
    inner = [(8, 13), (8, 52), (19, 41), (29, 63), (34, 61), (24, 39), (37, 39)]
    d.polygon(inner, fill=(255, 255, 255, 255))
    return c


CARD, CUR = file_card(), cursor().resize((90, 120), Image.LANCZOS)
shadow = Image.new("RGBA", CARD.size, (0, 0, 0, 0)); ImageDraw.Draw(shadow).rounded_rectangle((0, 0, 449, 494), radius=50, fill=(0, 0, 0, 90))

total = int(DUR * FPS)
for f in range(total):
    t = f / FPS
    scroll = inout(prog(t, 1.85, 2.75)) * (RESULTS_TOP - 30) * DPR
    if t < 1.6:
        base = over if 1.25 <= t else idle
        frame = base.crop((0, 0, W, H)).convert("RGBA")
    else:
        frame = full.crop((0, int(scroll), W, int(scroll) + H)).convert("RGBA")
    # Drag: from off-screen bottom right to the centre of the real drop zone.
    k = inout(prog(t, 0.35, 1.5))
    cx, cy = lerp(W + 120, (dl + dw / 2) * DPR, k), lerp(H + 260, (dt + dh / 2) * DPR, k)
    if 0.35 <= t < 1.72:
        drop = prog(t, 1.55, 1.72)
        sc = 1 - 0.5 * drop
        card = CARD.resize((int(450 * sc), int(495 * sc)), Image.LANCZOS)
        a = int(255 * (1 - drop))
        card.putalpha(card.getchannel("A").point(lambda v: v * a // 255))
        sh = shadow.resize(card.size)
        frame.alpha_composite(sh, (int(cx - card.width / 2 + 10), int(cy - card.height / 2 + 18)))
        frame.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2)))
    if t < 2.4:
        frame.alpha_composite(CUR, (int(cx + 140), int(cy + 170)))
    frame.convert("RGB").save(OUT / f"{f:04d}.png", optimize=False)
print(f"{total} screen frames -> {OUT}")
