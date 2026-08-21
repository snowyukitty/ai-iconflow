<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# 100-case Gallery

The public Gallery at `/gallery/` is IconFlow's practical reference library.
It maps two independent coordinates:

- **World / user job** explains what the icon means and why it exists.
- **Technique / grammar** explains how the icon is constructed and reduced.

The collection is not a prompt feed. A case is admitted only when it includes
an editable semantic SVG, clean automated QA, exact native 16px and 128px
renders, a visual silhouette, a current contract-bound receipt with all six
scores at least 4/5, and a reusable casebook record.

## Edition contract

The first 100-case edition combines nine earlier flagship cases with 91 new
cases selected from three independent 34-candidate batches. Eleven weaker,
less legible, or repetitive directions are explicitly rejected. The generated
`gallery/catalog.json` and deployed `website/assets/gallery/catalog.json` must
both report:

- 111 candidates;
- 100 admitted cases;
- 11 rejected candidates;
- 100 unique IDs and source hashes;
- exact 16×16, 128×128, and 256×256 renders for every admitted case.

`scripts/build_gallery.py` is fail-closed: it validates counts, candidate
fields, source IDs, IconFlow checks, current review contracts, render sizes,
public evidence files, and case records before replacing the deploy catalog.
Its `--verify-only` mode performs the same public-evidence checks from a clean
clone without requiring the gitignored candidate-adjudication workspace.

## Rebuild and verify

Verify the tracked edition from any clean clone:

```powershell
.venv\Scripts\python.exe scripts\build_gallery.py --verify-only
.venv\Scripts\python.exe -m unittest tests.test_website -v
```

Maintainers with the gitignored `work/gallery-100/` candidate manifests can run
the command without a mode to rebuild admitted sources and public assets; add
`--reviews` when every full Review Lab sheet must also be regenerated. The
deploy-ready output remains under `website/`; source cases and receipts remain
under `gallery/`.

## Image presentation

Large gallery specimens always use the editable SVG source, so they remain
crisp at any layout size. The native proof is a separate 16×16 PNG displayed
at exactly 16 CSS pixels. A raster proof is never enlarged and presented as
detail; any deliberate nearest-neighbor zoom must be separately labeled.

## Clean-room rule

Original story, anime, character, and game cases must not imitate a named
artist, studio, franchise, living creator, or trademark. Every subject is an
original product brief with its own user job, concrete noun, cliché filter,
four concept lenses, and one structural signature.

## Legacy route

`/imagination/` is retired and permanently redirects to `/gallery/`. Its first
edition remains in repository history as the research prototype that led to
the larger, stricter collection.
