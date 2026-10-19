<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Agent Contract v1 — machine-readable IconFlow

> Status: frozen for the v0.5 "Adoption Loop" milestone (2026-08-21). A
> change that removes or retypes anything bumps `schema`; additions do not —
> within `schema: 1` an object (`outputs`, and every object nested in it) may
> gain keys, and a consumer ignores keys it does not know. Every change is
> listed in `CHANGELOG.md`.

IconFlow's quality gate already exists: `check` finds mechanical risks,
`review` renders exact native pixels and records a six-axis receipt bound to
the source hash, and `ship` refuses a stale receipt or any axis below 4/5. This
contract makes that gate consumable by agents and CI without parsing human
prose. It adds a JSON output mode and pins the exit-code meaning; it does not
change any gate.

## Exit codes (every command)

| Code | Meaning | Examples |
|---:|---|---|
| `0` | completed; no gating failure (advisories allowed) | clean `check`; `review` rendered; `ship` wrote every file; `doctor` all PASS |
| `1` | gated: the work is blocked by IconFlow's own rules | `check` warnings; `ship` stale receipt or axis < 4; `doctor` FAIL; `case lint` errors |
| `2` | usage, configuration, or runtime failure | unknown flag; missing file; invalid `iconflow.toml`; Chromium launch error; I/O error |

Advisories (for example the tray-template audit from `--tray-svg`) never turn
a `0` into a `1`.

## `--json` envelope

`doctor`, `check`, `review`, `ship`, `ladder`, `neighbours`, and `demo` accept `--json`. In JSON mode
**stdout carries exactly one JSON object** and nothing else; human diagnostics
go to stderr. The object always has these keys:

```json
{
  "schema": 1,
  "command": "check",
  "status": "ok",
  "exit_code": 0,
  "warnings": [],
  "advisories": [],
  "outputs": {},
  "errors": []
}
```

- `status`: `"ok"` (exit 0), `"blocked"` (exit 1), `"error"` (exit 2).
- `warnings`: gating findings, each `{"code": "stroke-floor", "message": "..."}`.
  Codes are stable kebab-case identifiers (see below).
- `advisories`: non-gating findings with the same shape (`tray-template-featureless`).
- `errors`: only for `status: "error"`; `{"code": "...", "message": "..."}`.
- `outputs`: command-specific, documented below. Paths are absolute strings.
  Within `schema: 1`, `outputs` may gain keys and never loses or retypes one;
  a consumer must ignore keys it does not know.

### One audit: `outputs.audit` (0.7)

`check`, `review` and `ship` run one shared audit (`iconflow/audit.py`) and
each reports the inputs it used as `outputs.audit`:

```json
"audit": {"targets": ["web", "tauri"], "background_color": "#11142A",
          "color_scheme": "light", "maskable_audit": true, "maskable_scale": 0.8,
          "maskable_source": null, "tray_source": null,
          "tray_template_mode": "auto", "neighbours": true}
```

With the same SVG and `--config`, the three commands report the same `audit`
object and, on one machine, the same warnings; `tests/test_audit.py` fails if
they can differ. From 0.9 `ship --plan` measures the replayed bytes, so on
another machine its findings can differ from a local `check` on purpose
(`docs/RENDER_PLAN.md`).
Before 0.7, `check --config` composed the maskable icon on white while `review`
and `ship` used the configured background. Precedence is: explicit flag, then
the config, then the defaults (`web,pwa`, `#ffffff`, light). `check` with
`--config` no longer needs `MASTER`.

### `check --json`

```
iconflow check [MASTER] [--config iconflow.toml] [--bg ...] [--targets ...]
               [--color-scheme ...] [--tray-svg ...] [--json]
```

`outputs`: `{"source": "<abs path>", "source_sha256": "<hex>", "tray_source": "<abs path or null>"}`.
Warning codes follow the warning prefixes `iconflow/qa.py` already prints,
lower-cased and hyphenated: `svg-safety`, `viewbox`, `stroke-floor`,
`coverage-16`, `contrast`, `maskable-detail`, `maskable-drift` (a linked
`maskable_svg` that is not the master's mark), `distinctiveness-text`,
`tray-template-featureless` (advisory). Every message names the input it was
measured under (background colour, size, scheme, rung, scale) and ends with a
concrete fix.

A source that opts into the detail ladder (`docs/DETAIL_LADDER.md`) is also
gated on the same-mark invariant, adding `ladder-annotation`,
`ladder-empty-rung`, `ladder-footprint`, `ladder-silhouette`,
`ladder-centroid`, `ladder-hue`, and `ladder-subtraction`. A flat source — no
`data-lod` anywhere — never emits them and renders exactly as before.

With `--config`, a project whose `iconflow.toml` carries a `[neighbours]`
table (`docs/NEIGHBOURHOOD.md`) is also audited for shape collision at 16px:
`neighbour-collision` (gating — a declared `avoid` mark is the same shape;
the message names it), `neighbour-familiar` (advisory — the bundled collision
set or house corpus), and `neighbour-house-rut` (advisory — three or more
`portfolio` marks inside the radius). A config without the table, or no
`--config` at all, emits none of them and the envelope is unchanged. `review
--config` and `ship` run the same audit, and a collision blocks `ship` behind
`qa-warnings` like any other check warning.

### `ladder --json`

```
iconflow ladder MASTER [--sheet PNG] [--size N] [--color-scheme ...]
                       [--containment F] [--iou F] [--centroid-drift F]
                       [--hue-drift DEG] [--json]
```

`outputs`: `{"source": "<abs path>", "source_sha256": "<hex>", "ladder": true|false,
"rungs": ["glyph", "mark", "plate"], "compare_size": 256, "measures": [{"rung": "...",
"coverage": 0.0, "visible": 0.0, "centroid": [x, y], "hue": 0.0}], "steps":
[{"smaller": "glyph", "larger": "mark", "footprint_containment": 1.0,
"footprint_iou": 1.0, "visible_iou": 1.0, "centroid_drift": 0.0, "hue_drift": 0.0}],
"sheet": "<abs path or null>"}`.

`measures` and `steps` are reported whether or not anything failed — a green
run still carries its evidence. A flat source reports `ladder: false`, empty
`rungs` and `steps`, one advisory `ladder-flat`, and exits `0`: having no
ladder is a valid state, not a defect. Warning codes are the `ladder-*` set
above.

### `neighbours --json`

```
iconflow neighbours [MASTER] [--config iconflow.toml] [--avoid SVG]... [--family SVG]...
                    [--sheet PNG] [--radius F] [--nearest N] [--color-scheme ...] [--json]
```

`outputs`: `{"source": "<abs path>", "source_sha256": "<hex>", "radius": 0.12,
"field": {"components": 1, "holes": 0, "coverage": 0.31, "aspect": 1.2},
"nearest": [{"id": "collision/bar-chart", "set": "collision|house|avoid|portfolio",
"title": "...", "source": "...", "distance": 0.071, "same_topology": true,
"components": [3, 3], "holes": [0, 0]}], "collisions": ["<id>", ...],
"familiar": ["<id>", ...], "rut": ["<id>", ...], "family": [<same shape as nearest>],
"sheet": "<abs path or null>"}`.

`nearest` carries the closest `--nearest` marks plus every mark inside the
radius, whether or not anything failed. Warning code: `neighbour-collision`
(only against the declared or `--avoid` set). Advisory codes:
`neighbour-familiar`, `neighbour-house-rut`. Exit `1` only for a collision;
without any avoid set the command can only advise and exits `0`. It is not a
clearance check and the human distinctiveness gate still applies.

### `family --json`

```
iconflow family SVG... [--sheet PNG] [--json]
```

`outputs`: `{"coherence": 0.2, "twin_floor": 0.3333, "members": [{"id": "family/joy",
"title": "...", "source": "...", "source_sha256": "<hex>", "field": {"components": 1,
"holes": 0, "coverage": 0.31, "aspect": 1.0}}], "groups": [["family/joy", ...]],
"nearest": [{"a": "<id>", "b": "<id>", "group": 0, "residual": 0.503,
"raw": {"distance": 0.087, "same_topology": false, "components": [1, 3], "holes": [1, 1]},
"twin": false}], "twins": [["<id>", "<id>"]], "sources": {"<stem>": "<hex>"},
"sheet": "<abs path or null>"}`.

Members are paths or quoted globs (at least two). `groups` are the carrier
groups found from the fields; `nearest` carries the closest sibling pairs —
every twin, then the next closest — whether or not anything failed. `residual`
is null for a pair whose group has only two members, which is judged on its
raw distance instead (`docs/FAMILY.md`). Warning code: `family-twins`. Exit
`1` only for twins.

### `doctor --json`

`outputs`: `{"checks": [{"name": "python", "status": "PASS|WARN|FAIL", "detail": "...", "fix": "<copy-paste command or null>"}], "chromium": "PASS|FAIL|SKIPPED"}`.
Every FAIL carries a `fix` the user can paste (for Chromium: the exact
`iconflow setup` invocation for this interpreter).

### `review --json`

`outputs`: `{"sheet": "<abs path>", "html": "<abs path or null>", "receipt_template": "<abs path or null>", "source_sha256": "...", "contract_sha256": "...", "targets": ["web", ...]}`.
A source that opted into the detail ladder also gets a `<sheet>-ladder.png`
proof written beside `sheet`, and its path is printed. It is deliberately *not*
a new `outputs` key: the ladder's structure belongs to the `ladder` command,
which reports it in full, and `review`'s envelope stays the PR Proof action's
small contract (that action accepts `schema: 1` only).
`review` exits `1` only when automated QA warnings exist (the human score is
not machine-judged); it never scores taste.

### `ship --json`

`outputs`: `{"files": ["<abs path>", ...], "receipt": "<abs path>", "source_sha256": "...", "contract_sha256": "...", "scores": {"legibility": 4, ...}}`.
Blocked ships report `status: "blocked"` with `warnings` codes
`receipt-stale-source`, `receipt-stale-contract`, `receipt-not-ready`,
`score-below-floor`, `qa-warnings`, and from 0.8 `plan-drift` (the rendered
output differs from the plan the receipt approved) and `plan-replay` (a
`--plan` directory that cannot be published as the reviewed bytes).

When more than one gate would refuse, the first in this order is reported,
alone: the approval (`receipt-*`, `score-below-floor`), automated warnings
(`qa-warnings` and their codes), a plan that cannot be built or replayed
(`plan-replay`, or a `runtime` error), then `plan-drift`. Nothing is written
on any refusal.

From 0.9 `outputs.audit` is reported as soon as the audit inputs resolve,
blocked or not, and a passing ship adds `outputs.receipt_sha256`: the SHA-256
of the exact receipt bytes validated (`null` for a `[review]` table). It
identifies the approval; it does not authenticate it (`docs/TRUST.md`).
`review` and `ship` exit `2` with error code `source-changed` when a source
is not the one the approval names, or changed while the command ran.

### `outputs.plan` (0.8, the render plan)

`ship`, `review` and `score` gain one key (`docs/RENDER_PLAN.md`):

```json
"plan": {"digest": "<content sha256>", "artifact_digest": "<bytes sha256>",
         "verified": true, "bytes_verified": true, "drift": [], "mode": "rendered",
         "audited": true,
         "audit_frames": {"master-16": {"from": "plan", "file": "favicon.ico", "slot": 16,
                                        "size": 16, "sha256": "...", "content_sha256": "..."},
                          "master-32": {"...": "..."},
                          "maskable-512": {"from": "plan", "file": "icon-512-maskable.png", "...": "..."}}}
```

`verified` is `true` when the shipped content equals the approved plan,
`false` on drift (the ship is then blocked), and `null` when there is nothing
to compare with: a receipt from before 0.8, a `[review]` table, and every
`review`/`score` (they *make* a plan; they do not compare one). `drift` lists
changed, added and removed paths. `mode` (ship only) is `rendered` or
`replayed` (`ship --plan DIR`). `review`'s `plan` is `null` when no plan could
be computed (for example, a tray template that cannot be derived); the review
still runs, and its other renders still need Chromium.
Advisory `plan-unbound`: a ship whose receipt carries no plan.

From 0.9 (`review` and `ship`): `audited` is `true` when the audit measured
the plan's own files for every probe that has a shipped counterpart, whatever
its outcome — it can be `true` on a ship blocked by warnings, and it never
means every output file was inspected. `audit_frames` says, per probe, which
file and slot the pixels came from, or `{"from": "render", "reason": "..."}`
(`docs/RENDER_PLAN.md`, "The audit reads the plan").

### `score --json` (0.7, headless review)

```
iconflow score --config iconflow.toml --evidence DIR --scores "..." --rationale AXIS=TEXT...
               --notes "..." --reviewer-name NAME [--reviewer-kind agent|human]
               [--second-opinion RECEIPT]... [--out master-review.json] [--json]
```

`outputs`: `{"receipt": "<abs path>", "status": "ready|blocked", "scores": {...},
"source_sha256": "...", "contract_sha256": "...", "review_surface": {...},
"second_opinions": 0}`. Exit `0` when the receipt is ready, `1` when an axis is
below 4 (`score-below-floor`) or the evidence carries automated warnings (their
own codes), `2` for stale or edited evidence, a missing reason, or a second
opinion over different evidence or from the same reviewer. Advisory:
`second-opinion-dissent`. `review --evidence DIR` adds `outputs.findings` (the
path of `findings.json`, `null` without `--evidence`).

From 0.9 everything the command line carries (`--scores`, every
`--rationale`, `--notes`, `--reviewer-name`) is validated before the axis walk
is printed, and `--rationale` without `--scores` is refused rather than
ignored. `findings.json` gains `audit_provenance` (`{"schema": 1, "plan":
{...three digests...}, "audited": bool, "frames": {...}}`); `score` re-derives
every frame it names from the saved plan and exits `2` on any mismatch or a
malformed record. Evidence without it (0.8) is accepted as not audited.

### `demo --json`

`outputs`: `{"out": "<abs dir>", "steps": [{"name": "doctor|check|review|ship", "status": "ok|blocked|error", "exit_code": 0}], "files": [...], "receipt": "<abs path>"}`.

## `iconflow demo`

```
iconflow demo --out DIR [--setup] [--json] [--force]
```

Materializes one packaged, already-reviewed family (the IconFlow brand
family: `master.svg`, `tray.svg`, `iconflow.toml`, `master-review.json`) into
`DIR` (which must not exist unless `--force`), then runs `doctor` → `check` →
`review` (sheet + HTML) → `ship` against the bundled receipt. `--setup` runs
`iconflow setup` first (the only step that uses the network). The demo proves
the engine with a real receipt; it does not claim to design a new identity.
Editing the materialized `master.svg` and re-running `ship` must fail closed
with `receipt-stale-source` — that is part of the acceptance test.

## Review Packet v1 (receipt additions)

The existing receipt (`source_sha256`, `contract_sha256`, targets, build,
scores, notes, status) is the packet. v1 adds optional fields that `ship`
records when present and never requires:

```json
"toolchain": {"iconflow": "0.9.0", "chromium": "<version>", "pillow": "<version>"},
"artifacts": {"review_png_sha256": "...", "review_html_sha256": "..."},
"reviewer": {"kind": "human|agent", "name": "free text", "declared_at": "ISO-8601"}
```

`ship` trusts content, staleness, and the ≥4/5 floor — never the reviewer's
name. A named reviewer is provenance, not authority.

0.7 adds, from `iconflow score`:

```json
"rationale": {"legibility": "...", "...": "..."},
"review_surface": {"kind": "headless-evidence", "interactive_lab": false,
                   "findings_sha256": "...", "audited_plan": true, "note": "..."},
"second_opinions": [{"reviewer": {...}, "scores": {...}, "notes": "...",
                     "receipt_sha256": "...", "dissent": ["..."]}]
```

`ship` reports `review_surface` in its outputs and re-derives dissent from
`second_opinions` as advisories. Neither changes a gate.

0.8 adds the render plan the review showed:

```json
"plan": {"schema": 1, "digest": "...", "artifact_digest": "...", "provenance_digest": "...",
         "files": {"favicon.ico": {"content": "...", "sha256": "..."}, "...": {}},
         "toolchain": {"iconflow": "0.8.0", "chromium": "...", "pillow": "...", "platform": "..."}}
```

Absent, it is a pre-0.8 receipt (valid, reported unbound). Present, it must be
well formed — a malformed `plan` is a configuration error, never an unbound
receipt — and `ship` gates on it (`plan-drift`). A second opinion's `plan`, when
both are bound, must be the same plan.

0.9 adds to a Review Lab export what a headless receipt already had, as
provenance that no gate reads:

```json
"review_surface": {"kind": "review-lab", "interactive_lab": true, "note": "..."},
"toolchain": {"iconflow": "0.9.0", "chromium": "...", "pillow": "...", "platform": "..."},
"reviewer": {"kind": "human|agent", "name": "self-declared", "declared_at": "export time"}
```

`toolchain` is the one that generated the Lab (the plan keeps its own);
`reviewer` appears only when the reviewer filled it in. The `toolchain`
`iconflow` value is now the running code's version, not installed metadata.

## Where it is tested

- `tests/test_cli.py`: golden JSON envelopes for each command (ok / blocked /
  error), exit-code matrix, stdout purity in JSON mode.
- `tests/test_distribution.py`: the demo family is present on the wheel and
  `demo` works from an installed wheel without the source tree.
- `tests/test_neighbours.py`: the `neighbours` envelope, the codes, the
  index drift checks, and (under Chromium) the calibration table.
- `tests/test_audit_on_plan.py` (0.9): the render session, frame selectors,
  the audit on the plan, gate precedence, captured sources, evidence
  provenance, receipt digests and the Lab's bindings.
- `.github/actions/proof`: consumes `check --json` and `review --json` only.
