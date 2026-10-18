# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Orchestrate: one SVG master -> a full icon set for the chosen targets."""
from __future__ import annotations

import io
import shutil
import stat
from pathlib import Path
from typing import Iterable, Protocol

from PIL import Image, ImageChops, ImageDraw

from . import assemble, htmlhead, ladder
from .rasterize import Rasterizer, load_svg

# Targets the CLI understands. "all" expands to the app-icon targets: an
# emote pack is a different deliverable from an app's icon set, so it is only
# ever built when it is asked for by name. "all" is frozen at the 0.6 set:
# receipts store the expanded list, so growing it would turn every approved
# "all" project stale on upgrade. Android is therefore asked for by name too.
TARGETS = ("web", "pwa", "tauri", "electron", "tray", "android", "emote")
APP_TARGETS = ("web", "pwa", "tauri", "electron", "tray")
# Targets whose assets are composed for a platform's adaptive crop. One
# composition serves all of them, so one maskable audit covers all of them.
ADAPTIVE_TARGETS = frozenset({"web", "pwa", "android"})

# The maskable composition: the artwork occupies this fraction of the
# maskable canvas, centred, on the opaque background colour. 0.8 is the
# historical 10% padding. A linked maskable source is drawn for the crop
# already, so it defaults to the whole canvas.
DEFAULT_MASKABLE_SCALE = 0.8
DEFAULT_LINKED_MASKABLE_SCALE = 1.0
MASKABLE_SCALE_RANGE = (0.5, 1.0)
# W3C maskable safe zone: a centred circle of radius 40% of the icon.
MASKABLE_SAFE_RADIUS = 0.40

# Android adaptive icons (docs/OUTPUT_TARGETS.md). Layers are 108dp; the
# launcher shows the central 72dp through its mask and guarantees the central
# 66dp circle. The maskable canvas maps onto the layer so that its 40% safe
# circle lands exactly on Android's 66dp circle: 66 / 0.8 = 82.5dp.
ANDROID_LAYER_DP = 108
ANDROID_VISIBLE_DP = 72
ANDROID_SAFE_DP = 66
ANDROID_MASKABLE_DP = ANDROID_SAFE_DP / (2 * MASKABLE_SAFE_RADIUS)
ANDROID_LEGACY_DP = 48
ANDROID_DENSITIES = (
    ("mdpi", 1.0), ("hdpi", 1.5), ("xhdpi", 2.0), ("xxhdpi", 3.0), ("xxxhdpi", 4.0),
)
# Legacy (pre-Android 8) launcher icons: IconFlow's keylines inside the 48dp
# canvas, a rounded square 44dp wide and a 44dp circle, each showing the same
# central 72dp of the adaptive composition a modern launcher shows.
ANDROID_LEGACY_SHAPE_DP = 44
ANDROID_LEGACY_CORNER = 0.16
ANDROID_PLAY_STORE_SIZE = 512

# Emotes are uploaded at these sizes: Twitch takes 28, 56 and 112 together;
# Discord and Slack take one 128 (docs/EMOTES.md). Each is rendered natively.
EMOTE_SIZES = (28, 56, 112, 128)
# The strictest platform limit that applies to each file, in bytes: Twitch
# rejects a static emote over 25 KB per size; Slack caps a custom emoji at
# 128 KB (Discord allows 256 KB). A file over its budget fails the build
# rather than failing later in a platform's upload form.
EMOTE_BUDGETS = {28: 25_000, 56: 25_000, 112: 25_000, 128: 128_000}

# Match Tauri CLI's observable ICO directory order. The order starts with the
# conventional Windows 32px frame, then includes every natively rendered size.
ICO_FRAME_ORDER = (32, 16, 24, 48, 64, 256)
ICNS_FRAME_SIZES = (16, 32, 64, 128, 256, 512, 1024)
DESKTOP_FRAME_SIZES = tuple(sorted(set(ICO_FRAME_ORDER) | set(ICNS_FRAME_SIZES)))
TAURI_PNG_SPECS = (
    ("icons/32x32.png", 32),
    ("icons/64x64.png", 64),
    ("icons/128x128.png", 128),
    ("icons/128x128@2x.png", 256),
    ("icons/icon.png", 512),
)


class PngCache(Protocol):
    """Minimal read-only cache contract shared by build and Review Lab."""

    def png(self, size: int) -> bytes: ...


class _FrozenCache:
    """A PngCache over renders that already exist (QA, Review Lab)."""

    def __init__(self, renders: dict[int, bytes]):
        self.renders = renders

    def png(self, size: int) -> bytes:
        try:
            return self.renders[size]
        except KeyError as exc:
            raise ValueError(f"render cache has no {size}px frame") from exc


def validate_maskable_scale(scale) -> float:
    """Return a valid maskable artwork scale, or raise a ValueError that says why."""
    low, high = MASKABLE_SCALE_RANGE
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        raise ValueError("maskable_scale must be a number")
    scale = float(scale)
    if not low <= scale <= high:
        raise ValueError(
            f"maskable_scale must be between {low} and {high} "
            f"(the share of the maskable canvas the artwork fills); got {scale:g}"
        )
    return scale


def resolve_maskable_scale(scale: float | None, *, linked: bool) -> float:
    """The effective scale: explicit, else the default for a master or a linked source."""
    if scale is None:
        return DEFAULT_LINKED_MASKABLE_SCALE if linked else DEFAULT_MASKABLE_SCALE
    return validate_maskable_scale(scale)


def maskable_png(cache: PngCache, bg_color: str, *, scale: float | None = None,
                 maskable_cache: PngCache | None = None) -> bytes:
    """The one maskable composition every path ships, previews, and audits.

    ``maskable_cache`` is a linked source drawn for the crop (``maskable.svg``);
    without one the master is composed. The default master composition is
    byte-identical to IconFlow 0.6's fixed 10% padding.
    """
    source = maskable_cache or cache
    effective = resolve_maskable_scale(scale, linked=maskable_cache is not None)
    return assemble.maskable_asset(source.png(512), bg_color, padding=(1 - effective) / 2)


def normalize_targets(targets) -> list[str]:
    """Validate and normalize target names while preserving canonical order."""
    requested = [str(t).strip().lower() for t in targets if str(t).strip()]
    if not requested:
        raise ValueError("no targets requested")
    if "all" in requested:
        unknown = sorted(set(requested) - {"all"})
        if unknown:
            raise ValueError(f"'all' cannot be combined with other targets: {', '.join(unknown)}")
        return list(APP_TARGETS)
    unknown = sorted(set(requested) - set(TARGETS))
    if unknown:
        raise ValueError(
            f"unknown target(s): {', '.join(unknown)}. Choose from: {', '.join(TARGETS)}, all"
        )
    return [target for target in TARGETS if target in requested]


class RenderCache:
    """Render each size once, on demand, reusing a single browser session.

    Every size is rendered from its detail-ladder rung, so one annotated source
    can carry material at 1024px and one idea at 16px. A source with no
    ``data-lod`` reduces to itself, which is why this is invisible to every
    master authored before the ladder existed.
    """

    def __init__(self, svg_text: str, rasterizer: Rasterizer, *, optimize: bool = True):
        self.svg = svg_text
        self.r = rasterizer
        self.optimize = optimize
        self._cache: dict[int, bytes] = {}
        self._rungs: dict[str, str] = {}

    def rung_svg(self, rung: str) -> str:
        """The source reduced to one rung, computed once per rung."""
        if rung not in self._rungs:
            self._rungs[rung] = ladder.reduce_svg(self.svg, rung)
        return self._rungs[rung]

    def png(self, size: int) -> bytes:
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError("render size must be a positive integer")
        if size not in self._cache:
            png = self.r.render(self.rung_svg(ladder.rung_for_size(size)), size)
            self._cache[size] = assemble.optimize_png(png) if self.optimize else png
        return self._cache[size]

    def many(self, sizes) -> dict[int, bytes]:
        return {s: self.png(s) for s in sizes}


def _is_link_or_reparse_point(path: Path) -> bool:
    """Recognize POSIX symlinks and Windows reparse-point links/junctions."""

    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(status, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _validate_output_tree(outdir: Path) -> None:
    """Refuse an output tree that could redirect generated writes elsewhere."""

    if _is_link_or_reparse_point(outdir):
        raise ValueError(f"output directory must not be a symlink or junction: {outdir}")
    if outdir.exists() and not outdir.is_dir():
        raise ValueError(f"output path is not a directory: {outdir}")
    if outdir.is_dir():
        for path in outdir.rglob("*"):
            if _is_link_or_reparse_point(path):
                raise ValueError(
                    "output directory contains a symlink or junction; remove it before "
                    f"building: {path}"
                )


def _write(outdir: Path, name: str, data: bytes, produced: list[str]) -> None:
    destination = outdir / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    produced.append(name)


def _write_assets(outdir: Path, assets: dict[str, bytes], produced: list[str]) -> None:
    for name, data in assets.items():
        _write(outdir, name, data, produced)


def electron_frames(
    cache: PngCache, radius: float, sizes: Iterable[int]
) -> dict[int, bytes]:
    """Return exact transformed PNG frames used in Electron PNG/ICO/ICNS.

    This read-only helper is also the Review Lab integration point: previews can
    inspect any native frame without writing or approximating the build output.
    """
    radius = assemble.validate_radius(radius)
    frames: dict[int, bytes] = {}
    for size in sizes:
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError("Electron frame sizes must be positive integers")
        frames[size] = assemble.round_corners(cache.png(size), radius)
    return frames


def _windows_tile_assets(cache: PngCache, bg: str) -> dict[str, bytes]:
    specs = [
        ("mstile-70x70.png", 70, 70, 0.72),
        ("mstile-144x144.png", 144, 144, 0.72),
        ("mstile-150x150.png", 150, 150, 0.72),
        ("mstile-310x310.png", 310, 310, 0.72),
        ("mstile-310x150.png", 310, 150, 0.56),
    ]
    src = cache.png(512)
    return {
        filename: assemble.contain_on_canvas(src, width, height, bg, scale)
        for filename, width, height, scale in specs
    }


def preview_assets(
    cache: PngCache,
    target: str,
    *,
    bg_color: str = "#ffffff",
    electron_radius: float = 0.0,
    tray_cache: PngCache | None = None,
    tray_template_mode: str = "auto",
    windows_tiles: bool = False,
    tile_color: str | None = None,
    maskable_scale: float | None = None,
    maskable_cache: PngCache | None = None,
    monochrome_cache: PngCache | None = None,
) -> dict[str, bytes]:
    """Return target-transformed PNG assets without touching the filesystem.

    The returned keys are the eventual relative output paths. Container formats
    are intentionally excluded; use :func:`electron_frames` for exact Electron
    ICO/ICNS frame bytes. Build functions consume these same dictionaries, so a
    Review Lab preview cannot drift from the PNGs that ship.
    """
    target = str(target).strip().lower()
    if target == "pwa":
        target = "web"
    if target not in {"web", "tauri", "electron", "tray", "android", "emote"}:
        raise ValueError(
            "preview target must be web, pwa, tauri, electron, tray, android, or emote"
        )

    if target == "android":
        return android_assets(
            cache, bg_color, maskable_scale=maskable_scale,
            maskable_cache=maskable_cache, monochrome_cache=monochrome_cache,
            template_mode=tray_template_mode,
        )

    if target == "emote":
        return {f"emote/{size}.png": cache.png(size) for size in EMOTE_SIZES}

    if target == "web":
        assemble.opaque_color(bg_color, "background color")
        assets = {
            "apple-touch-icon.png": assemble.flatten(cache.png(180), bg_color),
            "icon-192.png": cache.png(192),
            "icon-512.png": cache.png(512),
            "icon-512-maskable.png": maskable_png(
                cache, bg_color, scale=maskable_scale, maskable_cache=maskable_cache,
            ),
        }
        if windows_tiles:
            assets.update(_windows_tile_assets(cache, tile_color or bg_color))
        return assets

    if target == "tauri":
        return {name: cache.png(size) for name, size in TAURI_PNG_SPECS}

    if target == "electron":
        return {
            "build/icon.png": electron_frames(cache, electron_radius, (1024,))[1024]
        }

    source = tray_cache or cache
    color_32 = source.png(32)
    color_16 = source.png(16)
    return {
        "tray/tray.png": color_32,
        "tray/tray@16.png": color_16,
        "tray/trayTemplate.png": assemble.to_template(color_16, tray_template_mode),
        "tray/trayTemplate@2x.png": assemble.to_template(color_32, tray_template_mode),
    }


def _android_art(cache: PngCache, layer_px: int, scale: float) -> bytes:
    """Render the artwork natively at the pixel size it occupies in a layer."""
    art_px = max(1, int(round(layer_px * scale * ANDROID_MASKABLE_DP / ANDROID_LAYER_DP)))
    return cache.png(art_px)


def _centred(png: bytes, canvas: int) -> Image.Image:
    art = Image.open(io.BytesIO(png)).convert("RGBA")
    layer = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    layer.alpha_composite(art, ((canvas - art.width) // 2, (canvas - art.height) // 2))
    return layer


def _png_bytes(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def _visible_window(composed: Image.Image) -> Image.Image:
    """The central 72dp of a 108dp layer: what a launcher mask can show."""
    layer = composed.width
    visible = int(round(layer * ANDROID_VISIBLE_DP / ANDROID_LAYER_DP))
    offset = (layer - visible) // 2
    return composed.crop((offset, offset, offset + visible, offset + visible))


def _legacy_icon(composed: Image.Image, legacy_px: int, *, round_shape: bool) -> bytes:
    """A pre-adaptive launcher icon: the visible 72dp, cut to IconFlow's keyline."""
    shape_px = max(1, int(round(legacy_px * ANDROID_LEGACY_SHAPE_DP / ANDROID_LEGACY_DP)))
    art = (
        _visible_window(composed).convert("RGBa")
        .resize((shape_px, shape_px), Image.Resampling.LANCZOS).convert("RGBA")
    )
    # Draw the keyline at 4x and reduce it, so the edge is antialiased.
    big = shape_px * 4
    mask = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(mask)
    if round_shape:
        draw.ellipse([0, 0, big - 1, big - 1], fill=255)
    else:
        draw.rounded_rectangle(
            [0, 0, big - 1, big - 1], radius=int(round(big * ANDROID_LEGACY_CORNER)), fill=255,
        )
    mask = mask.resize((shape_px, shape_px), Image.Resampling.LANCZOS)
    art.putalpha(ImageChops.multiply(art.getchannel("A"), mask))
    canvas = Image.new("RGBA", (legacy_px, legacy_px), (0, 0, 0, 0))
    canvas.alpha_composite(art, ((legacy_px - shape_px) // 2, (legacy_px - shape_px) // 2))
    return _png_bytes(canvas)


ANDROID_ADAPTIVE_XML = """<?xml version="1.0" encoding="utf-8"?>
<!-- AUTO-GENERATED by IconFlow. Rebuild from the SVG source; do not edit. -->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>
</adaptive-icon>
"""


def android_background_xml(bg_color: str) -> str:
    red, green, blue, _ = assemble.opaque_color(bg_color, "background color")
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!-- AUTO-GENERATED by IconFlow. Rebuild from the SVG source; do not edit. -->\n"
        "<resources>\n"
        f'    <color name="ic_launcher_background">#{red:02X}{green:02X}{blue:02X}</color>\n'
        "</resources>\n"
    )


def android_layer_scale(maskable_scale: float | None, *, linked: bool) -> float:
    """Share of the 108dp layer the artwork's canvas occupies."""
    scale = resolve_maskable_scale(maskable_scale, linked=linked)
    return scale * ANDROID_MASKABLE_DP / ANDROID_LAYER_DP


def android_assets(
    cache: PngCache, bg_color: str = "#ffffff", *,
    maskable_scale: float | None = None,
    maskable_cache: PngCache | None = None,
    monochrome_cache: PngCache | None = None,
    template_mode: str = "auto",
) -> dict[str, bytes]:
    """Every Android launcher resource, keyed by its path in the output tree.

    The foreground layer is the maskable composition mapped onto Android's
    108dp layer (its 40% safe circle lands on Android's 66dp circle), so the
    one audit that guards ``icon-512-maskable.png`` guards these layers too.
    Every density renders the artwork natively at the size it occupies. The
    background is a colour resource, not a bitmap. The themed-icon layer
    (Android 13+) is the alpha of a mark-only source when one is linked
    (``monochrome_svg``, else ``tray_svg``); otherwise it is the same
    reduction the macOS tray template uses, which fails closed rather than
    ship a featureless disc.
    """
    bg = assemble.opaque_color(bg_color, "background color")
    if template_mode not in {"auto", "alpha", "contrast"}:
        raise ValueError("template mode must be 'auto', 'alpha', or 'contrast'")
    source = maskable_cache or cache
    scale = resolve_maskable_scale(maskable_scale, linked=maskable_cache is not None)
    mono_source = monochrome_cache or source
    assets: dict[str, bytes] = {}
    composed = None
    for density, factor in ANDROID_DENSITIES:
        layer_px = int(round(ANDROID_LAYER_DP * factor))
        foreground = _centred(_android_art(source, layer_px, scale), layer_px)
        assets[f"res/mipmap-{density}/ic_launcher_foreground.png"] = _png_bytes(foreground)
        try:
            mono = assemble.to_template(_android_art(mono_source, layer_px, scale), template_mode)
        except ValueError as exc:
            raise ValueError(
                "android: the themed-icon (monochrome) layer cannot be derived from this "
                f"source ({exc}); link a mark-only source with build.monochrome_svg"
            ) from exc
        assets[f"res/mipmap-{density}/ic_launcher_monochrome.png"] = _png_bytes(
            _centred(mono, layer_px)
        )
        composed = Image.new("RGBA", (layer_px, layer_px), bg)
        composed.alpha_composite(foreground)
        legacy_px = int(round(ANDROID_LEGACY_DP * factor))
        assets[f"res/mipmap-{density}/ic_launcher.png"] = _legacy_icon(
            composed, legacy_px, round_shape=False,
        )
        assets[f"res/mipmap-{density}/ic_launcher_round.png"] = _legacy_icon(
            composed, legacy_px, round_shape=True,
        )
    # The store listing icon is a full opaque square: Google Play applies its
    # own mask, so it carries the same 72dp a launcher shows, unmasked.
    store = _visible_window(composed).resize(
        (ANDROID_PLAY_STORE_SIZE, ANDROID_PLAY_STORE_SIZE), Image.Resampling.LANCZOS,
    )
    flat = Image.new("RGBA", store.size, bg)
    flat.alpha_composite(store)
    assets["play-store-512.png"] = _png_bytes(flat)
    xml = ANDROID_ADAPTIVE_XML.encode("utf-8")
    assets["res/mipmap-anydpi-v26/ic_launcher.xml"] = xml
    assets["res/mipmap-anydpi-v26/ic_launcher_round.xml"] = xml
    assets["res/values/ic_launcher_background.xml"] = android_background_xml(bg_color).encode("utf-8")
    return {f"android/{name}": data for name, data in assets.items()}


def write_favicon_svg(svg_text: str, src_svg: Path, destination: Path) -> bool:
    """Write the vector favicon, adding the ladder layer only when it is used.

    A flat source is copied byte for byte, exactly as it always was: no icon
    that predates the ladder gains a stylesheet it does not need. An annotated
    source is written with :data:`ladder.LADDER_CSS`, which is what makes the
    single vector favicon show its plate rung in a large preview and its glyph
    rung in a 16px tab. Returns True when the layer was added.
    """
    if not ladder.has_ladder(svg_text):
        shutil.copyfile(src_svg, destination)
        return False
    destination.write_text(ladder.with_media_layer(svg_text), encoding="utf-8")
    return True


def build_web(cache: RenderCache, src_svg: Path, outdir: Path, name: str,
              theme: str, bg: str, produced: list[str],
              options: htmlhead.WebMetaOptions | None = None, *,
              maskable_scale: float | None = None,
              maskable_cache: PngCache | None = None) -> None:
    options = options or htmlhead.WebMetaOptions()
    write_favicon_svg(cache.svg, src_svg, outdir / "favicon.svg")
    produced.append("favicon.svg")
    assemble.write_ico(cache.many([16, 32, 48]), outdir / "favicon.ico")
    produced.append("favicon.ico")
    _write_assets(
        outdir,
        preview_assets(
            cache, "web", bg_color=bg, maskable_scale=maskable_scale,
            maskable_cache=maskable_cache,
        ),
        produced,
    )
    if options.windows_tiles:
        build_windows_tiles(cache, outdir, options.tile_color or theme or bg, produced)
    htmlhead.write_web_meta(outdir, name, theme, bg, options)
    produced += ["site.webmanifest", "favicon-head.html"]
    if options.windows_tiles:
        produced.append("browserconfig.xml")


def build_windows_tiles(cache: RenderCache, outdir: Path, bg: str,
                        produced: list[str]) -> None:
    _write_assets(outdir, _windows_tile_assets(cache, bg), produced)


def build_tauri(cache: RenderCache, outdir: Path, produced: list[str]) -> None:
    icons = outdir / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    _write_assets(outdir, preview_assets(cache, "tauri"), produced)
    assemble.write_ico(
        cache.many(ICO_FRAME_ORDER), icons / "icon.ico", order=ICO_FRAME_ORDER
    )
    assemble.write_icns(cache.many(ICNS_FRAME_SIZES), icons / "icon.icns")
    produced += ["icons/icon.ico", "icons/icon.icns"]


def build_electron(cache: RenderCache, outdir: Path, radius: float,
                   produced: list[str]) -> None:
    build = outdir / "build"
    build.mkdir(parents=True, exist_ok=True)
    _write_assets(
        outdir,
        preview_assets(cache, "electron", electron_radius=radius),
        produced,
    )
    frames = electron_frames(cache, radius, DESKTOP_FRAME_SIZES)
    assemble.write_ico(
        {size: frames[size] for size in ICO_FRAME_ORDER},
        build / "icon.ico",
        order=ICO_FRAME_ORDER,
    )
    assemble.write_icns(
        {size: frames[size] for size in ICNS_FRAME_SIZES}, build / "icon.icns"
    )
    produced += ["build/icon.ico", "build/icon.icns"]


def build_tray(cache: RenderCache, outdir: Path, ts_module: bool,
               produced: list[str], *, tray_cache: PngCache | None = None,
               template_mode: str = "auto") -> None:
    tray = outdir / "tray"
    tray.mkdir(parents=True, exist_ok=True)
    assets = preview_assets(
        cache,
        "tray",
        tray_cache=tray_cache,
        tray_template_mode=template_mode,
    )
    _write_assets(outdir, assets, produced)
    if ts_module:
        import base64
        b64 = base64.b64encode(assets["tray/tray.png"]).decode()
        (tray / "trayIcon.ts").write_text(
            "// AUTO-GENERATED by iconflow — do not edit by hand.\n"
            f'export const TRAY_ICON_DATA_URL =\n  "data:image/png;base64,{b64}";\n',
            encoding="utf-8",
        )
        produced.append("tray/trayIcon.ts")


def build_emote(cache: RenderCache, outdir: Path, produced: list[str]) -> None:
    assets = preview_assets(cache, "emote")
    for size in EMOTE_SIZES:
        data = assets[f"emote/{size}.png"]
        if len(data) > EMOTE_BUDGETS[size]:
            raise ValueError(
                f"emote/{size}.png is {len(data):,} bytes, over the {EMOTE_BUDGETS[size]:,}-byte "
                "upload limit for that size; simplify the drawing (fewer gradients and textures)"
            )
    _write_assets(outdir, assets, produced)


def build_android(cache: RenderCache, outdir: Path, bg: str, produced: list[str], *,
                  maskable_scale: float | None = None,
                  maskable_cache: PngCache | None = None,
                  monochrome_cache: PngCache | None = None,
                  template_mode: str = "auto") -> None:
    _write_assets(
        outdir,
        android_assets(
            cache, bg, maskable_scale=maskable_scale, maskable_cache=maskable_cache,
            monochrome_cache=monochrome_cache, template_mode=template_mode,
        ),
        produced,
    )


def build(master_svg: str | Path, outdir: str | Path, targets=("web",), *,
          name: str = "App", theme_color: str = "#0b0d12",
          bg_color: str = "#ffffff", electron_radius: float = 0.0,
          tray_ts: bool = False, color_scheme: str = "light",
          web_options: htmlhead.WebMetaOptions | None = None,
          optimize_png: bool = True, tray_svg: str | Path | None = None,
          tray_template_mode: str = "auto",
          maskable_scale: float | None = None,
          maskable_svg: str | Path | None = None,
          monochrome_svg: str | Path | None = None) -> list[str]:
    """Build the requested targets from `master_svg` into `outdir`.

    Returns the list of file paths produced (relative to outdir).
    """
    targets = normalize_targets(targets)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    assemble.opaque_color(theme_color, "theme color")
    assemble.opaque_color(bg_color, "background color")
    electron_radius = assemble.validate_radius(electron_radius)
    if tray_template_mode not in {"auto", "alpha", "contrast"}:
        raise ValueError("tray_template_mode must be 'auto', 'alpha', or 'contrast'")
    if web_options and web_options.tile_color:
        assemble.opaque_color(web_options.tile_color, "tile color")
    if maskable_scale is not None:
        maskable_scale = validate_maskable_scale(maskable_scale)
    master_svg = Path(master_svg)
    outdir = Path(outdir)
    _validate_output_tree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    svg_text = load_svg(master_svg)
    produced: list[str] = []

    with Rasterizer(color_scheme=color_scheme) as r:
        cache = RenderCache(svg_text, r, optimize=optimize_png)
        tray_cache = None
        if "tray" in targets and tray_svg is not None:
            tray_path = Path(tray_svg)
            if tray_path.resolve() == master_svg.resolve():
                tray_cache = cache
            else:
                tray_cache = RenderCache(
                    load_svg(tray_path), r, optimize=optimize_png
                )

        def linked(path) -> RenderCache | None:
            if path is None or Path(path).resolve() == master_svg.resolve():
                return None
            return RenderCache(load_svg(Path(path)), r, optimize=optimize_png)

        maskable_cache = linked(maskable_svg) if ADAPTIVE_TARGETS & set(targets) else None
        monochrome_cache = None
        if "android" in targets:
            monochrome_cache = linked(monochrome_svg if monochrome_svg is not None else tray_svg)
        if "web" in targets or "pwa" in targets:
            build_web(cache, master_svg, outdir, name, theme_color, bg_color, produced,
                      web_options, maskable_scale=maskable_scale,
                      maskable_cache=maskable_cache)
        if "tauri" in targets:
            build_tauri(cache, outdir, produced)
        if "electron" in targets:
            build_electron(cache, outdir, electron_radius, produced)
        if "tray" in targets:
            build_tray(
                cache,
                outdir,
                tray_ts,
                produced,
                tray_cache=tray_cache,
                template_mode=tray_template_mode,
            )
        if "android" in targets:
            build_android(
                cache, outdir, bg_color, produced, maskable_scale=maskable_scale,
                maskable_cache=maskable_cache, monochrome_cache=monochrome_cache,
                template_mode=tray_template_mode,
            )
        if "emote" in targets:
            build_emote(cache, outdir, produced)
    return produced
