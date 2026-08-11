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

IconFlow is licensed under Apache-2.0. Unless you explicitly and conspicuously
state otherwise before submission, a contribution intentionally submitted for
inclusion is offered under the same Apache-2.0 terms, consistent with Section 5
of the license. You retain copyright in your contribution. Confirm that you
have the right to submit it and identify any third-party code or assets and
their licenses in the PR.

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
