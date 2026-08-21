<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Contributing to IconFlow

Thanks for your interest. IconFlow is a **self-evolving icon design system**: a
mechanical build engine plus a set of docs (the "genes") that get sharper every
time an icon ships. Most contributions fall into one of three layers — read
[`docs/EVOLUTION.md`](docs/EVOLUTION.md) for the full loop before changing the
genes.

```
docs (the brain)  →  casebook (experience)  →  iconflow case stats (the signal)
        ▲                                                  │
        └──────────────── distill lessons ────────────────┘
```

## First 30 minutes

| You want to | Install | Then run |
|---|---|---|
| use IconFlow as a tool (agent or human) | `uv tool install iconflow` | `iconflow setup`, `iconflow doctor`, `iconflow demo --out work/demo` |
| same, without uv | `pipx install iconflow` | same (`pipx ensurepath` first on Windows if `iconflow` is not found) |
| pin it inside one project | `python -m venv .venv && .venv/bin/pip install iconflow` | `.venv/bin/iconflow setup` ... |
| contribute / run the tests | `git clone ... && cd iconflow && python -m pip install -e ".[dev]"` (or `scripts/setup.ps1` / `scripts/setup.sh`, which also create `.venv` and install the agent skill) | `python -m iconflow setup`, `python -m iconflow doctor`, `python -m iconflow demo --out work/demo` |

`setup` downloads Playwright Chromium once (the only network step); `doctor`
proves the environment; `demo` materializes the packaged, already-reviewed brand
family into a directory and runs `doctor -> check -> review -> ship` against its
bundled receipt, so your first success is a real gated ship, not a render. From
a checkout today the same proof is
`python -m iconflow ship --config brand/iconflow.toml --review brand/master-review.json --out work/quick-start/icon-out`.

Then read [`AGENTS.md`](AGENTS.md) (the procedure) and
[`docs/AGENT_CONTRACT.md`](docs/AGENT_CONTRACT.md) (`--json`, exit codes).
Every document either cites is served by the CLI — `iconflow docs` lists them,
`iconflow docs DESIGN_PLAYBOOK` prints one — so a wheel install never needs the
checkout to read them. Working through an agent? Claude Code installs the whole
procedure with `/plugin marketplace add snowyukitty/ai-iconflow` then
`/plugin install iconflow@iconflow`; other Agent Skills clients get it from
`iconflow skill install`.
Icon contributions go through **the case lane** below; engine and doc changes
through the sections after it.

## Licensing and sign-off

This repository is **not** under a single license. Before you edit, check which
tier your files sit in — [`LICENSES.md`](LICENSES.md) is the map, and each
tiered directory carries its own `LICENSE`:

| You are changing | License it lands under |
|---|---|
| `iconflow/`, `scripts/`, `tests/` | `Apache-2.0` |
| `templates/` technique scaffolds | `CC0-1.0` (public domain) |
| `docs/`, `casebook/`, `skills/` | `CC-BY-SA-4.0` |
| `brand/`, `demo/`, `docs/assets/` (shipped in the package) | `CC-BY-4.0` |
| `gallery/`, `showcase/`, `examples/`, `website/assets/` | `CC-BY-NC-ND-4.0` |

New Markdown under a `CC-BY-SA-4.0` directory and new SVG under `templates/`
must carry the matching `SPDX-License-Identifier` header; copy one from a
neighbouring file. `tests/test_licensing.py` fails the build if it is missing.

**Never** let a restrictive tier leak into something a user's project receives.
Files IconFlow copies or generates into a consuming project are CC0 by design,
because an icon someone built with this tool must carry no obligations at all.
That guarantee is [`LICENSES.md` §1](LICENSES.md) and it is load-bearing.

Two things are required, and they do different jobs:

1. **Sign off every commit** — `git commit -s` — certifying the
   [Developer Certificate of Origin](https://developercertificate.org/). This
   records the origin of each commit.
2. **Sign [`CLA.md`](CLA.md) once**, by putting this line in your pull request:

   ```
   I have read CLA.md and I agree to it.  Signed: <your full name>, <YYYY-MM-DD>
   ```

   You keep the copyright in what you write — the CLA is a license, not an
   assignment, and you may reuse your own work anywhere. What it adds is the
   right to relicense, so one outside pull request does not freeze IconFlow's
   licensing permanently. `CLA.md` §6 explains the specific scenario that is
   for, openly.

Contributions written with AI assistance are welcome under exactly the same
terms: you are the one certifying you have the right to submit them, so do not
paste in material whose provenance you cannot personally vouch for.

## Development setup

Python 3.10+ is required. Rendering uses a headless Chromium via Playwright.

```bash
python -m pip install -e ".[dev]"
python -m iconflow setup     # first time only: fetch Playwright Chromium
python -m iconflow doctor    # verify the environment
```

Run the checks that cover what you touched:

```bash
python -m unittest discover -s tests
python -m iconflow case lint          # casebook integrity
python -m iconflow case stats         # health report / evolution target
```

Browser-boundary changes also require the opt-in integration tests:

```bash
ICONFLOW_BROWSER_TESTS=1 python -m unittest tests.test_browser_security -v
```

On PowerShell, set `$env:ICONFLOW_BROWSER_TESTS = "1"` first. Packaging changes
must build and inspect both distributions with `python -m build` and
`python scripts/verify_distribution.py dist/*`.

## The quality bar (for icons)

An icon is not "done" because it renders. It ships only when:

- `python -m iconflow check master.svg` is clean, **and**
- every axis of the six-axis rubric ([`docs/REVIEW_CHECKLIST.md`](docs/REVIEW_CHECKLIST.md))
  scores ≥ 4/5, **and**
- **distinctiveness is a hard gate**: the mark must BE a specific object whose
  silhouette names a thing — not a bare letter on a gradient tile (the *monogram
  trap*). See [`docs/CONCEPTING.md`](docs/CONCEPTING.md), "Distinctiveness =
  specificity", and run the name-the-thing test.

Never end an icon session without recording the case
(`python -m iconflow case new ...`) — an unrecorded icon teaches the system
nothing.

## The case lane (contributing an icon family)

A case is one reviewed icon family plus what it taught. Three things carry it,
and none can be skipped:

1. **The PR template** - open the PR with `?template=case.md`
   (`.github/PULL_REQUEST_TEMPLATE/case.md`). Every box is a gate: semantic
   `master.svg` (+ linked `tray.svg` when a tray target is selected), clean
   `iconflow check`, a Review Lab receipt with all six axes >= 4 bound to the
   exact source and contract, the cliché avoided, the signature device, one
   reusable *testable* lesson, the `iconflow case new` record with `case lint`
   clean, the clean-room provenance checklist, and the privacy checklist.
2. **The fixture** - copy [`examples/community-case/`](examples/community-case/)
   (`iconflow.toml`, `master.svg`, `master-review.json`). It is the smallest
   real, receipt-bound family; replace the mark, keep the shape.
3. **The PR Proof action** - `.github/workflows/icon-proof.yml` runs
   `check --json`, `review --json`, and the receipt binding on every PR that
   touches an SVG, `iconflow.toml`, or receipt, uploads the review sheet, and
   fails on a QA warning or a stale receipt ([`docs/PROOF_ACTION.md`](docs/PROOF_ACTION.md)).
   It never scores taste: a green action is necessary, not sufficient.

### What reviewers will and will not accept

Reviewers **will** accept a case that passes the mechanical gate, whose receipt
binds to the submitted bytes, whose 16px cell still names the thing, and whose
lesson a future reader can test. They will **not** accept, regardless of how the
128px render looks: any axis below 4/5 or a distinctiveness score argued up from
3; a receipt for a different source, target set, or transform; a traced,
adapted, or recognizable third-party mark; a bare letter or generic shape on a
gradient tile (the monogram trap); a lesson phrased as taste ("make it
cleaner"); or a case that carries private repository names, local paths, or
generated `work/` files. The bar does not move for a first contribution:
[`docs/EVOLUTION.md`](docs/EVOLUTION.md) §3, "Never weaken a gate" - evolution
adds constraints and sharpens guidance; it never relaxes the >= 4/5 floor, the
distinctiveness gate, or the mandatory review step.

## Changing the style catalog

- A new preset must add a new structural model, not a recolor, fill toggle, or
  stroke-weight variant. Update `iconflow/styles.py`, the packaged SVG,
  `docs/STYLE_CATALOG.md`, tests, and the generated gallery together.
- Draw clean-room geometry from an abstract written rule. Do not trace, adapt,
  or copy an upstream path, palette, sample, name, prose, or recognizable trade
  dress. Record official upstream URLs and current license signals only when a
  general design lesson materially informed the work.
- Run `iconflow check` on every preset, regenerate the gallery, and inspect its
  native 16px light/dark cells plus a complete `iconflow compare` bake-off.
- State the tray/monochrome strategy. A full app-card alpha shape is not a
  meaningful menu-bar silhouette merely because automatic conversion succeeds.

## Changing the engine

- Mechanically checkable rules belong in `iconflow/qa.py` with a test in
  `tests/test_qa.py`. This is the strongest form a lesson can reach — `check`
  then enforces it forever. Prefer **advisory** warnings over false positives:
  validate any new heuristic against real icons so it never flags good marks.
- Keep runtime rendering deterministic: network-isolated, JavaScript-disabled,
  animation-frozen. Do not add network or filesystem access to the render path.
- All project artifacts are in **English** (code, comments, docs, commits).

## Changing the docs (the genes)

The rules in [`docs/EVOLUTION.md`](docs/EVOLUTION.md) §3 govern this. In short:

- **Never weaken a gate.** Evolution adds constraints and sharpens guidance; it
  does not relax the ≥4/5 rubric floor, the distinctiveness gate, or the
  mandatory review step.
- Every added rule must be **testable by a future reader** ("strokes < 2.3% of
  the viewBox vanish at 16px"), not vibes ("make it cleaner").
- Prefer editing the *one* doc section that owns the topic over scattering the
  same advice in three places.
- If a rule later proves wrong, delete it and record *that* as a lesson — the
  casebook is allowed to overturn the docs.

## Commits & PRs

IconFlow is **not** licensed under Apache-2.0 as a whole, so inbound terms
follow the tier of the files you touch rather than one blanket license.

Unless you explicitly and conspicuously state otherwise before submission, a
contribution intentionally submitted for inclusion is offered under the license
that governs the directory it lands in — `Apache-2.0` for the engine (consistent
with Section 5 of that license), `CC0-1.0` for `templates/` and
`examples/community-case/`, `CC-BY-SA-4.0` for the documentation, and
`CC-BY-4.0` or `CC-BY-NC-ND-4.0` for artwork, per the table above and
[`LICENSES.md`](LICENSES.md).

A contribution to `templates/` is a **public-domain dedication** and cannot be
made under Apache-2.0: a scaffold carrying attribution obligations would pass
them to every icon a user builds from it. Say so in the PR.

Contributing your own icon as a case or example means licensing that artwork
under the receiving directory's terms. Your icon stays yours everywhere else —
this is a grant for the copy in this repository, not a transfer.

You retain copyright in your contribution. Confirm that you have the right to
submit it and identify any third-party code or assets and their licenses in the
PR.

Contribution does not grant rights to the IconFlow name, logo, or official
project identity; see [`TRADEMARKS.md`](TRADEMARKS.md). It also does not promise
acceptance, merge access, roadmap influence, or release authority. Maintainers
remain responsible for the official project's quality gates, direction, and
release decisions.

- Keep diffs reviewable. One distillation = one commit
  (`evolve: distill <n> lessons into <docs>`), so `git log docs/` reads as the
  system's evolution history.
- Include tests for any engine change and run the full suite before opening a PR.
- In the PR description, state what changed and why, and — for an icon — the
  cliché avoided, the signature device, and the final rubric scores, so quality
  is auditable.

## Privacy

The casebook records real design sessions. When a case involves a third party or
sensitive project, anonymize identifying details (names, handles, brand-specific
terms) while keeping the reusable design lesson intact.

For vulnerabilities, follow [`SECURITY.md`](SECURITY.md) and never put exploit
details or secrets in a public issue.
