<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# What a receipt proves, and where trust comes from

IconFlow's gate ends in a receipt: six scores, the reasons for them, and the
hashes of what was scored. Since 0.8 the receipt binds the exact output bytes
(`docs/RENDER_PLAN.md`); since 0.9 the automated audit measures those same
bytes. This page says what all of that does and does not establish, and what
a team that needs more should put around it. It is the decision record for
0.9's "trust anchor" question, too.

## What IconFlow checks

Every `ship`, on every machine:

- **Consistency.** Each command captures its sources once, and every stage
  that renders or measures — the plan, the audit, the published files —
  uses that snapshot. Two reads are deliberately separate: `ship` hashes the
  sources to validate the approval before it captures them, and `review`
  reads them again at the end to see whether they moved. A source that
  differs from the one the approval names is a stale receipt
  (`receipt-stale-source`); one that changes between those reads is refused
  (`source-changed`).
- **Automated quality.** The audit's rules (coverage, contrast, maskable
  safe zone, identity of a linked source, the ladder, declared neighbours)
  must pass. With a render plan, the probes that have a shipped counterpart
  measure the plan's own files; the rest render the captured source.
- **Output identity, relative to the approval.** A plan-bound receipt names
  every output's pixels and bytes. `ship` refuses different pixels
  (`plan-drift`), and `ship --plan` publishes the reviewed bytes themselves.
- **The floor.** Every axis at 4 or more, a ready status, no warnings.

## What it does not

- **It does not authenticate the reviewer.** `reviewer.name` is whatever the
  person or agent typed. Anyone who can write the receipt and the plan can
  recompute every hash in them.
- **It does not prove that anyone looked.** A receipt says scores were
  recorded against these exact bytes; it cannot say eyes were on them.
- **It does not audit every output.** The audit reads the 16, 32 and 512 px
  master frames and the maskable composition the plan ships; Android's
  native layers, the ladder rungs, the tray template and the neighbourhood
  are measured from renders of the captured source. `outputs.plan.audit_frames`
  lists exactly which probe read which file.

The minimum honest summary: *IconFlow checks source and settings consistency,
its automated quality rules, and output identity relative to the supplied
approval. It does not authenticate the reviewer or prove visual inspection.
In a controlled workflow, approval authority comes from the repository's
enforced review process and a trusted CI job; an attestation can bind the
released files to that job and to the recorded approval, and is worth
something only to a consumer who verifies it.*

## Why IconFlow does not sign receipts

Considered for 0.9 and declined, with the independent reviewer's agreement.

A signature would authenticate a key, not an inspection, and it would move
key management — generation, storage, rotation, revocation, and telling every
consumer which keys to trust — into a local-first, offline tool with two
dependencies. Keyless signing needs an identity provider and the network.
Either way the tool would have to answer a question its users have usually
answered already, in the place where their review happens: the repository.

So IconFlow keeps the parts only it can provide — exact bindings, and the
digests that let something else refer to them:

- `ship --json` reports **`outputs.receipt_sha256`**: the SHA-256 of the exact
  receipt bytes it parsed and validated (`null` for an approval through the
  config's `[review]` table). It identifies the approval; it does not
  authenticate it.
- A headless receipt records `review_surface.findings_sha256` (the evidence
  scored) and `review_surface.audited_plan` (whether that audit measured the
  plan). A Review Lab receipt records `review_surface.kind: "review-lab"`, the
  toolchain that generated the page, and — when the reviewer fills it in — a
  self-declared `reviewer` with an export-time `declared_at`. None of these is
  read by any gate.

## If you need an anchor: a repository policy

This is a recipe, not something IconFlow enforces or its own CI exercises.
Verify each setting in your repository before claiming it.

1. **Fix the approval path.** One receipt (for example
   `design/master-review.json`), one config, one evidence directory. A job
   that accepts any receipt path accepts any receipt.
2. **Make changes to it reviewable by the right people.** A `CODEOWNERS` entry
   covering the receipt, `iconflow.toml`, every consumed source
   (`master.svg`, linked tray/maskable/monochrome sources), the saved plan,
   the workflow files, and `CODEOWNERS` itself. A `CODEOWNERS` file only
   *requests* review: branch protection must also require code-owner
   approval, dismiss stale approvals when new commits arrive, and require
   approval of the most recent push. Administrators bypass branch protection
   unless that is turned off; decide and document who may.
   (GitHub: [code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners),
   [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).)
3. **Ship from a trusted job with a pinned IconFlow** (0.9 or later) and fail
   on anything short of the full claim:

   ```yaml
   - run: iconflow ship --config iconflow.toml --review design/master-review.json --plan design/evidence/plan --json > ship.json
   - run: |
       python - <<'PY'
       import json, sys
       envelope = json.load(open("ship.json", encoding="utf-8"))
       plan = (envelope.get("outputs") or {}).get("plan") or {}
       ok = (envelope.get("status") == "ok" and plan.get("mode") == "replayed"
             and plan.get("verified") is True and plan.get("bytes_verified") is True
             and plan.get("audited") is True
             and isinstance(envelope["outputs"].get("receipt_sha256"), str))
       sys.exit(0 if ok else 1)
       PY
   ```

   A missing field is a failure, never an assumption. `audited` is false
   for a target set with no plan-aware probe (emote only, for one); a policy
   for such a project must say it accepts that, rather than drop the check.
   Locally, a receipt without a plan still ships (with `plan-unbound`); this
   job is where that stops being acceptable.
4. **Bind the delivery, not the directory.** `write_plan` leaves files it
   does not own where they are, so package `outputs.files` from `ship.json` —
   not the whole output directory — and, immediately before freezing the
   bundle, hash every packaged file and compare it with the approved plan's
   per-file `sha256` (`plan/plan.json`); a file changed after `ship` must stop
   the job, because nothing downstream would notice. Record the result in a
   manifest beside `receipt_sha256`, the plan digests and the commit, outside
   the render plan (the plan's contract is the icon bytes).
5. **Attest it, and verify where it is consumed.** GitHub's artifact
   attestations record which workflow, in which repository, at which commit,
   produced a file; they establish provenance, not safety, and they help only
   a consumer who checks them (`gh attestation verify`). Pin the attestation
   action to a reviewed commit; attestations need OIDC permissions, and their
   availability depends on the repository's visibility and plan — check
   GitHub's current guide rather than assuming.
   (GitHub: [artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations).)

The PR Proof action (`docs/PROOF_ACTION.md`) consumes `check` and `review`:
it shows a pull request's icon, it does not ship one. It is the wrong place
for an approval attestation, and 0.9 adds none to it.
