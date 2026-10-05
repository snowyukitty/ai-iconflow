# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Smoke-test the deployed /emotes/ page and its packs, as the edge serves them.

    python scripts/emotes_live_check.py                                   # production
    python scripts/emotes_live_check.py https://preview.iconflow.pages.dev

Every pack is downloaded and compared byte for byte with the checkout, so a
deploy that served a stale or truncated zip fails here. The page is driven in
Chromium and every emote image must actually decode. Console errors from the
edge-injected analytics beacon are reported, not failed (see docs/STATE.md).
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"
BEACON = ("cloudflareinsights",)


def fetch(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "iconflow-emotes-live-check"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    base = (argv[0] if argv else "https://ai-iconflow.com").rstrip("/")
    failures: list[str] = []

    def expect(ok: bool, label: str, detail: str = "") -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}{f'  ({detail})' if detail else ''}")
        if not ok:
            failures.append(label)

    print(f"Emotes live check: {base}/emotes/")
    status, headers, _ = fetch(f"{base}/emotes/")
    expect(status == 200, "page answers 200", str(status))
    csp = headers.get("content-security-policy", "")
    expect("script-src 'self'" in csp and "'unsafe-inline'" not in csp, "page carries the strict CSP")

    catalog = json.loads((SITE / "emotes" / "catalog.json").read_text(encoding="utf-8"))
    for name in catalog["packs"]:
        status, headers, body = fetch(f"{base}/emotes/{name}")
        local = (SITE / "emotes" / name).read_bytes()
        expect(status == 200 and body == local, f"{name} is the checked-in pack", f"{len(body):,} bytes")
        expect(headers.get("content-type", "").startswith("application/zip"), f"{name} served as a zip",
               headers.get("content-type", ""))
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            expect(archive.testzip() is None, f"{name} unzips cleanly")
    status, headers, body = fetch(f"{base}/emotes/svg/joy.svg")
    expect(status == 200 and body == (SITE / "emotes" / "svg" / "joy.svg").read_bytes(), "SVG source served unchanged")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        problems: list[str] = []
        page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and problems.append(m.text))
        page.on("requestfailed", lambda r: problems.append(f"requestfailed: {r.url}"))
        page.goto(f"{base}/emotes/", wait_until="load")
        # Lazy images load as they scroll in; walk the page so every one is asked for.
        page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {"
                      " window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } }")
        page.wait_for_load_state("networkidle")
        broken = page.evaluate("() => [...document.querySelectorAll('.emo-big img')]"
                               ".filter(i => !i.complete || i.naturalWidth !== 128).map(i => i.alt)")
        expect(page.locator(".emo-big img").count() == len(catalog["emotes"]), "every emote has a tile")
        expect(not broken, "every emote image decodes at 128px", ", ".join(broken))
        sheet = page.evaluate("() => document.querySelector('.emo-sheet img').naturalWidth")
        expect(sheet > 0, "family proof sheet loads")
        home = browser.new_page()
        home.goto(f"{base}/", wait_until="load")
        expect(home.locator('nav a[href="/emotes/"]').count() >= 1, "homepage nav links the emotes")
        ref = browser.new_page()
        ref.goto(f"{base}/reference/icon-sizes/", wait_until="load")
        expect(ref.locator("#emote table").count() == 1, "reference page has the emote table")
        browser.close()

    own = [p for p in problems if not any(b in p for b in BEACON)]
    edge = len(problems) - len(own)
    expect(not own, "no console errors of the page's own", "; ".join(own))
    if edge:
        print(f"  note edge-injected beacon blocked by the CSP ({edge} message(s)); see docs/STATE.md")
    print("PASS" if not failures else f"FAIL: {', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
