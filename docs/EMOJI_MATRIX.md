# Emoji 20 × 20 Matrix

The Emoji Matrix rebuilds 20 frequently used emoji meanings through all 20
IconFlow construction grammars. The complete cross product contains 400
original clean-room SVG practice specimens.

This collection is published separately from the 100-case IconFlow Gallery and
is explicitly labeled practice work rather than shipped identities.

## Status

- Research snapshot: 2026-08-12
- Public route: `/gallery/emoji-matrix/`
- Complete comparison route: `/gallery/emoji-matrix/all/`
- Public catalog: `/assets/gallery/emoji-matrix/catalog.json`
- Meanings: exactly 20
- Styles: exactly 20
- Cells: 400 generated, 400 visually reviewed, 400 admitted, 0 rejected
- Classification: source-bound practice specimens

## Ranking method

The primary order follows the Unicode Consortium's Emoji Frequency table. That
table uses median relative frequency across available sources and filters
gender and skin-tone variants. Brandwatch's analysis of global online use from
2025-01-01 through 2025-06-30 is used as a recent cross-platform relevance
check, not as a replacement ranking because it publishes only a top ten.

Sources:

- [Unicode Emoji Frequency](https://www.unicode.org/emoji/frequency.html)
- [Unicode Emoji, UTS #51](https://www.unicode.org/reports/tr51/)
- [Brandwatch: The Most Popular Emojis of 2025](https://www.brandwatch.com/blog/the-most-popular-emojis/)
- [Unicode CLDR JSON](https://github.com/unicode-org/cldr-json)

Normalization:

1. Preserve Unicode's visual row order and within-row order.
2. Collapse skin-tone variants into the base semantic meaning.
3. Collapse text/emoji presentation sequences into one meaning.
4. Collapse `U+2665 U+FE0F` into the already-selected red-heart meaning.
5. Stop at exactly 20 distinct meanings.

Code points and CLDR English short names are semantic labels only.

## Artwork boundary

No Apple, Google, Microsoft, Samsung, Meta, Twemoji, Noto, or other vendor
emoji artwork is copied, modified, traced, sampled, or embedded. Every source
is editable SVG geometry authored for this study.

A style must change construction grammar or topology. A new palette, gradient,
texture, or stroke color by itself does not constitute a distinct style.

## Evidence contract

Every cell includes:

- editable `master.svg` with `viewBox="0 0 1024 1024"`;
- clean `iconflow check` output, independently re-run during integration;
- exact 16×16 and 128×128 PNGs;
- a 128×128 silhouette proof;
- a source-bound receipt labeled `practice`;
- six review scores at 4/5 or higher;
- stable ID in the form `u1f602--woodcut`.

The 20 original-resolution contact sheets contain 20 cells each. The main
reviewer inspects every sheet and native proof; a completed generation agent is
then reused as an adversarial curator to identify repeated constructions,
ambiguous semantics, weak 16px cells, style-grammar drift, accidental vendor
resemblance, and perceptual duplicates. Weak cells are replaced before the
collection review decision can bind the source set.

The public explorer loads one selected SVG at a time. Its actual-size proof is
always 16 CSS pixels. The nearest-neighbor enlargement is separately labeled
“Pixel zoom.” Stable hash URLs identify every cell.

The complete comparison route presents the full 20 × 20 field without issuing
400 artwork requests. Integration deterministically composites the reviewed
128px proofs into one 2560 × 2560 lossless WebP poster, records its dimensions
and SHA-256 in the catalog, and overlays a roving-tabindex keyboard grid on
desktop. A quality lens loads only the focused SVG and exact 16px proof. On
compact screens the poster fits the viewport without horizontal scrolling;
the focus view compares one meaning across 20 grammars or one grammar across
20 meanings using lazy-loaded SVG sources. Query parameters provide stable
focus-view URLs.

## Rebuild

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\build_emoji_matrix.py --prepare-review
.\.venv\Scripts\python.exe scripts\build_emoji_matrix.py --recheck
.\.venv\Scripts\python.exe scripts\build_emoji_matrix.py --integrate
```

`--prepare-review` verifies both isolated agent handoffs and writes the
similarity report. `--recheck` independently runs IconFlow QA over all 400
current sources. `--integrate` fails closed unless the source-set-bound review
decision, 400/400 clean check record, exact dimensions, manifests, and assets
are current.
