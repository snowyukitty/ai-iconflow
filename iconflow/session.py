# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""One render session per command: every render asked for once.

Before 0.9 each stage of a ``review`` opened its own Chromium — the audit, the
plan, the contact sheet, and six more for the Review Lab's light and dark
renders — and rendered the same frames again and again (a Lab review of the
demo family: nine browsers, 67 renders, 43 of them repeats). A
:class:`RenderSession` is owned by the command: it starts at most one browser
per colour scheme, only when something is rendered, and hands every stage a
borrowed rasterizer that remembers what it has already rendered.

What it caches is deliberately narrow: the renderer's own PNG bytes, keyed by
the complete request (operation, the exact SVG text, width, height, the
canonical background, and the scheme). Nothing downstream — PNG optimisation,
flattening, containers, templates — is cached here, so the bytes a build
writes are produced by exactly the code that produced them in 0.8.

A failed render is not cached and a browser that failed to start is not
started again in the same session; one scheme is never substituted for
another. The cache is bounded by bytes: past the budget a new render is still
returned but no longer remembered, so "once" becomes "at least once" rather
than memory without limit.
"""
from __future__ import annotations

import contextlib
import hashlib

from .rasterize import _background_css, _positive_size

#: Raw PNG bytes kept per session before new renders stop being remembered.
#: A Lab review of a five-target family holds well under 10 MB.
DEFAULT_BUDGET_BYTES = 256 * 1024 * 1024

SCHEMES = ("light", "dark", "no-preference")


class RenderSession:
    """Owner of every browser a command uses. Use as a context manager.

    ``factory`` builds a rasterizer for one scheme (``factory(color_scheme=...)``);
    it is resolved when the first render needs it, so a caller that substitutes
    :class:`iconflow.rasterize.Rasterizer` after creating the session still
    substitutes every render.
    """

    def __init__(self, *, factory=None, budget_bytes: int = DEFAULT_BUDGET_BYTES):
        self._factory = factory
        self.budget_bytes = budget_bytes
        self._active: dict[str, object] = {}
        self._failed: dict[str, BaseException] = {}
        self._cache: dict[tuple, bytes] = {}
        self._facades: dict[str, SessionRasterizer] = {}
        self.cached_bytes = 0
        self.launches = 0
        self.renders = 0
        self.hits = 0
        self.uncached = 0
        self._closed = False

    def rasterizer(self, color_scheme: str = "light") -> "SessionRasterizer":
        """A borrowed rasterizer bound to one scheme; entering or closing it is a no-op."""
        if color_scheme not in SCHEMES:
            raise ValueError("color_scheme must be 'light', 'dark', or 'no-preference'")
        if color_scheme not in self._facades:
            self._facades[color_scheme] = SessionRasterizer(self, color_scheme)
        return self._facades[color_scheme]

    def _browser(self, scheme: str):
        if self._closed:
            raise RuntimeError("the render session is closed")
        if scheme in self._failed:
            raise RuntimeError(
                f"the {scheme}-scheme renderer failed to start earlier in this run: "
                f"{self._failed[scheme]}"
            ) from self._failed[scheme]
        if scheme not in self._active:
            factory = self._factory
            if factory is None:
                from . import rasterize

                factory = rasterize.Rasterizer
            # Playwright's sync API runs one driver per thread, so a second
            # scheme borrows the first one's browser and owns only a context.
            # A substituted factory without that ability gets its own instance.
            host = next(iter(self._active.values()), None)
            try:
                if host is not None and getattr(factory, "shares_browser", False):
                    owned = factory(color_scheme=scheme, share=host[1])
                else:
                    owned = factory(color_scheme=scheme)
                active = owned.__enter__()
            except BaseException as exc:
                self._failed[scheme] = exc
                raise
            self.launches += 1
            # Keep what __exit__ must be called on: a factory may return a
            # different object from __enter__ than the one it constructed.
            self._active[scheme] = (owned, active)
        return self._active[scheme][1]

    def _render(self, scheme: str, operation: str, svg_text: str,
                width: int, height: int, bg: str) -> bytes:
        # Validate before the lookup: a warm cache must refuse what a cold one
        # refuses, and Python would otherwise let True stand in for 1.
        width = _positive_size(width)
        height = _positive_size(height)
        background, _transparent = _background_css(bg)
        if not isinstance(svg_text, str):
            raise ValueError("SVG text must be a string")
        key = (operation, hashlib.sha256(svg_text.encode("utf-8")).hexdigest(),
               width, height, background, scheme)
        cached = self._cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        active = self._browser(scheme)
        if operation == "square":
            data = active.render(svg_text, width, bg=bg)
        else:
            data = active.render_rect(svg_text, width, height, bg=bg)
        if not isinstance(data, bytes):
            raise ValueError("renderer returned something other than PNG bytes")
        self.renders += 1
        if self.cached_bytes + len(data) <= self.budget_bytes:
            self._cache[key] = data
            self.cached_bytes += len(data)
        else:
            self.uncached += 1
        return data

    def close(self, exc_info=(None, None, None)) -> None:
        """Close every browser and forget every render. Safe to call twice.

        A cleanup failure is raised only when no other error is propagating:
        the command's own failure is the one the user needs to see.
        """
        active, self._active = self._active, {}
        self._cache.clear()
        self.cached_bytes = 0
        self._closed = True
        error = None
        # Newest first: a scheme that borrowed the first browser closes before it.
        for owned, _entered in reversed(list(active.values())):
            try:
                owned.__exit__(*exc_info)
            except Exception as exc:  # noqa: BLE001 - close the others first
                error = error or exc
        if error is not None and exc_info[0] is None:
            raise error

    def __enter__(self) -> "RenderSession":
        return self

    def __exit__(self, *exc) -> None:
        self.close(exc)

    def stats(self) -> dict:
        return {"launches": self.launches, "renders": self.renders, "hits": self.hits,
                "uncached": self.uncached, "cached_bytes": self.cached_bytes}


class SessionRasterizer:
    """The :class:`~iconflow.rasterize.Rasterizer` protocol, borrowed from a session.

    Stages that own a rasterizer enter and close it; a borrowed one ignores
    both, so passing it into any function that takes ``rasterizer=`` can never
    close a browser another stage still needs.
    """

    def __init__(self, session: RenderSession, color_scheme: str):
        self.session = session
        self.color_scheme = color_scheme

    def render(self, svg_text: str, size: int, bg: str = "transparent") -> bytes:
        return self.session._render(self.color_scheme, "square", svg_text, size, size, bg)

    def render_rect(self, svg_text: str, width: int, height: int,
                    bg: str = "transparent") -> bytes:
        return self.session._render(self.color_scheme, "rect", svg_text, width, height, bg)

    def __enter__(self) -> "SessionRasterizer":
        return self

    def __exit__(self, *exc) -> None:
        return None


def scheme_rasterizer(rasterizer, color_scheme: str):
    """The rasterizer for ``color_scheme`` from a borrowed one, or None.

    A stage handed a session rasterizer for one scheme and needing another
    (the Lab renders light and dark) asks its session; any other rasterizer is
    only usable in its own scheme.
    """
    if isinstance(rasterizer, SessionRasterizer):
        return rasterizer.session.rasterizer(color_scheme)
    if rasterizer is not None and getattr(rasterizer, "color_scheme", None) == color_scheme:
        return rasterizer
    return None


@contextlib.contextmanager
def scheme_sibling(rasterizer, color_scheme: str):
    """A renderer for ``color_scheme`` beside ``rasterizer``, never a second driver.

    A session rasterizer asks its session; an open :class:`Rasterizer` (or a
    lazy one, started here) lends its browser to a new context in that
    scheme, as the session does, because Playwright's sync API allows one
    driver per thread. A substitute renderer has no schemes and is returned
    as it is.
    """
    from .rasterize import LazyRasterizer

    borrowed = scheme_rasterizer(rasterizer, color_scheme)
    if borrowed is not None:
        yield borrowed
        return
    host = rasterizer
    if isinstance(host, LazyRasterizer):
        host = host._session()
    if getattr(type(host), "shares_browser", False):
        if getattr(host, "color_scheme", None) == color_scheme:
            yield host
            return
        with type(host)(color_scheme=color_scheme, share=host._share or host) as sibling:
            yield sibling
        return
    yield rasterizer
