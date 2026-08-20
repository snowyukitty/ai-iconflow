# Site internationalization plan — five languages

> Status: planned 2026-08-21 for the session after the v0.5 checkpoint. Nothing
> here is built yet. Languages, in the owner's order: English (source),
> Spanish, Japanese, Traditional Chinese, Simplified Chinese.

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

1. **Phase A (one session):** build script + catalogs + tests; ship `zh-Hant`
   and `ja` for `/`, `/getting-started/`, `/how-icons-are-made/`, `/archive/`
   (UI chrome), 404.
2. **Phase B:** `es` and `zh-Hans` for the same pages; gallery/matrix chrome.
3. **Phase C:** archive readings and Theme World copy; per-language social
   previews if wanted (text on the image is English today).

## Open decisions for the owner

- Whether `/zh-hant/` should be the default for Taiwan/Hong Kong visitors via
  a hint banner (no redirect) — the plan says hint only.
- Whether the archive's 137 readings are worth translating (Phase C) or stay
  English as "source notes".
