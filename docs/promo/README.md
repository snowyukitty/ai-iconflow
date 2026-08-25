<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Promotional film handoff

These files are machine-readable production designs for Snowy HyperFrames, not
rendered videos and not a vendored HyperFrames project.

- `storyboard-60.json` is the full evidence-led film.
- `storyboard-30.json` keeps the source-bound receipt gate.
- `storyboard-15.json` is a reach cut built around the real stale-receipt
  refusal.

Each file follows the shared HyperFrames storyboard schema: one timing truth,
no more than three information blocks per slide, the real block vocabulary,
slide-specific media targets, and the four supported motion names. The extra
`production` and `mediaBindings` fields are allowed handoff data. Every binding
records the exact IconFlow source and SHA-256 that a production project must
copy into its own `assets/images/` directory.

The hash contract is cross-platform by design: JSON, Python, and SVG inputs use
UTF-8 with LF-normalized line endings (`utf8-lf`); binary media use exact raw
bytes (`raw-bytes`). A Git checkout changing CRLF/LF therefore cannot make an
unchanged source look stale.

To produce a film, create a private project with `hf new`, copy one storyboard
to `data/storyboard.json`, copy and verify its media bindings, then follow
[`PROMO_VIDEO.md`](../PROMO_VIDEO.md). The handoff files remain `draft`. A
private 15-second production instance has reached `ready-to-preview` with clean
automated checks, but `render` remains blocked until its real human preview
passes.
