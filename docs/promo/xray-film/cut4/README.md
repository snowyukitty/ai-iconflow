<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->
# 16px X-ray film — cut 4

A 42.5-second, 4K24 launch film. It is one camera journey through a sunlit
paper desk:

1. A hand sets a blank cobalt tile down.
2. The real icon develops on the tile's face.
3. A blade of light sweeps across it, and behind the blade the real 16 px
   raster rises as 256 blocks.
4. The colour drains and the blocks fuse into a black square, sitting in a
   giant menu bar.
5. The real X-ray runs on a laptop in the same room.
6. The blocks rebuild as the bold favicon, and a tray mark holds its shape.

## Why it looks like this

Cut 3 was competent and flat: slides cut on a beat. Cut 4 started from
research.

- **Grok and Codex**, each with web search, each named eight reference
  films and distilled rules from them.
- **Contact sheets** were sampled from three official films: Apple *MacBook
  Pro (M5 Pro/Max)*, Anthropic *Introducing Cowork* and Google *There's no
  place like Chrome*.

What was taken:

| Rule | From |
|---|---|
| Warm, practical light in a real room; the product in use, never in a void | Apple MacBook Pro, Anthropic brand films |
| One continuous camera journey; cuts only where motivated | Apple *Scary Fast*, Arc, both reviews |
| UI lives on a device in the room, with depth of field and reflections | Apple Vision Pro / WWDC, Anthropic Cowork |
| A serif for whole thoughts, a mono for dimensions, few words | Anthropic Cowork, Raycast |
| One human trace, then gone | Pixel, Claude films |
| Music felt, not cut: about 76 bpm, near-silence before the verdict | Claude *Keep Thinking*, both reviews |
| The signature shot: the icon crosses into 16 px and becomes 256 blocks | proposed independently by both reviews |

The choice was Anthropic's warmth with Apple's discipline. A free indie tool
should feel handmade and exact, not monumental.

## Material lanes

| Lane | Source | Product truth |
|---|---|---|
| Hand plate (0–3 s) | Google Flow: a Nano Banana Pro first frame, then Veo 3.1 Fast. The tile is blank | Carries no product pixels |
| 3D world | Blender 5.2 Cycles on the GPU, scripted in `scene.py` and `shots.py`; every frame is a function of its time | The icon face is the real 2048 px raster. Every block colour is a pixel of the real 16 px raster (`export_rasters.py`, the X-ray's own canvas path). The template blocks follow the raster's alpha |
| Laptop screen | `capture_screen.py` captures the real `/xray/` page after a real file drop; `screen_frames.py` crops it per frame, adds a cursor and the dragged file, and scrolls for real | Every pixel of the page is the page |
| Type | `film4.html`: Newsreader, Inter, JetBrains Mono | Words only; claims match the UI |

## Sound

- **Voice:** ElevenLabs v2 "Eric", the cut-3 take.
- **Music:** an ElevenLabs Music render of the composition plan `iconflow-xray-film-v4`, take `0559541c`
  (76 bpm). Commercial use was confirmed by Snowy on 2026-10-02.
- **Effects:**
  - procedural ticks, one per column the blade crosses (`timeline4.py`
    solves the crossing times);
  - a soft landing as the bar arrives;
  - a low hit on "square";
  - an error blip on "Two";
  - a chime on "Now";
  - Veo's own tap of the tile on paper in the hand plate.

The mix measures -14.0 LUFS, 6.2 LU, with a -1.5 dBFS true peak. A local
Whisper transcription of the mix reproduces the script word for word. Visual
cues and spoken words agree within ±0.05 s. One exception is the ASR label on
"Two", which the waveform shows is a Whisper timing error.

## Cost

- Flow: one Veo 3.1 Fast plate at 20 credits; the Nano Banana Pro stills were
  free.
- ElevenLabs: 1,168 Music credits for two takes.
- Blender, Cycles and the fonts are free and open source.

## Reproduce

```powershell
# Blender 5.2 portable, unpacked to work/tools/ (see the run log for the checksum)
$B = "work\tools\blender-5.2.2-windows-x64\blender.exe"
.venv\Scripts\python.exe docs/promo/xray-film/cut4/export_rasters.py
.venv\Scripts\python.exe docs/promo/xray-film/cut4/capture_screen.py
.venv\Scripts\python.exe docs/promo/xray-film/cut4/screen_frames.py
& $B -b --factory-startup -P docs/promo/xray-film/cut4/shots.py -- --shot all --res 960 --spp 16    # animatic
& $B -b --factory-startup -P docs/promo/xray-film/cut4/shots.py -- --shot all --res 3840 --spp 64   # master
.venv\Scripts\python.exe docs/promo/xray-film/cut4/timeline4.py --mix --hand-audio work/promo-xray/audio/hand-plate.wav
.venv\Scripts\python.exe docs/promo/xray-film/cut4/capture4.py --res 3840 --scale 2
```

Renders, frames, plates, stems and every MP4 live under `work/promo-xray/`.
None of them enters Git.
