"""Render review artifacts the agent can Read and critique.

Two views:
  contact_sheet  — one icon at every size on 3 backgrounds + pixel-zoom +
                   a SILHOUETTE strip (the distinctiveness / shape test).
  compare_sheet  — several candidate SVGs side by side (the bake-off): pick the
                   most distinctive AND legible finalist.

The single most important quality lever is seeing the icon at the sizes it will
actually be used. Distinctiveness is judged from the silhouette and the small
sizes, never from the 1024 master.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import html
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import assemble
from .build import electron_frames, preview_assets
from .config import review_build_contract
from .rasterize import Rasterizer, load_svg

_SIZES = [16, 24, 32, 48, 64, 128, 256]
_ROWS = [("#ffffff", "#111111"), ("#0b0d12", "#f2f2f2"), ("#8a8a8a", "#000000")]  # bg, label
_PAD = 24
_GAP = 28
_CELL = 256
_ZOOM = 12
_SHEET_BG = (23, 24, 28, 255)       # IconFlow graphite
_TXT = (245, 241, 232, 255)         # warm proof paper
_LABEL = (169, 171, 180, 255)
_SIGNAL = (255, 91, 61, 255)        # proof-gate coral


@dataclass(frozen=True)
class ReviewOptions:
    """Product context carried into an interactive review.

    The defaults keep the legacy ``review master.svg`` call useful, while a
    project config can make the artifact explain *why* the icon exists and
    which deployment contexts it must survive.
    """

    name: str = ""
    user_job: str = ""
    essence: str = ""
    personality: str = ""
    signature_device: str = ""
    cliches: tuple[str, ...] = ()
    targets: tuple[str, ...] = ("web", "pwa")
    theme_color: str = "#17181c"
    background_color: str = "#f5f1e8"
    electron_radius: float = 0.0
    tray_svg: str | Path | None = None
    tray_template_mode: str = "auto"
    color_scheme: str = "light"
    warnings: tuple[str, ...] = ()
    scores: dict[str, int] = field(default_factory=dict)
    notes: str = ""


class _FrozenRenderCache:
    """Read-only RenderCache protocol backed by already-rendered review bytes."""

    def __init__(self, renders: dict[int, bytes]):
        self.renders = renders

    def png(self, size: int) -> bytes:
        try:
            return self.renders[size]
        except KeyError as exc:
            raise ValueError(f"review render cache has no {size}px frame") from exc


def _img(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _pixels(im: Image.Image):
    if hasattr(im, "get_flattened_data"):
        return im.get_flattened_data()
    return im.getdata()


def _font(sz: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, sz)
        except Exception:
            continue
    return ImageFont.load_default()


def alpha_silhouette(png: bytes, fill=(20, 20, 22), bg=(255, 255, 255)) -> Image.Image:
    """Show the raw alpha footprint of the icon on a plain background."""
    im = _img(png)
    a = im.getchannel("A")
    out = Image.new("RGB", im.size, bg)
    shape = Image.new("RGB", im.size, fill)
    out.paste(shape, (0, 0), a)
    return out.convert("RGBA")


def visual_silhouette(png: bytes, bg=(255, 255, 255), threshold: int = 24,
                      fill=(20, 20, 22)) -> Image.Image:
    """Show the visible mark as a single-color shape against `bg`.

    This catches distinctive internal cuts on opaque app-card icons. An alpha
    silhouette of a blue rounded-square card is just a rounded square; this
    visual silhouette turns the card black while preserving white glyphs as
    negative space, which is the shape users actually recognize in a favicon row.
    """
    im = _img(png)
    flat = Image.new("RGB", im.size, bg)
    flat.paste(im.convert("RGB"), (0, 0), im.getchannel("A"))

    mask = Image.new("L", im.size, 0)
    bp = bg[:3]
    out_px = []
    for r, g, b in _pixels(flat):
        out_px.append(255 if max(abs(r - bp[0]), abs(g - bp[1]), abs(b - bp[2])) > threshold else 0)
    mask.putdata(out_px)

    out = Image.new("RGB", im.size, bg)
    shape = Image.new("RGB", im.size, fill)
    out.paste(shape, (0, 0), mask)
    return out.convert("RGBA")


# Backwards-compatible name for callers that imported review.silhouette.
silhouette = alpha_silhouette


def _adaptive_shape_mask(size: int, kind: str) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    if kind == "circle":
        d.ellipse([0, 0, size - 1, size - 1], fill=255)
    elif kind == "rounded":
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255)
    elif kind == "squircle":
        # Rounded-rect proxy: close enough for review contact sheets.
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.30), fill=255)
    else:
        raise ValueError(f"unknown adaptive mask kind: {kind}")
    return mask


def _clip_to_mask(im: Image.Image, mask: Image.Image) -> Image.Image:
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.alpha_composite(im)
    out.putalpha(mask)
    return out


def _maskable_asset(png512: bytes, bg: str = "#ffffff") -> Image.Image:
    return _img(assemble.maskable_asset(png512, bg))


def _draw_safe_zone(im: Image.Image) -> Image.Image:
    out = im.copy()
    d = ImageDraw.Draw(out)
    size = min(out.size)
    r = int(round(size * 0.40))
    c = size // 2
    d.ellipse([c - r, c - r, c + r, c + r], outline=(255, 255, 255, 220), width=max(2, size // 96))
    d.ellipse([c - r, c - r, c + r, c + r], outline=(16, 16, 18, 180), width=max(1, size // 192))
    return out


def contact_sheet(master_svg: str | Path, out: str | Path, *,
                  background_color: str = "#ffffff",
                  color_scheme: str = "light") -> Path:
    svg = load_svg(master_svg)
    f = _font(18)
    fs = _font(14)

    with Rasterizer(color_scheme=color_scheme) as r:
        renders = {s: r.render(svg, s) for s in sorted(set(_SIZES + [512]))}

    cols = len(_SIZES)
    grid_w = _PAD * 2 + cols * _CELL + (cols - 1) * _GAP
    row_h = _CELL + _GAP + 24
    zoom_sizes = (16, 32)
    zoom_h = max(s * _ZOOM for s in zoom_sizes) + 60
    alpha_h = _CELL + 60
    visual_h = _CELL + 60
    mask_h = _CELL + 60
    grid_h = 50 + len(_ROWS) * row_h + zoom_h + alpha_h + visual_h + mask_h + _PAD

    sheet = Image.new("RGBA", (grid_w, grid_h), _SHEET_BG)
    d = ImageDraw.Draw(sheet)
    d.rounded_rectangle([_PAD, 10, _PAD + 28, 38], radius=8, fill=_SIGNAL)
    d.rectangle([_PAD + 11, 17, _PAD + 23, 31], fill=_SHEET_BG)
    d.text((_PAD + 40, 8), "IconFlow Review — actual size, pixel proof, silhouettes, adaptive crops",
           font=f, fill=_TXT)

    y = 44
    for bg, _label in _ROWS:
        x = _PAD
        for s in _SIZES:
            cell = Image.new("RGBA", (_CELL, _CELL), bg)
            cell.alpha_composite(_img(renders[s]), ((_CELL - s) // 2, (_CELL - s) // 2))
            sheet.alpha_composite(cell, (x, y))
            d.rectangle([x, y, x + _CELL - 1, y + _CELL - 1], outline=(70, 72, 80, 255))
            d.text((x + 4, y + _CELL + 4), f"{s}px", font=fs, fill=_LABEL)
            x += _CELL + _GAP
        y += row_h

    # pixel-zoom strip — 16 & 32 blown up on white + dark
    d.text((_PAD, y), "pixel zoom (16px, 32px) — legibility & crispness", font=f, fill=_TXT)
    y += 26
    x = _PAD
    for s in zoom_sizes:
        big = _img(renders[s]).resize((s * _ZOOM, s * _ZOOM), Image.NEAREST)
        for bg in ("#ffffff", "#0b0d12"):
            cell = Image.new("RGBA", big.size, bg)
            cell.alpha_composite(big)
            sheet.alpha_composite(cell, (x, y))
            d.rectangle([x, y, x + big.width - 1, y + big.height - 1], outline=(70, 72, 80, 255))
            x += big.width + _GAP
    y += max(s * _ZOOM for s in zoom_sizes) + 24

    # alpha footprint strip — useful for transparent marks and container shape.
    d.text((_PAD, y), "alpha footprint — does the outer shape have safe-area room?",
           font=f, fill=_TXT)
    y += 26
    x = _PAD
    for s in [32, 48, 64, 128, 256]:
        sil = alpha_silhouette(renders[s]).resize((_CELL, _CELL), Image.NEAREST if s <= 48 else Image.LANCZOS)
        sheet.alpha_composite(sil, (x, y))
        d.rectangle([x, y, x + _CELL - 1, y + _CELL - 1], outline=(70, 72, 80, 255))
        d.text((x + 4, y + _CELL + 4), f"{s}px alpha", font=fs, fill=_LABEL)
        x += _CELL + _GAP
    y += _CELL + 34

    # visual silhouette strip — the distinctiveness test for opaque cards too.
    d.text((_PAD, y), "visual silhouette — is the visible shape distinctive without color?",
           font=f, fill=_TXT)
    y += 26
    x = _PAD
    for s in [32, 48, 64, 128, 256]:
        sil = visual_silhouette(renders[s]).resize((_CELL, _CELL), Image.NEAREST if s <= 48 else Image.LANCZOS)
        sheet.alpha_composite(sil, (x, y))
        d.rectangle([x, y, x + _CELL - 1, y + _CELL - 1], outline=(70, 72, 80, 255))
        d.text((x + 4, y + _CELL + 4), f"{s}px visual", font=fs, fill=_LABEL)
        x += _CELL + _GAP
    y += _CELL + 34

    # maskable previews — Android/adaptive crops and the minimum safe zone.
    d.text((_PAD, y), "maskable preview — keep essential detail inside the 40% safe-zone circle",
           font=f, fill=_TXT)
    y += 26
    x = _PAD
    maskable = _maskable_asset(renders[512], background_color)
    previews = [
        ("safe zone", _draw_safe_zone(maskable)),
        ("circle crop", _clip_to_mask(maskable, _adaptive_shape_mask(512, "circle"))),
        ("squircle crop", _clip_to_mask(maskable, _adaptive_shape_mask(512, "squircle"))),
        ("rounded crop", _clip_to_mask(maskable, _adaptive_shape_mask(512, "rounded"))),
    ]
    for label, im in previews:
        cell = Image.new("RGBA", (_CELL, _CELL), "#ffffff")
        cell.alpha_composite(im.resize((_CELL, _CELL), Image.LANCZOS))
        sheet.alpha_composite(cell, (x, y))
        d.rectangle([x, y, x + _CELL - 1, y + _CELL - 1], outline=(70, 72, 80, 255))
        d.text((x + 4, y + _CELL + 4), label, font=fs, fill=_LABEL)
        x += _CELL + _GAP

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)
    return out


def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def interactive_review(master_svg: str | Path, out: str | Path, *,
                       options: ReviewOptions | None = None) -> Path:
    """Write a self-contained, target-aware Review Lab.

    Light and dark SVG variants are rendered separately, so switching the UI
    scheme tests ``prefers-color-scheme`` rather than merely repainting a cell.
    The artifact stores no remote dependencies and can export the human rubric
    as a small JSON receipt for a later gated ``ship`` step.
    """
    path = Path(master_svg)
    svg = load_svg(path)
    options = options or ReviewOptions(name=path.stem)
    product_name = options.name or path.stem
    sizes = [16, 24, 32, 48, 64, 128, 180, 192, 256, 512, 1024]

    renders: dict[str, dict[int, bytes]] = {}
    for scheme in ("light", "dark"):
        with Rasterizer(color_scheme=scheme) as r:
            renders[scheme] = {s: r.render(svg, s) for s in sizes}

    tray_source_hash = None
    tray_renders = {scheme: {s: renders[scheme][s] for s in (16, 32)}
                    for scheme in ("light", "dark")}
    if options.tray_svg:
        tray_text = load_svg(options.tray_svg)
        tray_source_hash = hashlib.sha256(tray_text.encode("utf-8")).hexdigest()
        for scheme in ("light", "dark"):
            with Rasterizer(color_scheme=scheme) as r:
                tray_renders[scheme] = {s: r.render(tray_text, s) for s in (16, 32)}

    build_contract = review_build_contract(
        theme_color=options.theme_color,
        background_color=options.background_color,
        electron_radius=options.electron_radius,
        tray_template_mode=options.tray_template_mode,
        color_scheme=options.color_scheme,
        tray_source_sha256=tray_source_hash,
    )

    caches = {scheme: _FrozenRenderCache(renders[scheme]) for scheme in ("light", "dark")}
    tray_caches = {
        scheme: _FrozenRenderCache(tray_renders[scheme]) for scheme in ("light", "dark")
    }
    web_assets = {
        scheme: preview_assets(
            caches[scheme], "web", bg_color=options.background_color
        )
        for scheme in ("light", "dark")
    }

    source_hash = hashlib.sha256(svg.encode("utf-8")).hexdigest()
    silhouette_sizes = [32, 48, 64, 128, 256]
    visual = {s: _data_url(_png(visual_silhouette(renders["light"][s])))
              for s in silhouette_sizes}
    alpha = {s: _data_url(_png(alpha_silhouette(renders["light"][s])))
             for s in silhouette_sizes}
    maskable = _img(web_assets["light"]["icon-512-maskable.png"])
    masks = {
        "Safe zone": _data_url(_png(_draw_safe_zone(maskable))),
        "Circle crop": _data_url(_png(_clip_to_mask(maskable, _adaptive_shape_mask(512, "circle")))),
        "Squircle crop": _data_url(_png(_clip_to_mask(maskable, _adaptive_shape_mask(512, "squircle")))),
        "Rounded crop": _data_url(_png(_clip_to_mask(maskable, _adaptive_shape_mask(512, "rounded")))),
    }

    def scheme_image(light: bytes, dark: bytes, alt: str, css: str = "") -> str:
        cls = f' class="scheme-image {css}"' if css else ' class="scheme-image"'
        return (f'<img{cls} src="{_data_url(light)}" data-light="{_data_url(light)}" '
                f'data-dark="{_data_url(dark)}" alt="{html.escape(alt)}">')

    icon_cells = "\n".join(
        f'<figure><div class="cell actual-cell">'
        f'{scheme_image(renders["light"][s], renders["dark"][s], f"{s}px icon")}'
        f'</div><figcaption><strong>{s}</strong> px</figcaption></figure>'
        for s in [16, 24, 32, 48, 64, 128, 256]
    )
    zoom_cells = "\n".join(
        f'<figure class="zoom"><div class="zoom-cell">'
        f'{scheme_image(renders["light"][s], renders["dark"][s], f"{s}px pixel zoom")}'
        f'</div><figcaption>{s}px × pixel grid</figcaption></figure>'
        for s in (16, 32)
    )
    visual_cells = "\n".join(
        f'<figure><img class="preview" src="{visual[s]}" alt="{s}px visual silhouette">'
        f'<figcaption>{s}px visual</figcaption></figure>' for s in silhouette_sizes
    )
    alpha_cells = "\n".join(
        f'<figure><img class="preview" src="{alpha[s]}" alt="{s}px alpha footprint">'
        f'<figcaption>{s}px alpha</figcaption></figure>' for s in silhouette_sizes
    )
    mask_cells = "\n".join(
        f'<figure><img class="preview" src="{url}" alt="{html.escape(label)}">'
        f'<figcaption>{html.escape(label)}</figcaption></figure>'
        for label, url in masks.items()
    )

    target_cards: list[str] = []
    target_set = set(options.targets)
    if target_set & {"web", "pwa"}:
        apple = {
            scheme: web_assets[scheme]["apple-touch-icon.png"]
            for scheme in ("light", "dark")
        }
        target_cards.append(
            '<article class="target-card"><div class="target-label"><span>WEB / PWA</span>'
            '<small>browser + install</small></div><div class="browser-context">'
            f'{scheme_image(renders["light"][32], renders["dark"][32], "Browser tab favicon")}'
            f'<span>{html.escape(product_name)}</span></div><div class="target-art apple">'
            f'{scheme_image(apple["light"], apple["dark"], "Apple touch icon")}'
            '</div></article>'
        )
    if "tauri" in target_set:
        tauri = {
            scheme: preview_assets(caches[scheme], "tauri")["icons/128x128.png"]
            for scheme in ("light", "dark")
        }
        target_cards.append(
            '<article class="target-card"><div class="target-label"><span>TAURI</span>'
            '<small>desktop bundle</small></div><div class="dock-context"><span></span>'
            f'{scheme_image(tauri["light"], tauri["dark"], "Tauri app icon")}'
            '<span></span></div></article>'
        )
    if "electron" in target_set:
        electron = {
            scheme: electron_frames(caches[scheme], options.electron_radius, (128,))[128]
            for scheme in ("light", "dark")
        }
        target_cards.append(
            '<article class="target-card"><div class="target-label"><span>ELECTRON</span>'
            f'<small>radius {options.electron_radius:.2f}</small></div><div class="start-context">'
            f'{scheme_image(electron["light"], electron["dark"], "Electron app icon")}'
            f'<b>{html.escape(product_name)}</b></div></article>'
        )
    if "tray" in target_set:
        tray_assets = {
            scheme: preview_assets(
                caches[scheme], "tray", tray_cache=tray_caches[scheme],
                tray_template_mode=options.tray_template_mode,
            )
            for scheme in ("light", "dark")
        }
        target_cards.append(
            '<article class="target-card"><div class="target-label"><span>TRAY / MENU BAR</span>'
            '<small>16px + template</small></div><div class="menu-context">'
            '<span>09:41</span>'
            f'{scheme_image(tray_assets["light"]["tray/tray@16.png"], tray_assets["dark"]["tray/tray@16.png"], "Color tray icon")}'
            f'{scheme_image(tray_assets["light"]["tray/trayTemplate@2x.png"], tray_assets["dark"]["tray/trayTemplate@2x.png"], "macOS template icon", "template-image")}'
            '<span>•••</span></div></article>'
        )
    target_cards_html = "\n".join(target_cards) or (
        '<p class="empty">No targets selected. The source-size inspection remains available.</p>'
    )

    brief_items = [
        ("User job", options.user_job or "Not recorded"),
        ("Essence", options.essence or "Not recorded"),
        ("Personality", options.personality or "Not recorded"),
        ("Signature", options.signature_device or "Not recorded"),
        ("Avoid", ", ".join(options.cliches) or "Not recorded"),
        ("Targets", ", ".join(options.targets) or "None"),
    ]
    brief_html = "\n".join(
        f'<div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>'
        for label, value in brief_items
    )
    warnings_html = "\n".join(
        f'<li>{html.escape(warning)}</li>' for warning in options.warnings
    ) or '<li class="clean">No automated warnings supplied.</li>'
    axes = [
        ("legibility", "Legibility @16px"),
        ("distinctiveness", "Distinctiveness"),
        ("balance", "Balance & grid"),
        ("color", "Color & contrast"),
        ("scalability", "Scalability"),
        ("craft", "Craft"),
    ]
    rubric_html = "\n".join(
        '<label class="rubric-row">'
        f'<span>{html.escape(label)}</span><input type="range" min="0" max="5" step="1" '
        f'name="{axis}" value="{options.scores.get(axis, 0)}">'
        f'<output>{options.scores.get(axis, 0) or "—"}</output></label>'
        for axis, label in axes
    )
    review_seed = {
        "schema": 1,
        "source": path.name,
        "source_sha256": source_hash,
        "project": product_name,
        "user_job": options.user_job,
        "essence": options.essence,
        "personality": options.personality,
        "signature_device": options.signature_device,
        "cliches": list(options.cliches),
        "targets": list(options.targets),
        "build": build_contract,
        "warnings": list(options.warnings),
    }
    seed_json = json.dumps(review_seed, ensure_ascii=False).replace("</", "<\\/")
    name = html.escape(path.name)
    product = html.escape(product_name)
    notes = html.escape(options.notes)

    doc = f"""<!doctype html>
<html lang="en" data-ui-scheme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>IconFlow Review Lab — {product}</title>
<style>
:root {{ color-scheme: dark; --ink:#17181c; --panel:#212228; --panel-2:#292b32; --line:#3a3c45; --app-theme:{build_contract["theme_color"]};
  --paper:#f5f1e8; --coral:#ff5b3d; --coral-dark:#da3f25; --muted:#a9abb4;
  --pass:#5fd08a; --warn:#f4bd56; --test-bg:#fff; font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--ink); color:#f7f5ef; }}
button,input,textarea {{ font:inherit; }}
.topbar {{ position:sticky; top:0; z-index:20; display:flex; align-items:center; gap:16px; min-height:64px;
  padding:10px max(24px,calc((100vw - 1440px)/2)); background:rgba(23,24,28,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(16px); }}
.brand {{ display:flex; align-items:center; gap:10px; font-weight:760; letter-spacing:-.02em; }}
.brand-mark {{ width:30px; height:30px; border-radius:9px; overflow:hidden; }} .brand-mark svg {{ display:block; width:100%; height:100%; }}
.steps {{ display:flex; flex:1; justify-content:center; gap:4px; }}
.steps span {{ padding:6px 10px; border-radius:999px; color:#858892; font:650 11px/1 ui-monospace,SFMono-Regular,Consolas,monospace; letter-spacing:.06em; text-transform:uppercase; }}
.steps .active {{ color:#fff; background:#30323a; }}
.scheme-switch,.bg-controls {{ display:flex; gap:6px; align-items:center; }}
button {{ border:1px solid var(--line); border-radius:8px; background:#282a31; color:#efede7; padding:7px 10px; cursor:pointer; }}
button:hover,button[aria-pressed="true"] {{ border-color:var(--coral); background:#342a29; }}
main {{ max-width:1440px; margin:0 auto; padding:28px 24px 80px; }}
.hero {{ display:grid; grid-template-columns:minmax(0,1.5fr) minmax(320px,.8fr); gap:18px; margin-bottom:24px; }}
.hero-card,.panel {{ border:1px solid var(--line); border-radius:16px; background:linear-gradient(145deg,#23242a,#1e1f24); box-shadow:0 22px 70px rgba(0,0,0,.18); }}
.hero-card {{ position:relative; min-height:260px; padding:28px; overflow:hidden; }}
.hero-card::after {{ content:""; position:absolute; width:270px; height:270px; right:-80px; top:-130px; border:64px solid rgba(255,91,61,.12); border-radius:52px; transform:rotate(10deg); }}
.eyebrow {{ margin:0 0 10px; color:var(--coral); font:700 12px/1 ui-monospace,SFMono-Regular,Consolas,monospace; letter-spacing:.09em; text-transform:uppercase; }}
h1 {{ max-width:800px; margin:0; font-size:clamp(34px,5vw,68px); line-height:.98; letter-spacing:-.055em; }}
.source-line {{ margin-top:22px; color:var(--muted); font:13px ui-monospace,SFMono-Regular,Consolas,monospace; }}
.source-line b {{ color:#fff; }}
.gate-card {{ display:flex; flex-direction:column; justify-content:space-between; padding:22px; }}
.gate-status {{ display:flex; justify-content:space-between; align-items:center; gap:12px; }}
.gate-pill {{ padding:7px 10px; border-radius:999px; color:#d8d9de; background:#30323a; font-weight:700; font-size:12px; }}
.gate-pill.ready {{ color:#102318; background:var(--pass); }}
.gate-pill.blocked {{ color:#281b07; background:var(--warn); }}
.gate-card ul {{ margin:18px 0 0; padding-left:20px; color:#d7d5cf; font-size:14px; }}
.gate-card li+li {{ margin-top:7px; }} .gate-card .clean {{ color:var(--pass); }}
.panel {{ margin-top:18px; padding:22px; }}
.panel-head {{ display:flex; justify-content:space-between; gap:16px; align-items:end; margin-bottom:18px; }}
.panel-head h2 {{ margin:0; font-size:22px; letter-spacing:-.025em; }}
.panel-head p {{ margin:4px 0 0; max-width:700px; color:var(--muted); font-size:13px; }}
.brief {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1px; padding:1px; background:var(--line); border-radius:12px; overflow:hidden; }}
.brief div {{ min-height:82px; padding:15px; background:#24262c; }}
.brief dt {{ color:#8f929c; font:650 11px ui-monospace,SFMono-Regular,Consolas,monospace; letter-spacing:.07em; text-transform:uppercase; }}
.brief dd {{ margin:8px 0 0; color:#f4f2ec; font-size:14px; line-height:1.35; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:14px; }}
figure {{ margin:0; }} figcaption {{ margin-top:7px; color:var(--muted); font-size:12px; }}
figcaption strong {{ color:#fff; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }}
.cell {{ min-height:142px; display:grid; place-items:center; background:var(--test-bg); border:1px solid #474a53; border-radius:10px; }}
.scheme-image {{ display:block; max-width:100%; object-fit:contain; }}
.preview {{ width:132px; height:132px; object-fit:contain; background:#fff; border:1px solid #474a53; border-radius:10px; }}
.zoom-grid {{ grid-template-columns:repeat(2,minmax(240px,1fr)); }}
.zoom-cell {{ height:264px; display:grid; place-items:center; background:var(--test-bg); border:1px solid #474a53; border-radius:10px; overflow:hidden; }}
.zoom:nth-child(1) img {{ width:192px; height:192px; }} .zoom:nth-child(2) img {{ width:256px; height:256px; }}
.zoom img {{ image-rendering:pixelated; }}
.target-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:14px; }}
.target-card {{ min-height:220px; padding:14px; background:#26282e; border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
.target-label {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }}
.target-label span {{ color:#fff; font:700 11px ui-monospace,SFMono-Regular,Consolas,monospace; letter-spacing:.08em; }}
.target-label small {{ color:#8e919b; }}
.browser-context {{ height:42px; display:flex; align-items:center; gap:9px; padding:8px 12px; color:#25262b; background:#f7f5ef; border-radius:8px 8px 2px 2px; font-size:12px; box-shadow:inset 0 3px var(--app-theme); }}
.browser-context img {{ width:18px; height:18px; }}
.target-art {{ display:grid; place-items:center; height:130px; margin-top:8px; border-radius:7px; background:#e6e1d7; }} .target-art img {{ width:94px; height:94px; }}
.dock-context {{ height:164px; display:flex; align-items:end; justify-content:center; gap:10px; padding:18px; border-radius:10px; background:radial-gradient(circle at 50% 10%,#817d80,#292a30 72%); }}
.dock-context span {{ width:46px; height:46px; border-radius:12px; background:rgba(255,255,255,.22); }} .dock-context img {{ width:96px; height:96px; }}
.start-context {{ height:164px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:10px; color:#eee; border-radius:10px; background:#111216; }}
.start-context img {{ width:96px; height:96px; }} .start-context b {{ font-size:12px; font-weight:600; }}
.menu-context {{ height:90px; display:flex; justify-content:flex-end; align-items:center; gap:10px; padding:16px; color:#24252a; background:#f5f2ec; border-radius:10px; font-size:11px; }}
.menu-context img {{ width:18px; height:18px; }} .menu-context .template-image {{ width:22px; height:22px; }}
[data-ui-scheme="dark"] .browser-context,[data-ui-scheme="dark"] .menu-context {{ color:#f3f1eb; background:#17181c; }}
[data-ui-scheme="dark"] .template-image {{ filter:invert(1); }}
.review-layout {{ display:grid; grid-template-columns:minmax(0,1.2fr) minmax(300px,.8fr); gap:18px; }}
.rubric {{ display:grid; gap:8px; }} .rubric-row {{ display:grid; grid-template-columns:145px 1fr 28px; gap:10px; align-items:center; color:#e9e7e1; font-size:13px; }}
.rubric-row input {{ accent-color:var(--coral); }} .rubric-row output {{ color:var(--coral); font:700 14px ui-monospace,SFMono-Regular,Consolas,monospace; text-align:right; }}
textarea {{ width:100%; min-height:152px; resize:vertical; border:1px solid var(--line); border-radius:10px; padding:12px; color:#f4f2ed; background:#1d1e23; line-height:1.5; }}
.review-actions {{ display:flex; gap:8px; justify-content:flex-end; margin-top:12px; }} .primary {{ border-color:var(--coral-dark); background:var(--coral); color:#22130f; font-weight:750; }}
.empty {{ color:var(--muted); }}
@media (max-width:900px) {{ .hero,.review-layout {{ grid-template-columns:1fr; }} .steps {{ display:none; }} .brief {{ grid-template-columns:1fr 1fr; }} }}
@media (max-width:560px) {{ .topbar {{ flex-wrap:wrap; }} main {{ padding:18px 12px 60px; }} .brief {{ grid-template-columns:1fr; }} .zoom-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header class="topbar">
  <div class="brand"><span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 1024 1024"><rect width="1024" height="1024" rx="220" fill="#191a20"/><path d="M256 288H640V448H448V640H576V704H704V768" fill="none" stroke="#fff4e8" stroke-width="128" stroke-linecap="square" stroke-linejoin="round"/><rect x="512" y="320" width="256" height="256" rx="32" fill="#ff5a4f"/><rect x="576" y="384" width="128" height="128" rx="12" fill="#191a20"/></svg></span>IconFlow</div>
  <nav class="steps" aria-label="IconFlow stages"><span>Brief</span><span>Explore</span><span>Compare</span><span class="active">Inspect</span><span>Ship</span><span>Learn</span></nav>
  <div class="scheme-switch" aria-label="Rendered SVG color scheme">
    <button type="button" data-scheme="light" aria-pressed="true">Light SVG</button>
    <button type="button" data-scheme="dark" aria-pressed="false">Dark SVG</button>
  </div>
</header>
<main>
  <section class="hero">
    <div class="hero-card"><p class="eyebrow">Review Lab · source {source_hash[:12]}</p><h1>{product}</h1>
      <p class="source-line"><b>{name}</b> · one semantic master · proven at actual size</p></div>
    <aside class="hero-card gate-card"><div class="gate-status"><div><p class="eyebrow">Ship gate</p><strong id="gateCopy">Scores required</strong></div><span class="gate-pill" id="gatePill">Not scored</span></div>
      <ul>{warnings_html}</ul></aside>
  </section>

  <section class="panel"><div class="panel-head"><div><h2>Brief</h2><p>Intent is part of the artifact, so visual decisions remain tied to the product job.</p></div></div><dl class="brief">{brief_html}</dl></section>

  <section class="panel"><div class="panel-head"><div><h2>Actual size</h2><p>Start at 16px. Scheme buttons rerendered the SVG with real prefers-color-scheme values.</p></div>
    <div class="bg-controls"><button type="button" data-bg="#ffffff">White</button><button type="button" data-bg="#0b0d12">Dark</button><button type="button" data-bg="#8a8a8a">Gray</button><input id="customBg" type="color" value="#ffffff" aria-label="Custom test background"></div></div>
    <div class="grid">{icon_cells}</div></section>

  <section class="panel"><div class="panel-head"><div><h2>Pixel proof</h2><p>Nearest-neighbor enlargement exposes counters, anti-aliasing and lost signature cuts.</p></div></div><div class="grid zoom-grid">{zoom_cells}</div></section>

  <section class="panel"><div class="panel-head"><div><h2>Target contexts</h2><p>These previews apply the selected build transforms instead of judging the raw master alone.</p></div></div><div class="target-grid">{target_cards_html}</div></section>

  <section class="panel"><div class="panel-head"><div><h2>Visual silhouette</h2><p>The primary distinctiveness test. Color is removed; white glyphs remain negative space.</p></div></div><div class="grid">{visual_cells}</div></section>
  <section class="panel"><div class="panel-head"><div><h2>Alpha footprint</h2><p>Use this for container shape, transparent marks and safe-area balance—not app-card identity.</p></div></div><div class="grid">{alpha_cells}</div></section>
  <section class="panel"><div class="panel-head"><div><h2>Maskable proof</h2><p>The safe circle has radius 40% of the canvas. Essential detail must survive every crop.</p></div></div><div class="grid">{mask_cells}</div></section>

  <section class="panel"><div class="panel-head"><div><h2>Decision receipt</h2><p>Every axis must reach 4/5. Export the result for a gated ship and casebook record.</p></div></div>
    <div class="review-layout"><div class="rubric" id="reviewRubric">{rubric_html}</div><div><label for="reviewNotes" class="eyebrow">Why this wins / what changed</label><textarea id="reviewNotes" placeholder="Name the weakest axis, the decisive change, and why the silhouette is ownable.">{notes}</textarea>
      <div class="review-actions"><button type="button" id="resetReview">Reset</button><button type="button" class="primary" id="exportReview">Export review.json</button></div></div></div>
  </section>
</main>
<script>
const seed = {seed_json};
const root = document.documentElement;
const storageKey = `iconflow-review-${{seed.source_sha256}}`;
function setScheme(scheme) {{
  root.dataset.uiScheme = scheme;
  for (const image of document.querySelectorAll('.scheme-image')) image.src = image.dataset[scheme];
  for (const button of document.querySelectorAll('[data-scheme]')) button.setAttribute('aria-pressed', String(button.dataset.scheme === scheme));
}}
for (const button of document.querySelectorAll('[data-scheme]')) button.addEventListener('click', () => setScheme(button.dataset.scheme));
for (const button of document.querySelectorAll('[data-bg]')) button.addEventListener('click', () => root.style.setProperty('--test-bg', button.dataset.bg));
document.getElementById('customBg').addEventListener('input', event => root.style.setProperty('--test-bg', event.target.value));

const scoreInputs = [...document.querySelectorAll('#reviewRubric input')];
const notesInput = document.getElementById('reviewNotes');
function readReview() {{
  const scores = Object.fromEntries(scoreInputs.map(input => [input.name, Number(input.value)]));
  const complete = Object.values(scores).every(value => value >= 1);
  const passing = complete && seed.warnings.length === 0 && Object.values(scores).every(value => value >= 4);
  const blocked = seed.warnings.length > 0 || complete;
  return {{...seed, scores, notes:notesInput.value.trim(), status:passing ? 'ready' : blocked ? 'blocked' : 'unscored'}};
}}
function paintGate() {{
  const review = readReview();
  for (const input of scoreInputs) input.nextElementSibling.value = input.value === '0' ? '—' : input.value;
  const pill = document.getElementById('gatePill');
  pill.className = `gate-pill ${{review.status === 'ready' ? 'ready' : review.status === 'blocked' ? 'blocked' : ''}}`;
  pill.textContent = review.status === 'ready' ? 'Ready to ship' : review.status === 'blocked' ? 'Revision required' : 'Not scored';
  document.getElementById('gateCopy').textContent = review.status === 'ready' ? 'All axes ≥ 4' : review.status === 'blocked' ? (seed.warnings.length ? 'Automated warning blocks ship' : 'One or more axes < 4') : 'Scores required';
  try {{ localStorage.setItem(storageKey, JSON.stringify({{scores:review.scores, notes:review.notes}})); }} catch (_) {{ /* file:// storage can be disabled. */ }}
}}
function restore() {{
  try {{
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
    if (!saved) return;
    for (const input of scoreInputs) if (saved.scores?.[input.name] != null) input.value = saved.scores[input.name];
    if (typeof saved.notes === 'string') notesInput.value = saved.notes;
  }} catch (_) {{ /* A malformed local draft should never block inspection. */ }}
}}
for (const input of scoreInputs) input.addEventListener('input', paintGate);
notesInput.addEventListener('input', paintGate);
document.getElementById('resetReview').addEventListener('click', () => {{ try {{ localStorage.removeItem(storageKey); }} catch (_) {{}} for (const input of scoreInputs) input.value = 0; notesInput.value = ''; paintGate(); }});
document.getElementById('exportReview').addEventListener('click', () => {{
  const blob = new Blob([JSON.stringify(readReview(), null, 2) + '\\n'], {{type:'application/json'}});
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${{seed.source.replace(/\\.svg$/i,'')}}-review.json`; link.click(); URL.revokeObjectURL(link.href);
}});
restore(); paintGate();
</script>
</body>
</html>
"""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out


def compare_sheet(candidates: list[tuple[str, str | Path]], out: str | Path) -> Path:
    """Bake-off: render each (label, svg_path) as a row across small sizes, a
    silhouette, and a dark-bg cell, so finalists can be compared head-to-head."""
    sizes = [16, 24, 32, 48, 64, 128]
    cell = 150
    f = _font(20)
    fs = _font(13)

    rendered = []
    with Rasterizer() as r:
        for label, path in candidates:
            svg = load_svg(path)
            rendered.append((label, {s: r.render(svg, s) for s in sizes}))

    extra = 2  # visual silhouette + dark-bg cells
    cols = len(sizes) + extra
    grid_w = _PAD * 2 + cols * cell + (cols - 1) * 14
    row_h = cell + 52
    grid_h = 52 + len(candidates) * row_h + _PAD

    sheet = Image.new("RGBA", (grid_w, grid_h), _SHEET_BG)
    d = ImageDraw.Draw(sheet)
    d.rounded_rectangle([_PAD, 12, _PAD + 26, 38], radius=7, fill=_SIGNAL)
    d.text((_PAD + 38, 10), "IconFlow Bake-off — pick the most DISTINCTIVE mark that still reads at 16px",
           font=f, fill=_TXT)
    # column headers
    hx = _PAD
    for s in sizes:
        d.text((hx + 4, 36), f"{s}px", font=fs, fill=(150, 152, 160, 255))
        hx += cell + 14
    d.text((hx + 4, 36), "visual shape", font=fs, fill=(150, 152, 160, 255))
    d.text((hx + cell + 18, 36), "on dark", font=fs, fill=(150, 152, 160, 255))

    y = 56
    for label, renders in rendered:
        x = _PAD
        for s in sizes:
            c = Image.new("RGBA", (cell, cell), "#ffffff")
            c.alpha_composite(_img(renders[s]), ((cell - s) // 2, (cell - s) // 2))
            sheet.alpha_composite(c, (x, y))
            d.rectangle([x, y, x + cell - 1, y + cell - 1], outline=(70, 72, 80, 255))
            x += cell + 14
        # Visual silhouette of the 64px render. This preserves internal
        # negative-space cuts on opaque card icons.
        sil = visual_silhouette(renders[64]).resize((cell, cell), Image.LANCZOS)
        sheet.alpha_composite(sil, (x, y))
        d.rectangle([x, y, x + cell - 1, y + cell - 1], outline=(70, 72, 80, 255))
        x += cell + 14
        # 32px on dark
        c = Image.new("RGBA", (cell, cell), "#0b0d12")
        c.alpha_composite(_img(renders[32]), ((cell - 32) // 2, (cell - 32) // 2))
        sheet.alpha_composite(c, (x, y))
        d.rectangle([x, y, x + cell - 1, y + cell - 1], outline=(70, 72, 80, 255))

        d.text((_PAD, y + cell + 6), label, font=f, fill=_TXT)
        y += row_h

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)
    return out
