"""Assemble multi-resolution .ico / .icns and post-process PNGs.

ICO and ICNS are packed by hand so each size carries the crisp, natively
browser-rendered bitmap (PNG-compressed entry, supported by Windows Vista+ and
macOS 10.7+). Pillow is used only for raster post-processing (rounded corners,
macOS template silhouettes, padded backgrounds).
"""
from __future__ import annotations

import io
import struct
from collections import Counter
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageColor, ImageDraw


def _dimension(value: int, label: str = "dimension", *, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must not exceed {maximum}")
    return value


def opaque_color(color: str, label: str = "color") -> tuple[int, int, int, int]:
    """Parse a Pillow/CSS color and require it to be fully opaque.

    Generated touch, maskable and tile backgrounds are contractually opaque;
    accepting an alpha color would silently violate those platform semantics.
    """
    if not isinstance(color, str):
        raise ValueError(f"{label} must be a color string")
    try:
        rgba = ImageColor.getcolor(color.strip(), "RGBA")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {label}: {color!r}") from exc
    if rgba[3] != 255:
        raise ValueError(f"{label} must be fully opaque")
    return rgba


def validate_radius(radius_frac: float) -> float:
    if isinstance(radius_frac, bool) or not isinstance(radius_frac, (int, float)):
        raise ValueError("corner radius must be a number")
    radius = float(radius_frac)
    if not 0 <= radius <= 0.5:
        raise ValueError("corner radius must be in the range [0, 0.5]")
    return radius


def _validate_png_map(
    png_by_size: dict[int, bytes], *, maximum: int | None = None
) -> dict[int, bytes]:
    if not isinstance(png_by_size, dict) or not png_by_size:
        raise ValueError("at least one PNG frame is required")
    validated: dict[int, bytes] = {}
    for raw_size, png in png_by_size.items():
        size = _dimension(raw_size, "frame size", maximum=maximum)
        image = _open(png)
        if image.size != (size, size):
            raise ValueError(
                f"PNG frame keyed as {size}px has dimensions {image.size}; "
                f"expected {(size, size)}"
            )
        validated[size] = png
    return validated


# ----------------------------------------------------------------------------- ICO
def write_ico(
    png_by_size: dict[int, bytes], out: Path, *, order: Iterable[int] | None = None
) -> Path:
    """Write a multi-size .ico embedding each PNG verbatim.

    ``order`` is optional for compatibility, but lets platform builders mirror
    an upstream tool's canonical directory order. Tauri uses
    ``32,16,24,48,64,256``; ordering is observable even though conforming ICO
    readers should choose frames by their declared dimensions.
    """
    frames = _validate_png_map(png_by_size, maximum=256)
    if order is None:
        sizes = sorted(frames)
    else:
        sizes = list(order)
        if any(isinstance(size, bool) or not isinstance(size, int) for size in sizes):
            raise ValueError("ICO frame order must contain integer sizes")
        if len(sizes) != len(set(sizes)) or set(sizes) != set(frames):
            raise ValueError("ICO frame order must contain every frame size exactly once")
    count = len(sizes)
    out_bytes = bytearray(struct.pack("<HHH", 0, 1, count))  # ICONDIR
    offset = 6 + 16 * count
    blobs = bytearray()
    for s in sizes:
        png = frames[s]
        dim = 0 if s == 256 else s  # 0 means 256 in the ICO spec
        out_bytes += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        blobs += png
        offset += len(png)
    out_bytes += blobs
    Path(out).write_bytes(out_bytes)
    return Path(out)


# ---------------------------------------------------------------------------- ICNS
# size -> OSType. PNG payloads are valid for these on macOS 10.7+.
_ICNS_TYPES = {
    16: b"icp4",
    32: b"icp5",
    64: b"icp6",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}


def write_icns(png_by_size: dict[int, bytes], out: Path) -> Path:
    """Write a .icns embedding each PNG under its matching OSType."""
    frames = _validate_png_map(png_by_size)
    unsupported = sorted(set(frames) - set(_ICNS_TYPES))
    if unsupported:
        raise ValueError(f"unsupported ICNS frame size(s): {', '.join(map(str, unsupported))}")
    body = bytearray()
    for s in sorted(frames):
        ostype = _ICNS_TYPES[s]
        png = frames[s]
        body += ostype + struct.pack(">I", len(png) + 8) + png  # length includes 8-byte header
    data = b"icns" + struct.pack(">I", len(body) + 8) + bytes(body)
    Path(out).write_bytes(data)
    return Path(out)


# --------------------------------------------------------------------- PNG helpers
def _open(png: bytes) -> Image.Image:
    if not isinstance(png, (bytes, bytearray, memoryview)) or not png:
        raise ValueError("PNG data must be non-empty bytes")
    try:
        source = Image.open(io.BytesIO(bytes(png)))
        source.load()
    except OSError as exc:
        raise ValueError("invalid PNG image data") from exc
    if source.format != "PNG":
        raise ValueError(f"expected PNG image data, got {source.format or 'unknown'}")
    return source.convert("RGBA")


def _dump(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def optimize_png(png: bytes) -> bytes:
    """Losslessly re-pack a PNG through Pillow's optimizer."""
    return _dump(_open(png))


def _square(im: Image.Image, operation: str) -> None:
    if im.width != im.height:
        raise ValueError(f"{operation} requires a square PNG, got {im.size}")


def _resize_rgba(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Lanczos-resize premultiplied RGBA to avoid colored transparent fringes."""
    width = _dimension(size[0], "resize width")
    height = _dimension(size[1], "resize height")
    return im.convert("RGBa").resize((width, height), Image.Resampling.LANCZOS).convert("RGBA")


def round_corners(png: bytes, radius_frac: float) -> bytes:
    """Clip to a rounded square (radius as a fraction of the side, e.g. 0.18).
    Intersects with the existing alpha so artwork transparency is preserved."""
    radius_frac = validate_radius(radius_frac)
    im = _open(png)
    _square(im, "corner rounding")
    if radius_frac == 0:
        return png
    w, h = im.size
    r = max(1, int(round(min(w, h) * radius_frac)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    im.putalpha(ImageChops.darker(im.getchannel("A"), mask))
    return _dump(im)


def flatten(png: bytes, bg: str = "#ffffff") -> bytes:
    """Composite onto an opaque background. Apple touch icons should not be
    transparent (iOS adds a black box), so the web target flattens them."""
    im = _open(png)
    base = Image.new("RGBA", im.size, opaque_color(bg, "background color"))
    return _dump(Image.alpha_composite(base, im))


def _alpha_coverage(alpha: Image.Image, threshold: int = 16) -> float:
    histogram = alpha.histogram()
    return sum(histogram[threshold + 1:]) / (alpha.width * alpha.height)


def _background_palette(im: Image.Image) -> list[tuple[int, int, int]]:
    """Estimate full-card background colors from the outer quarter of an icon."""
    w, h = im.size
    band = max(1, min(w, h) // 4)
    samples: Counter[tuple[int, int, int]] = Counter()
    for y in range(h):
        for x in range(w):
            if band <= x < w - band and band <= y < h - band:
                continue
            r, g, b, a = im.getpixel((x, y))
            if a < 192:
                continue
            # Quantization groups antialiased/gradient neighbors while keeping
            # differently colored foreground marks distinct.
            samples[(r // 16 * 16, g // 16 * 16, b // 16 * 16)] += 1
    ranked = samples.most_common(12)
    if not ranked:
        return []
    dominant = ranked[0][1]
    # A foreground device may intentionally touch the edge. Do not teach one
    # or two such pixels to the background model and erase the signature mark.
    return [color for color, count in ranked if count >= max(2, dominant * 0.04)]


def _contrast_alpha(im: Image.Image) -> Image.Image:
    palette = _background_palette(im)
    if not palette:
        return Image.new("L", im.size, 0)
    out = Image.new("L", im.size, 0)
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = im.getpixel((x, y))
            if a <= 8:
                continue
            distance = min(
                ((r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2) ** 0.5
                for pr, pg, pb in palette
            )
            # Ignore compression/antialias noise, then rapidly promote a real
            # foreground contrast to solid template alpha.
            strength = max(0, min(255, int(round((distance - 14) * 5.0))))
            out.putpixel((x, y), a * strength // 255)
    return out


def to_template(png: bytes, mode: str = "auto") -> bytes:
    """Create a pure-black macOS template image.

    ``mode='auto'`` preserves alpha for a sparse semantic mark. For a full-card
    app icon it removes the border/background and derives alpha from the mark's
    contrast, avoiding the former featureless black-square failure. Supply a
    dedicated tray SVG whenever possible; ``mode='alpha'`` remains available
    for callers that intentionally want the exact legacy alpha silhouette.
    """
    if mode not in {"auto", "alpha", "contrast"}:
        raise ValueError("template mode must be 'auto', 'alpha', or 'contrast'")
    im = _open(png)
    _square(im, "template conversion")
    source_alpha = im.getchannel("A")
    source_coverage = _alpha_coverage(source_alpha)
    alpha = source_alpha
    if mode == "contrast" or (mode == "auto" and source_coverage >= 0.68):
        alpha = _contrast_alpha(im)
        derived_coverage = _alpha_coverage(alpha)
        if derived_coverage < 0.003 or derived_coverage > 0.62:
            raise ValueError(
                "could not isolate a semantic tray mark from the full-card icon; "
                "provide a dedicated tray SVG (tray_svg)"
            )
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.putalpha(alpha)  # rgb already (0,0,0)
    return _dump(out)


def pad(png: bytes, factor: float) -> bytes:
    """Shrink artwork into a transparent square, leaving `factor` padding on each
    side (e.g. 0.1 -> artwork at 80%). Useful for maskable PWA icons."""
    if isinstance(factor, bool) or not isinstance(factor, (int, float)):
        raise ValueError("padding factor must be a number")
    factor = float(factor)
    if not 0 <= factor < 0.5:
        raise ValueError("padding factor must be in the range [0, 0.5)")
    if factor == 0:
        return png
    im = _open(png)
    _square(im, "padding")
    w, h = im.size
    inner = max(1, int(round(w * (1 - 2 * factor))))
    art = _resize_rgba(im, (inner, inner))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(art, ((w - inner) // 2, (h - inner) // 2))
    return _dump(canvas)


def maskable_asset(png: bytes, bg: str = "#ffffff", padding: float = 0.10) -> bytes:
    """Apply IconFlow's canonical PWA maskable transform.

    The exact same helper is used by build, preview and QA so the audited bytes
    are the bytes that ship.
    """
    return flatten(pad(png, padding), bg)


def contain_on_canvas(png: bytes, width: int, height: int, bg: str = "#ffffff",
                      scale: float = 0.72) -> bytes:
    """Center artwork on an opaque canvas, preserving aspect ratio.

    Windows tile assets include rectangular canvases. This keeps one source icon
    optically centered without stretching it.
    """
    width = _dimension(width, "tile canvas width")
    height = _dimension(height, "tile canvas height")
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not 0 < scale <= 1:
        raise ValueError("scale must be in the range (0, 1]")

    im = _open(png)
    box = max(1, int(round(min(width, height) * scale)))
    ratio = min(box / im.width, box / im.height)
    size = (max(1, int(round(im.width * ratio))), max(1, int(round(im.height * ratio))))
    art = _resize_rgba(im, size)
    canvas = Image.new("RGBA", (width, height), opaque_color(bg, "canvas color"))
    canvas.paste(art, ((width - art.width) // 2, (height - art.height) // 2), art)
    return _dump(canvas)
