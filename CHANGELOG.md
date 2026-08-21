# Changelog

All notable changes to IconFlow are documented here. The project uses Semantic
Versioning for published releases; repository-only development before the
first published release remains under `Unreleased`.

## Unreleased

### Added

- **The site speaks five languages.** English under `website/` stays the source
  of truth; `scripts/build_i18n.py` extracts every translatable string into
  `website/i18n/en.json` (keyed by a slug plus a hash of the English text, so a
  copy edit invalidates its translations instead of silently keeping a stale
  one) and renders `/es/`, `/ja/`, `/zh-hant/`, and `/zh-hans/` copies of `/`,
  `/getting-started/`, `/how-icons-are-made/`, `/archive/`, and the 404 page.
  The build **fails closed**: one missing key drops that whole language rather
  than mixing English into a translated page, and a translation that loses a
  markup placeholder or a `{size}`/`{count}` token is rejected the same way.
  Every page carries the complete `hreflang` set with `x-default`, a canonical
  URL in its own language, a language switcher in the header and footer, and a
  matching `sitemap.xml` entry with `xhtml:link` alternates; `_headers` gains a
  revalidation stanza per language route. Inline markup inside a sentence
  survives translation as numbered placeholders, so commands such as
  `iconflow check` stay verbatim inside translated prose. Copy that used to be
  hard-coded in `app.js`, `archive.js`, `playground.js`, and one CSS
  `content:` rule now lives in `data-*` attributes on the markup, which is what
  makes it translatable at all. CJK typography uses installed system faces only
  (no webfont: `font-src 'self'`) and resets the Latin display tracking.
  Evidence is never translated — the 137 archive readings, mark names, file
  names, hashes, and score strings stay exactly as they ship. Terminology,
  honesty rules, and per-language style are pinned in
  `website/i18n/GLOSSARY.md`.

- **Agent Contract v1** (`docs/AGENT_CONTRACT.md`): `doctor`, `check`, `review`, `ship`, and `demo` accept `--json` and emit exactly one envelope on stdout (`schema`, `command`, `status`, `exit_code`, `warnings`, `advisories`, `outputs`, `errors`) with human lines on stderr. QA warnings now carry stable codes (`svg-safety`, `viewbox`, `stroke-floor`, `coverage-16`, `contrast`, `maskable-detail`, `distinctiveness-text`; advisory `tray-template-featureless`), `ship` blocks report `receipt-stale-source`, `receipt-stale-contract`, `receipt-not-ready`, `score-below-floor`, or `qa-warnings`, and every `doctor` FAIL carries a copy-paste `fix` (Chromium: the exact `<python> -m iconflow setup`). The exit-code matrix is pinned to `0` ok / `1` blocked by an IconFlow gate / `2` usage, configuration, or runtime failure: `review` now exits `1` when automated QA warnings exist, `check` with only advisories exits `0`, and an incomplete, unapproved, or stale approved-config fallback is a gate block (`1`) rather than a configuration error. Successful ships report Review Packet v1 provenance (`toolchain`, and `artifacts` / `reviewer` when a receipt carries them; unknown receipt keys are tolerated). `review --receipt-template receipt.json` writes an unscored, source-bound receipt an agent can score and pass to `ship --review`.
- `iconflow demo --out DIR [--setup] [--json] [--force]`: materializes the packaged, already-reviewed brand family (`iconflow.resources.demo`, copied from `brand/` into `demo/` and shipped on the wheel via `importlib.resources`) and runs `doctor` → `check` → `review` (sheet + Review Lab) → `ship` against the bundled receipt, reporting each step and the worst exit code. Editing the materialized `master.svg` and re-running `ship` fails closed with `receipt-stale-source`.
- The **PR Proof GitHub Action** (`.github/actions/proof`, wired by `.github/workflows/icon-proof.yml` on `pull_request` for `**/*.svg`, `**/iconflow.toml`, and receipts): installs the pinned package, caches Playwright Chromium, runs `check --json` and `review --json` for every touched `iconflow.toml`, validates the receipt read-only through `scripts/proof_receipt.py` (`receipt-stale-source` / `receipt-stale-contract`), uploads the review sheet, writes a job summary parsed only from the Agent Contract envelopes, and fails on a QA warning or stale receipt with `contents: read` and no secrets. Documented in `docs/PROOF_ACTION.md`.
- The contributor funnel: a checkbox-driven case PR template (`.github/PULL_REQUEST_TEMPLATE/case.md`), the minimal receipt-bound `examples/community-case/` fixture (Keepsake Knot), a CONTRIBUTING "First 30 minutes" section with the install table and case lane, `docs/ISSUE_SEEDS.md` with eight bounded good-first-issue drafts, and skill/AGENTS wording that resolves `iconflow` on PATH first with the checkout as contributor mode.
- A browser-side **Remix Lab** on the homepage: the Petal, Balloon, and Canopy Haypile sources from one brief, live palette, card-radius, scale, mirror, and card controls, exact native 16–128px canvases rasterized by the visitor's own browser, a 16× pixel zoom, a colour-removed silhouette, an alpha-template preview, and Download SVG / Copy SVG / Copy agent brief actions. Nothing is uploaded; the lab labels its output as unreviewed and points at `check`, `review`, and `ship`.
- The **Living Archive**: every identity direction IconFlow drew while searching for its own mark — 137 original SVG studies across 7 rounds (proof machines, living care, expanded living, hidden brand, orchard & garden, canopy cargo, organic neko), each with an exact 16px proof, its status (study, gated finalist, promoted, or the temporary product mark), and its one-line reading. `scripts/build_archive.py` promotes the gitignored exploration into tracked `website/assets/archive/` assets and a `catalog.json`, regenerates `/archive/` (filters, deep links, detail dialog) and the homepage blocks between marker comments, and has a clean-clone `--verify-only` gate that the website tests run. The homepage now opens with archive marks drifting around the current mark, a three-row marquee wall of the whole archive, and a strip of the nineteen directions that passed the gate.
- A first-class methodology page, `/how-icons-are-made/`: the nine-stage pipeline with its two human stages marked, the user-job brief, divergence and the signature-device test, editable 1024-grid SVG and deterministic generation, exact Chromium rendering, what `check` and the similarity audits really test, human review and source-bound receipts, vector-versus-raster, the clean-room boundary and trademark caveat, and a five-tier relative cost model with no invented prices. Every claim sits beside a real repository artifact; the route is in the sitemap, the cache headers, the primary navigation, and the website contract tests.
- Four distilled rules, `docs/LEARNINGS.md` L51–L54 (dense control families keep the noun and give state its own rail; a coloured band on a dark block is a folder tab until a wedge and a cut say otherwise; repeated teeth cannot say "torn" at 16px; scan the 128/256px strips for spikes before scoring craft), folded into `DESIGN_PLAYBOOK.md` §6 and `REVIEW_CHECKLIST.md`, with the two recorded cases that produced them.
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

- Pre-publish UI/UX pass on the site, synthesized from three independent audits (Codex, Grok, Gemini via ATD): the hero rail is a real native-size scrubber with a pixel loupe; the primary navigation is six real destinations with the menu collapsing at 1000px on every page; the works wall sits directly under the hero with a persistent Pause/Resume control while the archive's explanation and finalist strip moved below the case studies; visible `:focus-visible` rings on every control, 44px coarse-pointer targets, `scroll-padding-top` for the fixed header, honest reduced-motion (animations off, not 0.01ms), raised contrast on dimmed headings and captions, intrinsic dimensions on every image, `aria-labelledby` on the technique dialog, Escape/outside-click for the mobile menu, `role="button"` archive cards, "passed review" instead of "gated", a one-line definition of the receipt, US "color" everywhere, a product-describing `<title>`, `og:image` dimensions/alt, versioned CSS/JS URLs, and revalidation headers for every canonical route.
- Every remaining Flow Gate brand asset now shows the current Petal Haypile mark: the homepage proof PNGs (`/assets/proof/icon-16…256.png`), the Proof Lab receipt scores and hash, the bake-off and review-sheet evidence images, the README hero, and the social preview SVG/PNG. Flow Gate stays only where it is explicitly historical or the fixed technique specimen.
- The Emoji Matrix explorer and complete matrix raise every mono micro label to 13px on desktop and at least 12px on tablet, widen the axis columns to fit, and open on the `u2764-fe0f--mascot` cell instead of the first catalog cell (hash and query URLs still win).
- `brand/tray.svg` gained one broad transparent eye cut so the macOS alpha template keeps a face; the receipt and contract hashes were re-bound and the tray outputs re-shipped (web/Tauri/Electron outputs were byte-identical).
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

### Fixed

- The unit-test matrix had failed on every push since 2026-08-20 because the
  review CLI test let the tray-template audit launch Chromium inside a job that
  has none; the audit is mocked like the other renderers, and the contract
  tests compare paths canonically (macOS `/private` symlinks, Windows 8.3 temp
  names) and patch `iconflow.build.build` through the module object.
- The homepage hero's decorative rail looked like a slider and did nothing; it
  is now a labelled range input that previews the mark at native sizes. The
  floating archive marks no longer occlude the stage labels.

### Security

- SVG input now rejects DTD/entity declarations, malformed or non-SVG XML,
  documents over 4 MiB, more than 50,000 elements, or nesting over 128 levels.
- Build output rejects existing symlinks, junctions, and reparse points before
  generated files are written.
- Windows shortcut scripts now use securely created unique temporary files.

## 0.4.0 - 2026-07-21

- Introduced the brief-to-concept-to-review workflow, multi-target icon engine,
  six-axis quality gate, Review Lab receipts, and evolving casebook.

`0.4.0` was the package version while the work above accumulated; nothing was
tagged or published under it. The package now carries `0.5.0` as the first
public release candidate (see `docs/MILESTONE_v0.5.md`); the *Unreleased*
section folds into `0.5.0` when the owner tags it.
