# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Render the public gallery from its admitted catalog, without a browser."""
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "website/gallery/index.html"


def render() -> str:
    catalog = json.loads((ROOT / "gallery/catalog.json").read_text(encoding="utf-8"))
    cases = catalog["cases"]
    if len(cases) != 100 or len({item["id"] for item in cases}) != 100:
        raise ValueError("Expected 100 unique admitted cases")
    cards = []
    entries = []
    for item in cases:
        value = {key: escape(str(item[key]), quote=True) for key in (
            "id", "title", "world", "technique", "noun", "user_job", "signature",
        )}
        asset = {key: escape(url, quote=True) for key, url in item["assets"].items()}
        cards.append(f'''<article id="case-{value['id']}" class="gallery-card" data-world="{value['world']}" data-case-id="{value['id']}">
          <a class="gallery-open" href="{asset['case']}" data-open-case="{value['id']}" aria-label="Open {value['title']} case">
            <span class="gallery-number">{item['number']:03d}</span>
            <span class="gallery-art"><img src="{asset['svg']}" data-color="{asset['svg']}" data-silhouette="{asset['silhouette']}" data-native="{asset['native']}" width="112" height="112" loading="lazy" alt="{value['noun']}"></span>
            <span class="gallery-native"><img src="{asset['native']}" width="16" height="16" alt="">actual 16×16</span>
            <span class="gallery-coordinate">{value['world']} · {value['technique']}</span>
            <h3>{value['title']}</h3>
            <span class="gallery-job">{value['user_job']}</span>
            <span class="gallery-device">Signature · {value['signature']}</span>
          </a>
          <a class="gallery-permalink" href="#case-{value['id']}">Link to this case <span aria-hidden="true">↗</span></a>
        </article>''')
        entries.append({"@type": "ListItem", "position": item["number"],
                        "name": item["title"],
                        "url": f"https://ai-iconflow.com/gallery/#case-{item['id']}"})
    template = (ROOT / "scripts/templates/gallery.html").read_text(encoding="utf-8")
    return template.replace("<!-- gallery:cards -->", "\n".join(cards)).replace(
        '"itemListElement": []', '"itemListElement": ' + json.dumps(entries, ensure_ascii=False)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    document = render()
    if args.verify_only:
        if PAGE.read_text(encoding="utf-8") != document:
            raise SystemExit("Gallery page is stale; run scripts/build_gallery_page.py")
        print("Gallery page is current: 100 static cases")
    else:
        PAGE.write_text(document, encoding="utf-8", newline="\n")
        print("Rendered 100 static gallery cases")


if __name__ == "__main__":
    main()
