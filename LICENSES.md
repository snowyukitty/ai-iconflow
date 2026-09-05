# Licensing

IconFlow is one repository holding four different kinds of work, and they are
not licensed the same way. This file is the authoritative map. Where a
directory carries its own `LICENSE` file, that file governs the directory.

---

## 1. The icons you make with IconFlow are yours

**This comes first because it is the part that matters most to you.**

Every icon, favicon, logo, mark, tray asset, manifest, `.ico`, `.icns`, `.png`,
head snippet, `master.svg`, `tray.svg`, `iconflow.toml`, review receipt, and
case file **you** create by running IconFlow is **your work**. IconFlow's
maintainer claims no ownership in it and imposes no conditions on it.

Specifically, for your own output:

- **No attribution required.** You never have to credit IconFlow in your app,
  your website, your app store listing, or anywhere else. Say so if you like —
  we would enjoy it — but nothing requires it.
- **Commercial use is unrestricted.** Ship it, sell it, trademark it, put it on
  the App Store.
- **No copyleft, no share-alike, no viral terms.** Nothing in this repository
  reaches through IconFlow into the thing you designed.
- **No registration, no key, no account, no telemetry.** IconFlow runs locally
  and never phones home.

This holds even though parts of this repository are licensed restrictively. The
restrictive parts cover **IconFlow's own finished artwork and its written
methodology** — not your work, and not the output of the tool.

And a catch-all, so this does not depend on having enumerated every file:
**to the extent any copyrightable IconFlow boilerplate ends up embodied in
something IconFlow generates for you** — a manifest, a head snippet, the tray
TypeScript module, the Review Lab HTML and the tool code inside it, a receipt,
a case skeleton — **those portions are supplied to you under CC0 1.0**. There
is no path by which the toolkit's own code or wording attaches a condition to
an artifact it produced for you.

What this section does not do is promise something no license can. It does not
guarantee your icon is copyrightable, that it is registrable as a trademark, or
that it does not resemble someone else's mark. Those are yours to check — the
design procedure's cliché filter and distinctiveness gate help, but they are not
a clearance search.

Two mechanisms keep the rest true rather than merely promised:

1. Every file IconFlow copies or generates *into your project* — the technique
   scaffolds behind `iconflow new`, the `iconflow.toml` from `iconflow init`,
   the case skeleton from `iconflow case new` — is dedicated to the public
   domain under **CC0 1.0** (Tier 1b below). A public-domain starting point
   cannot make your finished logo a derivative work of anything. `iconflow new`
   also *strips* the licence header from the copy it writes, because that
   header would otherwise ride `master.svg` into the `favicon.svg` you serve —
   an IconFlow URL in your production asset is exactly the attribution this
   section promises never to require. It tells you on the terminal instead.
   `tests/test_licensing.py` fails the build if either guarantee regresses.
2. **Using a method is not copying its description.** Copyright protects the
   *expression* in `docs/DESIGN_PLAYBOOK.md`, not the ideas, procedures, or
   design rules it describes. Reading the playbook and then drawing an icon
   creates no obligation to anyone. The ShareAlike term in Tier 2 applies to
   someone republishing IconFlow's *prose*, not to someone applying its advice.

The single exception is described in §6: `iconflow demo` deliberately copies
**IconFlow's own product mark** into a directory so you can watch the engine
prove itself. That one family is IconFlow's identity, not a starting point.

---

## 2. The tier map

| Tier | What | Paths | License |
|---|---|---|---|
| **0** | **Your output** | anything you design or build with IconFlow | **Yours.** No conditions — see §1 |
| **1** | The tool | `iconflow/`, `scripts/`, `tests/`, `.github/`, `website/**` (`.html`, `.css`, `.js`, `.json`), packaging files | `Apache-2.0` |
| **1b** | Starting points | `templates/**` (including `templates/presets/`), `iconflow/resources/collision/` (the plain generic forms and their index), files IconFlow writes into your project | `CC0-1.0` |
| **2** | The methodology | `docs/**/*.md`, `casebook/**`, `skills/**`, `AGENTS.md`, `CONTRIBUTING.md` | `CC-BY-SA-4.0` |
| **3a** | Brand & packaged imagery | `brand/`, `demo/`, `docs/assets/` | `CC-BY-4.0` + [trademark](TRADEMARKS.md) |
| **3b** | The published corpus | `showcase/`, `gallery/`, `examples/*/`, `website/assets/` | `CC-BY-NC-ND-4.0` |

Full texts live in [`licenses/`](licenses/). `LICENSE` at the repository root is
the Apache-2.0 text, kept there because it governs the code and because tooling
expects it — which also means GitHub's sidebar will say "Apache-2.0" for the
whole repository. It is showing Tier 1. This file is the accurate answer.

**Anything not listed above is Tier 1, `Apache-2.0`.** That includes `README.md`,
`CHANGELOG.md`, `SECURITY.md`, and the packaging metadata. If a path is
genuinely ambiguous, open an issue rather than guessing.

### Tier 1 — the tool, `Apache-2.0`

The engine should spread. Apache-2.0 is permissive, carries an explicit patent
grant, and is what the packaged `iconflow` distribution is built from. Fork
it, embed it, sell a product built on it. You must keep the license and the
[`NOTICE`](NOTICE) with the *code* you redistribute — that obligation is on a
redistributor of IconFlow, never on a user of its output.

### Tier 1b — starting points, `CC0-1.0`

The twenty technique scaffolds, the plain generic forms of the collision set
(a gear, a bell, a folder — nobody's icon set, drawn only to be measured
against), and every file IconFlow generates into your project are dedicated
to the public domain. This is deliberate and it is the
load-bearing part of §1: if the scaffolds were Apache-2.0, an icon you evolved
from `iconflow new flat-geometric` would technically be a derivative work
owing attribution and a license copy. CC0 removes that entirely. Take the
scaffold, change it beyond recognition or barely at all, ship it, claim it.

### Tier 2 — the methodology, `CC-BY-SA-4.0`

The playbook, the concepting rules, the six-axis rubric, the distilled
`LEARNINGS`, the casebook, and the agent skill are the part of IconFlow that
took the longest to earn. They stay open — read them, quote them, translate
them, teach from them — but **a work that reuses this prose must credit
IconFlow and carry the same license**. You cannot lift `DESIGN_PLAYBOOK.md`
into a closed commercial product's documentation and call it your own.

Again: this binds *republication of the text*. It does not bind icons designed
by someone who read it.

### Tier 3a — brand and packaged imagery, `CC-BY-4.0` + trademark

The Petal / Balloon / Canopy Haypile masters and the documentation imagery ship
**inside the `iconflow` package**, because `iconflow demo` has to carry a
real reviewed family and the playbook is not useful without its images.
Attribution-only, deliberately: a noncommercial or no-derivatives term on
anything in the package would make the whole distribution non-free —
unpackageable by Linux distributions, blocked by many corporate legal reviews —
and would cost IconFlow the adoption it exists for.

It costs almost nothing to give up, because copyright is the wrong instrument
for what is actually being protected here. What stops someone adopting Petal
Haypile as their product's identity is [`TRADEMARKS.md`](TRADEMARKS.md), and a
trademark is not licensed by Apache-2.0 §6 or by any Creative Commons license.
That protection is unchanged.

### Tier 3b — the published corpus, `CC-BY-NC-ND-4.0`

The 137 Living Archive studies, the gallery, the showcase, and the worked
example families are **finished artwork**, published as evidence of what the
method produces. They are not stock assets and not a free icon pack: no
commercial use, no derivatives, attribution required. None of this ships in the
package, so keeping it restrictive costs the tool nothing.

---

## 3. Reusing the documentation IconFlow exported into your project

`iconflow docs --out DIR` writes Tier 2 material into a directory you chose, so
you can read the playbook without a checkout. Those are **reference copies**,
still `CC-BY-SA-4.0`, and each carries an SPDX header saying so.

Keep them out of version control — the agent procedure tells agents to export
into a gitignored `work/<slug>/docs`. Committing them to a public repository is
redistribution, and ShareAlike then applies to that copy. Nothing about this
touches the icon you designed.

## 4. Your casebook is yours

Tier 2 covers **IconFlow's** `casebook/` in this repository. The case files
*you* write in *your* project are Tier 0: your text, your evidence, your
license. The skeleton `iconflow case new` writes is CC0 (Tier 1b), so the case
you fill in carries no inherited terms.

If you contribute a case back to this repository, you license that contribution
under Tier 2 — see §8. The `examples/community-case/` fixture is carved out of
Tier 3 to **CC0**, because it exists precisely to be copied and adapted; a
no-derivatives term on a template would be a contradiction.

## 5. The Remix Lab

The browser [Remix Lab](https://ai-iconflow.com/#remix) bends three IconFlow
masters and hands you the SVG. Those masters are IconFlow's actual product
mark, so the remix stays **Tier 3a, `CC-BY-4.0`**: use it, change it, sell
something built on it — credit IconFlow. Derivatives are explicitly allowed,
which is what makes the lab honest; a no-derivatives term on something you were
invited to remix would not be.

It is deliberately **not** CC0. A CC0 grant on output derived from the official
mark would make a barely-modified IconFlow logo unconditionally reusable by
anyone, which is not a thing the lab should hand out.

Two consequences worth stating plainly:

- The lab is a **study surface** — a way to feel how the geometry behaves at
  16px — not a way to obtain a logo. **If you want a mark that is yours with no
  conditions at all, start from `iconflow new`**: the scaffolds are CC0 and
  §1 applies in full.
- However far you bend it, adopting IconFlow's identity — an unmodified Petal
  Haypile, or a mark confusingly similar to it, as *your* product's identity —
  is a trademark question that no copyright license answers.

## 6. `iconflow demo` copies IconFlow's own mark

`iconflow demo --out DIR` materializes the **Petal Haypile brand family** —
IconFlow's real product mark — and ships it against a real receipt. That is the
point: it proves the engine end to end with a design that genuinely passed the
gate. It is **not** a starting point for your icon.

That directory is Tier 3 and gets a `LICENSE-NOTICE.md` saying so. To start
your own design, use `iconflow init` and `iconflow new <preset>` (Tier 1b), or
follow the full procedure in the agent skill.

## 7. Redistributing IconFlow itself

Packaging IconFlow for a distribution? The published wheel is not
single-licensed and its `License-Expression` says so:
`Apache-2.0 AND CC0-1.0 AND CC-BY-SA-4.0 AND CC-BY-4.0`. It carries the engine,
the CC0 scaffolds, the CC BY-SA reference documents that `iconflow docs` serves,
and the CC BY imagery under `iconflow/resources/demo/` and
`iconflow/resources/docs/assets/`.

**Every one of those is a free license, and that is on purpose.** Nothing
noncommercial or no-derivatives is packaged, so the distribution is free to
redistribute and modify in full. The restrictively licensed material — Tier 3b,
the archive, gallery, showcase, and examples — lives only in the source
repository and never in the package. If you are auditing: `AND` here means the
distribution contains material under each of those licenses, not that every file
is under all of them.

## 8. Contributions

By opening a pull request you do two things: certify the
[Developer Certificate of Origin](https://developercertificate.org/) with a
`Signed-off-by:` line (`git commit -s`), and sign [`CLA.md`](CLA.md).

You keep your copyright — the CLA is a license, not an assignment. It grants
the right to **relicense**, which exists so that IconFlow's licensing is not
frozen permanently by its first outside contribution. Your contribution lands
under the tier that governs the files you touched. See
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## 9. Machine-readable

`iconflow license` prints this map and the §1 guarantee, so an agent working in
your repository can answer "may I ship this commercially?" without guessing.
[`docs/PROVENANCE.md`](docs/PROVENANCE.md) records how IconFlow's authorship is
established and verified.

## 10. Questions this file does not answer

This is a summary written by the maintainer, not legal advice, and the license
texts in [`licenses/`](licenses/) govern where they differ from this summary.
For a use that does not fit any tier, open an issue and describe it.
