"""Automated, fast sanity checks. These catch the failure modes that AI-authored
SVG icons most often hit; they do NOT replace the agent's visual review of the
contact sheet. Returns a list of human-readable warnings (empty == clean)."""
from __future__ import annotations

import io
import re
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from . import assemble
from .rasterize import Rasterizer, load_svg

_VIEWBOX_RE = re.compile(
    r'viewBox\s*=\s*["\']\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)\s*["\']',
    re.I,
)
_STROKE_WIDTH_RE = re.compile(
    r'(?:stroke-width\s*=\s*["\']([\d.]+)|stroke-width\s*:\s*([\d.]+))',
    re.I,
)
_ACTIVE_ELEMENT_RE = re.compile(
    r"<(?:script|iframe|object|embed|audio|video|animate|animateMotion|animateTransform|set)\b",
    re.I,
)
_EVENT_HANDLER_RE = re.compile(r"\s+on[a-z]+\s*=", re.I)
_EXTERNAL_ATTR_RE = re.compile(
    r"\b(?:href|src)\s*=\s*([\"'])(?!\s*(?:#|data:|blob:))[^\"']+\1",
    re.I,
)
_CSS_URL_RE = re.compile(r"url\(\s*([^)]+?)\s*\)", re.I)
_CSS_IMPORT_RE = re.compile(
    r"@import\s+(?:url\(\s*)?[\"']?(?!data:|blob:|#)([^\s\"') ;]+)", re.I
)
# A live <text>/<tspan> glyph is almost always a typed-letter monogram — the
# laziest and least distinctive icon (the "monogram trap", see docs/CONCEPTING.md)
# — and it also renders via the build machine's fonts, so it is non-deterministic.
# This is the ONE distinctiveness signal that is mechanically safe: empirically, a
# path-DRAWN letter (e.g. an "H") is raster-indistinguishable from a good abstract
# mark (e.g. a route node), so path monograms are left to the human name-the-thing
# gate; only live text is flagged here.
_LIVE_TEXT_RE = re.compile(r"<text[\s>]|<tspan[\s>]", re.I)


def _renderer_safety_warnings(svg_text: str) -> list[str]:
    """Explain content that the deterministic renderer intentionally disables."""
    warnings: list[str] = []
    if _ACTIVE_ELEMENT_RE.search(svg_text):
        warnings.append(
            "SVG contains script, embedded active content, or animation; "
            "IconFlow disables it for safe deterministic rendering."
        )
    elif _EVENT_HANDLER_RE.search(svg_text):
        warnings.append(
            "SVG contains event-handler JavaScript; IconFlow disables it for safe rendering."
        )
    css_urls = (
        value.strip().strip("\"'").strip().lower()
        for value in _CSS_URL_RE.findall(svg_text)
    )
    external_css = any(
        value and not value.startswith(("#", "data:", "blob:"))
        for value in css_urls
    )
    if _EXTERNAL_ATTR_RE.search(svg_text) or external_css or _CSS_IMPORT_RE.search(svg_text):
        warnings.append(
            "SVG references an external resource; IconFlow blocks all network/file "
            "resources. Inline it (data URI or SVG definition) before shipping."
        )
    return warnings


def _distinctiveness_warnings(svg_text: str) -> list[str]:
    """Advisory: flag the mechanically-detectable form of the monogram trap.

    A live ``<text>`` glyph is a typed-letter monogram — the most common way an
    AI icon is legible yet generic. The deeper distinctiveness call (a path-drawn
    letter, a generic silhouette) is not mechanically separable from good marks,
    so it stays with the human name-the-thing gate in the review rubric.
    """
    warnings: list[str] = []
    if _LIVE_TEXT_RE.search(svg_text):
        warnings.append(
            "SVG uses a live <text>/<tspan> glyph. A bare letter on a tile is the "
            "monogram trap — legible but low on distinctiveness (see "
            "docs/CONCEPTING.md 'Distinctiveness = specificity') — and live text "
            "renders via the build machine's fonts, so it is non-deterministic. "
            "Fuse the letter into an object (fado's plate-F) or use a specific "
            "object silhouette; if the letterform is intentional, convert it to a "
            "<path>."
        )
    return warnings


def _pixels(im: Image.Image):
    if hasattr(im, "get_flattened_data"):
        return im.get_flattened_data()
    return im.getdata()


def _alpha_coverage(im: Image.Image) -> float:
    a = im.getchannel("A")
    px = list(_pixels(a))
    return sum(1 for v in px if v > 16) / len(px)


def _corners_opaque(im: Image.Image, thresh: int = 200) -> bool:
    """True if all four extreme corner pixels are (near-)opaque, i.e. the artwork
    is a hard square reaching the corners. Any rounded container (squircle /
    rounded-rect) leaves the very corner pixel transparent — even a small radius
    at 16px — so this returns False for app-icon style backgrounds, letting us
    skip the safe-area warning for those."""
    w, h = im.size
    a = im.getchannel("A")
    pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    return all(a.getpixel(p) >= thresh for p in pts)


def _luma_spread(im: Image.Image, bg=(255, 255, 255)) -> float:
    """Std-dev of luminance after compositing on bg, 0..1. Low spread at 16px
    means the mark collapses into a featureless blob — a legibility red flag."""
    flat = Image.new("RGB", im.size, bg)
    flat.paste(im, (0, 0), im)
    px = list(_pixels(flat))
    lum = [(0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 for r, g, b in px]
    mean = sum(lum) / len(lum)
    var = sum((v - mean) ** 2 for v in lum) / len(lum)
    return var ** 0.5


def _detail_outside_safe_zone(im: Image.Image) -> float:
    """Ratio of high-frequency visual detail outside the maskable safe circle.

    The safe-zone rule is about essential content, not full-bleed background
    color. Comparing the icon to a blurred copy catches glyphs, cuts, text and
    strokes while mostly ignoring smooth app-card backgrounds. The outer 12%
    frame is ignored so rounded-card edges do not dominate the warning.
    """
    im = im.convert("RGBA")
    flat = Image.new("RGB", im.size, (255, 255, 255))
    flat.paste(im.convert("RGB"), (0, 0), im.getchannel("A"))
    radius = max(2, min(im.size) // 48)
    detail = ImageChops.difference(flat, flat.filter(ImageFilter.GaussianBlur(radius))).convert("L")

    # A maskable asset may contain a large app-card/container whose outside edge
    # is intentionally non-essential. Find the flat canvas connected to the
    # image border, then suppress only the outer boundary of a large enclosed
    # region. Internal cuts and marks remain auditable; a small edge glyph does
    # not qualify as a container and is therefore never hidden by this rule.
    w, h = im.size
    corner_colors = [
        flat.getpixel((0, 0)), flat.getpixel((w - 1, 0)),
        flat.getpixel((0, h - 1)), flat.getpixel((w - 1, h - 1)),
    ]
    canvas_color = tuple(
        sorted(color[channel] for color in corner_colors)[2]
        for channel in range(3)
    )

    def is_canvas(x: int, y: int) -> bool:
        return max(abs(value - canvas_color[index])
                   for index, value in enumerate(flat.getpixel((x, y)))) <= 8

    exterior = bytearray(w * h)
    queue: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            index = y * w + x
            if not exterior[index] and is_canvas(x, y):
                exterior[index] = 1
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            index = y * w + x
            if not exterior[index] and is_canvas(x, y):
                exterior[index] = 1
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                continue
            index = ny * w + nx
            if not exterior[index] and is_canvas(nx, ny):
                exterior[index] = 1
                queue.append((nx, ny))

    enclosed_ratio = 1 - sum(exterior) / (w * h)
    container_edge = Image.new("L", (w, h), 0)
    if enclosed_ratio >= 0.30:
        edge = container_edge.load()
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                index = y * w + x
                if exterior[index]:
                    continue
                if (exterior[index - 1] or exterior[index + 1]
                        or exterior[index - w] or exterior[index + w]):
                    edge[x, y] = 255
        filter_size = radius * 2 + 1
        container_edge = container_edge.filter(ImageFilter.MaxFilter(filter_size))

    cx, cy = w / 2, h / 2
    safe_r = min(w, h) * 0.40
    margin = min(w, h) * 0.12
    total = 0
    outside = 0
    for y in range(h):
        for x in range(w):
            value = detail.getpixel((x, y))
            if value <= 22:
                continue
            if container_edge.getpixel((x, y)):
                continue
            if x < margin or y < margin or x >= w - margin or y >= h - margin:
                continue
            total += 1
            if (x - cx) ** 2 + (y - cy) ** 2 > safe_r ** 2:
                outside += 1
    return outside / total if total else 0.0


def check(
    master_svg: str | Path, *, maskable: bool = True,
    maskable_bg: str = "#ffffff"
) -> list[str]:
    warnings: list[str] = []
    text = load_svg(master_svg)
    warnings.extend(_renderer_safety_warnings(text))
    warnings.extend(_distinctiveness_warnings(text))
    if maskable:
        assemble.opaque_color(maskable_bg, "maskable background color")

    viewbox = _VIEWBOX_RE.search(text)
    if not re.search(r"\bviewBox\s*=", text, re.I):
        warnings.append("SVG has no viewBox — it will not scale cleanly. Add one.")
    if viewbox:
        w, h = float(viewbox.group(1)), float(viewbox.group(2))
        if abs(w - h) > 0.5:
            warnings.append(f"viewBox is not square ({w}x{h}) — icons must be 1:1.")
    else:
        w = h = 1024.0

    # Very thin strokes vanish at 16px. Rule of thumb from the playbook:
    # keep line marks at least about 2.3% of the viewBox width.
    stroke_floor = w * 0.023
    for stroke_match in _STROKE_WIDTH_RE.findall(text):
        sw = next(value for value in stroke_match if value)
        if float(sw) and float(sw) < stroke_floor:
            warnings.append(
                f"stroke-width={sw} is very thin for a {w:.0f}px viewBox and may disappear at 16px."
            )
            break

    with Rasterizer() as r:
        im16 = Image.open(io.BytesIO(r.render(text, 16))).convert("RGBA")
        im32 = Image.open(io.BytesIO(r.render(text, 32))).convert("RGBA")
        if maskable:
            maskable_png = assemble.maskable_asset(r.render(text, 512), maskable_bg)
            im512 = Image.open(io.BytesIO(maskable_png)).convert("RGBA")
        else:
            im512 = None

    cov = _alpha_coverage(im16)
    if cov < 0.06:
        warnings.append(
            f"At 16px the mark fills only {cov*100:.0f}% of the canvas — too small/thin."
        )
    # Edge-to-edge only matters when the artwork is a HARD square reaching the
    # corners — a maskable/adaptive (circle) crop will clip it. A rounded
    # full-bleed container (app-icon squircle) leaves the corners transparent
    # and is intentional, so don't flag it.
    if cov > 0.97 and _corners_opaque(im16):
        warnings.append("At 16px the mark is a hard square reaching the corners — "
                        "a maskable/adaptive (circle) crop will clip it. Round the "
                        "container corners or add safe-area padding.")

    if _luma_spread(im16, (255, 255, 255)) < 0.06:
        warnings.append("Low contrast on WHITE at 16px — mark may be invisible on light UI.")
    if _luma_spread(im16, (11, 13, 18)) < 0.06:
        warnings.append("Low contrast on DARK at 16px — mark may be invisible on dark UI/taskbar.")

    if _luma_spread(im32, (128, 128, 128)) < 0.04:
        warnings.append("Low contrast on MID-GRAY at 32px — weak on neutral backgrounds.")

    if im512 is not None:
        outside_ratio = _detail_outside_safe_zone(im512)
        if outside_ratio > 0.08:
            warnings.append(
                "Final maskable asset audit: visible detail sits outside the central 40% "
                "safe-zone circle "
                f"({outside_ratio*100:.0f}% of detected detail). Review the maskable preview."
            )

    return warnings
