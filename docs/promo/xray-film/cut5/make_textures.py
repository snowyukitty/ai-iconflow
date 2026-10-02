# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Textures for cut 5 that are not plain master rasters.

- letter-*.png: the generic letter-on-a-square icons the film opens on. They
  are deliberately ordinary (soft gradient, centred initial), not bad.
- build/: a real `iconflow build --targets all` of the quiet-hero master, so every
  file name and pixel the "one SVG ships as..." shot shows is the actual output.
- favicon-16.png: the 16 px frame pulled out of that build's favicon.ico.

    python make_textures.py
"""
import shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TEX = HERE / "tex"; TEX.mkdir(exist_ok=True)
FONT = ROOT / "work" / "tools" / "fonts" / "extras" / "ttf" / "Inter-SemiBold.ttf"

LETTERS = [  # (letter, top colour, bottom colour)
    ("K", "#5B8DEF", "#3A5BD9"), ("M", "#7C6CF2", "#5A47D6"), ("T", "#3BB8A8", "#23907F"), ("A", "#4F7BE8", "#2F55C4"),
    ("S", "#8A93A6", "#646C80"), ("P", "#E46A6A", "#C24848"), ("N", "#4B9BE0", "#2C74BD"), ("R", "#6C7BF0", "#4A55CF"),
    ("D", "#52B37A", "#378F5C"), ("L", "#9A7AE8", "#7656C9"), ("F", "#F09A4A", "#D3762A"), ("C", "#4A5568", "#2D3748"),
    ("G", "#5AA9E6", "#3A86C8"), ("B", "#E07A9A", "#C2577A"), ("H", "#6FB98F", "#4E9A70"), ("E", "#8E86D8", "#6A61BC"),
]


def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def letter_tile(ch, top, bottom, size=1024):
    grad = Image.new("RGB", (1, size))
    a, b = hexrgb(top), hexrgb(bottom)
    for y in range(size):
        k = y / (size - 1); grad.putpixel((0, y), tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    grad = grad.resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((40, 40, 983, 983), radius=212, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0)); out.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(out); f = ImageFont.truetype(str(FONT), 680)
    d.text((size / 2, size / 2 + 12), ch, font=f, fill=(255, 255, 255, 255), anchor="mm")
    return out


def main():
    for ch, top, bottom in LETTERS:
        letter_tile(ch, top, bottom).save(TEX / f"letter-{ch}.png")
    build = TEX / "build"
    shutil.rmtree(build, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "iconflow", "build", str(HERE / "assets" / "quiet-hero.svg"), "--out", str(build),
                    "--targets", "all", "--tray-svg", str(HERE / "assets" / "quiet-hero-tray.svg"), "--name", "Quiet Hero"],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    ico = Image.open(build / "favicon.ico"); ico.size = (16, 16); ico.load()
    ico.convert("RGBA").save(TEX / "favicon-16.png")
    files = sorted(p.relative_to(build).as_posix() for p in build.rglob("*") if p.is_file())
    (TEX / "build-files.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
    print(f"{len(LETTERS)} letter tiles, {len(files)} built files -> {TEX}")


if __name__ == "__main__":
    main()
