<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Launch readiness

Status date: 2026-08-21. This file records evidence and remaining owner gates;
it is not a claim that a release has been published.

## Current readiness

- [x] Source, wheel resources, console entry point, and clean wheel installation tested.
- [x] Windows, Linux, and macOS CI spans the supported Python 3.10–3.14 range.
- [x] Chromium rendering and network/animation security boundaries have integration tests.
- [x] SVG/XML size, structure, DTD/entity, output-link, and review-contract boundaries have regression tests.
- [x] Wheel and sdist contents have a fail-closed verification script.
- [x] A non-publishing release-candidate workflow builds checksums and proves wheel reproducibility.
- [x] README provides a source-only installation path and a checked-in reviewed-family proof.
- [x] The agent-first Getting Started route, Windows/POSIX setup scripts, and
  open Agent Skill metadata have website and distribution contract tests.
- [x] A fresh wheel installed outside the source tree passed `doctor` and the
  source-bound 23-file brand ship on 2026-08-14.
- [x] Twenty packaged technique families have one metadata source, clean `check`
  results, native 16px visual proof, tray guidance, and clean-room provenance.
- [x] Security, provenance, changelog, contribution, issue, pull-request, and release guidance exists.
- [x] Owner selected Apache-2.0; the checkout includes license, notice, package metadata, and trademark policy.
- [x] Launch commits are on the public `main` branch, GitHub recognizes the
  Apache-2.0 license, and the cross-platform CI matrix is green.
- [x] Owner applied a public repository description and topic baseline.
- [x] The homepage opens on the Living Archive (137 directions, 19 passed
  review) with a Remix Lab, a real native-size hero scrubber, and a
  methodology page; a three-model UI/UX audit (Codex, Grok, Gemini via ATD)
  was folded in before publication on 2026-08-21.
- [x] Agent Contract v1 (`docs/AGENT_CONTRACT.md`): `--json` envelopes,
  0/1/2 exit codes, `iconflow demo` from the packaged brand family, the PR
  proof GitHub Action, and a contributor lane (case PR template, community
  fixture, issue seeds) landed on 2026-08-21 and CI is green on every
  platform of the matrix.
### Before the repository goes public (do these in order)

Publishing is one-way: once the repository is cloneable, every file in it is
distributed under whatever license it carried at that moment, and that grant
cannot be withdrawn for the copies already taken. The repository has 0 forks
and 0 stars and has never been meaningfully public, so the licensing structure
is still fully the owner's to choose. That window closes on publication.

- [x] Three-tier license split landed (`LICENSES.md`, per-directory `LICENSE`
  files, SPDX headers, substantive `NOTICE`, `iconflow license`,
  `tests/test_licensing.py`). Verified 2026-08-21.
- [ ] **Claim `ai-iconflow` on PyPI first.** Publishing a public repository
  whose package name is unregistered is the one concrete, immediate theft
  vector: anyone can register the name and ship malware to people following
  this README. Register the name and create the Trusted Publisher *before* the
  repository is visible, even if the first real release comes later.
- [ ] Owner reads `LICENSES.md` end to end and confirms the tier boundaries —
  especially §1, the promise that icons users make with IconFlow are theirs.
- [ ] Owner enables a CLA signature check (the
  [CLA Assistant](https://github.com/cla-assistant/cla-assistant) GitHub App is
  the usual choice). `CLA.md` and the PR-template checkbox are in place, but
  nothing yet *records* assent automatically. Until then, check the signature
  line by hand on every outside PR — a contribution merged without it freezes
  IconFlow's licensing permanently, which is the one thing the CLA exists to
  prevent.
- [ ] Owner decides whether to register the IconFlow word mark. `TRADEMARKS.md`
  asserts common-law rights, which are real but weaker than registration and
  jurisdiction-dependent.
- [ ] **Owner makes the GitHub repository public.** Checked again on
  2026-08-21: `gh repo view snowyukitty/ai-iconflow` reports
  `"visibility": "PRIVATE"` and an unauthenticated request returns 404, so
  the clone URL, the raw docs, `uv tool install git+...`, and the
  `/plugin marketplace add snowyukitty/ai-iconflow` catalog are all
  unreachable from outside this machine. Every adoption path below depends
  on this one. The 2026-08-21 line above stating that launch commits are on
  a public `main` no longer describes the repository's current state.
- [ ] Owner enables GitHub private vulnerability reporting.
- [ ] Owner approves and applies the remaining homepage and social-preview settings
  (`docs/assets/social-preview.png`, 1280×640, Petal Haypile).
- [ ] Owner confirms the `ai-iconflow` name on PyPI and creates a Trusted
  Publisher (`docs/MILESTONE_v0.5.md`, Phase 0).
- [ ] Owner files the eight `docs/ISSUE_SEEDS.md` issues by hand.
- [x] Desktop, tablet, and mobile visual sign-off for `/getting-started/`
  (Playwright at 1440/768/360 on 2026-08-21: no horizontal overflow, no console
  errors); the route is live on the canonical host.
- [ ] After publication: enable Cloudflare AI Crawl Control for
  `ai-iconflow.com` (the dashboard setting is the only measure here with
  teeth; `robots.txt` and `/llms.txt` are notice, honoured voluntarily).
- [ ] After publication: archive the repository in Software Heritage and mint a
  Zenodo DOI on the first GitHub Release. Both create dated third-party
  authorship records, which is what removes an "independent creation" defence
  later (`docs/PROVENANCE.md` §1).
- [ ] Sign release tags, so a release is attributable to the maintainer.
- [ ] Owner approves tag `v0.5.0`, the GitHub Release, and PyPI publication;
  the changelog's *Unreleased* folds into 0.5.0 at that moment.

This checkout is licensed in four tiers ([`LICENSES.md`](../LICENSES.md)):
`Apache-2.0` for the tool, `CC0-1.0` for the technique scaffolds,
`CC-BY-SA-4.0` for the methodology, and `CC-BY-NC-ND-4.0` for IconFlow's own
finished artwork — with icons made *with* the tool belonging outright to the
user who made them. GitHub's sidebar reports only the root `LICENSE`.
The [Releases page](https://github.com/snowyukitty/ai-iconflow/releases) remains
empty and no `v*` tag exists. The
[official PyPI JSON endpoint](https://pypi.org/pypi/ai-iconflow/json) for
`ai-iconflow` returned HTTP 404 again on 2026-08-14; GitHub still reported zero
releases and zero tags, so the README intentionally
documents source installation only. Name availability is not guaranteed until
PyPI accepts a first publication.

## License and trademark decision

The dependency and asset audit found no vendored third-party code, font, icon
set, or stock image. Runtime dependencies are separately installed under
Apache-2.0 (Playwright), MIT-CMU (Pillow), and MIT (Tomli); no upstream `NOTICE`
file was found in the Playwright Python repository. Their licenses do not force
IconFlow to choose the same project license, but anyone redistributing those
dependencies must preserve their applicable notices.

The owner selected **Apache-2.0** for the engine, for its permissive copyright
terms and explicit patent grant and termination provisions. On 2026-08-21 that
was extended into the three-tier split in [`LICENSES.md`](../LICENSES.md), so
the methodology and the finished artwork are protected without putting any
condition on the icons users build. `pyproject.toml` uses the PEP 639 SPDX
expression — now the compound
`Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND CC-BY-NC-ND-4.0` — and includes
`LICENSE`, `NOTICE`, `TRADEMARKS.md`, `LICENSES.md`, the vendored CC texts, and
this dependency notice in both release formats.

Apache-2.0 licenses repository copyright and applicable contributor patents; it
does not transfer copyright ownership or grant rights to brand another product
as IconFlow. [`TRADEMARKS.md`](../TRADEMARKS.md) permits truthful references,
compatibility descriptions, and clear provenance while reserving the IconFlow
name, logo, and official-release identity against confusing use.

## Current and proposed GitHub metadata

Verified on 2026-08-13, the public repository currently has:

- Description: `Reviewed, platform-ready icon families from one semantic SVG master — favicon, PWA, Tauri, Electron, tray. Distinctiveness = specificity, proven at 16px.`
- Topics: `app-icon`, `cli`, `design-system`, `electron`, `favicon`,
  `favicon-generator`, `icon`, `pwa`, `python`, `svg`, `tauri`, `tray-icon`
- Homepage: not set

The remaining owner-controlled proposals are:

- Homepage: `https://github.com/snowyukitty/ai-iconflow#readme`
- Documentation: `https://github.com/snowyukitty/ai-iconflow/tree/main/docs`
- Social preview: `docs/assets/social-preview.png` (1280×640, Petal Haypile; matches
  [GitHub's recommended dimensions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview))

Applying them changes GitHub repository settings and requires owner approval.

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

1. `Twenty execution languages, one semantic SVG, and native 16px proof before you choose a direction.`
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

1. Keep the reviewed Apache-2.0, notice, trademark, and package metadata on `main`.
2. Enable private vulnerability reporting and keep CI green on the release commit.
3. Apply the remaining homepage and reviewed social preview.
4. Manually run the non-publishing release-candidate workflow; verify checksums and clean-wheel behavior.
5. Tag `v0.5.0`, create the GitHub Release, and publish the exact candidate through PyPI Trusted Publishing only after explicit approval.
6. Run the documented PyPI clean-install smoke test, then share the visual proof and reproducible commands.

The smallest remaining owner action is to enable private vulnerability
reporting, then decide whether to apply the homepage/social preview and approve
the `v0.5.0` publication sequence. Publishing and repository-setting changes
still require separate explicit approval.
