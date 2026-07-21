"""Command-line interface.

    python -m iconflow build  master.svg --out ./out --targets web,tauri,tray
    python -m iconflow review --config iconflow.toml --html review.html
    python -m iconflow check  master.svg
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
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.resources
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PRESETS = ("gradient-glow", "flat-geometric", "line-mark", "mascot")


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
    """Return a packaged resource path/Traversable.

    Resolution order, most reliable first:

    1. The on-disk source tree next to this package — an editable install
       (``pip install -e .``), a plain checkout, or CI. A modern *strict*
       editable finder does not expose the ``package-dir``-remapped resource
       subpackages to ``importlib.resources`` (nor put the repo root on
       ``sys.path`` for the namespace fallback), so the checkout layout is the
       dependable source there.
    2. The packaged ``iconflow.resources.*`` subpackage — a real wheel install,
       where the source tree is absent so step 1 is skipped.
    3. The top-level namespace directories — legacy source execution.
    """

    subdir = {
        "presets": ("templates", "presets"),
        "templates": ("templates",),
        "docs": ("docs",),
    }.get(package)
    if subdir is not None:
        source = Path(__file__).resolve().parent.parent.joinpath(*subdir, name)
        if source.is_file():
            return source
    try:
        root = importlib.resources.files(f"iconflow.resources.{package}")
    except ModuleNotFoundError:
        source_package = (
            "templates.presets" if package == "presets"
            else "templates" if package == "templates"
            else "docs"
        )
        root = importlib.resources.files(source_package)
    return root.joinpath(name)


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


def _cmd_ship(a) -> int:
    """Run the fail-closed quality gate, then delegate to the low-level build."""

    from .build import build
    from .casebook import parse_scores
    from .config import (
        ConfigError, load_config, load_review_receipt, svg_sha256,
        validate_ship_scores,
    )
    from .qa import check

    try:
        config = load_config(a.config)
        master = config.master_path
        if not master.is_file():
            raise ConfigError(f"master SVG not found: {master}")
        receipt = load_review_receipt(a.review, config) if a.review else None
        if receipt:
            scores = receipt.scores
        else:
            scores = parse_scores(a.scores) if a.scores is not None else config.review_scores
            validate_ship_scores(scores)
            if config.review_status not in {"approved", "shipped"}:
                raise ConfigError(
                    "review.status must be 'approved' (or provide a ready Review Lab receipt)"
                )
            if not config.review_source_sha256:
                raise ConfigError(
                    "approved config fallback requires review.source_sha256 "
                    "(or provide a ready Review Lab receipt)"
                )
            if config.review_source_sha256 != svg_sha256(master):
                raise ConfigError(
                    "approved config review is stale: review.source_sha256 does not "
                    "match the current master SVG"
                )
    except (ConfigError, ValueError) as exc:
        print(f"iconflow ship: {exc}", file=sys.stderr)
        return 2

    try:
        warnings = check(
            master,
            maskable=bool({"web", "pwa"} & set(config.targets)),
            maskable_bg=config.background_color,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"iconflow ship: QA could not run: {exc}", file=sys.stderr)
        return 2
    if warnings:
        print(f"SHIP BLOCKED — automated check found {len(warnings)} warning(s):", file=sys.stderr)
        for warning in warnings:
            print(f"  ! {warning}", file=sys.stderr)
        print("Fix the warnings, regenerate review.png, and rescore before shipping.", file=sys.stderr)
        return 1

    try:
        produced = build(
            master,
            config.output_path,
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
        return 2
    print(f"SHIP PASSED — built {len(produced)} files into {config.output_path}:")
    for path in produced:
        print(f"  {path}")
    print(f"Review scores: " + ", ".join(f"{axis}={scores[axis]}" for axis in scores))
    if receipt:
        print(f"Review receipt: {receipt.source}")
    print(f"Record the shipped case in: {config.casebook_path}")
    return 0


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


def _cmd_review(a) -> int:
    from .build import normalize_targets
    from .config import ConfigError, load_config
    from .qa import check
    from .review import ReviewOptions, contact_sheet, interactive_review

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
        return 2

    out = contact_sheet(
        master, a.out, background_color=background, color_scheme=color_scheme,
    )
    print(f"Review sheet -> {out}")
    print("Open it (or Read it as an image) and score against docs/REVIEW_CHECKLIST.md.")
    if a.html:
        html_out = interactive_review(master, a.html, options=options)
        print(f"Review Lab -> {html_out}")
        print("Export its JSON receipt and pass it to `iconflow ship --review <receipt>`.")
    if warnings:
        print(f"Review includes {len(warnings)} automated warning(s); ship remains blocked.")
    return 0


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


def _cmd_check(a) -> int:
    from .qa import check
    warnings = check(
        a.master, maskable=not a.no_maskable_audit, maskable_bg=a.bg,
    )
    if not warnings:
        print("OK — no automated warnings. Still do the visual review.")
        return 0
    print(f"{len(warnings)} warning(s):")
    for w in warnings:
        print(f"  ! {w}")
    return 1


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
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(src.read_bytes())
    print(f"Copied {a.preset} preset -> {destination}")
    print("Now edit it following docs/DESIGN_PLAYBOOK.md, then `review` and `build`.")
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
    return subprocess.call([sys.executable, "-m", "playwright", "install", "chromium"])


def _cmd_doctor(a) -> int:
    """Diagnose install/runtime readiness without mutating the environment."""

    failures = 0

    def report(ok: bool | None, label: str, detail: str = "") -> None:
        nonlocal failures
        state = "PASS" if ok is True else "SKIP" if ok is None else "FAIL"
        if ok is False:
            failures += 1
        suffix = f" — {detail}" if detail else ""
        print(f"{state:<4} {label}{suffix}")

    report(sys.version_info >= (3, 10), "Python", sys.version.split()[0])
    try:
        import PIL
        pillow_version = getattr(PIL, "__version__", "unknown")
        report(
            _version_at_least(pillow_version, (10, 0)),
            "Pillow",
            f"{pillow_version} (requires >=10.0)",
        )
    except ImportError as exc:
        report(False, "Pillow", str(exc))
    try:
        import playwright  # noqa: F401
        playwright_version = importlib.metadata.version("playwright")
        report(
            _version_at_least(playwright_version, (1, 40)),
            "Playwright package",
            f"{playwright_version} (requires >=1.40)",
        )
    except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
        report(False, "Playwright package", str(exc))

    missing_resources: list[str] = []
    for preset in PRESETS:
        try:
            if not _resource("presets", f"{preset}.svg").is_file():
                missing_resources.append(f"presets/{preset}.svg")
        except (ModuleNotFoundError, TypeError):
            missing_resources.append(f"presets/{preset}.svg")
    for template in ("master.svg", "grid-overlay.svg"):
        try:
            if not _resource("templates", template).is_file():
                missing_resources.append(f"templates/{template}")
        except (ModuleNotFoundError, TypeError):
            missing_resources.append(f"templates/{template}")
    for doc in ("DESIGN_PLAYBOOK.md", "REVIEW_CHECKLIST.md", "OUTPUT_TARGETS.md"):
        try:
            if not _resource("docs", doc).is_file():
                missing_resources.append(f"docs/{doc}")
        except (ModuleNotFoundError, TypeError):
            missing_resources.append(f"docs/{doc}")
    report(not missing_resources, "Packaged resources",
           ", ".join(missing_resources) if missing_resources
           else f"{len(PRESETS)} presets + base templates + docs")

    config = None
    config_path = Path(a.config) if a.config else Path("iconflow.toml")
    if config_path.exists() or a.config:
        try:
            from .config import load_config, svg_sha256
            config = load_config(config_path)
            report(True, "Project config", str(config.source))
            master_exists = config.master_path.is_file()
            report(master_exists, "Master SVG", str(config.master_path))
            if config.tray_svg_path:
                report(
                    config.tray_svg_path.is_file(),
                    "Semantic tray SVG",
                    str(config.tray_svg_path),
                )
            if config.review_source_sha256 and master_exists:
                current_digest = svg_sha256(config.master_path)
                report(
                    config.review_source_sha256 == current_digest,
                    "Approved source hash",
                    "matches current master" if config.review_source_sha256 == current_digest
                    else "stale review.source_sha256",
                )
            else:
                report(None, "Approved source hash", "no bound approved fallback")
            output_probe = config.output_path
            while not output_probe.exists() and output_probe != output_probe.parent:
                output_probe = output_probe.parent
            report(
                output_probe.is_dir() and os.access(output_probe, os.W_OK),
                "Writable build output",
                str(config.output_path),
            )
        except (OSError, ValueError) as exc:
            report(False, "Project config", str(exc))
    else:
        report(None, "Project config", "no iconflow.toml in this directory")

    from .casebook import default_casebook_dir
    casebook = (
        config.casebook_path if config is not None
        else default_casebook_dir().expanduser().resolve(strict=False)
    )
    probe = casebook
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    report(probe.is_dir() and os.access(probe, os.W_OK), "Writable casebook", str(casebook))

    if a.no_browser:
        report(None, "Chromium runtime", "skipped by --no-browser")
    else:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as manager:
                browser = manager.chromium.launch(headless=True)
                browser.close()
            report(True, "Chromium runtime")
        except Exception as exc:  # Playwright exposes several runtime-specific exceptions
            report(False, "Chromium runtime", f"{exc} (run `iconflow setup`)")

    if failures:
        print(f"Doctor found {failures} blocking issue(s).", file=sys.stderr)
        return 1
    print("IconFlow is ready.")
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
    ship_review = ship.add_mutually_exclusive_group()
    ship_review.add_argument(
        "--review",
        help="Review Lab JSON receipt; verifies the current source and target set",
    )
    ship_review.add_argument(
        "--scores",
        help="six-axis override for an approved config, e.g. 'legibility=4 ...'",
    )
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
    c.set_defaults(func=_cmd_check)

    rn = sub.add_parser("render", help="rasterize a master SVG to exact pixel size(s)")
    rn.add_argument("master")
    rn.add_argument("--sizes", default="256", help="comma list of px sizes, e.g. 256,64,32")
    rn.add_argument("--out", default="icon-{size}.png",
                    help="output path; '{size}' is substituted, else -<size> is appended for multiple sizes")
    rn.add_argument("--bg", default="transparent",
                    help="flat backdrop CSS color, or 'transparent' to keep alpha")
    rn.add_argument("--color-scheme", default="light", choices=["light", "dark"])
    rn.set_defaults(func=_cmd_render)

    n = sub.add_parser("new", help="copy a style preset to start from")
    n.add_argument("preset", choices=PRESETS)
    n.add_argument("--out", default="master.svg")
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

    s = sub.add_parser("setup", help="install the Playwright Chromium runtime")
    s.set_defaults(func=_cmd_setup)

    doctor = sub.add_parser("doctor", help="diagnose package resources and Chromium readiness")
    doctor.add_argument("--config", help="also validate this project configuration")
    doctor.add_argument("--no-browser", action="store_true", help="skip launching Chromium")
    doctor.set_defaults(func=_cmd_doctor)
    return p


def main(argv=None) -> int:
    # Windows consoles default to a legacy codepage; CJK shortcut names then crash
    # on print. Force UTF-8 so non-ASCII output never raises UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"iconflow {args.cmd}: file not found: {exc.filename or exc}", file=sys.stderr)
        return 2
    except PermissionError as exc:
        print(f"iconflow {args.cmd}: permission denied: {exc.filename or exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"iconflow {args.cmd}: {exc}", file=sys.stderr)
        return 2
