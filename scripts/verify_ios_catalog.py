# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Compile IconFlow's iOS app icon sets with Xcode and check what Xcode made.

macOS only (it runs Apple's ``actool`` and ``assetutil``); CI runs it on
``macos-latest``. For each ``AppIcon.appiconset`` given, the set is compiled
into an ``Assets.car`` the way Xcode builds an app, and every rendition is
checked against the appearance its ``Contents.json`` entry declares:

* light: no appearance, opaque;
* dark: ``UIAppearanceDark``, not opaque (iOS draws its ground through it);
* tinted: ``ISAppearanceTintable``, grayscale, opaque.

``actool`` itself accepts a light icon with alpha and an RGB "tinted" image
without a word (probed on Xcode 26.6), so this checks what the compiler
*recorded*, not merely that it ran.

Usage::

    python scripts/verify_ios_catalog.py OUT/ios/AppIcon.appiconset [...]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECT = {
    "light": {"Appearance": None, "Opaque": True},
    "dark": {"Appearance": "UIAppearanceDark", "Opaque": False},
    "tinted": {"Appearance": "ISAppearanceTintable", "Opaque": True, "Encoding": "Gray"},
}
IDIOMS = ("phone", "pad")


def appearance_of(entry: dict) -> str:
    values = [a.get("value") for a in entry.get("appearances", [])
              if a.get("appearance") == "luminosity"]
    return values[0] if values else "light"


def verify(catalog: Path) -> list[str]:
    problems: list[str] = []
    contents = json.loads((catalog / "Contents.json").read_text(encoding="utf-8"))
    declared = {entry["filename"]: appearance_of(entry) for entry in contents["images"]}
    with tempfile.TemporaryDirectory() as work:
        assets = Path(work) / "Assets.xcassets"
        assets.mkdir()
        (assets / "Contents.json").write_text(
            json.dumps({"info": {"author": "xcode", "version": 1}}), encoding="utf-8")
        shutil.copytree(catalog, assets / "AppIcon.appiconset")
        out = Path(work) / "out"
        out.mkdir()
        compiled = subprocess.run(
            ["xcrun", "actool", str(assets), "--compile", str(out), "--platform", "iphoneos",
             "--minimum-deployment-target", "18.0", "--target-device", "iphone",
             "--target-device", "ipad", "--app-icon", "AppIcon",
             "--output-partial-info-plist", str(out / "partial.plist"),
             "--output-format", "human-readable-text", "--warnings", "--errors", "--notices"],
            capture_output=True, text=True)
        log = compiled.stdout + compiled.stderr
        if compiled.returncode != 0 or ": error:" in log or ": warning:" in log:
            return [f"actool did not compile cleanly:\n{log}"]
        info = subprocess.run(["xcrun", "assetutil", "--info", str(out / "Assets.car")],
                              capture_output=True, text=True, check=True)
        renditions = [r for r in json.loads(info.stdout)[1:]
                      if r.get("AssetType") == "Icon Image" and r.get("Name") == "AppIcon"]
    for filename, appearance in declared.items():
        for idiom in IDIOMS:
            found = [r for r in renditions
                     if r.get("RenditionName") == filename and r.get("Idiom") == idiom]
            if len(found) != 1:
                problems.append(f"{filename} ({idiom}): {len(found)} renditions, expected 1")
                continue
            for key, value in EXPECT[appearance].items():
                if found[0].get(key) != value:
                    problems.append(f"{filename} ({idiom}): {key} is {found[0].get(key)!r}, "
                                    f"expected {value!r} for the {appearance} appearance")
    if len(renditions) != len(declared) * len(IDIOMS):
        problems.append(f"{len(renditions)} icon renditions for {len(declared)} declared "
                        "appearance(s)")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    failed = False
    for name in argv:
        catalog = Path(name)
        problems = verify(catalog)
        appearances = sorted({appearance_of(e) for e in json.loads(
            (catalog / "Contents.json").read_text(encoding="utf-8"))["images"]})
        if problems:
            failed = True
            print(f"FAIL {catalog}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"OK   {catalog}: Xcode compiled {', '.join(appearances)} as declared")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
