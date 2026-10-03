# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Smoke-test a deployed Icon Forge, as the edge actually serves it.

tests/test_forge_browser.py proves the page against the CSP in _headers on a
local server. This proves the deploy: Cloudflare's real headers, MIME types,
caching and redirects, in Chromium, on the URL visitors use.

    python scripts/forge_live_check.py                                   # production
    python scripts/forge_live_check.py https://preview.iconflow.pages.dev

Exits non-zero on any failure. A console error caused by an edge-injected
third-party script (the Cloudflare Web Analytics beacon the CSP blocks; see
docs/STATE.md) is reported but does not fail the Forge, because it is not the
Forge's and appears on every page of the site.
"""
from __future__ import annotations

import sys
import urllib.request

BEACON = ("cloudflareinsights", "static.cloudflareinsights.com")
VENDOR = "/forge/vendor/three-0.169.0/three.module.min.js"


def head(url: str) -> dict[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "iconflow-forge-live-check"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return {k.lower(): v for k, v in response.headers.items()} | {":status": str(response.status)}


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    base = (argv[0] if argv else "https://ai-iconflow.com").rstrip("/")
    failures: list[str] = []

    def expect(ok: bool, label: str, detail: str = "") -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}{f'  ({detail})' if detail else ''}")
        if not ok:
            failures.append(label)

    print(f"Icon Forge live check: {base}/forge/")
    page_headers = head(f"{base}/forge/")
    expect(page_headers[":status"] == "200", "page answers 200", page_headers[":status"])
    csp = page_headers.get("content-security-policy", "")
    expect("script-src 'self'" in csp and "'unsafe-inline'" not in csp, "page carries the strict CSP")
    vendor = head(base + VENDOR)
    expect("javascript" in vendor.get("content-type", ""), "three.js served as JavaScript", vendor.get("content-type", ""))
    expect("immutable" in vendor.get("cache-control", ""), "vendored three.js cached immutable", vendor.get("cache-control", ""))
    card = head(f"{base}/assets/marketing/forge-1200x630.png")
    expect(card[":status"] == "200" and card.get("content-type") == "image/png", "social card served")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        problems: list[str] = []
        page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and problems.append(m.text))
        page.on("requestfailed", lambda r: problems.append(f"requestfailed: {r.url}"))
        page.goto(f"{base}/forge/", wait_until="load")
        page.wait_for_function("() => document.querySelectorAll('[data-forge-checks] li').length >= 6", timeout=30000)
        page.wait_for_function(
            "() => document.querySelector('[data-forge-stage] canvas')"
            " || !document.querySelector('[data-forge-nogl]').hidden", timeout=30000)
        expect(page.locator("[data-forge-stage] canvas").count() == 1, "3D workbench started")
        score = page.locator("[data-forge-score-text]").inner_text()
        expect(score == "Ready for the real review", "first-visit example passes every check", score)
        near = page.locator("[data-near-caption]").all_inner_texts()
        expect(all("·" in n for n in near), "neighbourhood panel names its nearest forms", "; ".join(near))
        page.click("[data-view=stamp]")
        page.wait_for_timeout(1200)
        page.select_option("[data-forge-example]", "tide")
        with page.expect_download() as download:
            page.click("[data-action=kit]")
        expect(download.value.suggested_filename == "my-icon.zip", "project kit downloads", download.value.suggested_filename)

        home = browser.new_page()
        home.goto(f"{base}/", wait_until="load")
        expect(home.locator('a[href="/forge/"] .button-cube').count() == 1, "homepage hero links the Forge")
        browser.close()

    own = [p for p in problems if not any(b in p for b in BEACON)]
    edge = [p for p in problems if any(b in p for b in BEACON)]
    expect(not own, "no console errors of the Forge's own", "; ".join(own))
    if edge:
        print(f"  note edge-injected beacon blocked by the CSP ({len(edge)} message(s)); see docs/STATE.md")
    print("PASS" if not failures else f"FAIL: {', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
