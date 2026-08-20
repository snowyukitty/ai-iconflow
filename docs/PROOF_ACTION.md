# PR Proof GitHub Action

`.github/actions/proof` is a composite action that runs IconFlow's
*mechanical* gate on a pull request and reports it in the job summary. It
consumes only the Agent Contract JSON envelopes (`docs/AGENT_CONTRACT.md`), so
it needs `ai-iconflow >= 0.5.0` (`--json` on `check` and `review`).

For every `iconflow.toml` in scope it runs:

| Step | Command | Fails the job when |
|---|---|---|
| check | `python -m iconflow check <master> --json --bg <background>` (+ `--tray-svg <tray> --tray-template-mode <mode>` when the toml names a tray source; `--no-maskable-audit` when no web/pwa target) | `status != "ok"` (any QA warning, or a runtime error) |
| review | `python -m iconflow review --config <toml> --out review.png --html review.html --json` | `status != "ok"` (QA warnings or a render error) |
| receipt | `python scripts/proof_receipt.py --config <toml> --json` | a receipt is present **and** stale/invalid: `receipt-stale-source`, `receipt-stale-contract`, `receipt-not-ready`, `score-below-floor`, `qa-warnings`, `receipt-invalid` |

Advisory (reported, never failing): tray-template findings from `check`
(`tray-template-featureless`). A family with no receipt and no approved `[review]` fallback is **blocked** with `receipt-not-ready`; a CLI that prints anything but exactly one JSON object on stdout, or whose exit code disagrees with its envelope, fails the step with `envelope-unparseable` / `envelope-invalid`. `review.png` and `review.html` are uploaded
as an artifact; `proof.json` in the same artifact holds every envelope.

What it deliberately does **not** do: score taste, approve a receipt, comment on
or label the PR, write to the repository, or read any secret. A human still
inspects the sheet and signs the receipt; `iconflow ship` stays the only thing
that writes the family.

## Using it in this repository

`.github/workflows/icon-proof.yml` runs on `pull_request` (never
`pull_request_target`) when paths match `**/*.svg`, `**/iconflow.toml`,
`**/*-review.json`, or `**/master-review.json`. It lists the changed files from
the PR base and hands them to the action, which proves only the configs those
files touch - `brand/iconflow.toml`, `examples/iconflow-balloon/`,
`examples/iconflow-parachute/`, `examples/community-case/`, or any new
`iconflow.toml`. A website asset change with no neighbouring `iconflow.toml`
produces a "nothing to prove" summary and a green job.

```yaml
- uses: ./.github/actions/proof
  with:
    install: .                                     # prove the checkout itself
    changed-files: ${{ runner.temp }}/changed-files.txt
```

The three fixture outcomes the milestone asks for are reproducible locally
against `examples/community-case/`: unchanged = clean pass; a stroke thinned
below the 16px floor = QA-warning fail; one coordinate edited without a new
receipt = `receipt-stale-source` fail.

## Using it in another repository

```yaml
name: Icon proof
on:
  pull_request:
    paths: ["**/*.svg", "**/iconflow.toml", "**/*-review.json"]
permissions:
  contents: read
jobs:
  proof:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          persist-credentials: false
      - name: List changed files
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
        run: |
          git fetch --no-tags --depth=1 origin "$BASE_SHA"
          git diff --name-only "$BASE_SHA" HEAD > "$RUNNER_TEMP/changed-files.txt"
      - uses: snowyukitty/ai-iconflow/.github/actions/proof@v0.5.0   # pin a tag or, better, a commit SHA
        with:
          install: ai-iconflow==0.5.0       # once the release is on PyPI; until then pin a git URL or a wheel path
          changed-files: ${{ runner.temp }}/changed-files.txt
```

Until `ai-iconflow` is on PyPI, `install` can be any pip spec:
`git+https://github.com/snowyukitty/ai-iconflow@<sha>` or a vendored wheel
path. Omit `changed-files` to prove every `iconflow.toml` in the repository on
each run, or pass `configs:` to name them explicitly.

## Inputs

| Input | Default | Meaning |
|---|---|---|
| `install` | `ai-iconflow==0.5.0` | pip requirement spec; `.` inside this repo |
| `python-version` | `3.12` | handed to `actions/setup-python` |
| `configs` | empty | newline/space-separated `iconflow.toml` paths; empty = discover (skips `.git`, `.venv`, `node_modules`, `work/`) |
| `changed-files` | empty | path to a newline-separated changed-file list; restricts discovery to configs whose directory, master, or tray source changed |
| `artifact-name` | `iconflow-proof` | artifact holding `review.png`, `review.html`, `proof.json` per config |
| `upload-artifacts` | `true` | set `false` to skip the upload step |

Outputs: `status` (`ok` / `blocked` / `error`) and `artifact-dir`.

## Exit codes and summary

The driver (`.github/actions/proof/proof.py`) folds envelopes fail-closed: any
`error` -> exit 2, else any `blocked` -> exit 1, else 0. The job summary is one
table (config / check / review / receipt / six scores / sheet) plus a per-config
list of warning and advisory codes with their messages - nothing is parsed from
human prose, and a CLI that prints anything but one JSON object on stdout is
reported as `envelope-unparseable` and fails.

## Permissions and security

- `permissions: contents: read` is all it needs. Artifact upload and the job
  summary use the runner's own token, not `GITHUB_TOKEN` write scopes.
- Trigger on `pull_request`, never `pull_request_target`: a fork PR then runs
  with a read-only token and no repository secrets, and the action reads no
  secret at all.
- `actions/checkout` runs with `persist-credentials: false`.
- Every `uses:` is pinned to a full commit SHA with the version in a comment
  (`checkout` v7, `setup-python` v7, `cache` v6, `upload-artifact` v6 - all on
  the Node 24 runtime). Bump pins deliberately and together with `ci.yml`.
- Chromium is installed by Playwright into `$RUNNER_TEMP/ms-playwright` and
  cached by OS, arch, and Playwright version. IconFlow renders with network,
  JavaScript, and external resources disabled, so an untrusted SVG from a fork
  cannot reach out; it is still rendered on a throwaway runner, not on your
  machine.
- The action installs a Python package. In a foreign repo pin `install` to an
  exact version (or a commit SHA) and pin the action ref the same way.

## Local equivalent

```bash
python -m iconflow check master.svg --json
python -m iconflow review --config iconflow.toml --out review.png --html review.html --json
python scripts/proof_receipt.py --config iconflow.toml --json
```

`scripts/proof_receipt.py` is the only new logic; it calls
`iconflow.config.load_config`, `load_review_receipt`, `svg_sha256`, and
`config_review_contract_digest`, reports the same stale codes `ship` would, and
never writes. `tests/test_repo_contract.py` covers it and the action files.
