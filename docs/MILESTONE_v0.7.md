<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Milestone 0.7 — one audit, platform targets, the brand kit, headless review

Built on branch `milestone-0.7` on 2026-10-18 from real use: a full-bleed
3x3 grid mark that `check` passed and `ship` failed, a hand-rendered Android
icon set, a brand change propagated by hand, and a review scored without the
Review Lab. `CHANGELOG.md` (Unreleased) lists every change; this page records
what was decided, what was measured, and what is still the owner's call.

## What changed, by goal

| Goal | Result | Where |
|---|---|---|
| A. One source of truth | `check`, `review`, `ship` resolve inputs and audit through one function; a regression test runs all three on one SVG and config | `iconflow/audit.py`, `tests/test_audit.py` |
| A. Warnings name inputs | every warning names its background, size, scheme, rung or scale and a concrete fix | `iconflow/qa.py` |
| B. Maskable composition | `maskable_scale`, linked `maskable_svg` with a `maskable-drift` same-mark gate; contract-bound only when it changes bytes | `iconflow/build.py`, `config.py` |
| B. Android | adaptive, themed, legacy and Play Store assets, golden-tested; one audit covers PWA and Android | `docs/OUTPUT_TARGETS.md`, `tests/test_android.py` |
| B. iOS / MSIX | **not added**, with the reason written down | `docs/OUTPUT_TARGETS.md` *Not targets yet* |
| C. Brand kit | `brand build` / `sync` / `outline`, gated on the mark's approval | `iconflow/brand.py`, `docs/BRAND_KIT.md` |
| D. Headless review | `review --evidence` + `score`; second opinions recorded, never gating | `iconflow/headless.py`, `docs/REVIEW_CHECKLIST.md` |
| E. Distillation | 20 lessons: 6 new rules (L59–L64), 7 merged, 2 rejected, 1 held; DISTILL NOW cleared | `docs/LEARNINGS.md` |
| E. Legibility budget | `iconflow budget`, in `compare` and in headless findings; advisory | `iconflow/budget.py`, `docs/LEGIBILITY_BUDGET.md` |
| F. DX seeds | 5 shipped, 1 closed as stale, 2 left open with notes; `init` detects targets | `docs/ISSUE_SEEDS.md`, `iconflow/detect.py` |
| G. Site | Getting started and the icon-size reference updated, five languages | `website/` |
| G. STATE | the two FAILs and two OPEN gates written as one-step owner actions | `docs/OWNER_ACTIONS.md` |

## Decisions taken (and why)

- **`all` stays the 0.6 set.** Receipts store the expanded target list; adding
  `android` to `all` would have turned every approved `all` project stale on
  upgrade. Android is asked for by name.
- **One composition for PWA and Android.** The maskable canvas maps onto the
  108dp layer at 82.5dp, so the 40% safe circle is Android's 66dp circle and
  one audit guards both. A per-platform scale was rejected: it would let the
  two crops drift apart.
- **Contract keys appear only when they change bytes.** Every 0.6 receipt,
  including the packaged demo family's, still matches (verified by the demo
  run and `tests/test_contract.py`).
- **`outputs` may gain keys within schema 1** (`audit`, `findings`,
  `review_surface`). The PR Proof action checks `schema`, not key sets.
- **Headless review needs a reason per axis.** That is a stricter bar than the
  Lab (which takes a slider), deliberately: a score without a stated reason is
  how an unattended agent rubber-stamps.
- **The budget advises, it never gates.** It flagged 6 of 7 documented failing
  first drafts and at least one finding on 43 of 100 shipped finals, which do
  lose what it says; that is a measurement to act on, not a verdict.
- **The brand kit takes an outlined wordmark; fontTools is optional.** Live
  `<text>` is non-deterministic and carries an unseen font licence. The core
  keeps its two dependencies.
- **`no-transform` was not added to the site headers.** It would close the
  beacon FAILs from the repository but also stop edge compression of HTML; the
  dashboard switch has no such cost.
- **Two cases were relabelled before admission.** Their file names and
  project labels carried private repository names; the same alias was also
  removed from `docs/NEIGHBOURHOOD.md` and two test fixtures. It remains in
  git history of the public repository, which a rename cannot undo.

## Verification (2026-10-18)

- `python -m unittest discover -s tests`: 437 tests, OK (32 skipped without
  Chromium), on Python 3.14 and on Python 3.10.
- Chromium-gated suites (`ICONFLOW_BROWSER_TESTS=1`): browser security,
  ladder, neighbours, family, Forge browser — all OK; `forge_parity.py`
  44/44; `build_collision_index.py --check`, `build_gallery.py --verify-only`
  OK; every preset passes `check`.
- `iconflow demo`: doctor → check → review → ship OK, 23 files.
- Clean-clone `uv build`: wheel and sdist pass `scripts/verify_distribution.py`;
  `OWNER_ACTIONS.md` and `STATE.md` stay out of the wheel.
- `ruff check .` clean; five-language site byte-identical to a fresh render.
- Real-use replay on the consuming project's drafts (read-only, in a scratch
  copy): the grid draft that passed `check` and failed `ship` now fails
  both; the owner's original full-bleed grid passes at `maskable_scale = 0.7`.
- Dogfood: the Android target, the target-context sheet, the Review Lab's
  Android card and a full brand kit were built from IconFlow's own mark and
  inspected as images; two presentation defects found that way were fixed.

## Independent review (2026-10-19)

`codex:default` (`gpt-6-astra`, effort xhigh) reviewed the ten core modules in
a sealed, read-only ATD packet: verdict **REQUEST_CHANGES**, fourteen defects
(seven high), one design note. Every defect was reproduced against the code,
fixed, and pinned by a regression in `tests/test_hardening.py` named after its
finding (R01–R14). The most serious one predates this branch: a namespace
prefix hid a `<script>` from `check`'s safety scan. The review ran on file
snapshots, not on the runtime; it executed nothing.

The same reviewer then verified each fix commit in four further sealed passes,
which converged: pass 2 found five fixes partial and four regressions the fixes
introduced (N01–N04), pass 3 one partial and one regression (N05), pass 4 a
Windows drive-relative bypass (N06), pass 5 an alias bypass (N07). All are
fixed with regressions. One point was deliberately not taken: pass 5 asked
that the working directory itself be refused when it is a link; it is the
caller's own location, and refusing it would break anyone who `cd`s into a
linked folder, so it is trusted and documented as such. CI separately caught
two things no static pass could: tests that launched Chromium only because
the machine had one, and macOS's `/var` → `/private/var`, which showed that
"no link in any ancestor" is the wrong rule. The rule now is "no link the
project carries": every component below the working directory, recognised
through any spelling of its path, plus `..` and drive-relative paths refused.

Its design note (R16) is the right next milestone, and is recorded here rather
than half-built: **one immutable render plan**. Today `check`, `review`,
`score`, `ship` and `brand` share their *inputs*, but each still renders its
own pixels; every composition defect the review found (scale rounding, the
master-as-link alias, Android's native sizes) was a place where those renders
could diverge. A plan — source snapshots, effective transforms, every native
variant, and the hash of every output — computed once, audited, shown to the
reviewer, and then published byte for byte after approval, would make
"reviewed pixels are shipped pixels" a property of the design instead of a
property each command must re-establish.

## Not measured

- Whether the budget raises first-pass legibility. It shipped today;
  `case stats --since 2026-10-19` measures it as cases arrive.
- Second opinions between different products: the protocol and receipt
  fields exist and are tested, no cross-product review has been recorded yet.
- `brand outline` against a real CJK or variable font in production use; it
  was exercised with Inter (OFL) and a synthetic test font.

## Owner decisions

1. ~~Release 0.7.0~~ — **done 2026-10-19** at the owner's instruction: release
   commit `96b904d`, annotated tag `v0.7.0`, TestPyPI rehearsal green and
   smoke-tested, GitHub Release with the candidate artifacts, `pypi`
   environment approved, PyPI wheel SHA-256 `3a72591a…` equal to the reviewed
   candidate (the sdist differs by archive timestamps, as expected).
2. ~~Merge `milestone-0.7` into `main`~~ — done (fast-forward); CI green.
3. ~~Deploy the site~~ — done: preview verified, then production; host
   contract and Forge live checks pass.
4. **The Cloudflare beacon** — disable it in the dashboard (preferred), take
   the `no-transform` fallback, or allow the script (`docs/OWNER_ACTIONS.md`).
5. **Social preview upload and Discussions** — one step each
   (`docs/OWNER_ACTIONS.md`).
6. **IconFlow's own wordmark.** A brand kit for IconFlow was built in a scratch
   directory with an Inter Bold outline to test the tool; adopting a wordmark
   is a brand decision, so nothing was committed to `brand/`.
7. **IconFlow's Android background.** The paper background puts the graphite
   card inside a paper tile on Android launchers; a graphite
   `background_color` (or a linked `maskable_svg`) would let the card fill the
   shape. A brand call, not changed.
8. **Atlas pointer.** The private registry's icon record for that production
   tool still names the case's old file name; it is now
   `casebook/2026-08-22-shot-coherence-pattern-card.md`. A cross-project edit,
   left to the owner.
9. **The held lessons.** Two stay open for corroboration (a hanging object's
   support ratio; a nested device capped by its grid).
