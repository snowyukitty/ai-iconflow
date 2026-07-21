"""Orchestrate: one SVG master -> a full icon set for the chosen targets."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, Protocol

from . import assemble, htmlhead
from .rasterize import Rasterizer, load_svg

# Targets the CLI understands. "all" expands to everything.
TARGETS = ("web", "pwa", "tauri", "electron", "tray")

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


def normalize_targets(targets) -> list[str]:
    """Validate and normalize target names while preserving canonical order."""
    requested = [str(t).strip().lower() for t in targets if str(t).strip()]
    if not requested:
        raise ValueError("no targets requested")
    if "all" in requested:
        unknown = sorted(set(requested) - {"all"})
        if unknown:
            raise ValueError(f"'all' cannot be combined with other targets: {', '.join(unknown)}")
        return list(TARGETS)
    unknown = sorted(set(requested) - set(TARGETS))
    if unknown:
        raise ValueError(
            f"unknown target(s): {', '.join(unknown)}. Choose from: {', '.join(TARGETS)}, all"
        )
    return [target for target in TARGETS if target in requested]


class RenderCache:
    """Render each size once, on demand, reusing a single browser session."""

    def __init__(self, svg_text: str, rasterizer: Rasterizer, *, optimize: bool = True):
        self.svg = svg_text
        self.r = rasterizer
        self.optimize = optimize
        self._cache: dict[int, bytes] = {}

    def png(self, size: int) -> bytes:
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError("render size must be a positive integer")
        if size not in self._cache:
            png = self.r.render(self.svg, size)
            self._cache[size] = assemble.optimize_png(png) if self.optimize else png
        return self._cache[size]

    def many(self, sizes) -> dict[int, bytes]:
        return {s: self.png(s) for s in sizes}


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
    if target not in {"web", "tauri", "electron", "tray"}:
        raise ValueError("preview target must be web, pwa, tauri, electron, or tray")

    if target == "web":
        assemble.opaque_color(bg_color, "background color")
        assets = {
            "apple-touch-icon.png": assemble.flatten(cache.png(180), bg_color),
            "icon-192.png": cache.png(192),
            "icon-512.png": cache.png(512),
            "icon-512-maskable.png": assemble.maskable_asset(cache.png(512), bg_color),
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


def build_web(cache: RenderCache, src_svg: Path, outdir: Path, name: str,
              theme: str, bg: str, produced: list[str],
              options: htmlhead.WebMetaOptions | None = None) -> None:
    options = options or htmlhead.WebMetaOptions()
    shutil.copyfile(src_svg, outdir / "favicon.svg")
    produced.append("favicon.svg")
    assemble.write_ico(cache.many([16, 32, 48]), outdir / "favicon.ico")
    produced.append("favicon.ico")
    _write_assets(
        outdir,
        preview_assets(cache, "web", bg_color=bg),
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


def build(master_svg: str | Path, outdir: str | Path, targets=("web",), *,
          name: str = "App", theme_color: str = "#0b0d12",
          bg_color: str = "#ffffff", electron_radius: float = 0.0,
          tray_ts: bool = False, color_scheme: str = "light",
          web_options: htmlhead.WebMetaOptions | None = None,
          optimize_png: bool = True, tray_svg: str | Path | None = None,
          tray_template_mode: str = "auto") -> list[str]:
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
    master_svg = Path(master_svg)
    outdir = Path(outdir)
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
        if "web" in targets or "pwa" in targets:
            build_web(cache, master_svg, outdir, name, theme_color, bg_color, produced, web_options)
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
    return produced
