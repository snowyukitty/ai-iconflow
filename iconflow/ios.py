# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The iOS / iPadOS app icon: one master, Apple's three appearances (0.10).

Xcode builds every iOS size from one 1024 px image per appearance (an asset
catalog's "Single Size" set). Apple's contract, in its own words: "Provide
your tinted app icon as a grayscale image. Provide your dark app icon with a
transparent background so the system-provided background can show through."
Both are optional: without them iOS applies its own treatment.

IconFlow derives the variants from the master's *semantic layers*
(``docs/SVG_TECHNIQUES.md`` §11) or from a linked ``ios_dark_svg``, and
never fakes one:

- **Light** — the declared ``iconflow-background`` extended to the full
  canvas (iOS masks the square itself; an inset card would show a border),
  flattened, RGB. Without a declared layer: the master flattened onto
  ``background_color``.
- **Dark** — the master without its background (or the linked source),
  rendered in the dark colour scheme on transparency, RGBA.
- **Tinted** — the dark image composited once over black and converted to
  luminance, mode ``L``: one fixed mapping, no per-image stretching.

Xcode's ``actool`` enforces none of these encodings (probed on Xcode 26.6: a
light icon with alpha and an RGB "tinted" image compile silently), so
:func:`validate_files` does, for every build, audit and imported plan.
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from dataclasses import dataclass
from typing import Mapping

from PIL import Image, ImageChops, ImageDraw, ImageStat

from . import assemble, ladder
from .findings import Finding

IOS_DIR = "ios/AppIcon.appiconset"
CONTENTS = f"{IOS_DIR}/Contents.json"
LIGHT = f"{IOS_DIR}/icon-1024.png"
DARK = f"{IOS_DIR}/icon-1024-dark.png"
TINTED = f"{IOS_DIR}/icon-1024-tinted.png"
COMPOSER_MARK = "ios/icon-composer/mark.svg"
README = "ios/README.md"
#: Every file the target can write. A build replaces exactly the ones it plans
#: and refuses to leave the others behind from an earlier build (C-F18).
ALL_FILES = (CONTENTS, LIGHT, DARK, TINTED, COMPOSER_MARK, README)
SIZE = 1024

#: ``build.ios_variants``: derive dark and tinted where IconFlow can, or leave
#: both to iOS.
VARIANTS = ("auto", "system")
APPEARANCES = ("light", "dark", "tinted")
APPEARANCE_FILES = {"light": LIGHT, "dark": DARK, "tinted": TINTED}

BACKGROUND_ID = "iconflow-background"
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

# The probes (docs/OUTPUT_TARGETS.md "ios"). Heuristics, written down once:
#: iOS draws a dark gradient behind a dark icon; this is its approximate
#: darkest tone, the harder ground for a dark mark.
DARK_GROUND = (28, 28, 30)
#: WCAG contrast a mark pixel needs against that ground to count as legible.
DARK_CONTRAST = 3.0
#: Share of the mark's opaque area that must be legible on the dark ground.
DARK_LEGIBLE_SHARE = 0.5
#: Per-channel distance within which a mark pixel is the card's own colour: a
#: cut painted in the background colour (an eye, a counter, a slot), which
#: reads as a cut on the dark ground too and is not counted either way.
COUNTER_TOLERANCE = 24
#: Below this opaque share of the canvas the dark layer is empty.
MIN_MARK_COVERAGE = 0.02
#: Mean luminance (0-255) the tinted image's mark must keep: iOS tints by
#: luminance, so a dark mark disappears into the tint's dark ground.
TINTED_MIN_MEAN = 96
#: Two colours that each cover this share of the mark, differ by at least
#: MERGE_RGB in RGB, but land within MERGE_GREY grey levels, are one tone in
#: the tinted icon (R10): advised, since only a person knows if it matters.
MERGE_SHARE = 0.03
MERGE_RGB = 80
MERGE_GREY = 16

_NON_PAINT = {"title", "desc", "defs", "style", "metadata"}
_SHAPES = {"rect", "circle", "ellipse", "path", "polygon"}
#: Attributes that change how the background paints; a background carrying
#: one cannot be extended (or removed) as a plain fill without changing it.
_REFUSED_ATTRS = ("transform", "filter", "mask", "clip-path", "opacity",
                  "fill-opacity", "style", "class", "data-lod", "display", "visibility",
                  # Conditional processing decides whether the card draws at all (AA02).
                  "requiredExtensions", "requiredFeatures", "systemLanguage")
_URL_RE = re.compile(r"^url\(\s*#([^)\s]+)\s*\)$")
_GRADIENTS = {"linearGradient", "radialGradient"}


class LayerError(ValueError):
    """A declared semantic layer IconFlow cannot honour; says which rule."""


@dataclass(frozen=True)
class Layers:
    """What the master declares (immutable: every derivation re-parses)."""

    declared: bool
    fill: str | None = None
    hint: str = ""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _parse(svg_text: str) -> ET.Element:
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    try:
        return ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise LayerError(f"SVG source is not well-formed XML: {exc}") from exc


def _view_box(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox")
    try:
        if raw:
            values = [float(v) for v in re.split(r"[\s,]+", raw.strip())]
            if len(values) == 4 and values[2] > 0 and values[3] > 0:
                return tuple(values)  # type: ignore[return-value]
        width, height = float(root.get("width", "")), float(root.get("height", ""))
        if width > 0 and height > 0:
            return (0.0, 0.0, width, height)
    except ValueError:
        pass
    raise LayerError("the master needs a viewBox (or numeric width and height) "
                     "for its background to be extended")


def _first_painted(root: ET.Element) -> ET.Element | None:
    for child in root:
        if _local(child.tag) not in _NON_PAINT:
            return child
    return None


def _candidate_hint(root: ET.Element) -> str:
    first = _first_painted(root)
    if first is not None and _local(first.tag) == "rect" and first.get("fill") not in (None, "none"):
        return ('its first shape looks like a card: give it id="iconflow-background" '
                "(docs/SVG_TECHNIQUES.md §11) so iOS can extend it to full bleed and "
                "derive the dark and tinted icons")
    return ('declare the card or backdrop as id="iconflow-background" '
            "(docs/SVG_TECHNIQUES.md §11), or link build.ios_dark_svg")


def resolve(svg_text: str) -> Layers:
    """The master's declared background, after proving IconFlow can honour it.

    Only a *declared* layer counts: geometry cannot prove intent, so an
    untagged master gets the light icon alone and a hint (C-F04). A declared
    layer outside the supported subset is a :class:`LayerError`, never a
    silent fallback.
    """
    root = _parse(svg_text)
    marked = [e for e in root.iter() if e.get("id") == BACKGROUND_ID]
    if not marked:
        return Layers(declared=False, hint=_candidate_hint(root))
    if len(marked) > 1:
        raise LayerError(f'more than one element is id="{BACKGROUND_ID}"')
    background = marked[0]
    name = _local(background.tag)
    if background not in list(root):
        raise LayerError(f'id="{BACKGROUND_ID}" must be a direct child of <svg>, '
                         "so no group transform or effect applies to it")
    if _first_painted(root) is not background:
        raise LayerError(f'id="{BACKGROUND_ID}" must be the first painted element: '
                         "nothing may be drawn beneath the background")
    extra = [_local(child.tag) for child in background
             if _local(child.tag) not in {"title", "desc", "metadata"}]
    if extra:
        # Full bleed replaces the element and everything in it: a stylesheet or
        # an animation inside the card would vanish with it (AB02).
        raise LayerError(f'id="{BACKGROUND_ID}" must be one empty shape; it holds <{extra[0]}>')
    if name not in _SHAPES:
        raise LayerError(f'id="{BACKGROUND_ID}" must be one shape ('
                         + ", ".join(sorted(_SHAPES)) + f"), not <{name}>")
    for attr in _REFUSED_ATTRS:
        if background.get(attr) is not None:
            raise LayerError(f'id="{BACKGROUND_ID}" carries {attr}; the background must '
                             "paint with a plain fill to be extended or removed")
    fill = (background.get("fill") or "").strip()
    if not fill or fill == "none":
        raise LayerError(f'id="{BACKGROUND_ID}" must declare its fill')
    match = _URL_RE.match(fill)
    if match:
        target = [e for e in root.iter() if e.get("id") == match.group(1)]
        if len(target) != 1 or _local(target[0].tag) not in _GRADIENTS:
            raise LayerError(f'id="{BACKGROUND_ID}" fill {fill} must name one '
                             "linearGradient or radialGradient in the master")
    else:
        try:
            assemble.opaque_color(fill, "background fill")
        except ValueError as exc:
            raise LayerError(f'id="{BACKGROUND_ID}": {exc}') from exc
    # A reference is found the way the renderer resolves it: percent-escapes
    # decoded first, so "#iconflow%2Dbackground" is the background too (AB01).
    reference = re.compile(rf"#{re.escape(BACKGROUND_ID)}(?![\w-])")
    for element in root.iter():
        for attr, value in element.attrib.items():
            if element is background and attr == "id":
                continue
            if reference.search(unquote(value)):
                raise LayerError(f"<{_local(element.tag)} {_local(attr)}> refers to the "
                                 "background; the mark must not depend on it")
    _check_stylesheets(root, name)
    return Layers(declared=True, fill=fill)


def _check_stylesheets(root: ET.Element, tag: str) -> None:
    """Refuse a stylesheet that could paint the background or depend on it.

    Every rule's selectors are read by a linear scanner (:func:`_css_rules`,
    :func:`_selector_problem`) and validated positively: compounds of an
    optional type and ``.class``/``#id`` qualifiers, joined by descendant or
    child combinators. Within that subset a rule is refused when it names the
    background's id, or selects by bare element type the background has now
    or will have once extended (a full bleed is a ``rect``) — with a class or
    id qualifier it cannot reach the background, which carries neither but
    its own id (R01, V02, W01-W03).
    """
    risky = {tag.lower(), "rect"}
    for style in root.iter(f"{{{SVG_NS}}}style"):
        for selector in _css_rules("".join(style.itertext())):
            problem = _selector_problem(selector, risky)
            if problem:
                raise LayerError(
                    f"the stylesheet rule '{selector}' {problem}; with "
                    f"id=\"{BACKGROUND_ID}\" declared, select the mark by class or id")


def _css_rules(css: str) -> list[str]:
    """Every selector of every style rule, in one forward pass (X01-X07).

    Beside a declared background a stylesheet is held to a deliberately small
    language that cannot be mis-read: top-level style rules and one level of
    ``@media`` blocks of them (enough for ``prefers-color-scheme``), comments,
    and nothing else — no strings, escapes, nested rules or other at-rules,
    each of which lets a rule hide from a check like this one. No master in
    IconFlow's repository uses a stylesheet at all; a linked ``ios_dark_svg``
    covers any dark styling this refuses.
    """
    if any(char in css for char in "\\\"'"):
        raise LayerError("a stylesheet beside a declared background may not hold strings or "
                         "escapes; link build.ios_dark_svg for dark styling instead")
    if re.search(r"url\s*\(", css, re.I):
        # An unquoted url() can hold comment markers (Y01) and can point at
        # the background's geometry (Y02).
        raise LayerError("a stylesheet beside a declared background may not use url(); "
                         "link build.ios_dark_svg for dark styling instead")
    parts, i = [], 0
    while True:  # comments, removed in one pass; with no strings none can hide in one
        opened = css.find("/*", i)
        if opened < 0:
            parts.append(css[i:])
            break
        parts.append(css[i:opened])
        closed = css.find("*/", opened + 2)
        if closed < 0:
            raise LayerError("a stylesheet comment is not closed")
        i = closed + 2
    css = "".join(parts)
    selectors: list[str] = []
    depth, i, n = 0, 0, len(css)
    while i < n:
        start = i
        while i < n and css[i] not in "{};":
            i += 1
        prelude = css[start:i].strip()
        if i >= n:
            if prelude:
                raise LayerError(f"the stylesheet ends inside '{prelude}'")
            break
        if css[i] == ";":
            if prelude:
                raise LayerError(f"the stylesheet statement '{prelude}' is not a style rule; "
                                 "beside a declared background only rules and @media are allowed")
            i += 1
            continue
        if css[i] == "}":
            if prelude or depth == 0:
                raise LayerError("the stylesheet closes a block it never opened")
            depth -= 1
            i += 1
            continue
        if prelude.startswith("@"):
            keyword = re.match(r"@[A-Za-z-]+", prelude)
            if depth == 0 and keyword and keyword.group(0).lower() == "@media":
                depth, i = 1, i + 1
                continue
            raise LayerError(f"the stylesheet uses '{prelude.split()[0]}'; beside a declared "
                             "background only style rules and @media blocks are allowed")
        selectors.extend(part.strip() for part in prelude.split(","))
        closed = css.find("}", i + 1)
        if closed < 0:
            raise LayerError("a stylesheet rule is not closed")
        if css.find("{", i + 1, closed) >= 0:
            raise LayerError("a stylesheet rule nests another rule inside it; with "
                             f'id="{BACKGROUND_ID}" declared, write each rule at the top')
        i = closed + 1
    if depth:
        raise LayerError("a stylesheet @media block is not closed")
    return selectors


def _is_name_char(char: str) -> bool:
    return char.isalnum() or char in "-_" or ord(char) > 0x7F


def _ident(selector: str, i: int) -> int:
    """The end of a CSS identifier starting at ``i`` (``i`` when there is none).

    Unescaped identifiers only: a letter, ``_``, a non-ASCII character, or
    ``-`` followed by one of those or by ``-``; escapes are refused upstream.
    """
    j = i
    if j < len(selector) and selector[j] == "-":
        j += 1
        if j < len(selector) and selector[j] == "-":
            j += 1
    if j >= len(selector) or not (selector[j].isalpha() or selector[j] == "_"
                                  or ord(selector[j]) > 0x7F or j > i + 1):
        return i if j == i or j < i + 2 else j
    while j < len(selector) and _is_name_char(selector[j]):
        j += 1
    return j


def _selector_problem(selector: str, risky: set[str]) -> str | None:
    """Why ``selector`` is unsafe beside a declared background, or None.

    One left-to-right pass over the characters (no backtracking): compounds
    are an optional type identifier followed by ``.class`` / ``#id``
    qualifiers; between compounds, whitespace and at most one ``>``.
    """
    unsupported = "uses selector syntax IconFlow cannot prove harmless"
    if not selector:
        return unsupported
    i, n, compounds = 0, len(selector), 0
    while i < n:
        element = None
        end = _ident(selector, i)
        if end > i and selector[i] not in ".#":
            element = selector[i:end]
            i = end
        qualified = False
        while i < n and selector[i] in ".#":
            kind = selector[i]
            end = _ident(selector, i + 1)
            if end == i + 1:
                return unsupported
            name = selector[i + 1:end]
            if kind == "#" and name == BACKGROUND_ID:
                return "selects the background"
            qualified = True
            i = end
        if element is None and not qualified:
            return unsupported
        if element is not None and element.lower() in risky and not qualified:
            return f"selects every <{element}>, the background among them"
        compounds += 1
        if i >= n:
            break
        start = i
        while i < n and selector[i].isspace():
            i += 1
        if i < n and selector[i] == ">":
            i += 1
            while i < n and selector[i].isspace():
                i += 1
        if i == start or i >= n:
            return unsupported
    return None if compounds else unsupported


def _derive(svg_text: str, replace: bool) -> str:
    root = _parse(svg_text)
    background = next(e for e in root if e.get("id") == BACKGROUND_ID)
    index = list(root).index(background)
    root.remove(background)
    if replace:
        x, y, width, height = _view_box(root)
        root.insert(index, ET.Element(f"{{{SVG_NS}}}rect", {
            "id": BACKGROUND_ID, "x": f"{x:g}", "y": f"{y:g}",
            "width": f"{width:g}", "height": f"{height:g}", "fill": background.get("fill"),
            # Explicit, so a stroke inherited from an ancestor cannot reappear
            # on the full-bleed card (AA02).
            "stroke": "none",
        }))
    return ET.tostring(root, encoding="unicode")


def full_bleed(svg_text: str) -> str:
    """The master with its declared background stretched to the whole canvas.

    The fill is kept as written: a solid colour is unchanged; an
    ``objectBoundingBox`` gradient is re-mapped onto the canvas (the field the
    card showed, enlarged), a ``userSpaceOnUse`` one keeps its field and pads.
    A background's stroke is not extended — at full bleed iOS's mask is the edge.
    """
    resolve(svg_text)
    return _derive(svg_text, replace=True)


def mark_only(svg_text: str) -> str:
    """The master without its declared background: everything it draws on top."""
    resolve(svg_text)
    return _derive(svg_text, replace=False)


#: Elements that draw; the proof switches their painting off, never removes them.
_RENDERED = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text",
             "image", "use", "g", "switch", "foreignObject", "a", "svg"}
#: The layer proof, made on exactly what ships: the master reduced to the
#: 1024 px rung, rendered at 1024 px in both schemes (Z01, AA04). Renders must
#: agree up to rounding: no pixel's channel may move by more than PROOF_DELTA
#: (Z02). Every declared master in the repository agrees within 2 levels, on
#: Windows and Linux alike; a dependency moves pixels by 8 levels (an opacity
#: change of 1/32) and up.
PROOF_DELTA = 4
#: Inline and important: no stylesheet rule can switch the painting back on.
_INVISIBLE = "opacity:0 !important"


def _painting_only(svg_text: str, *, card: bool) -> str:
    """The master's document unchanged, painting only the card (``card=True``)
    or everything but the card.

    Nothing is removed or moved -- sibling positions, ancestors, inherited
    paint and every definition stay where the master has them (AA01, AA03);
    only painting is switched off, with an inline important opacity.
    """
    root = _parse(svg_text)
    for child in root:
        if _local(child.tag) in _RENDERED and (child.get("id") == BACKGROUND_ID) != card:
            # Replaced, not appended to: an element that paints nothing needs no
            # other declaration, and an unclosed comment in the old value could
            # swallow an appended one (AB04).
            child.set("style", _INVISIBLE)
    return ET.tostring(root, encoding="unicode")


def _worst_change(a: bytes, b: bytes | Image.Image) -> tuple[int, int]:
    """(largest channel difference, pixels beyond PROOF_DELTA) between two renders."""
    difference = ImageChops.difference(_rgba(a), b if isinstance(b, Image.Image) else _rgba(b))
    worst = max(high for _, high in difference.getextrema())
    if worst <= PROOF_DELTA:
        return worst, 0
    bands = [band.point(lambda v: 255 if v > PROOF_DELTA else 0) for band in difference.split()]
    changed = bands[0]
    for band in bands[1:]:
        changed = ImageChops.lighter(changed, band)
    return worst, changed.histogram()[255]


def prove_layers(svg_text: str, light, dark) -> None:
    """Prove, by rendering, that the mark does not depend on the background.

    What can make the mark depend on its card is open-ended -- a stylesheet,
    a CSS function that reads the document's structure (``sibling-index()``),
    a motion path along the card, blending with it -- so instead of
    enumerating syntax, the Chromium that ships the pixels checks two facts,
    in the light and the dark scheme, at 1024 px on the 1024 px rung:

    * **structure** -- the mark IconFlow ships (the card removed from the
      document) is, pixel for pixel and in alpha, the master's mark with the
      card still in the document but not painting (AA01);
    * **interaction** -- the master is its card painting alone with that mark
      composited over it: nothing blends with, or otherwise reads, the card.

    Called whenever the master's mark ships on its own -- as the dark icon or
    as the Icon Composer layer (Z03, Z06); the light icon alone never
    separates them. ``light`` and ``dark`` must render in those schemes.
    Raises :class:`LayerError`.
    """
    svg_text = ladder.reduce_svg(svg_text, ladder.rung_for_size(SIZE))
    card_alone = _painting_only(svg_text, card=True)
    mark_in_place = _painting_only(svg_text, card=False)
    shipped = mark_only(svg_text)
    for renderer, scheme in ((light, "light"), (dark, "dark")):
        reference = renderer.render(mark_in_place, SIZE)
        worst, changed = _worst_change(renderer.render(shipped, SIZE), reference)
        if not changed:
            layered = _rgba(renderer.render(card_alone, SIZE))
            layered.alpha_composite(_rgba(reference))
            worst, changed = _worst_change(renderer.render(svg_text, SIZE), layered)
        if changed:
            raise LayerError(
                f"the mark depends on the background: drawn without it ({scheme} scheme) "
                f"{changed} pixels change by up to {worst} levels -- blending with the card, "
                "a stylesheet or a CSS function that reads the document can do this. Ship "
                'the light icon alone (build.ios_variants = "system"), or remove '
                'id="iconflow-background" and link build.ios_dark_svg')


def composer_svg(svg_text: str) -> str:
    """The transparent full-canvas foreground Icon Composer imports.

    Reduced to the rung the 1024 px icon renders (no ``data-lod`` left to
    interpret), LF line ends, one trailing newline.
    """
    text = ladder.reduce_svg(mark_only(svg_text), ladder.rung_for_size(SIZE))
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def appearances(variants: str, *, declared: bool, linked: bool) -> tuple[str, ...]:
    """The appearances a build ships for this policy and these sources."""
    if variants not in VARIANTS:
        raise ValueError("ios_variants must be 'auto' or 'system'")
    if variants == "auto" and (declared or linked):
        return APPEARANCES
    return ("light",)


# ------------------------------------------------------------------ encoding

def _encode(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def _rgba(png: bytes) -> Image.Image:
    with Image.open(io.BytesIO(png)) as image:
        return image.convert("RGBA")


def light_png(render: bytes, bg_color: str) -> bytes:
    """Composite over an opaque ground, then drop the (now opaque) alpha."""
    image = _rgba(render)
    ground = Image.new("RGBA", image.size, assemble.opaque_color(bg_color, "background color"))
    return _encode(Image.alpha_composite(ground, image).convert("RGB"))


def dark_png(render: bytes) -> bytes:
    return _encode(_rgba(render))


def tinted_png(dark: bytes) -> bytes:
    """One composite over black, then luminance (Pillow's ITU-R 601 ``L``).

    Fully transparent pixels become black whatever RGB they carry; no
    per-image normalisation, so the mapping is the same for every icon.
    """
    image = _rgba(dark)
    black = Image.new("RGBA", image.size, (0, 0, 0, 255))
    return _encode(Image.alpha_composite(black, image).convert("L"))


def contents_json(shipped: tuple[str, ...]) -> bytes:
    images = []
    for appearance in shipped:
        entry: dict = {"filename": APPEARANCE_FILES[appearance].rsplit("/", 1)[1],
                       "idiom": "universal", "platform": "ios", "size": f"{SIZE}x{SIZE}"}
        if appearance != "light":
            entry["appearances"] = [{"appearance": "luminosity", "value": appearance}]
        images.append(entry)
    document = {"images": images, "info": {"author": "iconflow", "version": 1}}
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def readme(shipped: tuple[str, ...], *, fill: str | None, composer: bool) -> bytes:
    """Installation notes generated from the files this build actually wrote."""
    variants = ", ".join(shipped)
    lines = [
        "# iOS / iPadOS app icon (generated by IconFlow — do not edit by hand)",
        "",
        f"`AppIcon.appiconset` holds the 1024 px icon for these appearances: {variants}.",
    ]
    if shipped == ("light",):
        lines += ["iOS draws its own dark and tinted versions of it."]
    lines += [
        "",
        "- **Xcode**: replace `Assets.xcassets/AppIcon.appiconset` with this folder.",
        "- **Expo** (SDK 52+): copy the folder into your project and point `ios.icon` at "
        "its PNGs: " + ", ".join(
            f'`"{a}": "./ios/AppIcon.appiconset/{APPEARANCE_FILES[a].rsplit("/", 1)[1]}"`'
            for a in shipped) + ".",
        "- **Capacitor**: replace `ios/App/App/Assets.xcassets/AppIcon.appiconset`.",
        "- **Flutter**: replace `ios/Runner/Assets.xcassets/AppIcon.appiconset`.",
    ]
    if composer:
        lines += [
            "",
            "## Icon Composer (Xcode 26 and later)",
            "",
            "`icon-composer/mark.svg` is the master's mark on a transparent, full-size",
            "canvas: the foreground layer Icon Composer imports. It is a starting point,",
            "not a finished `.icon` document — glass, translucency and the mono annotation",
            "are design decisions made in Icon Composer. Set the background there to",
            f"`{fill}`" + (" (recreate the gradient it names in `master.svg`)."
                           if fill and fill.startswith("url(") else "."),
            "Shapes the master paints in its background colour stay painted: they are",
            "not holes in the layer.",
        ]
    return ("\n".join(lines) + "\n").encode("utf-8")


# ------------------------------------------------------------------- build

@dataclass(frozen=True)
class Plan:
    """What one build ships: derived once from the policy and the sources."""

    shipped: tuple[str, ...]
    declared: bool
    linked: bool
    fill: str | None
    hint: str


def plan_for(master_text: str, *, variants: str, linked: bool) -> Plan:
    layers = resolve(master_text)
    shipped = appearances(variants, declared=layers.declared, linked=linked)
    return Plan(shipped, layers.declared, linked, layers.fill, layers.hint)


def texts(plan: Plan, master_text: str) -> dict[str, bytes]:
    """The iOS text files a build writes for this plan: one definition for
    the build and for every check of a plan made elsewhere (R03, R04)."""
    composer = plan.declared and plan.shipped != ("light",)
    out = {CONTENTS: contents_json(plan.shipped)}
    if composer:
        out[COMPOSER_MARK] = composer_svg(master_text).encode("utf-8")
    out[README] = readme(plan.shipped, fill=plan.fill, composer=composer)
    return out


def files(light_cache, dark_cache, plan: Plan, *, master_text: str,
          bg_color: str) -> dict[str, bytes]:
    """Every iOS file, by relative path, in the order a build writes them.

    ``light_cache`` renders the light composition (the full-bleed derivation,
    or the master itself without a declared layer); ``dark_cache`` the dark
    source (the master's mark, or the linked ``ios_dark_svg``) in the dark
    scheme. Only the 1024 px rung is rendered.
    """
    text = texts(plan, master_text)
    out = {CONTENTS: text[CONTENTS], LIGHT: light_png(light_cache.png(SIZE), bg_color)}
    if "dark" in plan.shipped:
        out[DARK] = dark_png(dark_cache.png(SIZE))
        out[TINTED] = tinted_png(out[DARK])
    out.update({path: data for path, data in text.items() if path != CONTENTS})
    validate_files(out, plan.shipped)
    return out


# ---------------------------------------------------------------- validation

#: (bit depth, colour type) of each appearance's IHDR, and whether a tRNS
#: chunk may appear: Pillow decodes 2- and 4-bit grey as ``L``, so the mode
#: alone does not prove the encoding (R08).
_ENCODING = {"light": (8, 2, False), "dark": (8, 6, False), "tinted": (8, 0, False)}
_ENCODING_NAME = {2: "8-bit RGB", 6: "8-bit RGBA", 0: "8-bit grayscale"}


def _header(payload: bytes) -> tuple[int, int, set[bytes]]:
    """(bit depth, colour type, chunk types) read from the PNG bytes themselves.

    The stream must be well formed: one 13-byte IHDR, first; every chunk
    inside the file; IEND last. A second IHDR would let a decoder disagree
    with this reader about the encoding (V06).
    """
    if len(payload) < 33 or payload[8:16] != b"\x00\x00\x00\rIHDR":
        raise ValueError("the PNG does not start with one 13-byte IHDR chunk")
    chunks: list[bytes] = []
    offset = 8
    while True:
        if offset + 12 > len(payload):
            raise ValueError("the PNG ends inside a chunk (no IEND)")
        length = int.from_bytes(payload[offset:offset + 4], "big")
        kind = payload[offset + 4:offset + 8]
        offset += 12 + length
        if offset > len(payload):
            raise ValueError(f"the PNG's {kind!r} chunk runs past the end of the file")
        chunks.append(kind)
        if kind == b"IEND":
            break
    if chunks.count(b"IHDR") != 1:
        raise ValueError("the PNG carries more than one IHDR chunk")
    if offset != len(payload):
        raise ValueError("the PNG has bytes after IEND")
    return payload[24], payload[25], set(chunks)


def _png(path: str, payload: bytes | None, appearance: str | None = None) -> Image.Image:
    if payload is None:
        raise ValueError(f"{path} is missing")
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    if appearance is not None:
        try:
            depth, colour, chunks = _header(payload)
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
        want_depth, want_colour, _ = _ENCODING[appearance]
        if (depth, colour) != (want_depth, want_colour):
            raise ValueError(f"{path} must be encoded {_ENCODING_NAME[want_colour]} "
                             f"(bit depth {depth}, colour type {colour} found)")
        if b"tRNS" in chunks or b"acTL" in chunks:
            raise ValueError(f"{path} must carry no transparency chunk and no animation")
    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(f"{path} cannot be decoded: {exc}") from exc
    if image.size != (SIZE, SIZE):
        raise ValueError(f"{path} must be {SIZE}x{SIZE}, not {image.size[0]}x{image.size[1]}")
    if getattr(image, "is_animated", False):
        raise ValueError(f"{path} must not be animated")
    return image


def validate_files(files: Mapping[str, bytes], shipped: tuple[str, ...]) -> None:
    """Apple's appearance encodings and the catalog, checked on the bytes.

    Light: RGB without transparency. Dark: RGBA that is transparent somewhere.
    Tinted: 8-bit grayscale without transparency. ``Contents.json`` must list
    exactly ``shipped``, each with its own file, and nothing else may be
    present. Raises ``ValueError`` naming the rule.
    """
    present = {path for path in files if path.startswith(IOS_DIR + "/")}
    expected = {CONTENTS} | {APPEARANCE_FILES[a] for a in shipped}
    if present != expected:
        extra, missing = sorted(present - expected), sorted(expected - present)
        raise ValueError("the iOS app icon set must hold exactly the shipped appearances"
                         + (f"; missing {', '.join(missing)}" if missing else "")
                         + (f"; unexpected {', '.join(extra)}" if extra else ""))
    if files[CONTENTS] != contents_json(shipped):
        raise ValueError(f"{CONTENTS} does not list exactly the {', '.join(shipped)} appearance(s)")
    light = _png(LIGHT, files.get(LIGHT), "light")
    if light.mode != "RGB" or "transparency" in light.info:
        raise ValueError(f"{LIGHT} must be opaque RGB (Apple rejects an app icon with alpha); "
                         f"it is {light.mode}")
    if "dark" in shipped:
        dark = _png(DARK, files.get(DARK), "dark")
        if dark.mode != "RGBA" or dark.getchannel("A").getextrema()[0] == 255:
            raise ValueError(f"{DARK} must be RGBA with a transparent background "
                             "(iOS draws the dark ground through it)")
        tinted = _png(TINTED, files.get(TINTED), "tinted")
        if tinted.mode != "L" or "transparency" in tinted.info:
            raise ValueError(f"{TINTED} must be opaque 8-bit grayscale; it is {tinted.mode}")


# -------------------------------------------------------------------- audit

def _luminance(rgb) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb[:3]
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a, b) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def counter_colour(fill: str | None) -> tuple[int, int, int] | None:
    """The declared background's solid colour, or None (a gradient has no one colour)."""
    if not fill or fill.startswith("url("):
        return None
    return assemble.opaque_color(fill, "background fill")[:3]


def measure(files: Mapping[str, bytes], shipped: tuple[str, ...], *,
            counter: tuple[int, int, int] | None = None) -> dict:
    """The probes, on the shipped 1024 px files themselves (no re-render).

    ``counter`` is the declared card colour: mark pixels painted in it are
    cuts and are left out of the legibility share (``dark_counter_share``
    records how much).
    """
    metrics: dict = {"appearances": list(shipped)}
    if "dark" not in shipped:
        return metrics
    dark = _rgba(files[DARK])
    alpha = dark.getchannel("A")
    histogram = alpha.histogram()
    opaque = sum(histogram[128:])
    metrics["dark_coverage"] = round(opaque / (SIZE * SIZE), 4)
    ground = DARK_GROUND
    cache: dict = {}
    legible = cuts = 0
    colours = dark.getcolors(SIZE * SIZE) or ()
    # Count by colour: a 1024² icon has few distinct colours, so this is exact
    # and quick. A pixel is judged as it is seen: composited onto the dark
    # ground, so a half-transparent grey is as dark as it looks (R09).
    for count, (r, g, b, a) in colours:
        if a < 128:
            continue
        key = (r, g, b, a)
        if key not in cache:
            if counter is not None and all(abs(x - y) <= COUNTER_TOLERANCE
                                           for x, y in zip(key[:3], counter)):
                cache[key] = "cut"
            else:
                seen = tuple(round((c * a + q * (255 - a)) / 255) for c, q in zip(key, ground))
                cache[key] = _contrast(seen, ground) >= DARK_CONTRAST
        if cache[key] == "cut":
            cuts += count
        elif cache[key]:
            legible += count
    metrics["tinted_merged"] = _merged(colours, opaque)
    drawn = opaque - cuts
    metrics["dark_counter_share"] = round(cuts / opaque, 4) if opaque else 0.0
    metrics["dark_legible_share"] = round(legible / drawn, 4) if drawn else 0.0
    tinted = Image.open(io.BytesIO(files[TINTED])).convert("L")
    mask = alpha.point(lambda v: 255 if v >= 128 else 0)
    metrics["tinted_mean"] = (round(ImageStat.Stat(tinted, mask).mean[0], 1)
                              if opaque else 0.0)
    return metrics


def _grey(rgb) -> int:
    r, g, b = rgb[:3]
    return round((r * 299 + g * 587 + b * 114) / 1000)


def _merged(colours, opaque: int) -> list[list[str]]:
    """Pairs of large, clearly different colours that become one grey.

    Each colour is taken as the tinted icon sees it: composited once over
    black, across the whole mark (alpha >= 128), translucent regions included (V07).
    """
    seen: dict[tuple, int] = {}
    for count, (r, g, b, a) in colours:
        if a >= 128:
            key = tuple(round(c * a / 255) for c in (r, g, b))
            seen[key] = seen.get(key, 0) + count
    large = [(count, rgb) for rgb, count in seen.items()
             if opaque and count / opaque >= MERGE_SHARE]
    large.sort(reverse=True)
    pairs = []
    for i, (_, a) in enumerate(large[:8]):
        for _, b in large[i + 1:8]:
            distance = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
            if distance >= MERGE_RGB and abs(_grey(a) - _grey(b)) < MERGE_GREY:
                pairs.append(["#%02X%02X%02X" % a, "#%02X%02X%02X" % b])
    return pairs


def findings(metrics: dict, plan: Plan) -> tuple[list[Finding], list[Finding]]:
    """(warnings, advisories) for one iOS build's measurements."""
    warnings: list[Finding] = []
    advisories: list[Finding] = []
    if "dark" in plan.shipped:
        source = "the linked ios_dark_svg" if plan.linked else "the master's mark"
        fix = ("redraw the mark lighter in ios_dark_svg" if plan.linked
               else "link build.ios_dark_svg (the mark drawn for a dark ground)")
        if metrics.get("dark_coverage", 0) < MIN_MARK_COVERAGE:
            warnings.append(Finding("ios-dark-empty", (
                f"iOS dark icon: {source} paints almost nothing once the background is "
                f"removed ({metrics.get('dark_coverage', 0):.1%} of the canvas); {fix}, "
                'or set build.ios_variants = "system" to let iOS derive it.')))
        else:
            if metrics.get("dark_legible_share", 0) < DARK_LEGIBLE_SHARE:
                warnings.append(Finding("ios-dark-contrast", (
                    f"iOS dark icon: only {metrics.get('dark_legible_share', 0):.0%} of "
                    f"{source} reaches {DARK_CONTRAST:g}:1 against the dark home screen "
                    f"(needs {DARK_LEGIBLE_SHARE:.0%}); {fix}, or set "
                    'build.ios_variants = "system".')))
            for a, b in metrics.get("tinted_merged", ()):
                advisories.append(Finding("ios-tinted-merge", (
                    f"iOS tinted icon: {a} and {b} become the same grey, so the tinted "
                    "icon cannot tell them apart; if that difference carries the mark, "
                    f"{fix}, or set build.ios_variants = \"system\".")))
            if metrics.get("tinted_mean", 0) < TINTED_MIN_MEAN:
                warnings.append(Finding("ios-tinted-faint", (
                    f"iOS tinted icon: the mark's mean luminance is "
                    f"{metrics.get('tinted_mean', 0):g}/255 (needs {TINTED_MIN_MEAN}); iOS "
                    f"tints by luminance, so a dark mark disappears; {fix}, or set "
                    'build.ios_variants = "system".')))
    elif not plan.declared and not plan.linked:
        advisories.append(Finding("ios-variants-system", (
            "iOS dark and tinted icons are left to iOS: the master declares no "
            f"background layer; {plan.hint}.")))
    else:
        advisories.append(Finding("ios-variants-system", (
            'iOS dark and tinted icons are left to iOS (build.ios_variants = "system").')))
    if not plan.declared:
        advisories.append(Finding("ios-light-flattened", (
            "iOS light icon: the master is flattened onto background_color, so any "
            "transparent corner around a card shows that colour on every iPhone; "
            'declare the card id="iconflow-background" to extend it to full bleed.')))
    return warnings, advisories


# --------------------------------------------------------------- rendering

@contextlib.contextmanager
def scheme_renderer(rasterizer, scheme: str):
    """A renderer in ``scheme`` beside ``rasterizer``, never a second driver."""
    from .session import scheme_sibling

    with scheme_sibling(rasterizer, scheme) as renderer:
        yield renderer


def dark_renderer(rasterizer):
    """A renderer in the dark scheme beside ``rasterizer``."""
    return scheme_renderer(rasterizer, "dark")


# ------------------------------------------------------------------ preview

#: Review approximations, never shipped: iOS's dark home-screen gradient and
#: one tint colour (iOS lets the person choose it).
PREVIEW_DARK_TOP = (58, 58, 60)
PREVIEW_DARK_BOTTOM = (22, 22, 24)
PREVIEW_TINT = (255, 196, 64)


def _squircle(size: int) -> Image.Image:
    """An approximation of iOS's continuous-corner mask (superellipse, n=5)."""
    scale = 4
    big = size * scale
    mask = Image.new("L", (big, big), 0)
    half = big / 2
    points = []
    steps = 720
    for step in range(steps):
        angle = 2 * math.pi * step / steps
        c, s = math.cos(angle), math.sin(angle)
        x = half + half * (abs(c) ** (2 / 5)) * (1 if c >= 0 else -1)
        y = half + half * (abs(s) ** (2 / 5)) * (1 if s >= 0 else -1)
        points.append((x, y))
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask.resize((size, size), Image.Resampling.LANCZOS)


def _dark_ground(size: int) -> Image.Image:
    ground = Image.new("RGBA", (size, size))
    top, bottom = PREVIEW_DARK_TOP, PREVIEW_DARK_BOTTOM
    for y in range(size):
        t = y / max(1, size - 1)
        ground.paste((*[round(a + (b - a) * t) for a, b in zip(top, bottom)], 255),
                     (0, y, size, y + 1))
    return ground


def previews(files: Mapping[str, bytes], shipped: tuple[str, ...], size: int = 180) -> dict:
    """Each shipped appearance as a home screen shows it, masked, at ``size``.

    Built only from the files given: an appearance left to iOS has no entry,
    and no preview is invented for it (C-F16). The artwork is composited onto
    its ground *before* masking, so a dark icon's transparency shows the dark
    ground, never white.
    """
    mask = _squircle(size)
    out: dict[str, Image.Image] = {}
    for appearance in shipped:
        art = _rgba(files[APPEARANCE_FILES[appearance]]).resize(
            (size, size), Image.Resampling.LANCZOS)
        if appearance == "light":
            tile = art
        elif appearance == "dark":
            tile = _dark_ground(size)
            tile.alpha_composite(art)
        else:
            gray = art.convert("L")
            tile = Image.merge("RGB", tuple(
                gray.point([round(v * channel / 255) for v in range(256)])
                for channel in PREVIEW_TINT)).convert("RGBA")
        masked = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        masked.paste(tile, (0, 0), mask)
        out[appearance] = masked
    return out
