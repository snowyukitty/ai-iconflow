# Changelog

All notable changes to IconFlow are documented here. The project uses Semantic
Versioning for published releases; repository-only development before the
first published release remains under `Unreleased`.

## Unreleased

### Added

- An advisory macOS tray-template audit, `iconflow check <master> --tray-svg <tray.svg> [--tray-template-mode auto|alpha|contrast]`, surfaced by `review` as well. It compares the interior detail of the colour tray asset against the enclosed holes of the derived template and reports a template that kept none of the mark's features — the failure that ships a featureless black lozenge to the menu bar. Advisory by design: it audits a linked variant, so it informs the designer without gating `ship`.
- Two worked `examples/` icon families built through the full gated loop from one brief, `iconflow-balloon` (Balloon Haypile) and `iconflow-parachute` (Canopy Haypile), each with its editable master and tray source, source-bound receipt, shipped web/Tauri/Electron/tray outputs, and casebook record.
- Five distilled rules, `docs/LEARNINGS.md` L46–L50, folded into `CONCEPTING.md` §3, `DESIGN_PLAYBOOK.md` §2/§5, `SVG_TECHNIQUES.md` §11, and `OUTPUT_TARGETS.md`.
- Twenty structurally distinct, small-size-first technique scaffolds, a
  machine-readable `iconflow styles --json` catalog, and a Chromium-rendered
  `styles --gallery` proof matrix with per-family tray guidance.
- A launch-site product narrative and a 24-brief, cross-theme showcase plan
  designed to turn reviewed icon cases into website and video evidence.
- A responsive, dependency-free promotional site with an interactive native-pixel
  Proof Lab, technique gallery, accessible controls, security headers, and a
  canonical production deployment at `ai-iconflow.com`, with
  `ai-iconflow.pages.dev` retained as a permanent compatibility redirect.
- An agent-first `/getting-started/` guide with copyable cross-platform setup,
  an honest agent/CLI responsibility split, the complete quality-gated loop,
  exact output families, current limitations beside the workflow, and
  crawlable `WebSite` / `SoftwareSourceCode` metadata without invented ratings.
- Cross-platform setup scripts that deploy the open-format IconFlow skill to
  Codex, Claude Code, open Agent Skills, and GitHub Copilot discovery homes.
- Nine reviewed Theme Worlds now prove subject range beyond the fixed Flow Gate
  specimen: relationship, cat, dog, fish, original character, and game. Each
  includes an editable SVG, source-bound receipt, native 16px render, shipped
  web assets, and a casebook record.
- A 100-case Gallery spanning specific product worlds and construction
  grammars. Every case exposes an editable SVG, exact native 16px proof,
  silhouette, contract-bound review receipt, and reusable case record; eleven
  weaker or repetitive directions were removed from 111 generated candidates.
- Two separately labeled clean-room practice collections: Social Signals maps
  20 user jobs across all 20 techniques, and Emoji Matrix provides a complete
  20-by-20 field of 400 source-bound specimens.
- A clean-clone `build_gallery.py --verify-only` gate that rechecks all 100
  tracked sources, receipts, renders, case records, and deploy copies without
  the gitignored candidate-adjudication workspace.
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

- Setup now installs the Codex/Open Agent Skills user copy only under
  `~/.agents/skills/iconflow/` and removes the legacy
  `~/.codex/skills/iconflow/` duplicate that current Codex also discovers.
- The promotional site's canonical host is now `ai-iconflow.com`. Canonical
  links, Open Graph URLs, structured data, `robots.txt`, and the sitemap point
  at the apex, and exactly one host serves content. `www.ai-iconflow.com` and
  `ai-iconflow.pages.dev` redirect through the shell project's `_redirects`;
  `iconflow.pages.dev` redirects through a Pages Functions middleware, because
  Pages supports no domain-level `_redirects` rule and a project cannot
  host-match its own default host. Deployment previews still serve, so they
  stay testable. `rel=canonical` was not sufficient on its own: it advises
  crawlers, while root-relative internal links kept a visitor who landed on the
  old host there for the whole session.
- The site's CSP drops its two pinned inline-script hashes for plain
  `script-src 'self'`. A Chromium probe confirmed that `application/ld+json`
  raises no `securitypolicyviolation` under `script-src 'self'` and stays
  readable from the DOM, so the hashes protected nothing while invalidating the
  CSP on every structured-data edit. Every executable script is an external
  file, so the policy is now strictly tighter: no inline allowance at all, with
  a test that fails if an executable inline script is ever added.
- Site deploys go through `scripts/deploy-site.ps1`, which pins each directory
  to its Pages project and verifies the host contract afterwards. The mapping is
  easy to get wrong in both directions: deploying the content tree from the
  repository root silently ships no Functions bundle, and deploying the redirect
  shell to the content project would make the apex redirect to itself.
- Manual review approvals are bound to the complete source, project, target,
  color, Electron, and semantic tray-source transform contract.
- `iconflow new` refuses to overwrite an existing destination unless `--force`
  is explicit.
- CI uses least-privilege permissions, immutable action revisions, timeouts,
  Python 3.10 through 3.14 coverage, and installed-wheel browser tests.
- Automated QA can reuse one isolated Chromium rasterizer across a collection,
  avoiding one browser startup per SVG without weakening any check.
- Source-bound SVG hashes normalize line endings, keeping review receipts valid
  across LF and CRLF worktrees, and distribution verification runs without
  importing the uninstalled source package.
- Casebook metadata is normalized across the full corpus, with strict lint and
  the generated Atlas covering 181 reviewed or shipped cases.
- Windows package guidance now treats manifest-defined dimensions and filenames
  as part of the reviewed asset contract instead of relying on implicit scaling.
- The release-candidate clean-wheel smoke now installs its Chromium runtime
  before exercising render-backed checks.

### Security

- SVG input now rejects DTD/entity declarations, malformed or non-SVG XML,
  documents over 4 MiB, more than 50,000 elements, or nesting over 128 levels.
- Build output rejects existing symlinks, junctions, and reparse points before
  generated files are written.
- Windows shortcut scripts now use securely created unique temporary files.

## 0.4.0 - 2026-07-21

- Introduced the brief-to-concept-to-review workflow, multi-target icon engine,
  six-axis quality gate, Review Lab receipts, and evolving casebook.

`0.4.0` is the repository's current package version. As of 2026-08-13 it has no
Git tag, GitHub Release, or PyPI distribution.
