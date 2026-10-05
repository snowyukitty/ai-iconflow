<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# IconFlow emotes — one family, judged at chat size

Fifty-five chat reactions drawn as one family — 32 faces, 10 hands and 13
symbols — every one an editable SVG in [`emotes/`](../emotes/),
dedicated to the public domain (CC0 — see [`emotes/LICENSE`](../emotes/LICENSE)).

This is not the [Emoji Matrix](EMOJI_MATRIX.md). The matrix redraws twenty
meanings through twenty construction grammars to compare techniques; each cell
stands alone and is labelled practice. The emotes are the opposite exercise:
**one** grammar, held across a set that is used together, where the failure
that matters is two members reading as the same reaction at 22 pixels.

## Where emotes are judged

An app icon is judged at 16px on one background. An emote is judged smaller
than its upload and on two backgrounds at once:

| Platform | Upload | Shown at |
|---|---|---|
| Twitch | 28, 56 and 112 px PNG, all three in one upload; ≤ 25 KB each | 28 px in chat |
| Discord | 128 px (larger is resized); ≤ 256 KB | about 22–32 px inline, 48 px as a reaction |
| Slack | 128 px; ≤ 128 KB | about 22–32 px |

Sources, checked 2026-10-05 and consistent with each other (platform help
pages do not publish display sizes): [Twitch emote size guide](https://streamemote.com/blog/twitch-emote-size-guide/),
[Discord emoji size guide](https://emoteresizer.net/blog/discord-emoji-size),
[Slack emoji size guide](https://emoteresizer.net/blog/slack-emoji-size-guide),
[Discord: custom emoji](https://discord.com/blog/beginners-guide-to-custom-emojis).

So every emote is reviewed at **22, 28 and 48 px, on a light chat line and a
dark one** — Slack's white and Discord's `#313338` — after being downscaled from
the 128 px PNG a platform actually stores, not rendered fresh at each size.

## The grammar

**The carrier is the app-icon card.** Every face sits on the squircle IconFlow
ships everywhere else — a rounded square, `rx` 300 on the 1024 grid — rather
than the round head every vendor draws. That one decision is the set's
signature device: at 22 px it already says *these are IconFlow's*, and it
keeps the set clear of every platform's own faces.

| Rule | Value | Why |
|---|---|---|
| Head | `rect` 96,104 832×832, `rx` 300 | the card; leaves room for drops, hats and bursts to break the outline |
| Outline | ink `#191a20`, 52 units (≈1.1 px at 22 px) | holds the edge on white *and* on dark chat |
| Feature line | 84 units (≈1.8 px at 22 px), round caps | the thinnest stroke that survives a 128 → 22 px downscale |
| Eyes | ellipses 112×148, or a stroke of the feature weight | two dots that are still two dots at 22 px |
| Palette | skin `#ffc94d`, ink, tear `#4da3ff`, coral `#ff4f5e`, mint `#3ecf8e`, bone `#f3efe4`, anger `#ff8a5c` | flat fills only; no gradient survives 22 px |
| Hands | one silhouette, one outline: every part drawn first as ink with a 104-unit stroke, then again in skin with none, so only the outer 52 units of ink survive; finger separations drawn inside as creases | a hand is built the way a face is — one outlined shape with its features inside |
| Symbols | no head; same outline, line and palette | 🔥 ❤️ ✨ belong to the family by grammar, not by a face |

Two habits, learned while drawing the set:

- **Break the outline on purpose.** The tears of joy, the sweat drop, the
  party hat, the mind-blown burst and the sleeping *Z* all leave the card.
  At 22 px the silhouette is what a reader catches first, and a member that
  owns a silhouette is never confused with its siblings.
- **Never let one feature carry the whole difference.** The first wink was
  the smile with one eye closed. The family check called it a twin of the
  smile (below), and the sheet at 22 px agreed: one eye is two pixels. The
  shipped wink squeezes its eye into a chevron *and* opens its grin.

## The family check

`iconflow family "emotes/*.svg" --sheet family.png` is how the set is held
together ([`FAMILY.md`](FAMILY.md)). It finds the faces' shared carrier from
their fields alone, compares the faces on what is *not* shared, and fails if
two are one expression drawn twice. On the shipped set:

- one carrier group: all 32 faces, plus the check mark, which sits on the
  same card; the other hands and symbols stand alone;
- no twins; the closest siblings are *eye roll / nerd* at a residual of 0.39
  and *flushed / pleading* at 0.42, against a floor of 0.33;
- along the way the first draft's *smile / wink* sat at 0.31 and the
  second wave's *eye roll / flushed* at 0.33; both were redrawn.

Every member also passes `iconflow check` with no warning.

## Growing the set: 24 to 55

The first 24 were the most-used reactions. The next 31 came from the same
sources — the Unicode frequency table and the reactions chat platforms put
first — plus the ones work chat runs on: ✅ ❌ ⚠️ ❓ 🐛 ☕ 🚀. Three things
the second wave taught:

- **The nearest pair gets nearer as a family grows.** At 24 members the
  closest siblings sat at 0.50; at 55, at 0.39. Every new face is drawn from
  the same few features — dots, arcs, white eyes, an open mouth — so the room
  between them shrinks. A family has a budget, and the twin floor is how you
  see what is left of it.
- **Colour is not a difference.** The first *flushed* was the eye roll with
  pink cheeks: white eyes, dark pupils, a flat mouth. The family check called
  it a twin at 0.33, and its message said why — change what tells them apart,
  not their colour. Blush is gone in a greyscale context and two pixels at
  22 px. The shipped *flushed* raises its brows and wobbles its mouth.
- **Hands are built the way faces are.** The first hands were assembled
  from parts that were each outlined — a palm, four fingers, a thumb, each
  with its own 52-unit rim. At chat size that is what they became: outline.
  Measured at 28 px against the faces, they carried half the mass (0.34 of
  the canvas against 0.65) and half again as much ink (0.51 of their drawn
  pixels against 0.34), and four of them broke into three or four pieces.
  The owner saw it before the numbers did: the hands did not hold up beside
  the faces. A face is one outlined shape with its features drawn inside; the
  redrawn hands are too. Every part is drawn once as solid ink with a stroke
  twice the rim, then again in skin with none, so the only ink left is the
  outer rim, and the separations a reader needs — between fingers, at a cuff
  — are drawn inside as creases. Fingers are at least 120 units wide. After:
  mass 0.50, ink 0.37, no thin parts. *Handshake* is still the hardest
  member at 22 px, as it is in every platform's set.

The check mark and the cross are the app-icon card itself, in mint and coral:
status reactions that read as tiny app icons, which is the set's idea taken
literally.

## What the neighbourhood says about faces, and why it is not a gate here

Run alone through `iconflow neighbours`, a face reports the generic *rounded
square* as its nearest form, sometimes inside the radius. That is the
instrument telling the truth: at 16 px, as a silhouette, a face on a card *is*
a card. It is also the design: the card is the carrier on purpose. The
emotes therefore do not put `@collision` in an avoid set; the family check,
which sets the shared carrier aside, is the gate that fits a set of siblings.

## Adding a member

Draw it on the 1024 grid with the rules above, give it a `<title>`, add it
to `emotes/catalog.json`, then run `iconflow check` on it and
`iconflow family "emotes/*.svg"` on the whole set. A new face that comes
back a twin of an existing one is the family check doing its job: change
what tells them apart.
