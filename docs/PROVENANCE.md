<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Provenance

How IconFlow's authorship is established, and how to check whether something
elsewhere was copied from it. This exists because the useful question is rarely
"can copying be prevented" — it cannot — but "can copying be *shown*".

None of this applies to icons made **with** IconFlow. Those are the user's own
work and carry no IconFlow provenance obligation at all; see
[`LICENSES.md`](../LICENSES.md) §1.

## 1. The record

Half of the useful record is *third-party* — dated by someone other than the
maintainer — and a private repository has none of it. This table is split
honestly, because a provenance document that lists records it does not have is
worse than one that admits the gap.

**Exists today**

| Evidence | What it fixes |
|---|---|
| Git history in this repository | Per-file authorship and dates from 2026-06-23 onward. Maintainer-controlled: commit dates can be rewritten, so this is weak on its own until a public mirror exists |
| `casebook/` | Dated design decisions, scores, and failed passes per icon |
| `website/assets/archive/catalog.json` | The 137 identity studies, their round, status, and reading |
| `ai-iconflow.com` | Published pages, dated by third-party crawls and archives |

**Created at publication — not yet in place**

| Evidence | What it will fix |
|---|---|
| Software Heritage archive | A permanent third-party copy with stable SWHIDs, and the first clock the maintainer does not control |
| Zenodo DOI on the first Release | A citable, dated authorship record outside GitHub |
| GitHub Releases with checksums | The exact bytes of each published artifact |
| Signed release tags | That a release came from the maintainer |
| PyPI release history | Independent third-party timestamps of each version |

Standing those up belongs in the same change that makes the repository public
(`docs/LAUNCH_READINESS.md`), not later: their value is the date they record,
and a record created after a dispute starts is worth very little.

The casebook and the Living Archive are the strongest evidence available today
and the hardest to fake: they record not just finished work but the *rejected*
passes, the scores before and after, and what failed first. A copy has the
outputs without the history that produced them.

## 2. Fingerprints

IconFlow's methodology introduced vocabulary that does not appear in general
icon-design writing. These are not secrets — they are published, and using the
*ideas* is free. But the specific coinages travel with copied text, and their
first appearance here is dated:

| Term | First committed |
|---|---|
| the monogram trap | 2026-07-21 |
| name-the-thing test | 2026-07-21 |
| signature device (as a required, named, single element) | 2026-07-21 |
| cliché filter | 2026-07-21 |
| proof cell | 2026-08-12 |
| Haypile (Petal / Balloon / Canopy) | 2026-08-14 |
| Living Archive (as the 137-direction exploration record) | 2026-08-21 |

Alongside them, the six-axis rubric (legibility, distinctiveness, balance,
color, scalability, craft) with a 4/5 floor and distinctiveness as a hard gate,
and the *source-bound review receipt* binding a human decision to a source hash
plus a contract hash, are structural signatures of this project.

Regenerate this table after adding a coinage:

```bash
git log --diff-filter=A --format=%cI -S"<term>" --reverse -- . | head -1
```

## 3. Asset provenance

Every SVG in the published corpus under `website/assets/archive/` carries an
RDF `<metadata>` block naming the work, its author, its license, and its
canonical URL. `scripts/build_archive.py` writes it, and `--verify-only` fails
if it is missing, so it cannot quietly fall out of the pipeline.

Two outcomes, both useful:

- the metadata survives in a copy → the copy is self-identifying;
- the metadata was stripped → stripping an attribution notice is a deliberate
  act, and evidence of one.

The technique scaffolds in `templates/presets/` carry the opposite marker: a
CC0 dedication saying the file is public domain and that anything designed from
it is unencumbered. That header is there to *reassure* a user, not to bind one.

## 3b. Code provenance, and what Apache-2.0 actually requires

The engine is Apache-2.0, which **permits** someone to take the code, modify it,
and ship the result in a closed commercial product. That is the license working
as designed, not a loophole, and no amount of metadata changes it. Saying so
plainly matters, because the useful question is the narrower one: what does that
person still owe, and how would anyone know if they skipped it?

Apache-2.0 §4 obliges a redistributor of the code — modified or not — to:

- **§4(a)** give recipients a copy of the license;
- **§4(b)** carry prominent notices stating that they changed the files;
- **§4(c)** retain every copyright, patent, trademark, and attribution notice in
  the source they took; and
- **§4(d)** reproduce the contents of `NOTICE` in their distribution.

In practice, a fork produced by pointing an agent at this repository and asking
it to "modify this into our product" strips all four. **That is the enforceable
failure** — not the copying itself. So the whole design here is to make those
notices travel, and their absence obvious:

- Every `.py` file carries `SPDX-License-Identifier: Apache-2.0` and a
  copyright line. `NOTICE` does not travel with an individual file; a header
  does. `tests/test_licensing.py` fails the build if one is missing.
- `NOTICE` is substantive rather than three lines, so §4(d) forces real
  attribution into any compliant redistribution.
- The stable warning and gate codes are distinctive strings that survive
  "appropriate modification" because they are part of the contract, not the
  prose: `receipt-stale-source`, `receipt-stale-contract`, `receipt-not-ready`,
  `score-below-floor`, `qa-warnings`, `stroke-floor`, `coverage-16`,
  `maskable-detail`, `distinctiveness-text`, `tray-template-featureless`.
- So is the receipt schema pairing `source_sha256` with `contract_sha256`, and
  the six axis names with a 4/5 floor.

### The asymmetry worth knowing

A code fork can take the engine. It **cannot** legally take what makes the
engine worth using:

| What a fork wants | Tier | Can they? |
|---|---|---|
| The rendering and packing engine | Apache-2.0 | Yes — that is the deal |
| `docs/` — playbook, concepting, rubric | CC-BY-SA-4.0 | Only by publishing their version under the same license, with credit |
| `casebook/` — the accumulated evidence | CC-BY-SA-4.0 | Same |
| The 137 archive studies, gallery, showcase | CC-BY-NC-ND-4.0 | No, not commercially |
| The name IconFlow | trademark | No |

A ripoff therefore ships the mechanism without the method: no playbook, no
distilled `LEARNINGS`, no casebook, no proof corpus. If it ships those too, the
infringement is of the licensed prose and is provable by §2 and §4 below. And it
gets a snapshot, not the loop — the casebook keeps producing rules the fork does
not have.

This is the honest shape of the protection. It is not "you cannot copy this". It
is "copying the easy part gets you the part that was never the hard part".

## 4. Checking a suspected copy

1. **Text.** Search the suspect work for the §2 coinages, and for whole phrases
   from `docs/DESIGN_PLAYBOOK.md` and `docs/CONCEPTING.md`. Independent
   arrival at "the monogram trap" plus "name-the-thing test" plus a six-axis
   rubric with those six axis names is not plausible.
2. **Artwork.** Check the SVG source for the §3 metadata block. Compare path
   data — IconFlow's masters are hand-authored on a 1024 grid with named
   `id`s (`iconflow-background`, `iconflow-mark`), which survive copying.
2b. **Code.** Search the suspect distribution for the §3b warning and gate
   codes, for `SPDX-FileCopyrightText: 2026 snowyukitty`, and for a `NOTICE`
   file. Finding the codes but no notices is the Apache-2.0 §4 failure, and it
   is the strongest position available: they relied on the license, and did not
   keep its one condition. Finding neither may simply mean an independent
   implementation, which is permitted and expected.
3. **Structure.** A `master-review.json` receipt shape, a
   `source_sha256` + `contract_sha256` pair, or the `iconflow.toml` schema
   indicates the *engine* was used — which is what Apache-2.0 permits, and what
   thousands of legitimate users will produce. Treat this as identifying the
   toolchain, never as evidence of wrongdoing. The same caution applies to a
   case file using `signature_device`: that is a user following the procedure.
4. **Date.** Establish the suspect's earliest public date and compare it with
   the git, PyPI, Software Heritage, and Zenodo records in §1.

## 5. What this cannot do

Stated plainly, because a protection document that oversells itself is worse
than none:

- It cannot stop a public repository from being cloned, read, or ingested.
- It cannot stop a model that already trained on this corpus from reproducing
  its ideas — and ideas were never protected anyway.
- It cannot detect paraphrase. Someone who reads the playbook and rewrites the
  method in their own words has done something copyright permits.
- Fingerprints prove copying of *expression*; they do not prove damages, and
  they are not self-enforcing.
- Publishing the fingerprint list means a careful copier can paraphrase around
  it. That is an accepted trade: these are litigable phrases, not secret
  watermarks, and a term nobody can point to is a term nobody can rely on. It
  does mean the registry catches careless copying, not determined copying.
- Several of the §2 coinages are weaker than others. "signature device" and
  "Living Archive" are ordinary enough that independent arrival is plausible;
  the strength is in the *combination* — the monogram trap, the name-the-thing
  test, and those six axis names together.

What it does do is remove the "we came up with it independently" defence for a
verbatim or near-verbatim copy, and make the date of authorship a matter of
third-party record rather than assertion.

## 6. If you find a copy

Open an issue, or use the private contact route in
[`SECURITY.md`](../SECURITY.md) if the matter is sensitive. Bring the URL, a
snapshot, and which §4 checks matched. Most cases are an honest reuse that
simply needs attribution added, and asking is the first step.
