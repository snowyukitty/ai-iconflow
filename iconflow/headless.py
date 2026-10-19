# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Headless review: the Review Lab's evidence without a browser, same gate.

An agent session often cannot open the interactive Review Lab. Before 0.7 it
scored from the static sheet and wrote the receipt JSON by hand, which put
the binding (source hash, contract hash, which evidence was read) in the
agent's care. This module makes that path a first-class one:

1. ``iconflow review --config iconflow.toml --evidence DIR`` writes the Lab's
   evidence as deterministic PNG sheets plus ``findings.json``: the audit's
   inputs, warnings, advisories and measurements, the hashes of every sheet,
   and the six-axis checklist naming which sheet answers which axis.
2. ``iconflow score --config iconflow.toml --evidence DIR ...`` walks the six
   axes, refuses evidence that no longer matches the source or contract or
   whose sheets were changed, requires a score *and a reason* for every axis,
   and writes a receipt that records ``review_surface.interactive_lab =
   false``.

Nothing about the gate moves. ``ship`` still re-runs QA, re-checks the source
and contract hashes, and requires every axis at 4/5 or better; a headless
receipt is a receipt like any other. A *second opinion* — another reviewer's
receipt over the same evidence — can be attached; it is recorded, compared,
and reported as an advisory, and it never replaces the gate.
"""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from .casebook import AXES

FINDINGS_FILE = "findings.json"
FINDINGS_SCHEMA = 1
SURFACE_KIND = "headless-evidence"
MIN_RATIONALE = 12
#: The sheets a headless receipt cannot be scored without.
REQUIRED_EVIDENCE = frozenset({"contact_sheet", "targets"})
#: An opinion this far from the primary score on any axis is called dissent.
DISSENT_GAP = 2


@dataclass(frozen=True)
class AxisGuide:
    axis: str
    question: str
    evidence: tuple[str, ...]


#: The six axes of docs/REVIEW_CHECKLIST.md, each with the sheet that answers it.
AXIS_GUIDES = (
    AxisGuide("legibility", "At 16px (pixel zoom) is it one shape, readable at a glance? "
              "Counters open, strokes present, no grey soup.",
              ("contact-sheet.png",)),
    AxisGuide("distinctiveness", "Name the visual silhouette in one noun. A letter, a rounded "
              "square with a glyph, or a stock symbol scores 3 or less. Gate: never ship below 4.",
              ("contact-sheet.png", "contact-sheet-neighbours.png")),
    AxisGuide("balance", "Optically centred, on a keyline, with safe-area room in every crop?",
              ("contact-sheet.png", "targets.png")),
    AxisGuide("color", "Holds on white, #0b0d12 and grey; one hue and an accent; every "
              "target context still reads?",
              ("contact-sheet.png", "targets.png")),
    AxisGuide("scalability", "The same idea at 16 and 512; detail only where size allows; the "
              "ladder (if any) adds detail without changing identity.",
              ("contact-sheet.png", "contact-sheet-ladder.png")),
    AxisGuide("craft", "Clean curves, even strokes, no spikes or pips in the 128/256px "
              "silhouette strips (L54), no accidental gaps.",
              ("contact-sheet.png",)),
)


class HeadlessError(ValueError):
    """Evidence that cannot honestly back a receipt."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _font(size: int):
    from .review import _font as review_font

    return review_font(size)


# --------------------------------------------------------------------------
# The target-context sheet: the Lab's "Target contexts" panel as one PNG.
# --------------------------------------------------------------------------

_INK = (23, 24, 28, 255)
_TEXT = (245, 241, 232, 255)
_LABEL = (169, 171, 180, 255)


def _open(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _on(png: bytes, ground, size: int | None = None, pad: int = 12) -> Image.Image:
    art = _open(png)
    if size is not None and art.width != size:
        # Enlarge with NEAREST so pixels stay pixels (the zoom proof); reduce
        # with LANCZOS so a large preview is not aliased by the sheet itself.
        resample = Image.Resampling.NEAREST if size > art.width else Image.Resampling.LANCZOS
        art = art.resize((size, size), resample)
    cell = Image.new("RGBA", (art.width + 2 * pad, art.height + 2 * pad), ground)
    cell.alpha_composite(art, (pad, pad))
    return cell


def _template_on(png: bytes, ground, ink, zoom: int = 2) -> Image.Image:
    """A macOS template the way the menu bar paints it: one ink, alpha only."""
    alpha = _open(png).getchannel("A")
    alpha = alpha.resize((alpha.width * zoom, alpha.height * zoom), Image.Resampling.NEAREST)
    cell = Image.new("RGBA", (alpha.width + 24, alpha.height + 24), ground)
    paint = Image.new("RGBA", alpha.size, ink)
    cell.paste(paint, (12, 12), alpha)
    return cell


def target_sheet(master_svg: str | Path, out: str | Path, *, options, plan=None) -> Path:
    """Write every selected target's exact assets, in context, as one PNG.

    With a render ``plan`` every cell is cut from the plan's own files — the
    favicon frames from ``favicon.ico``, Electron's from ``build/icon.icns`` —
    so the sheet shows the bytes ``ship`` will write, not a second rendering
    of them. Without one, the bytes come from ``build.preview_assets``, the
    same transforms.
    """
    from .build import RenderCache, electron_frames, preview_assets
    from .rasterize import Rasterizer, load_svg
    from .review import (
        _adaptive_shape_mask, _clip_to_mask, _draw_safe_zone, android_previews,
    )

    svg = load_svg(master_svg)
    targets = set(options.targets)
    rows: list[tuple[str, list[tuple[str, Image.Image]]]] = []
    light, dark = (247, 245, 239, 255), (17, 18, 22, 255)
    # Crops sit on a neutral the background colour cannot match, so the mask's
    # edge is visible whatever background_color is.
    crop_ground = (120, 122, 128, 255)
    with Rasterizer(color_scheme=options.color_scheme) as r:
        cache = RenderCache(svg, r, optimize=False)

        def linked(path):
            return RenderCache(load_svg(path), r, optimize=False) if path else None

        maskable_cache = linked(options.maskable_svg)

        def shipped(computed: dict[str, bytes]) -> dict[str, bytes]:
            if plan is None:
                return computed
            return {key: plan.get(key) if plan.get(key) is not None else value
                    for key, value in computed.items()}

        favicon = {16: None, 32: None}
        if plan is not None and plan.get("favicon.ico") is not None:
            from .assemble import ico_frames

            favicon.update({size: frame for size, frame in ico_frames(plan.get("favicon.ico")).items()
                            if size in favicon})
        for size in favicon:
            if favicon[size] is None:
                favicon[size] = cache.png(size)
        if targets & {"web", "pwa"}:
            web = shipped(preview_assets(
                cache, "web", bg_color=options.background_color,
                maskable_scale=options.maskable_scale, maskable_cache=maskable_cache,
            ))
            maskable = _open(web["icon-512-maskable.png"])
            small = maskable.resize((192, 192), Image.Resampling.LANCZOS)
            rows.append(("web / pwa — favicon 16 and 32 on light and dark tabs, apple-touch 180", [
                ("16 light", _on(favicon[16], light, 64)),
                ("16 dark", _on(favicon[16], dark, 64)),
                ("32 light", _on(favicon[32], light, 64)),
                ("32 dark", _on(favicon[32], dark, 64)),
                ("apple-touch 180", _on(web["apple-touch-icon.png"], light)),
            ]))
            rows.append(("maskable — the exact icon-512-maskable.png, safe circle and crops", [
                ("safe zone", _on(_png(_draw_safe_zone(maskable).resize((192, 192))), light, pad=6)),
                ("circle", _on(_png(_clip_to_mask(small, _adaptive_shape_mask(192, "circle"))), crop_ground, pad=6)),
                ("squircle", _on(_png(_clip_to_mask(small, _adaptive_shape_mask(192, "squircle"))), crop_ground, pad=6)),
                ("rounded", _on(_png(_clip_to_mask(small, _adaptive_shape_mask(192, "rounded"))), crop_ground, pad=6)),
            ]))
        if "tauri" in targets:
            tauri = shipped(preview_assets(cache, "tauri"))
            rows.append(("tauri — the shipped PNGs at actual size", [
                ("32x32", _on(tauri["icons/32x32.png"], dark)),
                ("128x128", _on(tauri["icons/128x128.png"], dark)),
                ("128x128 light", _on(tauri["icons/128x128.png"], light)),
            ]))
        if "electron" in targets:
            frames = electron_frames(cache, options.electron_radius, (32, 128))
            if plan is not None and plan.get("build/icon.icns") is not None:
                from .assemble import icns_frames

                frames = {**frames, **{size: frame for size, frame in
                                       icns_frames(plan.get("build/icon.icns")).items()
                                       if size in frames}}
            rows.append((f"electron — radius {options.electron_radius:g}, the ICO/ICNS frames", [
                ("32", _on(frames[32], dark)), ("128", _on(frames[128], dark)),
                ("128 light", _on(frames[128], light)),
            ]))
        if "tray" in targets:
            tray = shipped(preview_assets(
                cache, "tray", tray_cache=linked(options.tray_svg),
                tray_template_mode=options.tray_template_mode,
            ))
            rows.append((f"tray — colour and macOS template ({options.tray_template_mode}) on both bars", [
                ("colour 16 light", _on(tray["tray/tray@16.png"], light, 64)),
                ("colour 16 dark", _on(tray["tray/tray@16.png"], dark, 64)),
                ("template light", _template_on(tray["tray/trayTemplate@2x.png"], light, (0, 0, 0, 255))),
                ("template dark", _template_on(tray["tray/trayTemplate@2x.png"], dark, (255, 255, 255, 255))),
            ]))
        if "emote" in targets:
            emote = shipped(preview_assets(cache, "emote"))
            rows.append(("emote — 28 and 56 in light and dark chat", [
                ("28 light", _on(emote["emote/28.png"], light)),
                ("28 dark", _on(emote["emote/28.png"], dark)),
                ("56 light", _on(emote["emote/56.png"], light)),
                ("56 dark", _on(emote["emote/56.png"], dark)),
            ]))
    if "android" in targets:
        from .review import _plan_android

        android = android_previews(svg, options, assets=_plan_android(plan))
        rows.append(("android — circle and squircle launchers, themed (13+), legacy round", [
            (label, _on(android[key], crop_ground, 192 if key != "legacy" else None))
            for key, label in (("circle", "circle"), ("squircle", "squircle"),
                               ("themed", "themed"), ("legacy", "legacy round"))
        ]))

    heading, small_font = _font(18), _font(13)
    width = 40 + max(
        [sum(cell.width + 24 for _label, cell in cells) for _title, cells in rows] or [480]
    )
    height = 60 + sum(28 + max(cell.height for _l, cell in cells) + 30 for _t, cells in rows)
    sheet = Image.new("RGBA", (max(width, 640), max(height, 120)), _INK)
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 14), "IconFlow target contexts — the exact bytes ship writes", font=heading, fill=_TEXT)
    y = 52
    if not rows:
        draw.text((20, y), "No targets selected.", font=small_font, fill=_LABEL)
    for title, cells in rows:
        draw.text((20, y), title, font=small_font, fill=_TEXT)
        y += 24
        x = 20
        tallest = max(cell.height for _l, cell in cells)
        for label, cell in cells:
            sheet.alpha_composite(cell, (x, y))
            draw.text((x, y + cell.height + 4), label, font=small_font, fill=_LABEL)
            x += cell.width + 24
        y += tallest + 34
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)
    return out


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


# --------------------------------------------------------------------------
# The evidence bundle
# --------------------------------------------------------------------------


def write_findings(directory: Path, *, seed: dict, audit, sheets: dict[str, Path],
                   toolchain: dict, plan_dir: Path | None = None) -> Path:
    """Write ``findings.json``: what was measured, under which inputs, in which files."""
    from .qa import warning_code

    def finding(item) -> dict:
        return {"code": warning_code(item), "message": str(item)}

    missing = sorted(name for name in REQUIRED_EVIDENCE
                     if sheets.get(name) is None or not Path(sheets[name]).is_file())
    if missing:
        raise HeadlessError("evidence was not rendered: " + ", ".join(missing))
    files = {
        name: {"path": path.name, "sha256": _sha256(path)}
        for name, path in sorted(sheets.items()) if path is not None and path.is_file()
    }
    payload = {
        "schema": FINDINGS_SCHEMA,
        "kind": SURFACE_KIND,
        "interactive_lab": False,
        "project": seed["project"],
        "source": seed["source"],
        "source_sha256": seed["source_sha256"],
        "contract_sha256": seed["contract_sha256"],
        "targets": seed["targets"],
        "build": seed["build"],
        "audit": audit.inputs.describe(),
        "warnings": [finding(item) for item in audit.warnings],
        "advisories": [finding(item) for item in audit.advisories],
        "metrics": audit.metrics,
        "evidence": files,
        "axes": [
            {"axis": guide.axis, "question": guide.question,
             "read": [name for name in guide.evidence
                      if name in {entry["path"] for entry in files.values()}]}
            for guide in AXIS_GUIDES
        ],
        "toolchain": toolchain,
        # 0.8: the render plan these sheets show, saved beside them for
        # `ship --plan`. `score` inherits it; it never renders a new one.
        **({"plan": seed["plan"], "plan_dir": plan_dir.name}
           if seed.get("plan") is not None and plan_dir is not None else {}),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    path = directory / FINDINGS_FILE
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_evidence(directory: str | Path, *, source_sha256: str, contract_sha256: str) -> dict:
    """Read a findings file and prove it still describes the current review.

    Fails when the source or the contract moved since the evidence was
    rendered, or when any sheet it names is missing or was changed.
    """
    from .build import _is_link_or_reparse_point, link_in_path

    directory = Path(directory)
    path = directory / FINDINGS_FILE
    link = link_in_path(path)
    if link is not None:
        raise HeadlessError(f"evidence is read through a link or junction ({link}); "
                            "point --evidence at the real directory")
    try:
        findings = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HeadlessError(
            f"no {FINDINGS_FILE} in {directory}; run `iconflow review --config iconflow.toml "
            f"--evidence {directory}` first"
        ) from exc
    except (OSError, ValueError) as exc:
        raise HeadlessError(f"unreadable {path}: {exc}") from exc
    if not isinstance(findings, dict) or findings.get("schema") != FINDINGS_SCHEMA:
        raise HeadlessError(f"{path} is not a schema-{FINDINGS_SCHEMA} findings file")
    evidence = findings.get("evidence")
    if not isinstance(evidence, dict) or not REQUIRED_EVIDENCE <= set(evidence):
        raise HeadlessError(
            f"{path} does not name the required evidence ({', '.join(sorted(REQUIRED_EVIDENCE))}); "
            "re-run `iconflow review --evidence`"
        )
    for key in ("warnings", "advisories"):
        if not isinstance(findings.get(key), list):
            raise HeadlessError(f"{path} has no {key} list; re-run `iconflow review --evidence`")
    if findings.get("source_sha256") != source_sha256:
        raise HeadlessError(
            "the evidence is stale: it was rendered from a different master SVG; "
            "re-run `iconflow review --evidence` before scoring"
        )
    if findings.get("contract_sha256") != contract_sha256:
        raise HeadlessError(
            "the evidence is stale: targets, colours, transforms or linked sources changed "
            "since it was rendered; re-run `iconflow review --evidence` before scoring"
        )
    for name, entry in (findings.get("evidence") or {}).items():
        relative = str(entry.get("path", ""))
        # Evidence lives in the evidence directory itself; a findings file that
        # names anything else was not written by `review --evidence`.
        if not relative or Path(relative).name != relative:
            raise HeadlessError(f"evidence entry {name} names a path outside {directory}")
        sheet = directory / relative
        if _is_link_or_reparse_point(sheet):
            raise HeadlessError(f"evidence sheet {relative} is a link, not a rendered file")
        if not sheet.is_file():
            raise HeadlessError(f"evidence sheet {sheet.name} ({name}) is missing")
        if _sha256(sheet) != entry["sha256"]:
            raise HeadlessError(
                f"evidence sheet {sheet.name} ({name}) changed after it was rendered; "
                "re-run `iconflow review --evidence`"
            )
    if findings.get("plan") is not None:
        _check_saved_plan(directory, findings)
    findings["_sha256"] = _sha256(path)
    return findings


def _check_saved_plan(directory: Path, findings: dict) -> None:
    """The plan the findings name must be the plan saved beside them."""
    from .plan import PlanError, load_plan, validate_binding

    name = str(findings.get("plan_dir", ""))
    if not name or Path(name).name != name:
        raise HeadlessError("the findings name a plan outside the evidence directory")
    try:
        binding = validate_binding(findings["plan"])
        saved = load_plan(directory / name)
    except PlanError as exc:
        raise HeadlessError(f"the saved render plan cannot back this review: {exc}") from exc
    if saved.artifact_digest != binding["artifact_digest"] or saved.digest != binding["digest"]:
        raise HeadlessError("the saved render plan is not the one these sheets were rendered from; "
                            "re-run `iconflow review --evidence`")


def evidence_paths(directory: Path, findings: dict) -> dict[str, Path]:
    return {name: directory / entry["path"] for name, entry in findings.get("evidence", {}).items()}


def axis_walk(findings: dict, directory: Path) -> list[str]:
    """Human lines walking the six axes, each with the sheets that answer it."""
    names = {entry["path"] for entry in findings.get("evidence", {}).values()}
    lines = []
    for index, guide in enumerate(AXIS_GUIDES, 1):
        sheets = [directory / name for name in guide.evidence if name in names]
        lines.append(f"{index}. {guide.axis}: {guide.question}")
        for sheet in sheets:
            lines.append(f"     read {sheet}")
    return lines


def validate_rationale(rationale: dict[str, str], scores: dict[str, int]) -> None:
    """Every scored axis needs a reason a later reader can check."""
    missing = [axis for axis in AXES if len((rationale.get(axis) or "").strip()) < MIN_RATIONALE]
    if missing:
        raise HeadlessError(
            "a headless review needs a reason for every axis (at least "
            f"{MIN_RATIONALE} characters): add --rationale for " + ", ".join(missing)
        )
    unknown = sorted(set(rationale) - set(AXES))
    if unknown:
        raise HeadlessError("unknown rationale axis: " + ", ".join(unknown))
    del scores


def compare_opinion(primary: dict[str, int], opinion: dict[str, int]) -> list[str]:
    """Where an independent reviewer disagrees enough to say so."""
    notes = []
    if not isinstance(opinion, dict):
        return ["a second opinion has no scores object; it was ignored"]
    for axis in AXES:
        mine, theirs = primary.get(axis), opinion.get(axis)
        if isinstance(theirs, bool) or not isinstance(theirs, int) or not isinstance(mine, int):
            continue
        if theirs < 4 <= mine:
            notes.append(f"{axis}: second opinion {theirs} is below the floor (primary {mine})")
        elif abs(mine - theirs) >= DISSENT_GAP:
            notes.append(f"{axis}: second opinion {theirs} differs from primary {mine}")
    return notes


def load_opinion(path: str | Path, *, source_sha256: str, contract_sha256: str,
                 primary_reviewer: dict | None, plan_digest: str | None = None) -> dict:
    """Load another reviewer's receipt over the same source and contract.

    When both reviews are plan-bound they must have looked at the same
    pixels; an opinion without a plan is kept and marked ``same_plan: None``.
    """
    from .casebook import validate_scores

    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HeadlessError(f"unreadable second opinion {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HeadlessError(f"second opinion {path} is not a JSON object")
    if value.get("source_sha256") != source_sha256 or value.get("contract_sha256") != contract_sha256:
        raise HeadlessError(
            f"second opinion {path.name} scored a different source or contract; "
            "an opinion only counts over the same evidence"
        )
    opinion_plan = value.get("plan") if isinstance(value.get("plan"), dict) else None
    same_plan = None
    if plan_digest is not None and opinion_plan is not None:
        same_plan = opinion_plan.get("digest") == plan_digest
        if not same_plan:
            raise HeadlessError(
                f"second opinion {path.name} scored different pixels (another render plan); "
                "an opinion only counts over the same evidence"
            )
    scores = value.get("scores")
    if not isinstance(scores, dict):
        raise HeadlessError(f"second opinion {path.name} has no scores")
    try:
        validate_scores(scores)
    except ValueError as exc:
        raise HeadlessError(f"second opinion {path.name}: {exc}") from exc
    reviewer = value.get("reviewer") if isinstance(value.get("reviewer"), dict) else {}
    if not reviewer.get("name"):
        raise HeadlessError(f"second opinion {path.name} must name its reviewer")
    if primary_reviewer and reviewer.get("name") == primary_reviewer.get("name"):
        raise HeadlessError(
            "a second opinion must come from a different reviewer than the primary review"
        )
    return {
        "reviewer": reviewer,
        "scores": {axis: scores[axis] for axis in AXES if axis in scores},
        "notes": str(value.get("notes", ""))[:2000],
        "receipt_sha256": _sha256(path),
        "same_plan": same_plan,
    }


def build_receipt(*, seed: dict, scores: dict[str, int], notes: str,
                  rationale: dict[str, str], reviewer: dict, findings: dict,
                  toolchain: dict, opinions: list[dict]) -> dict:
    """The receipt ``ship --review`` accepts, with the headless surface recorded."""
    passing = all(scores.get(axis, 0) >= 4 for axis in AXES) and not findings.get("warnings")
    receipt = dict(seed)
    receipt.update({
        "scores": {axis: scores[axis] for axis in AXES},
        "notes": notes,
        "status": "ready" if passing else "blocked",
        "rationale": {axis: rationale[axis].strip() for axis in AXES},
        "reviewer": reviewer,
        "toolchain": toolchain,
        "artifacts": {
            f"{name}_sha256": entry["sha256"]
            for name, entry in sorted(findings.get("evidence", {}).items())
        },
        "review_surface": {
            "kind": SURFACE_KIND,
            "interactive_lab": False,
            "findings_sha256": findings["_sha256"],
            "note": "Scored from IconFlow's deterministic evidence sheets; the "
                    "interactive Review Lab was not opened.",
        },
    })
    if opinions:
        receipt["second_opinions"] = [
            {**opinion, "dissent": compare_opinion(scores, opinion["scores"])}
            for opinion in opinions
        ]
    return receipt
