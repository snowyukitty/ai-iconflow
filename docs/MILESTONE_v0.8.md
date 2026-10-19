<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license. -->
# Milestone 0.8 — the pixels you reviewed are the pixels that ship

Branch `milestone-0.8`, 2026-10-19. 0.7.0 was released the same morning; this
milestone takes the design note it ended on (R16) and makes it true, and
closes every open owner decision from 0.7.

## What changed

| | What | Where |
|---|---|---|
| Render plan | Every output computed once, in memory, from sources read once; immutable; a content digest and an exact-byte digest; a provenance digest over sources and settings | `iconflow/plan.py`, `docs/RENDER_PLAN.md` |
| Review binds pixels | Lab, `--receipt-template` and `--evidence` carry the plan; the sheets show the plan's own frames; `score` inherits it and never renders | `review.py`, `headless.py`, `cli.py` |
| Ship verifies | `plan-drift` (exit 1) when the rendered output differs, whatever the toolchain; full drift list in `outputs.plan` | `cli.py` |
| Reviewed bytes, anywhere | `ship --plan DIR` imports the saved plan as a hostile artifact and publishes it without re-rendering | `plan.py`, `cli.py` |
| No half-written icon sets | `build()` writes nothing until every file is staged; commit failures roll back; byte-identical to 0.7 | `build.py`, `plan.py` |
| Identity on a plate | `maskable-drift` reads the mark drawn on a card, so a card master can link a full-bleed maskable source | `qa.py` |
| IconFlow's own brand | Linked `maskable.svg` (the card fills launcher shapes), outlined Inter wordmark and tagline, deterministic GitHub card | `brand/` |

## Decisions, and who weighed them

The owner delegated the open decisions to Claude Code, with an independent
second voice (`codex:default`, model `gpt-6-astra`) weighed below it. Each
decision below was put to that voice first; its amendments were adopted
unless noted.

- **Beacon** — disable in the dashboard, never the `no-transform` fallback,
  never allow the script. The beacon turned out to come from the account-level
  Web Analytics site, not the Pages project the old notes named; it is off,
  and every page served is unmodified.
- **Social preview** — the brand kit's card, so the image is reproducible
  (two builds, identical bytes) and has no live text; the website's richer
  link-preview card stays a separate, documented generator.
- **Discussions** — on, with the default lanes and a welcome post that routes
  each kind of post and asks people to check sheets for private names.
- **Wordmark** — Inter Bold at −0.02em, picked by eye from 0 and −0.02em on
  both grounds; font release, file hashes and licence recorded.
- **Android background** — a linked maskable source instead of a new
  background colour, which would have changed the apple-touch icon and more.
  The identity check refused it at first: it compared the master's card with
  the maskable's mark. Fixed in the check, not worked around.
- **Brand and demo receipts stay plan-unbound** — they ship on every
  contributor's machine and inside the packaged demo, where another renderer
  may differ by a pixel; binding them would turn that into a refusal. The
  receipt says so. A project that ships from one place should bind.
- **R16 gates drift whatever the toolchain** — the second voice's first and
  highest finding against Claude Code's design, which had let a toolchain
  change excuse drift. A toolchain change explains drift; `--plan` is how a
  review made on one machine ships on another.
- **Held lessons** — both stay held (one case each); the counts in the 0.7
  record are reconciled.
- **Atlas pointer** — a one-commit branch in the private registry, left for
  the owner to merge, because its checkout was on someone else's branch.
- **A private project name in `PROMO_VIDEO.md`** — replaced on `main`; the
  published history keeps it.

## Independent review

All by `codex:default` (`gpt-6-astra`), sealed and read-only through ATD.

1. **Design consult** before any code: 12 findings on the R16 design; 11
   adopted, one (sharing one render provider between the audit and the plan)
   deferred and documented.
2. **Implementation review**: REQUEST_CHANGES, 13 defects (7 high) — review
   surfaces still showing their own renders, a planned file replacing a
   directory, a failed restore deleting backups, export clearing a directory
   it did not own, unauthenticated replay settings, containers identified by
   size instead of by slot, and more. All fixed with regressions
   (`tests/test_plan_hardening.py`, P01–P13).
3. **Verification**: nine fixed, four partial, three new (the worst: two
   glyphs sharing only a counter matched as one mark).
4. **Second verification**: four of seven fixed; the counter case survived
   for near-square glyphs, an empty unowned folder could still be deleted by
   export, and a deeply nested `plan.json` escaped as a crash.
5. **Third verification**: the folder and the nesting fixed; one more
   counter path (a glyph's counter against a standalone disk) and an
   overstated README line. Both changed: a plate's mark must span half the
   plate, and the README states that the pixel guarantee applies to
   plan-bound receipts.

Each pass's findings carry a regression test named after them. The final
state of the identity rule is deliberately conservative: when it cannot tell
a card from a glyph, it compares outlines only, which can refuse a correct
maskable source but cannot approve a different mark through a counter.

## Verification

- `python -m unittest discover -s tests`: 517 tests, 33 skipped, on Python
  3.14 and 3.10, with Chromium and with Chromium hidden (as CI's unit jobs
  run).
- Byte identity: `build()` before and after the refactor wrote the same 93
  files across two configurations (ladder, every target, linked sources).
- Real Chromium: plan-bound `review --evidence` → `score` → `ship` verified
  byte for byte; `ship --plan` replayed; the packaged demo passes all four
  steps.
- `state.py`: 25 pass, 0 fail, 0 open gates.

## Not done

- The audit still renders through its own calls (review finding F09).
- The trust anchor is still the receipt; a plan detects change, it does not
  authenticate a reviewer.
- The linked maskable icon reaches the website when this branch is released
  and the site redeployed.

## Owner decisions

1. **Release 0.8.0** — prepared on this branch, not done (it needs an explicit
   instruction, like every release).
2. **Merge the Atlas branch** `fix/iconflow-case-pointer`.
