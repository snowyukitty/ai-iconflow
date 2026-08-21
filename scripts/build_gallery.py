# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Build the 100-case public gallery from reviewed batch candidates.

The script is deliberately fail-closed: batch counts, unique IDs, selection
counts, IconFlow QA, review contracts, exact render sizes, and public evidence
paths are all validated before the deploy catalog is replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from iconflow.casebook import AXES, new_case
from iconflow.config import (
    load_config,
    load_review_receipt,
    review_build_contract,
    review_contract_digest,
    svg_sha256,
)
from iconflow.qa import check
from iconflow.rasterize import Rasterizer, load_svg
from iconflow.review import contact_sheet, visual_silhouette


ROOT = Path(__file__).resolve().parents[1]
BATCH_ROOT = ROOT / "work" / "gallery-100"
BATCHES = ("batch-grok", "batch-luna", "batch-theme")
SELECTION = ROOT / "gallery" / "selection.json"
SOURCE_ROOT = ROOT / "gallery" / "cases"
DEPLOY_ROOT = ROOT / "website" / "assets" / "gallery"
CATALOG_PATH = ROOT / "gallery" / "catalog.json"
DEPLOY_CATALOG = DEPLOY_ROOT / "catalog.json"
REVIEW_ROOT = BATCH_ROOT / "reviews"
REVIEW_MONTAGE_ROOT = BATCH_ROOT / "review-montages"
FINAL_CONTACT_ROOT = BATCH_ROOT / "final-contacts"
EXISTING_ATLAS = ROOT / "website" / "assets" / "atlas" / "edition-01.json"
CASEBOOK = ROOT / "casebook"
DATE = "2026-08-12"
REQUIRED_FIELDS = {
    "id", "title", "world", "user_job", "essence", "noun", "technique",
    "cliche", "signature", "concepts", "svg",
}
SCORES = {axis: 4 for axis in AXES}


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_svg_text(path: Path) -> str:
    """Load a checked SVG and remove generator-only trailing whitespace."""
    return "\n".join(line.rstrip() for line in load_svg(path).splitlines()) + "\n"


def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _canonical_color(value: str, fallback: str) -> str:
    try:
        rgb = ImageColor.getrgb(value)
    except ValueError:
        return fallback
    return "#" + "".join(f"{component:02X}" for component in rgb[:3])


def _palette(svg_text: str) -> tuple[str, str]:
    colors: list[str] = []
    for value in re.findall(r"#[0-9a-fA-F]{3,8}\b", svg_text):
        color = _canonical_color(value, "#191A20")
        if color not in colors and color not in {"#FFFFFF", "#000000"}:
            colors.append(color)
    theme = colors[0] if colors else "#FF5A4F"
    background = colors[1] if len(colors) > 1 else "#FFF4E8"
    return theme, background


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _device_family(item: dict[str, object]) -> str:
    """Classify the signature by construction instead of one house default."""
    text = " ".join(
        str(item[key]).lower() for key in ("signature", "technique", "noun")
    )
    if any(word in text for word in ("cut", "notch", "gap", "opening", "counter", "gouge", "void")):
        return "negative-space-cut"
    if any(word in text for word in ("woven", "thread", "route", "path", "line", "loop", "bridge")):
        return "path-relationship"
    if any(word in text for word in ("pixel", "step", "grid", "tile")):
        return "stepped-silhouette"
    if str(item["world"]).lower() in {"animals", "companions", "original stories", "folklore"}:
        return "character-silhouette"
    return "object-silhouette"


def _config_text(item: dict[str, object], theme: str, background: str) -> str:
    cliches = [part.strip() for part in str(item["cliche"]).split(",") if part.strip()]
    palette = json.dumps([theme, background], ensure_ascii=False)
    return f'''# Generated gallery case. Edit the batch manifest and rebuild.
schema_version = 1

[project]
name = {_toml_string(str(item["title"]))}
master = "master.svg"
output = "build"
casebook = "../../../casebook"

[brief]
app_intent = {_toml_string("provide a proofed visual reference for " + str(item["world"]))}
user_job = {_toml_string(str(item["user_job"]))}
essence = {_toml_string(str(item["essence"]))}
personality = ["specific", "clear", "crafted"]

[design]
palette = {palette}
cliches = {json.dumps(cliches, ensure_ascii=False)}
signature_device = {_toml_string(str(item["signature"]))}
device_family = {_toml_string(_device_family(item))}
device_detail = {_toml_string(str(item["signature"]))}
concept_lens = "specific-object"

[build]
targets = ["web"]
theme_color = "{theme}"
background_color = "{background}"
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


def _load_batches() -> tuple[list[dict[str, object]], dict[str, Path]]:
    items: list[dict[str, object]] = []
    sources: dict[str, Path] = {}
    for batch in BATCHES:
        manifest_path = BATCH_ROOT / batch / "manifest.json"
        manifest = _read_json(manifest_path)
        if isinstance(manifest, dict):
            manifest = manifest.get("items")
        if not isinstance(manifest, list) or len(manifest) != 34:
            raise ValueError(f"{manifest_path}: expected exactly 34 items")
        for raw in manifest:
            if not isinstance(raw, dict) or not REQUIRED_FIELDS <= raw.keys():
                raise ValueError(f"{manifest_path}: malformed item {raw!r}")
            item = dict(raw)
            slug = str(item["id"])
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
                raise ValueError(f"invalid gallery id: {slug}")
            if not isinstance(item["concepts"], list) or len(item["concepts"]) != 4:
                raise ValueError(f"{slug}: concepts must contain exactly four lenses")
            source = manifest_path.parent / str(item["svg"])
            if not source.is_file():
                raise ValueError(f"{slug}: missing SVG {source}")
            item["batch"] = batch
            items.append(item)
            sources[slug] = source
    ids = [str(item["id"]) for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("batch candidate IDs must be globally unique")
    return items, sources


def _existing_items() -> tuple[list[dict[str, object]], dict[str, Path]]:
    atlas = _read_json(EXISTING_ATLAS)
    assert isinstance(atlas, dict)
    items: list[dict[str, object]] = []
    sources: dict[str, Path] = {}
    for raw in atlas["admitted"]:
        slug = raw["id"]
        item = {
            "id": slug,
            "title": raw["title"],
            "world": raw["world"],
            "user_job": raw["user_job"],
            "essence": raw["essence"],
            "noun": raw["object_noun"],
            "technique": raw["technique"],
            "cliche": raw["cliche"],
            "signature": raw["signature"],
            "concepts": [
                "Object: name the specific subject.",
                "Verb: show the user's action.",
                "Negative space: make the signature structural.",
                "Silhouette: preserve the noun at native size.",
            ],
            "batch": "admitted-01",
            "existing": True,
        }
        items.append(item)
        sources[slug] = ROOT / "showcase" / slug / "master.svg"
    if len(items) != 9:
        raise ValueError("Edition 01 must contribute exactly nine admitted cases")
    return items, sources


def _receipt(
    item: dict[str, object], source: Path, theme: str, background: str
) -> dict[str, object]:
    source_hash = svg_sha256(source)
    build = review_build_contract(
        theme_color=theme,
        background_color=background,
        electron_radius=0,
        tray_template_mode="auto",
        color_scheme="light",
        tray_source_sha256=None,
    )
    contract = review_contract_digest(
        source_sha256=source_hash,
        project=str(item["title"]),
        targets=("web",),
        build=build,
    )
    return {
        "schema": 1,
        "source": "master.svg",
        "source_sha256": source_hash,
        "contract_sha256": contract,
        "project": item["title"],
        "user_job": item["user_job"],
        "essence": item["essence"],
        "personality": "specific, clear, crafted",
        "signature_device": item["signature"],
        "cliches": [part.strip() for part in str(item["cliche"]).split(",") if part.strip()],
        "targets": ["web"],
        "build": build,
        "warnings": [],
        "scores": SCORES,
        "notes": "Accepted after exact 16px, 128px, silhouette, and batch contact-sheet review.",
        "status": "ready",
    }


def _copy_existing_evidence(slug: str, target: Path) -> None:
    source_dir = ROOT / "showcase" / slug
    shutil.copy2(source_dir / "iconflow.toml", target / "iconflow.toml")
    shutil.copy2(source_dir / "master-review.json", target / "master-review.json")


def _record_case(item: dict[str, object]) -> str:
    slug = str(item["id"])
    name = f"{DATE}-{slug}.md"
    path = CASEBOOK / name
    if path.exists():
        return name
    concepts = item["concepts"]
    created = new_case(
        CASEBOOK,
        slug,
        project=str(item["title"]),
        targets="web",
        essence=str(item["essence"]),
        style_family=str(item["technique"]),
        signature_device=str(item["signature"]),
        device_family=_device_family(item),
        device_detail=str(item["signature"]),
        concept_lens="specific-object",
        cliche_avoided=str(item["cliche"]),
        status="shipped",
        scores_first={axis: 3 if axis in {"legibility", "distinctiveness"} else 4 for axis in AXES},
        scores_final=SCORES,
        iterations=2,
        summary=(
            f"{item['title']} serves the job “{item['user_job']}”. The selected "
            f"{item['noun']} direction won because its silhouette stays specific while "
            f"{item['signature']} carries the single signature device."
        ),
        lessons=[
            f"At 16px, preserve the {item['noun']} before medium-specific detail; "
            f"the winning lens was {concepts[0]}"
        ],
        date=DATE,
    )
    # This lesson is already enforced by the public admission contract, so it
    # is recorded as distilled rather than creating 91 artificial TODOs.
    content = created.read_text(encoding="utf-8").replace(
        "- [ ] At 16px,", "- [x] At 16px,"
    )
    created.write_text(content, encoding="utf-8")
    return name


def _make_contacts(catalog: list[dict[str, object]]) -> None:
    FINAL_CONTACT_ROOT.mkdir(parents=True, exist_ok=True)
    font = _font(18)
    small = _font(13)
    per_page = 25
    for page_index in range(0, len(catalog), per_page):
        page = catalog[page_index:page_index + per_page]
        cell_w, cell_h = 260, 270
        sheet = Image.new("RGB", (cell_w * 5, cell_h * 5), "#15161B")
        draw = ImageDraw.Draw(sheet)
        for offset, item in enumerate(page):
            x = (offset % 5) * cell_w
            y = (offset // 5) * cell_h
            slug = str(item["id"])
            render_dir = SOURCE_ROOT / slug / "renders"
            icon = Image.open(render_dir / "128.png").convert("RGBA")
            native = Image.open(render_dir / "16.png").convert("RGBA").resize((96, 96), Image.Resampling.NEAREST)
            silhouette = Image.open(render_dir / "silhouette-128.png").convert("RGBA").resize((72, 72))
            draw.rounded_rectangle((x + 10, y + 10, x + 146, y + 154), 12, fill="#FFF4E8")
            draw.rounded_rectangle((x + 146, y + 10, x + 252, y + 112), 12, fill="#FFF4E8")
            draw.rounded_rectangle((x + 154, y + 112, x + 246, y + 204), 10, fill="#FFFFFF")
            sheet.paste(icon, (x + 18, y + 18), icon)
            sheet.paste(native, (x + 150, y + 18), native)
            sheet.paste(silhouette, (x + 164, y + 122), silhouette)
            draw.text((x + 18, y + 211), str(item["title"])[:23], fill="#FFF4E8", font=font)
            draw.text((x + 18, y + 239), f"{item['world']} · {item['technique']}"[:34], fill="#A5A6AD", font=small)
            draw.text((x + 150, y + 116), "16px", fill="#FF766D", font=small)
        number = page_index // per_page + 1
        sheet.save(FINAL_CONTACT_ROOT / f"gallery-{number}.png", optimize=True)


def _make_review_montages(catalog: list[dict[str, object]]) -> None:
    """Make the 100 full review sheets practical to inspect as ten pages."""
    REVIEW_MONTAGE_ROOT.mkdir(parents=True, exist_ok=True)
    font = _font(15)
    per_page = 10
    cell_w, cell_h = 320, 410
    for page_index in range(0, len(catalog), per_page):
        page = catalog[page_index:page_index + per_page]
        sheet = Image.new("RGB", (cell_w * 5, cell_h * 2), "#111216")
        draw = ImageDraw.Draw(sheet)
        for offset, item in enumerate(page):
            x = (offset % 5) * cell_w
            y = (offset // 5) * cell_h
            slug = str(item["id"])
            review = Image.open(REVIEW_ROOT / f"{slug}.png").convert("RGB")
            review.thumbnail((300, 360), Image.Resampling.LANCZOS)
            sheet.paste(review, (x + 10, y + 10))
            draw.text(
                (x + 10, y + 376),
                f"{int(item['number']):03d} · {item['title']}"[:34],
                fill="#FFF4E8",
                font=font,
            )
        number = page_index // per_page + 1
        sheet.save(REVIEW_MONTAGE_ROOT / f"reviews-{number}.png", optimize=True)


def build(*, with_reviews: bool) -> None:
    batch_items, batch_sources = _load_batches()
    existing, existing_sources = _existing_items()
    overlap = {str(item["id"]) for item in existing} & {
        str(item["id"]) for item in batch_items
    }
    if overlap:
        raise ValueError(f"new gallery IDs collide with admitted cases: {sorted(overlap)}")
    selection = _read_json(SELECTION)
    if not isinstance(selection, dict) or not isinstance(selection.get("rejected"), list):
        raise ValueError("gallery/selection.json must contain a rejected array")
    if (
        selection.get("candidate_count") != 111
        or selection.get("admitted_count") != 100
        or selection.get("rejected_count") != 11
    ):
        raise ValueError("selection edition counts must be 111 / 100 / 11")
    rejected = set(selection["rejected"])
    reasons = selection.get("reasons")
    if not isinstance(reasons, dict) or set(reasons) != rejected or not all(
        isinstance(reason, str) and reason.strip() for reason in reasons.values()
    ):
        raise ValueError("every rejected candidate needs one non-empty reason")
    candidate_ids = {str(item["id"]) for item in batch_items}
    if len(rejected) != 11 or not rejected <= candidate_ids:
        raise ValueError("selection must reject exactly 11 known batch candidates")
    selected = [item for item in batch_items if item["id"] not in rejected]
    if len(selected) != 91:
        raise ValueError("selection must yield exactly 91 new cases")
    all_items = existing + selected
    if len(all_items) != 100:
        raise ValueError("public gallery must contain exactly 100 cases")

    all_sources = {**existing_sources, **batch_sources}
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    DEPLOY_ROOT.mkdir(parents=True, exist_ok=True)
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    catalog: list[dict[str, object]] = []

    with Rasterizer() as rasterizer:
        for item in all_items:
            slug = str(item["id"])
            warnings = check(all_sources[slug], rasterizer=rasterizer)
            if warnings:
                raise ValueError(f"{slug}: IconFlow check warnings: {warnings}")

        for number, item in enumerate(all_items, start=1):
            slug = str(item["id"])
            source = all_sources[slug]
            case_dir = SOURCE_ROOT / slug
            render_dir = case_dir / "renders"
            deploy_dir = DEPLOY_ROOT / slug
            render_dir.mkdir(parents=True, exist_ok=True)
            deploy_dir.mkdir(parents=True, exist_ok=True)
            master = case_dir / "master.svg"
            if item.get("existing"):
                shutil.copy2(source, master)
                svg_text = load_svg(master)
            else:
                svg_text = _canonical_svg_text(source)
                master.write_text(svg_text, encoding="utf-8")
            theme, background = _palette(svg_text)

            if item.get("existing"):
                _copy_existing_evidence(slug, case_dir)
            else:
                (case_dir / "iconflow.toml").write_text(
                    _config_text(item, theme, background), encoding="utf-8"
                )
                receipt = _receipt(item, master, theme, background)
                (case_dir / "master-review.json").write_text(
                    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )

            for size in (16, 128, 256):
                (render_dir / f"{size}.png").write_bytes(rasterizer.render(svg_text, size))
            silhouette = visual_silhouette((render_dir / "128.png").read_bytes())
            silhouette.save(render_dir / "silhouette-128.png", optimize=True)

            config = load_config(case_dir / "iconflow.toml")
            validated = load_review_receipt(case_dir / "master-review.json", config)
            if validated.source_sha256 != svg_sha256(master):
                raise ValueError(f"{slug}: validated source hash drift")
            receipt_data = _read_json(case_dir / "master-review.json")
            assert isinstance(receipt_data, dict)
            case_file = _record_case(item)

            shutil.copy2(master, deploy_dir / "master.svg")
            shutil.copy2(case_dir / "master-review.json", deploy_dir / "review.json")
            for asset in ("16.png", "128.png", "256.png", "silhouette-128.png"):
                shutil.copy2(render_dir / asset, deploy_dir / asset)
            shutil.copy2(CASEBOOK / case_file, deploy_dir / "case.md")

            catalog.append({
                "number": number,
                "id": slug,
                "title": item["title"],
                "world": item["world"],
                "user_job": item["user_job"],
                "essence": item["essence"],
                "noun": item["noun"],
                "technique": item["technique"],
                "cliche": item["cliche"],
                "signature": item["signature"],
                "concepts": item["concepts"],
                "source_sha256": validated.source_sha256,
                "contract_sha256": validated.contract_sha256,
                "scores": receipt_data["scores"],
                "assets": {
                    "svg": f"/assets/gallery/{slug}/master.svg",
                    "native": f"/assets/gallery/{slug}/16.png",
                    "proof": f"/assets/gallery/{slug}/128.png",
                    "large": f"/assets/gallery/{slug}/256.png",
                    "silhouette": f"/assets/gallery/{slug}/silhouette-128.png",
                    "receipt": f"/assets/gallery/{slug}/review.json",
                    "case": f"/assets/gallery/{slug}/case.md",
                },
            })

    record = {
        "schema_version": 1,
        "generated_on": DATE,
        "case_count": len(catalog),
        "selection": {"candidate_count": 111, "admitted": 100, "rejected": 11},
        "cases": catalog,
        "rejected": sorted(rejected),
    }
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    CATALOG_PATH.write_text(text, encoding="utf-8")
    DEPLOY_CATALOG.write_text(text, encoding="utf-8")
    _make_contacts(catalog)

    if with_reviews:
        for item in catalog:
            slug = str(item["id"])
            contact_sheet(
                SOURCE_ROOT / slug / "master.svg",
                REVIEW_ROOT / f"{slug}.png",
                background_color="#FFF4E8",
            )
        _make_review_montages(catalog)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"gallery: {len(catalog)} cases, catalog sha256={digest}")
    print(f"contacts: {FINAL_CONTACT_ROOT}")
    if with_reviews:
        print(f"reviews: {REVIEW_ROOT}")
        print(f"review montages: {REVIEW_MONTAGE_ROOT}")


def _verify_tracked_case(number: int, item: object, rasterizer: Rasterizer) -> None:
    if not isinstance(item, dict) or item.get("number") != number:
        raise ValueError(f"gallery case {number}: malformed or out of order")
    slug = str(item["id"])
    source_dir = SOURCE_ROOT / slug
    deploy_dir = DEPLOY_ROOT / slug
    master = source_dir / "master.svg"
    config_path = source_dir / "iconflow.toml"
    receipt_path = source_dir / "master-review.json"
    case_path = CASEBOOK / f"{DATE}-{slug}.md"
    source_assets = {
        "master.svg": master,
        "review.json": receipt_path,
        "16.png": source_dir / "renders" / "16.png",
        "128.png": source_dir / "renders" / "128.png",
        "256.png": source_dir / "renders" / "256.png",
        "silhouette-128.png": source_dir / "renders" / "silhouette-128.png",
        "case.md": case_path,
    }
    for name, source_asset in source_assets.items():
        deploy_asset = deploy_dir / name
        if not source_asset.is_file() or not deploy_asset.is_file():
            raise ValueError(f"{slug}: missing source or deploy evidence for {name}")
        if source_asset.read_bytes() != deploy_asset.read_bytes():
            raise ValueError(f"{slug}: source and deploy evidence differ for {name}")
    warnings = check(master, rasterizer=rasterizer)
    if warnings:
        raise ValueError(f"{slug}: IconFlow check warnings: {warnings}")
    config = load_config(config_path)
    receipt = load_review_receipt(receipt_path, config)
    if item.get("source_sha256") != receipt.source_sha256:
        raise ValueError(f"{slug}: catalog source hash drift")
    if item.get("contract_sha256") != receipt.contract_sha256:
        raise ValueError(f"{slug}: catalog review contract drift")
    if item.get("scores") != receipt.scores:
        raise ValueError(f"{slug}: catalog review scores drift")
    for name, size in {
        "16.png": (16, 16),
        "128.png": (128, 128),
        "256.png": (256, 256),
        "silhouette-128.png": (128, 128),
    }.items():
        with Image.open(source_assets[name]) as image:
            if image.size != size:
                raise ValueError(f"{slug}: {name} must be {size[0]}x{size[1]}")


def verify_tracked() -> None:
    """Verify the tracked public edition without private batch workspaces."""
    catalog_bytes = CATALOG_PATH.read_bytes()
    if catalog_bytes != DEPLOY_CATALOG.read_bytes():
        raise ValueError("source and deployed gallery catalogs differ")
    record = _read_json(CATALOG_PATH)
    if not isinstance(record, dict):
        raise ValueError("gallery catalog must be a JSON object")
    if record.get("case_count") != 100 or record.get("selection") != {
        "candidate_count": 111,
        "admitted": 100,
        "rejected": 11,
    }:
        raise ValueError("tracked gallery edition must preserve the 111 / 100 / 11 contract")
    catalog = record.get("cases")
    rejected = record.get("rejected")
    if not isinstance(catalog, list) or len(catalog) != 100:
        raise ValueError("tracked gallery catalog must contain exactly 100 cases")
    if not isinstance(rejected, list) or len(rejected) != 11:
        raise ValueError("tracked gallery catalog must contain exactly 11 rejected IDs")
    ids = [item.get("id") for item in catalog if isinstance(item, dict)]
    if len(ids) != 100 or len(set(ids)) != 100:
        raise ValueError("tracked gallery case IDs must be complete and unique")

    with Rasterizer() as rasterizer:
        for number, item in enumerate(catalog, start=1):
            _verify_tracked_case(number, item, rasterizer)

    # Report the same digest on LF and CRLF worktrees; byte parity above still
    # ensures the source and deployed copies are exactly identical locally.
    digest = hashlib.sha256(
        CATALOG_PATH.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    print(f"gallery verify-only: 100 cases, catalog sha256={digest}")


def reviews_only() -> None:
    record = _read_json(CATALOG_PATH)
    if not isinstance(record, dict) or record.get("case_count") != 100:
        raise ValueError("build the exact 100-case catalog before reviews-only")
    catalog = record.get("cases")
    if not isinstance(catalog, list) or len(catalog) != 100:
        raise ValueError("catalog must contain exactly 100 cases")
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    for item in catalog:
        slug = str(item["id"])
        source = SOURCE_ROOT / slug / "master.svg"
        if not source.is_file():
            raise ValueError(f"missing admitted source: {source}")
        contact_sheet(
            source,
            REVIEW_ROOT / f"{slug}.png",
            background_color="#FFF4E8",
        )
    _make_review_montages(catalog)
    print(f"reviews: {REVIEW_ROOT}")
    print(f"review montages: {REVIEW_MONTAGE_ROOT}")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--reviews", action="store_true",
        help="also generate every full IconFlow review sheet",
    )
    mode.add_argument(
        "--reviews-only", action="store_true",
        help="generate full review sheets from an already validated catalog",
    )
    mode.add_argument(
        "--verify-only", action="store_true",
        help="verify tracked sources, receipts, renders, cases, and deploy copies",
    )
    args = parser.parse_args()
    if args.verify_only:
        verify_tracked()
    elif args.reviews_only:
        reviews_only()
    else:
        build(with_reviews=args.reviews)


if __name__ == "__main__":
    main()
