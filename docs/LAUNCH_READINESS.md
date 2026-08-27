<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Launch readiness

> **Current state lives in [`STATE.md`](STATE.md), which is generated.** This
> file is the *record* — how the launch was reached, and the reasoning behind
> the decisions that shaped it. It deliberately no longer restates anything a
> probe can check.

## Why this file was rewritten

Until 2026-08-25 this was a live status board: hand-ticked boxes describing the
repository, the package index and the site as they stood on the day someone
last looked. By that morning it said, in its own words, that the `iconflow`
name "returns 404, so both are still free" — three days after `0.5.0` was
published from this repository. In an adjacent bullet it announced the
repository was public and then quoted `gh repo view` reporting it `PRIVATE`.
It listed twelve topics when there were twenty, and a homepage as "not set"
when it had been set for days.

Nobody lied. A person ticked a box, the world moved, and the box stayed ticked.

That is precisely the failure `iconflow ship` exists to prevent: an approval
that outlived the thing it approved. The tool refuses to build against a review
receipt whose source hash no longer matches, and it was doing so while its own
launch document told visitors something false about where the package lived.

The fix is structural, not vigilance. `scripts/state.py` asks the world —
GitHub, PyPI, the deployed site, the generators — and writes
[`STATE.md`](STATE.md). A probe that cannot run reports UNKNOWN, never PASS.
`tests/test_state.py` fails if this file starts restating live state again.

## How the launch was reached

A dated record, not a status board. Every line below is history: it was true
when it happened and stays true, because it describes an event rather than a
condition.

| When | What |
|---|---|
| 2026-06-23 | Development began in a private repository. |
| 2026-08-13 | Dependency and asset audit: no vendored third-party code, font, icon set, or stock image. |
| 2026-08-14 | A fresh wheel installed outside the source tree passed `doctor` and the source-bound 23-file brand ship. |
| 2026-08-21 | Three-tier license split landed — `LICENSES.md`, per-directory `LICENSE` files, SPDX headers, a substantive `NOTICE`, `iconflow license`, `tests/test_licensing.py`. |
| 2026-08-21 | Agent Contract v1: `--json` envelopes, 0/1/2 exit codes, `iconflow demo`, the PR proof action, and a contributor lane. |
| 2026-08-21 | Homepage rebuilt on the Living Archive with the Remix Lab, native-size hero scrubber, and methodology page, after a three-model UI/UX audit (Codex, Grok, Gemini via ATD). |
| 2026-08-21 | Responsive sign-off for `/getting-started/` — Playwright at 1440/768/360, no horizontal overflow, no console errors. |
| 2026-08-22 | Trusted Publishing proven end to end on TestPyPI (run `32516576257`). `0.5.0` installed from TestPyPI into a clean venv and answered *IconFlow is ready*. |
| 2026-08-22 | Distribution renamed `ai-iconflow` → `iconflow` before any upload — 123 references across 36 files, done while a rename was still possible. |
| 2026-08-22 | Repository made public; private vulnerability reporting enabled; community health reached GitHub's 100%. |
| 2026-08-22 | `v0.5.0` tagged, released, and published to PyPI with signed attestations. The name became the project's at that upload and not before. |
| 2026-08-24 | `/reference/icon-sizes/` generated from `iconflow/build.py`; structured data, `robots.txt` terms, and the README animation landed. |
| 2026-08-25 | Self-audit (`scripts/state.py`) and a Python-floor lint gate added, after a 3.12-only f-string reached `main` and only the Windows 3.10 matrix leg caught it. |
| 2026-08-26 | Five source-bound campaign stills, route-specific social cards, and schema-compatible 60/30/15-second HyperFrames handoffs landed with local visual, i18n, manifest, and test gates. No video render or site deployment was part of that checkpoint. |
| 2026-08-26 | A private 15-second HyperFrames production instance reached `ready-to-preview`: 0 audit warnings, 0 strict browser findings, 21/21 WCAG AA text checks, and a self-contained human-review artifact. Its first abstract opening was later superseded by the clearer 2026-08-27 cut. |
| 2026-08-27 | Replaced the unclear Coral Gate artwork with a literal one-source inspection story. One accepted Flow Quality plate now carries only physical atmosphere; exact IconFlow pixels and claims remain deterministic. The revised 15-second HyperFrames cut passes audit and strict browser QA; human preview and render remain pending. |

### What the sequence taught

**Publishing to PyPI *is* the public disclosure.** PyPI has no name
reservation: a pending publisher explicitly does not hold a name until an
upload uses it, and because the sdist and wheel both carry the full source,
that first upload discloses everything. There is no ordering that claims a name
while keeping the code private. Doing PyPI first still mattered, for the
narrower reason that it closed the window in which someone who noticed the
public repository could take the name.

**A version number is spent once.** A PyPI version can never be re-uploaded,
which is why the TestPyPI rehearsal was not optional.

**Licensing is decided at the moment of publication.** Once a repository is
cloneable, every file is distributed under whatever license it carried then,
and that grant cannot be withdrawn for copies already taken.

## License and trademark decision

Runtime dependencies are separately installed under Apache-2.0 (Playwright),
MIT-CMU (Pillow), and MIT (Tomli); no upstream `NOTICE` file exists in the
Playwright Python repository. Their licenses do not force IconFlow to choose
the same project license, but anyone redistributing those dependencies must
preserve their applicable notices.

The owner selected **Apache-2.0** for the engine, for its permissive copyright
terms and its explicit patent grant and termination provisions. On 2026-08-21
that was extended into the four-tier split in [`LICENSES.md`](../LICENSES.md):
`Apache-2.0` for the tool, `CC0-1.0` for the technique scaffolds,
`CC-BY-SA-4.0` for the methodology, and `CC-BY-NC-ND-4.0` for IconFlow's own
finished artwork — so the methodology and the artwork are protected without
putting any condition on the icons users build. GitHub's sidebar reports only
the root `LICENSE`.

Apache-2.0 licenses repository copyright and applicable contributor patents. It
does not transfer copyright ownership or grant rights to brand another product
as IconFlow. [`TRADEMARKS.md`](../TRADEMARKS.md) permits truthful references,
compatibility descriptions, and clear provenance while reserving the IconFlow
name, logo, and official-release identity against confusing use.

## Market position

The nearest tools solve adjacent jobs:

- [RealFaviconGenerator](https://realfavicongenerator.net/developers/favicon-generation)
  generates web favicon packages and exposes an API.
- [Tauri's icon command](https://v2.tauri.app/develop/icons/) converts a source
  image into Tauri platform assets.
- [electron-builder](https://www.electron.build/docs/features/icons-and-images/)
  consumes platform icon files and derives formats for packaging.
- [PWA Asset Generator](https://github.com/elegantapp/pwa-asset-generator)
  generates PWA icons and splash assets from a source image.

Those are useful conversion tools. IconFlow serves an agent, designer, or small
product team that also needs to decide whether the source is specific, readable
at 16px, correct after target transforms, and approved by a receipt that goes
stale when the reviewed inputs change. That workflow — not a claim of
universally better conversion — is the defensible differentiator.

Search language and launch messaging moved to [`SEO.md`](SEO.md), which keeps
the keyword map beside the pages that answer it rather than in a checklist.

## Known limits to keep visible

- Playwright Chromium is a one-time network download, and materially larger
  than the Python package.
- Reproducibility is scoped to a fixed IconFlow/Chromium/Pillow toolchain.
- Tauri output is desktop-only; mobile app-icon sets are not generated.
- The SVG renderer is isolated, but IconFlow is not a sanitizer for serving
  arbitrary original SVG files to web users.
- Source archive members are content-repeatable locally, but the sdist archive
  is not byte-identical, because generated timestamps vary.

## What is still open

Deliberately not listed here. Run:

```bash
python scripts/state.py
```

It reports the open gates it can observe, and names the decisions no probe can
settle — the ones genuinely waiting on a person. Anything written here instead
would be correct on the day it was typed and misleading a week later, which is
the whole reason this file was rewritten.
