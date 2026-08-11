# Launch readiness

Status date: 2026-08-12. This file records evidence and remaining owner gates;
it is not a claim that a release has been published.

## Current readiness

- [x] Source, wheel resources, console entry point, and clean wheel installation tested.
- [x] Windows, Linux, and macOS CI spans the supported Python 3.10–3.14 range.
- [x] Chromium rendering and network/animation security boundaries have integration tests.
- [x] SVG/XML size, structure, DTD/entity, output-link, and review-contract boundaries have regression tests.
- [x] Wheel and sdist contents have a fail-closed verification script.
- [x] A non-publishing release-candidate workflow builds checksums and proves wheel reproducibility.
- [x] README provides a source-only installation path and a checked-in reviewed-family proof.
- [x] Fourteen packaged technique families have one metadata source, clean `check`
  results, native 16px visual proof, tray guidance, and clean-room provenance.
- [x] Security, provenance, changelog, contribution, issue, pull-request, and release guidance exists.
- [x] Owner selected Apache-2.0; the checkout includes license, notice, package metadata, and trademark policy.
- [ ] Owner enables GitHub private vulnerability reporting.
- [ ] Owner approves and applies repository metadata and social preview.
- [ ] Owner approves a tag, GitHub Release, and PyPI publication.

This checkout is licensed under Apache-2.0. The public GitHub repository will
not display that license until these local commits are pushed; its
[Releases page](https://github.com/snowyukitty/ai-iconflow/releases) remains
empty. The [official PyPI JSON endpoint](https://pypi.org/pypi/ai-iconflow/json)
for `ai-iconflow` returned HTTP 404 on 2026-08-11, so the README intentionally
documents source installation only. Name availability is not guaranteed until
PyPI accepts a first publication.

## License and trademark decision

The dependency and asset audit found no vendored third-party code, font, icon
set, or stock image. Runtime dependencies are separately installed under
Apache-2.0 (Playwright), MIT-CMU (Pillow), and MIT (Tomli); no upstream `NOTICE`
file was found in the Playwright Python repository. Their licenses do not force
IconFlow to choose the same project license, but anyone redistributing those
dependencies must preserve their applicable notices.

The owner selected **Apache-2.0** for its permissive copyright terms and explicit
patent grant and termination provisions. `pyproject.toml` uses the PEP 639 SPDX
expression and includes `LICENSE`, `NOTICE`, `TRADEMARKS.md`, and this dependency
notice in both release formats.

Apache-2.0 licenses repository copyright and applicable contributor patents; it
does not transfer copyright ownership or grant rights to brand another product
as IconFlow. [`TRADEMARKS.md`](../TRADEMARKS.md) permits truthful references,
compatibility descriptions, and clear provenance while reserving the IconFlow
name, logo, and official-release identity against confusing use.

## Proposed GitHub metadata

- Description: `Design, review, and ship platform-ready favicon, PWA, desktop, and tray icon families from one semantic SVG.`
- Topics: `app-icon`, `cli`, `design-system`, `developer-tools`, `electron`,
  `favicon`, `favicon-generator`, `icon-design`, `playwright`, `pwa`, `python`,
  `svg`, `tauri`, `tray-icon`
- Homepage: `https://github.com/snowyukitty/ai-iconflow#readme`
- Documentation: `https://github.com/snowyukitty/ai-iconflow/tree/main/docs`
- Social preview: `docs/assets/social-preview.png` (1280×640, 47 KB; matches
  [GitHub's recommended dimensions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview))

These are proposals only. Applying them changes GitHub repository settings and
requires owner approval.

## Market position and discoverability

The nearest tools solve adjacent jobs:

- [RealFaviconGenerator](https://realfavicongenerator.net/developers/favicon-generation)
  generates web favicon packages and exposes an API.
- [Tauri's icon command](https://v2.tauri.app/develop/icons/) converts a source
  image into Tauri platform assets.
- [electron-builder](https://www.electron.build/docs/features/icons-and-images/)
  consumes platform icon files and can derive formats for application packaging.
- [PWA Asset Generator](https://github.com/elegantapp/pwa-asset-generator)
  generates PWA icons and splash assets from a source image.

Those are useful conversion/package tools. IconFlow best serves an agent,
designer, or small product team that also needs to decide whether the source is
specific, readable at 16px, correct after target transforms, and approved by a
receipt that becomes stale when reviewed inputs change. That workflow—not a
claim of universally better conversion—is the defensible differentiator.

Natural search language to use in docs and launch copy:

- `app icon workflow`, `favicon generator from SVG`, `Tauri icon generator`;
- `Electron icon generator`, `PWA maskable icon`, `tray icon template`;
- `review icons at 16px`, `SVG to ICO ICNS`, `cross-platform app icons`.

Evidence-led launch messages:

1. `Fourteen execution languages, one semantic SVG, and native 16px proof before you choose a direction.`
2. `See the same icon in adaptive crops, Electron corners, and menu-bar templates before you ship it.`
3. `IconFlow starts with the product job and competing silhouettes, then builds 23 favicon, PWA, desktop, and tray assets locally.`

## Known limits to keep visible

- Playwright Chromium is a one-time network download and materially larger than
  the Python package.
- Reproducibility is scoped to a fixed IconFlow/Chromium/Pillow toolchain.
- Tauri output is desktop-only; mobile app-icon sets are not generated.
- The SVG renderer is isolated, but IconFlow is not a sanitizer for serving
  arbitrary original SVG files to web users.
- Source archive members are content-repeatable locally, but the current sdist
  archive is not byte-identical because generated timestamps vary.

A separate `SUPPORT.md` and code of conduct are intentionally deferred. Before
the first release, usage support can stay in the bug/proposal issue forms; add
broader community governance documents when contribution volume demonstrates a
real need rather than creating promises the maintainer cannot yet support.

## Recommended launch sequence

1. Review and push the Apache-2.0 license, notice, trademark policy, and package metadata.
2. Enable private vulnerability reporting and run CI on the final release commit.
3. Apply the proposed description, topics, homepage, and reviewed social preview.
4. Manually run the release-candidate workflow; verify checksums and clean-wheel behavior.
5. Tag `v0.4.0`, create the GitHub Release, and publish the exact candidate through PyPI Trusted Publishing only after explicit approval.
6. Run the documented PyPI clean-install smoke test, then share the visual proof and reproducible commands.

The smallest remaining owner action is to review these local commits and decide
when to push them. Publishing and repository-setting changes still require
separate explicit approval.
