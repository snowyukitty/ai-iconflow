# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The detail ladder — one source, three size regimes.

Every rule IconFlow has ever distilled is a *compression* rule: survive 16px,
own two pixels, one idea per icon. That is why the marks are good, and it is
also the ceiling. A 1024px store plate, a dock icon, an about-box mark are all
judged at arm's length, where the drawing that wins at 16px is simply
under-drawn — and the toolkit had no way to say "this detail exists only when
there is room for it".

The ladder says it. A group carries ``data-lod`` listing the rungs it belongs
to; anything without the attribute belongs to every rung, so every master
recorded before this existed keeps rendering byte-for-byte as before.

    <g data-lod="glyph mark plate"> the one idea      </g>
    <g data-lod="mark plate">       secondary reading </g>
    <g data-lod="plate">            material, depth   </g>

Two mechanisms carry it, and they agree by construction:

* **Rasters** are reduced *structurally* — :func:`reduce_svg` deletes the
  subtrees that do not belong to the rung before the renderer ever sees them.
  Deterministic, browser-independent, and testable without Chromium.
* **The shipped vector** carries :data:`LADDER_CSS`, whose ``@media`` rules key
  off the size the SVG is *drawn* at, so one ``favicon.svg`` shows the plate in
  a 512px preview and the glyph in a 16px tab. A renderer that ignores media
  queries falls back to the plate rung — the complete artwork, which is exactly
  IconFlow's behaviour before the ladder existed.

Adding detail must never become redrawing the logo. :func:`identity_findings`
is the gate: it renders the rungs at one comparison size and proves the smaller
rung is still *inside* the larger one, still centred where it was, and still
the same colour. See ``docs/DETAIL_LADDER.md``.
"""
from __future__ import annotations

import colorsys
import io
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .findings import Finding

# Rungs, smallest first. The names are deliberately typographic: a glyph is
# what survives at text size, a mark is the identity, a plate is the large
# impression that can afford material.
RUNGS = ("glyph", "mark", "plate")

#: Largest pixel size still rendered from the ``glyph`` rung.
GLYPH_MAX = 48
#: Largest pixel size still rendered from the ``mark`` rung.
MARK_MAX = 256

LOD_ATTR = "data-lod"
#: Marks the generated stylesheet so it can be recognised and removed again.
LADDER_MARKER = "data-iconflow"
LADDER_MARKER_VALUE = "detail-ladder"

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

# Every selector is (0,2,0) so the cascade resolves purely by source order: the
# narrowest matching band is last and therefore wins. The first rule sits
# outside any media query on purpose — a renderer that ignores media queries
# keeps the plate rung, i.e. the complete drawing.
LADDER_CSS = """/* IconFlow detail ladder - generated; see docs/DETAIL_LADDER.md */
[data-lod]:not([data-lod~="plate"]){display:none}
@media (max-width:%(mark)dpx){
[data-lod][data-lod~="mark"]{display:inline}
[data-lod]:not([data-lod~="mark"]){display:none}
}
@media (max-width:%(glyph)dpx){
[data-lod][data-lod~="glyph"]{display:inline}
[data-lod]:not([data-lod~="glyph"]){display:none}
}""" % {"mark": MARK_MAX, "glyph": GLYPH_MAX}

# Default identity thresholds. They are deliberately generous about *adding*
# and strict about *moving*: a plate rung may grow the drawing, but the mark it
# grew from has to still be there, in the same place, in the same colour.
CONTAINMENT_FLOOR = 0.98
IOU_FLOOR = 0.62
# 5% of the canvas is 0.8px at 16px: below that a shifted optical centre is
# invisible, above it the small and large icons visibly sit differently.
CENTROID_DRIFT_CEILING = 0.05
HUE_DRIFT_CEILING = 15.0
#: Every rung is rendered at this size before the invariant is measured.
COMPARE_SIZE = 256

_LOD_ATTR_RE = re.compile(r'\sdata-lod\s*=\s*(["\'])(.*?)\1', re.I | re.S)
# The marker has to be recognised as the attribute it is, not as a word: this
# document is allowed to *mention* the detail ladder in its own <title>.
_MARKER_RE = re.compile(
    r'<style[^>]*\s' + LADDER_MARKER + r'\s*=\s*(["\'])' + LADDER_MARKER_VALUE + r'\1',
    re.I,
)


class LadderError(ValueError):
    """Raised when a source's ladder annotations are not usable."""


def normalize_rung(rung: str) -> str:
    """Return a validated rung name."""
    name = str(rung).strip().lower()
    if name not in RUNGS:
        raise LadderError(f"unknown rung {rung!r}; choose from: {', '.join(RUNGS)}")
    return name


def rung_for_size(size: int) -> str:
    """Return the rung a given output pixel size is rendered from."""
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise LadderError("size must be a positive integer")
    if size <= GLYPH_MAX:
        return "glyph"
    if size <= MARK_MAX:
        return "mark"
    return "plate"


def rung_sizes(rung: str) -> str:
    """Human description of the pixel band a rung covers."""
    rung = normalize_rung(rung)
    if rung == "glyph":
        return f"<={GLYPH_MAX}px"
    if rung == "mark":
        return f"{GLYPH_MAX + 1}-{MARK_MAX}px"
    return f">={MARK_MAX + 1}px"


def parse_rungs(value: str) -> frozenset[str]:
    """Parse one ``data-lod`` attribute value into a set of rung names."""
    names = str(value).replace(",", " ").split()
    if not names:
        raise LadderError(
            f'{LOD_ATTR}="" is empty; list at least one rung: {", ".join(RUNGS)}'
        )
    unknown = sorted({n.lower() for n in names} - set(RUNGS))
    if unknown:
        raise LadderError(
            f'{LOD_ATTR}="{value}" names unknown rung(s): {", ".join(unknown)}. '
            f'Choose from: {", ".join(RUNGS)}'
        )
    return frozenset(n.lower() for n in names)


def has_ladder(svg_text: str) -> bool:
    """True when the source annotates any element with ``data-lod``."""
    return bool(_LOD_ATTR_RE.search(svg_text))


def has_media_layer(svg_text: str) -> bool:
    """True when the generated ladder stylesheet is already present."""
    return bool(_MARKER_RE.search(svg_text))


def source_rungs(svg_text: str) -> frozenset[str]:
    """Every rung named anywhere in the source (empty for a flat source)."""
    found: set[str] = set()
    for _quote, value in _LOD_ATTR_RE.findall(svg_text):
        found |= parse_rungs(value)
    return frozenset(found)


def annotation_findings(svg_text: str) -> list[Finding]:
    """Validate the ladder annotations without rendering anything."""
    try:
        rungs = source_rungs(svg_text)
    except LadderError as exc:
        return [Finding("ladder-annotation", str(exc))]
    if not rungs:
        return []
    if "glyph" not in rungs:
        return [Finding(
            "ladder-annotation",
            'No element is marked data-lod="glyph ...", so nothing is annotated as '
            "surviving to 16px. Name the one idea that must reach the glyph rung; "
            "unannotated elements reach every rung and may not be what you meant.",
        )]
    return []


def _local(tag: object) -> str:
    return str(tag).rsplit("}", 1)[-1].lower()


def _prune(parent: ET.Element, rung: str, removed: list[str]) -> None:
    for child in list(parent):
        value = child.get(LOD_ATTR)
        if value is not None:
            if rung not in parse_rungs(value):
                removed.append(_local(child.tag))
                parent.remove(child)
                continue
            del child.attrib[LOD_ATTR]
        if (
            _local(child.tag) == "style"
            and child.get(LADDER_MARKER) == LADDER_MARKER_VALUE
        ):
            parent.remove(child)
            continue
        _prune(child, rung, removed)


def reduce_svg(svg_text: str, rung: str) -> str:
    """Return `svg_text` containing only what belongs to `rung`.

    A source with no ``data-lod`` anywhere is returned unchanged, byte for
    byte — the ladder is opt-in and costs nothing to a source that ignores it.
    The result carries no ladder metadata at all: no ``data-lod`` attributes
    and no generated stylesheet, so the rung it represents is unambiguous and
    cannot be re-interpreted by a second mechanism downstream.
    """
    rung = normalize_rung(rung)
    if not has_ladder(svg_text) and not has_media_layer(svg_text):
        return svg_text
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise LadderError(f"SVG source is not well-formed XML: {exc}") from exc
    if root.get(LOD_ATTR) is not None:
        raise LadderError(
            "data-lod on the root <svg> would reduce the whole icon to nothing; "
            "annotate the groups inside it instead"
        )
    removed: list[str] = []
    _prune(root, rung, removed)
    return ET.tostring(root, encoding="unicode")


def _open_tag_end(svg_text: str) -> int:
    """Index just past the opening ``<svg ...>`` tag, quotes respected."""
    start = svg_text.find("<svg")
    if start < 0:
        raise LadderError("SVG document root must be <svg>")
    quote = ""
    for index in range(start, len(svg_text)):
        char = svg_text[index]
        if quote:
            if char == quote:
                quote = ""
        elif char in ("\"", "'"):
            quote = char
        elif char == ">":
            return index + 1
    raise LadderError("SVG root element is not closed")


def with_media_layer(svg_text: str) -> str:
    """Return `svg_text` with the ladder stylesheet inserted after ``<svg>``.

    Text surgery, not a parse-and-serialize round trip: the author's bytes are
    preserved exactly, because this result is a *shipped* file. A flat source,
    or one that already carries the layer, is returned unchanged.
    """
    if not has_ladder(svg_text) or has_media_layer(svg_text):
        return svg_text
    cut = _open_tag_end(svg_text)
    style = (
        f'\n<style {LADDER_MARKER}="{LADDER_MARKER_VALUE}">\n{LADDER_CSS}\n</style>'
    )
    return svg_text[:cut] + style + svg_text[cut:]


# --------------------------------------------------------------------------
# The same-mark invariant
# --------------------------------------------------------------------------
#
# Two masks, because an icon has two silhouettes and a ladder can break either
# one. The *footprint* is the alpha channel: the space the icon occupies. The
# *visible shape* is what a viewer actually recognises - for a transparent mark
# the two agree, but for a full-bleed card (most of the casebook) the footprint
# is only the rounded square, and just the visible shape can tell a kiln from a
# teapot. Gating on alpha alone would pass anything at all on a card.


@dataclass(frozen=True)
class RungMeasure:
    """What one rung's render is, reduced to comparable numbers."""

    rung: str
    coverage: float
    visible: float
    centroid: tuple[float, float] | None
    hue: float | None

    def as_dict(self) -> dict:
        return {
            "rung": self.rung,
            "coverage": round(self.coverage, 5),
            "visible": round(self.visible, 5),
            "centroid": (
                None if self.centroid is None
                else [round(self.centroid[0], 5), round(self.centroid[1], 5)]
            ),
            "hue": None if self.hue is None else round(self.hue, 2),
        }


def _image(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _pixels(image: Image.Image):
    """Pillow renamed ``getdata``; both spellings ship in the wild."""
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def _footprint(image: Image.Image, threshold: int = 24) -> Image.Image:
    """Binary mask of the alpha channel: the space the icon occupies."""
    return image.getchannel("A").point(lambda a: 255 if a >= threshold else 0)


#: Rungs are composited over mid grey before the figure is separated, so a
#: light mark on transparency and a dark mark on transparency both stand out.
FIGURE_GROUND = (128, 128, 128)


@dataclass(frozen=True)
class FigurePolicy:
    """How one icon family separates figure from ground.

    Derived once, from the richest rung, and then applied unchanged to every
    other rung — a threshold recomputed per rung could flip polarity between
    two renders and report a difference that is purely an artefact of the
    measurement.
    """

    threshold: int
    dark_is_figure: bool


def _luma(image: Image.Image) -> Image.Image:
    """Luminance of the render composited over mid grey."""
    flat = Image.new("RGB", image.size, FIGURE_GROUND)
    flat.paste(image.convert("RGB"), (0, 0), image.getchannel("A"))
    return flat.convert("L")


def otsu_threshold(histogram: list[int]) -> int:
    """The luminance boundary a 256-bin histogram itself implies.

    Shared by the ladder (one source, several rungs) and the shape field (many
    sources), so both split figure from ground at the same kind of boundary.
    """
    total = sum(histogram)
    if not total:
        return 128
    sum_all = sum(index * count for index, count in enumerate(histogram))
    sum_below = 0.0
    weight_below = 0.0
    best_variance = -1.0
    threshold = 128
    for index, count in enumerate(histogram):
        weight_below += count
        if weight_below == 0:
            continue
        weight_above = total - weight_below
        if weight_above == 0:
            break
        sum_below += index * count
        mean_below = sum_below / weight_below
        mean_above = (sum_all - sum_below) / weight_above
        variance = weight_below * weight_above * (mean_below - mean_above) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = index
    return threshold


def figure_policy(image: Image.Image) -> FigurePolicy:
    """Split an icon into figure and ground without knowing its palette.

    Otsu's threshold finds the luminance boundary the drawing itself implies,
    and the *minority* side is the figure. That is what makes this work across
    the whole casebook: on a transparent mark the ink is the minority, and on a
    full-bleed card the card is the majority ground while the mark punched into
    it is the minority — which is exactly the shape a person recognises, and
    the one an alpha mask cannot see.
    """
    histogram = _luma(image).histogram()
    total = sum(histogram)
    if not total:
        return FigurePolicy(128, True)
    threshold = otsu_threshold(histogram)
    dark = sum(histogram[: threshold + 1])
    return FigurePolicy(threshold, dark <= total - dark)


def figure_mask(image: Image.Image, policy: FigurePolicy) -> Image.Image:
    """The recognisable shape, as a binary mask, under one shared policy."""
    luma = _luma(image)
    if policy.dark_is_figure:
        return luma.point(lambda v: 255 if v <= policy.threshold else 0)
    return luma.point(lambda v: 255 if v > policy.threshold else 0)


def _mask_stats(mask: Image.Image) -> tuple[int, tuple[float, float] | None]:
    width, height = mask.size
    count = 0
    sum_x = 0
    sum_y = 0
    for index, value in enumerate(_pixels(mask)):
        if value:
            count += 1
            sum_x += index % width
            sum_y += index // width
    if not count:
        return 0, None
    return count, (sum_x / count / width, sum_y / count / height)


def _mean_hue(image: Image.Image, mask: Image.Image) -> float | None:
    """Saturation-weighted circular mean hue, so red does not average to grey."""
    sin_total = 0.0
    cos_total = 0.0
    weight_total = 0.0
    for (r, g, b, _a), m in zip(_pixels(image), _pixels(mask)):
        if not m:
            continue
        hue, _light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if sat < 0.08:  # grey carries no hue worth averaging
            continue
        angle = hue * 2 * math.pi
        sin_total += math.sin(angle) * sat
        cos_total += math.cos(angle) * sat
        weight_total += sat
    if weight_total <= 0:
        return None
    return (math.degrees(math.atan2(sin_total, cos_total)) + 360.0) % 360.0


def measure(rung: str, png: bytes, policy: FigurePolicy | None = None) -> RungMeasure:
    """Reduce one rung's render to the numbers the invariant compares."""
    image = _image(png)
    footprint = _footprint(image)
    figure = figure_mask(image, policy or figure_policy(image))
    ink, _ = _mask_stats(footprint)
    seen, centroid = _mask_stats(figure)
    total = image.width * image.height
    return RungMeasure(
        rung=normalize_rung(rung),
        coverage=ink / total if total else 0.0,
        visible=seen / total if total else 0.0,
        centroid=centroid,
        hue=_mean_hue(image, footprint) if ink else None,
    )


def _overlap(small: Image.Image, large: Image.Image) -> tuple[float, float]:
    """Return (containment of `small` in `large`, IoU) for two binary masks."""
    inter = 0
    union = 0
    small_count = 0
    for a, b in zip(_pixels(small), _pixels(large)):
        a = bool(a)
        b = bool(b)
        if a:
            small_count += 1
        if a and b:
            inter += 1
        if a or b:
            union += 1
    containment = inter / small_count if small_count else 1.0
    iou = inter / union if union else 1.0
    return containment, iou


def _hue_delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    delta = abs(a - b) % 360.0
    return round(min(delta, 360.0 - delta), 2)


def compare_rungs(smaller_png: bytes, larger_png: bytes, *,
                  smaller: str, larger: str,
                  policy: FigurePolicy | None = None) -> dict:
    """Measure one step of the ladder: is the smaller rung still the same mark?"""
    small_image = _image(smaller_png)
    large_image = _image(larger_png)
    if small_image.size != large_image.size:
        raise LadderError("rung renders must share one comparison size")
    policy = policy or figure_policy(large_image)
    containment, footprint_iou = _overlap(
        _footprint(small_image), _footprint(large_image)
    )
    _figure_containment, visible_iou = _overlap(
        figure_mask(small_image, policy), figure_mask(large_image, policy)
    )
    small_measure = measure(smaller, smaller_png, policy)
    large_measure = measure(larger, larger_png, policy)
    drift = None
    if small_measure.centroid and large_measure.centroid:
        drift = max(
            abs(small_measure.centroid[0] - large_measure.centroid[0]),
            abs(small_measure.centroid[1] - large_measure.centroid[1]),
        )
    return {
        "smaller": small_measure.rung,
        "larger": large_measure.rung,
        "footprint_containment": round(containment, 5),
        "footprint_iou": round(footprint_iou, 5),
        "visible_iou": round(visible_iou, 5),
        "centroid_drift": None if drift is None else round(drift, 5),
        "hue_drift": _hue_delta(small_measure.hue, large_measure.hue),
    }


def identity_findings(
    renders: dict[str, bytes],
    *,
    containment_floor: float = CONTAINMENT_FLOOR,
    iou_floor: float = IOU_FLOOR,
    centroid_ceiling: float = CENTROID_DRIFT_CEILING,
    hue_ceiling: float = HUE_DRIFT_CEILING,
) -> tuple[list[Finding], list[dict]]:
    """Prove every adjacent pair of rungs still draws the same mark.

    `renders` maps rung name to a PNG of the *reduced* source, every one at the
    same pixel size. Returns gating findings plus the measured steps, which the
    caller reports as evidence whether or not anything failed.
    """
    present = [rung for rung in RUNGS if rung in renders]
    findings: list[Finding] = []
    steps: list[dict] = []
    if not present:
        return findings, steps
    # One policy for the whole family, taken from the richest rung present.
    policy = figure_policy(_image(renders[present[-1]]))
    for rung in present:
        if measure(rung, renders[rung], policy).visible <= 0.0:
            findings.append(Finding(
                "ladder-empty-rung",
                f"The {rung!r} rung ({rung_sizes(rung)}) draws nothing visible. Every "
                "size IconFlow builds comes from some rung, so this one would ship a "
                "blank icon. Mark the elements that must survive to it.",
            ))
    for smaller, larger in zip(present, present[1:]):
        step = compare_rungs(
            renders[smaller], renders[larger],
            smaller=smaller, larger=larger, policy=policy,
        )
        steps.append(step)
        # Reduction only deletes elements, so a rung's footprint is normally a
        # clean subset of the rung above it. When it is not, a mask, clip, or
        # blend mode is making removal do something other than remove - and the
        # rungs stop being one drawing seen at two depths.
        if step["footprint_containment"] < containment_floor:
            findings.append(Finding(
                "ladder-subtraction",
                f"Only {step['footprint_containment']:.0%} of the {smaller!r} rung's "
                f"footprint lies inside {larger!r} (floor {containment_floor:.0%}). "
                "Removing a rung's elements should only ever remove ink; a mask, clip "
                "or blend mode here makes the smaller rung draw its own shape.",
            ))
        if step["footprint_iou"] < iou_floor:
            findings.append(Finding(
                "ladder-footprint",
                f"{smaller!r} and {larger!r} share only {step['footprint_iou']:.0%} of "
                f"their outer footprint (floor {iou_floor:.0%}). The ladder grows "
                "inward: every trait that defines the outer contour belongs on the "
                "glyph rung, and the rungs above it own what happens inside.",
            ))
        if step["visible_iou"] < iou_floor:
            findings.append(Finding(
                "ladder-silhouette",
                f"{smaller!r} and {larger!r} share only {step['visible_iou']:.0%} of "
                f"their visible shape (floor {iou_floor:.0%}). At that distance a "
                "viewer meets two different objects, not one identity at two sizes.",
            ))
        drift = step["centroid_drift"]
        if drift is not None and drift > centroid_ceiling:
            findings.append(Finding(
                "ladder-centroid",
                f"The optical centre moves {drift:.1%} of the canvas between "
                f"{smaller!r} and {larger!r} (ceiling {centroid_ceiling:.1%}). Detail "
                "added at one rung is pulling the mark off its own balance point.",
            ))
        hue_drift = step["hue_drift"]
        if hue_drift is not None and hue_drift > hue_ceiling:
            findings.append(Finding(
                "ladder-hue",
                f"Dominant hue shifts {hue_drift:.0f} degrees between {smaller!r} and "
                f"{larger!r} (ceiling {hue_ceiling:.0f}). The rungs must be one brand "
                "colour; a rung that carries its own palette reads as a second logo.",
            ))
    return findings, steps


class RungSource:
    """One source, served as whichever rung a requested size renders from.

    Reduction happens once per rung, not once per size, so a twenty-size build
    parses the ladder three times at most. A flat source returns itself, so
    every caller can route through this without paying for a feature it does
    not use.
    """

    __slots__ = ("svg", "_rungs")

    def __init__(self, svg_text: str):
        self.svg = svg_text
        self._rungs: dict[str, str] = {}

    def rung(self, rung: str) -> str:
        rung = normalize_rung(rung)
        if rung not in self._rungs:
            self._rungs[rung] = reduce_svg(self.svg, rung)
        return self._rungs[rung]

    def for_size(self, size: int) -> str:
        return self.rung(rung_for_size(size))

    def render(self, rasterizer, size: int, **kwargs) -> bytes:
        return rasterizer.render(self.for_size(size), size, **kwargs)


def render_rungs(svg_text: str, rasterizer, *, size: int = COMPARE_SIZE,
                 rungs: tuple[str, ...] = RUNGS,
                 bg: str = "transparent") -> dict[str, bytes]:
    """Render each rung's reduced source at one comparison size."""
    return {
        rung: rasterizer.render(reduce_svg(svg_text, rung), size, bg=bg)
        for rung in rungs
    }


def ladder_report(master_svg: str | Path, *, color_scheme: str = "light",
                  size: int = COMPARE_SIZE, **thresholds) -> dict:
    """Audit one source end to end: annotations, rung renders, the invariant."""
    from .rasterize import Rasterizer, load_svg

    svg_text = load_svg(master_svg)
    flat = not has_ladder(svg_text)
    report: dict = {
        "source": str(Path(master_svg)),
        "ladder": not flat,
        "rungs": sorted(source_rungs(svg_text), key=RUNGS.index),
        "compare_size": size,
        "steps": [],
        "measures": [],
    }
    findings = annotation_findings(svg_text)
    with Rasterizer(color_scheme=color_scheme) as rasterizer:
        renders = render_rungs(svg_text, rasterizer, size=size)
    policy = figure_policy(_image(renders[RUNGS[-1]]))
    report["measures"] = [
        measure(rung, png, policy).as_dict() for rung, png in renders.items()
    ]
    if not flat:
        invariant, steps = identity_findings(renders, **thresholds)
        findings += invariant
        report["steps"] = steps
    report["findings"] = [{"code": f.code, "message": str(f)} for f in findings]
    return report
