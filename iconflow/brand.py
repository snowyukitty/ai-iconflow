# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The brand kit: one approved mark, every surface outside the favicon set.

``ship`` turns ``master.svg`` into icons. A product's identity reaches much
further — the site header, press-kit lockups, app tiles, social and Open
Graph cards, repository banners — and before 0.7 every one of those was
re-rendered by hand-written project scripts when the mark changed (L45 asks
for one source-bound transaction). ``iconflow brand`` makes the rest of the
transaction:

* it refuses an unapproved mark (the same receipt or approved config ``ship``
  honours), so a brand kit can never carry a mark that skipped review;
* from ``master.svg`` plus an **outlined** wordmark SVG it writes lockups
  (horizontal and stacked, for dark and for light grounds, as SVG and PNG),
  app tiles, a clear-space and minimum-size sheet, social card templates
  (Open Graph 1200x630, GitHub 1280x640, banner 1500x500) and a contact sheet
  of the whole kit to review;
* it records every file it wrote, the project's ``ship`` output, and every
  source by SHA-256 in ``brand-manifest.json``; when the mark changes, the
  previous mark's hashes move to ``retired``;
* ``iconflow brand sync --project DIR`` lists every file in a consuming
  project — including PNGs inlined as data URLs in HTML, CSS, JS and TS —
  that still carries a retired mark's bytes.

The wordmark must be outlined paths. Live ``<text>`` renders with whatever
fonts the build machine has and carries a font licence IconFlow cannot see,
so it is refused; ``iconflow brand outline`` (optional ``fontTools``) turns
a local, licence-checked font into an outlined wordmark.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from .findings import Finding

MANIFEST = "brand-manifest.json"
MANIFEST_SCHEMA = 1
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

#: Lockup geometry, as fractions of the mark's height.
DEFAULT_WORDMARK_SCALE = 0.42   # wordmark height beside the mark
DEFAULT_CLEAR_SPACE = 0.25      # the clear-space unit x around a lockup
STACKED_WORDMARK_SCALE = 0.30
HORIZONTAL_GAP = 0.22
STACKED_GAP = 0.16
TILE_SIZES = (1024, 512, 192)
TILE_SCALE = 0.78
TILE_RADIUS = 0.22
LOCKUP_PNG_HEIGHT = 512
#: The smallest rendered wordmark height that still reads, in pixels.
MIN_WORDMARK_PX = 10
SOCIAL_CARDS = (
    ("og-1200x630", 1200, 630, "Open Graph / link previews"),
    ("github-social-1280x640", 1280, 640, "GitHub repository social preview"),
    ("banner-1500x500", 1500, 500, "profile and README banner"),
)
SCAN_SUFFIXES = {".png", ".ico", ".icns", ".svg", ".webp", ".jpg", ".jpeg", ".gif"}
TEXT_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".json",
                 ".md", ".vue", ".svelte", ".astro", ".xml", ".webmanifest"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", ".mypy_cache",
             ".ruff_cache", ".pytest_cache", "target", ".next", ".turbo", ".cache"}
MAX_SCAN_BYTES = 20 * 1024 * 1024
_DATA_URL_RE = re.compile(rb"data:image/(?:png|x-icon|vnd\.microsoft\.icon|webp|jpeg|gif);base64,([A-Za-z0-9+/=]+)")


class BrandError(ValueError):
    """A brand kit that cannot be built honestly."""


@dataclass(frozen=True)
class BrandSpec:
    name: str
    master: Path
    wordmark: Path
    tagline: Path | None
    dark: str
    light: str
    ink_on_dark: str
    ink_on_light: str
    output: Path
    wordmark_scale: float = DEFAULT_WORDMARK_SCALE
    clear_space: float = DEFAULT_CLEAR_SPACE


def spec_from_config(config, *, output: str | Path | None = None) -> BrandSpec:
    """Read ``[brand]`` from a project config; colours default to the build's."""
    from . import assemble

    table = dict(getattr(config, "brand", {}) or {})
    if not table.get("wordmark"):
        raise BrandError(
            "iconflow.toml needs a [brand] table with wordmark = \"wordmark.svg\" "
            "(an outlined wordmark; `iconflow brand outline` can make one from a local font)"
        )
    dark = table.get("dark") or config.theme_color
    light = table.get("light") or "#FFFFFF"

    def colour(value, label):
        try:
            red, green, blue, _ = assemble.opaque_color(value, f"brand.{label}")
        except ValueError as exc:
            raise BrandError(str(exc)) from exc
        return f"#{red:02X}{green:02X}{blue:02X}"

    dark, light = colour(dark, "dark"), colour(light, "light")
    return BrandSpec(
        name=config.name,
        master=config.master_path,
        wordmark=config.resolve(table["wordmark"]),
        tagline=config.resolve(table["tagline"]) if table.get("tagline") else None,
        dark=dark,
        light=light,
        ink_on_dark=colour(table.get("ink_on_dark") or light, "ink_on_dark"),
        ink_on_light=colour(table.get("ink_on_light") or dark, "ink_on_light"),
        output=Path(output) if output else config.resolve(table.get("output") or "brand-kit"),
        wordmark_scale=float(table.get("wordmark_scale", DEFAULT_WORDMARK_SCALE)),
        clear_space=float(table.get("clear_space", DEFAULT_CLEAR_SPACE)),
    )


# --------------------------------------------------------------------------
# SVG composition
# --------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _viewbox(root: ET.Element, label: str) -> tuple[float, float, float, float]:
    raw = root.get("viewBox")
    if not raw:
        raise BrandError(f"{label} has no viewBox; add one so it can be placed exactly")
    values = [float(v) for v in re.split(r"[\s,]+", raw.strip()) if v]
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise BrandError(f"{label} has an invalid viewBox: {raw!r}")
    return values[0], values[1], values[2], values[3]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


ACTIVE_ELEMENTS = {
    "script", "foreignobject", "iframe", "object", "embed", "audio", "video",
    "animate", "animatemotion", "animatetransform", "set", "handler", "listener",
}


def validate_tree(text: str, label: str, *, wordmark: bool) -> ET.Element:
    """Parse an SVG and refuse anything active, external, or unscoped.

    The check runs on the parsed tree, so a namespace prefix
    (``<s:script xmlns:s="http://www.w3.org/2000/svg">``) is seen for what it
    is. A wordmark is also refused live text (non-deterministic, unseen font
    licence) and ``<style>`` (selectors are global once nested next to the
    master and would repaint it).
    """
    from .qa import _renderer_safety_warnings
    from .rasterize import _validated_svg_text

    problems = _renderer_safety_warnings(text)
    if problems:
        raise BrandError(f"{label}: {problems[0]}")
    try:
        root = ET.fromstring(_validated_svg_text(text))
    except ET.ParseError as exc:
        raise BrandError(f"{label} is not well-formed SVG: {exc}") from exc
    for element in root.iter():
        name = _local(element.tag).lower()
        if name in ACTIVE_ELEMENTS:
            raise BrandError(f"{label} contains <{_local(element.tag)}>, which is active content")
        for key, value in element.attrib.items():
            attribute = _local(key).lower()
            if attribute.startswith("on"):
                raise BrandError(f"{label} has an event handler ({_local(key)})")
            if attribute in {"href", "src"} and not value.strip().startswith(("#", "data:image/")):
                raise BrandError(f"{label} references an external resource ({value[:60]})")
        if wordmark and name in {"text", "tspan", "textpath"}:
            raise BrandError(
                f"{label} uses live <text>: it would render with the build machine's fonts "
                "and carries a font licence IconFlow cannot check. Outline it (in a type tool, "
                "or with `iconflow brand outline --font <local font> --text ...`)."
            )
        if wordmark and name == "style":
            raise BrandError(
                f"{label} has a <style> element; its selectors would also apply to the mark "
                "it is placed beside. Use presentation attributes (fill=\"currentColor\")."
            )
    return root


def validate_wordmark(text: str, label: str) -> None:
    """A wordmark is outlined artwork: no live text, no CSS, nothing active or external."""
    validate_tree(text, label, wordmark=True)


def _prefixed(root: ET.Element, prefix: str) -> ET.Element:
    """Prefix every id and the references to it, and nothing else.

    Only fragment references are rewritten — ``url(#id)`` in an attribute and
    an ``href`` of exactly ``#id`` — so a colour such as ``fill="#fff"`` is
    never mistaken for a reference to an element called ``fff``. Sources that
    carry a stylesheet are not inlined at all (see :func:`_nest`).
    """
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    if not ids:
        return root
    url_ref = re.compile(r"url\(\s*(['\"]?)#([^)'\"\s]+)\1\s*\)", re.I)

    def rewrite_urls(value: str) -> str:
        return url_ref.sub(
            lambda m: f"url({m.group(1)}#{prefix}{m.group(2)}{m.group(1)})"
            if m.group(2) in ids else m.group(0),
            value,
        )

    for el in root.iter():
        for key, value in list(el.attrib.items()):
            if key == "id":
                el.set(key, prefix + value)
            elif _local(key) == "href" and value.startswith("#") and value[1:] in ids:
                el.set(key, f"#{prefix}{value[1:]}")
            elif "url(" in value.lower():
                el.set(key, rewrite_urls(value))
    return root


#: Root attributes that place an SVG; every other root attribute (stroke-width,
#: opacity, filter, clip-path, fill-rule, ...) changes how it looks and is kept.
_PLACEMENT_ATTRIBUTES = {"x", "y", "width", "height", "viewBox", "preserveAspectRatio",
                         "version", "baseProfile", "id"}


def _nest(text: str, *, x: float, y: float, width: float, height: float,
          prefix: str, color: str | None = None, label: str = "") -> ET.Element:
    """Place an SVG at the given box, keeping its own viewBox and appearance.

    A source with a ``<style>`` is embedded as an image (a data URI), so its
    selectors cannot reach the other half of the lockup and the other half's
    cannot reach it; a source without one is inlined, with its ids prefixed and
    its root's rendering attributes preserved.
    """
    root = validate_tree(text, label or prefix.rstrip("-"), wordmark=False)
    vb = _viewbox(root, label or prefix.rstrip("-"))
    box = {"x": _num(x), "y": _num(y), "width": _num(width), "height": _num(height)}
    if any(_local(el.tag) == "style" for el in root.iter()):
        data = base64.b64encode(text.encode("utf-8")).decode("ascii")
        image = ET.Element(f"{{{SVG_NS}}}image", {
            **box, "preserveAspectRatio": "xMidYMid meet",
            "href": f"data:image/svg+xml;base64,{data}",
        })
        return image
    root = _prefixed(root, prefix)
    nested = ET.Element(f"{{{SVG_NS}}}svg", {
        **box,
        "viewBox": " ".join(_num(v) for v in vb),
        "preserveAspectRatio": root.get("preserveAspectRatio", "xMidYMid meet"),
        "overflow": "visible",
    })
    for key, value in root.attrib.items():
        if _local(key) not in _PLACEMENT_ATTRIBUTES:
            nested.set(key, value)
    if color:
        nested.set("color", color)
    for child in list(root):
        nested.append(child)
    return nested


def _num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _document(width: float, height: float, children: list[ET.Element], *,
              background: str | None = None, title: str = "") -> str:
    root = ET.Element(f"{{{SVG_NS}}}svg", {
        "viewBox": f"0 0 {_num(width)} {_num(height)}",
        "width": _num(width), "height": _num(height),
    })
    if title:
        node = ET.SubElement(root, f"{{{SVG_NS}}}title")
        node.text = title
    if background:
        ET.SubElement(root, f"{{{SVG_NS}}}rect", {
            "width": _num(width), "height": _num(height), "fill": background,
        })
    for child in children:
        root.append(child)
    body = ET.tostring(root, encoding="unicode")
    return ("<!-- AUTO-GENERATED by iconflow brand from master.svg and the wordmark; "
            "rebuild, do not edit. -->\n" + body + "\n")


@dataclass(frozen=True)
class Layout:
    width: float
    height: float
    mark: tuple[float, float, float]           # x, y, size
    wordmark: tuple[float, float, float, float]  # x, y, w, h


def _aspect(text: str, label: str) -> float:
    from .rasterize import _validated_svg_text

    _x, _y, w, h = _viewbox(ET.fromstring(_validated_svg_text(text)), label)
    return w / h


def lockup_layout(kind: str, wordmark_aspect: float, *, mark: float = 512.0,
                  wordmark_scale: float = DEFAULT_WORDMARK_SCALE,
                  clear_space: float = DEFAULT_CLEAR_SPACE) -> Layout:
    """Place mark and wordmark with the clear-space unit around them.

    ``x`` (the clear-space unit) is ``clear_space`` times the mark height. The
    horizontal lockup sets the wordmark at ``wordmark_scale`` of the mark's
    height, optically centred on it; the stacked one centres the wordmark under
    the mark at a smaller scale.
    """
    unit = mark * clear_space
    if kind == "horizontal":
        wh = mark * wordmark_scale
        ww = wh * wordmark_aspect
        gap = mark * HORIZONTAL_GAP
        width = 2 * unit + mark + gap + ww
        height = 2 * unit + mark
        return Layout(width, height, (unit, unit, mark),
                      (unit + mark + gap, unit + (mark - wh) / 2, ww, wh))
    if kind == "stacked":
        wh = mark * STACKED_WORDMARK_SCALE
        ww = min(wh * wordmark_aspect, mark * 2.6)
        wh = ww / wordmark_aspect
        gap = mark * STACKED_GAP
        inner = max(mark, ww)
        width = 2 * unit + inner
        height = 2 * unit + mark + gap + wh
        return Layout(width, height, (unit + (inner - mark) / 2, unit, mark),
                      (unit + (inner - ww) / 2, unit + mark + gap, ww, wh))
    raise BrandError(f"unknown lockup kind: {kind}")


def lockup_svg(master_text: str, wordmark_text: str, *, kind: str, ink: str,
               background: str | None, spec: BrandSpec) -> tuple[str, Layout]:
    layout = lockup_layout(kind, _aspect(wordmark_text, "wordmark"),
                           wordmark_scale=spec.wordmark_scale, clear_space=spec.clear_space)
    mx, my, ms = layout.mark
    wx, wy, ww, wh = layout.wordmark
    children = [
        _nest(master_text, x=mx, y=my, width=ms, height=ms, prefix="mark-"),
        _nest(wordmark_text, x=wx, y=wy, width=ww, height=wh, prefix="word-", color=ink),
    ]
    return _document(layout.width, layout.height, children, background=background,
                     title=f"{spec.name} {kind} lockup"), layout


def social_svg(master_text: str, wordmark_text: str, tagline_text: str | None, *,
               width: int, height: int, spec: BrandSpec) -> str:
    """A social card: the horizontal lockup on the dark ground, tagline beneath."""
    layout = lockup_layout("horizontal", _aspect(wordmark_text, "wordmark"),
                           wordmark_scale=spec.wordmark_scale, clear_space=0)
    block_h = height * (0.36 if tagline_text else 0.44)
    scale = min(block_h / layout.height, (width * 0.82) / layout.width)
    block_w = layout.width * scale
    tag_h = height * 0.075 if tagline_text else 0
    gap = height * 0.07 if tagline_text else 0
    top = (height - (layout.height * scale + gap + tag_h)) / 2
    left = (width - block_w) / 2
    mx, my, ms = layout.mark
    wx, wy, ww, wh = layout.wordmark
    children = [
        _nest(master_text, x=left + mx * scale, y=top + my * scale, width=ms * scale,
              height=ms * scale, prefix="mark-"),
        _nest(wordmark_text, x=left + wx * scale, y=top + wy * scale, width=ww * scale,
              height=wh * scale, prefix="word-", color=spec.ink_on_dark),
    ]
    if tagline_text:
        aspect = _aspect(tagline_text, "tagline")
        tw = min(tag_h * aspect, width * 0.8)
        th = tw / aspect
        children.append(_nest(
            tagline_text, x=(width - tw) / 2, y=top + layout.height * scale + gap,
            width=tw, height=th, prefix="tag-", color=spec.ink_on_dark,
        ))
    return _document(width, height, children, background=spec.dark,
                     title=f"{spec.name} social card {width}x{height}")


# --------------------------------------------------------------------------
# Raster outputs
# --------------------------------------------------------------------------


def _png(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def _tile(mark_png: bytes, size: int, colour: str) -> bytes:
    from . import assemble

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size * 4 - 1, size * 4 - 1], radius=int(size * 4 * TILE_RADIUS), fill=255,
    )
    plate = Image.new("RGBA", (size, size), assemble.opaque_color(colour))
    canvas.paste(plate, (0, 0), mask.resize((size, size), Image.Resampling.LANCZOS))
    art = Image.open(io.BytesIO(mark_png)).convert("RGBA")
    canvas.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return _png(canvas)


def _contrast(a: str, b: str) -> float:
    from . import assemble

    def luminance(colour):
        channels = []
        for value in assemble.opaque_color(colour)[:3]:
            c = value / 255
            channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def clear_space_sheet(rasterizer, master_text: str, horizontal_svg: str, layout: Layout,
                      spec: BrandSpec) -> tuple[bytes, dict]:
    """The clear-space rule drawn on the lockup, plus the minimum sizes measured."""
    from . import ladder
    from .review import _font

    scale = 0.75
    lock_w, lock_h = int(round(layout.width * scale)), int(round(layout.height * scale))
    lock = Image.open(io.BytesIO(rasterizer.render_rect(
        horizontal_svg, lock_w, lock_h, bg=spec.light))).convert("RGBA")
    pad = 40
    sheet_w = max(lock_w + 2 * pad, 900)
    sheet = Image.new("RGBA", (sheet_w, lock_h + 380), (245, 242, 236, 255))
    draw = ImageDraw.Draw(sheet)
    title, small = _font(20), _font(14)
    draw.text((pad, 14), f"{spec.name} — clear space and minimum size", font=title, fill=(23, 24, 28))
    sheet.alpha_composite(lock, (pad, 50))
    unit = layout.mark[2] * spec.clear_space * scale
    x0, y0 = pad, 50
    box = [x0 + unit, y0 + unit, x0 + lock_w - unit, y0 + lock_h - unit]
    for i in range(int(box[0]), int(box[2]), 12):
        draw.line([(i, box[1]), (min(i + 6, box[2]), box[1])], fill=(255, 91, 61), width=2)
        draw.line([(i, box[3]), (min(i + 6, box[2]), box[3])], fill=(255, 91, 61), width=2)
    for j in range(int(box[1]), int(box[3]), 12):
        draw.line([(box[0], j), (box[0], min(j + 6, box[3]))], fill=(255, 91, 61), width=2)
        draw.line([(box[2], j), (box[2], min(j + 6, box[3]))], fill=(255, 91, 61), width=2)
    draw.rectangle([x0, y0, x0 + lock_w - 1, y0 + lock_h - 1], outline=(120, 122, 128), width=1)
    draw.text((pad, y0 + lock_h + 8),
              f"clear space x = {spec.clear_space:g} × mark height on every side (outer frame); "
              "nothing else enters it", font=small, fill=(23, 24, 28))
    min_lockup_h = math.ceil(MIN_WORDMARK_PX / (spec.wordmark_scale * layout.mark[2] / layout.height))
    minimums = {"mark_px": 16, "horizontal_lockup_height_px": int(min_lockup_h),
                "clear_space_unit": spec.clear_space}
    y = y0 + lock_h + 50
    draw.text((pad, y), "minimum sizes — actual pixels", font=small, fill=(23, 24, 28))
    y += 24
    x = pad
    source = ladder.RungSource(master_text)
    for size in (16, 24, 32):
        mark = Image.open(io.BytesIO(source.render(rasterizer, size))).convert("RGBA")
        sheet.alpha_composite(mark, (x, y))
        draw.text((x, y + 40), f"{size}px", font=small, fill=(90, 92, 98))
        x += 70
    small_w = int(round(layout.width * min_lockup_h / layout.height))
    tiny = Image.open(io.BytesIO(rasterizer.render_rect(
        horizontal_svg, max(1, small_w), max(1, min_lockup_h), bg=spec.light))).convert("RGBA")
    sheet.alpha_composite(tiny, (x + 20, y))
    draw.text((x + 20, y + 40), f"lockup at its minimum: {min_lockup_h}px tall "
              f"(wordmark {MIN_WORDMARK_PX}px)", font=small, fill=(90, 92, 98))
    zoom = tiny.resize((tiny.width * 4, tiny.height * 4), Image.Resampling.NEAREST)
    if zoom.width + 2 * pad <= sheet_w and y + 80 + zoom.height <= sheet.height:
        sheet.alpha_composite(zoom, (pad, y + 80))
        draw.text((pad + zoom.width + 12, y + 80), "the minimum lockup, 4x", font=small,
                  fill=(90, 92, 98))
    return _png(sheet), minimums


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------


@dataclass
class KitResult:
    files: list[dict] = field(default_factory=list)
    advisories: list[Finding] = field(default_factory=list)
    manifest: Path | None = None
    sheet: Path | None = None


def build_kit(spec: BrandSpec, *, approval: dict, ship_output: Path | None = None,
              shipped: list[str] | None = None,
              color_scheme: str = "light") -> KitResult:
    """Write the brand kit and its manifest. ``approval`` binds the mark's review."""
    from .config import svg_sha256
    from .rasterize import Rasterizer, load_svg

    master_text = load_svg(spec.master)
    wordmark_text = load_svg(spec.wordmark)
    validate_wordmark(wordmark_text, "wordmark")
    tagline_text = None
    if spec.tagline is not None:
        tagline_text = load_svg(spec.tagline)
        validate_wordmark(tagline_text, "tagline")
    from .build import _validate_output_tree

    result = KitResult()
    out = spec.output
    _validate_output_tree(out)        # no symlink or junction, at or under it
    out.mkdir(parents=True, exist_ok=True)

    def write(rel: str, data: bytes, kind: str, **extra) -> None:
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        result.files.append({"path": rel, "sha256": _sha256_bytes(data), "bytes": len(data),
                             "kind": kind, **extra})

    for ground, ink in (("dark", spec.ink_on_dark), ("light", spec.ink_on_light)):
        background = spec.dark if ground == "dark" else spec.light
        ratio = _contrast(ink, background)
        if ratio < 4.5:
            result.advisories.append(Finding(
                "brand-contrast",
                f"the wordmark ink {ink} on the {ground} ground {background} has a contrast "
                f"ratio of {ratio:.1f}:1 (WCAG asks 4.5:1 for text). Set brand.ink_on_{ground}.",
            ))
    if "currentColor" not in wordmark_text:
        result.advisories.append(Finding(
            "brand-wordmark-fixed-colour",
            "the wordmark does not use fill=\"currentColor\", so the dark and light lockups "
            "carry the same ink. Draw it with currentColor to let the kit recolour it.",
        ))

    sheet_cells: list[tuple[str, Image.Image]] = []
    horizontal_light = None
    horizontal_layout = None
    for scheme_ground in ("dark", "light"):
        scheme = "dark" if scheme_ground == "dark" else color_scheme
        ink = spec.ink_on_dark if scheme_ground == "dark" else spec.ink_on_light
        background = spec.dark if scheme_ground == "dark" else spec.light
        with Rasterizer(color_scheme=scheme) as r:
            for kind in ("horizontal", "stacked"):
                svg, layout = lockup_svg(master_text, wordmark_text, kind=kind, ink=ink,
                                         background=None, spec=spec)
                name = f"lockups/{kind}-on-{scheme_ground}"
                write(f"{name}.svg", svg.encode("utf-8"), "lockup-svg", ground=background)
                height = LOCKUP_PNG_HEIGHT
                width = int(round(layout.width * height / layout.height))
                png = r.render_rect(svg, width, height, bg=background)
                write(f"{name}.png", png, "lockup-png", ground=background, size=[width, height])
                sheet_cells.append((name, Image.open(io.BytesIO(png)).convert("RGBA")))
                if kind == "horizontal" and scheme_ground == "light":
                    horizontal_light, horizontal_layout = svg, layout
            for size in TILE_SIZES:
                art = r.render(master_text, int(round(size * TILE_SCALE)))
                tile = _tile(art, size, background)
                write(f"tiles/tile-{scheme_ground}-{size}.png", tile, "app-tile",
                      ground=background, size=[size, size])
            if scheme_ground == "dark":
                for slug, width, height, purpose in SOCIAL_CARDS:
                    svg = social_svg(master_text, wordmark_text, tagline_text,
                                     width=width, height=height, spec=spec)
                    write(f"social/{slug}.svg", svg.encode("utf-8"), "social-svg", purpose=purpose)
                    png = r.render_rect(svg, width, height, bg=spec.dark)
                    write(f"social/{slug}.png", png, "social-png", purpose=purpose,
                          size=[width, height])
                    sheet_cells.append((f"social/{slug}", Image.open(io.BytesIO(png)).convert("RGBA")))
    with Rasterizer(color_scheme=color_scheme) as r:
        png, minimums = clear_space_sheet(r, master_text, horizontal_light, horizontal_layout, spec)
        write("guides/clear-space-and-minimum-size.png", png, "guide", minimums=minimums)
        mark_raw = r.render(master_text, 1024)
        write("mark/mark-1024.png", mark_raw, "mark-png", size=[1024, 1024])
    write("mark/master.svg", master_text.encode("utf-8"), "mark-svg")

    result.sheet = out / "brand-sheet.png"
    contact = _kit_sheet(sheet_cells, spec)
    result.sheet.write_bytes(contact)

    manifest_path = out / MANIFEST
    previous = _read_manifest(manifest_path)
    mark_sha = svg_sha256(spec.master)
    # Only the files a gated ship wrote in this same run are known to carry this
    # mark — not the whole output tree, which may still hold files of earlier
    # marks and targets. Without a ship, the record of the same mark's earlier
    # ship is carried forward, so its icons are still retired when it changes.
    same_mark = bool(previous) and previous.get("mark_sha256") == svg_sha256(spec.master)
    known = list(previous.get("ship_outputs", [])) if same_mark else []
    if shipped is not None and ship_output is not None:
        known += [
            {"path": rel, "sha256": _sha256_bytes((ship_output / rel).read_bytes())}
            for rel in sorted(shipped) if (ship_output / rel).is_file()
        ]
    # Every proven output of this mark is kept — a later ship of fewer targets
    # must not forget the files an earlier one wrote, or they would never be
    # retired when the mark changes.
    seen: set[tuple[str, str]] = set()
    ship_files = []
    for entry in known:
        key = (entry["path"], entry["sha256"])
        if key not in seen:
            seen.add(key)
            ship_files.append(entry)
    retired = list(previous.get("retired", [])) if previous else []
    if previous and previous.get("mark_sha256") and previous["mark_sha256"] != mark_sha:
        retired.insert(0, {
            "mark_sha256": previous["mark_sha256"],
            "retired_on": datetime.now(timezone.utc).date().isoformat(),
            "files": [{"path": f["path"], "sha256": f["sha256"]}
                      for f in previous.get("files", []) + previous.get("ship_outputs", [])],
        })
    from . import __version__

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generator": f"iconflow {__version__}",
        "project": spec.name,
        "mark_sha256": mark_sha,
        "approval": approval,
        "sources": {
            "master": {"path": spec.master.name, "sha256": mark_sha},
            "wordmark": {"path": spec.wordmark.name, "sha256": svg_sha256(spec.wordmark)},
            "tagline": ({"path": spec.tagline.name, "sha256": svg_sha256(spec.tagline)}
                        if spec.tagline else None),
        },
        "colours": {"dark": spec.dark, "light": spec.light, "ink_on_dark": spec.ink_on_dark,
                    "ink_on_light": spec.ink_on_light},
        "geometry": {"wordmark_scale": spec.wordmark_scale, "clear_space": spec.clear_space,
                     "minimums": minimums},
        "files": result.files,
        "ship_outputs": ship_files,
        "retired": retired,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    result.manifest = manifest_path
    return result


def _kit_sheet(cells: list[tuple[str, Image.Image]], spec: BrandSpec) -> bytes:
    from .review import _font

    pad, row_h = 24, 220
    width = 1400
    images = []
    for name, image in cells:
        scale = min((width - 2 * pad) / image.width, (row_h - 30) / image.height, 1.0)
        images.append((name, image.resize(
            (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
            Image.Resampling.LANCZOS)))
    sheet = Image.new("RGBA", (width, 60 + len(images) * row_h), (23, 24, 28, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 16), f"{spec.name} brand kit — review every surface at this size",
              font=_font(20), fill=(245, 241, 232))
    y = 56
    for name, image in images:
        sheet.alpha_composite(image, (pad, y))
        draw.text((pad, y + image.height + 4), name, font=_font(13), fill=(169, 171, 180))
        y += row_h
    return _png(sheet)


def _read_manifest(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) and value.get("schema") == MANIFEST_SCHEMA else None


def _walk(root: Path):
    """Every regular file under ``root``, never following a link or junction."""
    import os
    import stat as stat_module

    from .build import _is_link_or_reparse_point

    for directory, folders, files in os.walk(root, followlinks=False):
        here = Path(directory)
        folders[:] = sorted(
            name for name in folders
            if name not in SKIP_DIRS and not _is_link_or_reparse_point(here / name)
        )
        for name in sorted(files):
            path = here / name
            try:
                info = path.lstat()
            except OSError:
                continue
            # Regular files only: never a link, junction, FIFO or device,
            # any of which could escape the root or block a read forever.
            if stat_module.S_ISREG(info.st_mode) and not _is_link_or_reparse_point(path):
                yield path


def _hash_tree(root: Path) -> list[dict]:
    files = []
    for path in _walk(root):
        if path.stat().st_size <= MAX_SCAN_BYTES:
            files.append({"path": path.relative_to(root).as_posix(),
                          "sha256": _sha256_bytes(path.read_bytes())})
    return files


# --------------------------------------------------------------------------
# Propagation report
# --------------------------------------------------------------------------


@dataclass
class SyncHit:
    path: str
    where: str          # "file", "svg-source" or "data-url"
    mark_sha256: str    # the retired mark it belongs to
    asset: str          # which asset of that mark it matches

    def as_dict(self) -> dict:
        return {"path": self.path, "where": self.where, "mark_sha256": self.mark_sha256,
                "asset": self.asset}


def sync_report(project: str | Path, manifests: list[dict]) -> tuple[list[SyncHit], int, int]:
    """Every file under ``project`` still carrying a retired mark.

    Matches whole files by SHA-256, SVG sources by the normalized SVG hash of a
    retired master, and PNG/ICO images inlined as base64 data URLs in text
    files. Returns (stale hits, current files found, files scanned).
    """
    from .config import svg_sha256

    retired: dict[str, tuple[str, str]] = {}
    current: set[str] = set()
    current_masters: set[str] = set()
    retired_masters: dict[str, str] = {}
    for manifest in manifests:
        if manifest.get("mark_sha256"):
            current_masters.add(manifest["mark_sha256"])
        for entry in manifest.get("files", []) + manifest.get("ship_outputs", []):
            current.add(entry["sha256"])
        for old in manifest.get("retired", []):
            retired_masters[old["mark_sha256"]] = old["mark_sha256"]
            for entry in old.get("files", []):
                retired.setdefault(entry["sha256"], (old["mark_sha256"], entry["path"]))
    for digest in list(retired):
        if digest in current:
            del retired[digest]   # unchanged across marks (a manifest, a font): not stale
    for digest in current_masters:
        retired_masters.pop(digest, None)   # A -> B -> A: the restored mark is current
    hits: list[SyncHit] = []
    found_current = 0
    scanned = 0
    # The project the caller named is resolved once, deliberately, and nothing
    # under it is followed out of it (see _walk).
    root = Path(project).resolve()
    for path in _walk(root):
        suffix = path.suffix.lower()
        if suffix not in SCAN_SUFFIXES and suffix not in TEXT_SUFFIXES:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_SCAN_BYTES or path.name == MANIFEST:
            continue
        data = path.read_bytes()
        scanned += 1
        rel = path.relative_to(root).as_posix()
        digest = _sha256_bytes(data)
        if digest in retired:
            mark, asset = retired[digest]
            hits.append(SyncHit(rel, "file", mark, asset))
            continue
        if digest in current:
            found_current += 1
        if suffix == ".svg":
            try:
                normalized = svg_sha256(path)
            except (OSError, ValueError):
                normalized = ""
            if normalized in retired_masters:
                hits.append(SyncHit(rel, "svg-source", normalized, "master.svg"))
                continue
        if suffix in TEXT_SUFFIXES and b"base64," in data:
            for match in _DATA_URL_RE.finditer(data):
                try:
                    blob = base64.b64decode(match.group(1), validate=False)
                except (ValueError, TypeError):
                    continue
                inner = _sha256_bytes(blob)
                if inner in retired:
                    mark, asset = retired[inner]
                    hits.append(SyncHit(rel, "data-url", mark, asset))
    return hits, found_current, scanned


# --------------------------------------------------------------------------
# Outlining a wordmark from a local font (optional dependency)
# --------------------------------------------------------------------------

PERMISSIVE_LICENCES = (
    "sil open font license", "open font license", "scripts.sil.org/ofl", "openfontlicense.org",
    "apache license", "apache.org/licenses", "ubuntu font licence", "mit license",
    "creative commons zero", "cc0", "public domain", "bitstream vera",
)


def font_licence(path: Path) -> dict:
    """What a font says about its licence, from its own name and OS/2 tables."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError as exc:
        raise BrandError(
            "outlining a wordmark needs fontTools: pip install \"iconflow[brand]\""
        ) from exc
    with TTFont(str(path), lazy=True) as font:
        names = font["name"]
        fields = {i: names.getDebugName(i) or "" for i in (1, 2, 5, 13, 14)}
        fs_type = int(getattr(font["OS/2"], "fsType", 0)) if "OS/2" in font else 0

    def name(name_id: int) -> str:
        return fields[name_id]

    text = f"{name(13)} {name(14)}".lower()
    permissive = any(marker in text for marker in PERMISSIVE_LICENCES)
    return {
        "family": name(1), "style": name(2), "version": name(5),
        "licence": name(13)[:300], "licence_url": name(14),
        "fs_type": fs_type, "restricted": bool(fs_type & 0x0002),
        "permissive": permissive,
        "sha256": _sha256_bytes(Path(path).read_bytes()),
    }


def outline_wordmark(text: str, font_path: str | Path, *, tracking: float = 0.0,
                     weight: float | None = None, licence_ok: str = "") -> tuple[str, dict]:
    """Outline ``text`` with a local font into a ``currentColor`` wordmark SVG.

    Refuses a font whose licence it cannot recognise as permissive, or whose
    OS/2 embedding bits say *restricted*, unless ``licence_ok`` records why the
    use is licensed. Layout is advance widths plus the legacy ``kern`` table:
    there is no shaping, so check kerning in a type tool before the wordmark
    ships.
    """
    font_path = Path(font_path)
    licence = font_licence(font_path)
    if (licence["restricted"] or not licence["permissive"]) and not licence_ok.strip():
        reason = ("its OS/2 embedding bits say restricted" if licence["restricted"]
                  else "its name table names no licence IconFlow recognises as permissive")
        raise BrandError(
            f"refusing to outline {font_path.name}: {reason} "
            f"({licence['licence'][:120] or 'no licence text'}). If you hold a licence that "
            "covers a logo, pass --licence-ok \"<what licence and where it is recorded>\"."
        )
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    font = TTFont(str(font_path))
    if "fvar" in font and weight is not None:
        from fontTools.varLib.instancer import instantiateVariableFont

        axes = {axis.axisTag for axis in font["fvar"].axes}
        if "wght" in axes:
            font = instantiateVariableFont(font, {"wght": weight})
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    units = font["head"].unitsPerEm
    kern = {}
    if "kern" in font:
        for table in font["kern"].kernTables:
            kern.update(getattr(table, "kernTable", {}))
    pen = SVGPathPen(glyphs)
    bounds = BoundsPen(glyphs)
    x = 0.0
    previous = None
    for char in text:
        name = cmap.get(ord(char))
        if name is None:
            raise BrandError(f"{font_path.name} has no glyph for {char!r}")
        if previous is not None:
            x += kern.get((previous, name), 0)
        glyph = glyphs[name]
        # Flip y: fonts are y-up, SVG is y-down.
        transform = (1, 0, 0, -1, x, 0)
        glyph.draw(TransformPen(pen, transform))
        glyph.draw(TransformPen(bounds, transform))
        x += glyph.width + tracking * units
        previous = name
    font.close()
    if bounds.bounds is None:
        raise BrandError("the wordmark text produced no outlines")
    x_min, y_min, x_max, y_max = bounds.bounds
    pad = units * 0.02
    view = f"{_num(x_min - pad)} {_num(y_min - pad)} {_num(x_max - x_min + 2 * pad)} {_num(y_max - y_min + 2 * pad)}"
    def clean(value: str) -> str:
        return re.sub(r"-{2,}", "-", value).replace("<", "(").replace(">", ")")

    note = (
        f"outlined by iconflow brand outline from {licence['family']} {licence['style']} "
        f"{licence['version']}; licence: {licence['licence'][:160]}"
        + (f"; licence-ok: {licence_ok}" if licence_ok else "")
    )
    meta = f"<!-- {clean(note)} -->"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">\n'
        f"  {meta}\n"
        f'  <path fill="currentColor" d="{pen.getCommands()}"/>\n'
        "</svg>\n"
    )
    licence["licence_ok"] = licence_ok
    return svg, licence
