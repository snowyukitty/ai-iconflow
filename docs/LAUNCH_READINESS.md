<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Launch readiness

Status date: 2026-08-26.

IconFlow launched on 2026-08-22. This file is a current-state checkpoint, not a
pre-launch plan and not an authority to publish anything. External state must
be re-observed with the commands below before an agent reports it.

## Verified public state

- GitHub repository: `snowyukitty/ai-iconflow`, public, default branch `main`.
- Canonical site: <https://ai-iconflow.com> (HTTP 200 through Cloudflare).
- Repository homepage: <https://ai-iconflow.com>.
- GitHub Release: `v0.5.0`, **IconFlow 0.5.0 — first public release**,
  published 2026-08-22.
- PyPI: [`iconflow 0.5.0`](https://pypi.org/project/iconflow/).
- Latest observed pushed `main` CI was green on 2026-08-25. A new checkpoint
  must rely on its own local checks and resulting GitHub run.
- GitHub recognizes the repository as Apache-2.0 at the root. The complete
  four-tier map remains [`LICENSES.md`](../LICENSES.md): Apache-2.0 engine,
  CC0-1.0 scaffolds, CC-BY-SA-4.0 methodology, and CC-BY-NC-ND-4.0 showcase
  artwork. Icons made with IconFlow belong to their makers.

Observed repository description:

> Reviewed, platform-ready icon families from one semantic SVG master —
> favicon, PWA, Tauri, Electron, tray. Distinctiveness = specificity, proven
> at 16px.

Observed topics include `app-icon`, `favicon-generator`, `icon-generator`,
`pwa`, `python`, `svg`, `svg-to-png`, `tauri`, `electron`, `tray-icon`,
`maskable-icons`, `claude-code`, and `developer-tools`.

## Product and adoption readiness

- [x] `pip install iconflow` exposes the `iconflow` command.
- [x] The wheel contains the Agent Skill, reference docs, 20 CC0 technique
  scaffolds, and the reviewed demo family.
- [x] Agent Contract v1 provides JSON envelopes, stable gate codes, and 0/1/2
  exit semantics.
- [x] `check`, `review`, and `ship` fail closed on warnings, stale receipts,
  mismatched targets, and scores below 4/5.
- [x] CI covers Windows, Linux, macOS, Python 3.10–3.14, wheel resources, and
  isolated Chromium rendering.
- [x] The public site carries source-linked native-size proof, 100 gallery
  cases, 20 technique scaffolds, 137 archive marks, and an agent-first Getting
  Started route.
- [x] English source pages and Spanish, Japanese, Traditional Chinese, and
  Simplified Chinese localized routes have canonical URLs, `hreflang`, sitemap
  entries, and fail-closed catalog verification.
- [x] Community health files, security policy, private vulnerability reporting,
  contribution guidance, CLA text, issue templates, and PR templates exist.
- [x] Release provenance, SPDX headers, attribution boundaries, and the
  user-output licence guarantee have regression tests.

## 2026-08-26 marketing checkpoint

- [x] Five final campaign stills are rendered from exact repository assets:
  three 1200×630 route cards, one 1080×1080 square, and one 1080×1920 story.
- [x] The renderer blocks network and JavaScript, fixes the viewport,
  device-scale factor, and sRGB profile, validates dimensions, and writes a
  source-bound manifest plus a visual review board.
- [x] Documentation and website copies are byte-identical. Tests bind every
  manifest input and both output trees by SHA-256.
- [x] Getting Started, methodology, Gallery, and Archive use route-specific
  Open Graph/Twitter images with title, description, canonical URL, `og:url`,
  dimensions, and meaningful image alt.
- [x] Marketing image alt is localized in all five site languages; localized
  titles, descriptions, canonical URLs, and `hreflang` already come from the
  existing fail-closed i18n build.
- [x] The 60-, 30-, and 15-second promotional-film handoffs use Snowy
  HyperFrames' real storyboard schema, block vocabulary, density limits,
  motion vocabulary, slide-specific media targets, and SHA-256 asset binds.
- [ ] No promotional video has been rendered. The storyboards remain `draft`,
  `humanPreview` remains `pending`, and each cut still requires a private
  production project, `npm run check`, `npm run review`, and human approval.
- [ ] These new website assets are not claimed as deployed by this checkpoint.
  A Git push runs CI only; site deployment is a separate owner-authorized
  operation.

The canonical film contract is [`PROMO_VIDEO.md`](PROMO_VIDEO.md); the
machine-readable cuts live in [`promo/`](promo/). The canonical still-image
contract is [`LAUNCH_SITE.md`](LAUNCH_SITE.md); generation and review are
documented in [`website/README.md`](../website/README.md).

## Owner-only follow-ups

These are not launch blockers and must not be silently converted into agent
tasks:

- Confirm in GitHub's web UI whether the custom repository social preview was
  uploaded. GitHub exposes no supported repository field for this check; the
  reviewed 1280×640 source remains `docs/assets/social-preview.png`.
- Decide whether to install a CLA signature app. Until then, verify the signed
  CLA statement manually before merging any outside contribution.
- Decide whether and where to register the IconFlow word mark.
- Decide whether to enable Cloudflare AI Crawl Control.
- Decide whether to archive the release with Software Heritage or Zenodo and
  whether future release tags should be signed.
- File any selected drafts from `docs/ISSUE_SEEDS.md`; creating public issues is
  a separate representational action.

## Known limits that stay visible

- Playwright Chromium is a one-time download and materially larger than the
  Python package.
- Exact marketing PNG regeneration is scoped to the pinned project browser and
  host font stack. The manifest proves source freshness and output identity; it
  does not claim cross-OS font rasterization is byte-identical.
- Tauri output is desktop-only; mobile app-icon sets and Apple Icon Composer
  files are not generated.
- The SVG renderer is isolated, but IconFlow is not a sanitizer for serving an
  arbitrary original SVG to website visitors.
- Source archives are content-repeatable under a fixed toolchain, but the sdist
  archive is not byte-identical because generated timestamps vary.
- The 15-second film is a reach hook. It does not show or claim the
  source-bound receipt contract carried by the 30- and 60-second cuts.

## Re-observe external state

Run these instead of copying dated sentences from this document:

```powershell
gh repo view snowyukitty/ai-iconflow `
  --json visibility,defaultBranchRef,description,homepageUrl,repositoryTopics
gh release view v0.5.0 --repo snowyukitty/ai-iconflow
(Invoke-RestMethod https://pypi.org/pypi/iconflow/json).info `
  | Select-Object name,version,package_url
Invoke-WebRequest -UseBasicParsing https://ai-iconflow.com/ -Method Head
gh run list --repo snowyukitty/ai-iconflow --branch main --limit 5
```

Before a finished push, run the established local suite and inspect the exact
outward effects. A normal branch or `main` push triggers `.github/workflows/ci.yml`.
The release-candidate workflow runs only on a `v*` tag or manual dispatch, and
the publishing workflow runs only on a published GitHub Release or explicit
manual dispatch. No workflow in this repository deploys the website from a
normal `main` push.
