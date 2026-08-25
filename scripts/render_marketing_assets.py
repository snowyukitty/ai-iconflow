# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Render IconFlow's evidence-led marketing image set from exact project assets."""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import shutil
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
DOCS_OUTPUT = ROOT / "docs" / "assets" / "marketing"
SITE_OUTPUT = ROOT / "website" / "assets" / "marketing"
REVIEW_OUTPUT = ROOT / "work" / "marketing" / "marketing-board.html"
MANIFEST_OUTPUT = DOCS_OUTPUT / "manifest.json"

WORLD_CASES = (
    ("Forest Familiar", "forest-familiar"),
    ("Sky Courier", "sky-courier"),
    ("Koi Return", "koi-return"),
    ("Keepsake Knot", "keepsake-knot"),
    ("Boss Helm", "boss-helm"),
    ("Catnap Focus", "catnap-focus"),
)


@dataclass(frozen=True)
class Frame:
    name: str
    width: int
    height: int
    body: str


TEXT_INPUT_SUFFIXES = {".json", ".py", ".svg"}


def hash_record(path: Path) -> dict[str, str]:
    """Return a cross-platform digest plus the byte contract it uses."""
    if path.suffix.lower() in TEXT_INPUT_SUFFIXES:
        payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        mode = "utf8-lf"
    else:
        payload = path.read_bytes()
        mode = "raw-bytes"
    return {"sha256": hashlib.sha256(payload).hexdigest(), "mode": mode}


def source_paths() -> tuple[Path, ...]:
    """List every repository asset embedded into at least one campaign frame."""
    fixed = (
        ROOT / "brand" / "master.svg",
        ROOT / "brand" / "master-review.json",
        ROOT / "website" / "assets" / "proof" / "icon-16.png",
        ROOT / "website" / "assets" / "proof" / "icon-32.png",
        ROOT / "website" / "assets" / "proof" / "icon-128.png",
        ROOT / "brand" / "build" / "icon-192.png",
        ROOT / "brand" / "build" / "icons" / "128x128.png",
        ROOT / "brand" / "build" / "tray" / "tray.png",
    )
    worlds = tuple(
        ROOT / "website" / "assets" / "worlds" / f"{slug}-{size}.png"
        for _, slug in WORLD_CASES
        for size in (16, 128)
    )
    return fixed + worlds


def write_manifest(rendered: tuple[Frame, ...]) -> None:
    """Bind every frame to the exact generator, sources, and output bytes."""
    inputs = (Path(__file__).resolve(),) + source_paths()
    manifest = {
        "schema": 1,
        "generator": "scripts/render_marketing_assets.py",
        "render_contract": {
            "browser": "Playwright Chromium from the project environment",
            "color_profile": "sRGB",
            "device_scale_factor": 1,
            "javascript": False,
            "network": "blocked",
            "fonts": [
                "Segoe UI Variable Display",
                "Segoe UI",
                "Arial",
                "Cascadia Mono",
                "Consolas",
            ],
            "reproducibility_scope": (
                "Source freshness and output identity are exact; raster bytes are "
                "reproducible within the pinned project browser and host font stack."
            ),
        },
        "inputs": {
            path.relative_to(ROOT).as_posix(): hash_record(path)
            for path in inputs
        },
        "outputs": {
            frame.name: {
                "width": frame.width,
                "height": frame.height,
                "sha256": hash_record(DOCS_OUTPUT / frame.name)["sha256"],
            }
            for frame in rendered
        },
    }
    MANIFEST_OUTPUT.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def data_uri(path: Path) -> str:
    """Return a local project asset as an embeddable, network-free data URI."""
    mime = mimetypes.guess_type(path.name)[0]
    if mime is None:
        raise ValueError(f"unknown asset MIME type: {path}")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def img(path: Path, *, class_name: str = "", alt: str = "") -> str:
    classes = f' class="{escape(class_name)}"' if class_name else ""
    return f'<img{classes} src="{data_uri(path)}" alt="{escape(alt)}">'


def page(frame: Frame) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={frame.width}, initial-scale=1">
<style>
  :root {{
    --graphite: #191a20;
    --graphite-2: #23242b;
    --paper: #fff4e8;
    --paper-dim: #d9d0c7;
    --coral: #ff5a4f;
    --lagoon: #59c7c1;
    --gold: #f2b84b;
    --violet: #845ec2;
    --green: #5fd08a;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    width: {frame.width}px;
    height: {frame.height}px;
    overflow: hidden;
    background: var(--graphite);
    color: var(--paper);
    font-family: "Segoe UI Variable Display", "Segoe UI", Arial, sans-serif;
  }}
  body {{ position: relative; }}
  body::before {{
    content: "";
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,244,232,.055) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,244,232,.055) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
  }}
  .frame {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
  .frame::after {{
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 8px;
    background: var(--coral);
  }}
  h1, h2, h3, p {{ margin: 0; }}
  .eyebrow {{
    color: var(--coral);
    font-size: 17px;
    font-weight: 800;
    letter-spacing: .19em;
    text-transform: uppercase;
  }}
  .mono {{
    font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
    font-variant-numeric: tabular-nums;
  }}
  .panel {{
    background: rgba(35,36,43,.96);
    border: 1px solid rgba(255,244,232,.20);
    border-radius: 22px;
  }}
  .pill {{
    display: inline-flex;
    align-items: center;
    gap: 9px;
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid rgba(255,244,232,.22);
    border-radius: 999px;
    background: rgba(255,244,232,.055);
    color: var(--paper-dim);
    font-size: 14px;
    font-weight: 650;
  }}
  .dot {{ width: 9px; height: 9px; border-radius: 50%; background: var(--green); }}
  .pixelated {{ image-rendering: pixelated; image-rendering: crisp-edges; }}
  img {{ display: block; }}
  {frame.body}
</style>
</head>
<body>{frame_html(frame.name)}</body>
</html>"""


def proof_assets() -> dict[str, str]:
    receipt = json.loads((ROOT / "brand" / "master-review.json").read_text(encoding="utf-8"))
    return {
        "master": img(ROOT / "brand" / "master.svg", class_name="master-mark"),
        "native16": img(
            ROOT / "website" / "assets" / "proof" / "icon-16.png",
            class_name="native-16 pixelated",
        ),
        "native128": img(
            ROOT / "website" / "assets" / "proof" / "icon-128.png",
            class_name="native-128",
        ),
        "hash": escape(receipt["source_sha256"][:12]),
        "scores": " / ".join(str(receipt["scores"][key]) for key in (
            "legibility", "distinctiveness", "balance", "color", "scalability", "craft"
        )),
    }


def frame_html(name: str) -> str:
    proof = proof_assets()
    if name == "proof-at-16-1200x630.png":
        return f"""
<main class="frame proof-wide">
  <header>
    <div class="eyebrow">IconFlow · Native-size proof</div>
    <h1>Looks polished large.<br><em>Prove it at 16.</em></h1>
    <p>Color, silhouette, crop, and receipt—bound to the exact source.</p>
  </header>
  <section class="proof-stages" aria-label="Vector source, native pixels, and review gate">
    <article class="stage panel source-stage">
      <span class="stage-label mono">MASTER.SVG</span>
      <div class="mark-pad">{proof["master"]}</div>
      <b>Editable source</b>
    </article>
    <div class="rail-arrow" aria-hidden="true"><span></span><i></i></div>
    <article class="stage panel pixel-stage">
      <span class="stage-label mono">NATIVE 16 PX</span>
      <div class="pixel-window">{proof["native16"]}</div>
      <b>Exact pixels</b>
    </article>
    <div class="rail-arrow" aria-hidden="true"><span></span><i></i></div>
    <article class="stage panel receipt-stage">
      <span class="stage-label mono">SOURCE-BOUND</span>
      <div class="receipt-head"><span class="dot"></span><b>REVIEW GATE PASSED</b></div>
      <dl class="mono">
        <div><dt>source</dt><dd>{proof["hash"]}</dd></div>
        <div><dt>scores</dt><dd>{proof["scores"]}</dd></div>
        <div><dt>status</dt><dd>ready</dd></div>
      </dl>
      <span class="pill"><span class="dot"></span>all six axes ≥ 4/5</span>
    </article>
  </section>
  <footer><span class="mono">BRIEF → EXPLORE → COMPARE → INSPECT → SHIP → LEARN</span><b>One master. Every surface. Proven at 16px.</b></footer>
</main>"""
    if name == "workflow-1200x630.png":
        target_paths = (
            ("FAVICON", ROOT / "website" / "assets" / "proof" / "icon-32.png"),
            ("PWA", ROOT / "brand" / "build" / "icon-192.png"),
            ("DESKTOP", ROOT / "brand" / "build" / "icons" / "128x128.png"),
            ("TRAY", ROOT / "brand" / "build" / "tray" / "tray.png"),
        )
        targets = "".join(
            f'<div class="target"><span>{label}</span>{img(path)}</div>'
            for label, path in target_paths
        )
        return f"""
<main class="frame workflow-wide">
  <header>
    <div class="eyebrow">IconFlow · The decision workflow</div>
    <h1>One source. A visible decision.<br><em>Every target.</em></h1>
    <p>Generators make options. Converters make files. IconFlow proves what ships.</p>
  </header>
  <section class="workflow-cards">
    <article class="flow-card panel source-card">
      <span class="step mono">01 · SOURCE</span>
      <div class="source-visual">{proof["master"]}</div>
      <h2>Semantic SVG</h2>
      <p>One editable master.</p>
    </article>
    <div class="connector"><span></span></div>
    <article class="flow-card panel inspect-card">
      <span class="step mono">02 · PROVE</span>
      <div class="inspect-visual">
        {proof["native128"]}
        <div class="inspect-pixel">{proof["native16"]}<span class="mono">16px</span></div>
      </div>
      <h2>Inspect the pixels</h2>
      <p>Silhouette · crops · receipt.</p>
    </article>
    <div class="connector"><span></span></div>
    <article class="flow-card panel targets-card">
      <span class="step mono">03 · SHIP</span>
      <div class="target-grid">{targets}</div>
      <h2>Exact outputs</h2>
      <p>Web · PWA · desktop · tray.</p>
    </article>
  </section>
  <footer><code>pip install iconflow</code><span class="mono">setup → compare → review → ship</span></footer>
</main>"""
    if name == "many-worlds-1200x630.png":
        cards = "".join(
            f"""<article class="world panel">
              <div class="world-mark">{img(ROOT / "website" / "assets" / "worlds" / f"{slug}-128.png")}</div>
              <div class="world-copy"><h2>{title}</h2><span class="mono">exact 16px</span></div>
              <div class="world-native">{img(ROOT / "website" / "assets" / "worlds" / f"{slug}-16.png")}</div>
            </article>"""
            for title, slug in WORLD_CASES
        )
        return f"""
<main class="frame worlds-wide">
  <header>
    <div><div class="eyebrow">IconFlow · Reviewed case evidence</div><h1>One small-size contract.<br><em>Many worlds.</em></h1></div>
    <dl class="counts mono"><div><dt>100</dt><dd>reviewed cases</dd></div><div><dt>20</dt><dd>technique scaffolds</dd></div><div><dt>137</dt><dd>archive marks</dd></div></dl>
  </header>
  <section class="world-grid">{cards}</section>
  <footer><span>Every large specimen is source-linked.</span><b>Every tiny chip is the exact native 16×16 PNG.</b></footer>
</main>"""
    if name == "proof-at-16-1080x1080.png":
        return f"""
<main class="frame proof-square">
  <header><div class="eyebrow">IconFlow · Native-size proof</div><h1>The proof<br><em>is the pixel.</em></h1><p>One editable SVG. Exact 16px evidence. A receipt that goes stale when the source changes.</p></header>
  <section>
    <div class="square-master panel"><span class="mono">VECTOR SOURCE</span>{proof["master"]}</div>
    <div class="square-pixel panel"><span class="mono">NATIVE 16 PX</span><div>{proof["native16"]}</div></div>
  </section>
  <aside class="square-receipt panel"><span class="dot"></span><b>REVIEW GATE PASSED</b><span class="mono">{proof["scores"]}</span></aside>
  <footer><b>One master. Every surface.</b><code>pip install iconflow</code></footer>
</main>"""
    if name == "proof-at-16-1080x1920.png":
        target_paths = (
            ("FAVICON", ROOT / "website" / "assets" / "proof" / "icon-32.png"),
            ("PWA", ROOT / "brand" / "build" / "icon-192.png"),
            ("DESKTOP", ROOT / "brand" / "build" / "icons" / "128x128.png"),
            ("TRAY", ROOT / "brand" / "build" / "tray" / "tray.png"),
        )
        outputs = "".join(
            f'<div class="story-target panel">{img(path)}<span class="mono">{label}</span></div>'
            for label, path in target_paths
        )
        return f"""
<main class="frame proof-story">
  <header><div class="eyebrow">IconFlow · Proof before pixels ship</div><h1>Looks polished<br>large.<br><em>Prove it at 16.</em></h1></header>
  <section class="story-source panel"><span class="mono">ONE EDITABLE MASTER</span>{proof["master"]}</section>
  <div class="story-rail"><span></span><b class="mono">SOURCE → PROOF → TARGETS</b></div>
  <section class="story-proof panel"><div><span class="mono">EXACT NATIVE PIXELS</span><h2>16×16</h2><p>No smoothing. No redraw.</p></div><div class="story-pixel">{proof["native16"]}</div></section>
  <section class="story-targets">{outputs}</section>
  <aside class="story-receipt panel"><span class="dot"></span><div><b>REVIEW GATE PASSED</b><span>all six axes ≥ 4/5 · source-bound</span></div></aside>
  <footer><h2>One master.<br>Every surface.<br><em>Proven at 16px.</em></h2><code>pip install iconflow</code></footer>
</main>"""
    raise ValueError(f"unknown frame: {name}")


def frames() -> tuple[Frame, ...]:
    wide_proof_css = """
      .proof-wide { padding: 54px 58px 42px; }
      .proof-wide header { width: 570px; }
      .proof-wide h1 { margin-top: 15px; font-size: 48px; line-height: 1.04; letter-spacing: -.035em; }
      .proof-wide h1 em { color: var(--coral); font-style: normal; }
      .proof-wide header p { margin-top: 15px; color: var(--paper-dim); font-size: 19px; }
      .proof-stages { position: absolute; left: 58px; right: 58px; top: 265px; display: grid; grid-template-columns: 245px 54px 245px 54px 1fr; align-items: center; }
      .stage { height: 248px; padding: 18px; overflow: hidden; }
      .stage-label { color: var(--coral); font-size: 12px; font-weight: 800; letter-spacing: .11em; }
      .mark-pad { margin: 14px auto 9px; width: 136px; height: 136px; padding: 10px; border-radius: 26px; background: var(--paper); }
      .mark-pad .master-mark { width: 100%; height: 100%; }
      .stage > b { display: block; font-size: 16px; }
      .pixel-window { margin: 14px auto 9px; width: 136px; height: 136px; background: var(--paper); border: 8px solid var(--paper); box-shadow: 0 0 0 1px rgba(255,244,232,.22); }
      .pixel-window .native-16 { width: 128px; height: 128px; }
      .receipt-stage { padding: 22px; }
      .receipt-head { display: flex; align-items: center; gap: 10px; margin: 22px 0 16px; font-size: 15px; }
      .receipt-stage dl { margin: 0 0 15px; font-size: 13px; color: var(--paper-dim); }
      .receipt-stage dl div { display: grid; grid-template-columns: 72px 1fr; margin: 7px 0; }
      .receipt-stage dt { color: #8e9099; }
      .receipt-stage dd { margin: 0; color: var(--paper); }
      .rail-arrow { display: flex; align-items: center; }
      .rail-arrow span { height: 4px; flex: 1; background: var(--paper); border-radius: 4px; }
      .rail-arrow i { width: 12px; height: 12px; border-top: 4px solid var(--paper); border-right: 4px solid var(--paper); transform: rotate(45deg); }
      .proof-wide footer { position: absolute; left: 58px; right: 58px; bottom: 22px; display: flex; justify-content: space-between; align-items: center; }
      .proof-wide footer span { color: #a9abb4; font-size: 11px; letter-spacing: .03em; }
      .proof-wide footer b { font-size: 13px; }
    """
    workflow_css = """
      .workflow-wide { padding: 48px 56px 42px; }
      .workflow-wide header { max-width: 850px; }
      .workflow-wide h1 { margin-top: 12px; font-size: 44px; line-height: 1.02; letter-spacing: -.035em; }
      .workflow-wide h1 em { color: var(--coral); font-style: normal; }
      .workflow-wide header p { margin-top: 12px; color: var(--paper-dim); font-size: 18px; }
      .workflow-cards { position: absolute; left: 56px; right: 56px; top: 238px; display: grid; grid-template-columns: 1fr 48px 1fr 48px 1.18fr; align-items: center; }
      .flow-card { height: 290px; padding: 18px; }
      .step { color: var(--coral); font-size: 11px; font-weight: 800; letter-spacing: .1em; }
      .source-visual { width: 136px; height: 136px; margin: 15px auto 10px; padding: 9px; border-radius: 26px; background: var(--paper); }
      .source-visual img { width: 100%; height: 100%; }
      .flow-card h2 { font-size: 18px; }
      .flow-card > p { margin-top: 5px; color: var(--paper-dim); font-size: 13px; }
      .connector span { display: block; height: 4px; background: var(--paper); position: relative; }
      .connector span::after { content: ""; position: absolute; right: -1px; top: -4px; width: 9px; height: 9px; border-top: 4px solid var(--paper); border-right: 4px solid var(--paper); transform: rotate(45deg); }
      .inspect-visual { height: 164px; margin: 12px 0 10px; display: flex; align-items: center; justify-content: center; gap: 14px; }
      .inspect-visual > .native-128 { width: 132px; height: 132px; border: 6px solid var(--paper); }
      .inspect-pixel { position: relative; width: 112px; height: 112px; background: var(--paper); border: 6px solid var(--paper); }
      .inspect-pixel img { width: 100px; height: 100px; }
      .inspect-pixel span { position: absolute; left: 0; bottom: -27px; color: var(--paper-dim); font-size: 11px; }
      .target-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 13px 0 12px; }
      .target { height: 75px; display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 12px; background: #111216; }
      .target img { width: 48px; height: 48px; object-fit: contain; image-rendering: auto; }
      .target span { font: 700 10px "Cascadia Mono", Consolas, monospace; color: var(--paper-dim); }
      .workflow-wide footer { position: absolute; left: 56px; right: 56px; bottom: 23px; display: flex; justify-content: space-between; align-items: center; }
      .workflow-wide footer code { padding: 10px 16px; border-radius: 10px; background: var(--paper); color: var(--graphite); font: 700 15px "Cascadia Mono", Consolas, monospace; }
      .workflow-wide footer span { color: #a9abb4; font-size: 12px; }
    """
    worlds_css = """
      .worlds-wide { padding: 46px 54px 38px; }
      .worlds-wide header { display: flex; justify-content: space-between; align-items: end; }
      .worlds-wide h1 { margin-top: 12px; font-size: 43px; line-height: 1.02; letter-spacing: -.035em; }
      .worlds-wide h1 em { color: var(--coral); font-style: normal; }
      .counts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; width: 456px; }
      .counts div { padding-left: 14px; border-left: 2px solid var(--coral); }
      .counts dt { font-size: 28px; font-weight: 800; color: var(--paper); }
      .counts dd { margin: 3px 0 0; color: var(--paper-dim); font-size: 10px; text-transform: uppercase; letter-spacing: .07em; }
      .world-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 13px; margin-top: 24px; }
      .world { height: 156px; padding: 13px; display: grid; grid-template-columns: 116px 1fr 28px; gap: 14px; align-items: center; }
      .world-mark { width: 116px; height: 116px; padding: 4px; border-radius: 17px; background: var(--paper); }
      .world-mark img { width: 108px; height: 108px; }
      .world h2 { font-size: 17px; line-height: 1.08; }
      .world-copy span { display: block; margin-top: 9px; color: var(--paper-dim); font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }
      .world-native { align-self: end; width: 24px; height: 24px; padding: 4px; border: 1px solid rgba(255,244,232,.25); background: #111216; }
      .world-native img { width: 16px; height: 16px; }
      .worlds-wide footer { position: absolute; left: 54px; right: 54px; bottom: 21px; display: flex; justify-content: space-between; color: var(--paper-dim); font-size: 12px; }
      .worlds-wide footer b { color: var(--paper); }
    """
    square_css = """
      .proof-square { padding: 72px 68px 60px; }
      .proof-square h1 { margin-top: 18px; font-size: 84px; line-height: .96; letter-spacing: -.045em; }
      .proof-square h1 em { color: var(--coral); font-style: normal; }
      .proof-square header p { margin-top: 24px; max-width: 770px; color: var(--paper-dim); font-size: 24px; line-height: 1.35; }
      .proof-square > section { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 54px; }
      .square-master, .square-pixel { height: 344px; padding: 22px; }
      .square-master > span, .square-pixel > span { color: var(--coral); font-size: 13px; font-weight: 800; letter-spacing: .12em; }
      .square-master .master-mark { width: 248px; height: 248px; margin: 20px auto 0; }
      .square-pixel > div { width: 248px; height: 248px; margin: 20px auto 0; background: var(--paper); border: 12px solid var(--paper); }
      .square-pixel .native-16 { width: 224px; height: 224px; }
      .square-receipt { margin-top: 24px; height: 74px; display: flex; align-items: center; gap: 14px; padding: 0 22px; }
      .square-receipt b { font-size: 17px; }
      .square-receipt > span:last-child { margin-left: auto; color: var(--paper-dim); font-size: 13px; }
      .proof-square footer { position: absolute; left: 68px; right: 68px; bottom: 42px; display: flex; justify-content: space-between; align-items: center; }
      .proof-square footer b { font-size: 18px; }
      .proof-square footer code { padding: 14px 18px; background: var(--paper); color: var(--graphite); border-radius: 12px; font: 700 16px "Cascadia Mono", Consolas, monospace; }
    """
    story_css = """
      .proof-story { padding: 90px 72px 72px; }
      .proof-story h1 { margin-top: 22px; font-size: 86px; line-height: .98; letter-spacing: -.047em; }
      .proof-story h1 em { color: var(--coral); font-style: normal; }
      .story-source { width: 100%; height: 390px; margin-top: 64px; padding: 24px; }
      .story-source > span { color: var(--coral); font-size: 13px; font-weight: 800; letter-spacing: .12em; }
      .story-source .master-mark { width: 300px; height: 300px; margin: 26px auto 0; }
      .story-rail { height: 100px; display: flex; flex-direction: column; justify-content: center; gap: 16px; }
      .story-rail span { height: 6px; background: var(--paper); position: relative; border-radius: 4px; }
      .story-rail span::after { content: ""; position: absolute; right: -1px; top: -7px; width: 16px; height: 16px; border-top: 6px solid var(--paper); border-right: 6px solid var(--paper); transform: rotate(45deg); }
      .story-rail b { color: var(--paper-dim); font-size: 12px; letter-spacing: .06em; }
      .story-proof { height: 286px; padding: 30px; display: flex; align-items: center; justify-content: space-between; }
      .story-proof span { color: var(--coral); font-size: 13px; font-weight: 800; letter-spacing: .11em; }
      .story-proof h2 { margin-top: 12px; font-size: 60px; }
      .story-proof p { margin-top: 8px; color: var(--paper-dim); font-size: 17px; }
      .story-pixel { width: 228px; height: 228px; padding: 10px; background: var(--paper); }
      .story-pixel img { width: 208px; height: 208px; }
      .story-targets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 24px; }
      .story-target { height: 148px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; }
      .story-target img { width: 76px; height: 76px; object-fit: contain; }
      .story-target span { color: var(--paper-dim); font-size: 10px; }
      .story-receipt { height: 86px; margin-top: 24px; display: flex; align-items: center; gap: 16px; padding: 0 24px; }
      .story-receipt b { display: block; font-size: 17px; }
      .story-receipt div span { display: block; margin-top: 5px; color: var(--paper-dim); font-size: 13px; }
      .proof-story footer { margin-top: 48px; }
      .proof-story footer h2 { font-size: 58px; line-height: 1.04; letter-spacing: -.035em; }
      .proof-story footer h2 em { color: var(--coral); font-style: normal; }
      .proof-story footer code { display: block; margin-top: 34px; padding: 24px 28px; border-radius: 16px; background: var(--paper); color: var(--graphite); font: 700 24px "Cascadia Mono", Consolas, monospace; text-align: center; }
    """
    return (
        Frame("proof-at-16-1200x630.png", 1200, 630, wide_proof_css),
        Frame("workflow-1200x630.png", 1200, 630, workflow_css),
        Frame("many-worlds-1200x630.png", 1200, 630, worlds_css),
        Frame("proof-at-16-1080x1080.png", 1080, 1080, square_css),
        Frame("proof-at-16-1080x1920.png", 1080, 1920, story_css),
    )


def render() -> None:
    DOCS_OUTPUT.mkdir(parents=True, exist_ok=True)
    SITE_OUTPUT.mkdir(parents=True, exist_ok=True)
    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    board_cards: list[str] = []
    rendered = frames()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--force-color-profile=srgb"])
        try:
            for frame in rendered:
                output = DOCS_OUTPUT / frame.name
                document = page(frame)
                context = browser.new_context(
                    viewport={"width": frame.width, "height": frame.height},
                    device_scale_factor=1,
                    java_script_enabled=False,
                    service_workers="block",
                    locale="en-US",
                    timezone_id="UTC",
                )
                context.route("**/*", lambda route: route.abort("blockedbyclient"))
                canvas = context.new_page()
                canvas.set_content(document, wait_until="domcontentloaded")
                canvas.screenshot(path=str(output), type="png", animations="disabled")
                context.close()
                with Image.open(output) as image:
                    image.load()
                    if image.size != (frame.width, frame.height) or image.format != "PNG":
                        raise ValueError(
                            f"unexpected marketing asset {frame.name}: "
                            f"{image.format} {image.size}"
                        )
                shutil.copy2(output, SITE_OUTPUT / frame.name)
                board_cards.append(
                    f'<figure><img src="data:image/png;base64,'
                    f'{base64.b64encode(output.read_bytes()).decode("ascii")}" '
                    f'alt="{escape(frame.name)}"><figcaption>{escape(frame.name)}</figcaption></figure>'
                )
                print(f"Rendered {output.relative_to(ROOT)} ({frame.width}x{frame.height})")
        finally:
            browser.close()
    write_manifest(rendered)
    REVIEW_OUTPUT.write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>IconFlow marketing board</title>"
        "<style>body{margin:0;padding:32px;background:#111216;color:#fff4e8;"
        "font:14px Segoe UI,Arial,sans-serif}main{display:grid;gap:32px}figure{margin:0}"
        "img{display:block;max-width:100%;max-height:88vh;margin:auto;border:1px solid #42434a}"
        "figcaption{text-align:center;margin-top:10px;color:#a9abb4}</style><main>"
        + "".join(board_cards)
        + "</main>",
        encoding="utf-8",
    )


def main() -> int:
    render()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"marketing asset render failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
