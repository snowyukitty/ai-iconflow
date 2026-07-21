"""Rasterize an SVG to PNG exactly as a browser renders it.

Chromium is the ground truth for how an SVG icon will actually be displayed
(filters, gradients, blend modes, display-p3 color, prefers-color-scheme), so
we render with Playwright rather than a partial SVG library. Every size is
rendered natively at its target resolution — never downscaled from a master —
so small sizes get the browser's own anti-aliasing instead of muddy resampling.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from PIL import Image, ImageColor

# Inline SVG inside a sized box. The box is the screenshot target; omit_background
# keeps real transparency. The SVG is told to fill the box regardless of its own
# intrinsic width/height.
_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';
 img-src data: blob:; style-src 'unsafe-inline'; font-src data:;
 media-src data: blob:; object-src 'none'; frame-src 'none'; connect-src 'none';
 base-uri 'none'; form-action 'none'">
<style>
*{{margin:0;padding:0;border:0}}
html,body{{background:{bg}}}
#wrap{{width:{s}px;height:{s}px;display:block;overflow:hidden}}
#wrap>svg{{width:{s}px;height:{s}px;display:block}}
*,*::before,*::after{{animation:none!important;transition:none!important;
caret-color:transparent!important}}
</style></head><body><div id="wrap">{svg}</div></body></html>"""

_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>\s*", re.I)
_DOCTYPE = re.compile(r"^\s*<!DOCTYPE[^>]*>\s*", re.I)

# Playwright evaluates this in its isolated automation world even though page
# JavaScript is disabled. It removes active SVG/HTML nodes before capture,
# freezes SMIL at its base value, strips event handlers, and detaches external
# resource references. CSP and request interception remain independent layers.
_HARDEN_DOM_JS = """root => {
  const svg = root.querySelector('svg');
  if (svg && typeof svg.pauseAnimations === 'function') {
    svg.pauseAnimations();
    if (typeof svg.setCurrentTime === 'function') svg.setCurrentTime(0);
  }
  root.querySelectorAll(
    'script,iframe,object,embed,audio,video,animate,animateMotion,animateTransform,set'
  ).forEach(node => node.remove());
  root.querySelectorAll('*').forEach(node => {
    for (const attr of [...node.attributes]) {
      const name = attr.name.toLowerCase();
      if (name.startsWith('on')) node.removeAttribute(attr.name);
      if (name === 'href' || name === 'xlink:href' || name === 'src') {
        const value = attr.value.trim().toLowerCase();
        if (!(value.startsWith('#') || value.startsWith('data:') || value.startsWith('blob:'))) {
          node.removeAttribute(attr.name);
        }
      }
    }
  });
}"""


def load_svg(path: str | Path) -> str:
    """Read an SVG file and strip the XML prolog so it can be inlined in HTML."""
    text = Path(path).read_text(encoding="utf-8")
    text = _XML_DECL.sub("", text)
    text = _DOCTYPE.sub("", text)
    return text.strip()


def _positive_size(size: int) -> int:
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ValueError("render size must be a positive integer")
    # Chromium's maximum surface varies by platform. Icons never need anything
    # close to this guard, and rejecting absurd values avoids accidental OOMs.
    if size > 8192:
        raise ValueError("render size must not exceed 8192 pixels")
    return size


def _background_css(bg: str) -> tuple[str, bool]:
    """Return a canonical, injection-safe CSS color and transparency flag."""
    if not isinstance(bg, str):
        raise ValueError("background must be a CSS color string")
    if bg.strip().lower() == "transparent":
        return "transparent", True
    try:
        rgba = ImageColor.getcolor(bg.strip(), "RGBA")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid background color: {bg!r}") from exc
    r, g, b, a = rgba
    return f"rgba({r},{g},{b},{a / 255:.6f})", a == 0


def _validated_png(data: bytes, size: int) -> bytes:
    """Fail loudly if Chromium ever returns a malformed or wrong-sized image."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if image.format != "PNG" or image.size != (size, size):
                raise ValueError(
                    f"renderer returned {image.format or 'unknown'} {image.size}, "
                    f"expected PNG {(size, size)}"
                )
    except (OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("renderer returned invalid PNG data") from exc
    return data


class Rasterizer:
    """A reusable headless-Chromium session. Use as a context manager.

        with Rasterizer() as r:
            png_bytes = r.render(svg_text, 32)
    """

    def __init__(self, color_scheme: str = "light"):
        if color_scheme not in {"light", "dark", "no-preference"}:
            raise ValueError("color_scheme must be 'light', 'dark', or 'no-preference'")
        self.color_scheme = color_scheme
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def __enter__(self) -> "Rasterizer":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:  # pragma: no cover
            raise SystemExit(
                "Playwright is required. Run:  python -m iconflow setup\n"
                "(or: pip install playwright && python -m playwright install chromium)"
            ) from e
        self._pw = sync_playwright().start()
        try:
            # Force sRGB so screenshots are color-stable across machines;
            # display-p3 source colors are gamut-mapped to sRGB.
            self._browser = self._pw.chromium.launch(args=[
                "--force-color-profile=srgb",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-default-apps",
                "--disable-sync",
                "--metrics-recording-only",
                "--no-first-run",
            ])
            # One isolated page is resized and replaced for every frame. Reusing
            # it keeps a 20-size native build fast without sharing any page state:
            # set_content replaces the document and page JavaScript is disabled.
            self._context = self._browser.new_context(
                viewport={"width": 1, "height": 1},
                device_scale_factor=1,
                color_scheme=self.color_scheme,
                reduced_motion="reduce",
                java_script_enabled=False,
                service_workers="block",
                locale="en-US",
                timezone_id="UTC",
            )
            self._context.route("**/*", lambda route: route.abort("blockedbyclient"))
            self._page = self._context.new_page()
        except Exception:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            self._pw.stop()
            self._context = self._browser = self._pw = None
            raise
        return self

    def __exit__(self, *exc) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = self._context = self._browser = self._pw = None

    def render(self, svg_text: str, size: int, bg: str = "transparent") -> bytes:
        """Render `svg_text` to a `size`x`size` PNG (RGBA). bg='transparent'
        preserves alpha; pass a CSS color (e.g. '#0b0d12') for a flat backdrop.

        Page JavaScript, service workers and every external request are disabled.
        Screenshot-time animation suppression also freezes CSS, Web Animations
        and SVG/SMIL animation, making repeated renders deterministic while
        preserving ordinary inline SVG features such as gradients and filters.
        """
        if self._page is None:
            raise RuntimeError("Rasterizer must be used as a context manager")
        if not isinstance(svg_text, str) or not svg_text.strip():
            raise ValueError("svg_text must be a non-empty string")
        size = _positive_size(size)
        bg_css, transparent = _background_css(bg)

        # Request interception on the reusable context is intentionally stricter
        # than CSP alone: SVG images, CSS imports, fonts, foreignObject frames,
        # and future Chromium resource types are rejected before the network.
        self._page.set_viewport_size({"width": size, "height": size})
        self._page.set_content(
            _HTML.format(s=size, svg=svg_text, bg=bg_css),
            wait_until="domcontentloaded",
        )
        el = self._page.locator("#wrap")
        el.evaluate(_HARDEN_DOM_JS)
        data = el.screenshot(
            omit_background=transparent,
            type="png",
            animations="disabled",
            caret="hide",
        )
        return _validated_png(data, size)
