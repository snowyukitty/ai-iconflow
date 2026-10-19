<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Milestone 0.10 — semantic layers and the iOS app icon

Branch `milestone-0.10`, started 2026-10-19 on top of the 0.9.0 release.
`CHANGELOG.md` (Unreleased) lists every change; this page records why this
milestone, what was decided and how it was verified. Not released: a release
needs the owner's word.

## Why this milestone

Three candidates were weighed, with evidence:

1. **More integrity work** — 0.9's "Not done" (Android layers, ladder rungs,
   tray template and neighbourhood measured from plan files; release
   manifests). 0.7, 0.8 and 0.9 were all integrity milestones; the remaining
   items are real but small for a user. Kept on the list.
2. **First-pass legibility** — `iconflow case stats` names legibility the
   weakest first-pass axis (3.2 over 203 cases; distinctiveness 3.3; 2.3
   review rounds per ship). Mined: August's 169 cases are mostly bulk matrix
   and social-signal batches (first-pass legibility 3.08 there, 3.78 in July),
   and the casebook keeps no first-draft SVGs, so no predictor could be
   backtested. A milestone here could not be measured honestly; deferred.
3. **iOS** — the largest mobile platform, and the one target IconFlow lacked.
   0.7 declined it in writing: iOS 18's dark and tinted icons "need *semantic*
   sources, not a transform of the light icon". Meanwhile
   `SVG_TECHNIQUES.md` §11 had told every author since 0.5 to declare
   `id="iconflow-background"` "so the build/review pipeline can select the
   right semantic role" — and **no code read it**. The sources 0.7 asked for
   existed and were unused. Chosen.

## What Apple asks for (researched 2026-10-19)

- Apple, *Configuring your app icon using an asset catalog*: iOS builds every
  size from one 1024 px image ("Single Size"); appearances Any, Dark, Tinted;
  "Provide your tinted app icon as a grayscale image. Provide your dark app
  icon with a transparent background so the system-provided background can
  show through." Variants are optional (the system applies its own treatment).
- Icon Composer (`.icon`, Xcode 26+) is Apple's preferred path; the WWDC26
  Icon Composer lab recommends importing SVG layers at full canvas size and
  treats Icon Composer as "a second step after your initial drawing, as a
  place to annotate your icon". The `.icon` format is not published; asset
  catalog icons remain supported (and are auto-segmented for Liquid Glass).
- Expo (`ios.icon: {light, dark, tinted}`), Flutter (`flutter_launcher_icons`)
  and Capacitor consume the same three PNGs.
- **Probe** (throwaway branch, Xcode 26.6 on `macos-latest`): a hand-made set
  compiled; `assetutil` recorded light `Opaque`, dark `UIAppearanceDark`
  non-opaque, tinted `ISAppearanceTintable` `Gray` opaque, phone and pad. A
  deliberately wrong set (light with alpha, opaque dark, RGB tinted) compiled
  **without a warning**: Xcode enforces none of the appearance rules, so
  IconFlow must.

## What was built

| | | Where |
|---|---|---|
| Semantic layer reader | declared background only; a capability check, not a guess | `iconflow/ios.py` `resolve`, `full_bleed`, `mark_only` |
| `ios` target | catalog + light RGB / dark RGBA / tinted L, Icon Composer layer, README | `iconflow/ios.py`, `plan.ios_files` |
| Policy and linked source | `ios_variants` auto/system, `ios_dark_svg` (a captured, bound, replayed role) | `config.py`, `plan.py`, `cli.py` |
| Audit | 3 gating + 2 advisory codes on the plan's files; encodings validated; provenance | `audit._ios_audit`, `plan.audit_ios` |
| Review | iOS row in `targets.png`, iOS card in the Lab, plan files only | `headless._ios_row`, `review._ios_card` |
| Scaffolds | 15 card presets declare their card (render-identical) | `templates/presets/` |
| Detection | real iOS project evidence only | `detect._ios_evidence` |
| Xcode in CI | `actool` + `assetutil` on three generated sets | `scripts/verify_ios_catalog.py`, `ci.yml` `xcode-ios` |

Calibration on the 15 tagged presets (real Chromium): IconFlow's own master
and 10 presets pass; woodcut and ink-brush (black ink on a light card) are
refused, correctly — their mark disappears on the dark screen; mascot (its
black contour) and woven (0.4994 against 0.5, purple on near-black) are
refused at the edge. Counting cuts painted in the card colour as cuts, not as
illegible mark, was added after blueprint, chrome and stained-glass were
flagged while visibly readable.

## Design consult (sealed, before code)

`codex:default`, model `gpt-6-astra`, `--quality deep`: 21 findings,
confidence 0.92, "adopt iOS, but not as proposed". Every finding was taken;
the regression that proves each is named after it in `tests/test_ios.py`.

| # | Finding | Resolution |
|---|---|---|
| C-F01 | new defaults would stale old approvals and evidence | iOS keys appear in the contract, plan parameters and `outputs.audit` only when `ios` is selected and they bind something; both target registries extended |
| C-F02 | derived texts could alias the master's caches | independent `RenderCache` per derived text; immutable resolution, every derivation re-parses |
| C-F03 | tagging presets changes source bytes | claim scoped: renders identical, text and hashes change; said in the CHANGELOG |
| C-F04 | rectangle inference is no proof (and missed the 84.98% house card) | dropped: only a declaration counts; untagged masters ship light only, with a hint |
| C-F05 | copying `fill` loses transforms, CSS, effects, inheritance | a strict supported subset; anything else is a `LayerError` naming the rule |
| C-F06 | references to the background break the mark | any `href`/`url()` to it, or a stylesheet selecting it, is refused |
| C-F07 | removing a light card does not make a dark design | linked `ios_dark_svg` and `ios_variants = "system"` ship now; contrast measured as legible share of the mark (a bright dot cannot rescue it); dark rendered in the dark scheme |
| C-F08 | min–max normalisation is unstable and can erase identity | dropped: one composite over black, then luminance; `ios-tinted-faint` gates a faint result |
| C-F09 | ladder rungs could differ between audit, export and ship | the audit reads the shipped 1024 px files; `mark.svg` is reduced to the 1024 rung |
| C-F10 | pixel identity cannot see PNG modes; RGB conversion is not flattening | `validate_files` on build, audit and import; light composited before dropping alpha |
| C-F11 | completeness and plan-bound approval | `audit_ios` validates the set; the audit refuses a plan whose appearances contradict the policy; an `ios` ship needs a plan-bound approval |
| C-F12 | provenance would omit iOS measurements | `ios-light/dark/tinted` origins from one definition (`audit_origins`), checked by `score` |
| C-F13 | an iOS sheet could silently go missing | the iOS row lives in the required `targets.png`, cut from plan files with no recompute fallback |
| C-F14 | corner rules misfire on valid iOS artwork | inset-card became the `ios-light-flattened` advisory; `ios` alone skips the hard-square `coverage-16` (0.9 behaviour kept for every other selection) |
| C-F15 | parser and exported SVG need a safety contract | the master is validated by `load_svg` before any parse; `mark.svg` is that validated text minus one element, no more exposed than the `favicon.svg` IconFlow already ships (see "Dissent") |
| C-F16 | the clip helper turns transparent previews white | previews composite onto their ground before masking; missing appearances are labelled |
| C-F17 | the Icon Composer promise was too strong | "a starting point, not a finished `.icon`"; emitted only with a declared foreground; painted cuts are said not to be holes |
| C-F18 | a light-only build leaves stale variants behind | refused before any write, naming the files |
| C-F19 | README line endings could drift across platforms | every iOS text file is written LF |
| C-F20 | broad detection would mistake output for evidence | Xcode `iphoneos` builds and framework iOS scaffolds only |
| C-F21 | advisories could become receipt warnings | the two informational codes are advisories, never warnings |

### Dissent

**C-F15 (partly).** The consult asked for a full SVG safety contract before
vector export (bounded parsing, DTD rejection, active-content sanitising).
Every master already passes `rasterize.load_svg` — the size bound, UTF-8, the
active-content and external-reference checks — before `ios.resolve` parses
it, and `mark.svg` is that validated text with one element removed. It is no
more exposed than the master's own `favicon.svg`, which IconFlow has shipped
verbatim since 0.5. A sanitiser for republishing arbitrary SVG remains out of
scope, as `README.md` already says.

## Verification

- Suite: 630 tests (`tests/test_ios.py` adds 45) on Python 3.14 and 3.10;
  ruff clean; real-Chromium classes pass (`ICONFLOW_BROWSER_TESTS=1`).
- Built bytes: 156 files across the five 0.9 configurations identical to a
  `v0.9.0` checkout, through `build()` and through the session `ship` uses.
- Xcode: the `xcode-ios` CI job compiles a declared master, a tagged
  scaffold and an untagged one with `actool` 26.x; `assetutil` agrees with
  every declared appearance and encoding.
- Real flows on the demo family plus `ios`: `check`, `review --evidence`,
  `score`, `ship`, `ship --plan` (byte-identical replay), the Lab card (also
  at 360 px).
- Presets: 15 tagged, render-identical to `v0.9.0` in both schemes at 16, 32,
  64 and 1024 px.

## Limits

- The dark ground (`#1C1C1E`) and the three thresholds are heuristics; the
  Lab shows the files, and iOS's own gradient differs.
- No Icon Composer `.icon` is written; Liquid Glass "clear" appearances are
  Icon Composer's.
- Expo, Capacitor and Flutter recipes follow their documentation; only Xcode's
  compiler is exercised in CI.
- The Review Lab overflows horizontally at 360 px with or without iOS
  (pre-existing).

## Release checklist (0.10.0, on the owner's word)

The usual run (`docs/RELEASING.md`), plus, because `ios` is not on PyPI yet:

1. remove the "New in IconFlow 0.10" note from `scripts/build_reference.py`
   and re-render the reference page;
2. drop the "on `main` until it reaches PyPI" qualifiers in `README.md`;
3. teach the skill the `ios` target and move the plugin version;
4. deploy the site only after PyPI carries 0.10.0.

## Owner decisions

1. **Release 0.10.0** — when the owner says so.
