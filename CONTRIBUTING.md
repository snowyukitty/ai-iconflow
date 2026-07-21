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
python -m pip install -e .
python -m iconflow setup     # first time only: fetch Playwright Chromium
python -m iconflow doctor    # verify the environment
```

Run the checks that cover what you touched:

```bash
python -m unittest discover -s tests
python -m iconflow case lint          # casebook integrity
python -m iconflow case stats         # health report / evolution target
```

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
