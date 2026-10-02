# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The music is the grid and the narration is placed on it.

Cut 3 cuts hard on the music's measured 100 bpm grid. Every scene starts on a
beat, every narration line is anchored to a beat (some so that one named word
lands on it), and every effect is a cue on that same grid. This script writes:

  timeline.json   beat grid, scene windows, named cues, voice placements
  captions.en.srt the narration as captions, for muted autoplay
  <work>/mix-v3.wav  voice + music bed + procedural effects, -14 LUFS  (--mix)

    python timeline.py
    python timeline.py --mix
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2] / "work" / "promo-xray" / "audio"
VOICE = "voice-v3"            # ElevenLabs v2 "Eric", speed 1.08, one take
MUSIC = "bgm-v3-take1.mp3"    # composition plan iconflow-xray-film-v3, take 1

# Measured on the bed itself (librosa beat track, straight-line fit):
# 100.02 bpm, first beat at 0.077 s, largest residual 17 ms.
BPM = 100.0
PHASE = 0.077
DURATION = 40.0


def beat(k: float) -> float:
    return round(PHASE + k * 60.0 / BPM, 3)


# Scene windows in beats. Each scene starts on a cut.
SCENES = {
    "hook": (0, 4),        # the real menu-bar square, before anything is explained
    "tile": (4, 8),        # Flow plate P1, match-cut to the flat 512 icon
    "ladder": (8, 13),     # 256 → 16 in one fixed box, one step per beat
    "tab": (13, 19),       # the 16px grid holds; a real-size tab
    "metal": (19, 21),     # Flow plate P2
    "menubar": (21, 27),   # the template image, full bleed
    "card": (27, 29),      # Flow plate P3: a blank card lands
    "xray": (29, 41),      # the real tool, revealed in order
    "fix": (41, 53),       # rebuilt card and tray mark, same grid
    "rhyme": (53, 55),     # Flow plate P1 again
    "end": (55, None),     # mark, line, URL
}

# Narration: (line index, beat, word that must land on the beat or None, offset s).
LINES = [
    (0, 2, None, 0.10),       # This is your icon.
    (1, 4, None, 0.35),       # Designed at five-twelve.
    (2, 12, "sixteen", 0.0),  # Shipped at sixteen.   ("sixteen" on the 16px step)
    (3, 14, None, 0.20),      # In a browser tab, the chart is gone.
    (4, 21, None, 0.30),      # On the Mac menu bar, it's a square.
    (5, 27, None, 0.25),      # Drop it into the sixteen-pixel X-ray.
    (6, 34, "Two", 0.0),      # Two failures.        (on the red badge)
    (7, 36, None, 0.15),      # It runs in your browser. Nothing is uploaded.
    (8, 41, None, 0.30),      # Fewer shapes for the tab. A mark drawn for the menu bar.
    (9, 50, "Now", 0.0),      # Now it holds.        (on the green badge)
    (10, 55, None, 0.45),     # IconFlow. See your icon at sixteen pixels, before your users do.
]

# Visual cues tied to spoken words: (name, line index, phrase, edge).
WORD_CUES = [
    ("square", 4, "square", "start"),
    ("tab", 8, "tab", "start"),
    ("menubar", 8, "menu bar", "start"),
    ("see", 10, "See", "start"),
]


def effects(c: dict) -> list[tuple[float, str, float]]:
    """Short, dry, material sounds on the grid. No whooshes."""
    fx = [
        (c["ring"], "editorial-motion-precision-hit-a.wav", -12),
        (c["card_land"], "editorial-motion-soft-landing-a.wav", -9),
        (c["drop"], "ui-crisp-focus-a.wav", -10),
        (c["reveal1"], "ui-crisp-focus-b.wav", -14),
        (c["reveal2"], "ui-crisp-focus-b.wav", -14),
        (c["reveal3"], "ui-crisp-focus-b.wav", -14),
        (c["fail"], "ui-soft-error.wav", -8),
        (c["swap"], "ui-crisp-focus-a.wav", -11),
        (c["traymark"], "ui-crisp-focus-a.wav", -11),
        (c["holds"], "ui-soft-success.wav", -7),
        (c["logo"], "ui-crisp-confirm-a.wav", -12),
        (c["menu_square"], "ui-soft-error.wav", -14),
    ]
    for k in range(5):
        fx.append((beat(8 + k), "ui-crisp-focus-b.wav", -15 + k))   # ladder ticks grow
    return fx


def load_alignment() -> tuple[str, list[float], list[float]]:
    data = json.loads((WORK / f"{VOICE}.alignment.json").read_text(encoding="utf-8"))
    data = data.get("alignment", data)
    return ("".join(data["characters"]), data["character_start_times_seconds"],
            data["character_end_times_seconds"])


def build() -> dict:
    text, starts, ends = load_alignment()
    lines = (HERE / "narration.txt").read_text(encoding="utf-8").strip().split("\n")
    spans, pos = [], 0
    for line in lines:
        i = text.index(line, pos)
        spans.append((i, i + len(line) - 1))
        pos = i + len(line)

    voice = []
    for idx, b, word, offset in LINES:
        i, j = spans[idx]
        src0, src1 = starts[i], ends[j]
        at = beat(b) + offset
        if word:
            at -= starts[text.index(word, i)] - src0
        voice.append({"line": lines[idx], "src": [round(src0, 3), round(src1, 3)], "at": round(at, 3)})

    def spoken(idx: int, phrase: str, edge: str) -> float:
        i, _ = spans[idx]
        p = text.index(phrase, i)
        t = starts[p] if edge == "start" else ends[p + len(phrase) - 1]
        return round(voice[idx]["at"] + t - starts[i], 3)

    cues = {name: spoken(idx, phrase, edge) for name, idx, phrase, edge in WORD_CUES}
    cues.update({
        "light": 0.0, "dark": beat(1), "ring": beat(2),
        "match": beat(7),
        "grid": beat(13), "tabstrip": beat(14),
        "menu_square": cues["square"],
        "card_land": round(beat(27) + 0.93, 3),     # measured landing frame in plate P3
        "drop": beat(30), "reveal1": beat(31), "reveal2": beat(32), "reveal3": beat(33),
        "fail": beat(34), "verdicts": beat(35), "private": beat(36),
        "swap": cues["tab"], "traymark": cues["menubar"],
        "holds": beat(50), "logo": beat(55),
    })
    scenes = {k: [beat(a), beat(b) if b is not None else DURATION] for k, (a, b) in SCENES.items()}
    scenes["hook"][0] = 0.0
    # Overlaps would put two headlines on screen at once: refuse them.
    for idx in range(len(voice) - 1):
        a, b = voice[idx], voice[idx + 1]
        assert a["at"] + a["src"][1] - a["src"][0] < b["at"], f"lines {idx} and {idx + 1} overlap"
    return {"duration": DURATION, "bpm": BPM, "phase": PHASE, "scenes": scenes,
            "cues": cues, "voice": voice}


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def mix(tl: dict) -> Path:
    lines = WORK / "voice-lines-v3"
    lines.mkdir(exist_ok=True)
    inputs, filters, labels = [], [], []
    for n, v in enumerate(tl["voice"]):
        clip = lines / f"line-{n + 1}.wav"
        a, b = v["src"]
        ffmpeg("-i", str(WORK / f"{VOICE}.mp3"), "-ss", f"{max(0, a - 0.04):.3f}", "-to", f"{b + 0.14:.3f}",
               "-af", "afade=t=in:d=0.01,areverse,afade=t=in:d=0.06,areverse", "-ar", "48000", "-ac", "2", str(clip))
        inputs += ["-i", str(clip)]
        ms = int(round(max(0, v["at"] - 0.04) * 1000))
        filters.append(f"[{n}]adelay={ms}|{ms}[v{n}]")
        labels.append(f"[v{n}]")
    nv = len(tl["voice"])
    filters.append(f"{''.join(labels)}amix=inputs={nv}:normalize=0,apad,highpass=f=80,"
                   "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120[voice]")
    filters.append("[voice]asplit=2[vo][key]")

    dur = tl["duration"]
    inputs += ["-i", str(WORK / MUSIC)]
    m = nv
    filters.append(f"[{m}]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur},volume=-7dB[bed]")
    # A gentle duck, a few dB under speech, never pumping.
    filters.append("[bed][key]sidechaincompress=threshold=0.05:ratio=2.2:attack=60:release=600:makeup=1[ducked]")

    fx = effects(tl["cues"])
    for k, (t, wav, gain) in enumerate(fx):
        inputs += ["-i", str(WORK / "sfx" / wav)]
        ms = int(round(max(0, t) * 1000))
        filters.append(f"[{m + 1 + k}]aresample=48000,aformat=channel_layouts=stereo,volume={gain}dB,adelay={ms}|{ms}[fx{k}]")
    fxl = "".join(f"[fx{k}]" for k in range(len(fx)))
    filters.append(f"[vo][ducked]{fxl}amix=inputs={2 + len(fx)}:normalize=0,atrim=0:{dur}[out]")
    pre = WORK / "mix-v3.pre.wav"
    ffmpeg(*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(pre))
    # Two-pass loudness: measure, then apply linearly so the dynamics survive.
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    out = WORK / "mix-v3.wav"
    ffmpeg("-i", str(pre), "-af",
           "loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
           f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
           f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}",
           "-ar", "48000", "-c:a", "pcm_s24le", str(out))
    return out


def srt(tl: dict) -> str:
    def stamp(x: float) -> str:
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    out = []
    for n, v in enumerate(tl["voice"], 1):
        a, b = v["src"]
        out.append(f"{n}\n{stamp(v['at'])} --> {stamp(v['at'] + b - a + 0.25)}\n{v['line']}\n")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mix", action="store_true")
    args = ap.parse_args()
    tl = build()
    (HERE / "timeline.json").write_text(json.dumps(tl, indent=2) + "\n", encoding="utf-8")
    (HERE / "captions.en.srt").write_text(srt(tl), encoding="utf-8")
    for v in tl["voice"]:
        print(f"{v['at']:6.2f}-{v['at'] + v['src'][1] - v['src'][0]:6.2f}  {v['line']}")
    print("cues:", tl["cues"])
    if args.mix:
        print("mix ->", mix(tl))


if __name__ == "__main__":
    main()
