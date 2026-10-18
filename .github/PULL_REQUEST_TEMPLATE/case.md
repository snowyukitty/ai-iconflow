<!-- Case contribution: one reviewed icon family + its case record.
     Open this template with ?template=case.md on the PR URL.
     Every box is a gate, not a suggestion; see CONTRIBUTING.md "The case lane". -->

## Case

- Slug / project label:
- Essence (one word):
- User job (one line):

## Sources (semantic SVG)

- [ ] `master.svg` is semantic, on the 1024 grid, inside the safe area (groups/ids name the parts; no traced raster, no live `<text>`).
  <!-- prove: docs/SVG_TECHNIQUES.md §11; `iconflow check --config iconflow.toml` flags live <text> -->
- [ ] `tray.svg` is included and linked to `iconflow.toml` **when a tray target is selected** (a card alpha is not a menu-bar silhouette).
  <!-- prove: `iconflow check --config iconflow.toml` (audits the template); docs/OUTPUT_TARGETS.md `tray` -->
- [ ] `iconflow.toml` records the brief: app intent, user job, essence, clichés, signature device, targets.
  <!-- prove: `iconflow init` writes the fields; `iconflow doctor --config iconflow.toml` -->

## Mechanical gate

- [ ] `iconflow check master.svg` is clean (paste the output or attach `check --json`); tray sources also ran `--tray-svg tray.svg --tray-template-mode <mode>`.
  <!-- prove: `iconflow check --config iconflow.toml --json` (same audit as ship) -->
- [ ] Review Lab receipt (`master-review.json`) is attached, `status: "ready"`, bound to this exact source (`source_sha256`) and contract (`contract_sha256`).
  <!-- prove: Review Lab export, or headless `iconflow review --evidence DIR` + `iconflow score`; docs/REVIEW_CHECKLIST.md -->
- [ ] All six axes score >= 4 (legibility / distinctiveness / balance / color / scalability / craft):
  <!-- prove: the receipt's `scores`; `iconflow ship --config iconflow.toml --review master-review.json` refuses anything less -->
- [ ] The PR Proof action is green (check, review, receipt binding) - or explain which step could not run.
  <!-- prove: docs/PROOF_ACTION.md -->

## Design evidence

- [ ] Cliché avoided (name it):
  <!-- prove: docs/CONCEPTING.md Step 2 -->
- [ ] Signature device (one, ownable):
  <!-- prove: docs/CONCEPTING.md Step 3; bake off a device-free control (L56) -->
- [ ] Name-the-thing test passed at 128px **and** 16px (the noun did not change).
  <!-- prove: the visual-silhouette strip of review.png; `iconflow neighbours` -->
- [ ] One reusable, testable lesson (a future reader can check it, not "make it cleaner"):
  <!-- prove: docs/EVOLUTION.md §1 (a rule, not a diary entry) -->

## Case record

- [ ] `iconflow case new ...` file is in `casebook/` with *Summary* and *What failed first* filled in, first-pass and final scores recorded.
  <!-- prove: `iconflow case new --slug ... --first ... --final ...` -->
- [ ] `iconflow case lint` is clean.
  <!-- prove: `iconflow case lint` -->

## Provenance (clean room)

- [ ] Original geometry drawn from a written rule; no traced, adapted, or copied third-party mark, path, palette, or trade dress.
  <!-- prove: docs/PROVENANCE.md -->
- [ ] Any reference that materially informed the work is named with its license signal.
  <!-- prove: docs/PROVENANCE.md (name the source and its license) -->
- [ ] Contributed under Apache-2.0 (CONTRIBUTING.md "Commits & PRs"); no rights to the IconFlow name or logo are implied.
  <!-- prove: CONTRIBUTING.md "Commits & PRs" -->

## Privacy

- [ ] No private repository names, local paths, personal data, secrets, or generated `work/` files.
  <!-- prove: AGENTS.md step 8 privacy rules; `git diff --stat` shows no work/ files -->
- [ ] Privacy-sensitive origins are reduced to a neutral user-job verb; the case keeps the visual evidence only.
  <!-- prove: docs/EVOLUTION.md §1 "Sanitize public cases" -->

## Contributor terms

- [ ] Commits are signed off (`git commit -s`, the DCO).
  <!-- prove: `git log --format=%b` shows Signed-off-by on every commit -->
- [ ] I have read [`CLA.md`](../CLA.md) and agree to it — paste the signature line below.
  <!-- prove: the signature line below -->

```
I have read CLA.md and I agree to it.  Signed: <your full name>, <YYYY-MM-DD>
```
