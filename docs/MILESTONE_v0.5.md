# Milestone v0.5 — Adoption Loop: Install → Prove → PR

Decided 2026-08-21 from two independent plans (Codex `gpt-5.6-sol` and Grok
`grok-4.6`, sealed read-only ATD delegations over the README, CHANGELOG,
CONTRIBUTING, launch docs, AGENTS.md, the skill, `pyproject.toml`, and
`iconflow/cli.py`), synthesized by the maintainer's agent. Both plans ranked
the same thing first and rejected the same things; the differences were the
version number (v0.5.0 rather than a stale v0.4.0) and how far to take the
machine contract (JSON + exit codes + a signable packet, not an MCP server).

## The problem this milestone solves

The product already has its differentiator — brief → diverge → exact 16px
proof → source-bound receipt → fail-closed `ship` → casebook — and a strong
site. What it lacks is a **front door**: no PyPI package, no tag or release,
a README proof that needs a git clone and `brand/` files the wheel does not
carry, an agent skill that assumes a local `AI_Projects` checkout, and a CLI
whose results must be read as prose. Adoption is blocked by reach and first
success, not by missing icon formats.

## Scope (7 items)

1. **Owner gates first (human-only).** Enable GitHub private vulnerability
   reporting; set the repository Homepage and social preview
   (`docs/assets/social-preview.png`); confirm the `ai-iconflow` name on PyPI
   and create a Trusted Publisher. If the name is taken, choose the public
   name before any doc rewrite.
2. **One public release, v0.5.0.** Fold `CHANGELOG.md` *Unreleased* into
   0.5.0, bump `pyproject.toml` and the skill metadata, run the existing
   non-publishing release-candidate workflow (checksums, clean-wheel `doctor`,
   brand ship), then tag, GitHub Release, and PyPI via Trusted Publishing.
3. **`iconflow demo`** — a wheel-native, one-command proof that materializes
   the packaged, already-reviewed brand family and runs doctor → check →
   review → ship against the bundled receipt (`docs/AGENT_CONTRACT.md`).
4. **Agent Contract v1** — `--json` envelopes for `doctor`, `check`,
   `review`, `ship`, `demo`; the 0/1/2 exit-code matrix; optional Review
   Packet v1 fields; golden tests. No MCP server in this milestone.
5. **PR Proof GitHub Action** — on PRs touching `*.svg`, `iconflow.toml`, or
   receipts: install the pinned wheel, cache Chromium, run `check --json` and
   `review --json`, upload the review sheet, fail on QA warnings or a stale
   receipt, never score taste, never need a write token.
6. **Contributor funnel that cannot skip the gate** — case PR template
   (semantic SVG, clean `check`, receipt with all six axes ≥ 4, cliché
   avoided, signature device, one reusable lesson, `case lint` clean), a
   minimal community-case fixture, CONTRIBUTING "first 30 minutes" (pipx/uv
   tool → demo → Action), 5–8 bounded good-first-issue drafts for the owner
   to file.
7. **Adoption-first docs and CTAs** — after PyPI exists: README and
   `/getting-started/` lead with `uv tool install ai-iconflow` / `pipx`,
   then `iconflow setup`, `iconflow doctor`, `iconflow demo`; clone/editable
   becomes the contributor path; the skill and AGENTS.md resolve `iconflow`
   on PATH with checkout as contributor mode. Until then the copy keeps
   saying "not on PyPI yet".

## Explicit non-goals

Mobile app icon sets, Apple Icon Composer, MSIX target, Figma auto-rewriter,
light/dark dual families, stateful tray families, MCP server, hosted
renderer/uploads, product telemetry, leaderboards, weekly challenges, formal
governance, SUPPORT.md, any weakening of the ≥4/5 / distinctiveness /
stale-receipt rules, more gallery/archive/remix expansion.

## Sequencing

- **Phase 0 (owner):** item 1.
- **Phase 1 (agents, reviewed by owner):** freeze `docs/AGENT_CONTRACT.md`;
  implement items 3–4 with golden tests; item 5 consuming only the JSON;
  item 6 templates and issue drafts.
- **Phase 2 (owner + agents):** RC workflow on the release commit; clean-wheel
  `doctor`, `demo`, brand ship on Windows/POSIX; tag v0.5.0; publish; run the
  documented clean-install smoke on a machine that is not the checkout.
- **Phase 3 (agents):** item 7 CTA swap, only after PyPI files exist.
- **Phase 4 (observe, 60 days):** first external issue, first receipt-bearing
  PR, first foreign-repo agent completing init → check → review → ship from
  PATH, Action usage outside this repo. The next milestone is chosen from
  that evidence, not from gallery size.

## Acceptance (fail-closed)

1. Fresh environment, no repo: install from PyPI, `iconflow setup`,
   `iconflow doctor` PASS.
2. `iconflow demo --out d` produces a review sheet, a receipt, and the
   built family; editing `d/master.svg` then re-running `ship` is refused
   with `receipt-stale-source`.
3. `pip install ai-iconflow` never needs `brand/` from GitHub.
4. The skill never tells an agent to `cd` into a hardcoded toolkit path.
5. Fixture PRs prove clean pass, QA-warning fail, and stale-packet fail in
   the Action.
6. `python -m build && python scripts/verify_distribution.py dist/*` stays
   fail-closed; demo resources ship via `importlib.resources`.
7. `scripts/build_archive.py --verify-only`, the website tests, and the full
   suite pass on the release commit.
