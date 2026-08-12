"""Small-size-first metadata for IconFlow's technique scaffolds.

Presets demonstrate an execution grammar around IconFlow's house rail. They are
not finished logos: the consuming project must replace that geometry with one
product-specific object and signature device, then complete the review gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class StyleSpec:
    """One structurally distinct preset family exposed by ``iconflow new``."""

    slug: str
    name: str
    technique: str
    best_for: str
    small_size_rule: str
    tray_strategy: str
    structural_model: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


STYLE_CATALOG = (
    StyleSpec(
        "flat-geometric",
        "Flat geometric",
        "Solid primitives, one accent, and deliberate negative space.",
        "utilities, dashboards, and precise product tools",
        "Merge tiny booleans; keep every cut at least two output pixels wide.",
        "Extract or author a mark-only silhouette.",
        "primitive-fill",
    ),
    StyleSpec(
        "gradient-glow",
        "Gradient glow",
        "A restrained same-family glow clipped inside one opaque core shape.",
        "creative, premium, and modern software",
        "The opaque core must remain identifiable with every glow removed.",
        "Use a dedicated solid tray source; never convert the full glow card.",
        "masked-luminous-core",
    ),
    StyleSpec(
        "line-mark",
        "Line mark",
        "One uniform contour with a contrast halo and one semantic accent.",
        "editorial sites, developer tools, and minimal systems",
        "Use one weight and expand it optically at 16 px; never cross strokes.",
        "The contour can become the tray source after an exact-size review.",
        "uniform-contour",
    ),
    StyleSpec(
        "mascot",
        "Soft mascot",
        "Rounded character construction, thick outline, and a warm palette.",
        "consumer products with an identity-owned character",
        "Keep at most two expression details and one identity trait at 16 px.",
        "Author a simplified face or mark-only tray source.",
        "character-silhouette",
    ),
    StyleSpec(
        "duotone-cut",
        "Duotone cut",
        "One primary mass split by a large secondary plane instead of shading.",
        "design tools, modern SaaS, and data products",
        "The primary plane must read alone; merge a secondary slice under one pixel.",
        "Use the primary plane as the monochrome source.",
        "split-plane-fill",
    ),
    StyleSpec(
        "stencil-cut",
        "Stencil cut",
        "A single plate whose bold transparent cuts carry the semantic shape.",
        "security, industrial, and print-led identities",
        "Keep holes and bridges at least two output pixels wide.",
        "The same plate can work in tray contexts after fill inversion tests.",
        "negative-space-plate",
    ),
    StyleSpec(
        "pixel-grid",
        "Pixel grid",
        "Integer-grid blocks, stepped corners, and no decorative antialiasing.",
        "games, terminal tools, and deliberately retro products",
        "Design on the 16 px grid first; preserve even/odd pixel parity.",
        "Provide a grid-snapped one-color sprite for tray output.",
        "integer-pixel-blocks",
    ),
    StyleSpec(
        "isometric",
        "Isometric",
        "Two or three explicit faces create depth without photoreal rendering.",
        "storage, 3D, infrastructure, and spatial products",
        "Drop micro-edges at 16 px and retain no more than two essential faces.",
        "Author a front-facing silhouette; color faces cannot carry tray meaning.",
        "multi-face-projection",
    ),
    StyleSpec(
        "cut-paper",
        "Cut paper",
        "Hard-edged offset layers create tactile depth without blur filters.",
        "publishing, craft, education, and friendly productivity",
        "Use only broad layers; remove any offset that resolves below one pixel.",
        "Collapse layers into a single outer silhouette for tray output.",
        "offset-paper-layers",
    ),
    StyleSpec(
        "enamel-pin",
        "Enamel pin",
        "A dark metal contour, inset color, and one bounded hard highlight.",
        "community, events, playful utilities, and collectible identities",
        "Protect the metal boundary at two pixels and omit tiny shine marks.",
        "Use the outer metal contour as the tray silhouette.",
        "outlined-inlay",
    ),
    StyleSpec(
        "blueprint",
        "Blueprint",
        "A technical contour, sparse construction guides, and explicit nodes.",
        "engineering, architecture, CAD, and system tools",
        "Keep guides subordinate and delete any line thinner than two pixels.",
        "Ship the primary contour only; construction guides are app-art detail.",
        "technical-construction",
    ),
    StyleSpec(
        "stained-glass",
        "Stained glass",
        "Large color panes separated by heavy leading inside one silhouette.",
        "creative, cultural, music, and expressive products",
        "Use three or four panes at most and keep every leading bar two pixels wide.",
        "Use the leading-and-outer silhouette as a dedicated mono source.",
        "faceted-leading",
    ),
    StyleSpec(
        "risograph",
        "Risograph",
        "Two bold spot-color plates use controlled offset and visible overprint.",
        "indie publishing, events, music, and experimental tools",
        "Keep a stable shared core; the registration offset must resolve as one pixel.",
        "Use the shared core, never the two offset color plates, for tray output.",
        "offset-ink-plates",
    ),
    StyleSpec(
        "clay",
        "Clay",
        "Chunky rounded volumes use explicit shadow and highlight shapes, not blur.",
        "friendly consumer software, learning, and creative tools",
        "Retain one shadow edge and one highlight only; the base volume must stand alone.",
        "Author a flat silhouette without highlights for tray output.",
        "rounded-explicit-volume",
    ),
    StyleSpec(
        "cel-shaded",
        "Cel shaded",
        "A decisive ink contour and one hard-edged value plane create graphic depth.",
        "games, animation, fandom, and energetic consumer products",
        "Keep one shadow plane only; the inked outer contour must name the object alone.",
        "Use the closed ink contour without the interior value plane.",
        "inked-hard-shadow",
    ),
    StyleSpec(
        "chrome",
        "Chrome",
        "A solid dark contour contains a few hard specular value bands.",
        "music, games, creator tools, and high-energy premium products",
        "Collapse the reflection to six broad value bands, each at least two output pixels wide, and preserve a solid outer contour.",
        "Use the outer contour as a one-color silhouette; reflections are app-art detail.",
        "banded-specular-volume",
    ),
    StyleSpec(
        "ink-brush",
        "Ink brush",
        "A tapered calligraphic mass uses one broad dry-brush cut for organic energy.",
        "editorial, culture, craft, wellness, and expressive creator products",
        "The filled brush mass must read without dry texture; keep only one broad cut at 16 px.",
        "Use the filled calligraphic mass and omit every dry-brush texture cut.",
        "tapered-calligraphic-mass",
    ),
    StyleSpec(
        "woodcut",
        "Woodcut",
        "A bold relief mass uses angular edges and a few broad carved ink breaks.",
        "animals, folklore, craft, culture, and story-led products",
        "The uncarved mass must identify the object; retain no more than two broad cuts at 16 px.",
        "Use the untextured relief mass and omit decorative hatch cuts.",
        "carved-relief-mass",
    ),
    StyleSpec(
        "glass-stack",
        "Glass stack",
        "Crisp translucent panes overlap around one opaque semantic skeleton.",
        "collaboration, spatial, media, and modern cross-platform products",
        "The opaque skeleton must identify the object when translucency and overlap vanish.",
        "Author the opaque skeleton as the tray source; never flatten the full glass card to alpha.",
        "crisp-alpha-overlap",
    ),
    StyleSpec(
        "woven",
        "Woven",
        "Two broad bands alternate over and under through deliberate knockout gaps.",
        "relationships, networks, exchange, communities, and connected systems",
        "Every underpass needs a full-pixel separation and every band must stay two pixels wide.",
        "Use a simplified interlocked silhouette with explicit knockout gaps.",
        "interlaced-band-topology",
    ),
)

PRESETS = tuple(style.slug for style in STYLE_CATALOG)


def _validate_catalog() -> None:
    slugs = [style.slug for style in STYLE_CATALOG]
    models = [style.structural_model for style in STYLE_CATALOG]
    if len(slugs) < 10:
        raise RuntimeError("IconFlow must expose at least ten technique families")
    if len(slugs) != len(set(slugs)):
        raise RuntimeError("IconFlow style slugs must be unique")
    if len(models) != len(set(models)):
        raise RuntimeError("IconFlow style families must be structurally distinct")


_validate_catalog()
