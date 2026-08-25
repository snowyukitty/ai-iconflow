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
- `storyboard-15.json` is a reach cut and intentionally makes no receipt claim.

Each file follows the shared HyperFrames storyboard schema: one timing truth,
no more than three information blocks per slide, the real block vocabulary,
slide-specific media targets, and the four supported motion names. The extra
`production` and `mediaBindings` fields are allowed handoff data. Every binding
records the exact IconFlow source and SHA-256 that a production project must
copy into its own `assets/images/` directory.

To produce a film, create a private project with `hf new`, copy one storyboard
to `data/storyboard.json`, copy and verify its media bindings, then follow
[`PROMO_VIDEO.md`](../PROMO_VIDEO.md). The handoff is still `draft`: do not run
`render` until `npm run check`, `npm run review`, and a real human preview all
pass.
