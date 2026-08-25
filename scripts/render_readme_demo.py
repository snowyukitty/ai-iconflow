# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Render the animated README demo from a captured `iconflow demo` transcript.

A repository front page has about ten seconds to say what the tool does. Prose
does not survive that; a terminal that fills in, ships 23 files, and then
*refuses* the same command after one control point moves, does.

The transcript is a real capture, checked in beside this script, so nothing on
the animation is a mock-up. Frames are drawn by the same pinned Chromium the
toolkit already uses for every other rendered asset — no font files, no canvas
libraries, and the brand palette comes from one place.

Usage::

    python scripts/render_readme_demo.py
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "docs" / "assets" / "demo-transcript.txt"
OUTPUT = ROOT / "docs" / "assets" / "demo.gif"
PROOF = ROOT / "website" / "assets" / "proof"

WIDTH, HEIGHT = 1000, 600
# Lines revealed per frame. Two keeps the file small while still reading as
# output arriving rather than a slideshow.
STEP = 2
FRAME_MS = 260
# The refusal is the point of the whole animation; let a reader finish it.
HOLD_MS = 3400

INK = "#191a20"
PAPER = "#fff4e8"
CORAL = "#ff5a4f"
MINT = "#6ce0a0"
MUTED = "rgba(255,244,232,.52)"

COLORS = {
    "cmd": PAPER,
    "out": "rgba(255,244,232,.72)",
    "file": MINT,
    "pass": MINT,
    "good": MINT,
    "fail": CORAL,
    "note": MUTED,
    "gap": MUTED,
}


def load_transcript() -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
        if raw.startswith("#") or not raw.strip():
            continue
        kind, _, text = raw.partition("\t")
        kind = kind.strip()
        if kind not in COLORS:
            raise SystemExit(f"unknown transcript kind: {kind!r}")
        lines.append((kind, text))
    return lines


def data_uri(path: Path) -> str:
    import base64

    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def sizes_panel() -> str:
    """The same approved mark at four native sizes, at 1:1."""
    cells = []
    for size in (128, 64, 32, 16):
        source = PROOF / f"icon-{size}.png"
        if not source.is_file():
            raise SystemExit(f"missing proof render: {source}")
        cells.append(
            f'<figure><img src="{data_uri(source)}" width="{size}" height="{size}" alt="">'
            f"<figcaption>{size}px</figcaption></figure>"
        )
    return "".join(cells)


def document(lines: list[tuple[str, str]], shown: int) -> str:
    body = []
    for index, (kind, text) in enumerate(lines[:shown]):
        if kind == "gap":
            body.append('<div class="gap"></div>')
            continue
        prefix = '<b>$</b> ' if kind == "cmd" else ""
        last = index == shown - 1
        caret = '<i class="caret"></i>' if last else ""
        body.append(f'<div class="l {kind}">{prefix}{escape(text)}{caret}</div>')

    return f"""<!doctype html><meta charset="utf-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:{WIDTH}px;height:{HEIGHT}px;overflow:hidden;background:{INK}}}
  body{{display:grid;grid-template-columns:1fr 236px;
        font-family:ui-monospace,"Cascadia Mono",Consolas,"DejaVu Sans Mono",monospace}}
  .term{{display:grid;grid-template-rows:auto 1fr;
         padding:22px 26px;overflow:hidden}}
  /* A real terminal scrolls. Anchoring the log to the bottom clips the oldest
     lines instead of the newest, so the refusal is never the part cut off. */
  .log{{display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden}}
  .bar{{display:flex;gap:7px;align-items:center;margin-bottom:18px}}
  .bar span{{width:10px;height:10px;border-radius:50%;background:rgba(255,244,232,.16)}}
  .bar p{{margin-left:10px;color:{MUTED};font-size:12px;letter-spacing:.04em}}
  .l{{flex:none;font-size:15px;line-height:1.62;white-space:pre;letter-spacing:-.01em}}
  .l b{{color:{CORAL};font-weight:700}}
  .gap{{flex:none;height:11px}}
  .cmd{{color:{COLORS['cmd']}}} .out{{color:{COLORS['out']}}}
  .file{{color:{COLORS['file']};font-size:14px;opacity:.85}}
  .pass{{color:{COLORS['pass']}}} .good{{color:{COLORS['good']};font-weight:700;font-size:16px}}
  .fail{{color:{COLORS['fail']};font-weight:700}} .note{{color:{COLORS['note']};font-style:italic}}
  .caret{{display:inline-block;width:8px;height:15px;margin-left:3px;
          background:{CORAL};vertical-align:-2px}}
  .side{{display:flex;flex-direction:column;justify-content:center;gap:26px;
         padding:26px 22px;border-left:1px solid rgba(255,244,232,.12);
         background:#15161b}}
  .side h1{{color:{CORAL};font-size:11px;font-weight:700;letter-spacing:.12em;
            text-transform:uppercase}}
  .grid{{display:flex;flex-wrap:wrap;align-items:flex-end;gap:16px}}
  figure{{display:grid;justify-items:center;gap:7px}}
  figure img{{display:block;border-radius:20%;image-rendering:pixelated}}
  figcaption{{color:{MUTED};font-size:10px}}
  .side p{{color:rgba(255,244,232,.66);font-size:12px;line-height:1.6}}
  .side p em{{color:{PAPER};font-style:normal}}
</style>
<div class="term">
  <div class="bar"><span></span><span></span><span></span><p>iconflow demo</p></div>
  <div class="log">{''.join(body)}</div>
</div>
<div class="side">
  <div><h1>One master</h1><div class="grid">{sizes_panel()}</div></div>
  <p>Every size is rendered from the same SVG through a pinned Chromium.<br><br>
     <em>ship</em> fails closed unless the receipt still matches the source.</p>
</div>
"""


def escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main() -> int:
    lines = load_transcript()
    frames: list[Image.Image] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--force-color-profile=srgb"])
        try:
            context = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
                java_script_enabled=False,
                service_workers="block",
                locale="en-US",
                timezone_id="UTC",
            )
            # Nothing may be fetched: every asset is inlined as a data URI.
            context.route("**/*", lambda route: route.abort("blockedbyclient"))
            page = context.new_page()
            for shown in range(1, len(lines) + 1, STEP):
                page.set_content(document(lines, shown), wait_until="domcontentloaded")
                frames.append(Image.open(BytesIO(page.screenshot(type="png"))).convert("RGB"))
            page.set_content(document(lines, len(lines)), wait_until="domcontentloaded")
            frames.append(Image.open(BytesIO(page.screenshot(type="png"))).convert("RGB"))
            context.close()
        finally:
            browser.close()

    palette = frames[-1].quantize(colors=64, method=Image.MEDIANCUT)
    quantized = [frame.quantize(palette=palette, dither=Image.NONE) for frame in frames]
    durations = [FRAME_MS] * (len(quantized) - 1) + [HOLD_MS]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        OUTPUT, save_all=True, append_images=quantized[1:],
        duration=durations, loop=0, optimize=True, disposal=2,
    )
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Rendered {OUTPUT.relative_to(ROOT)} — "
          f"{len(quantized)} frames, {WIDTH}x{HEIGHT}, {size_kb:.0f} KB")
    if size_kb > 3000:
        print("warning: over 3 MB; a README image that slow is a cost, not an asset",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"README demo render failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
