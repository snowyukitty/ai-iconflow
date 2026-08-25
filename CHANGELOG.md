# Changelog

All notable changes to IconFlow are documented here. The project uses Semantic
Versioning for published releases; repository-only development before the
first published release remains under `Unreleased`.

## Unreleased

### Added

- **A reference page the tool generates about itself**, at
  `/reference/icon-sizes/`. Every icon file and frame size each target needs —
  web favicon, PWA manifest and maskable safe zone, Windows tiles, Tauri,
  Electron, macOS tray template — plus the paste-ready `<head>` block, the
  generated manifest, and nine FAQ answers.

  It exists because the site ranked for nothing. Twenty-four indexed URLs, all
  of them brand pages that convert someone who already knows what IconFlow is,
  and none of them containing the words a person in trouble actually types:
  *favicon.ico sizes*, *maskable icon safe zone*, *macOS menu bar icon black
  square*. That traffic went to tools whose size tables are human
  transcriptions, drifting quietly whenever a platform moves.

  `scripts/build_reference.py` reads `preview_assets`, `ICO_FRAME_ORDER`,
  `ICNS_FRAME_SIZES`, `TAURI_PNG_SPECS` and `assemble.maskable_asset` — the
  same code a real `ship` runs — so the published table cannot disagree with
  the tool. A build change that has not been re-rendered fails the website
  tests, and an output file the page does not describe fails the generator
  outright. That is the durable difference: every competing table on the web is
  a transcription nobody can date, and this one breaks CI before it can be
  wrong.

- **An animated README demo**, `docs/assets/demo.gif`, rendered by
  `scripts/render_readme_demo.py` from a checked-in transcript of a real run.
  `ship` builds 23 files; one control point moves in the master SVG; the same
  command refuses with a stale receipt. Ten seconds, no prose, and it shows the
  one thing no other icon tool does. Rendered through the same pinned Chromium
  as every other generated asset, and excluded from the wheel — half a megabyte
  of GIF has no business in a package that never displays it.

- **Structured data that describes the software.** `SoftwareApplication` on the
  homepage with category, platforms, requirements, install URL, feature list
  and `isAccessibleForFree`; `TechArticle` + `FAQPage` + `BreadcrumbList` on
  the reference page; `CollectionPage` + `ItemList` + `BreadcrumbList` on the
  four collection pages, three of which published none at all. Still no
  `offers` and no `aggregateRating`: nobody has rated or sold this, and markup
  for a rating that does not exist is the one kind of claim this site refuses
  to make everywhere else. The tests enforce both absences, and now also
  enforce a distinct, non-thin title and description on every indexed page.

- `docs/SEO.md` and `docs/PROMO_VIDEO.md`: the discoverability diagnosis with
  the queue of pages worth generating next, and the launch-film brief —
  including why the film uses real screen capture and HyperFrames rather than a
  video model, when the product's whole promise is that what you see is what
  shipped.

### Changed
- **A self-audit that asks the world instead of remembering it.**
  `scripts/state.py` checks what is actually true — are the generated site
  artifacts current, does PyPI carry this version with resolvable attestations,
  does the repository look the way the docs say, and **does the deployed site
  still serve what the repository holds**. That last one is a failure nothing
  else here could see: a perfect commit and a two-day-old Cloudflare deploy are
  indistinguishable from inside a checkout, and the first run found exactly
  that.

  It writes `docs/STATE.md` with `--write`, speaks the `--json` envelope from
  `docs/AGENT_CONTRACT.md`, and follows one rule throughout: a probe that could
  not run reports UNKNOWN, never PASS. A tick meaning "I could not check" is
  worse than no tick. An open owner gate is reported and never fails the run,
  because a gate is a decision waiting on a person rather than a defect.

- **`LAUNCH_READINESS.md` rewritten to hold only what cannot drift.** It had
  become the exact thing IconFlow exists to refuse. On the morning of
  2026-08-25 it still said the `iconflow` name "returns 404, so both are still
  free" — three days after 0.5.0 was published from this repository — and in an
  adjacent bullet announced the repository was public while quoting `gh repo
  view` reporting it `PRIVATE`. It listed twelve topics when there were twenty.

  Nobody lied; a person ticked a box and the world moved. So the file is now
  the *record* — a dated history table, the licensing reasoning, the market
  position, the known limits — and every live-state claim defers to
  `STATE.md`. `tests/test_state.py` fails if a status checkbox reappears there,
  because a checkbox is a condition asserted as of whenever someone last
  looked, and nothing re-checks it.

- **The reference page stopped being rewritten at the CDN.** Three of the
  filenames it publishes — `icons/128x128@2x.png`, `tray/tray@16.png`,
  `tray/trayTemplate@2x.png` — read as email addresses to Cloudflare's Email
  Address Obfuscation, which is on by default. It replaced all three at the
  edge with `[email protected]` links and injected a decoder script. The
  repository was correct and the served page was wrong, so a developer copying
  a filename off the one page built never to lie got a file that does not
  exist. Nothing in the repository could see it; the self-audit found it on its
  first run against a fresh deploy.

  `&#64;` parses to the same character for a reader, a copy-paste and a
  crawler, while matching no email pattern in the raw HTML. The generator now
  emits it, and refuses to write a page carrying a literal `@` outside the
  JSON-LD block — where `@context` and `@type` must stay literal to parse.

- **`docs/STATE.md` is excluded from the wheel.** It is a report about *this
  repository* at the moment it was generated — open gates, whether the deployed
  site is current, whether CI is green. Frozen into a package it becomes a
  stale answer to a question the reader never asked, listed by `iconflow docs`
  beside the methodology, which is the exact drift the report exists to end.

- **A lint gate pinned to the oldest supported Python.** A backslash inside an
  f-string expression is legal from 3.12 and a `SyntaxError` on 3.10. One
  reached `main` in this very changelog's previous entry: green on a 3.12
  machine, red minutes later on a single leg of the CI matrix. `ruff` reports
  syntax errors against `target-version` regardless of which rules are
  selected, so a deliberately narrow rule set — undefined names, unreachable
  branches, broken comparisons, dead imports — buys that whole class of failure
  for a job that finishes in under a minute. Restyling 250 existing files would
  have buried the signal; the two dead imports it did find are gone.


- `robots.txt` now carries an explicit `Allow: /reference/` inside the named
  training-crawler block. The line is deliberate, not a loosening: the CC BY-SA
  methodology and the CC BY-NC-ND artwork stay out of bulk collection, while
  tables generated from Apache-2.0 code that describe other people's platforms
  stay open to the answer engines that will be asked these questions. `llms.txt`
  says the same thing in the terms it publishes.

- The repository's GitHub topics went from 12 to the maximum 20, and the
  reference route is linked from the homepage, from every footer including the
  four translated language trees, and from the sitemap.

## 0.5.0 - 2026-08-22

First public release. IconFlow had been developed in a private repository since
2026-06-23; this is the version that made it installable.


### Added

- **The distribution is now `iconflow`, renamed from `ai-iconflow` before any
  upload.** `pip install iconflow` gives you an `iconflow` command — the
  property the entire adoption story rests on, since an agent told to use
  IconFlow types the obvious thing first. The CLI, the product, the agent skill,
  the Claude Code plugin, and the slash commands were all already called
  `iconflow`; the distribution was the only piece out of step, and the `ai-`
  prefix additionally misdescribed a toolkit that deliberately has no image
  model and no API key. The README's claim that the package "remains named
  `ai-iconflow` for compatibility" was compatibility with nothing: nothing had
  ever been published.

  123 references across 36 files, done before the name could become permanent —
  PyPI has no rename. The domain `ai-iconflow.com`, the GitHub repository
  `snowyukitty/ai-iconflow`, and the Cloudflare Pages project keep their names;
  none of them has to match the distribution. The translation catalogs needed no
  work, because the one user-visible occurrence sits inside a `<code>` element
  that `build_i18n.py` carries as a placeholder — 708 strings still verify
  across four languages.

- **Per-file attribution across the whole source tree, and a CLA.** The engine
  stays `Apache-2.0` — a modified fork inside someone else's closed product is
  permitted, and that permissiveness is what makes the tool safe to adopt. What
  a redistributor still owes is attribution, so every one of the 41 Python files
  now carries `SPDX-License-Identifier: Apache-2.0` and a copyright line.
  `NOTICE` binds a distribution; a per-file header travels with an individual
  file, which is what makes a stripped copy identifiable later. Apache-2.0 §4
  obliges a redistributor to keep those notices, to say that files changed, and
  to reproduce `NOTICE` — and a fork produced by pointing an agent at the
  repository typically drops all of it. `docs/PROVENANCE.md` §3b writes down
  exactly what is required, which distinctive gate codes survive modification,
  and the asymmetry that matters: the engine is Apache, but the playbook is
  CC BY-SA and the proof corpus is CC BY-NC-ND, so copying the code gets the
  mechanism without the method.
- [`CLA.md`](CLA.md) — contributors keep their copyright (it is a license, not
  an assignment) and grant the right to **relicense**, so one outside pull
  request cannot freeze IconFlow's licensing permanently. §6 states the reason
  openly rather than leaving it implied. Wired into `CONTRIBUTING.md`, both PR
  templates, and `LICENSES.md` §8; `tests/test_licensing.py` fails if a source
  file loses its header or a referrer loses the link.

- **A three-tier licence split, built so that the icons users make stay theirs.**
  The repository is no longer under one licence, and
  [`LICENSES.md`](LICENSES.md) is the map: the engine, scripts, and site code
  stay `Apache-2.0`; the technique scaffolds in `templates/` become `CC0-1.0`;
  the written methodology in `docs/`, `casebook/`, and `skills/` becomes
  `CC-BY-SA-4.0`; IconFlow's product mark and the imagery that ships inside the
  package — `brand/`, `demo/`, `docs/assets/` — becomes `CC-BY-4.0` on top of
  the existing trademark policy; and the published corpus that does *not* ship —
  `showcase/`, `gallery/`, `examples/`, and the 137 Living Archive studies —
  becomes `CC-BY-NC-ND-4.0`. Each tier carries its own `LICENSE`, 241 files
  carry an SPDX header, the full texts are vendored in `licenses/`, and the
  wheel declares `Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND CC-BY-4.0` —
  every one a free licence, so the distribution stays packageable. Nothing
  noncommercial is shipped; the identity is protected by trademark, which is
  the right instrument for it.
- **The scaffolds are CC0 for one specific reason, and it is load-bearing.**
  Under `Apache-2.0` an icon evolved from `iconflow new flat-geometric` would
  technically be a derivative work owing attribution and a licence copy when
  shipped. `CC0-1.0` removes that chain: **no attribution, no share-alike, no
  commercial restriction reaches through the tool into anything a user
  designs**, and applying the published method creates no obligation either
  because copyright covers the playbook's wording, not its design rules.
  `LICENSES.md` §1, `NOTICE`, the README, the agent skill, `/llms.txt`, and the
  new `iconflow license` (with `--json`) all say so, and
  `tests/test_licensing.py` fails the build if a restrictive tier ever leaks
  into a user-facing resource.
- `iconflow new` now **strips the licence header** from the scaffold it copies.
  Left in, it rode `master.svg` all the way into the `favicon.svg` a user serves
  in production — an IconFlow URL embedded in someone's shipped asset, which is
  precisely the attribution §1 promises never to require. The CC0 grant is
  printed to the terminal instead, where it is information for the person rather
  than for their visitors' browsers.
- `iconflow demo` writes a `LICENSE-NOTICE.md` beside the family it
  materializes, because that one command deliberately copies **IconFlow's own
  product mark** into a directory the user chose. It says what the directory
  holds, that it is not a starting point, and which commands are.
  `iconflow docs --out` likewise reports that its export is CC BY-SA reference
  material to keep out of version control.
- The Remix Lab bends IconFlow's actual product mark, so its output carries the
  mark's own `CC-BY-4.0` — derivatives and commercial use allowed, attribution
  required — stated on the site in all five languages, in `brand/LICENSE`, and
  in `LICENSES.md` §5. A no-derivatives term on something a visitor was invited
  to remix would be dishonest; an unconditional CC0 grant on output derived from
  the official logo would be too broad, and the lab now points anyone who wants
  a start with no conditions at all to the CC0 scaffolds behind `iconflow new`.
  `examples/community-case/` *is* carved out to CC0, because that fixture exists
  to be copied and a no-derivatives term on a template is a contradiction.
- **Two adversarial reviews (Codex `gpt-5.6-sol`, Grok `grok-4.6`) attacked the
  split before publication and found real holes, all closed here.** The
  scaffold's own licence header was riding `master.svg` into the `favicon.svg`
  users serve; `LICENSES.md` §1 claimed *every* file the toolkit writes is CC0
  when `docs --out` and `skill install` write CC BY-SA reference material;
  `CONTRIBUTING.md` still declared all contributions Apache-2.0, which would
  have re-created the very problem CC0 on the scaffolds exists to avoid; the
  `demo` notice could be suppressed by a pre-planted symlink; and `robots.txt`
  was blocking the on-demand fetchers that agents use on a person's behalf,
  which costs discovery and does nothing about training. §1 now also carries an
  explicit catch-all: any IconFlow boilerplate embodied in a generated artifact
  is supplied under CC0, and the section states plainly what no licence can
  promise — that an icon is copyrightable, registrable, or clear of other marks.
  `tests/test_licensing.py` runs a real `build` and fails if any produced file
  contains an IconFlow notice, URL, or SPDX tag.

- **Provenance that makes copying provable rather than preventable.** All 137
  published archive studies carry an RDF `<metadata>` block naming the work,
  its author, its licence, and its canonical URL; `scripts/build_archive.py`
  writes it and `--verify-only` fails without it.
  [`docs/PROVENANCE.md`](docs/PROVENANCE.md) records the evidence trail, a dated
  registry of the coined terminology that fingerprints this corpus, how to check
  a suspected copy — and, plainly, what none of this can do.
- `website/llms.txt` states terms for AI systems and doubles as an agent-facing
  index; `robots.txt` asks named training crawlers to stay out of `/archive/`,
  `/gallery/`, and `/how-icons-are-made/` in every language while leaving the
  front door and `/getting-started/` open to everyone, because being found by
  agents is the point. Both are voluntary, and both say so.
- `NOTICE` became substantive. Apache-2.0 §4(d) obliges every redistributor to
  reproduce it, so it is the one attribution a fork cannot quietly drop: it now
  carries the maintainer attribution, the per-directory licence map, the
  trademark reservation, and the user-output carve-out.
- `CONTRIBUTING.md` gains the tier table, the rule that new files carry an SPDX
  header, and a Developer Certificate of Origin sign-off requirement
  (`git commit -s`) so the copyright chain stays clean enough to enforce.

- **A one-command front door for other people's agents.** IconFlow ships as a
  Claude Code plugin: `/plugin marketplace add snowyukitty/ai-iconflow` then
  `/plugin install iconflow@iconflow` installs the design procedure plus the
  `/iconflow:icon` and `/iconflow:setup` slash commands. The catalog is
  `.claude-plugin/marketplace.json` and the plugin itself is the `skills/`
  directory (`skills/.claude-plugin/plugin.json`), so the published plugin is
  five files rather than the whole repository, and its skill *is* the canonical
  `skills/iconflow/SKILL.md` — there is no second copy to drift.
- `iconflow skill install|print|path`: deploys the Agent Skill into
  `~/.claude/skills/`, `~/.agents/skills/`, and `~/.copilot/skills/` (and clears
  the superseded `~/.codex/skills/iconflow/` duplicate) **straight from the
  installed package**, so a Codex or Copilot session no longer needs a clone to
  get the procedure. `--project` writes into the current repository and `--dir`
  names a location. `scripts/setup.ps1` and `scripts/setup.sh` now call this one
  command instead of each maintaining its own copy of the discovery-root list —
  the place those two scripts were free to drift apart.
- `iconflow docs [NAME] [--out DIR] [--path] [--json]`: lists, prints, or
  exports the packaged reference documents the procedure cites. An agent that
  installed a wheel used to need
  `python -c "from importlib.resources import files; ..."` and a walk through
  `site-packages` to read `DESIGN_PLAYBOOK.md`; it now runs
  `iconflow docs DESIGN_PLAYBOOK`. `doctor` verifies the packaged skill along
  with the other resources, and the wheel carries `SKILL.md` and its Codex
  metadata under `iconflow/resources/skill/`.
- Two independent reviews of the front door (Codex `gpt-5.6-sol` and Grok
  `grok-4.6`, sealed read-only ATD delegations) found the same defects, all
  fixed here: the source-checkout branch of resource resolution now demands
  this project's own `pyproject.toml` beside the package before it is trusted,
  so an unrelated distribution's top-level `site-packages/docs` can no longer
  shadow the packaged playbook; `importlib.resources.files(None)` silently
  resolving to IconFlow's own package turned an unknown resource set into a
  wrong answer instead of an error; `skill install` reads every packaged file
  before writing any destination, so a broken install fails closed rather than
  leaving an empty skill directory that shadows a working one; the superseded
  `~/.codex/skills/iconflow/` deployment is retired by deleting only the files
  IconFlow wrote and then removing the directory only if nothing else is left,
  instead of an unconditional `rmtree`; every deployed write refuses to follow
  a symlink out of its target; and `--path` reports honestly when an install
  keeps resources inside a zip rather than printing a path nothing can open.
- The skill was rewritten for an agent working in **someone else's**
  repository. It no longer resolves a two-mode `<AI_PROJECTS>/iconflow`
  placeholder against the maintainer's private workspace layout: the runner is
  `iconflow` on PATH, reference documents come from `iconflow docs <NAME>`,
  drafts go to the consuming project's `work/<slug>/`, and cases land in its own
  `./casebook`. Both reviews caught the same two regressions in that rewrite
  and both are repaired: the PyPI warning now leads with a hard stop *before*
  any index install command, because an agent runs the first command it reads;
  and the guardrails the old procedure carried — one bold idea on the 1024 grid
  inside the safe area, reporting the brief's essence, and the rule that a
  recolored preset is not a finished icon — are back. The managed-browser
  fallback used to strand an agent by describing the approved-config route and
  then telling it to `ship --review` anyway; it now names both routes exactly.
  `tests/test_agentkit.py` fails the build if a workspace path, a `cd` into the
  toolkit, a dropped quality gate, an index install command that precedes its
  warning, or a broken exemplar image link comes back.

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
  names, hashes, and score strings stay exactly as they ship, and the build
  now **fails closed when a translation drops one**: if the English says
  `Chromium`, `master.svg`, `PyPI` or `16px`, every language has to say it too.
  Terminology, honesty rules, and per-language style are pinned in
  `website/i18n/GLOSSARY.md`, whose terminology table is parsed by
  `--status`, which reports per-language adherence so a term splitting into two
  renderings surfaces as a number instead of waiting for a reader to notice.
  A controlled four-model benchmark (111 curated zh-Hant strings, one prompt,
  candidates shuffled per string, mapping withheld until the picks were
  recorded) settled the drafting comparison and, more usefully, exposed
  consistency defects in the shipped catalogs that string-by-string review had
  missed; `docs/I18N_PLAN.md` records the method, the numbers and the caveats.

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
  `iconflow.pages.dev` retained as a permanent compatibility redirect.
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
  `iconflow.pages.dev` redirect through the shell project's `_redirects`;
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
