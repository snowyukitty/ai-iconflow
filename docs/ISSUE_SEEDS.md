# Good-first-issue seeds (v0.5 adoption loop)

Drafts for the owner to file by hand. Each is bounded, keeps every gate, and
names its acceptance test. Sizes: **S** = under an hour, **M** = an afternoon.
None of them touches the >= 4/5 floor, the distinctiveness gate, or the
stale-receipt rule (`docs/EVOLUTION.md`, "Never weaken a gate").

---

## 1. Document the exit-code matrix in `iconflow --help` (S)

**Why.** `docs/AGENT_CONTRACT.md` pins 0 / 1 / 2, but a user who only runs
`iconflow --help` never sees it.

**Acceptance.** `iconflow --help` ends with an epilog naming the three codes
and their meaning in one line each; a test in `tests/test_cli.py` asserts the
epilog text is present; `README.md` links the contract from the CLI section.

**Files.** `iconflow/cli.py` (argparse `epilog`), `tests/test_cli.py`,
`README.md`.

## 2. `doctor`: per-OS Chromium remediation copy (S)

**Why.** A FAIL on the Chromium check currently points at `iconflow setup`;
on Linux the usual cause is missing shared libraries, which `setup` does not fix.

**Acceptance.** When the Chromium check fails, `doctor` prints one `fix` line
per platform: Windows/macOS `python -m iconflow setup`, Linux
`python -m playwright install --with-deps chromium` (and mentions that
`--with-deps` needs sudo on Debian/Ubuntu). `doctor --json` carries the same
string in `fix`. A unit test patches the failure and checks the copy per
`sys.platform`.

**Files.** `iconflow/cli.py` (`_cmd_doctor`), `tests/test_cli.py`.

## 3. Getting-started install table on the website (S)

**Why.** `CONTRIBUTING.md` now has the four-row install table (uv tool / pipx /
pip venv / contributor editable); `/getting-started/` still leads with clone.

**Acceptance.** The page shows the same table with the "PyPI pending - from a
checkout use the venv interpreter" note, and `tests/test_website.py` asserts
the four install verbs are present. No CTA swap to PyPI until the release
exists (milestone phase 3).

**Files.** `website/getting-started/index.html`, `tests/test_website.py`.

## 4. Case PR template: one-line "how to prove each box" hints (S)

**Why.** `.github/PULL_REQUEST_TEMPLATE/case.md` lists the gates; a first-time
contributor still has to find the command behind each box.

**Acceptance.** Every checkbox carries the exact command or doc section in an
HTML comment (so the rendered PR stays short), and
`tests/test_repo_contract.py` still finds every required checkbox.

**Files.** `.github/PULL_REQUEST_TEMPLATE/case.md`, `tests/test_repo_contract.py`.

## 5. Proof action: embed the native 16px cell in the job summary (M)

**Why.** The summary links the artifact, but reviewers decide fastest from the
16px cell itself.

**Acceptance.** `.github/actions/proof/proof.py` crops the 16px cell (and the
silhouette cell) out of `review.png` with Pillow, upscales it 8x nearest-
neighbour, writes `cell-16.png` into the artifact directory, and references it
from the summary via the artifact (GitHub summaries cannot inline local files,
so the summary must say which artifact file to open). Pure-function test with a
synthetic sheet. Must not change any exit code.

**Files.** `.github/actions/proof/proof.py`, `tests/test_repo_contract.py`,
`docs/PROOF_ACTION.md`.

## 6. Preset tray-strategy cross-link audit (S)

**Why.** `iconflow styles --json` exposes a tray strategy per preset;
`docs/STYLE_CATALOG.md` and `docs/OUTPUT_TARGETS.md` describe the same thing in
prose and have drifted before.

**Acceptance.** A test loads `STYLE_CATALOG` and asserts every preset's tray
strategy string appears in `docs/STYLE_CATALOG.md` next to that preset; any
mismatch found is fixed in the doc, not the catalog.

**Files.** `tests/test_cli.py` or `tests/test_qa.py`, `docs/STYLE_CATALOG.md`.

## 7. `styles --json` consumer example (S)

**Why.** The catalog is machine-readable, but nothing shows an agent picking a
preset from it.

**Acceptance.** `examples/README.md` §2 gains a ten-line Python snippet that
reads `iconflow styles --json`, filters by tray strategy, and calls
`iconflow new <preset>`; the snippet is executed by a test against the packaged
catalog (no Chromium needed).

**Files.** `examples/README.md`, `tests/test_cli.py`.

## 8. Windows `pipx` / `uv tool` PATH hint in `doctor` (S)

**Why.** After `pipx install` or `uv tool install` on Windows, `iconflow` is
often not on PATH until `pipx ensurepath` / `uv tool update-shell` and a new
shell; users then report "command not found" as a bug.

**Acceptance.** `doctor` adds a WARN (never FAIL) check on Windows when
`shutil.which("iconflow")` is empty while the package is importable, with the
two `ensurepath` commands as the `fix`. Unit test patches `shutil.which`.

**Files.** `iconflow/cli.py` (`_cmd_doctor`), `tests/test_cli.py`,
`CONTRIBUTING.md` install table footnote.
