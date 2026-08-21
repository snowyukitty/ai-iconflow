<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Releasing IconFlow

This is the maintainer checklist for producing a release. It prepares and
verifies artifacts; no step should be interpreted as permission to publish.

## 1. Clear owner-controlled gates

- Confirm that `LICENSE`, `NOTICE`, `TRADEMARKS.md`, and
  `THIRD_PARTY_NOTICES.md` match the intended release and that built metadata
  reports the SPDX expression `Apache-2.0` plus all four legal files.
- Confirm the release version in `pyproject.toml`, `iconflow/__init__.py`, and
  `CHANGELOG.md`.
- Enable GitHub private vulnerability reporting before broad announcement.
- Confirm that the package name is still available on PyPI. A 404 project page
  is evidence that no public distribution exists, not a reservation guarantee.

For the first public release, `v0.5.0` is the recommended tag: that version has
been consistent since the repository's first commit and has never been tagged
or published. Move the current `Unreleased` changelog entries into `0.5.0`
before tagging. Use `v0.5.0` only if the maintainer deliberately wants to treat
the July 2026 repository state as an internal 0.5.0 baseline.

## 2. Verify the checkout

Run from a clean clone or a worktree whose unrelated files are understood:

```bash
python -m pip install -e ".[dev]"
python -m iconflow doctor
python -m unittest discover -s tests
ICONFLOW_BROWSER_TESTS=1 python -m unittest tests.test_browser_security -v
python -m iconflow case lint
python -m iconflow case stats
```

Review `git status --short --branch`, the complete diff, and the commit range
that will be released. Scan for credentials, private paths, personal data,
generated work files, and unreviewed casebook entries.

## 3. Build and inspect distributions

Set a stable archive time to the release commit timestamp before building:

```bash
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)"
python -m build
python scripts/verify_distribution.py dist/*
sha256sum dist/*.whl dist/*.tar.gz > dist/SHA256SUMS
```

PowerShell equivalent:

```powershell
$env:SOURCE_DATE_EPOCH = git log -1 --format=%ct
python -m build
python scripts/verify_distribution.py dist/*
Get-FileHash dist\*.whl, dist\*.tar.gz -Algorithm SHA256
```

Build the wheel a second time with the same `SOURCE_DATE_EPOCH` and compare it
byte for byte. Current setuptools sdists have repeatable member contents but
generated member timestamps can differ, so verify the file lists and contents
without claiming byte-identical sdist archives.

Create a fresh temporary venv outside the checkout, install only the built
wheel, and run:

```bash
iconflow --help
iconflow doctor
iconflow styles --json > styles.json
iconflow styles --gallery style-gallery.png
iconflow new flat-geometric --out master.svg
iconflow init --out iconflow.toml --name "Release Smoke" --targets web,tray
iconflow check master.svg
iconflow render master.svg --sizes 16,32 --out "render-{size}.png"
```

Inspect the style gallery plus the 16px and 32px PNGs. Confirm that every style
listed in `styles.json` has a packaged SVG and an actual-size light/dark sample.
Run a full checked-in receipt through `ship` with an output override and inspect
its target assets as well.

## 4. Produce the candidate without publishing

The `Release candidate` workflow runs on manual dispatch and `v*` tag pushes.
It validates tag/version agreement, runs tests, inspects wheel and sdist
contents, proves the wheel reproducible, performs an installed-wheel smoke test,
writes SHA-256 checksums, and uploads a 14-day workflow artifact. It does not
create a GitHub Release or upload to PyPI.

Review the workflow artifact and CI results before any publication decision.

## 5. Claiming the name on PyPI

**PyPI has no way to reserve a name.** There is no "register this name" button,
and a *pending publisher* explicitly does not hold it — the PyPI documentation
says a pending publisher "does not create a project or reserve a project's name
until it is actually used to publish", and warns that if someone else registers
the name first, the pending publisher becomes invalid.

Two consequences worth stating before anyone plans around them:

1. **The name becomes yours at the moment of the first successful upload, and
   not before.** Configuring everything in advance is preparation, not a claim.
2. **Uploading is publishing.** The sdist and the wheel both carry the full
   source, so there is no order of operations that claims the name while keeping
   the code private. The reason to reach PyPI before the GitHub repository goes
   public is narrower than it sounds: it removes the window in which someone who
   noticed the public repository could take the name first.

Name status, checked 2026-08-22: both `iconflow` and `iconflow` return HTTP
404 on `https://pypi.org/pypi/<name>/json`, meaning both are unregistered.
Re-check immediately before publishing; this is the one fact that can change
without warning.

## 6. Publish only after explicit approval

`.github/workflows/publish.yml` does the upload. It re-runs the whole
release-candidate verification first, authenticates with Trusted Publishing
(OIDC — there is no API token in this repository and there should never be one),
and runs the upload inside a GitHub Environment so a required reviewer can hold
it.

One-time setup, in this order:

1. **PyPI account with 2FA.** PyPI requires two-factor authentication on every
   account that uploads. Set up a TOTP app or a hardware key at
   <https://pypi.org/manage/account/#two-factor>.
2. **Add a pending publisher** at
   <https://pypi.org/manage/account/publishing/> with exactly these values:

   | Field | Value |
   |---|---|
   | PyPI project name | `iconflow` |
   | Owner | `snowyukitty` |
   | Repository name | `iconflow` |
   | Workflow name | `publish.yml` |
   | Environment name | `pypi` |

   Repeat on <https://test.pypi.org/manage/account/publishing/> with environment
   name `testpypi` to rehearse first.
3. **The two GitHub Environments already exist** — `pypi` and `testpypi` were
   created on 2026-08-22 and need no further action for Trusted Publishing to
   work; the environment name only has to match what the pending publisher
   declares.

   What is *not* yet in place is the human gate. Adding a **required reviewer**
   to an environment on a **private** repository needs a paid GitHub plan
   (attempting it returns *"Please ensure the billing plan supports the required
   reviewers protection rule"*). The rule is free once the repository is public,
   which is the plan anyway — so the moment the repo goes public, add yourself
   as a required reviewer on `pypi` at `Settings → Environments → pypi`.

   Until then the workflow's own safeguards are what stand between a stray click
   and an irreversible upload: `workflow_dispatch` defaults to TestPyPI, and
   reaching the real index needs either an explicit `index: pypi` choice or a
   published GitHub Release.

Then, to release:

1. Confirm the approved license, trademark policy, and GitHub metadata.
2. Merge the release commit and require a green CI run.
3. **Rehearse:** run the Publish workflow manually with `index: testpypi`, then
   install from TestPyPI in a clean environment and run the smoke test. This
   costs nothing and is the only way to find a packaging problem *before* the
   version number is spent — a PyPI version can never be re-uploaded.

   Done once already, on 2026-08-22 (run `32516576257`): both jobs green, the
   OIDC handshake worked on the first attempt, and `iconflow 0.5.0` installed
   from TestPyPI into a clean venv and answered `iconflow doctor` with
   *IconFlow is ready*. Install from TestPyPI needs
   `--extra-index-url https://pypi.org/simple/`, because Playwright and Pillow
   are not mirrored there.

   Note what actually gets published: the workflow **builds in CI from the
   checked-out commit**, so the files uploaded are not the ones in a local
   `dist/`. Their digests will differ from a local build — the reproducibility
   `cmp` inside the workflow is what proves the CI build is self-consistent.
4. Create the signed or annotated `v0.5.0` tag.
5. Create the GitHub Release with changelog notes and the candidate artifacts;
   publishing the Release triggers the workflow against the real index.
6. Approve the waiting `pypi` environment.
7. Install from PyPI in a new environment and repeat the CLI/browser smoke test.

Never upload a locally different rebuild after the candidate was reviewed. The
workflow builds from the tagged commit and verifies reproducibility, so the
files it uploads are the files that were reviewed.
