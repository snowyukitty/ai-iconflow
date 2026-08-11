# Third-party software and asset provenance

IconFlow does not vendor third-party source code, fonts, icon sets, or stock
graphics in this repository. The SVG masters, presets, diagrams, and raster
proof assets currently tracked here were authored for IconFlow or generated
from those repository sources. SVG marketing diagrams name system font stacks
but do not bundle font files.

Runtime dependencies are installed separately by `pip` and retain their own
licenses and notices:

| Dependency | Purpose | License |
|---|---|---|
| [Playwright for Python](https://github.com/microsoft/playwright-python) | Isolated Chromium rendering | Apache-2.0 |
| [Pillow](https://python-pillow.org/) | Pixel inspection and image/container assembly | MIT-CMU |
| [Tomli](https://pypi.org/project/tomli/) | TOML parser on Python 3.10 only | MIT |

The optional development dependency [build](https://pypi.org/project/build/)
is MIT-licensed. Playwright downloads a separate Chromium runtime during
`iconflow setup`; IconFlow does not redistribute that runtime. Review the
licenses shipped with the downloaded browser and each installed wheel when
redistributing an environment rather than this source package alone.

This inventory is a provenance aid, not a substitute for IconFlow's own
project license. No project license has been selected yet.
