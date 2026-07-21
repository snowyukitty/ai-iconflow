# Evolution — how this design system improves itself

IconFlow is built to get **better with every icon it ships**, not just to ship
icons. The mechanism is a closed loop with three moving parts:

```
        ┌─────────────────────────────────────────────────────┐
        │                                                     │
   design & ship  ──►  RECORD (casebook/)  ──►  MEASURE       │
   (playbook +         one structured          (iconflow      │
    learnings)         case per icon           case stats)    │
        ▲                                          │          │
        │                                          ▼          │
        └──────────  DISTILL (docs/LEARNINGS.md ──────────────┘
                     and, when load-bearing, the playbook)
```

The docs are the system's *genes*; the casebook is its *experience*; `stats`
is its *sense of pain*. The agent-designer runs all three — no human in the
loop is required, but a human can audit every step because everything is
plain markdown in git.

---

## 1. RECORD — after every shipped icon (mandatory)

Right after the gated `iconflow ship` succeeds, record the case:

```bash
python -m iconflow case new --slug <project-slug> \
  --project "..." --targets web,tray --essence <one-word> \
  --style <family> --device "<signature device>" \
  --device-family <normalized-family> --device-detail "<specific execution>" \
  --concept-lens <winning-lens> --status shipped --cliche "<avoided>" \
  --first  "legibility=3 distinctiveness=4 balance=4 color=4 scalability=3 craft=4" \
  --final  "legibility=4 distinctiveness=5 balance=4 color=4 scalability=4 craft=4" \
  --iterations 3 \
  --lesson "<one reusable rule you learned>"
```

- `--first` = your rubric scores on the **first** review pass (honest — these
  measure how good the *playbook* made your first draft, which is the whole
  point). `--final` = the shipped scores.
- Then open the created file and fill **Summary** and **What failed first**
  with specifics (which axis, at which size, which shape change fixed it).
- Run `iconflow case lint`. New cases should be error-free; use `--strict` when
  a repository has finished migrating legacy files to the normalized taxonomy.
- A lesson must be a *rule the next designer can apply*, not a diary entry.
  Good: "two opaque foreground elements fuse into mud below 32px — carry the
  second idea in negative space." Bad: "the icon was blurry at first."
- **Also record reference exemplars, not only fresh sessions.** The loop learns
  only from what the casebook holds; a casebook of repair-driven cases teaches
  the system to *pass its gates*, not to be excellent. Periodically add the best
  shipped marks (owner favourites) as reference cases — honestly-labelled scores
  with the exemplar provenance noted in the Summary — so `stats`, the rubric bar,
  and `CONCEPTING.md`'s gallery measure against real quality (see L23).

## 2. MEASURE — read the health report

```bash
python -m iconflow case stats
python -m iconflow case atlas --out case-atlas.html
```

`stats` is the compact machine/action report. The self-contained atlas is the
human pattern-recognition surface: it places first→final score movement,
taxonomy distributions, status, and undistilled lessons in one view. Inspect
both before changing the system's genes.

Act on what it flags:

| Signal | Meaning | Action |
|---|---|---|
| **EVOLUTION TARGET** (weakest first-pass axis) | The playbook fails to prevent that class of first-draft mistake | Strengthen the corresponding doc section: legibility/scalability → PLAYBOOK §2/§5; distinctiveness → CONCEPTING; color → PLAYBOOK §4; balance → PLAYBOOK §2; craft → SVG_TECHNIQUES |
| **mean iterations > 3** | First drafts are chronically weak | Distill harder, more testable rules; check that LEARNINGS.md is actually being read at step 0 |
| **HOUSE-CLICHE WARNING** | One signature device dominates the casebook — the system is converging on its own cliché | On the next brief, deliberately pick a different device; consider adding the over-used device to CONCEPTING's cliché table *for this toolkit* |
| **DISTILL NOW** (≥3 undistilled lessons) | Experience is piling up without becoming genes | Run the distillation below |

Sample counts are part of every axis mean. Do not interpret a one-case average
as strongly as a recurring pattern, and do not hide tied weakest axes by
reporting only the first one.

## 3. DISTILL — promote lessons into the docs

When `stats` says DISTILL NOW (or a lesson clearly repeats across cases):

1. Read the undistilled lessons it lists. Group duplicates — a lesson seen in
   ≥2 cases is proven; a one-off needs judgment.
2. Promote each proven lesson to `docs/LEARNINGS.md` as a numbered rule:
   statement + why + evidence links to its case file(s).
3. If a rule is **load-bearing** (it would have changed the outcome of most
   cases), also fold it into the authoritative doc: an anti-pattern goes into
   `DESIGN_PLAYBOOK.md` §6, a cliché into `CONCEPTING.md`'s table, a
   technique into `SVG_TECHNIQUES.md`. Keep LEARNINGS.md as the index either way.
4. Flip the lesson checkboxes in the case files to `- [x]`.
5. If a rule is *mechanically checkable* (a threshold, a geometry property),
   consider encoding it as a new warning in `iconflow/qa.py` with a test —
   the strongest form of distillation, because `check` then enforces it
   automatically forever.
6. If a lesson concerns a transformed target (maskable padding, Electron
   corners, tray templates), encode one canonical transform and make build,
   Review Lab, and QA consume it. A rule is not truly mechanized if the preview
   audits different bytes from those that ship.

### Rules for editing the genes (docs)

- **Never weaken a gate** (the ≥4/5 rubric floor, the distinctiveness gate,
  the mandatory review step). Evolution adds constraints and sharpens
  guidance; it does not relax quality bars.
- Every added rule must be **testable by a future reader** ("strokes < 2.3%
  of the viewBox vanish at 16px"), not vibes ("make it cleaner").
- Prefer editing the *one* doc section that owns the topic over scattering
  the same advice in three places.
- Keep diffs reviewable: one distillation = one commit
  (`evolve: distill <n> lessons into <docs>`), so `git log docs/` is the
  system's evolution history.
- If a rule later proves wrong, delete it and record *that* as a lesson —
  the casebook is allowed to overturn the docs.

## 4. Where things live

| Artifact | Role |
|---|---|
| `casebook/*.md` | raw experience — one file per shipped icon |
| `docs/LEARNINGS.md` | distilled, numbered rules with evidence links |
| `docs/DESIGN_PLAYBOOK.md`, `CONCEPTING.md`, `SVG_TECHNIQUES.md` | the authoritative genes; receive load-bearing rules |
| `iconflow/qa.py` | mechanized rules — the highest form a lesson can reach |
| `iconflow case stats` | the feedback signal that drives all of the above |
| `iconflow case atlas` | the visual pattern report for score movement, taxonomy, and lessons |
