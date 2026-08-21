# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""IconFlow — turn one semantic SVG master into a reviewed icon family.

The design step follows docs/DESIGN_PLAYBOOK.md. This package is the
deterministic build engine: it rasterizes SVG with network-isolated headless
Chromium and assembles crisp, per-size .ico / .icns / .png sets for web, PWA,
Tauri desktop, Electron, and tray use.
"""

__version__ = "0.5.0"

from .rasterize import Rasterizer, load_svg
from .build import build, RenderCache

__all__ = ["Rasterizer", "load_svg", "build", "RenderCache", "__version__"]
