<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The render plan — reviewed pixels are shipped pixels

IconFlow's gate rests on a person (or an agent) looking at pixels and scoring
them. Before 0.8 the receipt that recorded the scores was bound to the
*source* and the *settings*, not to the pixels: `review` rendered once, `ship`
rendered again, and nothing compared the two. A Chromium or Pillow upgrade
between review and ship could change every shipped file under an approval
that still read as valid. And `build` wrote files as it went, so a target
that failed late — an emote over its upload limit, an Android themed layer
that could not be derived — left half an icon set in the output directory.

0.8 computes the whole output once, as a **render plan**, and carries it from
review to ship.

## What a plan is

`iconflow.plan.compute_plan` takes exactly `build()`'s arguments and returns
every file the build would write — PNGs, `.ico`/`.icns` containers, the web
manifest and head snippet, Android resources, the tray module — in memory,
with the source snapshots and parameters that produced it. Each source is read
**once**; that snapshot is what is rendered, hashed, and (for an unannotated
favicon) copied, so an edit made mid-build cannot mix two versions. The plan
is immutable.

`build()` is now `compute_plan` followed by `write_plan`. Its signature,
defaults, return value and the bytes it writes are unchanged — a refactor
check compared 93 files across two configurations byte for byte.

## Two identities

| | covers | survives | used by |
|---|---|---|---|
| `digest` (content) | each PNG's decoded RGBA pixels and size; each ICO/ICNS frame's pixels, in slot order; every other file's bytes, text read with LF newlines | a lossless PNG re-encode, CRLF vs LF | `ship` (rendered): are these the reviewed pixels? |
| `artifact_digest` (bytes) | every file's exact SHA-256 and length | nothing | `ship --plan`: are these the reviewed bytes? |

The content digest is a *hybrid*: `tray/trayIcon.ts` embeds PNG bytes, so a
re-encode changes it. A receipt also carries the per-file identities, so a
mismatch names the files that changed, appeared, or disappeared.

## From review to ship

1. **`review`** computes the plan for what it shows. The Lab and the
   `--receipt-template` seed carry `plan` (both digests, every file's
   identities, the toolchain that rendered them). In the scheme the build
   uses, the Lab's target previews *are* the plan's files.
2. **`review --evidence DIR`** also saves the plan as `DIR/plan/` (`plan.json`
   plus `files/`), cuts `targets.png` from the plan's own files (favicon frames
   from `favicon.ico`, Electron's from `build/icon.icns`), and records the plan
   in `findings.json`.
3. **`score`** inherits the plan from the evidence. It never renders one: a
   renderer that changed between review and score must not attach old scores
   to new pixels. It refuses evidence whose saved plan was altered.
4. **`ship`** renders the plan again and compares it with the receipt's:

   | receipt | rendered plan | result |
   |---|---|---|
   | no `plan` (written before 0.8, or a `[review]` table) | — | ships; advisory `plan-unbound` |
   | `plan` | same content | ships; `outputs.plan.verified = true` (`bytes_verified` says whether the bytes match too) |
   | `plan` | any difference | **blocked**, `plan-drift` (exit 1), files listed; nothing written |
   | malformed `plan` | — | configuration error (exit 2) — never quietly treated as unbound |

   Drift is blocked **whatever the toolchain**. A changed toolchain explains a
   difference (`ship` prints which versions moved); it does not approve it.
5. **`ship --plan DIR/plan`** publishes the saved bytes without rendering the
   shipped files again. This is how a receipt made on one machine ships on
   another (CI on Linux from a review on Windows): the plan is imported as a
   hostile artifact — no links anywhere in it, no file the manifest does not
   name, bounded sizes, portable relative paths only, duplicate JSON keys
   refused, and every identity recomputed from the bytes read, never taken
   from the manifest — then it must match the receipt's `artifact_digest`,
   the current sources, and the settings `iconflow.toml` now has. The
   automated QA still runs on the current source (it may render for that).

`brand build --ship` goes through the same ship and records the icon plan in
`brand-manifest.json` as `approval.icon_plan` — scoped to the icon files; the
plan does not cover the wordmark, the fonts, or the rest of the kit.

A second opinion attached to `score` must have scored the same plan when both
are plan-bound; a pre-0.8 opinion is kept and marked `same_plan: null`.

## What writing guarantees, and what it does not

`write_plan` stages every file inside the output directory before touching
the destination, then moves them into place one by one. If a move fails, the
files already replaced are restored from staged backups and the error is
raised. So:

- a failure while rendering or staging leaves the output directory exactly as
  it was, and a missing output directory is not created;
- a failure while committing is rolled back as far as the filesystem allows;
- it is **not crash-atomic**: a power loss mid-commit can leave a mixture,
  and an interrupted run can leave a `.iconflow-staging-*` directory behind;
- files already in the output directory that the plan does not name are left
  alone, as in every earlier release.

## Not in 0.8

- The audit still renders through its own calls (in the same session where it
  can); sharing one source-aware render provider between `check` and the plan
  (review finding F09) is the next step.
- The trust anchor is still the receipt. Hash binding detects that output
  changed relative to an approval; it does not authenticate a reviewer to
  someone who can replace both the receipt and the plan.
- Older IconFlow executables ignore `plan` in a receipt. A workflow that
  promises "reviewed pixels shipped" must run 0.8 or later and read
  `outputs.plan.verified` from `ship --json`.
