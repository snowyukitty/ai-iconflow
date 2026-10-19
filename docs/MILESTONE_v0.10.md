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
| C-F08 | min–max normalisation is unstable and can erase identity | dropped: one composite over black, then luminance; `ios-tinted-faint` gates a faint result; colours that merge into one grey are advised (R10) — partly closed: a merge is reported, not gated |
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

## Implementation review

Same route, on the code: **REQUEST_CHANGES**, 13 findings (R01–R13),
confidence 0.96. All taken; each regression is named after its finding. Run
against the pre-fix code, the behaviour regressions for R01–R10 and R12 fail;
the R11 additions (the real square, the README promises, the 0.9 contract
keys) pin behaviour that was already right, and R13's refusal predates 0.10
(below). The first verification pass corrected an earlier, broader claim.

| # | Finding | Resolution |
|---|---|---|
| R01 | a stylesheet (`circle{fill:red}` on a circle card, `rect + circle{…}`) or `display`/`visibility` could repaint or re-mean the artwork once the background is removed or extended | `display`/`visibility` refused on the background; stylesheet rules may select by id or class only — a rule naming the background's element type, or using siblings, position, negation, attributes or `*`, is refused; `@media` blocks are read like any other |
| R02 | `score` inherited 0.9's allowance for evidence without provenance | an iOS review must carry its saved plan and plan-bound provenance; `load_plan` validates every imported iOS set |
| R03 | nothing compared a plan's iOS set with what the trusted master and settings make | `audit.check_ios_plan`: appearances, `ios_variants`, background, dark-source hash and every text file, used by the audit, `ship` and `score` |
| R04 | an imported `mark.svg` was never validated | validated as SVG and held to `check`'s active/external-content rule, and compared with the master's own derivation |
| R05 | an unused `ios_dark_svg` was still read (and could break) non-iOS reviews | captured only when consumed |
| R06 | moving a project made linked-dark evidence stale | `ios_dark_source` compared by name, like the other linked sources |
| R07 | an iOS failure inside the audit became exit 2 and hid QA warnings | an underivable set is the gating finding `ios-underivable`; a replayed set the inputs contradict is a deferred `plan-replay` |
| R08 | Pillow decodes 2- and 4-bit grey as `L` | the PNG header's bit depth and colour type are checked, and `tRNS`/`acTL` refused |
| R09 | contrast was judged on uncomposited RGB | each pixel is composited onto the dark ground before it is judged |
| R10 | colours that become one grey were not reported (C-F08's structure loss) | advisory `ios-tinted-merge` names the pair; it does not gate, since only a person knows whether the difference carries the mark |
| R11 | the square regression was vacuous; C-F15/C-F17 had none | a renderer that really draws a square, with the mixed selection asserted; regressions for the Composer layer on import, the README's promises and the 0.9 contract keys |
| R12 | an Expo `platforms` list excluding iOS was ignored | an explicit list decides |
| R13 | `exists()` misses a dangling link at a known iOS path | already refused before this check: 0.8's output-tree validation rejects any link in the output folder (shown by mutation); `lexists` added, and the regression pins the refusal |

## Verification passes

1. **First verification**: **REQUEST_CHANGES**, 8 findings; R05, R09, R12
   and R13 confirmed closed.

| # | Finding | Resolution |
|---|---|---|
| V01 | `load_plan`'s iOS check never ran (`RenderPlan` freezes lists into tuples) and its test loaded `plan.json` instead of the directory | tuples accepted; the test loads the directory, with a valid control and a wrong-mode and a hostile import, each refused for the iOS reason |
| V02 | with a circle card, `rect{…}` becomes live once full bleed makes it a rect; upper-case pseudo-classes and CSS escapes slipped through; `.iconflow-background-accent` was falsely refused | selectors are validated positively (type, `.class` and `#id` compounds with descendant or child combinators; anything else refused), bare `rect` is refused alongside the card's own type, and ids are matched as tokens |
| V03 | `check_ios_plan` did not bind the master or the scheme | both compared, the master hashed the way a captured source is |
| V04 | an unexpected Composer layer passed | every iOS text file must be present exactly when the master makes it |
| V05 | a Windows path recorded in evidence did not compare on POSIX (also true of 0.9's maskable and tray sources) | basenames split on both separators |
| V06 | a second IHDR could disagree with the decoder | one 13-byte IHDR first, chunks inside the file, IEND last, nothing after |
| V07 | translucent regions escaped the merge advisory | merge candidates are the colours composited over black, alpha ≥ 128 |
| V08 | the R07 replay regression never reached the new check; the mutation claim was too broad | a self-consistent downgraded plan with a receipt bound to it is refused as `plan-replay` (exit 1) before the audit; the claim above is now exact |

Run against the code before these fixes, the V01, V02, V03, V04, V06 and V07
regressions fail; V05's fails on POSIX only (Windows `pathlib` reads both
separators); V08's replay test exercises the R07 fix and is the regression
that finding asked for.

2. **Second verification**: **REQUEST_CHANGES**, 3 findings, all in the
   stylesheet check; V01 and V03–V07 confirmed closed.

| # | Finding | Resolution |
|---|---|---|
| W01 | a `;`-ended at-rule (`@layer icons; rect{…}`) hid the rule after it | the regular expressions were replaced by a linear CSS scanner: statements end at `;`, grouping at-rules (`@media`, `@supports`, `@layer`, …) are scanned for rules at any depth, other at-rule blocks are skipped, strings are respected, and anything it cannot classify is refused |
| W02 | an empty-able compound under a repetition backtracked exponentially on long whitespace | selectors are tokenised in one left-to-right pass with no backtracking; a 5,000-space adversarial selector is refused in under a millisecond |
| W03 | legal identifiers (`.-accent`, non-ASCII, `#-mark`) were refused | CSS identifier rules (a letter, `_`, non-ASCII, or `-` then one of those or `-`); escapes are still refused |

On the code before these fixes the W01 and W03 regressions fail and W02's
hangs — the defect itself; a scan of every SVG in the repository (1,439, of
which 48 declare a background) finds no declared master refused.

3. **Third verification**: **REQUEST_CHANGES**, 7 findings (X01–X07), again
   all in the stylesheet check: comment markers inside strings, nested rules
   (CSS Nesting, which Chromium applies — found here independently and shown
   by a render), an escaped `@m\65 dia`, escaped braces and newline-broken
   strings, `@scope` preludes, two quadratic paths, and a quoted `@supports`
   condition refused.

   Each pass had found a deeper corner of CSS lexing, and a partial CSS
   parser is an arms race. The decisive fact: not one of the 1,439 SVGs in
   this repository has a `<style>` element. So the accepted language was cut
   to what cannot be mis-read — top-level style rules and one level of
   `@media` blocks, comments, element/class/id compounds with descendant or
   child combinators — and everything else is refused: strings, escapes,
   nested rules, every other at-rule. With no quotes or backslashes there is
   nothing to mis-lex, and one forward pass with `str.find` is linear.
   X01–X06 are closed by that; **X07 is refused by design** (a quoted
   condition is a string), recorded as the one deliberate narrowing: dark
   styling belongs in a linked `ios_dark_svg`. On the previous scanner every
   X regression fails; the pathological inputs (20,000-deep `@media`,
   unterminated comments, long whitespace) now run in a child process with a
   hard timeout, so a super-linear scanner fails the test instead of hanging
   the suite.

## Verification

- Suite: 653 tests (`tests/test_ios.py` adds 68) on Python 3.14 and 3.10;
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
4. Getting started: replace the "Mobile scope" line (it says iOS is not a
   target) and add an iOS output card, in all five languages
   (`website/i18n/*.json`, `scripts/build_i18n.py`);
5. deploy the site only after PyPI carries 0.10.0.

## Owner decisions

1. **Release 0.10.0** — when the owner says so.
