# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Command-line interface.

    python -m iconflow build  master.svg --out ./out --targets web,tauri,tray
    python -m iconflow review --config iconflow.toml --html review.html
    python -m iconflow check  master.svg
    python -m iconflow ladder master.svg --sheet work/app/ladder.png
    python -m iconflow render master.svg --sizes 256,64 --out icon.png
    python -m iconflow new    gradient-glow --out master.svg
    python -m iconflow init   --essence flow --targets web,electron,tray
    python -m iconflow ship   --config iconflow.toml --review master-review.json
    python -m iconflow doctor
    python -m iconflow shortcut --target app.vbs --icon build/icon.ico --name "My App"
    python -m iconflow shortcut --powershell-script launch.ps1 --icon build/icon.ico --name "My App"
    python -m iconflow case new --slug my-app --essence save --device "letterform fusion" ...
    python -m iconflow case stats
    python -m iconflow setup
    python -m iconflow demo   --out ./iconflow-demo [--json]
    python -m iconflow docs   DESIGN_PLAYBOOK
    python -m iconflow skill  install

``doctor``, ``check``, ``review``, ``ship``, ``ladder``, and ``demo`` accept
``--json`` and
then follow docs/AGENT_CONTRACT.md: stdout carries exactly one envelope, human
lines go to stderr, and the exit code is 0 (ok), 1 (blocked by an IconFlow
gate), or 2 (usage, configuration, or runtime failure).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.resources
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import agentkit
from . import ladder as _LADDER
from .styles import PRESETS, STYLE_CATALOG

# Commands whose result is a machine-readable Report (docs/AGENT_CONTRACT.md).
JSON_COMMANDS = frozenset({"doctor", "check", "review", "ship", "demo", "ladder"})
DEMO_FILES = ("master.svg", "tray.svg", "iconflow.toml", "master-review.json")
JSON_HELP = "emit one docs/AGENT_CONTRACT.md envelope on stdout; human lines go to stderr"

# `demo` is the only command that copies IconFlow's own identity into a
# directory the user chose, so the directory has to say what it is holding.
DEMO_NOTICE = """# What is in this directory

This is **IconFlow's own product mark** — the Petal Haypile family — copied here
so `iconflow demo` can prove the engine end to end against a real, source-bound
review receipt. A green run means the whole pipeline works on a design that
genuinely passed the quality gate.

**It is not a starting point for your icon.** These files are IconFlow's
finished artwork and identity — and so is everything `ship` just built from
them, including every `.ico`, `.icns`, and `.png` under `build/` and `icons/`
in this directory:

- licensed CC BY 4.0 (attribution required), and
- covered by the IconFlow trademark policy, which no copyright licence grants.

Shipping any of it as your product's identity is a trademark problem no
copyright licence solves.

## To design your own icon instead

    iconflow init --out iconflow.toml
    iconflow styles
    iconflow new <preset> --out work/<slug>/a.svg

The technique scaffolds behind `iconflow new` are CC0 public domain, and
**whatever you design from them is entirely yours** — no attribution, no
share-alike, commercial use unrestricted. Run `iconflow license` for the full
picture, or follow the complete procedure with `iconflow skill print`.
"""


@dataclass
class Report:
    """Outcome of one command in the Agent Contract v1 envelope shape.

    Commands keep printing their human lines; this object carries the same
    facts with stable codes so ``--json`` never has to parse prose.
    """

    command: str
    exit_code: int = 0
    warnings: list[dict] = field(default_factory=list)
    advisories: list[dict] = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)

    def warn(self, code: str, message: str) -> None:
        """Record a gating finding; the command is blocked (exit 1) unless it errors."""
        self.warnings.append({"code": code, "message": str(message)})
        self.exit_code = max(self.exit_code, 1)

    def advise(self, code: str, message: str) -> None:
        """Record a non-gating finding; it never changes the exit code."""
        self.advisories.append({"code": code, "message": str(message)})

    def error(self, code: str, message: str) -> None:
        """Record a usage, configuration, or runtime failure (exit 2)."""
        self.errors.append({"code": code, "message": str(message)})
        self.exit_code = 2

    @property
    def status(self) -> str:
        return {0: "ok", 1: "blocked"}.get(self.exit_code, "error")

    def envelope(self) -> dict:
        return {
            "schema": 1,
            "command": self.command,
            "status": self.status,
            "exit_code": self.exit_code,
            "warnings": list(self.warnings),
            "advisories": list(self.advisories),
            "outputs": dict(self.outputs),
            "errors": list(self.errors),
        }


def _abs(path: str | Path | None) -> str | None:
    """Absolute string form for envelope paths (``None`` stays ``None``)."""
    if path is None:
        return None
    return os.path.abspath(Path(path).expanduser())


def _shell_quote(value: str) -> str:
    """Quote a copy-paste path for both PowerShell and POSIX shells."""
    return f'"{value}"' if re.search(r"[\s()&|;<>^]", value) else value


def _toolchain() -> dict[str, str | None]:
    """Versions the Review Packet records as provenance (never as authority)."""
    from . import __version__
    try:
        iconflow_version = importlib.metadata.version("iconflow")
    except importlib.metadata.PackageNotFoundError:
        iconflow_version = __version__
    try:
        import PIL
        pillow_version = getattr(PIL, "__version__", None)
    except ImportError:
        pillow_version = None
    chromium_version = None
    try:
        import playwright
        catalog = Path(playwright.__file__).resolve().parent / "driver" / "package" / "browsers.json"
        for browser in json.loads(catalog.read_text(encoding="utf-8")).get("browsers", []):
            if browser.get("name") == "chromium":
                chromium_version = browser.get("browserVersion") or None
                break
    except (ImportError, OSError, ValueError, AttributeError):
        chromium_version = None
    return {"iconflow": iconflow_version, "chromium": chromium_version, "pillow": pillow_version}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _version_at_least(current: str, required: tuple[int, ...]) -> bool:
    """Compare the numeric release prefix without adding a packaging dependency."""

    match = re.match(r"\s*(\d+(?:\.\d+)*)", current)
    if not match:
        return False
    parts = tuple(int(part) for part in match.group(1).split("."))
    width = max(len(parts), len(required))
    return parts + (0,) * (width - len(parts)) >= required + (0,) * (width - len(required))


def _csv(*values: str) -> list[str]:
    """Expand repeatable comma-separated CLI values into a clean list."""

    return [item.strip() for value in values for item in value.split(",") if item.strip()]


def _resource(package: str, name: str):
    """Return a packaged resource path/Traversable (see :mod:`iconflow.agentkit`)."""

    return agentkit.resource(package, name)


def _cmd_build(a) -> int:
    from .build import build
    try:
        web_options = _web_options(a)
    except ValueError as e:
        print(f"iconflow build: {e}", file=sys.stderr)
        return 2
    targets = [t.strip() for t in a.targets.split(",") if t.strip()]
    try:
        produced = build(
            a.master, a.out, targets,
            name=a.name, theme_color=a.theme, bg_color=a.bg,
            electron_radius=a.electron_radius, tray_ts=a.tray_ts,
            color_scheme=a.color_scheme, web_options=web_options,
            optimize_png=not a.no_optimize,
            tray_svg=a.tray_svg,
            tray_template_mode=a.tray_template_mode,
        )
    except ValueError as e:
        print(f"iconflow build: {e}", file=sys.stderr)
        return 2
    print(f"Built {len(produced)} files into {a.out}:")
    for p in produced:
        print(f"  {p}")
    print("Next (self-evolution loop): record this design —")
    print('  python -m iconflow case new --slug <slug> --essence <word> --device "<signature device>" \\')
    print('      --first "legibility=4 ..." --final "legibility=5 ..." --lesson "<reusable rule>"')
    return 0


def _cmd_init(a) -> int:
    from .build import normalize_targets
    from .casebook import normalize_detail, normalize_taxonomy
    from .config import ConfigError, IconFlowConfig, write_config

    try:
        targets = normalize_targets(_csv(a.targets))
        config = IconFlowConfig(
            source=Path(a.out),
            name=a.name or Path.cwd().name or "App",
            master=a.master,
            output=a.build_out,
            casebook=a.casebook,
            app_intent=a.app_intent,
            user_job=a.user_job,
            essence=a.essence,
            personality=_csv(*a.personality),
            palette=_csv(*a.palette),
            cliches=_csv(*a.cliche),
            signature_device=normalize_detail(a.signature_device),
            device_family=normalize_taxonomy(a.device_family),
            device_detail=normalize_detail(a.device_detail),
            concept_lens=normalize_taxonomy(a.concept_lens),
            targets=targets,
            theme_color=a.theme,
            background_color=a.bg,
            tray_svg=a.tray_svg,
            tray_template_mode=a.tray_template_mode,
        )
        path = write_config(config, force=a.force)
    except (ConfigError, ValueError) as exc:
        print(f"iconflow init: {exc}", file=sys.stderr)
        return 2
    print(f"Project workflow -> {path}")
    print("Next: fill the brief, diverge, then export a Review Lab receipt before `iconflow ship`.")
    return 0


def _ship_approval(a):
    """Resolve the reviewed approval ``ship`` must honour.

    Returns ``(config, master, receipt, scores, contract_sha256)``. Raises
    :class:`ConfigError` with a gate ``code`` when IconFlow's own rules block
    the ship, and a plain one when the configuration itself is invalid.
    """

    from .casebook import parse_scores
    from .config import (
        GATE_NOT_READY, GATE_STALE_CONTRACT, GATE_STALE_SOURCE, ConfigError,
        config_review_contract_digest, load_config, load_review_receipt,
        svg_sha256, validate_ship_scores,
    )

    config = load_config(a.config)
    master = config.master_path
    if not master.is_file():
        raise ConfigError(f"master SVG not found: {master}")
    if a.review:
        receipt = load_review_receipt(a.review, config)
        return config, master, receipt, receipt.scores, receipt.contract_sha256

    scores = parse_scores(a.scores) if a.scores is not None else config.review_scores
    validate_ship_scores(scores)
    if config.review_status not in {"approved", "shipped"}:
        raise ConfigError(
            "review.status must be 'approved' (or provide a ready Review Lab receipt)",
            code=GATE_NOT_READY,
        )
    if not config.review_source_sha256:
        raise ConfigError(
            "approved config fallback requires review.source_sha256 "
            "(or provide a ready Review Lab receipt)",
            code=GATE_NOT_READY,
        )
    if config.review_source_sha256 != svg_sha256(master):
        raise ConfigError(
            "approved config review is stale: review.source_sha256 does not "
            "match the current master SVG",
            code=GATE_STALE_SOURCE,
        )
    if not config.review_contract_sha256:
        raise ConfigError(
            "approved config fallback requires review.contract_sha256 "
            "from the reviewed contract (or provide a ready Review Lab receipt)",
            code=GATE_NOT_READY,
        )
    if config.review_contract_sha256 != config_review_contract_digest(config):
        raise ConfigError(
            "approved config review is stale: review.contract_sha256 does not "
            "match the current source, project, targets, or visual transforms",
            code=GATE_STALE_CONTRACT,
        )
    return config, master, None, scores, config.review_contract_sha256


def _cmd_ship(a) -> Report:
    """Run the fail-closed quality gate, then delegate to the low-level build."""

    from .build import build
    from .config import GATE_CODES, GATE_QA_WARNINGS, ConfigError, svg_sha256
    from .qa import check, warning_code

    report = Report("ship")
    try:
        config, master, receipt, scores, contract_sha256 = _ship_approval(a)
    except ConfigError as exc:
        print(f"iconflow ship: {exc}", file=sys.stderr)
        if exc.code in GATE_CODES:
            report.warn(exc.code, str(exc))
        else:
            report.error("config", str(exc))
        return report
    except ValueError as exc:
        print(f"iconflow ship: {exc}", file=sys.stderr)
        report.error("config", str(exc))
        return report

    try:
        warnings = check(
            master,
            maskable=bool({"web", "pwa"} & set(config.targets)),
            maskable_bg=config.background_color,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"iconflow ship: QA could not run: {exc}", file=sys.stderr)
        report.error("runtime", f"QA could not run: {exc}")
        return report
    if warnings:
        print(f"SHIP BLOCKED — automated check found {len(warnings)} warning(s):", file=sys.stderr)
        report.warn(
            GATE_QA_WARNINGS, f"automated check found {len(warnings)} warning(s)",
        )
        for warning in warnings:
            print(f"  ! {warning}", file=sys.stderr)
            report.warn(warning_code(warning), warning)
        print("Fix the warnings, regenerate review.png, and rescore before shipping.", file=sys.stderr)
        return report

    try:
        output_path = (
            Path(os.path.abspath(Path(a.out).expanduser()))
            if a.out else config.output_path
        )
        produced = build(
            master,
            output_path,
            config.targets,
            name=config.name,
            theme_color=config.theme_color,
            bg_color=config.background_color,
            electron_radius=config.electron_radius,
            tray_ts=config.tray_ts,
            color_scheme=config.color_scheme,
            optimize_png=config.optimize_png,
            tray_svg=config.tray_svg_path,
            tray_template_mode=config.tray_template_mode,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"iconflow ship: build failed: {exc}", file=sys.stderr)
        report.error("runtime", f"build failed: {exc}")
        return report
    print(f"SHIP PASSED — built {len(produced)} files into {output_path}:")
    for path in produced:
        print(f"  {path}")
    print(f"Review scores: " + ", ".join(f"{axis}={scores[axis]}" for axis in scores))
    if receipt:
        print(f"Review receipt: {receipt.source}")
    print(f"Record the shipped case in: {config.casebook_path}")
    report.outputs = {
        "files": [_abs(output_path / path) for path in produced],
        "receipt": _abs(receipt.source) if receipt else None,
        "source_sha256": svg_sha256(master),
        "contract_sha256": contract_sha256,
        "scores": dict(scores),
        # Review Packet v1: provenance recorded when present, never required.
        "toolchain": _toolchain(),
        "artifacts": receipt.artifacts if receipt else None,
        "reviewer": receipt.reviewer if receipt else None,
    }
    return report


def _parse_pairs(items: list[str], *, value_json: bool) -> dict:
    parsed: dict[str, object] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"expected KEY=VALUE, got '{item}'")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty metadata key in '{item}'")
        if value_json:
            try:
                parsed[key] = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed[key] = raw_value
        else:
            parsed[key] = raw_value
    return parsed


def _web_options(a):
    from .htmlhead import WebMetaOptions
    return WebMetaOptions(
        path_prefix=a.path_prefix,
        relative_paths=a.relative_paths,
        short_name=a.short_name,
        description=a.description,
        start_url=a.start_url,
        scope=a.scope,
        display=a.display,
        orientation=a.orientation,
        lang=a.lang,
        dir=a.dir,
        categories=[c.strip() for c in a.categories.split(",") if c.strip()],
        app_id=a.app_id,
        manifest_extra=_parse_pairs(a.manifest_extra, value_json=True),
        head_meta={k: str(v) for k, v in _parse_pairs(a.head_meta, value_json=False).items()},
        windows_tiles=a.windows_tiles,
        tile_color=a.tile_color,
    )


def _cmd_review(a) -> Report:
    from .build import normalize_targets
    from .config import ConfigError, load_config, svg_sha256
    from .qa import check, tray_template_warnings, warning_code
    from .rasterize import load_svg
    from .review import (
        ReviewOptions, contact_sheet, interactive_review, ladder_sheet,
        receipt_seed, receipt_template,
    )

    report = Report("review")
    try:
        config = load_config(a.config) if a.config else None
        if a.master:
            master = Path(a.master).expanduser().resolve(strict=False)
        elif config:
            master = config.master_path
        else:
            raise ConfigError("provide MASTER or --config iconflow.toml")
        if not master.is_file():
            raise ConfigError(f"master SVG not found: {master}")

        targets = (
            normalize_targets(_csv(a.targets)) if a.targets
            else config.targets if config
            else ["web", "pwa"]
        )
        background = a.bg or (config.background_color if config else "#ffffff")
        color_scheme = a.color_scheme or (config.color_scheme if config else "light")
        electron_radius = (
            a.electron_radius if a.electron_radius is not None
            else config.electron_radius if config else 0.0
        )
        tray_svg = (
            Path(a.tray_svg).expanduser().resolve(strict=False) if a.tray_svg
            else config.tray_svg_path if config else None
        )
        tray_template_mode = (
            a.tray_template_mode or
            (config.tray_template_mode if config else "auto")
        )
        warnings = check(
            master,
            maskable=bool({"web", "pwa"} & set(targets)),
            maskable_bg=background,
        )
        # Advisory only: a linked tray source is a different reduction of the
        # same mark, so it informs the designer without gating `ship`.
        tray_advisories = (
            tray_template_warnings(tray_svg, template_mode=tray_template_mode)
            if tray_svg and "tray" in targets else []
        )
        options = ReviewOptions(
            name=a.name or (config.name if config else master.stem),
            user_job=config.user_job if config else "",
            essence=config.essence if config else "",
            personality=", ".join(config.personality) if config else "",
            signature_device=config.signature_device if config else "",
            cliches=tuple(config.cliches) if config else (),
            targets=tuple(targets),
            theme_color=a.theme or (config.theme_color if config else "#17181c"),
            background_color=background,
            electron_radius=electron_radius,
            tray_svg=tray_svg,
            tray_template_mode=tray_template_mode,
            color_scheme=color_scheme,
            warnings=tuple(warnings),
            scores=dict(config.review_scores) if config else {},
            notes=config.review_notes if config else "",
        )
    except (ConfigError, ValueError) as exc:
        print(f"iconflow review: {exc}", file=sys.stderr)
        report.error("config", str(exc))
        return report

    out = contact_sheet(
        master, a.out, background_color=background, color_scheme=color_scheme,
    )
    print(f"Review sheet -> {out}")
    print("Open it (or Read it as an image) and score against docs/REVIEW_CHECKLIST.md.")
    # A laddered source is three drawings, and the contact sheet shows the one
    # each size happens to land on. The ladder proof is where a person can see
    # whether detail appears as the size grows without the identity moving, so
    # it is written beside the sheet rather than behind a separate command.
    ladder_out = None
    if _LADDER.has_ladder(load_svg(master)):
        ladder_out = ladder_sheet(
            master,
            Path(out).with_name(f"{Path(out).stem}-ladder{Path(out).suffix or '.png'}"),
            color_scheme=color_scheme,
        )
        print(f"Detail-ladder proof -> {ladder_out}")
        print("Read it too: detail must APPEAR as the size grows, never change identity.")
    html_out = None
    if a.html:
        html_out = interactive_review(master, a.html, options=options)
        print(f"Review Lab -> {html_out}")
        print("Export its JSON receipt and pass it to `iconflow ship --review <receipt>`.")
    template_out = None
    if getattr(a, "receipt_template", None):
        template_out = receipt_template(master, a.receipt_template, options=options)
        print(f"Receipt template -> {template_out}")
        print("Score every axis, set status to \"ready\", then `iconflow ship --review <receipt>`.")
    if warnings:
        print(f"Review includes {len(warnings)} automated warning(s); ship remains blocked.")
    for warning in warnings:
        report.warn(warning_code(warning), warning)
    for advisory in tray_advisories:
        print(f"Tray template advisory: {advisory}")
        report.advise(warning_code(advisory), advisory)
    seed = receipt_seed(master, options=options)
    # `review`'s envelope is frozen at schema 1 and the PR Proof action rejects
    # anything else, so the ladder proof is reported as a path on stderr and
    # through `iconflow ladder --json`, not as a new key here.
    report.outputs = {
        "sheet": _abs(out),
        "html": _abs(html_out),
        "receipt_template": _abs(template_out),
        "source_sha256": svg_sha256(master),
        "contract_sha256": seed["contract_sha256"],
        "targets": list(targets),
    }
    return report


def _cmd_compare(a) -> int:
    from .review import compare_sheet
    if len(a.candidates) < 2:
        print("iconflow compare: provide at least two candidate SVGs", file=sys.stderr)
        return 2
    candidates = [(Path(p).stem, p) for p in a.candidates]
    out = compare_sheet(candidates, a.out)
    print(f"Bake-off sheet -> {out}")
    print("Read it: pick the most DISTINCTIVE candidate that still reads at 16px and in silhouette.")
    return 0


def _cmd_check(a) -> Report:
    from .config import svg_sha256
    from .qa import check, tray_template_warnings, warning_code

    report = Report("check")
    warnings = check(
        a.master, maskable=not a.no_maskable_audit, maskable_bg=a.bg,
    )
    advisories: list[str] = []
    if a.tray_svg:
        try:
            advisories = tray_template_warnings(
                a.tray_svg, template_mode=a.tray_template_mode,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"iconflow check: tray audit could not run: {exc}", file=sys.stderr)
            report.error("runtime", f"tray audit could not run: {exc}")
            return report
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ! {w}")
            report.warn(warning_code(w), w)
    else:
        print("OK — no automated warnings. Still do the visual review.")
    # Advisories inform the designer; they never turn a clean check into a block.
    for advisory in advisories:
        print(f"  ~ tray template advisory: {advisory}")
        report.advise(warning_code(advisory), advisory)
    report.outputs = {
        "source": _abs(a.master),
        "source_sha256": svg_sha256(a.master),
        "tray_source": _abs(a.tray_svg) if a.tray_svg else None,
    }
    return report


def _cmd_render(a) -> int:
    from .rasterize import Rasterizer, load_svg
    svg = load_svg(a.master)
    sizes = [int(s.strip()) for s in str(a.sizes).split(",") if s.strip()]
    if not sizes:
        print("No sizes given. Example: --sizes 256,64,32", file=sys.stderr)
        return 2

    def dest_for(size: int) -> Path:
        out = a.out
        if "{size}" in out:
            return Path(out.format(size=size))
        p = Path(out)
        if len(sizes) > 1:  # disambiguate: insert -<size> before the suffix
            return p.with_name(f"{p.stem}-{size}{p.suffix or '.png'}")
        return p

    with Rasterizer(color_scheme=a.color_scheme) as r:
        for size in sizes:
            dest = dest_for(size)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.render(svg, size, bg=a.bg))
            print(f"  {dest} ({size}px)")
    return 0


def _cmd_ladder(a) -> Report:
    from . import ladder as detail_ladder
    from .config import svg_sha256
    from .rasterize import load_svg
    from .review import ladder_sheet

    report = Report("ladder")
    svg = load_svg(a.master)
    annotated = detail_ladder.has_ladder(svg)
    thresholds = {
        "containment_floor": a.containment,
        "iou_floor": a.iou,
        "centroid_ceiling": a.centroid_drift,
        "hue_ceiling": a.hue_drift,
    }
    audit = detail_ladder.ladder_report(
        a.master, color_scheme=a.color_scheme, size=a.size, **thresholds
    )

    if not annotated:
        print(
            f"{Path(a.master).name} is flat — no data-lod anywhere, so every size "
            "renders the same drawing."
        )
        print(
            "  That is a valid icon and nothing is broken. It is also the ceiling: "
            "the mark you tuned for 16px is the mark a 1024px store plate shows."
        )
        print("  To open the ladder, see: python -m iconflow docs DETAIL_LADDER")
        report.advise(
            "ladder-flat",
            "source has no data-lod annotations; every size renders one drawing",
        )
    else:
        named = ", ".join(audit["rungs"])
        print(f"Ladder: {named}  (compared at {audit['compare_size']}px)")
        for measure in audit["measures"]:
            hue = "-" if measure["hue"] is None else f"{measure['hue']:.0f} deg"
            print(
                f"  {measure['rung']:<6} {detail_ladder.rung_sizes(measure['rung']):>10}"
                f"   footprint {measure['coverage']:.1%}"
                f"   visible {measure['visible']:.1%}   hue {hue}"
            )
        for step in audit["steps"]:
            drift = step["centroid_drift"]
            hue = step["hue_drift"]
            print(
                f"  {step['smaller']} -> {step['larger']}: "
                f"shape {step['visible_iou']:.0%}, "
                f"footprint {step['footprint_iou']:.0%}, "
                f"centre moves {0.0 if drift is None else drift:.1%}, "
                f"hue moves {0.0 if hue is None else hue:.0f} deg"
            )

    for finding in audit["findings"]:
        print(f"  ! {finding['message']}")
        report.warn(finding["code"], finding["message"])

    sheet = None
    if a.sheet:
        sheet = ladder_sheet(
            a.master, a.sheet, color_scheme=a.color_scheme, compare_size=a.size
        )
        print(f"Ladder proof sheet -> {sheet}")
        print("Read it: detail should APPEAR as the size grows, never change identity.")

    report.outputs = {
        "source": _abs(a.master),
        "source_sha256": svg_sha256(a.master),
        "ladder": audit["ladder"],
        "rungs": audit["rungs"],
        "compare_size": audit["compare_size"],
        "measures": audit["measures"],
        "steps": audit["steps"],
        "sheet": _abs(sheet) if sheet else None,
    }
    return report


def _cmd_new(a) -> int:
    try:
        src = _resource("presets", f"{a.preset}.svg")
    except (ModuleNotFoundError, TypeError) as exc:
        print(f"iconflow new: packaged presets are unavailable: {exc}", file=sys.stderr)
        return 2
    if not src.is_file():
        print(f"Unknown preset '{a.preset}'. Choose from: {', '.join(PRESETS)}", file=sys.stderr)
        return 2
    destination = Path(a.out)
    if destination.is_symlink():
        print(
            f"iconflow new: destination must not be a symlink: {destination}",
            file=sys.stderr,
        )
        return 2
    if destination.exists() and not a.force:
        print(
            f"iconflow new: destination already exists: {destination} "
            "(use --force to replace it)",
            file=sys.stderr,
        )
        return 2
    destination.parent.mkdir(parents=True, exist_ok=True)
    # The scaffold's licence header stays on IconFlow's copy. Carried into this
    # one it would ride master.svg into the favicon the user serves in
    # production, which is precisely the attribution LICENSES.md §1 promises
    # never to require. Tell the person instead of their visitors' browsers.
    destination.write_text(
        agentkit.strip_spdx_comment(src.read_text(encoding="utf-8")),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Copied {a.preset} preset -> {destination}")
    print("It is a public-domain (CC0) scaffold: this file and whatever you make")
    print("from it are yours — no attribution, no conditions. `iconflow license`.")
    print("Now edit it following `iconflow docs DESIGN_PLAYBOOK`, then `review` and `ship`.")
    return 0


def _cmd_styles(a) -> int:
    """Describe or render the packaged technique-scaffold catalog."""
    if a.force and not a.gallery:
        print("iconflow styles: --force requires --gallery PNG", file=sys.stderr)
        return 2
    if a.gallery:
        from .review import style_gallery

        destination = Path(a.gallery)
        if destination.is_symlink():
            print(
                f"iconflow styles: gallery destination must not be a symlink: {destination}",
                file=sys.stderr,
            )
            return 2
        if destination.exists() and not a.force:
            print(
                f"iconflow styles: gallery destination already exists: {destination} "
                "(use --force to replace it)",
                file=sys.stderr,
            )
            return 2
        sources = []
        try:
            for style in STYLE_CATALOG:
                sources.append((style, _resource("presets", f"{style.slug}.svg").read_text(
                    encoding="utf-8"
                )))
            destination = style_gallery(sources, destination)
        except (FileNotFoundError, ModuleNotFoundError, OSError, TypeError, ValueError) as exc:
            print(f"iconflow styles: {exc}", file=sys.stderr)
            return 2
        print(f"Style gallery -> {destination}")
        print("Read it at actual size: every tile includes 16px proof on light and dark.")
        return 0

    if a.json:
        print(json.dumps([style.to_dict() for style in STYLE_CATALOG], indent=2))
        return 0

    width = max(len(style.slug) for style in STYLE_CATALOG)
    print(f"{len(STYLE_CATALOG)} technique scaffolds (starting points, not finished logos):")
    for style in STYLE_CATALOG:
        print(f"  {style.slug:<{width}}  {style.technique}")
        print(f"  {'':<{width}}  16px: {style.small_size_rule}")
    print("\nInspect the full matrix: iconflow styles --gallery style-gallery.png")
    print("Then: iconflow new <style> --out master.svg")
    return 0


def _cmd_shortcut(a) -> int:
    from .shortcut import create_shortcut
    target = a.target
    args_line = a.args_line
    if a.powershell_script:
        if target:
            print("iconflow shortcut: use either --target or --powershell-script, not both", file=sys.stderr)
            return 2
        if args_line:
            print("iconflow shortcut: --args is not supported with --powershell-script", file=sys.stderr)
            return 2
        script = Path(a.powershell_script)
        target = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        args_line = f'-NoProfile -ExecutionPolicy Bypass -File "{script}"'
    elif not target:
        print("iconflow shortcut: either --target or --powershell-script is required", file=sys.stderr)
        return 2

    lines = create_shortcut(
        target=target, name=a.name, icon=a.icon, args=args_line,
        workdir=a.workdir, desc=a.desc, out=a.out, verify=a.verify,
        content_address_icon=a.content_address_icon,
    )
    for ln in lines:
        print(f"  {ln}")
    return 0 if any(ln.startswith("OK") for ln in lines) else 1


def _cmd_case_new(a) -> int:
    from .casebook import new_case, parse_scores
    try:
        path = new_case(
            a.dir, a.slug, project=a.project, targets=a.targets, essence=a.essence,
            style_family=a.style, signature_device=a.device, cliche_avoided=a.cliche,
            device_family=a.device_family, device_detail=a.device_detail,
            concept_lens=a.concept_lens, status=a.status,
            scores_first=parse_scores(a.first or ""),
            scores_final=parse_scores(a.final or ""),
            iterations=a.iterations, summary=a.summary,
            lessons=a.lesson, date=a.date or "",
        )
    except ValueError as e:
        print(f"iconflow case new: {e}", file=sys.stderr)
        return 2
    print(f"Case recorded -> {path}")
    print("Fill in 'What failed first' and the Lessons bullets, then run: iconflow case stats")
    return 0


def _cmd_case_stats(a) -> int:
    from .casebook import format_stats, load_casebook, stats
    for line in format_stats(stats(load_casebook(a.dir))):
        print(line)
    return 0


def _cmd_case_list(a) -> int:
    from .casebook import load_casebook
    cases = load_casebook(a.dir)
    if not cases:
        print(f"No cases in {a.dir}.")
        return 0
    for c in cases:
        undistilled = len(c.undistilled)
        extra = f"  ({undistilled} undistilled lesson(s))" if undistilled else ""
        print(f"  {c.path.name}: {c.essence or '?'} / {c.signature_device or '?'}{extra}")
    return 0


def _cmd_case_lint(a) -> int:
    from .casebook import lint_casebook

    issues = lint_casebook(a.dir)
    if not issues:
        print(f"OK — casebook is clean: {Path(a.dir).resolve(strict=False)}")
        return 0
    for issue in issues:
        print(f"  {issue.severity.upper():<7} {issue.path.name}: {issue.message}")
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = len(issues) - errors
    print(f"case lint: {errors} error(s), {warnings} warning(s)")
    return 1 if errors or (a.strict and warnings) else 0


def _cmd_case_atlas(a) -> int:
    from .casebook import load_casebook, write_atlas

    cases = load_casebook(a.dir)
    path = write_atlas(a.dir, a.out, cases=cases)
    print(f"Casebook atlas -> {path} ({len(cases)} case(s))")
    return 0


def _cmd_setup(a) -> int:
    print("Installing Playwright Chromium...")
    # `demo --json --setup`: the installer's own output must not reach stdout.
    sink = sys.__stderr__ if getattr(a, "json", False) else None
    return subprocess.call(
        [sys.executable, "-m", "playwright", "install", "chromium"], stdout=sink,
    )


def _writable_dir_probe(path: Path) -> bool:
    """True when ``path`` or its nearest existing ancestor is a writable directory."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe.is_dir() and os.access(probe, os.W_OK)


def _cmd_doctor(a) -> Report:
    """Diagnose install/runtime readiness without mutating the environment."""

    python = _shell_quote(sys.executable)
    report = Report("doctor")
    checks: list[dict] = []

    def record(ok: bool | None, label: str, detail: str = "", fix: str | None = None) -> None:
        # Human: PASS / SKIP / FAIL. Machine: PASS / WARN / FAIL — a skipped
        # check is reported as WARN because nothing was verified.
        state = "PASS" if ok is True else "SKIP" if ok is None else "FAIL"
        suffix = f" — {detail}" if detail else ""
        print(f"{state:<4} {label}{suffix}")
        checks.append({
            "name": label,
            "status": "PASS" if ok is True else "WARN" if ok is None else "FAIL",
            "detail": detail,
            "fix": fix if ok is False else None,
        })
        if ok is False:
            report.warn(re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-"), f"{label}: {detail}")

    record(
        sys.version_info >= (3, 10), "Python", sys.version.split()[0],
        fix="Install Python 3.10 or newer and recreate the virtual environment: python3 -m venv .venv",
    )
    try:
        import PIL
        pillow_version = getattr(PIL, "__version__", "unknown")
        record(
            _version_at_least(pillow_version, (10, 0)),
            "Pillow",
            f"{pillow_version} (requires >=10.0)",
            fix=f'{python} -m pip install "Pillow>=10.0"',
        )
    except ImportError as exc:
        record(False, "Pillow", str(exc), fix=f'{python} -m pip install "Pillow>=10.0"')
    try:
        import playwright  # noqa: F401
        playwright_version = importlib.metadata.version("playwright")
        record(
            _version_at_least(playwright_version, (1, 40)),
            "Playwright package",
            f"{playwright_version} (requires >=1.40)",
            fix=f'{python} -m pip install "playwright>=1.40"',
        )
    except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
        record(
            False, "Playwright package", str(exc),
            fix=f'{python} -m pip install "playwright>=1.40"',
        )

    missing_resources: list[str] = []
    resource_sets = (
        ("presets", [f"{preset}.svg" for preset in PRESETS]),
        ("templates", ["master.svg", "grid-overlay.svg"]),
        ("docs", ["DESIGN_PLAYBOOK.md", "REVIEW_CHECKLIST.md", "OUTPUT_TARGETS.md"]),
        ("demo", list(DEMO_FILES)),
        ("skill", list(agentkit.SKILL_FILES)),
    )
    for package, names in resource_sets:
        for name in names:
            try:
                if not _resource(package, name).is_file():
                    missing_resources.append(f"{package}/{name}")
            except (ModuleNotFoundError, TypeError):
                missing_resources.append(f"{package}/{name}")
    record(
        not missing_resources, "Packaged resources",
        ", ".join(missing_resources) if missing_resources
        else f"{len(PRESETS)} presets + base templates + docs + demo family + agent skill",
        fix=f"{python} -m pip install --force-reinstall --no-deps iconflow",
    )

    config = None
    config_path = Path(a.config) if a.config else Path("iconflow.toml")
    config_arg = _shell_quote(str(config_path))
    if config_path.exists() or a.config:
        try:
            from .config import config_review_contract_digest, load_config, svg_sha256
            config = load_config(config_path)
            record(True, "Project config", str(config.source))
            master_exists = config.master_path.is_file()
            record(
                master_exists, "Master SVG", str(config.master_path),
                fix=f"{python} -m iconflow new flat-geometric --out {_shell_quote(str(config.master_path))}",
            )
            if config.tray_svg_path:
                record(
                    config.tray_svg_path.is_file(),
                    "Semantic tray SVG",
                    str(config.tray_svg_path),
                    fix=f"{python} -m iconflow new flat-geometric --out {_shell_quote(str(config.tray_svg_path))}",
                )
            re_review = f"{python} -m iconflow review --config {config_arg} --html review.html"
            if config.review_source_sha256 and master_exists:
                current_digest = svg_sha256(config.master_path)
                record(
                    config.review_source_sha256 == current_digest,
                    "Approved source hash",
                    "matches current master" if config.review_source_sha256 == current_digest
                    else "stale review.source_sha256",
                    fix=re_review,
                )
            else:
                record(None, "Approved source hash", "no bound approved fallback")
            if config.review_contract_sha256 and master_exists:
                current_contract = config_review_contract_digest(config)
                record(
                    config.review_contract_sha256 == current_contract,
                    "Approved review contract",
                    "matches current build" if config.review_contract_sha256 == current_contract
                    else "stale review.contract_sha256",
                    fix=re_review,
                )
            else:
                record(None, "Approved review contract", "no bound approved fallback")
            record(
                _writable_dir_probe(config.output_path),
                "Writable build output",
                str(config.output_path),
                fix=f"mkdir {_shell_quote(str(config.output_path))}",
            )
        except (OSError, ValueError) as exc:
            record(
                False, "Project config", str(exc),
                fix=f"{python} -m iconflow init --out {config_arg} --force",
            )
    else:
        record(None, "Project config", "no iconflow.toml in this directory")

    from .casebook import default_casebook_dir
    casebook = (
        config.casebook_path if config is not None
        else default_casebook_dir().expanduser().resolve(strict=False)
    )
    record(
        _writable_dir_probe(casebook), "Writable casebook", str(casebook),
        fix=f"mkdir {_shell_quote(str(casebook))}",
    )

    chromium = "SKIPPED"
    if a.no_browser:
        record(None, "Chromium runtime", "skipped by --no-browser")
    else:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as manager:
                browser = manager.chromium.launch(headless=True)
                browser.close()
            record(True, "Chromium runtime")
            chromium = "PASS"
        except Exception as exc:  # Playwright exposes several runtime-specific exceptions
            record(
                False, "Chromium runtime", f"{exc} (run `iconflow setup`)",
                fix=f"{python} -m iconflow setup",
            )
            chromium = "FAIL"

    report.outputs = {"checks": checks, "chromium": chromium}
    failures = len(report.warnings)
    if failures:
        print(f"Doctor found {failures} blocking issue(s).", file=sys.stderr)
        return report
    print("IconFlow is ready.")
    return report


def _materialize_demo(out: Path, *, force: bool) -> dict[str, Path]:
    """Copy the packaged, already-reviewed brand family into ``out``."""
    if out.is_symlink():
        raise ValueError(f"destination must not be a symlink: {out}")
    if out.exists() and not force:
        raise ValueError(f"destination already exists: {out} (use --force to reuse it)")
    try:
        sources = {name: _resource("demo", name) for name in DEMO_FILES}
        missing = [name for name, source in sources.items() if not source.is_file()]
    except (ModuleNotFoundError, TypeError) as exc:
        raise RuntimeError(f"packaged demo family is unavailable: {exc}") from exc
    if missing:
        raise RuntimeError(
            "packaged demo family is incomplete: missing " + ", ".join(missing)
        )
    out.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    for name, source in sources.items():
        destination = out / name
        if destination.is_symlink():
            raise ValueError(f"destination must not be a symlink: {destination}")
        destination.write_bytes(source.read_bytes())
        copied[name] = destination
    # This directory now holds IconFlow's real product mark, which is the one
    # thing the toolkit copies out that is NOT a starting point for your icon.
    notice = out / "LICENSE-NOTICE.md"
    if notice.is_symlink():
        # Skipping the notice would leave IconFlow's own mark sitting in a
        # directory with nothing saying so. Fail closed instead.
        raise ValueError(f"destination must not be a symlink: {notice}")
    notice.write_text(DEMO_NOTICE, encoding="utf-8", newline="\n")
    copied["LICENSE-NOTICE.md"] = notice
    return copied


def _cmd_demo(a) -> Report:
    """Prove the engine end to end on the packaged brand family."""

    report = Report("demo")
    out = Path(os.path.abspath(Path(a.out).expanduser()))
    try:
        files = _materialize_demo(out, force=a.force)
    except ValueError as exc:
        print(f"iconflow demo: {exc}", file=sys.stderr)
        report.error("usage", str(exc))
        return report
    except (OSError, RuntimeError) as exc:
        print(f"iconflow demo: {exc}", file=sys.stderr)
        report.error("runtime", str(exc))
        return report
    print(f"Demo family -> {out}")
    for name in DEMO_FILES:
        print(f"  {name}")

    if a.setup:
        print("Step setup: iconflow setup")
        setup_code = _cmd_setup(a)
        if setup_code != 0:
            print("iconflow demo: setup failed; Chromium is required for review and ship", file=sys.stderr)
            report.error("runtime", f"iconflow setup exited with {setup_code}")
            report.outputs = {"out": str(out), "steps": [], "files": [], "receipt": None}
            return report

    from .config import load_config
    config = load_config(files["iconflow.toml"])
    config_arg = str(files["iconflow.toml"])
    plan = [
        ("doctor", ["doctor", "--config", config_arg]),
        ("check", [
            "check", str(files["master.svg"]), "--bg", config.background_color,
            "--tray-svg", str(files["tray.svg"]),
            "--tray-template-mode", config.tray_template_mode,
        ]),
        ("review", [
            "review", "--config", config_arg,
            "--out", str(out / "review.png"), "--html", str(out / "review.html"),
        ]),
        ("ship", ["ship", "--config", config_arg, "--review", str(files["master-review.json"])]),
    ]
    parser = build_parser()
    steps: list[dict] = []
    shipped: Report | None = None
    for name, argv in plan:
        print(f"Step {name}: iconflow {' '.join(argv)}")
        step = _execute(parser.parse_args(argv))
        assert isinstance(step, Report)
        steps.append({"name": name, "status": step.status, "exit_code": step.exit_code})
        report.warnings.extend(step.warnings)
        report.advisories.extend(step.advisories)
        report.errors.extend(step.errors)
        report.exit_code = max(report.exit_code, step.exit_code)
        if step.exit_code != 0:
            print(f"iconflow demo: step '{name}' {step.status} (exit {step.exit_code}); stopping.", file=sys.stderr)
            break
        if name == "ship":
            shipped = step

    evidence = {
        "review_png_sha256": out / "review.png",
        "review_html_sha256": out / "review.html",
    }
    report.outputs = {
        "out": str(out),
        "steps": steps,
        "files": list(shipped.outputs.get("files", [])) if shipped else [],
        "receipt": str(files["master-review.json"]),
        # Review Packet v1 artifact hashes for the evidence this run produced.
        "artifacts": {
            key: _file_sha256(path) if path.is_file() else None
            for key, path in evidence.items()
        },
    }
    if report.exit_code == 0:
        print(f"DEMO PASSED — doctor, check, review, and ship agreed on {out}")
        print(f"Open {out / 'review.html'} to see the evidence; edit master.svg and re-run ship to watch it fail closed.")
    return report


def _cmd_docs(a) -> int:
    """Serve the packaged reference documents the design procedure cites.

    An agent that installed a wheel has no `docs/` directory to read; this is
    how it gets DESIGN_PLAYBOOK, CONCEPTING, and the rest without a checkout.
    """
    if a.json and a.name:
        print(
            "iconflow docs: --json lists the catalog; drop NAME, or read the "
            "document with `iconflow docs NAME` or `--path`",
            file=sys.stderr,
        )
        return 2
    try:
        if a.out:
            names = [agentkit.resolve_doc(a.name)] if a.name else None
            written = agentkit.export_docs(Path(a.out), names)
            for path in written:
                print(path)
            print(
                f"{len(written)} file(s) -> {Path(a.out).resolve()}. "
                "Read them from disk; images resolve beside the markdown.",
                file=sys.stderr,
            )
            print(
                "Reference copies, not your work: the documents are CC BY-SA 4.0 and "
                "the images beside them are CC BY 4.0.\nKeep them out of version "
                "control unless you accept those terms for your copy — a gitignored "
                "work/ directory is the usual place.\nReading them obliges you "
                "nothing, and icons you design afterwards are yours: `iconflow license`.",
                file=sys.stderr,
            )
            return 0
        if not a.name:
            names = agentkit.doc_names()
            if a.json:
                print(json.dumps(
                    [{"name": name, "summary": agentkit.doc_summary(name)} for name in names],
                    ensure_ascii=False, indent=2,
                ))
                return 0
            width = max((len(name) for name in names), default=0)
            for name in names:
                summary = agentkit.doc_summary(name)
                print(f"{name.ljust(width)}  {summary}" if summary else name)
            sys.stdout.flush()
            print("\nRead one with: iconflow docs DESIGN_PLAYBOOK", file=sys.stderr)
            return 0
        name = agentkit.resolve_doc(a.name)
        if a.path:
            return _print_resource_path("docs", f"{name}.md")
        print(agentkit.read_doc(name))
        return 0
    except ValueError as exc:
        print(f"iconflow docs: {exc}", file=sys.stderr)
        return 2


def _print_resource_path(package: str, name: str) -> int:
    """Print a packaged resource's real path, or explain why there isn't one.

    An install that keeps resources inside a zip has no filesystem path to
    print; saying so beats printing something that cannot be opened.
    """
    located = agentkit.resource(package, name)
    path = Path(str(located))
    if not path.is_file():
        print(
            f"iconflow: {name} is packaged without a filesystem path in this "
            "install; use `iconflow docs --out DIR` or `iconflow skill print`",
            file=sys.stderr,
        )
        return 2
    print(path)
    return 0


def _skill_roots(a) -> list[Path]:
    """Resolve which `skills/` roots this invocation writes into."""
    if a.dir:
        return [Path(value).expanduser() for value in a.dir]
    if a.project:
        return agentkit.project_skill_roots(Path.cwd())
    return agentkit.default_skill_roots()


def _cmd_skill(a) -> int:
    """Deploy or print the packaged Agent Skill.

    `install` is the no-checkout path: it copies SKILL.md and its client
    metadata out of the wheel into the discovery roots current Agent Skills
    clients scan, so any agent picks up the same procedure the repository ships.
    """
    if a.skill_cmd == "print":
        print(agentkit.skill_text())
        return 0
    if a.skill_cmd == "path":
        return _print_resource_path("skill", "SKILL.md")

    chose_roots = bool(a.dir or a.project)
    roots = _skill_roots(a)
    try:
        installed, replaced = agentkit.install_skill(roots)
    except OSError as exc:
        print(f"iconflow skill install: {exc}", file=sys.stderr)
        return 2
    removed = [] if chose_roots else agentkit.remove_legacy_skills()
    for path in installed:
        print(f"Installed IconFlow skill to {path}")
    for path in replaced + removed:
        print(f"Removed superseded IconFlow skill file {path}", file=sys.stderr)
    sys.stdout.flush()
    plugin_dirs = [] if chose_roots else agentkit.claude_plugin_dirs()
    if plugin_dirs:
        print(
            f"\nSkipped ~/.claude/skills — the IconFlow Claude Code plugin at "
            f"{plugin_dirs[0]} already carries this skill, and a second copy "
            "would show up twice.\nPass --dir to install there anyway.",
            file=sys.stderr,
        )
    else:
        print(
            "\nClaude Code users can instead install the plugin, which carries this"
            "\nsame skill plus /iconflow:icon and /iconflow:setup:"
            "\n  /plugin marketplace add snowyukitty/ai-iconflow"
            "\n  /plugin install iconflow@iconflow",
            file=sys.stderr,
        )
    print(
        "Restart the agent client so it rescans skills, then ask it for an icon."
        "\nThe skill itself is CC BY-SA 4.0 reference material; committing a copy "
        "to a public\nrepository redistributes it under those terms. It puts no "
        "condition on the icons you make.",
        file=sys.stderr,
    )
    return 0


def _cmd_license(a) -> int:
    """Answer "may I ship this commercially?" without anyone reading a lawyer.

    An agent working in someone else's repository needs this in one call, and
    the honest answer is short: the icon it just designed carries no IconFlow
    conditions at all.
    """
    if a.json:
        print(json.dumps(agentkit.license_summary(), ensure_ascii=False, indent=2))
        return 0
    summary = agentkit.license_summary()
    print(summary["headline"])
    print()
    for line in summary["your_output"]:
        print(f"  - {line}")
    print()
    print("This repository is not under one licence. What each part carries:")
    width = max(len(tier["paths"]) for tier in summary["tiers"])
    for tier in summary["tiers"]:
        print(f"  {tier['paths'].ljust(width)}  {tier['license']}")
    print()
    for line in summary["notes"]:
        print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iconflow", description="IconFlow design-proof and build engine")
    from . import __version__
    p.add_argument("--version", action="version", version=f"IconFlow {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="create a project brief and build contract (iconflow.toml)")
    init.add_argument("--out", default="iconflow.toml", help="configuration path")
    init.add_argument("--force", action="store_true", help="replace an existing configuration")
    init.add_argument("--name", help="app/product name (defaults to the current directory name)")
    init.add_argument("--master", default="master.svg", help="editable SVG source path")
    init.add_argument("--build-out", default="icon-out", help="generated icon directory")
    init.add_argument("--casebook", default="casebook", help="writable project casebook directory")
    init.add_argument("--app-intent", default="", help="what the app enables")
    init.add_argument("--user-job", default="", help="the user's job-to-be-done")
    init.add_argument("--essence", default="", help="one-word design essence")
    init.add_argument("--personality", action="append", default=[],
                      help="personality trait(s), comma-separated or repeatable")
    init.add_argument("--palette", action="append", default=[],
                      help="brand/color token(s), comma-separated or repeatable")
    init.add_argument("--cliche", action="append", default=[],
                      help="category cliché to avoid, repeatable")
    init.add_argument("--signature-device", default="", help="the single ownable visual device")
    init.add_argument("--device-family", default="", help="normalized device family")
    init.add_argument("--device-detail", default="", help="specific execution of the device")
    init.add_argument("--concept-lens", default="", help="winning concept lens")
    init.add_argument("--targets", default="web", help="comma list of build targets")
    init.add_argument("--theme", default="#0b0d12", help="theme color")
    init.add_argument("--bg", default="#ffffff", help="flattening/background color")
    init.add_argument("--tray-svg", default="", help="optional semantic foreground SVG for tray output")
    init.add_argument("--tray-template-mode", default="auto",
                      choices=["auto", "alpha", "contrast"],
                      help="macOS tray template extraction mode")
    init.set_defaults(func=_cmd_init)

    ship = sub.add_parser("ship", help="quality-gated build driven by iconflow.toml")
    ship.add_argument("--config", default="iconflow.toml", help="project configuration path")
    ship.add_argument(
        "--out",
        help="output directory override (does not change the reviewed visual contract)",
    )
    ship_review = ship.add_mutually_exclusive_group()
    ship_review.add_argument(
        "--review",
        help="Review Lab JSON receipt; verifies the current source and target set",
    )
    ship_review.add_argument(
        "--scores",
        help="six-axis override for an approved config, e.g. 'legibility=4 ...'",
    )
    ship.add_argument("--json", action="store_true", help=JSON_HELP)
    ship.set_defaults(func=_cmd_ship)

    b = sub.add_parser("build", help="build icon set(s) from a master SVG")
    b.add_argument("master")
    b.add_argument("--out", default="./icon-out")
    b.add_argument("--targets", default="web", help="comma list: web,pwa,tauri,electron,tray,all")
    b.add_argument("--name", default="App")
    b.add_argument("--short-name", help="manifest short_name (defaults to --name)")
    b.add_argument("--description", help="manifest/head description")
    b.add_argument("--theme", default="#0b0d12", help="manifest theme_color")
    b.add_argument("--bg", default="#ffffff", help="manifest/apple-icon background_color")
    b.add_argument("--path-prefix", default="/",
                   help="prefix for generated head/manifest asset URLs, e.g. /assets/icons/")
    b.add_argument("--relative-paths", action="store_true",
                   help="emit ./favicon.ico head paths and relative manifest icon paths")
    b.add_argument("--start-url", help="manifest start_url")
    b.add_argument("--scope", help="manifest scope")
    b.add_argument("--display", default="standalone",
                   choices=["fullscreen", "standalone", "minimal-ui", "browser"])
    b.add_argument("--orientation", help="manifest orientation")
    b.add_argument("--lang", help="manifest lang")
    b.add_argument("--dir", choices=["ltr", "rtl", "auto"], help="manifest text direction")
    b.add_argument("--categories", default="", help="comma list for manifest categories")
    b.add_argument("--app-id", help="manifest id")
    b.add_argument("--manifest-extra", action="append", default=[],
                   help="extra manifest KEY=JSON_VALUE entry; may be repeated")
    b.add_argument("--head-meta", action="append", default=[],
                   help="extra <meta name=...> KEY=VALUE entry; may be repeated")
    b.add_argument("--windows-tiles", action="store_true",
                   help="also emit Windows tile PNGs and browserconfig.xml")
    b.add_argument("--tile-color", help="Windows tile background color (defaults to --theme)")
    b.add_argument("--electron-radius", type=float, default=0.0,
                   help="round electron icon corners, fraction of side (e.g. 0.18)")
    b.add_argument("--tray-ts", action="store_true", help="also emit trayIcon.ts data-url module")
    b.add_argument("--tray-svg", help="semantic foreground SVG for tray/menu-bar output")
    b.add_argument("--tray-template-mode", default="auto",
                   choices=["auto", "alpha", "contrast"],
                   help="macOS template extraction mode")
    b.add_argument("--color-scheme", default="light", choices=["light", "dark"])
    b.add_argument("--no-optimize", action="store_true",
                   help="skip lossless PNG re-packing")
    b.set_defaults(func=_cmd_build)

    r = sub.add_parser("review", help="render static proof and a target-aware Review Lab")
    r.add_argument("master", nargs="?", help="SVG source (optional with --config)")
    r.add_argument("--config", help="load brief, source, targets, transforms, and prior scores")
    r.add_argument("--out", default="review.png")
    r.add_argument("--html", help="also write a self-contained interactive HTML review")
    r.add_argument("--name", help="project name override")
    r.add_argument("--targets", help="target override: web,pwa,tauri,electron,tray,all")
    r.add_argument("--theme", help="theme color override")
    r.add_argument("--bg", help="maskable and flattened background color override")
    r.add_argument("--electron-radius", type=float, help="Electron corner radius override")
    r.add_argument("--tray-svg", help="semantic tray/menu-bar SVG override")
    r.add_argument("--tray-template-mode", choices=["auto", "alpha", "contrast"],
                   help="macOS template extraction override")
    r.add_argument("--color-scheme", choices=["light", "dark"],
                   help="static review sheet SVG color scheme")
    r.add_argument("--receipt-template", metavar="JSON",
                   help="also write an unscored receipt bound to this source and contract")
    r.add_argument("--json", action="store_true", help=JSON_HELP)
    r.set_defaults(func=_cmd_review)

    cmp = sub.add_parser("compare", help="bake-off: compare candidate SVGs side by side")
    cmp.add_argument("candidates", nargs="+", help="two or more master SVG paths")
    cmp.add_argument("--out", default="compare.png")
    cmp.set_defaults(func=_cmd_compare)

    c = sub.add_parser("check", help="run automated QA warnings")
    c.add_argument("master")
    c.add_argument("--no-maskable-audit", action="store_true",
                   help="skip the maskable safe-zone detail audit")
    c.add_argument("--bg", default="#ffffff",
                   help="background used by the exact maskable asset audit")
    c.add_argument("--tray-svg",
                   help="also audit the macOS template derived from this tray source")
    c.add_argument("--tray-template-mode", choices=["auto", "alpha", "contrast"],
                   default="auto", help="extraction mode used by the tray audit")
    c.add_argument("--json", action="store_true", help=JSON_HELP)
    c.set_defaults(func=_cmd_check)

    ld = sub.add_parser(
        "ladder",
        help="audit the detail ladder: does the big icon stay the same mark as the small one?",
    )
    ld.add_argument("master")
    ld.add_argument("--sheet", help="also write the visual ladder proof sheet here")
    ld.add_argument("--size", type=int, default=_LADDER.COMPARE_SIZE,
                    help="pixel size every rung is rendered at before comparison")
    ld.add_argument("--color-scheme", choices=["light", "dark", "no-preference"],
                    default="light")
    ld.add_argument("--containment", type=float, default=_LADDER.CONTAINMENT_FLOOR,
                    help="minimum share of a rung that must sit inside the rung above it")
    ld.add_argument("--iou", type=float, default=_LADDER.IOU_FLOOR,
                    help="minimum silhouette overlap between adjacent rungs")
    ld.add_argument("--centroid-drift", type=float, default=_LADDER.CENTROID_DRIFT_CEILING,
                    help="maximum optical-centre movement between adjacent rungs")
    ld.add_argument("--hue-drift", type=float, default=_LADDER.HUE_DRIFT_CEILING,
                    help="maximum dominant-hue shift, in degrees, between adjacent rungs")
    ld.add_argument("--json", action="store_true", help=JSON_HELP)
    ld.set_defaults(func=_cmd_ladder)

    rn = sub.add_parser("render", help="rasterize a master SVG to exact pixel size(s)")
    rn.add_argument("master")
    rn.add_argument("--sizes", default="256", help="comma list of px sizes, e.g. 256,64,32")
    rn.add_argument("--out", default="icon-{size}.png",
                    help="output path; '{size}' is substituted, else -<size> is appended for multiple sizes")
    rn.add_argument("--bg", default="transparent",
                    help="flat backdrop CSS color, or 'transparent' to keep alpha")
    rn.add_argument("--color-scheme", default="light", choices=["light", "dark"])
    rn.set_defaults(func=_cmd_render)

    styles = sub.add_parser(
        "styles",
        help="list or render the small-size-first technique scaffolds",
    )
    style_output = styles.add_mutually_exclusive_group()
    style_output.add_argument("--json", action="store_true", help="emit catalog metadata as JSON")
    style_output.add_argument("--gallery", metavar="PNG", help="render all packaged styles as a proof matrix")
    styles.add_argument("--force", action="store_true", help="replace an existing --gallery destination")
    styles.set_defaults(func=_cmd_styles)

    n = sub.add_parser("new", help="copy a style preset to start from")
    n.add_argument("preset", choices=PRESETS)
    n.add_argument("--out", default="master.svg")
    n.add_argument("--force", action="store_true", help="replace an existing destination")
    n.set_defaults(func=_cmd_new)

    sc = sub.add_parser("shortcut",
                        help="(Windows) create a desktop/Start-menu .lnk wearing your built icon")
    sc.add_argument("--target", help="what the shortcut launches (exe/script/file)")
    sc.add_argument("--powershell-script",
                    help="shortcut helper: launch this .ps1 via powershell.exe with safe default flags")
    sc.add_argument("--name", required=True, help="shortcut display name (CJK ok); '.lnk' is appended")
    sc.add_argument("--icon", default="", help="path to icon.ico to apply")
    sc.add_argument("--args", dest="args_line", default="", help="arguments passed to --target")
    sc.add_argument("--workdir", default="", help="working directory ('Start in')")
    sc.add_argument("--desc", default="", help="hover description")
    sc.add_argument("--out", default="desktop", help="desktop | startmenu | <directory>")
    sc.add_argument("--verify", action="store_true",
                    help="read back TargetPath/Arguments/WorkingDirectory/IconLocation after creation")
    sc.add_argument(
        "--content-address-icon", action="store_true",
        help="copy --icon to a SHA-256-named alias and imply --verify (avoids stale Shell pixels)",
    )
    sc.set_defaults(func=_cmd_shortcut)

    ca = sub.add_parser("case", help="casebook: record shipped designs, surface what to evolve")
    ca_sub = ca.add_subparsers(dest="case_cmd", required=True)
    from .casebook import CASE_STATUSES, default_casebook_dir
    default_dir = str(default_casebook_dir())

    cn = ca_sub.add_parser("new", help="record a shipped icon as a structured case file")
    cn.add_argument("--slug", required=True, help="short kebab-case id, e.g. tgs-planning-site")
    cn.add_argument("--project", default="", help="what the icon was for")
    cn.add_argument("--targets", default="", help="targets built, e.g. web,pwa,tray")
    cn.add_argument("--essence", default="", help="the brief's one-word essence")
    cn.add_argument("--style", default="", help="style family used (gradient-glow, flat-geometric, ...)")
    cn.add_argument("--device", default="", help="the signature device chosen")
    cn.add_argument("--device-family", default="", help="normalized device family")
    cn.add_argument("--device-detail", default="", help="specific device execution")
    cn.add_argument("--concept-lens", default="", help="winning concept lens")
    cn.add_argument("--cliche", default="", help="the category cliche(s) deliberately avoided")
    cn.add_argument("--status", default="shipped", choices=CASE_STATUSES)
    cn.add_argument("--first", default="", help='first-pass rubric scores, e.g. "legibility=3 distinctiveness=4"')
    cn.add_argument("--final", default="", help="final rubric scores, same format")
    cn.add_argument("--iterations", type=int, default=1, help="review passes needed to ship")
    cn.add_argument("--summary", default="", help="one paragraph: brief, winning concept, why")
    cn.add_argument("--lesson", action="append", default=[],
                    help="a reusable lesson learned; may be repeated")
    cn.add_argument("--date", default="", help="override date (YYYY-MM-DD), defaults to today")
    cn.add_argument("--dir", default=default_dir)
    cn.set_defaults(func=_cmd_case_new)

    cs = ca_sub.add_parser("stats", help="aggregate the casebook: weakest axis, house cliches, undistilled lessons")
    cs.add_argument("--dir", default=default_dir)
    cs.set_defaults(func=_cmd_case_stats)

    cl = ca_sub.add_parser("list", help="list recorded cases")
    cl.add_argument("--dir", default=default_dir)
    cl.set_defaults(func=_cmd_case_list)

    lint = ca_sub.add_parser("lint", help="strictly validate case metadata and taxonomy")
    lint.add_argument("--dir", default=default_dir)
    lint.add_argument("--strict", action="store_true", help="treat migration warnings as failures")
    lint.set_defaults(func=_cmd_case_lint)

    atlas = ca_sub.add_parser("atlas", help="write a self-contained visual casebook report")
    atlas.add_argument("--dir", default=default_dir)
    atlas.add_argument("--out", default="case-atlas.html")
    atlas.set_defaults(func=_cmd_case_atlas)

    docs = sub.add_parser(
        "docs",
        help="list, print, or export the packaged reference documents",
    )
    docs.add_argument("name", nargs="?", help="document name, e.g. DESIGN_PLAYBOOK")
    docs_mode = docs.add_mutually_exclusive_group()
    docs_mode.add_argument(
        "--out",
        help="export documents (and the images they reference) into this directory",
    )
    docs_mode.add_argument(
        "--path", action="store_true",
        help="print the resolved file path only, so you can Read the document",
    )
    docs_mode.add_argument(
        "--json", action="store_true", help="list documents as JSON (no NAME)",
    )
    docs.set_defaults(func=_cmd_docs)

    skill = sub.add_parser(
        "skill",
        help="install or print the packaged IconFlow Agent Skill",
    )
    skill_sub = skill.add_subparsers(dest="skill_cmd", required=True)
    skill_install = skill_sub.add_parser(
        "install",
        help="copy the skill into the agent skill discovery roots (no checkout needed)",
    )
    skill_scope = skill_install.add_mutually_exclusive_group()
    skill_scope.add_argument(
        "--dir", action="append", default=[],
        help="skills root to install into (an `iconflow/` directory is created "
             "inside it); repeatable. Default: the user-level roots",
    )
    skill_scope.add_argument(
        "--project", action="store_true",
        help="install into this project's own skills roots instead of the user's",
    )
    skill_install.set_defaults(func=_cmd_skill)
    skill_print = skill_sub.add_parser("print", help="write SKILL.md to stdout")
    skill_print.set_defaults(func=_cmd_skill, dir=[], project=False)
    skill_path = skill_sub.add_parser("path", help="print the packaged SKILL.md path")
    skill_path.set_defaults(func=_cmd_skill, dir=[], project=False)

    lic = sub.add_parser(
        "license",
        help="who owns what: your icons, the tool, the methodology, the artwork",
    )
    lic.add_argument("--json", action="store_true", help="emit the summary as JSON")
    lic.set_defaults(func=_cmd_license)

    s = sub.add_parser("setup", help="install the Playwright Chromium runtime")
    s.set_defaults(func=_cmd_setup)

    doctor = sub.add_parser("doctor", help="diagnose package resources and Chromium readiness")
    doctor.add_argument("--config", help="also validate this project configuration")
    doctor.add_argument("--no-browser", action="store_true", help="skip launching Chromium")
    doctor.add_argument("--json", action="store_true", help=JSON_HELP)
    doctor.set_defaults(func=_cmd_doctor)

    demo = sub.add_parser(
        "demo",
        help="materialize the packaged, reviewed brand family and run doctor → check → review → ship",
    )
    demo.add_argument("--out", required=True, help="directory to create (must not exist unless --force)")
    demo.add_argument("--setup", action="store_true", help="run `iconflow setup` first (network)")
    demo.add_argument("--force", action="store_true", help="reuse an existing --out directory")
    demo.add_argument("--json", action="store_true", help=JSON_HELP)
    demo.set_defaults(func=_cmd_demo)
    return p



def _execute(args) -> Report | int:
    """Run one parsed command, translating stray exceptions into exit 2.

    Contract commands always come back as a :class:`Report` so ``--json`` (and
    ``demo``, which runs them in-process) can read the structured outcome.
    """
    report = Report(args.cmd) if args.cmd in JSON_COMMANDS else None
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"iconflow {args.cmd}: file not found: {exc.filename or exc}", file=sys.stderr)
        if report is None:
            return 2
        report.error("file-not-found", f"file not found: {exc.filename or exc}")
    except PermissionError as exc:
        print(f"iconflow {args.cmd}: permission denied: {exc.filename or exc}", file=sys.stderr)
        if report is None:
            return 2
        report.error("permission-denied", f"permission denied: {exc.filename or exc}")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"iconflow {args.cmd}: {exc}", file=sys.stderr)
        if report is None:
            return 2
        report.error("config" if isinstance(exc, ValueError) else "runtime", str(exc))
    return report


def main(argv=None) -> int:
    # Windows consoles default to a legacy codepage; CJK shortcut names then crash
    # on print. Force UTF-8 so non-ASCII output never raises UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    raw = list(sys.argv[1:] if argv is None else argv)
    wants_json = "--json" in raw
    intended = next((token for token in raw if not token.startswith("-")), None)
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        # argparse already printed usage to stderr. Under --json the contract
        # still promises exactly one envelope on stdout.
        if wants_json and exc.code not in (0, None) and intended in JSON_COMMANDS:
            report = Report(intended)
            report.error("usage", "invalid arguments; see the usage message on stderr")
            print(json.dumps(report.envelope(), ensure_ascii=False, indent=2))
            return 2
        raise
    json_mode = args.cmd in JSON_COMMANDS and bool(getattr(args, "json", False))
    stdout = sys.stdout
    # In JSON mode every human line moves to stderr so stdout is exactly one object.
    with contextlib.redirect_stdout(sys.stderr) if json_mode else contextlib.nullcontext():
        result = _execute(args)
    if isinstance(result, Report):
        if json_mode:
            print(json.dumps(result.envelope(), ensure_ascii=False, indent=2), file=stdout)
        return result.exit_code
    return result
