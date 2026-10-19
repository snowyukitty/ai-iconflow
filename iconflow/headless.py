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
from typing import Mapping
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


def target_sheet(master_svg: str | Path, out: str | Path, *, options, plan=None,
                 rasterizer=None) -> Path:
    """Write every selected target's exact assets, in context, as one PNG.

    With a render ``plan`` every cell is cut from the plan's own files — the
    favicon frames from ``favicon.ico``, Electron's from ``build/icon.icns`` —
    so the sheet shows the bytes ``ship`` will write, not a second rendering
    of them. Without one, the bytes come from ``build.preview_assets``, the
    same transforms.
    """
    from .build import RenderCache, electron_frames, preview_assets
    from .rasterize import load_svg
    from .review import (
        _adaptive_shape_mask, _clip_to_mask, _draw_safe_zone, _renderer, android_previews,
    )

    svg = load_svg(master_svg)
    targets = set(options.targets)
    rows: list[tuple[str, list[tuple[str, Image.Image]]]] = []
    light, dark = (247, 245, 239, 255), (17, 18, 22, 255)
    # Crops sit on a neutral the background colour cannot match, so the mask's
    # edge is visible whatever background_color is.
    crop_ground = (120, 122, 128, 255)
    with _renderer(rasterizer, options.color_scheme) as r:
        cache = RenderCache(svg, r, optimize=False)

        def linked(path):
            return RenderCache(load_svg(path), r, optimize=False) if path else None

        maskable_cache = linked(options.maskable_svg)

        def shipped(compute, keys) -> dict[str, bytes]:
            """The plan's files for ``keys``; computed only when the plan lacks one (F06)."""
            if plan is not None and all(plan.get(key) is not None for key in keys):
                return {key: plan.get(key) for key in keys}
            computed = compute()
            if plan is None:
                return computed
            return {key: plan.get(key) if plan.get(key) is not None else value
                    for key, value in computed.items()}

        if targets & {"web", "pwa"}:
            favicon = {16: None, 32: None}
            if plan is not None and plan.get("favicon.ico") is not None:
                from .assemble import ico_frames

                favicon.update({size: frame for size, frame in
                                ico_frames(plan.get("favicon.ico")).items() if size in favicon})
            for size in favicon:
                if favicon[size] is None:
                    favicon[size] = cache.png(size)
            web = shipped(lambda: preview_assets(
                cache, "web", bg_color=options.background_color,
                maskable_scale=options.maskable_scale, maskable_cache=maskable_cache,
            ), ("apple-touch-icon.png", "icon-512-maskable.png"))
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
            tauri = shipped(lambda: preview_assets(cache, "tauri"),
                            ("icons/32x32.png", "icons/128x128.png"))
            rows.append(("tauri — the shipped PNGs at actual size", [
                ("32x32", _on(tauri["icons/32x32.png"], dark)),
                ("128x128", _on(tauri["icons/128x128.png"], dark)),
                ("128x128 light", _on(tauri["icons/128x128.png"], light)),
            ]))
        if "electron" in targets:
            frames = {}
            if plan is not None and plan.get("build/icon.icns") is not None:
                from .assemble import icns_frames

                frames = {size: frame for size, frame in
                          icns_frames(plan.get("build/icon.icns")).items() if size in (32, 128)}
            if set(frames) != {32, 128}:
                frames = {**electron_frames(cache, options.electron_radius, (32, 128)), **frames}
            rows.append((f"electron — radius {options.electron_radius:g}, the ICO/ICNS frames", [
                ("32", _on(frames[32], dark)), ("128", _on(frames[128], dark)),
                ("128 light", _on(frames[128], light)),
            ]))
        if "tray" in targets:
            tray = shipped(lambda: preview_assets(
                cache, "tray", tray_cache=linked(options.tray_svg),
                tray_template_mode=options.tray_template_mode,
            ), ("tray/tray@16.png", "tray/trayTemplate@2x.png"))
            rows.append((f"tray — colour and macOS template ({options.tray_template_mode}) on both bars", [
                ("colour 16 light", _on(tray["tray/tray@16.png"], light, 64)),
                ("colour 16 dark", _on(tray["tray/tray@16.png"], dark, 64)),
                ("template light", _template_on(tray["tray/trayTemplate@2x.png"], light, (0, 0, 0, 255))),
                ("template dark", _template_on(tray["tray/trayTemplate@2x.png"], dark, (255, 255, 255, 255))),
            ]))
        if "emote" in targets:
            emote = shipped(lambda: preview_assets(cache, "emote"),
                            ("emote/28.png", "emote/56.png"))
            rows.append(("emote — 28 and 56 in light and dark chat", [
                ("28 light", _on(emote["emote/28.png"], light)),
                ("28 dark", _on(emote["emote/28.png"], dark)),
                ("56 light", _on(emote["emote/56.png"], light)),
                ("56 dark", _on(emote["emote/56.png"], dark)),
            ]))
    if "android" in targets:
        from .review import _plan_android

        android = android_previews(svg, options, assets=_plan_android(plan),
                                   rasterizer=rasterizer)
        rows.append(("android — circle and squircle launchers, themed (13+), legacy round", [
            (label, _on(android[key], crop_ground, 192 if key != "legacy" else None))
            for key, label in (("circle", "circle"), ("squircle", "squircle"),
                               ("themed", "themed"), ("legacy", "legacy round"))
        ]))
    if "ios" in targets:
        rows.append(_ios_row(svg, options, plan, rasterizer, crop_ground))

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


def _ios_row(svg: str, options, plan, rasterizer, ground):
    """The iOS appearances: the plan's own 1024 px files, never recomputed
    beside a plan (C-F13); an appearance left to iOS is labelled, not drawn."""
    from . import ios
    from .plan import audit_ios, ios_files
    from .rasterize import load_svg
    from .review import _renderer

    if plan is not None:
        frames = audit_ios(plan)
        shipped = tuple(frames)
        files = {ios.APPEARANCE_FILES[a]: frame.png for a, frame in frames.items()}
    else:
        dark = (load_svg(options.ios_dark_svg)
                if options.ios_dark_svg and options.ios_variants != "system" else None)
        expected = ios.plan_for(svg, variants=options.ios_variants, linked=dark is not None)
        with _renderer(rasterizer, options.color_scheme) as r:
            files = ios_files(r, expected, svg, dark, options.background_color)
        shipped = expected.shipped
    shown = ios.previews(files, shipped)
    cells = []
    for appearance in ios.APPEARANCES:
        if appearance in shown:
            cells.append((appearance, _on(_png(shown[appearance]), ground)))
        else:
            blank = Image.new("RGBA", (204, 204), ground)
            ImageDraw.Draw(blank).text((40, 92), "left to iOS", font=_font(14), fill=_TEXT)
            cells.append((f"{appearance} (system)", blank))
    return ("ios — the 1024 px light, dark and tinted files on a squircle "
            "(dark ground and tint approximate iOS)", cells)


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
        # 0.9: where each probe's pixels came from, so the receipt (which binds
        # this file) binds what was audited, not only what was shown.
        "audit_provenance": audit.provenance(),
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


def load_evidence(directory: str | Path, *, source_sha256: str, contract_sha256: str,
                  expected: dict | None = None) -> dict:
    """Read a findings file and prove it still describes the current review.

    Fails when the source or the contract moved since the evidence was
    rendered, or when any sheet it names is missing or was changed.

    ``expected`` is what the *current configuration* says the review audited
    and planned — ``{"audit": <AuditInputs.describe()>, "roles": {role:
    sha256}, "parameters": <plan parameters>}`` — so a saved plan and an audit
    record are judged against trusted settings, never against the findings'
    own description of themselves (V-R04, V-R05).
    """
    from .build import _is_link_or_reparse_point, link_in_path

    directory = Path(directory)
    path = directory / FINDINGS_FILE
    link = link_in_path(path)
    if link is not None:
        raise HeadlessError(f"evidence is read through a link or junction ({link}); "
                            "point --evidence at the real directory")
    try:
        # One read (F08): the digest the receipt records is of the bytes validated.
        raw = path.read_bytes()
        findings = json.loads(raw.decode("utf-8"))
    except FileNotFoundError as exc:
        raise HeadlessError(
            f"no {FINDINGS_FILE} in {directory}; run `iconflow review --config iconflow.toml "
            f"--evidence {directory}` first"
        ) from exc
    except (OSError, ValueError) as exc:
        raise HeadlessError(f"unreadable {path}: {exc}") from exc
    if not isinstance(findings, dict) or findings.get("schema") != FINDINGS_SCHEMA:
        raise HeadlessError(f"{path} is not a schema-{FINDINGS_SCHEMA} findings file")
    _check_shapes(findings, path)
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
    try:
        saved = _check_saved_plan(directory, findings) if "plan" in findings else None
        if saved is not None:
            _check_plan_matches(saved, findings, source_sha256, expected)
        if expected is not None and "audit" in expected:
            _check_audit_inputs(findings, expected["audit"])
        findings["_audited"] = _check_provenance(
            findings, saved, audit_inputs=(expected or {}).get("audit"))
        if expected is not None and expected.get("ios_inputs") is not None:
            _check_ios_evidence(findings, saved, expected["ios_inputs"])
    except (TypeError, AttributeError, KeyError) as exc:
        # A record of the wrong shape is malformed evidence, not a crash (R06).
        raise HeadlessError(f"{path} is malformed ({exc}); re-run `iconflow review --evidence`") from exc
    findings["_sha256"] = hashlib.sha256(raw).hexdigest()
    return findings


def _check_ios_evidence(findings: dict, saved, inputs) -> None:
    """An iOS review is scored only on its own plan, audited (0.10, R02/R03).

    Evidence from before 0.10 cannot hold an iOS target, so none of 0.9's
    allowances for older evidence apply: the saved plan and its plan-bound
    provenance are required, and the plan's iOS set must be exactly what the
    current master and settings make.
    """
    from .audit import check_ios_plan, ios_sources
    from .plan import PlanError

    if saved is None or not findings.get("_audited"):
        raise HeadlessError("an iOS review must carry its render plan and an audit on it; "
                            "re-run `iconflow review --evidence`")
    try:
        check_ios_plan(saved, inputs, *ios_sources(inputs, lambda role: None))
    except PlanError as exc:
        raise HeadlessError(f"the saved render plan's iOS app icon: {exc}") from exc


def _check_shapes(findings: dict, path: Path) -> None:
    """Every record the loader and score index into, checked for shape first (V-R06)."""
    def bad(what: str):
        return HeadlessError(f"{path} is malformed ({what}); re-run `iconflow review --evidence`")

    evidence = findings.get("evidence")
    if isinstance(evidence, dict):
        for name, entry in evidence.items():
            if (not isinstance(entry, dict) or not isinstance(entry.get("path"), str)
                    or not isinstance(entry.get("sha256"), str)):
                raise bad(f"evidence entry {name!r}")
    for key in ("warnings", "advisories"):
        items = findings.get(key)
        if isinstance(items, list):
            for item in items:
                if (not isinstance(item, dict) or not isinstance(item.get("code"), str)
                        or not isinstance(item.get("message"), str)):
                    raise bad(f"a {key[:-1]} record")


_PATH_KEYS = ("maskable_source", "tray_source", "ios_dark_source")


def _comparable(inputs: dict) -> dict:
    # Source paths are machine-local: compare which file, by name, not where.
    return {key: (Path(value).name if key in _PATH_KEYS and value else value)
            for key, value in inputs.items()}


def _check_audit_inputs(findings: dict, trusted: dict) -> None:
    """The findings' audit must have run on the inputs the configuration gives now."""
    recorded = findings.get("audit")
    if not isinstance(recorded, dict) or _comparable(recorded) != _comparable(trusted):
        raise HeadlessError("the evidence was audited under other inputs than iconflow.toml "
                            "now gives; re-run `iconflow review --evidence`")


def _check_plan_matches(saved, findings: dict, source_sha256: str,
                        expected: dict | None = None) -> None:
    """The saved plan must be rendered from this evidence's sources and settings (R05).

    The findings' own hashes are checked against the current review; this
    connects the saved plan to them, so a valid plan for another source,
    scheme, background or linked source cannot ride along.
    """
    from . import assemble
    from .plan import _thaw

    if expected is not None:
        roles, parameters = expected["roles"], expected["parameters"]
        if set(saved.inputs) != set(roles):
            raise HeadlessError("the saved render plan was made from other sources than the "
                                "configuration names: " + ", ".join(sorted(saved.inputs)))
        for role, digest in roles.items():
            record = saved.inputs[role]
            if not isinstance(record, Mapping) or record.get("sha256") != digest:
                raise HeadlessError(f"the saved render plan was rendered from another {role} "
                                    "source than this evidence; re-run `iconflow review --evidence`")
        recorded = json.loads(json.dumps(_thaw(saved.parameters)))
        if recorded != json.loads(json.dumps(parameters)):
            changed = sorted(key for key in set(recorded) | set(parameters)
                             if recorded.get(key) != parameters.get(key))
            raise HeadlessError("the saved render plan was made with other settings than "
                                "iconflow.toml has: " + ", ".join(changed))
        return
    build = findings.get("build")
    if not isinstance(build, dict):
        raise HeadlessError("the findings carry no build contract")
    for role, record in saved.inputs.items():
        expected = (source_sha256 if role == "master"
                    else build.get(f"{role}_source_sha256"))
        if not isinstance(record, Mapping) or record.get("sha256") != expected:
            raise HeadlessError(f"the saved render plan was rendered from another {role} source "
                                "than this evidence; re-run `iconflow review --evidence`")
    parameters = saved.parameters or {}
    if parameters.get("color_scheme") != build.get("color_scheme"):
        raise HeadlessError("the saved render plan was rendered in another colour scheme")
    try:
        planned = "#{:02X}{:02X}{:02X}".format(
            *assemble.opaque_color(parameters.get("background_color"), "plan background")[:3])
    except (TypeError, ValueError) as exc:
        raise HeadlessError(f"the saved render plan's background is unreadable: {exc}") from exc
    if planned != build.get("background_color"):
        raise HeadlessError("the saved render plan was composed on another background")


def _check_provenance(findings: dict, saved, *, audit_inputs: dict | None = None) -> bool:
    """Validate the audit's provenance against the saved plan; True when it measured it.

    Evidence written before 0.9 carries none: valid, and not audited on the
    plan. Provenance that is present must be well formed, name the plan saved
    beside it, and every frame it says came from the plan must be exactly the
    frame that plan holds for that probe.
    """
    from .plan import PlanError, audit_origins

    if "audit_provenance" not in findings:
        return False
    record = findings["audit_provenance"]
    if (not isinstance(record, dict) or set(record) != {"schema", "plan", "audited", "frames"}
            or record["schema"] != 1 or not isinstance(record["frames"], dict)
            or not isinstance(record["audited"], bool)):
        raise HeadlessError("the findings' audit provenance is malformed; re-run `iconflow review --evidence`")
    plan_record, frames = record["plan"], record["frames"]
    if any(not isinstance(origin, dict) or not isinstance(origin.get("from"), str)
           or origin["from"] not in {"plan", "render"} for origin in frames.values()):
        raise HeadlessError("the findings' audit provenance names a frame of unknown origin")
    if plan_record is None:
        if record["audited"] or any(origin["from"] != "render" for origin in frames.values()):
            raise HeadlessError("the findings say the audit read a plan they do not name")
        return False
    if saved is None or not isinstance(plan_record, dict):
        raise HeadlessError("the findings' audit read a render plan that is not saved beside them")
    if plan_record != {"digest": saved.digest, "artifact_digest": saved.artifact_digest,
                       "provenance_digest": saved.provenance_digest}:
        raise HeadlessError("the audit measured another render plan than the one saved "
                            "beside these sheets; re-run `iconflow review --evidence`")
    # Which probes an audit must record is decided by the trusted inputs when
    # the caller has them, never by the findings alone (V-R04).
    inputs = audit_inputs if audit_inputs is not None else findings.get("audit")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("maskable_audit"), bool):
        raise HeadlessError("the findings do not say what the audit was run on")
    maskable = inputs.get("maskable_audit") is True
    try:
        expected = audit_origins(saved, maskable=maskable,
                                 linked=maskable and inputs.get("maskable_source") is not None,
                                 ios_target="ios" in (inputs.get("targets") or ()))
    except PlanError as exc:
        raise HeadlessError(f"the saved render plan cannot back the audit: {exc}") from exc
    # Exactly the record an audit on this plan makes: no probe left out, no
    # render claimed where the plan ships the frame, no frame it does not hold.
    if frames != expected:
        differ = sorted(key for key in set(frames) | set(expected)
                        if frames.get(key) != expected.get(key))
        raise HeadlessError("the audit provenance is not the record of an audit on the saved plan ("
                            + ", ".join(differ) + "); re-run `iconflow review --evidence`")
    audited = any(origin["from"] == "plan" for origin in expected.values())
    if record["audited"] != audited:
        raise HeadlessError("the findings' audit provenance contradicts itself")
    return audited


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
    if (saved.artifact_digest != binding["artifact_digest"] or saved.digest != binding["digest"]
            or saved.provenance_digest != binding["provenance_digest"]):
        raise HeadlessError("the saved render plan is not the one these sheets were rendered from; "
                            "re-run `iconflow review --evidence`")
    return saved


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
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
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
        # Of the bytes parsed above, never the file reopened (R14).
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
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
            # 0.9: the audit in that file measured the plan's own files.
            "audited_plan": bool(findings.get("_audited")),
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
