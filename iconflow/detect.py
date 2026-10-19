# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Detect which icon targets a consuming project needs, from its own files.

``iconflow init`` used to default to ``web`` whatever the project was, so a
Tauri app with a tray and an Android build started with the wrong contract and
found out at ship time. Detection reads only well-known project files in the
directory (never the network, never anything outside it) and explains each
target it proposes, so the person or agent running ``init`` can correct it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .build import normalize_targets


@dataclass(frozen=True)
class Detected:
    target: str
    reason: str


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _dependencies(package: dict) -> set[str]:
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        section = package.get(key)
        if isinstance(section, dict):
            names.update(section)
    return names


def _text(path: Path, limit: int = 1_000_000) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _ios_evidence(root: Path, package: dict) -> str | None:
    """Why the project builds for iOS, or None (0.10, C-F20).

    Only a project that targets iOS counts: an Xcode project whose build
    settings name the iPhone SDK, the iOS scaffold Capacitor, Flutter or
    Tauri generate, or an Expo config with an ``ios`` section. A macOS-only
    Xcode project does not, and neither does an ``AppIcon.appiconset`` on its
    own (IconFlow writes one).
    """
    for project in [*root.glob("*.xcodeproj"), *root.glob("ios/*.xcodeproj")][:20]:
        if "SDKROOT = iphoneos" in _text(project / "project.pbxproj"):
            return f"{project.relative_to(root).as_posix()} builds for iphoneos"
    if (root / "ios" / "App" / "App.xcodeproj").is_dir():
        return "ios/App/App.xcodeproj exists (Capacitor iOS)"
    if (root / "pubspec.yaml").is_file() and (root / "ios" / "Runner.xcodeproj").is_dir():
        return "ios/Runner.xcodeproj exists (Flutter iOS)"
    if (root / "src-tauri" / "gen" / "apple").is_dir():
        return "src-tauri/gen/apple exists (Tauri mobile)"
    expo = _read_json(root / "app.json").get("expo")
    if isinstance(expo, dict):
        platforms = expo.get("platforms")
        # An explicit platform list decides; without one, an ios section does (R12).
        if isinstance(platforms, list):
            if "ios" in platforms:
                return "app.json lists ios among Expo's platforms"
        elif isinstance(expo.get("ios"), dict):
            return "app.json configures Expo for iOS"
    return None


WEB_FRAMEWORKS = (
    "vite", "next", "astro", "nuxt", "@sveltejs/kit", "svelte", "react", "vue",
    "@angular/core", "solid-js", "gatsby", "@remix-run/react", "eleventy", "@11ty/eleventy",
)
PWA_PACKAGES = ("vite-plugin-pwa", "next-pwa", "@vite-pwa/sveltekit", "workbox-webpack-plugin")


def detect_targets(root: str | Path = ".") -> list[Detected]:
    """Targets the project at ``root`` appears to need, with the evidence for each."""
    root = Path(root)
    found: dict[str, str] = {}

    def add(target: str, reason: str) -> None:
        found.setdefault(target, reason)

    package = _read_json(root / "package.json")
    dependencies = _dependencies(package)

    tauri_conf = next(
        (path for path in (root / "src-tauri" / "tauri.conf.json",
                           root / "src-tauri" / "tauri.conf.json5",
                           root / "src-tauri" / "Tauri.toml") if path.is_file()),
        None,
    )
    if tauri_conf is not None:
        add("tauri", f"{tauri_conf.relative_to(root).as_posix()} exists")
        conf_text = _text(tauri_conf)
        cargo_text = _text(root / "src-tauri" / "Cargo.toml")
        if "trayIcon" in conf_text or "tray-icon" in cargo_text:
            add("tray", "the Tauri config or Cargo.toml enables a tray icon")
        if (root / "src-tauri" / "gen" / "android").is_dir():
            add("android", "src-tauri/gen/android exists (Tauri mobile)")
    if "electron" in dependencies or "electron-builder" in dependencies:
        add("electron", "package.json depends on electron")
        sources = " ".join(
            _text(path, 200_000)
            for pattern in ("main.*", "src/main*", "electron/*")
            for path in list(root.glob(pattern))[:20] if path.is_file()
        )
        if "new Tray(" in sources or "Tray(" in sources:
            add("tray", "the Electron main process creates a Tray")
    if (root / "android" / "app" / "build.gradle").is_file() or (
        root / "android" / "app" / "build.gradle.kts"
    ).is_file():
        add("android", "android/app/build.gradle exists")
    if any((root / name).is_file() for name in (
        "capacitor.config.json", "capacitor.config.ts", "capacitor.config.js",
    )):
        add("android", "a Capacitor config exists")
    if (root / "app" / "src" / "main" / "AndroidManifest.xml").is_file():
        add("android", "app/src/main/AndroidManifest.xml exists")
    ios_reason = _ios_evidence(root, package)
    if ios_reason:
        add("ios", ios_reason)

    web_reason = None
    framework = next((name for name in WEB_FRAMEWORKS if name in dependencies), None)
    if framework and "electron" not in found and "tauri" not in found:
        web_reason = f"package.json depends on {framework}"
    for candidate in ("index.html", "public/index.html", "website/index.html", "site/index.html"):
        if (root / candidate).is_file():
            web_reason = web_reason or f"{candidate} exists"
    if web_reason:
        add("web", web_reason)
    manifests = [
        path for pattern in ("*.webmanifest", "public/*.webmanifest", "public/manifest.json",
                             "static/manifest.json", "website/*.webmanifest")
        for path in root.glob(pattern)
    ]
    pwa_package = next((name for name in PWA_PACKAGES if name in dependencies), None)
    if manifests or pwa_package:
        add("pwa", f"{manifests[0].relative_to(root).as_posix()} exists" if manifests
            else f"package.json depends on {pwa_package}")
    ordered = normalize_targets(list(found)) if found else []
    return [Detected(target, found[target]) for target in ordered]
