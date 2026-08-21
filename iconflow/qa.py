# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Automated, fast sanity checks. These catch the failure modes that AI-authored
SVG icons most often hit; they do NOT replace the agent's visual review of the
contact sheet. Returns a list of human-readable warnings (empty == clean).

Every warning is a :class:`Finding`: a plain ``str`` for human output that also
carries the stable machine ``code`` published in ``docs/AGENT_CONTRACT.md``.
"""
from __future__ import annotations

import io
import re
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from . import assemble
from .rasterize import Rasterizer, load_svg


class Finding(str):
    """A human-readable warning that also carries a stable machine code.

    It *is* the message string, so every existing caller, receipt, and test
    keeps working; ``--json`` consumers read ``.code`` instead of parsing prose.
    """

    code: str

    def __new__(cls, code: str, message: str) -> "Finding":
        finding = super().__new__(cls, message)
        finding.code = code
        return finding

    def __reduce__(self):
        return (Finding, (self.code, str(self)))


# Fallback classification for warnings that arrive as plain strings (for
# example from an older receipt or a mocked check). First match wins.
_CODE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"^SVG (?:contains|references)", "svg-safety"),
    (r"^SVG uses a live <text>", "distinctiveness-text"),
    (r"^SVG has no viewBox|^viewBox is not square", "viewbox"),
    (r"^stroke-width=", "stroke-floor"),
    (r"^At 16px the mark", "coverage-16"),
    (r"^Low contrast on", "contrast"),
    (r"^Final maskable asset audit", "maskable-detail"),
    (r"^The macOS tray template keeps none", "tray-template-featureless"),
    (r"tray template cannot be derived", "tray-template-underivable"),
)


def warning_code(warning: str) -> str:
    """Return the stable machine code for a warning message."""
    code = getattr(warning, "code", None)
    if code:
        return str(code)
    for pattern, known in _CODE_PATTERNS:
        if re.search(pattern, warning):
            return known
    return "qa-warning"


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


def _renderer_safety_warnings(svg_text: str) -> list[Finding]:
    """Explain content that the deterministic renderer intentionally disables."""
    warnings: list[Finding] = []
    if _ACTIVE_ELEMENT_RE.search(svg_text):
        warnings.append(Finding(
            "svg-safety",
            "SVG contains script, embedded active content, or animation; "
            "IconFlow disables it for safe deterministic rendering.",
        ))
    elif _EVENT_HANDLER_RE.search(svg_text):
        warnings.append(Finding(
            "svg-safety",
            "SVG contains event-handler JavaScript; IconFlow disables it for safe rendering.",
        ))
    css_urls = (
        value.strip().strip("\"'").strip().lower()
        for value in _CSS_URL_RE.findall(svg_text)
    )
    external_css = any(
        value and not value.startswith(("#", "data:", "blob:"))
        for value in css_urls
    )
    if _EXTERNAL_ATTR_RE.search(svg_text) or external_css or _CSS_IMPORT_RE.search(svg_text):
        warnings.append(Finding(
            "svg-safety",
            "SVG references an external resource; IconFlow blocks all network/file "
            "resources. Inline it (data URI or SVG definition) before shipping.",
        ))
    return warnings


def _distinctiveness_warnings(svg_text: str) -> list[Finding]:
    """Advisory: flag the mechanically-detectable form of the monogram trap.

    A live ``<text>`` glyph is a typed-letter monogram — the most common way an
    AI icon is legible yet generic. The deeper distinctiveness call (a path-drawn
    letter, a generic silhouette) is not mechanically separable from good marks,
    so it stays with the human name-the-thing gate in the review rubric.
    """
    warnings: list[Finding] = []
    if _LIVE_TEXT_RE.search(svg_text):
        warnings.append(Finding(
            "distinctiveness-text",
            "SVG uses a live <text>/<tspan> glyph. A bare letter on a tile is the "
            "monogram trap — legible but low on distinctiveness (see "
            "docs/CONCEPTING.md 'Distinctiveness = specificity') — and live text "
            "renders via the build machine's fonts, so it is non-deterministic. "
            "Fuse the letter into an object (fado's plate-F) or use a specific "
            "object silhouette; if the letterform is intentional, convert it to a "
            "<path>.",
        ))
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


# A tray source whose interior is opaque everywhere renders a perfectly good
# colour icon and a featureless black blob in the macOS menu bar: the colour
# reduction keeps hue, the alpha reduction keeps only the outline and whatever
# is genuinely cut through it (docs/LEARNINGS.md L42, L48). These thresholds
# separate "the template lost the mark's features" from "the mark never had
# interior features", measured on the exact 32px bytes the build emits.
_TEMPLATE_PROBE_SIZE = 32
_TEMPLATE_MIN_INTERIOR = 32        # px of interior; below this there is nothing to judge
_TEMPLATE_COLOUR_STRUCTURE = 0.15  # interior edge ratio that counts as "has features"
_TEMPLATE_MAX_BLOB_HOLES = 2       # enclosed transparent px that still reads as a blob


def _erode(mask: Image.Image, passes: int = 2) -> Image.Image:
    """Shrink a binary mask so its own outer contour stops counting as detail."""
    for _ in range(passes):
        mask = mask.filter(ImageFilter.MinFilter(3))
    return mask


def _interior_edge_ratio(gray: Image.Image, interior: Image.Image) -> tuple[float, int]:
    """Fraction of interior pixels carrying a visible edge, plus the sample size."""
    edges = _pixels(gray.filter(ImageFilter.FIND_EDGES))
    inside = [value for value, keep in zip(edges, _pixels(interior)) if keep >= 128]
    if not inside:
        return 0.0, 0
    return sum(1 for value in inside if value > 40) / len(inside), len(inside)


def _enclosed_transparent_pixels(alpha: Image.Image) -> int:
    """Transparent pixels the border cannot reach — the mark's real holes.

    A macOS template carries no colour, so everything it can still say lives in
    its outer contour and in the cuts punched clean through it. Counting the
    enclosed transparent pixels is therefore a direct measure of how much the
    template has left to say.
    """
    width, height = alpha.size
    solid = [value >= 128 for value in _pixels(alpha)]
    seen = [False] * (width * height)
    queue: deque[int] = deque()

    def push(index: int) -> None:
        if not solid[index] and not seen[index]:
            seen[index] = True
            queue.append(index)

    for x in range(width):
        push(x)
        push((height - 1) * width + x)
    for y in range(height):
        push(y * width)
        push(y * width + width - 1)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                push(ny * width + nx)
    return sum(1 for index, filled in enumerate(solid) if not filled and not seen[index])


def tray_template_warnings(
    tray_svg: str | Path, *, template_mode: str = "auto",
    rasterizer: Rasterizer | None = None,
) -> list[Finding]:
    """Advisory: does the macOS template keep anything the colour tray shows?

    Colour reduction and alpha reduction discard different information, so a
    tray source can pass every other check and still ship a black lozenge to the
    menu bar. This audits the two reductions the build actually emits from one
    source and reports when the second one keeps none of the first one's
    features.

    Deliberately NOT part of :func:`check`: it needs a tray source rather than
    the master, and it is a heuristic about a linked variant, so it advises the
    designer instead of gating ``ship``.
    """
    if template_mode not in {"auto", "alpha", "contrast"}:
        raise ValueError("template mode must be 'auto', 'alpha', or 'contrast'")
    text = load_svg(tray_svg)

    def audit(active: Rasterizer) -> list[Finding]:
        colour_png = active.render(text, _TEMPLATE_PROBE_SIZE)
        try:
            template_png = assemble.to_template(colour_png, template_mode)
        except ValueError as exc:
            return [Finding(
                "tray-template-underivable",
                f"The '{template_mode}' tray template cannot be derived from this "
                f"source: {exc}",
            )]
        colour = Image.open(io.BytesIO(colour_png)).convert("RGBA")
        template_alpha = (
            Image.open(io.BytesIO(template_png)).convert("RGBA").getchannel("A")
        )
        footprint = colour.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
        flat = Image.new("RGB", colour.size, (128, 128, 128))
        flat.paste(colour, (0, 0), colour)
        structure, interior = _interior_edge_ratio(flat.convert("L"), _erode(footprint))
        holes = _enclosed_transparent_pixels(template_alpha)
        if (
            interior >= _TEMPLATE_MIN_INTERIOR
            and structure >= _TEMPLATE_COLOUR_STRUCTURE
            and holes <= _TEMPLATE_MAX_BLOB_HOLES
        ):
            return [Finding(
                "tray-template-featureless",
                f"The macOS tray template keeps none of this source's features: "
                f"{structure * 100:.0f}% of the colour mark's interior carries visible "
                f"detail, but the derived template has {holes} enclosed transparent "
                "pixel(s) and reads as a featureless silhouette on the menu bar. "
                "Colour and alpha are two different reductions of one source "
                "(docs/LEARNINGS.md L42): cut the one feature that identifies the mark "
                "— an eye, a counter, a seam — clean through the tray source as a broad "
                "transparent hole, placed away from any join between two shapes.",
            )]
        return []

    if rasterizer is None:
        with Rasterizer() as owned:
            return audit(owned)
    return audit(rasterizer)


def check(
    master_svg: str | Path, *, maskable: bool = True,
    maskable_bg: str = "#ffffff", rasterizer: Rasterizer | None = None,
) -> list[Finding]:
    warnings: list[Finding] = []
    text = load_svg(master_svg)
    warnings.extend(_renderer_safety_warnings(text))
    warnings.extend(_distinctiveness_warnings(text))
    if maskable:
        assemble.opaque_color(maskable_bg, "maskable background color")

    viewbox = _VIEWBOX_RE.search(text)
    if not re.search(r"\bviewBox\s*=", text, re.I):
        warnings.append(Finding(
            "viewbox", "SVG has no viewBox — it will not scale cleanly. Add one.",
        ))
    if viewbox:
        w, h = float(viewbox.group(1)), float(viewbox.group(2))
        if abs(w - h) > 0.5:
            warnings.append(Finding(
                "viewbox", f"viewBox is not square ({w}x{h}) — icons must be 1:1.",
            ))
    else:
        w = h = 1024.0

    # Very thin strokes vanish at 16px. Rule of thumb from the playbook:
    # keep line marks at least about 2.3% of the viewBox width.
    stroke_floor = w * 0.023
    for stroke_match in _STROKE_WIDTH_RE.findall(text):
        sw = next(value for value in stroke_match if value)
        if float(sw) and float(sw) < stroke_floor:
            warnings.append(Finding(
                "stroke-floor",
                f"stroke-width={sw} is very thin for a {w:.0f}px viewBox and may disappear at 16px.",
            ))
            break

    def render_checks(r: Rasterizer):
        im16 = Image.open(io.BytesIO(r.render(text, 16))).convert("RGBA")
        im32 = Image.open(io.BytesIO(r.render(text, 32))).convert("RGBA")
        if maskable:
            maskable_png = assemble.maskable_asset(r.render(text, 512), maskable_bg)
            im512 = Image.open(io.BytesIO(maskable_png)).convert("RGBA")
        else:
            im512 = None
        return im16, im32, im512

    if rasterizer is None:
        with Rasterizer() as owned_rasterizer:
            im16, im32, im512 = render_checks(owned_rasterizer)
    else:
        im16, im32, im512 = render_checks(rasterizer)

    cov = _alpha_coverage(im16)
    if cov < 0.06:
        warnings.append(Finding(
            "coverage-16",
            f"At 16px the mark fills only {cov*100:.0f}% of the canvas — too small/thin.",
        ))
    # Edge-to-edge only matters when the artwork is a HARD square reaching the
    # corners — a maskable/adaptive (circle) crop will clip it. A rounded
    # full-bleed container (app-icon squircle) leaves the corners transparent
    # and is intentional, so don't flag it.
    if cov > 0.97 and _corners_opaque(im16):
        warnings.append(Finding(
            "coverage-16",
            "At 16px the mark is a hard square reaching the corners — "
            "a maskable/adaptive (circle) crop will clip it. Round the "
            "container corners or add safe-area padding.",
        ))

    if _luma_spread(im16, (255, 255, 255)) < 0.06:
        warnings.append(Finding(
            "contrast", "Low contrast on WHITE at 16px — mark may be invisible on light UI.",
        ))
    if _luma_spread(im16, (11, 13, 18)) < 0.06:
        warnings.append(Finding(
            "contrast", "Low contrast on DARK at 16px — mark may be invisible on dark UI/taskbar.",
        ))

    if _luma_spread(im32, (128, 128, 128)) < 0.04:
        warnings.append(Finding(
            "contrast", "Low contrast on MID-GRAY at 32px — weak on neutral backgrounds.",
        ))

    if im512 is not None:
        outside_ratio = _detail_outside_safe_zone(im512)
        if outside_ratio > 0.08:
            warnings.append(Finding(
                "maskable-detail",
                "Final maskable asset audit: visible detail sits outside the central 40% "
                "safe-zone circle "
                f"({outside_ratio*100:.0f}% of detected detail). Review the maskable preview.",
            ))

    return warnings
