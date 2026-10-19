# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""One audit, one set of inputs, for ``check``, ``review`` and ``ship``.

Before 0.7 each command assembled its own call to :func:`iconflow.qa.check`.
``check --config`` audited the maskable icon against white while ``review``
and ``ship`` used the configured background, so one SVG and one config got
two answers. Every command now resolves an :class:`AuditInputs` the same way
and runs :func:`run_audit`; ``tests/test_audit.py`` fails if any two of them
can disagree on the same SVG and config.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .findings import Finding

#: What ``check MASTER`` audits when no project config says otherwise:
#: the web target, so the maskable icon is audited.
DEFAULT_TARGETS = ("web", "pwa")


@dataclass(frozen=True)
class AuditInputs:
    """Everything the automated gate depends on, resolved once."""

    master: Path
    targets: tuple[str, ...] = DEFAULT_TARGETS
    background_color: str = "#ffffff"
    color_scheme: str = "light"
    tray_svg: Path | None = None
    tray_template_mode: str = "auto"
    maskable_scale: float | None = None
    maskable_svg: Path | None = None
    skip_maskable: bool = False
    # The project config, only for its [neighbours] declarations.
    config: object | None = field(default=None, compare=False)

    @property
    def maskable_audited(self) -> bool:
        from .build import ADAPTIVE_TARGETS

        return not self.skip_maskable and bool(ADAPTIVE_TARGETS & set(self.targets))

    @property
    def tray_audited(self) -> bool:
        return self.tray_svg is not None and "tray" in self.targets

    def describe(self) -> dict:
        """The inputs as they appear in every ``--json`` envelope's ``outputs.audit``."""
        from .build import resolve_maskable_scale

        linked = self.maskable_svg is not None
        return {
            "targets": list(self.targets),
            "background_color": self.background_color,
            "color_scheme": self.color_scheme,
            "maskable_audit": self.maskable_audited,
            "maskable_scale": (
                resolve_maskable_scale(self.maskable_scale, linked=linked)
                if self.maskable_audited else None
            ),
            "maskable_source": str(self.maskable_svg) if linked else None,
            "tray_source": str(self.tray_svg) if self.tray_svg else None,
            "tray_template_mode": self.tray_template_mode,
            "neighbours": bool(getattr(self.config, "neighbours_declared", False)),
        }


def resolve_inputs(
    *, config=None, master: str | Path | None = None,
    targets=None, background_color: str | None = None,
    color_scheme: str | None = None, tray_svg: str | Path | None = None,
    tray_template_mode: str | None = None,
    maskable_scale: float | None = None,
    maskable_svg: str | Path | None = None,
    skip_maskable: bool = False,
) -> AuditInputs:
    """Resolve audit inputs: explicit overrides, then the config, then defaults.

    This is the only place the precedence is written down, so every command
    that takes ``--config`` audits exactly what ``ship`` would build.
    """
    from .build import normalize_targets
    from .config import ConfigError

    if master is not None:
        master_path = Path(master).expanduser().resolve(strict=False)
    elif config is not None:
        master_path = config.master_path
    else:
        raise ConfigError("provide MASTER or --config iconflow.toml")

    def path_or(value, fallback):
        if value:
            return Path(value).expanduser().resolve(strict=False)
        return fallback

    resolved_targets = (
        normalize_targets(targets) if targets
        else config.targets if config is not None
        else list(DEFAULT_TARGETS)
    )
    tray = path_or(tray_svg, config.tray_svg_path if config is not None else None)
    if tray_svg and "tray" not in resolved_targets and config is None:
        # `check MASTER --tray-svg tray.svg` asks for the tray audit by name.
        resolved_targets = normalize_targets([*resolved_targets, "tray"])
    return AuditInputs(
        master=master_path,
        targets=tuple(resolved_targets),
        background_color=background_color or (
            config.background_color if config is not None else "#ffffff"
        ),
        color_scheme=color_scheme or (config.color_scheme if config is not None else "light"),
        tray_svg=tray,
        tray_template_mode=tray_template_mode or (
            config.tray_template_mode if config is not None else "auto"
        ),
        maskable_scale=(
            maskable_scale if maskable_scale is not None
            else config.maskable_scale if config is not None else None
        ),
        maskable_svg=path_or(
            maskable_svg, config.maskable_svg_path if config is not None else None,
        ),
        skip_maskable=skip_maskable,
        config=config,
    )


@dataclass
class AuditResult:
    inputs: AuditInputs
    warnings: list[Finding]
    advisories: list[Finding]
    neighbourhood: object | None = None
    #: What the checks measured (coverage, contrast spreads, maskable share),
    #: recorded in a headless review's findings file.
    metrics: dict = field(default_factory=dict)
    #: Where each probe's pixels came from (0.9): a plan file and slot, or a
    #: render and why. Empty for an audit that measured nothing.
    frames: dict = field(default_factory=dict)
    #: The plan the audit read (its three digests), or None.
    plan: dict | None = None

    @property
    def audited(self) -> bool:
        """True when the audit measured the plan's own files for every probe that has one.

        Independent of the outcome: an audit with warnings can be ``audited``.
        It never means every output file was inspected — see ``frames``.
        """
        return self.plan is not None and any(
            origin.get("from") == "plan" for origin in self.frames.values()
        )

    def provenance(self) -> dict:
        """The record a headless review stores and ``score`` validates (schema 1)."""
        return {"schema": 1, "plan": self.plan, "audited": self.audited,
                "frames": self.frames}


def run_audit(inputs: AuditInputs, *, rasterizer=None, plan=None,
              sources=None) -> AuditResult:
    """Every automated finding for one source under one set of inputs.

    ``warnings`` gate ``ship`` (and make ``check``/``review`` exit 1);
    ``advisories`` inform and never gate. One Chromium session serves the
    whole audit.

    ``sources`` are the command's captured snapshots by role
    (:func:`iconflow.plan.capture_sources`): every probe measures those bytes,
    never a file reopened later. With a ``plan``, the probes that have a
    shipped counterpart measure the plan's files (0.9, F09) and the result
    records where every probe's pixels came from.
    """
    sources = dict(sources or {})

    def captured(role: str):
        source = sources.get(role)
        return source.text if source is not None else None

    from . import qa
    from .qa import check, neighbourhood_audit, tray_template_warnings

    def audit(r) -> AuditResult:
        metrics: dict = {}
        frames: dict = {}
        warnings = list(check(
            inputs.master,
            maskable=inputs.maskable_audited,
            maskable_bg=inputs.background_color,
            maskable_scale=inputs.maskable_scale,
            maskable_svg=inputs.maskable_svg if inputs.maskable_audited else None,
            android="android" in inputs.targets,
            color_scheme=inputs.color_scheme,
            rasterizer=r,
            metrics=metrics,
            text=captured("master"),
            maskable_text=captured("maskable") if inputs.maskable_audited else None,
            plan=plan,
            provenance=frames,
        ))
        advisories: list[Finding] = []
        hood = None
        config = inputs.config
        if config is not None and getattr(config, "neighbours_declared", False):
            hood = neighbourhood_audit(
                inputs.master,
                avoid=config.neighbours_avoid,
                family=config.neighbours_family,
                portfolio=config.neighbours_portfolio,
                base=config.source.parent,
                color_scheme=inputs.color_scheme,
                rasterizer=r,
                text=captured("master"),
            )
            gating, advising = hood.findings()
            warnings.extend(gating)
            advisories.extend(advising)
        if inputs.tray_audited:
            advisories.extend(tray_template_warnings(
                inputs.tray_svg, template_mode=inputs.tray_template_mode, rasterizer=r,
                text=captured("tray"),
            ))
        binding = None
        if plan is not None:
            binding = {"digest": plan.digest, "artifact_digest": plan.artifact_digest,
                       "provenance_digest": plan.provenance_digest}
        return AuditResult(inputs, warnings, advisories, hood, metrics, frames, binding)

    if rasterizer is not None:
        return audit(rasterizer)
    # Resolved through qa so a caller (or test) that substitutes qa's
    # renderer substitutes the whole audit's; lazy, so a check that renders
    # nothing (or is substituted) never starts Chromium.
    from .rasterize import LazyRasterizer

    with LazyRasterizer(color_scheme=inputs.color_scheme, factory=qa.Rasterizer) as owned:
        return audit(owned)
