<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Milestone 0.10.1 — system-design polish

Started 2026-10-20 on `main`, the day 0.10.0 was released. No feature: the
owner asked for a review and polish of the system design before the session
closed. The aim was a codebase that is easier to change correctly, documents
that say what the code does, and every boundary the earlier milestones drew
holding where it had a gap — with every built file byte-identical to 0.10.0.
Not released: a release needs the owner's word.

## How it was reviewed

1. **The owner's own survey** (Claude): the import graph, dead code (vulture),
   test warnings, every document's inbound links, the target registries.
2. **A sealed design review** by Codex (`codex:default`, `gpt-6-astra`,
   `--quality deep`, kind `analysis`) over the core sources and the trust
   documents, asked for misplaced responsibilities, implicit contracts,
   documents that disagree with the code, latent bugs, and a ranked list of
   changes safe for a wrap-up. It returned fourteen findings (PF01–PF14,
   below) and a list of refactors *not* to do now.
3. **An implementation review** of the resulting diff by the same reviewer,
   then **verification passes** in fresh contexts until it approved: ten in
   all, the last an APPROVE (below).

## Findings and what was done

`PF` findings are Codex's; `PO` are the owner survey's. Every one has a
regression test named after it, or a reasoned dissent.

| id | severity | finding | resolution |
|---|---|---|---|
| PF01 | high | `ship --plan` could publish with `outputs.plan.verified = false`: replay compared the byte and provenance digests, not the content identities or each file's bytes, so a shape-valid receipt that contradicted itself replayed | replay also requires the content to match and every file's recorded `sha256` to agree; either failure is `plan-replay`, nothing written |
| PF02 | high | a link or junction the project carries *above* the output directory (`dist` → elsewhere, `output = "dist/icons"`) was followed; only the output and what is below it were checked | `build.output_link` refuses a write that would pass through a link inside the project, `..` allowed; `build()`, the legacy writers, `ship` (configured output from the config's folder, `--out` from the working directory). Its final form came out of V1–V3, below |
| PF03 | medium | a missing Playwright raised `SystemExit` past the command's error handling: no `--json` envelope, exit 1 ("gated") instead of 2 | a `RuntimeError` (exit 2, one envelope); `shortcut`'s refusals map to exit 2 too |
| PF04 | medium | `check` let each audit stage read the master itself and hashed it again for `source_sha256`: an edit mid-command could mix versions | `check` captures its sources once, audits that snapshot under `frozen_view`, and reports its hash |
| PF05 | medium | dropping `ios` from the targets bypassed the stale-iOS-file refusal | **dissent** — the refusal guards one catalog's coherence (a `Contents.json` that no longer names a PNG beside it, C-F18). A build that writes no iOS file leaves an earlier, self-consistent catalog alone, as `write_plan` leaves every other target's earlier files; refusing would make `ios` the one target whose removal needs manual cleanup. The contract's wording overreached and is corrected; a test pins the behaviour |
| PF06 | medium | any exception while computing a review's plan — an IconFlow bug included — silently left the receipt unbound | only a build's own refusals (an `OSError`, a plain `ValueError`, IconFlow's own `ValueError` subclasses) and renderer failures fall back; anything else is a runtime error naming itself a defect (narrowed by IR06 and VR03) |
| PF07 | medium | the contract said an unsupported `id="iconflow-background"` is an exit-2 error; the auditing commands report it as the gating `ios-underivable` (exit 1) | documented as it is, per command (measured, after IR08); an exit-code taxonomy change was out of scope for a polish pass |
| PF08 | medium | the headless target sheet showed emotes at 28 and 56 px; the pack also ships 112 and 128, which a headless scorer never saw | every size in `EMOTE_SIZES`, from the plan's own files |
| PF09 | low | `LazyRasterizer` exited the object `__enter__` returned, not the context manager it entered | the owner is kept and exited once, as `RenderSession` does |
| PF10 | medium | a valid non-square `viewBox="0,0,1024,512"` (commas, or an exponent) passed `check`, and a nested element's `viewBox` could stand in for a missing root one | the root's `viewBox` is read as Chromium reads it (its grammar settled in V6, F6-02); an unusable one is reported (`viewbox`) |
| PF11 | medium | parameter projections are duplicated across modules; `contract_inputs` claimed unused sources cannot stale an approval, but a configured `tray_svg` always binds | docstrings corrected and the tray binding pinned by a characterization test; the projections are left for a milestone with characterization tests first (Codex's own advice) |
| PF12 | low | the manual `[review]` fallback was documented without saying `ship` refuses it for `ios` | `WORKFLOW.md`, and the generated `iconflow.toml` of an `ios` project (only of one: every other project's file is unchanged) |
| PF13 | low | doctor's Linux fix appended a parenthesis a shell cannot run; a quoted Windows executable needs PowerShell's `&`; POSIX quoting left `$` live | the explanation is a shell comment; Windows executables get `& "…"`; POSIX arguments are single-quoted |
| PF14 | medium | the plan import measured a file, then read it unbounded: a file that grew in between was read past the budget | reads are bounded to the measured size plus one byte |
| PO01 | medium | the 0.7 single-target writers (`build.build_tauri` and its siblings) wrote through a linked output tree | they validate the tree as `build()` does |
| PO02 | low | dead code: `cli._neighbourhood_for`, `brand._hash_tree`, `qa._normalised_figure` | removed (`headless.evidence_paths` kept: a public name, Codex's advice) |

Documents brought in line with the code: `WORKFLOW.md` (the receipt's plan,
headless review, `plan-drift`, `ship --plan`, the `ios` exception),
`TRUST.md` and `RENDER_PLAN.md` (which reads are the snapshot and which are
deliberate validation reads), `AGENT_CONTRACT.md` (path classes in
`outputs`, `source-changed` vs `receipt-stale-source`, PF05, PF07), the
review's `source-changed` message (the sheets show the replaced version;
they do not mix two), the 0.8 record's "Not done" (closed items marked), and
the package docstring (it still listed five targets).

## Implementation review

The same reviewer, fresh context, over the whole diff, its own design review
and the full sources of the changed modules: **REQUEST_CHANGES**, twelve
findings. The first attempt was rejected by ATD (the provider echoed a wrong
artifact digest) and was resent unchanged.

| id | severity | finding | resolution |
|---|---|---|---|
| IR01 | high | PF02's walker collapsed `..` lexically and compared with the base by spelling, so a path through a trusted alias of an ancestor plus `..` (`/var/…/project/safe/../dist` for `/private/var/…`) missed the project's link | one walker for every spelling: each component is checked when the directory it sits in *really* is the base or inside it (real path), the path joined as written so the operating system's own `..` is what is resolved; tested with an aliasing link above the project |
| IR02 | high | the check expanded `~`, the writer did not: `project/~` linked elsewhere was written through | the path is checked literally, as written; callers that expand (`ship`) expand before both; tested with a linked `~` |
| IR03 | medium | PO01's legacy writers checked the tree, not its ancestry | `_write_assets` runs the same ancestry check |
| IR04 | medium | the new ship check returned a configuration error before the audit, hiding QA warnings, plan failures and drift | computed early, reported where `write_plan`'s own refusal of a linked output always was, after every gate (`runtime`, exit 2); a test shows drift still wins |
| IR05 | medium | `check` captured every configured source, so an invalid source no selected target reads (an old monochrome file on a web-only project) failed a check that never measures it | `check` captures what its targets consume |
| IR06 | medium | `RecursionError`, `NotImplementedError` (both `RuntimeError`s) and `UnicodeError` (a `ValueError`) still counted as a build's refusal | exact builtin types, plus IconFlow's own `ValueError` subclasses; **residual, kept visible:** a plain `ValueError` the interpreter raises (a bad unpacking) cannot be told from a raised one without an exception taxonomy over ~90 raise sites, deferred with PF07's |
| IR07 | medium | PF10 read the root attribute case-sensitively, but the renderer inlines the SVG in HTML, whose parser accepts `viewbox`: a master that rendered correctly would newly fail `check` | the name is matched in any case, as the renderer reads it |
| IR08 | medium | PF07's new text still overstated: `review --html` and `review --evidence` exit 2 | measured per command and documented as a matrix (`check`, static `review`, `--receipt-template`: 1; `--html`, `--evidence`, `build`: 2; `ship` stops at `receipt-not-ready`) |
| IR09 | medium | `ARCHITECTURE.md` promised more than the code: commands outside check/review/ship open their own `Rasterizer`; SVG is size-checked after it is read; source links are a feature | the invariants now say exactly that |
| IR10 | medium | the PF14 tests would pass a read-everything-then-slice implementation | a test at the file handle, through the public `load_plan`: every read request is a positive bound, the manifest's is its cap plus one, and `Path.read_bytes`/`read_text` are not used |
| IR11 | low | PowerShell expands `$` and backquotes inside double quotes | Windows arguments are PowerShell single-quoted literals (`''` for an apostrophe), executables called with `&` |
| IR12 | low | a cleanup failure in `LazyRasterizer` hid the render failure | the body's error is kept; a cleanup failure alone is raised |

## Verification passes

**V1** (fresh context, the whole diff again): **REQUEST_CHANGES**, five.

| id | severity | finding | resolution |
|---|---|---|---|
| VR01 | high | a Windows extended-length spelling (`\\?\C:\project\dist\icons`) kept its prefix through `realpath`, so it never matched the base and the project's junction went unchecked | first by a canonical spelling; superseded in V2 by directory identity; tested with a real junction under both spellings |
| VR02 | medium | IR04 deferred the link, not an exception from the walk itself (a file standing where a directory must be raised `NotADirectoryError` before every gate) | a file in the path ends the walk (nothing below it exists to redirect), and any other error inspecting the output is held and reported where the link is; tested beside drift |
| VR03 | medium | a plain `RuntimeError` still counted as a build's refusal | it never does: IconFlow raises it only for a renderer or session used wrongly; a review then fails as a runtime error |
| VR04 | medium | the IR10 test bounded the manifest's read request, not each payload's | each payload's request must be exactly its measured size plus one |
| VR05 | low | each component re-resolved its whole parent: quadratic on deep paths | one link check per component; below a component that is not a link its real path is its parent's plus its name (on Windows an existing component is resolved by the system once, for 8.3 names); a call-count test, which the V3 and V4 designs still pass |

**V2**: **REQUEST_CHANGES**, five — all about the walker, which had grown a
patch per spelling. It was replaced by a simpler design rather than patched
again.

| id | severity | finding | resolution |
|---|---|---|---|
| SV01 | high | the check walked the path as written while `ship` wrote its `abspath`: through a missing folder or a file plus `..` (`ghost/../dist/icons`) the two named different places, and the linked `dist` was missed | one destination: `build.output_destination` (`abspath`: `..` collapsed, a drive-relative path resolved by the OS) is what is checked *and* written; command-level tests through `--out` and the configured output (the shared `abspath` was withdrawn in V3, TV03: `ship` keeps checking the absolute path it writes, `build()` the path it is given) |
| SV02 | high | a local share spelling (`\\localhost\C$\project`) is never equal, as a string, to `C:\project` | the project is recognised by directory identity (`samefile`), not by spelling; probed on Windows with a real junction under eighteen spellings (relative, `..`, 8.3, `\\?\`, local share, drive-relative), all correct |
| SV03 | medium | a base reached through a link (`p/current` → `p`) was refused as a link | a path spelled inside the base walks only below it: the base is the caller's own |
| SV04 | medium | a drive-relative output with no link (`C:icons`) was refused outright | resolved by the operating system, then checked like any other |
| SV05 | low | the review-plan docstring and the changelog still said an internal defect can never unbind a receipt | both now name the plain-`ValueError` residual |

**V3**: **REQUEST_CHANGES**, three — again the walker. SV03–SV05 accepted.

| id | severity | finding | resolution |
|---|---|---|---|
| TV01 | high | a `subst` drive whose root *is* the project: the walk never asked whether the drive root itself was inside | the walk now *resolves* the path and asks, for every link it meets, whether the directory holding that link is inside the project — the drive root included; tested with a real `subst` drive |
| TV02 | high | an alias outside the project pointing at the project's linked `dist`: the final `realpath` landed outside and the `dist` link passed through it was never seen | links met inside another link's target are judged too: resolution expands each link and keeps walking, so `to_dist/icons` meets `project/dist` and is refused |
| TV03 | medium | SV01's `abspath` changed where a POSIX build writes: the kernel follows a link before the `..` after it (`jump/../icons`), `abspath` does not | build and the legacy writers write the path they were given, as in 0.10.0; the check resolves it as the OS will — Windows collapses `..` first, POSIX follows each link before its `..`; `ship` checks the absolute path it writes. Run on Linux too |

**V4**: **REQUEST_CHANGES**, five, narrower again; TV02 and TV03 accepted.

| id | severity | finding | resolution |
|---|---|---|---|
| FV01 | high | a `subst` drive mapped to a folder *inside* the project: the drive root's spelled parents never reach the project | "inside" is asked of a directory's real location as well as its spelling; tested with a real `subst` of `project\sub` |
| FV02 | medium | a trusted base reached through a link, then `..`: the walk stepped up from the base's spelling, the kernel from where it really is | the walk starts from the base's real location (its spelling is still not walked: SV03 holds); tested on Linux |
| FV03 | medium | the forty-link bound is Linux's; Windows follows up to 63 reparse points, so a chain it accepts was refused | the platform's own bound; a 45-junction chain is followed and a two-junction loop refused |
| FV04 | medium | the TV03 test called the check only; it would not see a writer that collapses `..` again | a Linux test runs `build()` and a legacy writer through `jump/../icons` and finds the files where the kernel puts them, none where a collapse would |
| FV05 | low | `pending.pop(0)` made the walk quadratic in the number of components again | a `deque`; the call-count test stays, and the claim is limited to it |

**V5**: **REQUEST_CHANGES**, four; FV01–FV05 accepted, and no regression in
built bytes or envelopes.

| id | severity | finding | resolution |
|---|---|---|---|
| F5-01 | high | Windows resolves a relative symlink's `..` across a *junction* differently from a symlink; a junction outside the project, then a relative symlink outside it whose `..` leads back to the project's `dist`, is not emulated | **dissent** — out of the threat model, below |
| F5-02 | high | a `subst` drive on a folder *outside* the project, with a relative symlink on it whose `..` climbs past the drive root into the project's `dist` | **dissent** — out of the threat model |
| F5-03 | high | an SMB share whose root is a folder *inside* the project (`\\localhost\p-sub`): no ancestor of the share's spelling or real path is the project | **dissent** — out of the threat model; the docstring and this record no longer claim the project is recognised "under any name", only under the names tested |
| F5-04 | low | ship's comment still said it checks before `abspath` | corrected |

**Why F5-01–F5-03 are dissents.** The check exists for one threat, stated in
`build.link_in_path` since 0.7: a link the *project* carries — a cloned
repository whose `dist` or `brand-kit` points somewhere else. Every one of
these three needs, besides such a link, something only the machine's user can
make *outside* the project — a junction plus a crafted relative symlink, a
drive mapping, a network share — arranged to route back into it. Whoever can
make those can write anywhere already. Emulating each Windows namespace rule
in a path walker grew the walker through four passes; the honest boundary is
the threat model, and the documents now state it. If such routes ever matter,
the right tool is the operating system's own answer (open the final
directory and compare its handle), not a fifth emulation.

**V6**: **REQUEST_CHANGES**, three. The F5 dissent was accepted for the
routes it named; F6-01 is a route inside the threat model, and is fixed.

| id | severity | finding | resolution |
|---|---|---|---|
| F6-01 | high | a config in a sub-folder of a repository (`repo/cfg/iconflow.toml`, `output = "../dist/icons"`) and a `dist` link the repository carries: the config's folder was taken for the whole project, so the link counted as outside | the project of a configured output is the repository holding the config (found by its `.git`), else the config's folder (`build.project_base`); a command-level test with a sibling link refused and an ordinary sibling folder shipped |
| F6-02 | medium | the `viewBox` grammar was stricter than Chromium's (`0 0 24+24` is four numbers to it) and laxer (an overflowing `1e999` origin) | a tokenizer that follows Blink's `SVGRect::Parse`; sixteen spellings (twenty-one after V7) were compared with real Chromium (`viewBox.baseVal`), all agree, and that comparison is a Chromium-gated test |
| F6-03 | low | ship's docstring still said every source is read once | it says captured once, with the validation read before it |

**V7**: **REQUEST_CHANGES**, one. The F5 dissent was judged sound within the
stated threat model; F6-01 and F6-03 accepted.

| id | severity | finding | resolution |
|---|---|---|---|
| F7-01 | medium | Blink stores `viewBox` numbers as 32-bit floats: `0 0 100000000+100000001` is square to Chromium and was reported non-square here, and `1e39` (past the float range) counted as usable | each number is rounded to a 32-bit float and refused past its range (completed in V8, F8-01); the Chromium comparison grew to twenty-one spellings, and a `check` test holds the square case |

**V8**: **REQUEST_CHANGES**, one.

| id | severity | finding | resolution |
|---|---|---|---|
| F8-01 | medium | rounding once at the end is not Blink's arithmetic: it sums the digits right to left in 32-bit floats (`199999989` becomes `200000000`), and refuses an exponent above 38 before applying it (`0.1e39`) | a line-by-line port of Blink's `GenericParseNumber` (`qa._blink_number`), every step rounded to a 32-bit float; the Chromium comparison covers thirty-one spellings, all agree; `check` tests hold both cases |

**V9**: **REQUEST_CHANGES**, one.

| id | severity | finding | resolution |
|---|---|---|---|
| F9-01 | medium | an exponent long enough to overflow to `-inf` while it is summed raised `OverflowError` at an integer conversion Blink does not make; Chromium reads the value as `0 0 24 24` | the power is taken on the float itself, as `std::pow` is (`10 ** -inf` is 0); added to the Chromium comparison (thirty-two spellings) and the `check` tests. To stop finding spellings one at a time: a seeded comparison of four hundred random spellings against Chromium (Chromium-gated; five hundred agreed in a one-off run), and a fuzz test that the parser never raises |

**V10**: **APPROVE** — F9-01 closed, no regression and no document
claiming more than the code, no accepted finding or dissent reopened.

The final design, in `build.output_link`: resolve the output path the way
the operating system will for the writer; refuse at the first link whose
directory is inside the project (by directory identity, of its spelling and
of its real location); follow every other link, within the platform's own
bound. Each accepted finding of V1–V4 is a case of this one rule, and each
has a test.

## New: the map and its guard

- **`docs/ARCHITECTURE.md`** — the module layers, one icon from source to
  shipped files, the invariants a change must keep, the touch points of a new
  target, and the seams kept visible on purpose.
- **`tests/test_architecture.py`** — the layer table is checked, not
  described: every top-level import points down it, and the six upward
  imports (all function-level) are named in the document and the test.
- **`docs/README.md`** — every document, grouped by the question it answers;
  a test fails when a document is added without an entry (three had no
  inbound link at all).

## Not done, on purpose

From Codex's list of refactors not to do in a wrap-up, all adopted:

- Splitting `cli.py` by command: it would move the ship state machine, error
  translation and presentation at once. It needs characterization tests of
  the projections first.
- A target registry or plugin layer: indirection that could change canonical
  order or what `all` means.
- Collapsing the source sets (plan-consumed, approval-bound, review-shown,
  audit-measured) into one rule: their differences include compatibility
  commitments, the tray binding above among them.
- The exit-code taxonomy behind PF07.

## Verification

- Byte identity, re-measured after every pass: 112 built files across seven configurations (all app
  targets with a linked tray; web+android with a linked maskable; emote; the
  detail ladder with Electron radius and Windows tiles; ios+web on a
  declared preset; ios system variants; dark scheme with the tray module)
  built by a `v0.10.0` checkout and by this tree under real Chromium on
  Windows: identical.
- Each new regression test was run against the pre-fix code and fails there
  (PF01, PF02, PO01 shown explicitly).
- `ruff check`, the full suite on Python 3.14 and 3.10 (710 tests), and the
  Chromium-gated suites (`ICONFLOW_BROWSER_TESTS=1`) under real Chromium;
  the POSIX-only tests in a Linux container; real Windows junctions and a
  real `subst` drive for the output check; `iconflow demo` end to end.

## Owner decisions

1. **Release 0.10.1** — a patch release of these fixes, when the owner says
   so. Nothing in it changes a built file; PF02, PF03 and PF10 change what is
   refused or reported.
