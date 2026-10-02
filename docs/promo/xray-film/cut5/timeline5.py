# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Cut 5: IconFlow as a whole, told with real gallery cases. The picture is the clock.

Narration lines are anchored to visual events in shots5.py (the cat and hero
tiles landing, the compare sheet appearing, favicon.ico rising). Writes
timeline5.json, captions5.en.srt and, with --mix, the mix.

Each line is cut out of its take at the quietest point between it and the next
line, never past the next line's onset, so no line carries the first sound of
the one after it.
"""
from __future__ import annotations

import argparse
import array
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cut4"))
import timeline4 as T4  # noqa: E402  (ff, srt, blade_pass_times)

WORK = HERE.parents[3] / "work" / "promo-xray" / "audio"
TAKES = {0: "voice-v5", 1: "voice-v5-l2"}          # line index -> take; others use the first take
DEFAULT_TAKE = "voice-v5"
MUSIC = "bgm-v5-4a28e43f.mp3"      # composition plan iconflow-film-v5, take 1
FPS = 24

SCENES = {
    "flip": (0.0, 10.5),
    "laptop": (10.5, 20.5),
    "family": (20.5, 27.0),
    "pixels": (27.0, 32.5),
    "topdown": (32.5, 35.5),
    "traybar": (35.5, 38.5),
    "endtile": (38.5, 45.0),
}
DURATION = 45.0

# Mirrors shots5.py.
FLIP_DUR = 0.72
FLIPS = [4.33 - FLIP_DUR, 6.30 - FLIP_DUR] + [6.6 + n * 0.14 for n in range(14)]
FAMILY_RISE = [0.9, 1.4, 1.85, 2.2, 2.45, 4.6]
ROW_SCAN = (0.5, 3.6)

EVENTS = {
    "cat": 4.33,
    "hero": 6.30,
    "compare": SCENES["laptop"][0] + 5.8,      # screen.html switches to the bake-off sheet
    "favicon": SCENES["family"][0] + 2.45 + 0.3,
    "tray": SCENES["family"][0] + 4.6 + 0.3,
    "scan_end": SCENES["pixels"][0] + ROW_SCAN[1],
    "end": SCENES["endtile"][0],
}

# (line index, anchor time, word to land on the anchor or None)
LINES = [
    (0, 0.9, None),                              # Most app icons are a letter on a square.
    (1, EVENTS["cat"], "cat"),                   # A sleeping cat for a focus timer. A hooded hero for a story game.
    (2, 11.1, None),                             # You draw the SVG, or your coding agent does, with IconFlow's playbook.
    (3, EVENTS["compare"] + 0.05, None),         # Compare finalists side by side, at real size.
    (4, EVENTS["favicon"], "favicon"),           # Pass review, and one SVG ships as favicon, app icon, desktop and menu bar.
    (5, 27.5, None),                             # Free, open source, on your machine. And the icon is yours.
    (6, 39.3, "IconFlow"),                       # IconFlow. Still itself at sixteen pixels.
]
# Caption cues: long lines split where a reader would breathe (<= ~42 characters each).
SEGMENTS = {
    1: ["A sleeping cat for a focus timer.", "A hooded hero for a story game."],
    2: ["You draw the SVG, or your coding agent does,", "with IconFlow's playbook."],
    4: ["Pass review, and one SVG ships", "as favicon, app icon, desktop and menu bar."],
    5: ["Free, open source, on your machine.", "And the icon is yours."],
    6: ["IconFlow.", "Still itself at sixteen pixels."],
}
WORD_CUES = [("hero_word", 1, "hero"), ("menubar", 4, "menu bar"), ("yours", 5, "yours"),
             ("brand", 6, "IconFlow"), ("still", 6, "Still")]


def alignment(take):
    data = json.loads((WORK / f"{take}.alignment.json").read_text(encoding="utf-8")); data = data.get("alignment", data)
    return "".join(data["characters"]), data["character_start_times_seconds"], data["character_end_times_seconds"]


def envelope(take, rate=8000, win=0.01):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(WORK / f"{take}.mp3"), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    a = array.array("h"); a.frombytes(raw); n = int(rate * win)
    return [sum(v * v for v in a[i:i + n]) / n for i in range(0, len(a) - n, n)], win


def quiet_cut(env, win, end, limit):
    """The quietest 10 ms window in [end, limit]; the line's tail decays into it."""
    lo, hi = int(end / win), max(int(end / win) + 1, int(limit / win))
    hi = min(hi, len(env))
    best = min(range(lo, hi), key=lambda i: env[i]) if hi > lo else lo
    return best * win + win / 2


def build() -> dict:
    lines = (HERE / "narration.txt").read_text(encoding="utf-8").strip().split("\n")
    takes = {}
    for idx, line in enumerate(lines):
        take = TAKES.get(idx, DEFAULT_TAKE)
        if take not in takes:
            takes[take] = alignment(take) + envelope(take)
    spans = {}
    for take, (text, starts, ends, *_rest) in takes.items():
        pos = 0
        for idx, line in enumerate(lines):
            if TAKES.get(idx, DEFAULT_TAKE) != take or line not in text[pos:]:
                continue
            i = text.index(line, pos); spans[idx] = (take, i, i + len(line) - 1); pos = i + len(line)
    voice = []
    for idx, anchor, word in LINES:
        take, i, j = spans[idx]
        text, starts, ends, env, win = takes[take]
        src0, src1 = starts[i], ends[j]
        nxt = [starts[k] for k in range(j + 1, len(text)) if not text[k].isspace()]
        if nxt:
            cut = quiet_cut(env, win, src1, min(src1 + 0.30, nxt[0] - 0.03))
        else:                                          # last line of its take: keep the natural decay
            cut = min(src1 + 0.30, len(env) * win)
        at = anchor - ((starts[text.index(word, i)] - src0) if word else 0)
        voice.append({"line": lines[idx], "take": take, "src": [round(src0, 3), round(src1, 3)], "cut": round(cut, 3), "at": round(at, 3)})
    for a, b in zip(voice, voice[1:]):
        assert a["at"] + a["cut"] - a["src"][0] + 0.15 < b["at"], f"overlap: {a['line']!r} / {b['line']!r}"
    cues = dict(EVENTS)
    for name, idx, phrase in WORD_CUES:
        take, i, _ = spans[idx]; text, starts = takes[take][0], takes[take][1]
        cues[name] = round(voice[idx]["at"] + starts[text.index(phrase, i)] - starts[i], 3)
    captions = []
    for n, v in enumerate(voice):
        take, i, _ = spans[n]; text, starts = takes[take][0], takes[take][1]
        segs = SEGMENTS.get(n, [v["line"]]); pos = i
        for k, seg in enumerate(segs):
            j = text.index(seg, pos); pos = j + len(seg)
            start = v["at"] + starts[j] - starts[i]
            end = (v["at"] + v["cut"] - v["src"][0] + 0.2) if k == len(segs) - 1 else                 v["at"] + starts[text.index(segs[k + 1], pos)] - starts[i] - 0.04
            captions.append({"line": n, "seg": k, "start": round(start, 3), "end": round(end, 3), "text": seg})
    cues["flips"] = [round(t + FLIP_DUR, 3) for t in FLIPS]
    cues["rises"] = [round(SCENES["family"][0] + t + 0.3, 3) for t in FAMILY_RISE]
    return {"duration": DURATION, "fps": FPS, "scenes": SCENES, "cues": cues, "voice": voice, "captions": captions}


def effects(c):
    fx = []
    for n, t in enumerate(c["flips"]):
        fx.append((t - 0.02, "editorial-motion-soft-landing-a.wav", -15 if n < 2 else -25 + n * 0.25))
    for t in c["rises"]:
        fx.append((t - 0.05, "ui-crisp-focus-a.wav", -20))
    x0, x1 = -6.0 - 1.35, 6.0 + 1.35                 # shots5 ROW: five tiles 3.0 apart, half a tile plus margin
    for tile in range(5):
        for col in (0, 15):                           # a tick as the blade reaches and leaves each tile
            cx = (tile - 2) * 3.0 + (col - 7.5) * 2.4 / 16
            k = (cx - x0) / (x1 - x0)
            fx.append((SCENES["pixels"][0] + ROW_SCAN[0] + k * (ROW_SCAN[1] - ROW_SCAN[0]), "ui-crisp-focus-b.wav", -22 + tile))
    fx += [(c["compare"], "ui-soft-confirm-a.wav", -18), (c["brand"], "ui-crisp-confirm-a.wav", -15)]
    return fx


def mix(tl):
    ff = T4.ff
    lines = WORK / "voice-lines-v5"; lines.mkdir(exist_ok=True)
    inputs, filt, lab = [], [], []
    for n, v in enumerate(tl["voice"]):
        clip = lines / f"line-{n + 1}.wav"; a = v["src"][0]
        ff("-i", str(WORK / f"{v['take']}.mp3"), "-ss", f"{max(0, a - 0.04):.3f}", "-to", f"{v['cut']:.3f}",
           "-af", "afade=t=in:d=0.01,areverse,afade=t=in:d=0.03,areverse", "-ar", "48000", "-ac", "2", str(clip))
        inputs += ["-i", str(clip)]; ms = int(round(max(0, v["at"] - 0.04) * 1000))
        filt.append(f"[{n}]adelay={ms}|{ms}[v{n}]"); lab.append(f"[v{n}]")
    nv = len(tl["voice"]); dur = tl["duration"]
    filt.append(f"{''.join(lab)}amix=inputs={nv}:normalize=0,apad,highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120[voice]")
    filt.append("[voice]asplit=2[vo][key]")
    inputs += ["-i", str(WORK / MUSIC)]
    filt.append(f"[{nv}]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur},volume=-6dB,afade=t=out:st={dur - 1.6}:d=1.6[bed]")
    filt.append("[bed][key]sidechaincompress=threshold=0.05:ratio=2.2:attack=60:release=650:makeup=1[ducked]")
    k = nv + 1; extra = []
    for n, (t, wav, gain) in enumerate(effects(tl["cues"])):
        inputs += ["-i", str(WORK / "sfx" / wav)]; ms = int(round(max(0, t) * 1000))
        filt.append(f"[{k + n}]aresample=48000,aformat=channel_layouts=stereo,volume={gain}dB,adelay={ms}|{ms}[fx{n}]")
        extra.append(f"[fx{n}]")
    filt.append(f"[vo][ducked]{''.join(extra)}amix=inputs={2 + len(extra)}:normalize=0,atrim=0:{dur}[out]")
    pre = WORK / "mix-v5.pre.wav"
    ff(*inputs, "-filter_complex", ";".join(filt), "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(pre))
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
    mm = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    out = WORK / "mix-v5.wav"
    ff("-i", str(pre), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
       f"measured_I={mm['input_i']}:measured_TP={mm['input_tp']}:measured_LRA={mm['input_lra']}:"
       f"measured_thresh={mm['input_thresh']}:offset={mm['target_offset']}", "-ar", "48000", "-c:a", "pcm_s24le", str(out))
    return out


def srt(tl):
    def st(x):
        ms = int(round(x * 1000)); return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    return "\n".join(f"{n}\n{st(c['start'])} --> {st(c['end'])}\n{c['text']}\n" for n, c in enumerate(tl["captions"], 1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mix", action="store_true")
    a = ap.parse_args()
    tl = build()
    (HERE / "timeline5.json").write_text(json.dumps(tl, indent=2) + "\n", encoding="utf-8")
    (HERE / "captions5.en.srt").write_text(srt(tl), encoding="utf-8")
    for v in tl["voice"]:
        print(f"{v['at']:6.2f}-{v['at'] + v['cut'] - v['src'][0]:6.2f}  tail {v['cut'] - v['src'][1]:+.2f}s  {v['line']}")
    if a.mix:
        print("mix ->", mix(tl))


if __name__ == "__main__":
    main()
