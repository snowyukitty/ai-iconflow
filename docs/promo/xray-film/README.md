<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->
# 16px X-ray film

A 40-second launch film for the [16px X-ray](https://ai-iconflow.com/xray/).
The master is 3840×2160 at 24 fps, and a 1080p derivative is cut from it. It
carries English narration, an original score, and material sound effects.

The film makes one accusation and gives one proof. It opens on a real macOS
template image, which is a black square. It shows the same dashboard icon
collapsing from 512 px to 16 px in one fixed box, then drops the icon into
the real X-ray. Its failures are revealed one per beat. The film ends on the
rebuilt favicon and a dedicated tray mark that hold at 16 px, then the URL.

Cut 3 follows two independent director reviews of cut 2, by Codex and Grok
independently. Both said the same things:

- open on the failure, not on praise;
- cut hard on a beat grid instead of dipping between slides;
- keep type to one assertion per frame, never the sentence being spoken;
- isolate the privacy claim;
- end on one call to action;
- swap the sentimental piano for a dry, precise bed.

## Material lanes

| Lane | What carries it | Rule |
|---|---|---|
| Product truth | Real `/xray/` screenshots (`capture_ui.py`), rasters drawn by the X-ray's own canvas path | Every verdict shown is one the page printed for that file |
| Physical texture | Three Google Flow plates, each 1.2–1.8 s | Never shows UI, pixels, claims or text |
| Words | Type set in post, Inter and JetBrains Mono | One assertion per frame, coral = failure, mint = verified |

`hairline.svg` is deliberately over-detailed failure material, not a shipped
design. `fixed-card.svg` and `fixed-tray.svg` are its rebuilt versions.

## The music is the grid; the voice is placed on it

`timeline.py` sets the clock. It uses the bed's measured beat grid: 100.0 bpm,
first beat at 0.077 s, 17 ms worst residual from a straight-line fit. Every
scene starts on a beat. Every narration line is anchored to a beat, and some
are anchored so that one word lands on it: "sixteen" on the 16 px step, "Two"
on the red badge, "Now" on the green one. The script refuses overlapping
lines. It writes `timeline.json`, which `film.html` reads, and
`captions.en.srt` for platforms that autoplay muted.

| Layer | Source | Rights |
|---|---|---|
| Voice | ElevenLabs `eleven_multilingual_v2`, voice "Eric", speed 1.08, one take of `narration.txt` | Paid plan output |
| Music | A composition plan rendered with ElevenLabs Music, take 1 of 2 | Paid plan; commercial use confirmed by Snowy on 2026-10-02 |
| Effects | Procedural UI sounds (`ui-crisp`, `ui-soft`, `editorial-motion` families) | Procedural, owned outright |
| Plates | Google Flow, Veo 3.1 Fast, frames-to-video from Nano Banana Pro first frames | Generated on Snowy's plan |

## Flow plates

All four attempts are recorded here. The project ID, the account and the
signed media URLs are deliberately omitted.

| Plate | First frame | Motion prompt (summary) | Verdict |
|---|---|---|---|
| P1 tile | Blank cobalt anodized tile, face-on, black glass | Slow push in; one band of light crosses the face | keep. Used at 5.6–7.4 s, and reversed at 0.4–1.65 s for the end rhyme |
| P2 metal, take 1 | Brushed aluminium, softbox streak | Highlight slides down, camera tracks right | reject. A dark object enters at 1.3 s |
| P2 metal, take 2 | Same start frame; second aluminium still as the end frame | "Only the light moves … nothing enters the frame" | keep. Used at 2.2–3.45 s |
| P3 card | Empty walnut desk, top-down | A blank white card falls and lands flat | keep. Used at 1.4–2.65 s; lands at +0.93 s |

The four Fast generations cost 80 credits, and the balance moved 1,050 → 970.
The first frames were free. Media came down as 1080p upscales and were
conformed to 3840 px with Lanczos and light sharpening.

## Reproduce

From the repository root:

```powershell
.venv\Scripts\python.exe docs/promo/xray-film/capture_ui.py          # real UI plates + verdicts (3x density)
.venv\Scripts\python.exe docs/promo/xray-film/timeline.py --mix      # grid, cues, captions, audio mix
.venv\Scripts\python.exe docs/promo/xray-film/capture.py --scale 1 --stills 1.4 9 14.5 20.7 30.4 35.5
.venv\Scripts\python.exe docs/promo/xray-film/capture.py             # 960 frames -> 4K master + 1080p
.venv\Scripts\python.exe docs/promo/xray-film/og_card.py             # /xray/ social card
```

Audio stems, Flow downloads, the plate frame sequences under
`work/promo-xray/plates-seq/`, and every MP4 stay out of Git. Publish the film
through a release or a post, never through Git history.
