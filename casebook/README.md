# Casebook

One structured markdown file per **shipped** icon — the raw experience that
drives the self-evolution loop (see `docs/EVOLUTION.md`).

- Create entries with `python -m iconflow case new --slug <slug> ...`
  right after a successful gated `ship`, then fill in the prose sections.
- `python -m iconflow case lint` validates frontmatter, scores, dates, and the
  normalized taxonomy. Use `--strict` after legacy cases have been migrated.
- `python -m iconflow case stats` aggregates everything here into the health
  report: weakest first-pass rubric axis, house-cliché warnings, undistilled
  lessons.
- `python -m iconflow case atlas --out case-atlas.html` creates the
  dependency-free visual audit for score movement, taxonomy concentration,
  status, and evolution signals.
- Lesson bullets use checkboxes: `- [ ]` = not yet distilled into
  `docs/LEARNINGS.md`; flip to `- [x]` once promoted.

Case files are hand-editable; the parser only relies on the `---` frontmatter
block, the `## Lessons` heading, and checkbox bullets.
