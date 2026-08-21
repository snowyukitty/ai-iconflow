# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Render the tracked social-preview SVG to its 1280x640 PNG derivative."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from iconflow.rasterize import load_svg


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "assets" / "social-preview.svg"
OUTPUT = ROOT / "docs" / "assets" / "social-preview.png"


def main() -> int:
    svg = load_svg(SOURCE)
    document = (
        '<!doctype html><meta charset="utf-8"><style>'
        "*{margin:0;padding:0}html,body,svg{width:1280px;height:640px;display:block;overflow:hidden}"
        "</style>" + svg
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--force-color-profile=srgb"])
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 640},
                device_scale_factor=1,
                java_script_enabled=False,
                service_workers="block",
                locale="en-US",
                timezone_id="UTC",
            )
            context.route("**/*", lambda route: route.abort("blockedbyclient"))
            page = context.new_page()
            page.set_content(document, wait_until="domcontentloaded")
            page.screenshot(path=str(OUTPUT), type="png", animations="disabled")
            context.close()
        finally:
            browser.close()
    with Image.open(OUTPUT) as image:
        image.load()
        if image.size != (1280, 640) or image.format != "PNG":
            raise ValueError(f"unexpected social preview: {image.format} {image.size}")
    print(f"Rendered {OUTPUT.relative_to(ROOT)} (1280x640)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"social preview render failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
