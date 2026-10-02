# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Cut 4: one camera journey through a sunlit desk. The picture is the clock.

Scenes are fixed CG/plate windows; narration lines are anchored to visual
events (the scan finishing, the bar arriving, the file landing). Effects sit on
those events. Writes timeline4.json, captions4.en.srt and, with --mix, the mix.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILM = HERE.parent
WORK = HERE.parents[3] / "work" / "promo-xray" / "audio"
VOICE = "voice-v3"
MUSIC = "bgm-v4-0559541c.mp3"      # composition plan iconflow-xray-film-v4, take 2
FPS = 24

# Film-time windows. The CG shot lengths match shots.py SHOTS.
SCENES = {
    "hand": (0.0, 3.0),       # Flow plate: a hand sets the blank tile down
    "macro": (3.0, 7.5),
    "scan": (7.5, 12.5),
    "topdown": (12.5, 16.0),
    "square": (16.0, 22.5),
    "laptop": (22.5, 30.5),
    "fix": (30.5, 33.5),
    "traybar": (33.5, 36.5),
    "endtile": (36.5, 42.5),
}
DURATION = 42.5


def inout(x): return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def blade_pass_times(t0, t1, start):
    """Film times at which the scan blade crosses each of the 16 block columns."""
    size, cell = 2.4, 2.4 / 16
    x0, x1 = -size / 2 - 0.15, size / 2 + 0.15
    out = []
    for col in range(16):
        cx = (col - 7.5) * cell
        target = (cx - x0) / (x1 - x0)
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if inout(mid) < target else (lo, mid)
        out.append(round(start + t0 + (t1 - t0) * lo, 3))
    return out


EVENTS = {
    "tap": 2.55,                               # the tile meets the paper in the hand plate
    "develop": 3.0,                            # the icon appears on the blank tile
    "scan_end": 7.5 + 3.5,                     # blade leaves the last column
    "grid": 12.5,
    "drained": 16.0 + 2.2,
    "bar": 16.0 + 3.6,                         # the menu bar arrives under the black square
    "drop": 22.5 + 1.6,                        # the file lands in the real drop zone
    "results": 22.5 + 2.75,                    # the scroll reaches the results
    "fix_end": 30.5 + 2.2,
    "tray": 33.5,
    "end": 36.5,
}

# (line index, anchor time, word to land on the anchor or None, offset s)
LINES = [
    (0, 1.45, None, 0.0),                      # This is your icon.
    (1, 3.75, None, 0.0),                      # Designed at five-twelve.
    (2, EVENTS["scan_end"], "sixteen", 0.0),   # Shipped at sixteen.
    (3, 12.85, None, 0.0),                     # In a browser tab, the chart is gone.
    (4, EVENTS["bar"], "square", 1.9),         # On the Mac menu bar, it's a square.   (after a held breath)
    (5, 22.85, None, 0.0),                     # Drop it into the sixteen-pixel X-ray.
    (6, EVENTS["results"], "Two", 0.35),       # Two failures.
    (7, 26.95, None, 0.0),                     # It runs in your browser. Nothing is uploaded.
    (8, 30.75, None, 0.0),                     # Fewer shapes for the tab. A mark drawn for the menu bar.
    (9, 35.05, "Now", 0.0),                    # Now it holds.
    (10, 37.15, None, 0.0),                    # IconFlow. See your icon at sixteen pixels, before your users do.
]
WORD_CUES = [("square", 4, "square"), ("two", 6, "Two"), ("tab", 8, "tab"), ("menubar", 8, "menu bar"),
             ("now", 9, "Now"), ("see", 10, "See"), ("brand", 10, "IconFlow")]


def load_alignment():
    data = json.loads((WORK / f"{VOICE}.alignment.json").read_text(encoding="utf-8"))
    data = data.get("alignment", data)
    return "".join(data["characters"]), data["character_start_times_seconds"], data["character_end_times_seconds"]


def build() -> dict:
    text, starts, ends = load_alignment()
    lines = (FILM / "narration.txt").read_text(encoding="utf-8").strip().split("\n")
    spans, pos = [], 0
    for line in lines:
        i = text.index(line, pos); spans.append((i, i + len(line) - 1)); pos = i + len(line)
    voice = []
    for idx, anchor, word, off in LINES:
        i, j = spans[idx]; src0, src1 = starts[i], ends[j]
        at = anchor + off - ((starts[text.index(word, i)] - src0) if word else 0)
        voice.append({"line": lines[idx], "src": [round(src0, 3), round(src1, 3)], "at": round(at, 3)})
    for a, b in zip(voice, voice[1:]):
        assert a["at"] + a["src"][1] - a["src"][0] + 0.15 < b["at"], f"overlap: {a['line']!r} / {b['line']!r}"
    cues = dict(EVENTS)
    for name, idx, phrase in WORD_CUES:
        i, _ = spans[idx]
        cues[name] = round(voice[idx]["at"] + starts[text.index(phrase, i)] - starts[i], 3)
    cues["ticks_scan"] = blade_pass_times(0.8, 3.5, SCENES["scan"][0])
    cues["ticks_fix"] = blade_pass_times(0.25, 2.2, SCENES["fix"][0])
    return {"duration": DURATION, "fps": FPS, "scenes": SCENES, "cues": cues, "voice": voice}


def effects(c):
    fx = [
        (c["develop"], "ui-crisp-confirm-a.wav", -20),
        (c["bar"] - 0.05, "editorial-motion-soft-landing-a.wav", -12),
        (c["square"], "editorial-motion-precision-hit-a.wav", -9),
        (c["drop"], "ui-crisp-focus-a.wav", -12),
        (c["two"], "ui-soft-error.wav", -9),
        (c["now"], "ui-soft-success.wav", -8),
        (c["brand"], "ui-crisp-confirm-a.wav", -15),
    ]
    for k, t in enumerate(c["ticks_scan"]):
        fx.append((t, "ui-crisp-focus-b.wav", -22 + k * 0.5))     # sixteen columns, a little louder each
    for t in c["ticks_fix"]:
        fx.append((t, "ui-crisp-focus-b.wav", -20))
    return fx


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *a], check=True)


def mix(tl, hand_audio=None):
    lines = WORK / "voice-lines-v4"; lines.mkdir(exist_ok=True)
    inputs, filt, lab = [], [], []
    for n, v in enumerate(tl["voice"]):
        clip = lines / f"line-{n + 1}.wav"; a, b = v["src"]
        ff("-i", str(WORK / f"{VOICE}.mp3"), "-ss", f"{max(0, a - 0.04):.3f}", "-to", f"{b + 0.14:.3f}",
           "-af", "afade=t=in:d=0.01,areverse,afade=t=in:d=0.06,areverse", "-ar", "48000", "-ac", "2", str(clip))
        inputs += ["-i", str(clip)]; ms = int(round(max(0, v["at"] - 0.04) * 1000))
        filt.append(f"[{n}]adelay={ms}|{ms}[v{n}]"); lab.append(f"[v{n}]")
    nv = len(tl["voice"])
    filt.append(f"{''.join(lab)}amix=inputs={nv}:normalize=0,apad,highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120[voice]")
    filt.append("[voice]asplit=2[vo][key]")
    dur = tl["duration"]; m = nv
    inputs += ["-i", str(WORK / MUSIC)]
    filt.append(f"[{m}]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur},volume=-6dB,afade=t=out:st={dur - 1.6}:d=1.6[bed]")
    filt.append("[bed][key]sidechaincompress=threshold=0.05:ratio=2.2:attack=60:release=650:makeup=1[ducked]")
    k = m + 1; extra = []
    if hand_audio and Path(hand_audio).is_file():
        inputs += ["-i", str(hand_audio)]
        filt.append(f"[{k}]aresample=48000,aformat=channel_layouts=stereo,atrim=0:3.0,volume=-6dB,afade=t=out:st=2.75:d=0.25[hand]")
        extra.append("[hand]"); k += 1
    fx = effects(tl["cues"])
    for n, (t, wav, gain) in enumerate(fx):
        inputs += ["-i", str(WORK / "sfx" / wav)]; ms = int(round(max(0, t) * 1000))
        filt.append(f"[{k + n}]aresample=48000,aformat=channel_layouts=stereo,volume={gain}dB,adelay={ms}|{ms}[fx{n}]")
        extra.append(f"[fx{n}]")
    filt.append(f"[vo][ducked]{''.join(extra)}amix=inputs={2 + len(extra)}:normalize=0,atrim=0:{dur}[out]")
    pre = WORK / "mix-v4.pre.wav"
    ff(*inputs, "-filter_complex", ";".join(filt), "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", str(pre))
    probe = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
    mm = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    out = WORK / "mix-v4.wav"
    ff("-i", str(pre), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
       f"measured_I={mm['input_i']}:measured_TP={mm['input_tp']}:measured_LRA={mm['input_lra']}:"
       f"measured_thresh={mm['input_thresh']}:offset={mm['target_offset']}", "-ar", "48000", "-c:a", "pcm_s24le", str(out))
    return out


def srt(tl):
    def st(x):
        ms = int(round(x * 1000)); return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    return "\n".join(f"{n}\n{st(v['at'])} --> {st(v['at'] + v['src'][1] - v['src'][0] + 0.25)}\n{v['line']}\n"
                     for n, v in enumerate(tl["voice"], 1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mix", action="store_true"); ap.add_argument("--hand-audio")
    a = ap.parse_args()
    tl = build()
    (HERE / "timeline4.json").write_text(json.dumps(tl, indent=2) + "\n", encoding="utf-8")
    (HERE / "captions4.en.srt").write_text(srt(tl), encoding="utf-8")
    for v in tl["voice"]:
        print(f"{v['at']:6.2f}-{v['at'] + v['src'][1] - v['src'][0]:6.2f}  {v['line']}")
    if a.mix:
        print("mix ->", mix(tl, a.hand_audio))


if __name__ == "__main__":
    main()
