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
   the current sources, and the settings `iconflow.toml` now has. From 0.9
   the automated audit then measures the replayed files themselves (below);
   a saved plan that fails these checks is never measured, and the audit
   renders the captured source instead, so its warnings still come first.

`brand build --ship` goes through the same ship and records the icon plan in
`brand-manifest.json` as `approval.icon_plan` — scoped to the icon files; the
plan does not cover the wordmark, the fonts, or the rest of the kit.

A second opinion attached to `score` must have scored the same plan when both
are plan-bound; a pre-0.8 opinion is kept and marked `same_plan: null`.

## The audit reads the plan (0.9)

Before 0.9 the automated audit rendered for itself: what `check` measured,
what the review showed and what `ship` published were three renders that
agreed only because the renderer was deterministic. Now one command runs in
one **render session** (`iconflow/session.py`): at most one Chromium, a
context per colour scheme, and every request — operation, exact SVG text,
size, background, scheme — rendered once and remembered (up to a 256 MB
budget, past which a render is still returned but no longer kept: "once"
becomes "at least once", never unbounded memory). Only the renderer's
own bytes are cached; optimisation, flattening, containers and templates run
exactly as before, which is why every built file is byte-identical to 0.8
(156 files across five configurations, checked against a `v0.8.0` checkout).

Each source is captured once per command (`plan.capture_sources`); the plan
and the audit measure those bytes (from 0.10.1 `check` too). `ship` validates
the approval by hashing the sources first, then refuses a captured source that
is not the one that approval names, and `review` reads its sources again at
the end and refuses to write findings if one changed while it ran
(`source-changed`, exit 2).

With a plan, the audit's probes that have a shipped counterpart read the
plan's own files:

| probe | reads |
|---|---|
| 16 px coverage, white and dark contrast | the 16 px master frame (`favicon.ico`, Tauri's containers) |
| 32 px mid-grey contrast | the 32 px master frame |
| maskable safe zone | `icon-512-maskable.png` |
| linked-source identity | `icon-512.png` (or Tauri's 512) and `icon-512-maskable.png` |
| ladder rungs, Android native identity, tray template, neighbourhood | renders of the captured source |

Only untransformed master renders qualify: apple-touch is flattened,
Electron rounded, tray and Android composed, and no emote size is one the
audit probes. A frame whose pixels are not the size its name or slot says,
or two representations of one size that disagree, make the plan unusable as
evidence (`PlanError`) — never a reason to measure a fresh render instead. A
plan rendered from another source or scheme, or a maskable file composed on
another background or scale, is refused the same way.

The result says where each of those plan-aware probes took its pixels from
(the supplementary probes in the last row are not listed): `outputs.plan.audited`
(true when the audit measured the plan for every probe that has a
counterpart) and `outputs.plan.audit_frames` (per probe: file, slot, size,
byte and pixel digests, or `"from": "render"` and why). `review --evidence`
writes the same record into `findings.json` as `audit_provenance`; `score`
re-derives every frame it names from the saved plan and refuses evidence
whose record does not match, and the receipt carries `audited_plan`.

On the same machine the findings are the same with or without the plan —
same pixels, same rules; a test holds `check`, `review` and `ship` to it.
Under `ship --plan` they can differ on purpose: the audit measures the
reviewed bytes, and a newer renderer that would have drawn a pixel less is
`check`'s finding about that renderer, not about what ships.

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

## Limits

- The trust anchor is still the receipt. Hash binding detects that output
  changed relative to an approval; it does not authenticate a reviewer to
  someone who can replace both the receipt and the plan. `docs/TRUST.md` is
  the decision and the repository policy that supplies an anchor.
- `check` computes no plan (it stays a few renders); it measures the source.
- `brand build` composes its kit after the gated ship, outside that ship's
  session; the one-render guarantee covers `review` and `ship`.
- Older IconFlow executables ignore `plan` in a receipt. A workflow that
  promises "reviewed pixels shipped" must run 0.8 or later and read
  `outputs.plan.verified` from `ship --json`; one that promises "audited what
  shipped" must run 0.9 and read `outputs.plan.audited`.
