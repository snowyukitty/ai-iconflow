#!/usr/bin/env python3
"""Driver for the IconFlow PR Proof composite action.

For every `iconflow.toml` in scope it runs the mechanical gate through the CLI
and reads ONLY the Agent Contract JSON envelopes (`docs/AGENT_CONTRACT.md`):

    python -m iconflow check <master> --json [--tray-svg ... --tray-template-mode ...]
    python -m iconflow review --config <toml> --out review.png --html review.html --json
    python scripts/proof_receipt.py --config <toml> --json

It then writes a GitHub job summary, copies the review sheet and Review Lab
into the artifact directory, and exits 0 (all ok), 1 (something is blocked by
IconFlow's own rules), or 2 (a runtime/usage error). It never scores taste and
never approves anything: a human still has to inspect the sheet and sign the
receipt.

Configuration comes from environment variables set by `action.yml`:

    PROOF_CONFIGS          newline/space separated iconflow.toml paths (empty = discover)
    PROOF_CHANGED_FILES    path to a newline-separated list of changed files (empty = all)
    PROOF_ARTIFACT_DIR     where review.png / review.html / proof.json are written
    PROOF_RECEIPT_SCRIPT   path to scripts/proof_receipt.py
    PROOF_PYTHON           interpreter to run the CLI with (default: this one)
    GITHUB_WORKSPACE, GITHUB_STEP_SUMMARY, GITHUB_OUTPUT (standard runner variables)
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "work"}
STATUS_LABEL = {"ok": "PASS", "blocked": "BLOCKED", "error": "ERROR"}


def _read_lines(path: str | None) -> list[str] | None:
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8")
    return [line.strip().replace("\\", "/") for line in text.splitlines() if line.strip()]


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def discover_configs(root: Path, explicit: str | None, changed: list[str] | None) -> list[Path]:
    """Return the iconflow.toml files the proof should run on."""

    if explicit and explicit.strip():
        return [
            (root / item).resolve() if not Path(item).is_absolute() else Path(item)
            for item in explicit.split()
        ]
    candidates = sorted(
        path for path in root.rglob("iconflow.toml")
        if not (set(path.relative_to(root).parts) & SKIP_PARTS)
    )
    if changed is None:
        return candidates
    selected: list[Path] = []
    for config in candidates:
        rel_config = _relative(config, root)
        rel_dir = _relative(config.parent, root)
        prefix = "" if rel_dir == "." else rel_dir + "/"
        related = {rel_config}
        try:
            from iconflow.config import load_config

            loaded = load_config(config)
            related.add(_relative(loaded.master_path, root))
            if loaded.tray_svg_path:
                related.add(_relative(loaded.tray_svg_path, root))
        except Exception:  # noqa: BLE001 - an unloadable config is reported by prove()
            pass
        if any(item in related or item.startswith(prefix) for item in changed):
            selected.append(config)
    return selected


def run_envelope(command: list[str], *, cwd: Path, expected_command: str) -> dict[str, Any]:
    """Run a CLI command and return its JSON envelope, or a synthetic error envelope."""

    try:
        completed = subprocess.run(
            command, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
    except OSError as exc:
        return _synthetic(expected_command, 2, "launch-failed", str(exc))
    stdout = completed.stdout.strip()
    envelope = _parse_envelope(stdout)
    detail = (stdout or completed.stderr or "").strip()[-1200:]
    if envelope is None:
        return _synthetic(
            expected_command, completed.returncode, "envelope-unparseable",
            f"stdout was not exactly one Agent Contract JSON object (exit {completed.returncode}): {detail}",
        )
    problem = _validate_envelope(envelope, expected_command, completed.returncode)
    if problem:
        return _synthetic(expected_command, completed.returncode, "envelope-invalid", f"{problem}: {detail}")
    if completed.stderr.strip():
        envelope["_stderr"] = completed.stderr.strip()[-1200:]
    return envelope


STATUS_EXIT = {"ok": 0, "blocked": 1, "error": 2}


def _parse_envelope(stdout: str) -> dict[str, Any] | None:
    """Parse stdout as exactly one JSON object; anything else is a contract breach."""

    if not stdout:
        return None
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _validate_envelope(envelope: dict[str, Any], expected_command: str, returncode: int) -> str | None:
    """Return a reason when the envelope breaks the Agent Contract, else None."""

    if envelope.get("schema") != 1:
        return "envelope schema is not 1"
    if envelope.get("command") != expected_command:
        return f"envelope command {envelope.get('command')!r} is not {expected_command!r}"
    status = envelope.get("status")
    if status not in STATUS_EXIT:
        return f"envelope status {status!r} is not ok/blocked/error"
    if envelope.get("exit_code") != STATUS_EXIT[status]:
        return f"envelope exit_code {envelope.get('exit_code')!r} does not match status {status!r}"
    if returncode != STATUS_EXIT[status]:
        return f"process exited {returncode} but the envelope says {status}"
    for key in ("warnings", "advisories", "errors"):
        items = envelope.setdefault(key, [])
        if not isinstance(items, list) or any(
            not isinstance(item, dict) or "code" not in item or "message" not in item for item in items
        ):
            return f"envelope {key} is not a list of code/message objects"
    if not isinstance(envelope.setdefault("outputs", {}), dict):
        return "envelope outputs is not an object"
    return None


def _synthetic(command: str, exit_code: int, code: str, message: str) -> dict[str, Any]:
    return {
        "schema": 1,
        "command": command,
        "status": "error",
        "exit_code": exit_code if exit_code not in (0, 1) else 2,
        "warnings": [],
        "advisories": [],
        "outputs": {},
        "errors": [{"code": code, "message": message}],
    }


def prove(config: Path, *, root: Path, python: str, receipt_script: Path, artifact_dir: Path) -> dict[str, Any]:
    """Run check, review, and the receipt binding for one config."""

    rel = _relative(config, root)
    rel_dir = _relative(config.parent, root)
    slug = "root" if rel_dir == "." else rel_dir.replace("/", "__")
    out_dir = artifact_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"config": rel, "slug": slug, "artifacts": []}

    try:
        from iconflow.config import ConfigError, load_config

        loaded = load_config(config)
    except Exception as exc:  # noqa: BLE001 - report, never crash the whole proof
        result["check"] = _synthetic("check", 2, "config-invalid", str(exc))
        result["review"] = _synthetic("review", 2, "config-invalid", str(exc))
        result["receipt"] = _synthetic("proof-receipt", 2, "config-invalid", str(exc))
        return result

    check_cmd = [
        python, "-m", "iconflow", "check", str(loaded.master_path), "--json",
        "--bg", loaded.background_color,
    ]
    if not ({"web", "pwa"} & set(loaded.targets)):
        check_cmd.append("--no-maskable-audit")
    if loaded.tray_svg_path:
        check_cmd += [
            "--tray-svg", str(loaded.tray_svg_path),
            "--tray-template-mode", loaded.tray_template_mode,
        ]
    result["check"] = run_envelope(check_cmd, cwd=config.parent, expected_command="check")

    sheet = out_dir / "review.png"
    html = out_dir / "review.html"
    review_cmd = [
        python, "-m", "iconflow", "review", "--config", str(config),
        "--out", str(sheet), "--html", str(html), "--json",
    ]
    result["review"] = run_envelope(review_cmd, cwd=config.parent, expected_command="review")
    result["artifacts"] = [
        _relative(path, artifact_dir) for path in (sheet, html) if path.is_file()
    ]

    receipt_cmd = [python, str(receipt_script), "--config", str(config), "--json"]
    result["receipt"] = run_envelope(receipt_cmd, cwd=config.parent, expected_command="proof-receipt")
    return result


def decide(results: list[dict[str, Any]]) -> str:
    """Fold per-config envelopes into ok | blocked | error (fail-closed)."""

    overall = "ok"
    for result in results:
        for key in ("check", "review", "receipt"):
            envelope = result.get(key) or {}
            status = envelope.get("status", "error")
            exit_code = envelope.get("exit_code", 2)
            if status not in STATUS_EXIT or exit_code != STATUS_EXIT[status] or status == "error":
                return "error"
            if status == "blocked":
                overall = "blocked"
    return overall


def _findings(items: list[dict[str, Any]]) -> str:
    if not items:
        return "none"
    return "<br>".join(
        f"`{item.get('code', '?')}` {item.get('message', '')}".strip() for item in items
    )


def _cell(envelope: dict[str, Any]) -> str:
    status = envelope.get("status", "error")
    return f"{STATUS_LABEL.get(status, status)} (exit {envelope.get('exit_code', '?')})"


def render_summary(results: list[dict[str, Any]], *, overall: str, artifact_name: str) -> str:
    lines = [
        "## IconFlow proof",
        "",
        f"Overall: **{STATUS_LABEL[overall]}** - mechanical gate only; taste is not scored and "
        "nothing is approved here. A human still inspects the review sheet and signs the receipt.",
        "",
    ]
    if not results:
        lines += ["No `iconflow.toml` is in scope for the changed files; nothing to prove.", ""]
        return "\n".join(lines)
    lines += [
        "| Config | check | review | receipt | scores | sheet |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        scores = result["receipt"].get("outputs", {}).get("scores") or {}
        score_text = "/".join(str(scores[axis]) for axis in (
            "legibility", "distinctiveness", "balance", "color", "scalability", "craft"
        )) if scores else "-"
        sheet = ", ".join(result.get("artifacts") or []) or "-"
        lines.append(
            f"| `{result['config']}` | {_cell(result['check'])} | {_cell(result['review'])} | "
            f"{_cell(result['receipt'])} | {score_text} | {sheet} |"
        )
    lines += ["", f"Review sheets and Review Lab HTML are in the `{artifact_name}` artifact.", ""]
    for result in results:
        lines += [f"### `{result['config']}`", ""]
        for key in ("check", "review", "receipt"):
            envelope = result[key]
            lines.append(f"- **{key}**: {_cell(envelope)}")
            lines.append(f"  - warnings: {_findings(envelope.get('warnings', []))}")
            lines.append(f"  - advisories: {_findings(envelope.get('advisories', []))}")
            if envelope.get("errors"):
                lines.append(f"  - errors: {_findings(envelope['errors'])}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    root = Path(os.environ.get("GITHUB_WORKSPACE") or os.getcwd()).resolve()
    python = os.environ.get("PROOF_PYTHON") or sys.executable
    artifact_dir = Path(os.environ.get("PROOF_ARTIFACT_DIR") or (root / "work" / "iconflow-proof")).resolve()
    receipt_script = Path(
        os.environ.get("PROOF_RECEIPT_SCRIPT")
        or (Path(__file__).resolve().parents[3] / "scripts" / "proof_receipt.py")
    ).resolve()
    artifact_name = os.environ.get("PROOF_ARTIFACT_NAME") or "iconflow-proof"
    if not receipt_script.is_file():
        print(f"proof: receipt helper not found at {receipt_script}", file=sys.stderr)
        return 2

    changed = _read_lines(os.environ.get("PROOF_CHANGED_FILES") or None)
    configs = discover_configs(root, os.environ.get("PROOF_CONFIGS"), changed)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    results = [
        prove(config, root=root, python=python, receipt_script=receipt_script, artifact_dir=artifact_dir)
        for config in configs
    ]
    overall = decide(results) if results else "ok"
    (artifact_dir / "proof.json").write_text(
        json.dumps({"schema": 1, "status": overall, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    summary = render_summary(results, overall=overall, artifact_name=artifact_name)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(summary + "\n")
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"status={overall}\nartifact-dir={artifact_dir}\n")
    print(summary)
    for result in results:
        for key in ("check", "review", "receipt"):
            stderr = result[key].get("_stderr")
            if stderr:
                print(f"[{result['config']}] {key} stderr:\n{stderr}", file=sys.stderr)
    print(f"proof: {overall} ({len(results)} config(s)); commands: "
          + shlex.join([python, "-m", "iconflow", "check|review", "--json"]))
    return {"ok": 0, "blocked": 1, "error": 2}[overall]


if __name__ == "__main__":
    sys.exit(main())
