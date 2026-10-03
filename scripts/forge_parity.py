# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Prove the Forge's shapefield.js answers what iconflow/shapefield.py answers.

Renders every generic collision form, and the Forge's worked examples,
through the browser port in Chromium and compares the result with the Python
instrument: the collision forms against the checked-in index, the examples
against a fresh ``shapefield.field_from_svg`` render. Exits non-zero past the
same tolerances the index drift test uses (a field 0.03 apart, a quarter of
the collision radius; topology identical).

It also holds the worked examples to what they teach: each one, exported
exactly as the Forge's download writes it, must pass ``iconflow check`` with
no warning at all.

    python scripts/forge_parity.py
"""
from __future__ import annotations

import functools
import http.server
import json
import socket
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TOLERANCE = 0.03

PROBE = r"""async (sources) => {
  const sf = await import('/website/forge/shapefield.js');
  const load = (src) => new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = bad; i.src = src; });
  const out = {};
  for (const [name, src] of Object.entries(sources)) {
    const field = sf.fieldFromImage(await load(src));
    out[name] = { grid: field.grid, components: field.components, holes: field.holes, coverage: field.coverage };
  }
  return out;
}"""


def designs() -> dict[str, str]:
    """SVG text of Forge designs, exported by the Forge's own model.js."""
    script = (
        "import * as m from './website/forge/model.js';"
        "const out = { example: m.toSvg(m.example(), { metadata: true }) };"
        "for (const k of Object.keys(m.SEEDS || {})) out['seed-' + k] = m.toSvg(m.seed(k), { metadata: true });"
        "console.log(JSON.stringify(out));"
    )
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main() -> int:
    from playwright.sync_api import sync_playwright
    from iconflow import shapefield
    from iconflow.rasterize import Rasterizer

    index = json.loads((ROOT / "iconflow/resources/collision/index.json").read_text(encoding="utf-8"))
    collision = {e["id"]: e for e in index["entries"] if e["set"] == "collision"}
    sources = {i: "/" + e["source"] for i, e in collision.items()}
    forge = designs()
    sources.update({f"forge/{k}": "data:image/svg+xml;charset=utf-8," + __import__("urllib.parse").parse.quote(v)
                    for k, v in forge.items()})

    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    handler.extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}/website/forge/index.html")
            got = page.evaluate(PROBE, sources)
            browser.close()
    finally:
        httpd.shutdown()

    expected = {i: shapefield.ShapeField.from_dict(e["field"]) for i, e in collision.items()}
    with Rasterizer() as rasterizer:
        for name, svg in forge.items():
            expected[f"forge/{name}"] = shapefield.field_from_svg(svg, rasterizer)

    failures = 0
    import tempfile
    from iconflow import qa
    with tempfile.TemporaryDirectory() as scratch, Rasterizer() as rasterizer:
        for name, svg in forge.items():
            path = Path(scratch) / f"{name}.svg"
            path.write_text(svg, encoding="utf-8")
            findings = qa.check(path, rasterizer=rasterizer)
            failures += bool(findings)
            print(f"{'ok  ' if not findings else 'FAIL'} forge/{name:27} iconflow check: "
                  + ("; ".join(str(f) for f in findings) or "no warnings"))
    worst = 0.0
    for name, want in sorted(expected.items()):
        have = got[name]
        distance = shapefield.grid_distance(tuple(have["grid"]), want.grid)
        topology = (have["components"], have["holes"]) == (want.components, want.holes)
        worst = max(worst, distance)
        ok = distance <= TOLERANCE and topology
        failures += not ok
        if not ok or name.startswith("forge/"):
            print(f"{'ok  ' if ok else 'FAIL'} {name:32} distance {distance:.4f}  "
                  f"pieces {have['components']}/{want.components}  holes {have['holes']}/{want.holes}")
    print(f"forge parity: {len(expected) - failures}/{len(expected)} fields agree; worst distance {worst:.4f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
