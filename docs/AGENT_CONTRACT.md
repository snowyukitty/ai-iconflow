<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Agent Contract v1 — machine-readable IconFlow

> Status: frozen for the v0.5 "Adoption Loop" milestone (2026-08-21). Changes
> after v0.5.0 bump `schema` and are listed in `CHANGELOG.md`.

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

`doctor`, `check`, `review`, `ship`, `ladder`, and `demo` accept `--json`. In JSON mode
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

### `check --json`

`outputs`: `{"source": "<abs path>", "source_sha256": "<hex>", "tray_source": "<abs path or null>"}`.
Warning codes follow the warning prefixes `iconflow/qa.py` already prints,
lower-cased and hyphenated: `svg-safety`, `viewbox`, `stroke-floor`,
`coverage-16`, `contrast`, `maskable-detail`, `distinctiveness-text`,
`tray-template-featureless` (advisory).

A source that opts into the detail ladder (`docs/DETAIL_LADDER.md`) is also
gated on the same-mark invariant, adding `ladder-annotation`,
`ladder-empty-rung`, `ladder-footprint`, `ladder-silhouette`,
`ladder-centroid`, `ladder-hue`, and `ladder-subtraction`. A flat source — no
`data-lod` anywhere — never emits them and renders exactly as before.

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

### `doctor --json`

`outputs`: `{"checks": [{"name": "python", "status": "PASS|WARN|FAIL", "detail": "...", "fix": "<copy-paste command or null>"}], "chromium": "PASS|FAIL|SKIPPED"}`.
Every FAIL carries a `fix` the user can paste (for Chromium: the exact
`iconflow setup` invocation for this interpreter).

### `review --json`

`outputs`: `{"sheet": "<abs path>", "html": "<abs path or null>", "receipt_template": "<abs path or null>", "source_sha256": "...", "contract_sha256": "...", "targets": ["web", ...]}`.
A source that opted into the detail ladder also gets a `<sheet>-ladder.png`
proof written beside `sheet`, and its path is printed. It is deliberately *not*
a new `outputs` key: this envelope is frozen at `schema: 1` and the PR Proof
action rejects any other value, so new structure goes on the new `ladder`
command instead.
`review` exits `1` only when automated QA warnings exist (the human score is
not machine-judged); it never scores taste.

### `ship --json`

`outputs`: `{"files": ["<abs path>", ...], "receipt": "<abs path>", "source_sha256": "...", "contract_sha256": "...", "scores": {"legibility": 4, ...}}`.
Blocked ships report `status: "blocked"` with `warnings` codes
`receipt-stale-source`, `receipt-stale-contract`, `receipt-not-ready`,
`score-below-floor`, `qa-warnings`.

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
"toolchain": {"iconflow": "0.5.0", "chromium": "<version>", "pillow": "<version>"},
"artifacts": {"review_png_sha256": "...", "review_html_sha256": "..."},
"reviewer": {"kind": "human|agent", "name": "free text", "declared_at": "ISO-8601"}
```

`ship` trusts content, staleness, and the ≥4/5 floor — never the reviewer's
name. A named reviewer is provenance, not authority.

## Where it is tested

- `tests/test_cli.py`: golden JSON envelopes for each command (ok / blocked /
  error), exit-code matrix, stdout purity in JSON mode.
- `tests/test_distribution.py`: the demo family is present on the wheel and
  `demo` works from an installed wheel without the source tree.
- `.github/actions/proof`: consumes `check --json` and `review --json` only.
