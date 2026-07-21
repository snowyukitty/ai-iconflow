"""Emit the favicon <head> snippet and a web app manifest."""
from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
from pathlib import Path


@dataclass
class WebMetaOptions:
    """Options for generated web manifest and <head> metadata."""

    path_prefix: str = "/"
    relative_paths: bool = False
    short_name: str | None = None
    description: str | None = None
    start_url: str | None = None
    scope: str | None = None
    display: str = "standalone"
    orientation: str | None = None
    lang: str | None = None
    dir: str | None = None
    categories: list[str] = field(default_factory=list)
    app_id: str | None = None
    manifest_extra: dict[str, object] = field(default_factory=dict)
    head_meta: dict[str, str] = field(default_factory=dict)
    windows_tiles: bool = False
    tile_color: str | None = None


def _prefix(path_prefix: str) -> str:
    if path_prefix.startswith(("http://", "https://")):
        return path_prefix if path_prefix.endswith("/") else path_prefix + "/"
    if not path_prefix or path_prefix == "/":
        return "/"
    return "/" + path_prefix.strip("/") + "/"


def asset_path(filename: str, options: WebMetaOptions | None = None, *,
               manifest: bool = False) -> str:
    options = options or WebMetaOptions()
    if options.relative_paths:
        return filename if manifest else f"./{filename}"
    return _prefix(options.path_prefix) + filename


def _attr(value: object) -> str:
    return html.escape(str(value), quote=True)


def head_snippet(name: str, theme_color: str, bg_color: str,
                 options: WebMetaOptions | None = None) -> str:
    options = options or WebMetaOptions()
    tile_color = options.tile_color or theme_color or bg_color
    lines = [
        "<!-- Paste into <head>. SVG is primary; .ico is the legacy fallback. -->",
        f'<link rel="icon" href="{_attr(asset_path("favicon.ico", options))}" sizes="32x32">',
        f'<link rel="icon" href="{_attr(asset_path("favicon.svg", options))}" type="image/svg+xml">',
        f'<link rel="apple-touch-icon" href="{_attr(asset_path("apple-touch-icon.png", options))}">',
        f'<link rel="manifest" href="{_attr(asset_path("site.webmanifest", options))}">',
        f'<meta name="theme-color" content="{_attr(theme_color)}">',
    ]
    if options.description:
        lines.append(f'<meta name="description" content="{_attr(options.description)}">')
    for key, value in options.head_meta.items():
        lines.append(f'<meta name="{_attr(key)}" content="{_attr(value)}">')
    if options.windows_tiles:
        lines.extend([
            f'<meta name="msapplication-TileColor" content="{_attr(tile_color)}">',
            f'<meta name="msapplication-config" content="{_attr(asset_path("browserconfig.xml", options))}">',
        ])
    return "\n".join(lines) + "\n"


def manifest(name: str, theme_color: str, bg_color: str,
             options: WebMetaOptions | None = None) -> dict:
    options = options or WebMetaOptions()
    data = {
        "name": name,
        "short_name": options.short_name or name,
        "icons": [
            {"src": asset_path("icon-192.png", options, manifest=True), "sizes": "192x192", "type": "image/png"},
            {"src": asset_path("icon-512.png", options, manifest=True), "sizes": "512x512", "type": "image/png"},
            {
                "src": asset_path("icon-512-maskable.png", options, manifest=True),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "theme_color": theme_color,
        "background_color": bg_color,
        "display": options.display,
    }
    data["start_url"] = options.start_url or ("." if options.relative_paths else "/")
    data["scope"] = options.scope or ("." if options.relative_paths else "/")
    if options.description:
        data["description"] = options.description
    if options.orientation:
        data["orientation"] = options.orientation
    if options.lang:
        data["lang"] = options.lang
    if options.dir:
        data["dir"] = options.dir
    if options.categories:
        data["categories"] = options.categories
    if options.app_id:
        data["id"] = options.app_id
    data.update(options.manifest_extra)
    return data


def browserconfig_xml(theme_color: str, options: WebMetaOptions | None = None) -> str:
    options = options or WebMetaOptions()
    tile_color = options.tile_color or theme_color
    return f"""<?xml version="1.0" encoding="utf-8"?>
<browserconfig>
  <msapplication>
    <tile>
      <square70x70logo src="{_attr(asset_path("mstile-70x70.png", options))}"/>
      <square150x150logo src="{_attr(asset_path("mstile-150x150.png", options))}"/>
      <wide310x150logo src="{_attr(asset_path("mstile-310x150.png", options))}"/>
      <square310x310logo src="{_attr(asset_path("mstile-310x310.png", options))}"/>
      <TileColor>{_attr(tile_color)}</TileColor>
    </tile>
  </msapplication>
</browserconfig>
"""


def write_web_meta(outdir: Path, name: str, theme_color: str, bg_color: str,
                   options: WebMetaOptions | None = None) -> None:
    options = options or WebMetaOptions()
    (outdir / "site.webmanifest").write_text(
        json.dumps(manifest(name, theme_color, bg_color, options), indent=2), encoding="utf-8"
    )
    (outdir / "favicon-head.html").write_text(
        head_snippet(name, theme_color, bg_color, options), encoding="utf-8"
    )
    if options.windows_tiles:
        (outdir / "browserconfig.xml").write_text(
            browserconfig_xml(theme_color, options), encoding="utf-8"
        )
