<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# The launch film

A production plan for IconFlow's video assets. Written 2026-08-24. Nothing here
has been shot yet; this is the brief a production run should follow.

## The one rule

**Every frame must be real screen output.**

IconFlow's entire proposition is that a claim without an artifact behind it is
worthless. A film for it that opens on generated B-roll of a designer at a
sunlit desk would be a product lying about itself in its own advertisement.
That is not squeamishness about generative video — it is that this specific
product's promise is *the thing you see is the thing that shipped*, and the
film has to obey the rule it sells.

So: real terminal, real Review Lab, real archive scrubber, real 16px pixels.
Motion graphics may compose and transition that footage. They may not
manufacture it.

## Which tool

Three candidates were on the table. They are not interchangeable.

**Screen capture + [`snowy-hyperframes`](../../snowy-hyperframes) — the hero
film.** HyperFrames already does the part that is genuinely hard: narration
timing, TTS, an audio audit, a preview gate before render, and a repeatable
build. Its known failure mode is rendering too early, before a human has heard
the pacing — which is exactly what `npm run check`, `npm run audio:audit` and
`npm run preview` exist to prevent. Use it, and do not skip the preview gate.
The footage it composites comes from a real capture session, not from a model.

**[`cineloom`](../../cineloom) — not for this film.** CineLoom is a filmmaking
operating system: continuity bibles, shot boards, provenance ledgers, a policy
engine. It is built to keep a *narrative* coherent across many generated shots.
This film has no characters and no continuity problem; it has fourteen seconds
of terminal output and a review surface. Using CineLoom here would be paying
for machinery the job does not need. (It is also already an IconFlow consumer —
it carries its own `iconflow.toml` — which makes it a better *case study* than
a production tool for this.)

**[Gemini Omni Flash](https://cloud.google.com/blog/products/ai-machine-learning/nano-banana-2-lite-and-gemini-omni-flash-available)
— not in the hero film.** Google's multimodal video model, out for developers
since 2026-06-30, is genuinely good at exactly the thing this film must not
contain. Two further reasons to keep it out of the main cut: its output carries
SynthID provenance marking, and a repository with a `PROVENANCE.md` should not
have to explain why its trailer is watermarked as synthetic. Where it could
earn a place later: localized social variants, or an abstract 2-second title
sting that is obviously a title sting and not footage. Decide that separately,
after the honest cut exists.

## The 60-second cut

Screen recordings at 60fps, 2560×1440, downscaled to 1080p. No music under the
terminal section — keystrokes and silence read as real; a music bed reads as an
ad. Captions burned in, because most of this will autoplay muted.

| Time | Picture | Line |
|---:|---|---|
| 0:00–0:06 | One icon at 1024px, beautiful, filling frame. It shrinks continuously to 16px and turns to mush. | *It looked finished at 1024.* |
| 0:06–0:13 | Three failures side by side at native size: a counter closing, a hairline vanishing, a tray template collapsing to a black square. | *Nobody reviews the pixel that actually ships.* |
| 0:13–0:22 | Cut to terminal. `iconflow demo --out demo`. The doctor PASS list fills in. | *IconFlow starts where exporters stop.* |
| 0:22–0:34 | The Review Lab: actual-size row, pixel zoom, adaptive crop, the tray template on a light menu bar and a dark one. Cursor moves like a person's. | *Native pixels. Not a mockup of pixels.* |
| 0:34–0:43 | `ship`. `SHIP PASSED — built 23 files`. The filenames fan out into web, Tauri, Electron and tray groups. | *One master. Every surface.* |
| 0:43–0:52 | **The turn.** Hard cut back to the SVG. One control point moves — six units. Same command, retyped. Red: `review receipt is stale`. Hold. | *The pixels changed. The approval did not follow.* |
| 0:52–1:00 | The 137-direction archive wall scrolls, settles on Petal Haypile. Wordmark. `pip install iconflow` · ai-iconflow.com | — |

The turn at 0:43 is the film. Everything before it is a competent icon
pipeline that four other tools also have; the refusal is the only thing on
screen that nothing else does. If the edit runs long, cut from the middle and
protect that beat's full nine seconds.

## Cutdowns

- **0:15 social** — the shrink (0:00–0:06), the refusal (0:43–0:52), the
  install line. Three shots, no narration, captions only. This is the one that
  travels.
- **0:06 loop** — the refusal alone, silent, looping. For the README and the
  site hero, where the visitor has already arrived.
- **Localized** — the site reads in five languages and the film should too.
  Captions only; do not re-record narration until one language proves the
  format. Terminal output stays English, because it is evidence.

## Where it goes

1. **Site hero.** Poster image first, `<video>` behind a click, never autoplay
   with sound. Add `VideoObject` structured data *when the file exists* —
   schema describing a video that has not been published is exactly the kind of
   claim the rest of the site refuses to make.
2. **README.** GitHub does not play `<video>` from a repository path, so the
   README keeps the GIF. Link the full film beneath it.
3. **PyPI.** The project description renders the README; it cannot play video
   and does not resolve relative image paths. Leave it as text.
4. **Social.** The 0:15 cut, natively uploaded to each platform rather than
   linked — every one of them throttles outbound links.

## Before shooting

- [ ] Capture at 2560×1440 on a clean desktop with a neutral shell prompt and
      no personal paths on screen. The demo run writes into a temporary
      directory; use a short one, because it will be legible.
- [ ] Use the packaged demo family, so anyone can reproduce every frame with
      `iconflow demo`.
- [ ] Get the failing `ship` in the *same* recording session as the passing
      one, with the same window geometry, so the cut at 0:43 is a real match
      cut and not two sessions pretending.
- [ ] Run HyperFrames' `npm run check` and `npm run audio:audit`, then
      `npm run preview`, and watch it end to end before any render.
- [ ] Confirm no absolute path, API key, or private repository name appears in
      any frame — including the terminal scrollback above the visible region.
