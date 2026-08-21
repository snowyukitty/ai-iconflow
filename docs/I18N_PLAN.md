<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Site internationalization plan — five languages

> Status: **Phases A and B are built and deployed (2026-08-21).** All four
> target languages ship for `/`, `/getting-started/`, `/how-icons-are-made/`,
> `/archive/` chrome, and the 404 page. Phase C (the 137 archive readings, the
> gallery collections, per-language social previews) is still open. Languages,
> in the owner's order: English (source), Spanish, Japanese, Traditional
> Chinese, Simplified Chinese.
>
> What shipped, and where it differs from the plan below, is recorded in
> "Phasing" and "What actually happened" at the end of this document.

## Goals and non-goals

- Goal: every public page of `website/` readable in `en`, `es`, `ja`, `zh-Hant`,
  `zh-Hans`, with the same design, the same proofs, and honest copy in each
  language. Translation covers **prose**; the evidence (SVGs, PNG proofs,
  receipts, catalog JSON, code blocks, command lines, file names, rubric axis
  identifiers) stays untranslated because it is what ships.
- Non-goals: translating the toolkit CLI/docs in the repository (English is
  the project language per `AGENTS.md`); machine-translating the 137-entry
  archive readings or the 100 gallery cases on day one (see "phasing").

## URL and routing contract

- English stays at the root: `/`, `/archive/`, `/getting-started/`, ….
- Other languages live under a BCP-47 prefix: `/es/`, `/ja/`, `/zh-hant/`,
  `/zh-hans/` (lower-case in the path; `lang` attributes keep the canonical
  casing `zh-Hant` / `zh-Hans`).
- Every page carries a complete `hreflang` set (`en`, `es`, `ja`, `zh-Hant`,
  `zh-Hans`, `x-default` → English) in `<link rel="alternate">` and in
  `sitemap.xml`; `rel=canonical` points at the page's own language URL.
- `_headers` revalidation stanzas and `_redirects` are extended per prefix;
  `functions/_middleware.js` keeps redirecting legacy hosts with the path
  preserved (already path-preserving).
- A small language switcher in the header and footer (links, not JS
  detection). No automatic redirect by `Accept-Language`; at most a one-line
  "This page is available in …" hint driven by the static `hreflang` list.

## Build approach (static, dependency-free, CSP-safe)

1. Keep `website/` as the English source of truth.
2. Add `scripts/build_i18n.py`:
   - extracts translatable strings from the English pages into
     `website/i18n/en.json` keyed by a stable id (data attribute or a
     deterministic hash of the English string plus page/section);
   - reads `website/i18n/<lang>.json` and renders `website/<lang>/...` by
     substituting text nodes and attributes (`alt`, `aria-label`, `title`,
     `content` of description/og tags), rewriting root-relative links that
     point at HTML routes to the language prefix, and setting `<html lang>`;
   - leaves assets, JSON, code, and the generated archive/gallery blocks
     untouched except for their UI chrome strings;
   - fails closed on a missing key (no silent English fallback in a
     translated page; the build lists untranslated keys instead).
3. The archive and gallery generators (`build_archive.py`, `build_gallery.py`,
   emoji matrix scripts) gain a `--lang` pass that translates only their UI
   chrome (headings, filters, status labels) from the same catalogs; entry
   readings stay English until a later phase.
4. Fonts: system stacks only — extend `--sans` with `"Noto Sans JP"`,
   `"Hiragino Sans"`, `"Yu Gothic"`, `"PingFang TC"`, `"Microsoft JhengHei"`,
   `"PingFang SC"`, `"Microsoft YaHei"`, `"Noto Sans CJK"` per `:lang()` rules;
   no Google Fonts (CSP). Check line-height and letter-spacing for CJK headings
   (the display type uses negative tracking that CJK must not inherit).
5. Tests (`tests/test_website.py`): every translated page has the full
   `hreflang` set, correct `lang`, no untranslated-key markers, no inline
   styles/scripts, all local references resolving, and the same structured
   data types as its English twin; sitemap contains every language URL.

## Translation process

- Division of labour (owner's choice): drafts come from three delegated
  models through ATD — Codex (`gpt-5.6-luna` when the route lists it, else
  report and use `gpt-5.6-sol`), Antigravity (`gemini-3.7-flash-high`), and
  Grok (`grok-4.6`, `xhigh`) — each producing a complete catalog for an
  assigned language pair; the session agent (Claude) reviews every draft
  against the glossary and the English source, merges, and owns the final
  catalogs. No draft ships unreviewed.
- Agents draft each language from the English source with a glossary
  (`website/i18n/GLOSSARY.md`): product terms that stay English (IconFlow,
  Remix Lab, receipt → keep plus a gloss, `check`/`review`/`ship` commands),
  rubric axes (translate once, reuse everywhere), and the brand mark names
  (Petal Haypile etc. stay as names, with a short gloss on first use).
- Traditional and Simplified Chinese are written separately, not converted
  mechanically (terminology differs: 圖示/图标, 檔案/文件, 介面/界面, …).
- Review: one native-quality pass per language by an independent agent route
  through ATD (analysis kind, files artifact = the language JSON + the English
  source) before deploy; the owner spot-checks zh-Hant.
- Honesty rules carry over: no invented claims, the same "temporary mark",
  "not on PyPI yet", and clean-room wording in every language.

## Phasing

1. **Phase A — done.** Build script + catalogs + tests; `zh-Hant` and `ja` for
   `/`, `/getting-started/`, `/how-icons-are-made/`, `/archive/` (UI chrome),
   404.
2. **Phase B — done in the same session.** `es` and `zh-Hans` for the same
   pages. The gallery/matrix chrome was *not* included: those pages are
   generated by three other scripts with their own catalogs, and translated
   pages link to them at their English URL on purpose.
3. **Phase C — open.** The 137 archive readings and the finalist strip, the
   gallery collections (`/gallery/`, social signals, emoji matrix), and
   per-language social previews (the text on the image is English today).

## What actually happened

- **Keys.** `slug.sha1(text)[:8]`, global across pages, so shared chrome is
  translated once and an English copy edit retires its old translations
  instead of leaving a stale one behind. 707 strings on five pages.
- **Inline markup survives translation.** A sentence with a `<code>` or an
  `<a>` inside it stays one translatable string; the markup is handed to the
  translator as numbered placeholders (`<0>…</0>`, `<3/>`) and rebuilt
  afterwards. Commands inside `<code>` are atomic and cannot be edited.
- **Copy that lived in scripts had to move first.** `app.js`, `archive.js`,
  `playground.js` and one CSS `content:` rule carried visitor-facing English;
  it now lives in `data-label-*` attributes with the English as the fallback.
- **ATD delegates are read-only.** They cannot write a file in the workspace,
  so the drafts came back as JSON in the deliverable, in six chunks per
  language (`work/make_chunks.py` → `work/merge_drafts.py`). The codex route
  listed only `gpt-5.6-sol` on the day, not `gpt-5.6-luna`.
- **Division of labour, as decided:** ja and es drafted by codex
  (`gpt-5.6-sol`, xhigh), zh-Hant by grok (`grok-4.6`, xhigh), zh-Hans by
  Antigravity (`gemini-3.7-flash-high`). Every string was then reviewed
  against the glossary and the English source by the session agent, which
  merged, corrected, and owns the final catalogs.
- **Typography.** System CJK faces only (`font-src 'self'` forbids a webfont),
  the Latin display tracking is reset per `:lang()`, and below 560px the
  wordmark gives way to the five-language switcher.

## The four-model benchmark (2026-08-21)

The first round gave each language to a different model, so "which model
translates best" was unanswerable — the languages differed as much as the
models. A controlled run settled it: **111 curated zh-Hant strings, one shared
prompt, four models, candidates shuffled per string** and the mapping withheld
until the picks were recorded (`work/bench_build.py`, `work/bench_score.py`).
The set is not a random sample; it stresses six things on purpose — strings
that already broke once, display headlines, interface micro-copy, the honesty
disclaimers, dense technical prose, and placeholder-heavy markup.

| | delivered | machine defects | glossary | wall clock | blind wins | severe |
|---|---|---|---|---|---|---|
| codex `gpt-5.6-luna` xhigh | 111/111 | 0 | 94% | 10.1 min | 21.7 | 10 |
| `grok-4.6` xhigh | 111/111 | 0 | 94% | 11.8 min | 21.3 | 6 |
| `gemini-3.7-flash-high` | 111/111 | 0 | 95% | 2.3 min | 20.3 | 5 |
| `claude-sonnet-4-6` | 111/111 | 1 | 91% | ~25 min | 9.7 | 16 |

What it established:

- **The machine gate separates nobody.** Across ~450 translated strings not one
  model broke a placeholder, dropped a runtime token, or translated a command.
  Every defect worth finding was semantic, which is why the reviewer is the
  gate and the build check is only the floor.
- **The top three are a tie with different shapes.** luna writes the best
  display copy and technical prose but walks into terminology traps; grok wins
  the traps and the micro-copy and loses the long paragraphs; gemini never wins
  a category and never collapses in one, at a quarter of the wall clock.
- **The benchmark found defects in what had already shipped.** Four renderings
  side by side exposed what string-by-string review cannot: the zh-Hant catalog
  carried two words for "render", two for "hash", two for "digest", a
  "fail-closed" that did not match the glossary, and later a "brief" split
  between 設計說明 and 簡報. All unified; 35 strings adopted a better rendering,
  including two real meaning fixes ("third-party marks" as 標誌 where trademark
  law means 商標; "live `<text>` glyphs" as 即時 where it means 未轉外框).
- **Two rules came out of it and are now enforced.** `EVIDENCE` in
  `build_i18n.py` fails the build when a translation drops a name the visitor
  types or verifies — it caught a Spanish `meta description` that had
  compressed out "Chromium" and "1024". And `--status` parses the terminology
  table straight out of `GLOSSARY.md` and reports adherence per language, so a
  term splitting in two shows up as a number instead of waiting for a reader.

Caveats worth keeping: one language, one reviewer, 111 strings; and Sonnet ran
through a different harness — ATD cannot route Claude models through `agy`
because that provider rejects `--effort` for them, so it ran against the raw
CLI in a sealed directory with the same task and inputs but without ATD's
contract envelope. Discount its number somewhat; do not discount it to a tie.

## Delegation facts worth not rediscovering

- `atd models list --target codex:default` reports the route's advertised
  model, **not** what the CLI accepts. `gpt-5.6-luna` routes fine even though
  the listing shows only `gpt-5.6-sol`. Check with `--dry-run`, not the listing.
- ATD delegates run **read-only** (`action_authorized: false`): they cannot
  write a file in the workspace, so a large deliverable has to come back as
  JSON in the response, in chunks.
- `agy` refuses `--effort` for `claude-sonnet-4-6` and
  `claude-opus-4-6-thinking`, and ATD always sends one, so those models cannot
  be reached through ATD on this machine.

## Decisions taken (small, by the session agent)

- **No hint banner and no `Accept-Language` redirect.** Language selection is
  by link only, so a shared URL always shows the same page. The switcher sits
  in the header and the footer of every page in every language.
- **`/gallery/` stays English** in this phase, and translated pages link to it
  at its English URL rather than 404 on a prefixed one.

## Open decisions for the owner

- Whether `/zh-hant/` should be surfaced to Taiwan/Hong Kong visitors by a
  one-line hint banner driven by the static `hreflang` list. Not built: the
  switcher covers discovery, and a banner is a visible change to every page.
- Whether the archive's 137 readings are worth translating (Phase C) or stay
  English as "source notes".
