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

## 5. Publish only after explicit approval

Recommended order after the owner approves publication:

1. Confirm the approved license, trademark policy, and GitHub metadata.
2. Merge the release commit and require a green CI run.
3. Create the signed or annotated `v0.5.0` tag.
4. Review the release-candidate artifact and checksums.
5. Create the GitHub Release with changelog notes and artifacts.
6. Configure PyPI Trusted Publishing with a protected GitHub environment and
   manual approval, then publish the exact already-reviewed artifacts.
7. Install from PyPI in a new environment and repeat the CLI/browser smoke test.

Never upload a locally different rebuild after the candidate was reviewed.
