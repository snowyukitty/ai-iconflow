<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license. -->
# Milestone 0.9 — what was audited is what was reviewed is what ships

Branch `milestone-0.9`, started 2026-10-19 on top of the 0.8.0 release. 0.8
made the receipt bind the exact output bytes; its record ended on two open
items — the audit still rendered for itself (review finding F09), and nothing
authenticated the reviewer. This milestone closes the first, decides the
second, and fixes the friction found by using the product end to end.

## How the work was chosen

Before any design, the product was used as a newcomer would: the packaged
demo, a fresh project (`init` → `new` → `check` → `review --evidence` →
`score` → `ship` → `ship --plan`), the Review Lab in a browser with an
exported receipt shipped, and the live Forge and emotes pages, including a
Forge project kit taken through the CLI. Every Chromium session and render was
counted by wrapping the renderer.

| run (0.8.0, demo family unless noted) | browsers | renders | repeats | wall |
|---|---|---|---|---|
| `review --html` (Review Lab) | 9 | 67 | 19 | 10.7 s |
| `review --evidence` | 5 | 31 | — | 5.8 s |
| `ship` | 2 | 19 | — | 3.9 s |
| `review --evidence`, a one-target project | 6 | 33 | — | 6.8 s |

(Repeats counted on the full request — SVG, size, background and scheme; the
first count, without the scheme, overstated them, as the second voice pointed
out.) The Lab rendered every size in both schemes and then replaced the
shipped scheme's renders with the plan's frames. `ship --plan`, the strongest
0.8 mode, audited a fresh local render, not the bytes it published.

Friction found on the way, and what became of it:

| found | outcome |
|---|---|
| A Lab draft was keyed by the SVG alone: the same SVG under another background, target set or renderer restored the old scores (found by the second voice, D13) | fixed |
| An emote-only Review Lab said "No targets selected" (D16) | fixed: an emote card |
| A Lab receipt carried no reviewer, toolchain or surface, unlike a headless one | fixed, as provenance |
| `score` printed the whole axis walk, then rejected a short reason | fixed: validated first |
| A Playwright error escaped as a traceback (it is not a `RuntimeError`) | fixed: exit-2 envelope |
| Toolchain provenance said `iconflow 0.7.0` on 0.8 code (stale editable metadata) | fixed: the running code's version |
| `review --evidence` help said "no browser needed" | corrected |
| The Forge project kit's README gave only the Lab path | fixed: the headless path, with every required flag |
| 110 emote download links named only "SVG" / "PNG 128" | fixed: "Joy SVG" |
| The emotes page's nav lacked Icon sizes | fixed |
| Two Forge layer buttons can share a name ("Wedge layer 3") | kept: the list is an ordered list, so position is announced; a distinct name needs new strings in five languages for little gain |
| The scaffold sits at distance 0.00 from two house presets | not a bug: 0.004, printed to two places; the two scaffolds are near-identical at 16 px |

## What changed

| | What | Where |
|---|---|---|
| Render session | One owner per command; one browser, a context per scheme; the renderer's raw bytes remembered by the complete request; bounded by bytes; failures never cached, a failed launch never retried, schemes never substituted | `iconflow/session.py`, `rasterize.py` |
| Captured sources | Each source read once per command; the plan, the audit, the approval check and the replay check measure those bytes | `plan.capture_sources`, `cli.py` |
| The audit on the plan | Probes with a shipped counterpart read the plan's files; validated selectors; provenance per probe | `qa.py`, `audit.py`, `plan.audit_frames` |
| Gate selection | One state machine in `ship`: plan, audit, then one outcome in 0.8's order | `cli._cmd_ship` |
| Evidence | `audit_provenance` in findings, validated by `score` against the saved plan; one-read digests | `headless.py` |
| Receipt identity | `outputs.receipt_sha256`; receipts hashed from the bytes validated | `config.py`, `cli.py` |
| Review Lab | plan-first rendering, bound drafts, provenance, emote card | `review.py` |
| Trust | the decision and a repository policy | `docs/TRUST.md` |

## Decisions, and who weighed them

Claude Code decided; `codex:default` (model `gpt-6-astra`, deep) was the
second voice, weighed below it, through sealed read-only ATD consults.

- **F09's shape** — a render session that memoises raw renderer bytes, plus a
  narrow frame resolver for the plan's files, not a public provider framework.
  The second voice's design: both layers, internal.
- **Which probes may read the plan** — only untransformed master renders.
  Emote sizes are none the audit probes; Electron is rounded, apple-touch
  flattened, tray and Android composed. A wrong-sized frame or two
  disagreeing representations refuse the plan: an integrity failure is never
  "fall back to a clean render".
- **`ship --plan` audits the replayed bytes.** That ends 0.8's promise that
  `check`, `review` and `ship` always agree: on another machine they now
  measure different pixels, on purpose. The parity promise is kept where it
  means something — the same machine, the same pixels.
- **Precedence is unchanged, order is not.** The plan is made first (the audit
  reads it); the outcome is chosen afterwards, in 0.8's order, so a deferred
  plan failure never reaches the report unless it is the outcome.
- **No signing in IconFlow** (`docs/TRUST.md`). Agreed by the second voice,
  which corrected the rationale (signing need not mean a new dependency;
  external tools exist) and made the repository anchor conditional on an
  enforced policy rather than "the VCS".
- **No approval attestation in the PR Proof action**, and no release-manifest
  tooling in 0.9: the action consumes `check` and `review`, which do not
  ship; a manifest needs a consumer and a verification policy first. The
  recipe is documented; IconFlow's own CI does not exercise it.
- **`check` computes no plan** — it stays a few renders.
- **`brand build`** composes its kit after the gated ship, outside the ship's
  session; the one-render claim is scoped to `review` and `ship`.
- **Website changes** reach production with the next release's site deploy.

## Independent review

1. **Design consult** (before code): 16 findings, D01–D16, twelve high. All
   adopted; the attestation and manifest tooling it outlined (D12) is
   documented, not built, for the reason above. Each finding has a regression
   in `tests/test_audit_on_plan.py` named after it:

   | | finding | closed by |
   |---|---|---|
   | D01 | a master-only check does not bind the run to its approval; QA reopened paths | captured sources, approval checked against them, review checkpoint |
   | D02 | plan-first could reverse precedence or downgrade integrity failures | the state machine; `PlanError` never downgraded |
   | D03 | `master_frames` lost selectors and validation | `audit_frames` / `audit_maskable` |
   | D04 | auditing saved pixels breaks universal parity | parity scoped to equal pixels; replay test |
   | D05 | pixel equality is not byte identity | raw bytes only cached; 156-file baseline |
   | D06 | renderer reuse did not reach every surface; eager rendering | seams in every surface; plan-first lookups |
   | D07 | a digest check is not a provenance contract | `audit_provenance`, validated frame by frame |
   | D08 | hashes must cover the bytes parsed | one-read findings and receipts |
   | D09 | `audited` needs a meaning | defined; `audit_frames` reports scope |
   | D10 | the session needs a failure and memory policy | bounded, no retries, ordered close |
   | D11 | repository authority is conditional | `docs/TRUST.md` |
   | D12 | attesting build files alone binds nothing | documented, not built |
   | D13 | Lab drafts could carry old scores to a new plan | bound drafts and prefill |
   | D14 | score prevalidation must handle interactive input | complete preflight |
   | D15 | contract wording | `docs/AGENT_CONTRACT.md` reconciled |
   | D16 | the Lab had no emote context | emote card |

2. **Implementation review**: REQUEST_CHANGES, 14 findings (R01–R14, four
   high). The reviewer passed renderer isolation and ship's publication order.
   Each finding has a regression named after it (`ImplementationReviewTests`,
   `LazySurfaceTests`):

   | | finding | outcome |
   |---|---|---|
   | R01 | review surfaces and the receipt seed reopened source files; a replaced hard-linked role went unseen | a frozen view: while a command runs every `load_svg` of a captured path returns the captured text; each role keeps its own path for the checkpoint |
   | R02 | configured scores could pre-fill a Lab for another effective contract or plan | never for a plan-bound Lab; otherwise only for the effective contract |
   | R03 | an incomplete web plan fell back to fresh pixels | required files and favicon slots per target, or `PlanError` |
   | R04 | a partial provenance record could certify a full audit | one definition (`plan.audit_origins`) that `qa.check` follows and `score` compares exactly |
   | R05 | a valid plan for another source could ride along in evidence | the saved plan's inputs, scheme and background must be the evidence's |
   | R06 | a malformed origin escaped as a traceback | type checks; shape errors become exit 2 |
   | R07 | a QA-blocked ship omitted the plan record | reported before the outcome is chosen |
   | R08 | renderer cleanup stopped at the first failure | each part released, the first error raised after |
   | R09 | the emote card scaled its images | native sizes on light and dark chat grounds, the plan's own bytes |
   | R10 | fallbacks still ran before plan lookups | the favicon only for web; the Lab's linked source only at 512 |
   | R11 | the trust recipe did not check `audited`, the receipt digest, or packaged bytes | all three |
   | R12 | wording: universal parity, schema, caching, probe coverage | reconciled |
   | R13 | three tests did not exercise what they named | rewritten: a file replaced right after it is read, a valid but unapproved replay; one was mutation-checked against the old code |
   | R14 | a second opinion was hashed from a reopened file | one read |

   **Kept, against the reviewer (R01):** review outputs are not staged and
   withheld until the final checkpoint. With the frozen view no artifact can
   mix two versions; each is bound to the captured hash, so one left behind
   by a refused review is refused downstream as stale (`score` checks the
   source hash, `ship` the receipt's). Staging every sheet, the Lab and the
   template would add a publication step to a command whose outputs are
   evidence, not deliverables, to protect against a case the hashes already
   refuse.

3. **First verification**: REQUEST_CHANGES, ten findings — eight partial
   closures and two new defects introduced by the fixes. All taken; each has
   a regression in `VerificationPassTests` (V-…, N…). The reviewer judged
   the R01 dissent reasonable once every source a review reads is captured,
   which this pass made true.

   | | finding | outcome |
   |---|---|---|
   | V-R01 | `--targets` could drop a linked source the sheets still show from the capture | every configured source captured and checked; the plan gets the consumed ones |
   | V-R03 | Tauri containers could lose a frame | exact slot sets for every audit container; the targets list validated |
   | V-R04 | the findings' own audit inputs decided which probes were required | `score` passes the configuration's inputs; the findings must match them |
   | V-R05 | a saved plan missing a linked role, or with other settings, passed | exact role set and the full plan parameters from the configuration |
   | V-R06 | null evidence entries or warnings escaped as tracebacks | every record's shape checked first |
   | V-R08 | a cleanup error could replace the error that mattered | the primary failure always wins |
   | V-R10 | the Lab still computed shipped-scheme transforms before taking plan files | plan files first for web, Tauri, Electron and tray; no linked render when the plan ships the composition |
   | V-R13 | the second-opinion test passed against the old loader | the hook now fires after a text read too; mutation-checked against the 0.8 loader |
   | N01 | emote rows could clip in a narrow card | rows wrap; checked in a browser at 360 and 1280 px (six images at native size, none clipped) — a manual check, not a test |
   | N02 | a plan failing the completeness check broke the gate order | checked in ship's deferred plan phase: `plan-replay` after a clean audit, `qa-warnings` first |

## Verification

- Built bytes: 156 files across five configurations, identical to a `v0.8.0`
  checkout in content and path order, through `build()` and through the
  session `ship` uses (real Chromium, Windows).
- Audit parity under real Chromium: findings and metrics identical with and
  without the plan in five configurations, two of them with warnings.
- Real flows: demo; Lab review → export (with a reviewer) → ship; headless
  review → score → ship → `ship --plan`; the Forge kit's README sequence from
  a clean project, including its placeholder reasons failing in one line.
- Suite: 583 tests (`tests/test_audit_on_plan.py` adds 64), on Python 3.14
  and 3.10; its Chromium tests run with `ICONFLOW_BROWSER_TESTS=1`.
- What is a test and what is a measurement: the byte baseline, the parity
  table and the render counts were measured by scripts against real Chromium
  (the parity has a Chromium test; the byte baseline and the counts do not —
  they need a `v0.8.0` checkout and a wrapped renderer). D06, D11, D12, D15,
  R11 and R12 are closed by code structure and documents, not by a named
  test; N01 by a browser measurement.

## Not done

- The release-manifest and attestation tooling sketched in `docs/TRUST.md`.
- Android's native layers, the ladder rungs, the tray template and the
  neighbourhood are measured from renders of the captured source, not from
  plan files (none of them is a plain master frame).

## Owner decisions

1. **Release 0.9.0** — when the milestone is ready, on the owner's word.
2. **Merge the Atlas branch** `fix/iconflow-case-pointer` (still open from 0.8).
