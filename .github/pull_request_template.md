<!-- Contributing a reviewed icon family + case record? Use the case template
     instead: add ?template=case.md to this PR's URL (.github/PULL_REQUEST_TEMPLATE/case.md). -->

## Outcome

Describe the user-visible or maintainer-visible result and why it is needed.

## Verification

- [ ] Focused tests cover the change.
- [ ] `python -m unittest discover -s tests` passes.
- [ ] `python -m iconflow case lint` passes when casebook data changed.
- [ ] Built distributions were checked when packaging/resources changed.
- [ ] Browser output was rendered and inspected when pixels or target transforms changed.

List exact commands and any skipped or failing checks.

## Visual evidence

For icon or rendering changes, attach the bake-off/review evidence and record:

- cliché avoided:
- signature device:
- six final rubric scores:
- actual sizes and target contexts inspected:

## Safety and privacy

- [ ] No secrets, personal data, private project names, local paths, or generated work files were added.
- [ ] New dependencies/assets include provenance and license information.
- [ ] The change preserves network isolation and review-receipt binding, or explains and tests the intended boundary change.
