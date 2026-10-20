<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Architecture — how the engine is put together

IconFlow is a deterministic engine around one decision a person (or an agent)
makes: *these pixels are good enough to ship*. Everything in `iconflow/`
exists either to make that decision well-informed (render the truth, measure
it, show it) or to make it binding (record what was decided, refuse anything
else). This page maps the modules onto that job, follows one icon from source
to shipped files, and lists the invariants a change must keep. The contracts
it summarises live in their own documents: [`WORKFLOW.md`](WORKFLOW.md) (the
procedure), [`RENDER_PLAN.md`](RENDER_PLAN.md) (reviewed pixels are shipped
pixels), [`TRUST.md`](TRUST.md) (what a receipt proves), and
[`AGENT_CONTRACT.md`](AGENT_CONTRACT.md) (exit codes, JSON, warning codes).

## Layers

Read from the bottom up. Every top-level import points down this table;
the six that point up are function-level imports, made where they are needed
(`build.build` → `plan`, `plan` → `qa` for the renderer-safety warnings,
`audit` and `neighbours` → `config`, `budget` and `family` → `review` for
their sheets). Five modules import nothing of IconFlow's and serve every
layer: `findings` (the one warning type), `styles` (preset metadata),
`agentkit` (packaged resources, the skill and the docs), `casebook` and
`shortcut`. `tests/test_architecture.py` holds the code to this table.

| layer | modules | job |
|---|---|---|
| front doors | `cli`, `detect`, `brand` | parse a command, call the layers below, print one result; propose targets from a project's own files; propagate an approved mark into the brand kit |
| decision records | `config`, `review`, `headless` | the `iconflow.toml` contract and its digest; the contact sheet, Review Lab and receipt template; the headless evidence directory and `score` |
| audit | `audit`, `qa`, `budget`, `shapefield`, `neighbours`, `family` | one set of audit inputs for `check`, `review` and `ship`; every probe, each speaking the one `Finding` type with its stable code |
| plan | `plan` | every byte a build will write, computed once, compared, saved, replayed |
| composition | `build`, `ios`, `ladder`, `assemble`, `htmlhead` | per-target file sets from rendered frames: detail-ladder rungs, `.ico`/`.icns` packing, maskable and Android composition, the iOS appearances, the web head and manifest |
| rendering | `rasterize`, `session` | validate untrusted SVG and render it in isolated Chromium; one browser per command, every request rendered once |

`rasterize` is the only module that renders (`cli` only installs and
diagnoses Chromium). In `check`, `review` and `ship` a `RenderSession` owns
the browser and every stage borrows it, which is what makes "the audit
measured what ships" checkable rather than assumed. A library caller that
passes no renderer, and the commands outside that chain (`compare`,
`family`, `render`, parts of `brand`), open a `Rasterizer` of their own.

## One icon, review to ship

```text
master.svg ─┐
iconflow.toml┤  plan.capture_sources   each source read once, hashed
             │          │
             │  config.contract_inputs ─► contract_sha256 (targets, colours, scheme, linked sources…)
             │          │
             │  plan.compute_plan ─► RenderPlan (every file, content + byte digests)
             │          │
             │  audit.run_audit(plan=…)  probes read the plan's own frames where one exists
             │          │
  review ────┴─► Lab / review.png / --evidence DIR (findings.json + plan/)
                        │
  score  ────────► receipt: six scores + reasons, bound to source, contract, plan, audited frames
                        │
  ship   ────────► re-capture → re-audit → plan.compare(receipt.plan, new plan)
                        │                     └─ any difference: plan-drift, nothing written
                        └─► plan.write_plan (or `ship --plan DIR`: replay the reviewed bytes)
```

Every arrow is a hash comparison, not a convention. A source edited between
review and ship changes `source_sha256`; a setting changes `contract_sha256`;
a renderer that draws one pixel differently changes the plan's content digest.
`build` is `compute_plan` then `write_plan` with no gate — the lower-level door
for integrations that own an equivalent gate.

## Invariants a change must keep

1. **Byte identity.** A milestone that does not mean to change an output keeps
   every built file byte-identical to the previous release; each milestone
   record (`MILESTONE_v*.md`) says how that was measured. New behaviour
   arrives behind a new target, a new key, or a declaration in the source
   (`data-lod`, `id="iconflow-background"`), never as a silent change to an
   old file.
2. **Fail closed.** A gate that cannot decide refuses: an unreadable plan is
   a `PlanError`, never a reason to measure a fresh render instead; a
   malformed receipt field is a configuration error, never "unbound".
3. **One render per request.** `check`, `review` and `ship` open at most one
   Chromium (`RenderSession`), one context per colour scheme; a failed
   browser is not retried, one scheme is never substituted for another.
4. **Write after compute.** `write_plan` writes only a plan that is complete;
   a target that fails late leaves the output directory as it was.
5. **Untrusted input.** SVG is validated before Chromium sees it (size,
   element count, depth, no DTD; `WORKFLOW.md` § Security) — after it is
   read, so a source's size is checked, not its read. A saved plan is
   imported as hostile: no links, no unnamed file, reads bounded by the
   measured size, every identity recomputed from the bytes. Evidence and
   receipts are bound by hashes of the bytes parsed. Source paths may be
   links (a linked maskable source is a feature); output paths may not go
   through one the project carries (`build.output_link`; for a configured
   output the project is the repository holding the config).
6. **One vocabulary.** Every finding is a `Finding` with a code published in
   `AGENT_CONTRACT.md`; exit codes mean the same with or without `--json`
   (`0` completed, `1` blocked by a gate, `2` usage, configuration or runtime).

## Adding a target

A target touches more modules than a probe does, because it is part of the
contract a receipt binds. The `android` (0.7) and `ios` (0.10) changes are
the worked examples; the touch points, in dependency order:

1. `build.TARGETS` and `config.TARGETS` (append; a test holds them equal;
   `APP_TARGETS`, what `all` means, stays frozen so old receipts stay valid).
2. The file set: a `*_files` function in `build` (or its own module, as
   `ios`), called from `plan.compute_plan`; any new source role in
   `plan.ROLES`, `consumed_roles` and `capture_sources`.
3. The contract: new settings in `config` (field, validation, `contract_inputs`
   key — bound only when the target is selected, so older digests are
   unchanged) and in `audit.AuditInputs`.
4. The audit: probes in `qa` or the target's module, with codes added to
   `AGENT_CONTRACT.md`; plan-aware frames in `plan.audit_*` when a probe has a
   shipped counterpart.
5. The evidence: a row in `headless.target_sheet`, a card in the Review Lab
   (`review`), and the receipt fields `score` checks.
6. The front doors: CLI flags, `detect` evidence, `OUTPUT_TARGETS.md`, the
   reference page (`scripts/build_reference.py`), and the skill — the skill
   only in the release commit that puts the target on PyPI
   ([`RELEASING.md`](RELEASING.md)).

## Known seams

Kept visible so they are changed deliberately rather than discovered:

- `cli.py` carries orchestration that belongs to no single command: the
  ship gate (`_cmd_ship`) and review (`_cmd_review`) are each several hundred
  lines. They are tested end to end through `main()`, which is why they have
  not been split during feature milestones.
- `build.build_web` and its siblings write one target straight into a
  directory without a plan. They are the 0.7 writers, kept for callers that
  drive a single target; `build()` and `ship` never use them.
- Per-target knowledge is spread across the touch points above by design (a
  receipt must bind it), so a target's rules are found by its name, not in
  one class.
