# Social Signals

Social Signals is an independent clean-room design study: 20 familiar social
user jobs translated into 20 original concrete nouns, silhouettes, negative-
space systems, and IconFlow construction grammars.

The collection is published separately from the 100-case IconFlow Gallery. It
does not change that gallery's admission count.

## Status

- Research snapshot: 2026-08-12
- Public route: `/gallery/social-signals/`
- Public catalog: `/assets/gallery/social-signals/catalog.json`
- Cases: 20 generated, 20 visually reviewed, 20 admitted, 0 rejected
- Classification: reviewed practice specimens, not shipped identities
- Seed: `iconflow-social-signals-2026-08-12-v1`

## Research method

Context selection uses DataReportal's Digital 2026 global reporting and Pew
Research Center's current social-media fact sheet as complementary evidence.
The sample optimizes for broad recognition, distinct user jobs, and geographic
and category coverage. It is not presented as a universal MAU ranking because
platforms disclose incompatible metrics and several do not publish comparable
current figures.

Sources:

- [DataReportal Digital 2026: Global Overview Report](https://datareportal.com/reports/digital-2026-global-overview-report)
- [DataReportal Digital 2026 Mid-Year Global Update](https://datareportal.com/reports/digital-2026-mid-year-global-update-report)
- [DataReportal: Top Social Platforms](https://datareportal.com/reports/digital-2025-sub-section-top-social-platforms)
- [Pew Research Center Social Media Fact Sheet](https://www.pewresearch.org/internet/fact-sheet/social-media/)

Direct platform-name mapping, per-brand guideline URLs, access limitations, and
restriction notes are kept in `work/social-signals/research.md`; that appendix is
not deployed. Public labels describe generic jobs only.

## Deterministic style assignment

The build script starts with the 20 style IDs in milestone order and calls
`random.Random(seed).shuffle(styles)`. The resulting mapping is checked against
the catalog before any render or receipt is written. Every style appears once.

## Clean-room safeguards

- No official logo, wordmark, glyph, mascot, font, screenshot, UI, or vendor
  asset was downloaded into or used by the build.
- No official silhouette is combined with official brand colors.
- Each study starts from a generic user job and a concrete noun outside the
  relevant platform's established trade dress.
- Public copy does not pair a platform name with a study mark.
- The page states that the collection is independent and unaffiliated.
- The collection does not claim to replace official logos or to be guaranteed
  non-infringing.

Visual distance is not legal clearance. Residual risk includes undiscovered
third-party marks, jurisdiction-specific confusion analysis, and future brand
changes. Commercial adoption should receive a formal trademark search and
legal review.

## Evidence contract

Every admitted study includes:

- editable `master.svg` with `viewBox="0 0 1024 1024"`;
- clean `iconflow check` output;
- exact 16×16 and 128×128 PNGs;
- 128×128 silhouette proof;
- a complete Review Lab sheet inspected at original resolution;
- a receipt bound to the current source and build contract;
- all six rubric axes at 4/5 or higher;
- a reusable casebook record.

Large public specimens use SVG. Native proofs are true 16×16 PNGs displayed at
exactly 16 CSS pixels.

## Rebuild

Use the repository interpreter from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\build_social_signals.py --stage
.\.venv\Scripts\python.exe scripts\build_social_signals.py --finalize
```

`--stage` writes finalists, bake-offs, review sheets, and check results. It does
not create passing receipts. `--finalize` fails closed unless the current 20
sources have a complete visually reviewed decision file.
