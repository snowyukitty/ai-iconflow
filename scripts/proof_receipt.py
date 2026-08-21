#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Validate that an IconFlow review receipt still binds to its source and contract.

`iconflow ship` refuses a stale receipt but has no dry-run mode and writes the
icon family when it passes. CI wants the refusal without the build, so this
helper performs the same binding checks read-only and reports them in the
Agent Contract envelope shape (`docs/AGENT_CONTRACT.md`):

    python scripts/proof_receipt.py --config iconflow.toml [--review master-review.json] [--json]

Exit codes follow the contract: 0 = bound (or no receipt present, reported as
an advisory), 1 = a receipt is present but stale/invalid, 2 = usage/config error.

Warning codes (gating): `receipt-stale-source`, `receipt-stale-contract`,
`receipt-not-ready`, `score-below-floor`, `qa-warnings`, `receipt-invalid`.
A missing receipt is reported as `receipt-not-ready` (blocked), never as an advisory.

It never scores taste and never writes files. The `iconflow` package must be
importable (the PR Proof action installs it before calling this script).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = 1
COMMAND = "proof-receipt"
RECEIPT_CANDIDATES = ("master-review.json",)


def _envelope(
    status: str,
    *,
    warnings: list[dict[str, str]] | None = None,
    advisories: list[dict[str, str]] | None = None,
    outputs: dict[str, Any] | None = None,
    errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    exit_code = {"ok": 0, "blocked": 1, "error": 2}[status]
    return {
        "schema": SCHEMA,
        "command": COMMAND,
        "status": status,
        "exit_code": exit_code,
        "warnings": warnings or [],
        "advisories": advisories or [],
        "outputs": outputs or {},
        "errors": errors or [],
    }


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def find_receipt(config_path: Path, master: Path) -> Path | None:
    """Return the conventional receipt next to the config/master, if any."""

    names = [f"{master.stem}-review.json", *RECEIPT_CANDIDATES]
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        for base in (config_path.parent, master.parent):
            candidate = base / name
            if candidate.is_file():
                return candidate
    return None


def _classify_receipt_error(message: str) -> str:
    lowered = message.lower()
    if "status must be 'ready'" in lowered:
        return "receipt-not-ready"
    if "review gate failed" in lowered or "incomplete" in lowered:
        return "score-below-floor"
    if "automated warnings" in lowered:
        return "qa-warnings"
    if "stale" in lowered and "source_sha256" in lowered:
        return "receipt-stale-source"
    if "mismatch" in lowered:
        return "receipt-stale-contract"
    return "receipt-invalid"


def evaluate(config_path: Path, receipt_path: Path | None, *, auto: bool = True) -> dict[str, Any]:
    """Evaluate the binding and return an Agent Contract envelope (never raises)."""

    try:
        from iconflow.casebook import AXES
        from iconflow.config import (
            ConfigError,
            config_review_contract_digest,
            load_config,
            load_review_receipt,
            svg_sha256,
            validate_ship_scores,
        )
    except ImportError as exc:  # pragma: no cover - depends on the environment
        return _envelope(
            "error",
            errors=[_finding("iconflow-missing", f"iconflow is not importable: {exc}")],
        )

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        return _envelope("error", errors=[_finding("config-invalid", str(exc))])
    master = config.master_path
    if not master.is_file():
        return _envelope(
            "error", errors=[_finding("master-missing", f"master SVG not found: {master}")]
        )
    try:
        current_source = svg_sha256(master)
        expected_contract = config_review_contract_digest(config)
    except (ConfigError, OSError, RuntimeError, ValueError) as exc:
        return _envelope("error", errors=[_finding("source-unreadable", str(exc))])

    outputs: dict[str, Any] = {
        "config": str(config.source),
        "source": str(master),
        "source_sha256": current_source,
        "contract_sha256": expected_contract,
        "receipt": None,
        "receipt_kind": None,
        "scores": {},
    }
    warnings: list[dict[str, str]] = []

    if receipt_path is None and auto:
        receipt_path = find_receipt(config.source, master)

    if receipt_path is not None:
        receipt_path = Path(receipt_path).expanduser().resolve(strict=False)
        outputs["receipt"] = str(receipt_path)
        outputs["receipt_kind"] = "review-lab"
        try:
            raw = json.loads(receipt_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return _envelope(
                "error",
                outputs=outputs,
                errors=[_finding("receipt-missing", f"review receipt not found: {receipt_path}")],
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            warnings.append(_finding("receipt-invalid", f"review receipt is not valid JSON: {exc}"))
            return _envelope("blocked", warnings=warnings, outputs=outputs)
        if not isinstance(raw, dict):
            warnings.append(_finding("receipt-invalid", "review receipt must be a JSON object"))
            return _envelope("blocked", warnings=warnings, outputs=outputs)

        claimed_source = raw.get("source_sha256")
        if not isinstance(claimed_source, str) or claimed_source.lower() != current_source:
            warnings.append(
                _finding(
                    "receipt-stale-source",
                    "receipt source_sha256 does not match the current master SVG; "
                    "re-run review and rescore",
                )
            )
        else:
            claimed_contract = raw.get("contract_sha256")
            if isinstance(claimed_contract, str) and claimed_contract.lower() != expected_contract:
                warnings.append(
                    _finding(
                        "receipt-stale-contract",
                        "receipt contract_sha256 does not match the current project, targets, "
                        "colors, Electron radius, color scheme, or tray source/mode",
                    )
                )
        if not warnings:
            try:
                receipt = load_review_receipt(receipt_path, config)
            except ConfigError as exc:
                code = getattr(exc, "code", None) or _classify_receipt_error(str(exc))
                warnings.append(_finding(str(code), str(exc)))
            else:
                outputs["scores"] = {axis: receipt.scores[axis] for axis in AXES}
        return _envelope("blocked" if warnings else "ok", warnings=warnings, outputs=outputs)

    # No Review Lab receipt: honour the approved `[review]` config fallback.
    if config.review_status in {"approved", "shipped"} and (
        config.review_source_sha256 or config.review_contract_sha256
    ):
        outputs["receipt"] = str(config.source)
        outputs["receipt_kind"] = "config-fallback"
        if config.review_source_sha256 != current_source:
            warnings.append(
                _finding(
                    "receipt-stale-source",
                    "[review].source_sha256 does not match the current master SVG",
                )
            )
        elif config.review_contract_sha256 != expected_contract:
            warnings.append(
                _finding(
                    "receipt-stale-contract",
                    "[review].contract_sha256 does not match the current source, project, "
                    "targets, or visual transforms",
                )
            )
        else:
            try:
                validate_ship_scores(config.review_scores)
            except ConfigError as exc:
                warnings.append(_finding("score-below-floor", str(exc)))
            else:
                outputs["scores"] = {axis: config.review_scores[axis] for axis in AXES}
        return _envelope("blocked" if warnings else "ok", warnings=warnings, outputs=outputs)

    # No receipt and no approved fallback: the family cannot ship, so a PR that
    # touches it is blocked until a review is recorded (fail closed).
    return _envelope(
        "blocked",
        warnings=[
            _finding(
                "receipt-not-ready",
                "no Review Lab receipt or approved [review] fallback found; "
                "ship will be refused until one exists",
            )
        ],
        outputs=outputs,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="proof_receipt.py",
        description="Read-only staleness check for an IconFlow review receipt.",
    )
    parser.add_argument("--config", default="iconflow.toml", help="project configuration path")
    parser.add_argument("--review", help="Review Lab JSON receipt (auto-detected when omitted)")
    parser.add_argument(
        "--no-auto", action="store_true",
        help="do not look for master-review.json next to the config when --review is omitted",
    )
    parser.add_argument("--json", action="store_true", help="emit the Agent Contract envelope")
    args = parser.parse_args(argv)

    envelope = evaluate(
        Path(args.config).expanduser(),
        Path(args.review).expanduser() if args.review else None,
        auto=not args.no_auto,
    )
    if args.json:
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True))
    else:
        label = {"ok": "OK", "blocked": "BLOCKED", "error": "ERROR"}[envelope["status"]]
        print(f"{label} - receipt check for {envelope['outputs'].get('config', args.config)}")
        for item in envelope["warnings"]:
            print(f"  ! {item['code']}: {item['message']}")
        for item in envelope["advisories"]:
            print(f"  ~ {item['code']}: {item['message']}")
        for item in envelope["errors"]:
            print(f"  x {item['code']}: {item['message']}", file=sys.stderr)
        scores = envelope["outputs"].get("scores") or {}
        if scores:
            print("  scores: " + ", ".join(f"{axis}={value}" for axis, value in scores.items()))
    return int(envelope["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
