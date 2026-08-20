<!-- Case contribution: one reviewed icon family + its case record.
     Open this template with ?template=case.md on the PR URL.
     Every box is a gate, not a suggestion; see CONTRIBUTING.md "The case lane". -->

## Case

- Slug / project label:
- Essence (one word):
- User job (one line):

## Sources (semantic SVG)

- [ ] `master.svg` is semantic, on the 1024 grid, inside the safe area (groups/ids name the parts; no traced raster, no live `<text>`).
- [ ] `tray.svg` is included and linked to `iconflow.toml` **when a tray target is selected** (a card alpha is not a menu-bar silhouette).
- [ ] `iconflow.toml` records the brief: app intent, user job, essence, clichés, signature device, targets.

## Mechanical gate

- [ ] `iconflow check master.svg` is clean (paste the output or attach `check --json`); tray sources also ran `--tray-svg tray.svg --tray-template-mode <mode>`.
- [ ] Review Lab receipt (`master-review.json`) is attached, `status: "ready"`, bound to this exact source (`source_sha256`) and contract (`contract_sha256`).
- [ ] All six axes score >= 4 (legibility / distinctiveness / balance / color / scalability / craft):
- [ ] The PR Proof action is green (check, review, receipt binding) - or explain which step could not run.

## Design evidence

- [ ] Cliché avoided (name it):
- [ ] Signature device (one, ownable):
- [ ] Name-the-thing test passed at 128px **and** 16px (the noun did not change).
- [ ] One reusable, testable lesson (a future reader can check it, not "make it cleaner"):

## Case record

- [ ] `iconflow case new ...` file is in `casebook/` with *Summary* and *What failed first* filled in, first-pass and final scores recorded.
- [ ] `iconflow case lint` is clean.

## Provenance (clean room)

- [ ] Original geometry drawn from a written rule; no traced, adapted, or copied third-party mark, path, palette, or trade dress.
- [ ] Any reference that materially informed the work is named with its license signal.
- [ ] Contributed under Apache-2.0 (CONTRIBUTING.md "Commits & PRs"); no rights to the IconFlow name or logo are implied.

## Privacy

- [ ] No private repository names, local paths, personal data, secrets, or generated `work/` files.
- [ ] Privacy-sensitive origins are reduced to a neutral user-job verb; the case keeps the visual evidence only.
