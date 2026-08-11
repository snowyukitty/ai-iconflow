# Changelog

All notable changes to IconFlow are documented here. The project uses Semantic
Versioning for published releases; repository-only development before the
first published release remains under `Unreleased`.

## Unreleased

### Added

- Fourteen structurally distinct, small-size-first technique scaffolds, a
  machine-readable `iconflow styles --json` catalog, and a Chromium-rendered
  `styles --gallery` proof matrix with per-family tray guidance.
- A clean-room style research record covering current upstream licenses,
  small-size lessons, and explicit no-asset-copy provenance.
- Apache-2.0 project licensing, package license metadata, attribution notices,
  and a separate trademark policy protecting the official IconFlow identity.
- Browser integration tests proving that external SVG resources do not reach
  the network and that animated input renders repeatably.
- Distribution-content verification and a non-publishing release-candidate
  workflow with checksums and wheel reproducibility checks.
- Security, provenance, contribution, issue, pull-request, and release guidance.

### Changed

- Manual review approvals are bound to the complete source, project, target,
  color, Electron, and semantic tray-source transform contract.
- `iconflow new` refuses to overwrite an existing destination unless `--force`
  is explicit.
- CI uses least-privilege permissions, immutable action revisions, timeouts,
  Python 3.10 through 3.14 coverage, and installed-wheel browser tests.

### Security

- SVG input now rejects DTD/entity declarations, malformed or non-SVG XML,
  documents over 4 MiB, more than 50,000 elements, or nesting over 128 levels.
- Build output rejects existing symlinks, junctions, and reparse points before
  generated files are written.
- Windows shortcut scripts now use securely created unique temporary files.

## 0.4.0 - 2026-07-21

- Introduced the brief-to-concept-to-review workflow, multi-target icon engine,
  six-axis quality gate, Review Lab receipts, and evolving casebook.

`0.4.0` is the repository's current package version. As of 2026-08-11 it has no
Git tag, GitHub Release, or PyPI distribution.
