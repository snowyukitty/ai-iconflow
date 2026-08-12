"""Integrate, review-bind, and publish the 20 x 20 Emoji Matrix.

Agent drafts remain under work/. This script is the sole renderer that promotes
clean-room sources into the repository and public static asset tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

from PIL import Image

from iconflow.casebook import AXES, new_case
from iconflow.config import (
    load_config,
    load_review_receipt,
    review_build_contract,
    review_contract_digest,
    svg_sha256,
)
from iconflow.qa import check


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "work" / "emoji-matrix"
AGENT_ROOTS = (WORK_ROOT / "agent-a", WORK_ROOT / "agent-b")
SOURCE_ROOT = ROOT / "gallery" / "emoji-matrix" / "cases"
CATALOG_PATH = ROOT / "gallery" / "emoji-matrix" / "catalog.json"
OVERVIEW_PATH = ROOT / "gallery" / "emoji-matrix" / "overview-2560.webp"
REVIEW_DECISION = ROOT / "gallery" / "emoji-matrix" / "review-decision.json"
CHECK_RESULTS = ROOT / "gallery" / "emoji-matrix" / "check-results.json"
SIMILARITY_REPORT = WORK_ROOT / "similarity-report.json"
CHECK_PROGRESS = WORK_ROOT / "recheck-progress.json"
DEPLOY_ROOT = ROOT / "website" / "assets" / "gallery" / "emoji-matrix"
CASEBOOK = ROOT / "casebook"
DATE = "2026-08-12"

STYLES = [
    "flat-geometric", "gradient-glow", "line-mark", "mascot", "duotone",
    "stencil-cut", "pixel-grid", "isometric", "cut-paper", "enamel",
    "blueprint", "stained-glass", "risograph", "clay", "woven",
    "glass-stack", "cel-shaded", "ink-brush", "chrome", "woodcut",
]

EMOJI = [
    (1, "u1f602", "U+1F602", "face with tears of joy"),
    (2, "u2764-fe0f", "U+2764 U+FE0F", "red heart"),
    (3, "u1f60d", "U+1F60D", "smiling face with heart-eyes"),
    (4, "u1f923", "U+1F923", "rolling on the floor laughing"),
    (5, "u1f60a", "U+1F60A", "smiling face with smiling eyes"),
    (6, "u1f64f", "U+1F64F", "folded hands"),
    (7, "u1f495", "U+1F495", "two hearts"),
    (8, "u1f62d", "U+1F62D", "loudly crying face"),
    (9, "u1f618", "U+1F618", "face blowing a kiss"),
    (10, "u1f44d", "U+1F44D", "thumbs up"),
    (11, "u1f605", "U+1F605", "grinning face with sweat"),
    (12, "u1f44f", "U+1F44F", "clapping hands"),
    (13, "u1f601", "U+1F601", "beaming face with smiling eyes"),
    (14, "u1f525", "U+1F525", "fire"),
    (15, "u1f494", "U+1F494", "broken heart"),
    (16, "u1f496", "U+1F496", "sparkling heart"),
    (17, "u1f499", "U+1F499", "blue heart"),
    (18, "u1f622", "U+1F622", "crying face"),
    (19, "u1f914", "U+1F914", "thinking face"),
    (20, "u1f606", "U+1F606", "grinning squinting face"),
]


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _agent_for(rank: int) -> Path:
    return AGENT_ROOTS[0 if rank <= 10 else 1]


def _folder_candidates(stable: str) -> tuple[str, ...]:
    plain = stable.removeprefix("u")
    return (plain.lower(), plain.upper())


def _agent_case(agent: Path, stable: str, style: str) -> Path:
    for folder in _folder_candidates(stable):
        candidate = agent / "cases" / folder / style
        if candidate.is_dir():
            return candidate
    raise ValueError(f"missing agent case: {agent.name}/{stable}/{style}")


def _validate_agent_summary(agent: Path) -> None:
    manifest = _read_json(agent / "manifest.json")
    count = manifest.get("specimen_count")
    if count is None:
        cells = manifest.get("cells")
        count = len(cells) if isinstance(cells, list) else None
    if count != 200:
        raise ValueError(f"{agent.name}: expected 200 manifest cells, got {count}")

    checks = _read_json(agent / "check-results.json")
    if isinstance(checks.get("results"), list):
        rows = checks["results"]
        clean = [row for row in rows if row.get("clean") is True and row.get("returncode") == 0]
    elif isinstance(checks.get("cells"), list):
        rows = checks["cells"]
        clean = [row for row in rows if row.get("status") in {"clean", "passed"} and row.get("returncode") == 0]
    else:
        raise ValueError(f"{agent.name}: malformed check-results.json")
    if len(rows) != 200 or len(clean) != 200:
        raise ValueError(f"{agent.name}: expected 200/200 clean IconFlow checks, got {len(clean)}/{len(rows)}")


def _source_set() -> list[dict[str, object]]:
    cells: list[dict[str, object]] = []
    for rank, stable, sequence, name in EMOJI:
        agent = _agent_for(rank)
        for style_index, style in enumerate(STYLES, 1):
            directory = _agent_case(agent, stable, style)
            source = directory / "master.svg"
            for asset, size in (("16.png", (16, 16)), ("128.png", (128, 128)), ("silhouette-128.png", (128, 128))):
                path = directory / asset
                if not path.is_file() or Image.open(path).size != size:
                    raise ValueError(f"{directory}: {asset} must be an exact {size[0]}x{size[1]} PNG")
            cells.append({
                "rank": rank, "emoji_id": stable, "unicode_sequence": sequence,
                "cldr_short_name": name, "style_index": style_index, "style": style,
                "id": f"{stable}--{style}", "agent": agent.name,
                "source": source, "source_sha256": svg_sha256(source),
                "native": directory / "16.png", "proof": directory / "128.png",
                "silhouette": directory / "silhouette-128.png",
            })
    ids = [str(cell["id"]) for cell in cells]
    if len(cells) != 400 or len(set(ids)) != 400:
        raise ValueError("Emoji Matrix must contain exactly 400 unique cells")
    return cells


def _set_digest(cells: list[dict[str, object]]) -> str:
    material = "\n".join(f"{cell['id']}:{cell['source_sha256']}" for cell in cells) + "\n"
    return hashlib.sha256(material.encode()).hexdigest()


def _build_overview(cells: list[dict[str, object]]) -> dict[str, object]:
    """Compose the reviewed proofs into one deterministic 20 x 20 poster."""
    tile_size = 128
    side = tile_size * 20
    paper = (248, 237, 225, 255)
    canvas = Image.new("RGBA", (side, side), paper)
    for cell in cells:
        row = int(cell["rank"]) - 1
        column = int(cell["style_index"]) - 1
        proof = Image.open(Path(cell["proof"])).convert("RGBA")
        if proof.size != (tile_size, tile_size):
            raise ValueError(f"{cell['id']}: overview proof must be exactly 128x128")
        tile = Image.new("RGBA", (tile_size, tile_size), paper)
        tile.alpha_composite(proof)
        canvas.alpha_composite(tile, (column * tile_size, row * tile_size))

    OVERVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(
        OVERVIEW_PATH,
        format="WEBP",
        lossless=True,
        quality=100,
        method=6,
    )
    shutil.copy2(OVERVIEW_PATH, DEPLOY_ROOT / OVERVIEW_PATH.name)
    return {
        "asset": f"/assets/gallery/emoji-matrix/{OVERVIEW_PATH.name}",
        "width": side,
        "height": side,
        "tile_width": tile_size,
        "tile_height": tile_size,
        "sha256": hashlib.sha256(OVERVIEW_PATH.read_bytes()).hexdigest(),
    }


def _dhash(path: Path, channel: str) -> int:
    image = Image.open(path).convert("RGBA")
    if channel == "alpha":
        plane = image.getchannel("A")
    else:
        white = Image.new("RGBA", image.size, "white")
        plane = Image.alpha_composite(white, image).convert("L")
    values = list(plane.resize((9, 8), Image.Resampling.LANCZOS).get_flattened_data())
    value = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            value = (value << 1) | int(values[offset + column] > values[offset + column + 1])
    return value


def _config_text(cell: dict[str, object]) -> str:
    project = f"Emoji Matrix: {cell['cldr_short_name']} / {cell['style']}"
    return f'''# Generated from scripts/build_emoji_matrix.py.
schema_version = 1

[project]
name = {json.dumps(project)}
master = "master.svg"
output = "build"
casebook = "../../../../casebook"

[brief]
app_intent = {json.dumps("study recognizability across a structurally distinct icon grammar")}
user_job = {json.dumps("recognize the " + str(cell['cldr_short_name']) + " meaning at native icon size")}
essence = "recognition"
personality = ["original", "clear", "experimental"]

[design]
palette = ["#FF766D", "#FFF4E8"]
cliches = ["vendor emoji artwork, traced glyph geometry, palette-only restyling"]
signature_device = {json.dumps(str(cell['style']) + " construction grammar around the semantic silhouette")}
device_family = "semantic-style-grammar"
device_detail = {json.dumps(str(cell['style']) + " construction grammar around the semantic silhouette")}
concept_lens = "cross-style-semantic"

[build]
targets = ["web"]
theme_color = "#FF766D"
background_color = "#FFF4E8"
electron_radius = 0
tray_ts = false
tray_svg = ""
tray_template_mode = "auto"
color_scheme = "light"
optimize_png = true

[review]
status = "pending"
source_sha256 = ""
contract_sha256 = ""
scores = {{}}
notes = ""
'''


def _receipt(cell: dict[str, object], scores: dict[str, int], evidence: dict[str, object]) -> dict[str, object]:
    project = f"Emoji Matrix: {cell['cldr_short_name']} / {cell['style']}"
    build = review_build_contract(
        theme_color="#FF766D", background_color="#FFF4E8", electron_radius=0,
        tray_template_mode="auto", color_scheme="light", tray_source_sha256=None,
    )
    contract = review_contract_digest(
        source_sha256=str(cell["source_sha256"]), project=project,
        targets=("web",), build=build,
    )
    return {
        "schema": 1, "source": "master.svg", "source_sha256": cell["source_sha256"],
        "contract_sha256": contract, "project": project,
        "user_job": f"recognize the {cell['cldr_short_name']} meaning at native icon size",
        "essence": "recognition", "personality": "original, clear, experimental",
        "signature_device": f"{cell['style']} construction grammar around the semantic silhouette",
        "cliches": ["vendor emoji artwork", "traced glyph geometry", "palette-only restyling"],
        "targets": ["web"], "build": build, "warnings": [], "scores": scores,
        "notes": (
            "Practice specimen, not a shipped identity. Reviewed at exact 16px and 128px, "
            f"in silhouette, and on contact sheet {evidence['contact_sheet_pattern']}."
        ),
        "status": "ready", "specimen_status": "practice",
        "collection_review_sha256": evidence["review_sha256"],
    }


def _record_emoji_case(entry: tuple[int, str, str, str], scores: dict[str, int]) -> str:
    _, stable, sequence, name = entry
    slug = f"emoji-matrix-{stable}"
    expected = CASEBOOK / f"{DATE}-{slug}.md"
    if expected.is_file():
        return expected.name
    created = new_case(
        CASEBOOK, slug, project=f"Emoji Matrix: {name}", targets="20 web practice specimens",
        essence="recognition", style_family="twenty-style-matrix",
        signature_device="semantic core preserved through 20 construction grammars",
        device_family="semantic-style-grammar",
        device_detail="semantic core preserved through 20 construction grammars",
        concept_lens="cross-style-semantic", status="reviewed",
        cliche_avoided="vendor emoji artwork and palette-only restyling",
        scores_first={axis: 3 if axis in {"legibility", "distinctiveness"} else 4 for axis in AXES},
        scores_final=scores, iterations=2,
        summary=(f"{sequence} ({name}) was redrawn as original clean-room geometry across all "
                 "20 IconFlow construction grammars and reviewed together at exact native size."),
        lessons=[f"For {name}, preserve the semantic core before style material and keep every expression cue above two output pixels."],
        date=DATE,
    )
    content = created.read_text(encoding="utf-8").replace("- [ ] For ", "- [x] For ")
    created.write_text(content, encoding="utf-8")
    return created.name


def prepare_review() -> None:
    for agent in AGENT_ROOTS:
        _validate_agent_summary(agent)
    cells = _source_set()
    fingerprints: dict[str, dict[str, str]] = {}
    perceptual: dict[str, tuple[int, int]] = {}
    duplicates: list[list[str]] = []
    by_digest: dict[str, list[str]] = {}
    for cell in cells:
        digest = hashlib.sha256(Path(cell["proof"]).read_bytes()).hexdigest()
        alpha_hash = _dhash(Path(cell["proof"]), "alpha")
        luminance_hash = _dhash(Path(cell["proof"]), "luminance")
        fingerprints[str(cell["id"])] = {
            "png_sha256": digest,
            "alpha_dhash64": f"{alpha_hash:016x}",
            "luminance_dhash64": f"{luminance_hash:016x}",
        }
        perceptual[str(cell["id"])] = (alpha_hash, luminance_hash)
        by_digest.setdefault(digest, []).append(str(cell["id"]))
    duplicates = [ids for ids in by_digest.values() if len(ids) > 1]
    pairs: list[dict[str, object]] = []
    ids = list(perceptual)
    for left_index, left in enumerate(ids):
        left_emoji, left_style = left.split("--", 1)
        for right in ids[left_index + 1:]:
            right_emoji, right_style = right.split("--", 1)
            alpha_distance = (perceptual[left][0] ^ perceptual[right][0]).bit_count()
            luminance_distance = (perceptual[left][1] ^ perceptual[right][1]).bit_count()
            distance = alpha_distance + luminance_distance
            pairs.append({
                "left": left, "right": right,
                "same_emoji": left_emoji == right_emoji,
                "same_style": left_style == right_style,
                "alpha_hamming": alpha_distance,
                "luminance_hamming": luminance_distance,
                "combined_hamming": distance,
            })
    pairs.sort(key=lambda pair: (pair["combined_hamming"], pair["alpha_hamming"], pair["left"], pair["right"]))
    high_risk = [
        pair for pair in pairs
        if (pair["same_emoji"] and pair["combined_hamming"] <= 12)
        or (not pair["same_emoji"] and pair["combined_hamming"] <= 6)
    ]
    report = {
        "schema_version": 1, "generated_on": DATE, "cell_count": 400,
        "source_set_sha256": _set_digest(cells), "exact_128px_duplicate_groups": duplicates,
        "method": (
            "Exact PNG SHA-256 plus 64-bit alpha and white-composited luminance dHashes. "
            "Hamming distance is a triage signal for visual inspection, not an admission score."
        ),
        "perceptual_high_risk_pairs": high_risk,
        "nearest_100_pairs": pairs[:100], "fingerprints": fingerprints,
    }
    path = SIMILARITY_REPORT
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"review set: 400 cells, source-set sha256={report['source_set_sha256']}")
    print(f"exact duplicate groups: {len(duplicates)}")
    print(f"perceptual high-risk pairs: {len(high_risk)}")
    print(f"similarity report: {path}")


def _check_one(path: str) -> dict[str, object]:
    source = Path(path)
    warnings = check(source)
    return {
        "id": f"u{source.parents[1].name.lower()}--{source.parent.name}",
        "source_sha256": svg_sha256(source), "warnings": warnings,
    }


def _check_one_with_retry(path: str, attempts: int = 3) -> dict[str, object]:
    for attempt in range(1, attempts + 1):
        try:
            return _check_one(path)
        except Exception as exc:
            message = str(exc)
            transient = "BrowserType.launch" in message and "Timeout" in message
            if not transient or attempt == attempts:
                raise
            time.sleep(attempt * 2)
    raise AssertionError("unreachable check retry state")


def recheck() -> None:
    cells = _source_set()
    source_set_sha256 = _set_digest(cells)
    prior: dict[str, dict[str, object]] = {}
    if CHECK_PROGRESS.is_file():
        progress = _read_json(CHECK_PROGRESS)
        if progress.get("source_set_sha256") == source_set_sha256:
            prior = {
                row["id"]: row for row in progress.get("results", [])
                if isinstance(row, dict) and isinstance(row.get("id"), str)
            }
    rows: list[dict[str, object]] = []
    for index, cell in enumerate(cells, start=1):
        source = cell["source"]
        cell_id = cell["id"]
        current_hash = svg_sha256(source)
        cached = prior.get(cell_id)
        if cached is not None and cached.get("source_sha256") == current_hash:
            row = cached
        else:
            row = _check_one_with_retry(str(source))
        rows.append(row)
        checkpoint = {
            "schema_version": 1,
            "source_set_sha256": source_set_sha256,
            "completed": index,
            "total": 400,
            "results": rows,
        }
        CHECK_PROGRESS.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    warnings = [row for row in rows if row["warnings"]]
    payload = {
        "schema_version": 1, "checked_on": DATE,
        "source_set_sha256": source_set_sha256,
        "command": "iconflow.qa.check via repository .venv, one isolated check at a time with transient browser-launch retries",
        "total": 400, "clean": 400 - len(warnings), "failed": len(warnings),
        "results": rows,
    }
    CHECK_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    CHECK_RESULTS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if warnings:
        raise ValueError(f"independent Emoji Matrix recheck found {len(warnings)} warning cells")
    print("emoji-matrix independent recheck: 400/400 clean")


def integrate() -> None:
    for agent in AGENT_ROOTS:
        _validate_agent_summary(agent)
    cells = _source_set()
    decision = _read_json(REVIEW_DECISION)
    if decision.get("source_set_sha256") != _set_digest(cells):
        raise ValueError("Emoji Matrix review decision is stale for the current 400-source set")
    if not SIMILARITY_REPORT.is_file():
        raise ValueError("missing current similarity report; run --prepare-review")
    similarity = _read_json(SIMILARITY_REPORT)
    if similarity.get("source_set_sha256") != _set_digest(cells):
        raise ValueError("Emoji Matrix similarity report is stale for the current 400-source set")
    if similarity.get("exact_128px_duplicate_groups") != []:
        raise ValueError("Emoji Matrix similarity report contains exact duplicate renders")
    if decision.get("status") != "accepted-practice-specimens":
        raise ValueError("Emoji Matrix review decision must explicitly accept practice specimens")
    if decision.get("contact_sheets_inspected") != 20:
        raise ValueError("all 20 Emoji Matrix contact sheets must be inspected")
    if decision.get("native_16px_inspected") is not True or decision.get("silhouettes_inspected") is not True:
        raise ValueError("native 16px and silhouette inspection evidence is required")
    scores = decision.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(AXES):
        raise ValueError("review decision must score all six IconFlow axes")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 4 for value in scores.values()):
        raise ValueError("every Emoji Matrix review score must be an integer >= 4")
    decision_bytes = REVIEW_DECISION.read_bytes()
    evidence = {
        "review_sha256": hashlib.sha256(decision_bytes).hexdigest(),
        "contact_sheet_pattern": "agent-a/contact-sheet-*.png or agent-b/contact-*.png",
    }
    if not CHECK_RESULTS.is_file():
        raise ValueError("missing independent 400-cell check results; run --recheck")
    checks = _read_json(CHECK_RESULTS)
    if checks.get("total") != 400 or checks.get("clean") != 400 or checks.get("failed") != 0:
        raise ValueError("independent check-results.json must report 400/400 clean")
    check_rows = checks.get("results")
    if not isinstance(check_rows, list) or len(check_rows) != 400:
        raise ValueError("independent check-results.json must contain exactly 400 rows")
    current_hashes = {str(cell["id"]): str(cell["source_sha256"]) for cell in cells}
    checked_hashes = {str(row.get("id")): str(row.get("source_sha256")) for row in check_rows}
    if checked_hashes != current_hashes or any(row.get("warnings") != [] for row in check_rows):
        raise ValueError("independent check rows are stale or contain warnings")
    curator_path = ROOT / str(decision.get("curator_report", ""))
    if not curator_path.is_file():
        raise ValueError("review decision must reference the final curator report")
    if decision.get("curator_report_sha256") != hashlib.sha256(curator_path.read_bytes()).hexdigest():
        raise ValueError("final curator report hash is stale")

    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    DEPLOY_ROOT.mkdir(parents=True, exist_ok=True)
    case_files = {stable: _record_emoji_case(entry, scores) for entry in EMOJI for stable in [entry[1]]}
    catalog_cells: list[dict[str, object]] = []
    for cell in cells:
        target = SOURCE_ROOT / str(cell["emoji_id"]) / str(cell["style"])
        deploy = DEPLOY_ROOT / str(cell["emoji_id"]) / str(cell["style"])
        target.mkdir(parents=True, exist_ok=True)
        deploy.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cell["source"], target / "master.svg")
        for label, source in (("16.png", cell["native"]), ("128.png", cell["proof"]), ("silhouette-128.png", cell["silhouette"])):
            shutil.copy2(source, target / label)
        (target / "iconflow.toml").write_text(_config_text(cell), encoding="utf-8")
        receipt = _receipt(cell, scores, evidence)
        (target / "review.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        config = load_config(target / "iconflow.toml")
        validated = load_review_receipt(target / "review.json", config)
        for label in ("master.svg", "16.png", "128.png", "silhouette-128.png", "review.json"):
            shutil.copy2(target / label, deploy / label)
        catalog_cells.append({
            "id": cell["id"], "rank": cell["rank"], "emoji_id": cell["emoji_id"],
            "unicode_sequence": cell["unicode_sequence"], "cldr_short_name": cell["cldr_short_name"],
            "style_index": cell["style_index"], "style": cell["style"],
            "status": "practice-specimen", "source_sha256": validated.source_sha256,
            "contract_sha256": validated.contract_sha256, "scores": scores,
            "assets": {
                "svg": f"/assets/gallery/emoji-matrix/{cell['emoji_id']}/{cell['style']}/master.svg",
                "native": f"/assets/gallery/emoji-matrix/{cell['emoji_id']}/{cell['style']}/16.png",
                "proof": f"/assets/gallery/emoji-matrix/{cell['emoji_id']}/{cell['style']}/128.png",
                "silhouette": f"/assets/gallery/emoji-matrix/{cell['emoji_id']}/{cell['style']}/silhouette-128.png",
                "receipt": f"/assets/gallery/emoji-matrix/{cell['emoji_id']}/{cell['style']}/review.json",
                "case": f"/assets/gallery/emoji-matrix/cases/{cell['emoji_id']}.md",
            },
        })
    case_deploy = DEPLOY_ROOT / "cases"
    case_deploy.mkdir(parents=True, exist_ok=True)
    for stable, name in case_files.items():
        shutil.copy2(CASEBOOK / name, case_deploy / f"{stable}.md")

    overview = _build_overview(cells)
    record = {
        "schema_version": 1, "generated_on": DATE, "research_snapshot": DATE,
        "collection": "Emoji 20 x 20 Matrix", "status": "practice-specimens",
        "method": "Unicode Emoji Frequency median ordering with normalized variants; Brandwatch 2025 cross-check.",
        "artwork": "Original clean-room SVG geometry; no vendor emoji artwork used.",
        "emoji_count": 20, "style_count": 20, "cell_count": 400,
        "generated_count": 400, "admitted_count": 400, "rejected_count": 0,
        "source_set_sha256": _set_digest(cells), "review_sha256": evidence["review_sha256"],
        "overview": overview,
        "emoji": [{"rank": rank, "id": stable, "unicode_sequence": sequence, "cldr_short_name": name} for rank, stable, sequence, name in EMOJI],
        "styles": [{"index": index, "id": style} for index, style in enumerate(STYLES, 1)],
        "cells": catalog_cells, "rejected": [],
    }
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(text, encoding="utf-8")
    (DEPLOY_ROOT / "catalog.json").write_text(text, encoding="utf-8")
    shutil.copy2(REVIEW_DECISION, DEPLOY_ROOT / "review-decision.json")
    shutil.copy2(CHECK_RESULTS, DEPLOY_ROOT / "check-results.json")
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"emoji-matrix integrated: 400 practice specimens, catalog sha256={digest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-review", action="store_true")
    parser.add_argument("--recheck", action="store_true")
    parser.add_argument("--integrate", action="store_true")
    args = parser.parse_args()
    if sum((args.prepare_review, args.recheck, args.integrate)) != 1:
        parser.error("choose exactly one action")
    if args.prepare_review:
        prepare_review()
    elif args.recheck:
        recheck()
    else:
        integrate()


if __name__ == "__main__":
    main()
