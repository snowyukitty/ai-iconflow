"""Project configuration for IconFlow's brief-to-ship workflow.

``iconflow.toml`` is deliberately small and human-editable.  Relative paths are
resolved from the configuration file, so the same project behaves consistently
whether IconFlow is invoked from the project root, CI, or another directory.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .casebook import AXES, normalize_detail, normalize_taxonomy, validate_scores

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised by the Python 3.10 CI job
    import tomli as tomllib


SCHEMA_VERSION = 1
CONFIG_FILENAME = "iconflow.toml"
TARGETS = ("web", "pwa", "tauri", "electron", "tray")
REVIEW_STATUSES = ("pending", "reviewed", "approved", "shipped", "archived")


class ConfigError(ValueError):
    """Raised when an IconFlow project configuration is invalid."""


@dataclass(frozen=True)
class ReviewReceipt:
    """Validated human-review decision bound to one SVG and target set."""

    source: Path
    source_sha256: str
    project: str
    targets: tuple[str, ...]
    scores: dict[str, int]
    notes: str


@dataclass
class IconFlowConfig:
    """Normalized project configuration.

    ``source`` is not serialized.  It anchors relative master/output/casebook
    paths and makes the configuration portable.
    """

    source: Path
    schema_version: int = SCHEMA_VERSION
    name: str = "App"
    master: str = "master.svg"
    output: str = "icon-out"
    casebook: str = "casebook"

    app_intent: str = ""
    user_job: str = ""
    essence: str = ""
    personality: list[str] = field(default_factory=list)

    palette: list[str] = field(default_factory=list)
    cliches: list[str] = field(default_factory=list)
    signature_device: str = ""
    device_family: str = ""
    device_detail: str = ""
    concept_lens: str = ""

    targets: list[str] = field(default_factory=lambda: ["web"])
    theme_color: str = "#0b0d12"
    background_color: str = "#ffffff"
    electron_radius: float = 0.0
    tray_ts: bool = False
    tray_svg: str = ""
    tray_template_mode: str = "auto"
    color_scheme: str = "light"
    optimize_png: bool = True

    review_status: str = "pending"
    review_source_sha256: str = ""
    review_scores: dict[str, int] = field(default_factory=dict)
    review_notes: str = ""

    def resolve(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.source.parent / path
        return path.resolve(strict=False)

    @property
    def master_path(self) -> Path:
        return self.resolve(self.master)

    @property
    def output_path(self) -> Path:
        return self.resolve(self.output)

    @property
    def casebook_path(self) -> Path:
        return self.resolve(self.casebook)

    @property
    def tray_svg_path(self) -> Path | None:
        return self.resolve(self.tray_svg) if self.tray_svg else None


def _table(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise ConfigError(f"[{key}] must be a TOML table")
    return value


def _string(table: Mapping[str, Any], key: str, default: str = "") -> str:
    value = table.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"{key} must be a string")
    return value.strip()


def _strings(table: Mapping[str, Any], key: str) -> list[str]:
    value = table.get(key, [])
    # Accept comma-separated strings from early hand-written configs while
    # always writing the canonical TOML-array representation.
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be an array of strings")
    return [item.strip() for item in value if item.strip()]


def _boolean(table: Mapping[str, Any], key: str, default: bool) -> bool:
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be true or false")
    return value


def _number(table: Mapping[str, Any], key: str, default: float) -> float:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{key} must be a number")
    return float(value)


def _normalize_targets(values: list[str]) -> list[str]:
    normalized = [value.strip().lower() for value in values if value.strip()]
    if not normalized:
        raise ConfigError("build.targets must contain at least one target")
    if "all" in normalized:
        if len(set(normalized)) != 1:
            raise ConfigError("build.targets 'all' cannot be combined with other targets")
        return list(TARGETS)
    unknown = sorted(set(normalized) - set(TARGETS))
    if unknown:
        raise ConfigError(
            f"unknown build target(s): {', '.join(unknown)}. "
            f"Choose from: {', '.join(TARGETS)}, all"
        )
    return [target for target in TARGETS if target in normalized]


def load_config(path: str | Path = CONFIG_FILENAME) -> IconFlowConfig:
    """Load and normalize an ``iconflow.toml`` file."""

    source = Path(path).expanduser().resolve(strict=False)
    try:
        raw = source.read_bytes()
    except FileNotFoundError as exc:
        raise ConfigError(
            f"configuration not found: {source}. Run `iconflow init` first."
        ) from exc
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"invalid TOML in {source}: {exc}") from exc

    version = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, bool) or not isinstance(version, int):
        raise ConfigError("schema_version must be an integer")
    if version != SCHEMA_VERSION:
        raise ConfigError(
            f"unsupported schema_version {version}; this IconFlow supports {SCHEMA_VERSION}"
        )

    project = _table(data, "project")
    brief = _table(data, "brief")
    design = _table(data, "design")
    build = _table(data, "build")
    review = _table(data, "review")

    scores_value = review.get("scores", {})
    if not isinstance(scores_value, Mapping):
        raise ConfigError("review.scores must be a TOML table")
    scores: dict[str, int] = {}
    for axis, value in scores_value.items():
        if not isinstance(axis, str) or isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError("review.scores values must be integers from 1 to 5")
        scores[axis.strip().lower()] = value
    try:
        validate_scores(scores)
    except ValueError as exc:
        raise ConfigError(f"invalid review.scores: {exc}") from exc

    status = _string(review, "status", "pending").lower()
    if status not in REVIEW_STATUSES:
        raise ConfigError(
            f"review.status must be one of: {', '.join(REVIEW_STATUSES)}"
        )
    review_digest = _string(review, "source_sha256").lower()
    if review_digest and not _is_sha256(review_digest):
        raise ConfigError("review.source_sha256 must be a full SHA-256 hex digest")
    color_scheme = _string(build, "color_scheme", "light").lower()
    if color_scheme not in ("light", "dark"):
        raise ConfigError("build.color_scheme must be 'light' or 'dark'")
    radius = _number(build, "electron_radius", 0.0)
    if not 0.0 <= radius <= 0.5:
        raise ConfigError("build.electron_radius must be between 0 and 0.5")
    tray_template_mode = _string(build, "tray_template_mode", "auto").lower()
    if tray_template_mode not in ("auto", "alpha", "contrast"):
        raise ConfigError("build.tray_template_mode must be 'auto', 'alpha', or 'contrast'")
    theme_color = _string(build, "theme_color", "#0b0d12")
    background_color = _string(build, "background_color", "#ffffff")
    from . import assemble
    try:
        assemble.opaque_color(theme_color, "build.theme_color")
        assemble.opaque_color(background_color, "build.background_color")
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    name = _string(project, "name", "App")
    master = _string(project, "master", "master.svg")
    output = _string(project, "output", "icon-out")
    casebook = _string(project, "casebook", "casebook")
    if not name:
        raise ConfigError("project.name cannot be empty")
    if not master:
        raise ConfigError("project.master cannot be empty")
    if not output:
        raise ConfigError("project.output cannot be empty")
    if not casebook:
        raise ConfigError("project.casebook cannot be empty")

    return IconFlowConfig(
        source=source,
        schema_version=version,
        name=name,
        master=master,
        output=output,
        casebook=casebook,
        app_intent=_string(brief, "app_intent"),
        user_job=_string(brief, "user_job"),
        essence=_string(brief, "essence"),
        personality=_strings(brief, "personality"),
        palette=_strings(design, "palette"),
        cliches=_strings(design, "cliches"),
        signature_device=normalize_detail(_string(design, "signature_device")),
        device_family=normalize_taxonomy(_string(design, "device_family")),
        device_detail=normalize_detail(_string(design, "device_detail")),
        concept_lens=normalize_taxonomy(_string(design, "concept_lens")),
        targets=_normalize_targets(_strings(build, "targets") or ["web"]),
        theme_color=theme_color,
        background_color=background_color,
        electron_radius=radius,
        tray_ts=_boolean(build, "tray_ts", False),
        tray_svg=_string(build, "tray_svg"),
        tray_template_mode=tray_template_mode,
        color_scheme=color_scheme,
        optimize_png=_boolean(build, "optimize_png", True),
        review_status=status,
        review_source_sha256=review_digest,
        review_scores=scores,
        review_notes=_string(review, "notes"),
    )


def validate_ship_scores(scores: Mapping[str, int]) -> None:
    """Enforce the visual-review gate used by the high-level ship command."""

    normalized = dict(scores)
    validate_scores(normalized)
    missing = [axis for axis in AXES if axis not in normalized]
    if missing:
        raise ConfigError(
            "review.scores is incomplete; add: " + ", ".join(missing)
        )
    below = [f"{axis}={normalized[axis]}" for axis in AXES if normalized[axis] < 4]
    if below:
        raise ConfigError(
            "review gate failed (every axis must be >=4): " + ", ".join(below)
        )


def load_review_receipt(
    path: str | Path, config: IconFlowConfig
) -> ReviewReceipt:
    """Load a Review Lab JSON receipt and bind it to the current build.

    A score file is useful only if it proves which editable source and target
    family a person actually inspected.  This validator therefore fails closed
    on stale hashes, mismatched project/targets, warnings, or partial scores.
    """

    source = Path(path).expanduser().resolve(strict=False)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"review receipt not found: {source}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"invalid review receipt {source}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ConfigError("review receipt must be a JSON object")
    schema = value.get("schema")
    if isinstance(schema, bool) or schema != 1:
        raise ConfigError("review receipt schema must be 1")

    digest = value.get("source_sha256")
    if not isinstance(digest, str) or not _is_sha256(digest):
        raise ConfigError("review receipt source_sha256 must be a full SHA-256 hex digest")
    current = svg_sha256(config.master_path)
    if digest.lower() != current:
        raise ConfigError(
            "review receipt is stale: source_sha256 does not match the current master SVG"
        )

    project = value.get("project")
    if not isinstance(project, str) or project != config.name:
        raise ConfigError(
            f"review receipt project mismatch: expected {config.name!r}, got {project!r}"
        )
    raw_targets = value.get("targets")
    if not isinstance(raw_targets, list) or any(
        not isinstance(target, str) for target in raw_targets
    ):
        raise ConfigError("review receipt targets must be an array of strings")
    try:
        targets = _normalize_targets(raw_targets)
    except ConfigError as exc:
        raise ConfigError(f"invalid review receipt targets: {exc}") from exc
    if targets != config.targets:
        raise ConfigError(
            "review receipt target mismatch: expected "
            + ",".join(config.targets)
            + "; got "
            + ",".join(targets)
        )

    actual_build = value.get("build")
    if not isinstance(actual_build, Mapping):
        raise ConfigError("review receipt build must be an object")
    expected_build = review_build_contract(
        theme_color=config.theme_color,
        background_color=config.background_color,
        electron_radius=config.electron_radius,
        tray_template_mode=config.tray_template_mode,
        color_scheme=config.color_scheme,
        tray_source_sha256=(
            svg_sha256(config.tray_svg_path) if config.tray_svg_path else None
        ),
    )
    if dict(actual_build) != expected_build:
        raise ConfigError(
            "review receipt build contract mismatch; regenerate after changing "
            "colors, Electron radius, color scheme, or tray source/mode"
        )

    warnings = value.get("warnings")
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise ConfigError("review receipt warnings must be an array of strings")
    if warnings:
        raise ConfigError("review receipt contains automated warnings; regenerate after fixing them")
    if value.get("status") != "ready":
        raise ConfigError("review receipt status must be 'ready'")

    raw_scores = value.get("scores")
    if not isinstance(raw_scores, Mapping):
        raise ConfigError("review receipt scores must be an object")
    scores: dict[str, int] = {}
    for axis, score in raw_scores.items():
        if not isinstance(axis, str) or isinstance(score, bool) or not isinstance(score, int):
            raise ConfigError("review receipt scores must be integer axis values")
        scores[axis.strip().lower()] = score
    validate_ship_scores(scores)
    notes = value.get("notes", "")
    if not isinstance(notes, str):
        raise ConfigError("review receipt notes must be a string")
    return ReviewReceipt(
        source=source,
        source_sha256=current,
        project=project,
        targets=tuple(targets),
        scores=scores,
        notes=notes.strip(),
    )


def _is_sha256(value: str) -> bool:
    """Return whether ``value`` is exactly one lowercase/uppercase SHA-256."""

    return len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def svg_sha256(path: str | Path) -> str:
    """Hash the normalized SVG text used by render, review, and ship."""

    from .rasterize import load_svg
    return hashlib.sha256(load_svg(path).encode("utf-8")).hexdigest()


def review_build_contract(
    *, theme_color: str, background_color: str, electron_radius: float,
    tray_template_mode: str, color_scheme: str,
    tray_source_sha256: str | None,
) -> dict[str, object]:
    """Return the canonical visual-transform contract stored in a receipt."""

    from . import assemble

    def canonical_color(value: str, label: str) -> str:
        try:
            red, green, blue, _ = assemble.opaque_color(value, label)
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        return f"#{red:02X}{green:02X}{blue:02X}"

    try:
        radius = assemble.validate_radius(electron_radius)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    if tray_template_mode not in {"auto", "alpha", "contrast"}:
        raise ConfigError("tray template mode must be 'auto', 'alpha', or 'contrast'")
    if color_scheme not in {"light", "dark"}:
        raise ConfigError("color scheme must be 'light' or 'dark'")
    if tray_source_sha256 is not None and not _is_sha256(tray_source_sha256):
        raise ConfigError("tray source hash must be a full SHA-256 hex digest")
    return {
        "theme_color": canonical_color(theme_color, "theme color"),
        "background_color": canonical_color(background_color, "background color"),
        "electron_radius": radius,
        "tray_template_mode": tray_template_mode,
        "color_scheme": color_scheme,
        "tray_source_sha256": tray_source_sha256.lower() if tray_source_sha256 else None,
    }


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_strings(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def config_text(config: IconFlowConfig) -> str:
    """Serialize the stable, intentionally-commented IconFlow schema."""

    score_items = ", ".join(
        f"{axis} = {config.review_scores[axis]}"
        for axis in AXES if axis in config.review_scores
    )
    return f'''# IconFlow project brief and deterministic build contract.
# Relative paths are resolved from this file.
schema_version = {SCHEMA_VERSION}

[project]
name = {_toml_string(config.name)}
master = {_toml_string(config.master)}
output = {_toml_string(config.output)}
casebook = {_toml_string(config.casebook)}

[brief]
app_intent = {_toml_string(config.app_intent)}
user_job = {_toml_string(config.user_job)}
essence = {_toml_string(config.essence)}
personality = {_toml_strings(config.personality)}

[design]
palette = {_toml_strings(config.palette)}
cliches = {_toml_strings(config.cliches)}
signature_device = {_toml_string(normalize_detail(config.signature_device))}
device_family = {_toml_string(normalize_taxonomy(config.device_family))}
device_detail = {_toml_string(normalize_detail(config.device_detail))}
concept_lens = {_toml_string(normalize_taxonomy(config.concept_lens))}

[build]
targets = {_toml_strings(config.targets)}
theme_color = {_toml_string(config.theme_color)}
background_color = {_toml_string(config.background_color)}
electron_radius = {config.electron_radius:g}
tray_ts = {str(config.tray_ts).lower()}
tray_svg = {_toml_string(config.tray_svg)}
tray_template_mode = {_toml_string(config.tray_template_mode)}
color_scheme = {_toml_string(config.color_scheme)}
optimize_png = {str(config.optimize_png).lower()}

[review]
status = {_toml_string(config.review_status)}
source_sha256 = {_toml_string(config.review_source_sha256)}
# Review Lab receipt is preferred. For this manual fallback, set status to
# "approved" and copy the reviewed source hash; `ship` requires every score >= 4.
scores = {{{score_items}}}
notes = {_toml_string(config.review_notes)}
'''


def write_config(config: IconFlowConfig, *, force: bool = False) -> Path:
    """Write a new project config without silently replacing existing intent."""

    path = config.source.expanduser().resolve(strict=False)
    if path.exists() and not force:
        raise ConfigError(f"configuration already exists: {path} (use --force to replace it)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config_text(config), encoding="utf-8")
    return path
