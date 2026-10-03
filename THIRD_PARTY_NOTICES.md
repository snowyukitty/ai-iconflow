# Third-party software and asset provenance

IconFlow does not vendor third-party fonts, icon sets, or stock graphics in
this repository, and vendors exactly one piece of third-party source code,
listed below. The SVG masters, presets, diagrams, and raster
proof assets currently tracked here were authored for IconFlow or generated
from those repository sources. SVG marketing diagrams name system font stacks
but do not bundle font files.

[`docs/STYLE_CATALOG.md`](docs/STYLE_CATALOG.md) records public systems studied
for abstract small-size and workflow principles. It imports none of their code
or artwork and does not turn those research sources into dependencies.

## Vendored: three.js (website only)

The [Icon Forge](https://ai-iconflow.com/forge/) page draws its 3D workbench
with [three.js](https://threejs.org/) r169, copied from the npm package
`three@0.169.0` into `website/forge/vendor/three-0.169.0/` because the site's
Content-Security-Policy allows only same-origin scripts. It is MIT-licensed;
the license text ships beside the code in that directory.

- `three.module.min.js` is byte-identical to the package's
  `build/three.module.min.js`; `tests/test_website.py` pins its SHA-256.
- `OrbitControls.js` is the package's `examples/jsm/controls/OrbitControls.js`
  with one change: its bare `'three'` import points at the vendored module,
  because an import map would need an inline script. A header comment in the
  file says so.

It is not part of the Python package and is not installed by `pip`.

## Installed dependencies

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

This inventory supplements IconFlow's Apache-2.0 project license; it does not
replace the license and notices that accompany separately installed
dependencies or the Chromium runtime. IconFlow's name and logo are also
subject to [`TRADEMARKS.md`](TRADEMARKS.md).
