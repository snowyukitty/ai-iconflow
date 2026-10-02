# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Turn a finished film master into the site's film deliverables, or restore them.

    python scripts/film_publish.py build --graded MASTER.mp4 --clean CLEAN.mp4 --cut docs/promo/xray-film/cut5 --release film-v5
    python scripts/film_publish.py verify
    python scripts/film_publish.py fetch          # restore website/media/film/ from the GitHub Release

Video never enters git. The deliverables live in the gitignored
``website/media/film/`` and in a GitHub Release; ``docs/promo/film-manifest.json``
is the small, committed record of what the page references (names, sizes,
SHA-256), and ``website/index.html`` carries those names between ``film:*`` markers.

- ``--graded`` is the master as audiences see it, with its film grain. The AV1
  encode starts from it: SVT-AV1 removes the grain, codes the clean picture and
  sends a grain model that the decoder re-synthesises, so grain costs ~nothing.
- ``--clean`` is the same film rendered without grain. H.264 cannot synthesise
  grain, and coding real grain would cost ~3x the bytes, so it starts here.

Every output is content-addressed (``film-<sha8>.*``) and served immutable, so an
update never needs a cache purge. Earlier versions stay in place until pruned,
which keeps a rollback deploy whole.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "website" / "media" / "film"
MANIFEST = ROOT / "docs" / "promo" / "film-manifest.json"
INDEX = ROOT / "website" / "index.html"
REPO = "snowyukitty/ai-iconflow"
URL_PREFIX = "/media/film/"

MiB = 1024 * 1024
BUDGET = {"mp4": 24 * MiB, "webm": 24 * MiB, "github": 9_500_000, "poster": 600 * 1024, "vtt": 16 * 1024}
LANG_ORDER = ["en", "es", "ja", "zh-Hant", "zh-Hans"]
TYPES = {
    "webm": 'video/webm; codecs="av01.0.08M.10, opus"',
    "mp4": 'video/mp4; codecs="avc1.640028, mp4a.40.2"',
}


def run(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def place(tmp: Path, kind: str, suffix: str) -> str:
    """Move a finished output into MEDIA under its content address; return the file name."""
    digest = sha256(tmp)[:8]
    name = f"film-{digest}{suffix}"
    if tmp.stat().st_size > BUDGET[kind]:
        sys.exit(f"{name}: {tmp.stat().st_size / MiB:.1f} MiB is over the {kind} budget of {BUDGET[kind] / MiB:.1f} MiB")
    MEDIA.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp), MEDIA / name)
    return name


# ---------- encodes ----------

def encode_mp4(clean: Path, out: Path) -> None:
    """H.264 High 4.0, 1080p24, AAC-LC: the file every browser can play."""
    for crf in (20, 21, 22, 23, 24, 25, 26):
        run("-i", str(clean), "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryslow", "-tune", "film", "-crf", str(crf),
            "-profile:v", "high", "-level:v", "4.0", "-g", "48", "-keyint_min", "48", "-sc_threshold", "0",
            "-c:a", "aac", "-b:a", "160k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart", str(out))
        if out.stat().st_size <= BUDGET["mp4"] * 0.8:
            print(f"  mp4  crf {crf}: {out.stat().st_size / MiB:.1f} MiB")
            return
    print(f"  mp4  crf 26: {out.stat().st_size / MiB:.1f} MiB")


def encode_webm(graded: Path, out: Path) -> None:
    """AV1 Main 10-bit in WebM with film-grain synthesis, Opus audio."""
    run("-i", str(graded), "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p10le",
        "-c:v", "libsvtav1", "-preset", "4", "-crf", "30", "-g", "48",
        "-svtav1-params", "tune=0:film-grain=10:film-grain-denoise=1:enable-overlays=1",
        "-c:a", "libopus", "-b:a", "128k", "-ac", "2", "-ar", "48000", "-f", "webm", str(out))
    print(f"  webm av1: {out.stat().st_size / MiB:.1f} MiB")


def encode_github(clean: Path, out: Path, tmpdir: Path) -> None:
    """720p H.264, two-pass to fit GitHub Free's 10 MB attachment limit with headroom."""
    secs = duration(clean); audio = 96_000
    video = int((BUDGET["github"] * 0.95 * 8) / secs) - audio
    log = str(tmpdir / "gh2pass")
    common = ["-vf", "scale=1280:720:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "veryslow",
              "-tune", "film", "-b:v", str(video), "-maxrate", str(int(video * 1.5)), "-bufsize", str(video * 3),
              "-profile:v", "high", "-level:v", "3.1", "-g", "48", "-passlogfile", log]
    run("-i", str(clean), *common, "-pass", "1", "-an", "-f", "null", "NUL" if sys.platform == "win32" else "/dev/null")
    run("-i", str(clean), *common, "-pass", "2", "-c:a", "aac", "-b:a", str(audio), "-ac", "2",
        "-movflags", "+faststart", str(out))
    print(f"  github 720p: {out.stat().st_size / 1e6:.2f} MB")


README_POSTER = ROOT / "docs" / "assets" / "marketing" / "film-poster-1280.jpg"


def readme_poster(png: Path) -> None:
    """The README cannot play the site's video, so it links a poster that says 'play'."""
    from PIL import Image, ImageDraw
    im = Image.open(png).convert("RGB"); w, h = im.size
    scale = 4; big = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    r = int(h * 0.075) * scale; cx, cy = int(w * 0.06) * scale + r, h * scale - int(h * 0.07) * scale - r
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 90, 79, 255))
    t = r * 0.42
    d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t, cy)], fill=(25, 26, 32, 255))
    im.paste(big.resize((w, h), Image.LANCZOS), (0, 0), big.resize((w, h), Image.LANCZOS))
    README_POSTER.parent.mkdir(parents=True, exist_ok=True)
    im.save(README_POSTER, quality=84, optimize=True, progressive=True)


def posters(clean: Path, at: float, tmpdir: Path) -> dict[str, str]:
    names = {}
    for width in (1280, 1920):
        png = tmpdir / f"poster-{width}.png"
        run("-ss", f"{at:.3f}", "-i", str(clean), "-frames:v", "1", "-vf", f"scale={width}:-2:flags=lanczos", str(png))
        avif, jpg = tmpdir / f"p{width}.avif", tmpdir / f"p{width}.jpg"
        run("-i", str(png), "-c:v", "libaom-av1", "-still-picture", "1", "-crf", "28", "-cpu-used", "4",
            "-pix_fmt", "yuv420p10le", str(avif))
        run("-i", str(png), "-q:v", "3", str(jpg))
        if width == 1280:
            readme_poster(png)
        names[f"avif{width}"] = place(avif, "poster", f".{width}.avif")
        names[f"jpg{width}"] = place(jpg, "poster", f".{width}.jpg")
    return names


# ---------- captions ----------

def vtt_time(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}"


def captions(cut: Path, tmpdir: Path) -> dict[str, dict]:
    timeline = json.loads((cut / "timeline5.json").read_text(encoding="utf-8"))
    langs = json.loads((cut / "captions.json").read_text(encoding="utf-8"))["languages"]
    cues = timeline["captions"]
    english = [c["text"] for c in cues]
    if langs["en"]["cues"] != english:
        sys.exit("captions.json English cues have drifted from timeline5.json; update the translations first")
    first = cues[0]["start"]
    out = {}
    for lang in LANG_ORDER:
        spec = langs[lang]
        if len(spec["cues"]) != len(cues):
            sys.exit(f"captions.json {lang}: {len(spec['cues'])} cues, timeline has {len(cues)}")
        lines = ["WEBVTT", "", f"{vtt_time(0.0)} --> {vtt_time(max(0.4, first - 0.05))}", spec["music"], ""]
        for cue, text in zip(cues, spec["cues"]):
            lines += [f"{vtt_time(cue['start'])} --> {vtt_time(cue['end'])} line:88%", text, ""]
        tmp = tmpdir / f"{lang}.vtt"
        tmp.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        out[lang] = {"file": place(tmp, "vtt", f".{lang}.vtt"), "label": spec["label"]}
    return out


# ---------- page and manifest ----------

def replace_block(html: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- film:{name}:start -->)(.*?)(\s*<!-- film:{name}:end -->)", re.S)
    if not pattern.search(html):
        sys.exit(f"website/index.html has no film:{name} markers")
    return pattern.sub(lambda m: m.group(1) + body + m.group(3), html, count=1)


def render_page(m: dict) -> None:
    f = m["files"]; indent = "\n        "
    media = indent + indent.join(
        [f'<source src="{URL_PREFIX}{f["webm"]}" type=\'{TYPES["webm"]}\'>',
         f'<source src="{URL_PREFIX}{f["mp4"]}" type=\'{TYPES["mp4"]}\'>']
        + [f'<track kind="captions" src="{URL_PREFIX}{c["file"]}" srclang="{lang}" label="{c["label"]}"'
           + (" default" if lang == "en" else "") + ">"
           for lang, c in m["captions"].items()])
    p = f["posters"]
    poster = indent + indent.join([
        f'<source type="image/avif" srcset="{URL_PREFIX}{p["avif1280"]} 1280w, {URL_PREFIX}{p["avif1920"]} 1920w" sizes="(min-width: 1290px) 1240px, calc(100vw - 48px)">',
        f'<img src="{URL_PREFIX}{p["jpg1280"]}" srcset="{URL_PREFIX}{p["jpg1280"]} 1280w, {URL_PREFIX}{p["jpg1920"]} 1920w" '
        f'sizes="(min-width: 1290px) 1240px, calc(100vw - 48px)" width="1920" height="1080" loading="lazy" decoding="async" alt="">'])
    download = f'https://github.com/{REPO}/releases/download/{m["release"]}/{m["release_master"]}'
    html = INDEX.read_text(encoding="utf-8")
    html = replace_block(html, "media", media)
    html = replace_block(html, "poster", poster)
    # The size sits outside the translated link text, so a new cut does not retire five translations.
    html = replace_block(html, "download", f'{indent}<a class="film-download" href="{download}">Download the 4K master</a>'
                                           f'<span class="film-size" data-i18n="skip">{m["release_master_mb"]} MB</span>')
    INDEX.write_text(html, encoding="utf-8", newline="\n")


def build(a: argparse.Namespace) -> None:
    graded, clean, cut = Path(a.graded).resolve(), Path(a.clean).resolve(), Path(a.cut).resolve()
    if abs(duration(graded) - duration(clean)) > 0.1:
        sys.exit("graded and clean masters differ in length")
    dist = ROOT / "work" / "film-dist" / a.release; dist.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        print("encoding")
        encode_mp4(clean, tmp / "a.mp4"); mp4 = place(tmp / "a.mp4", "mp4", ".mp4")
        encode_webm(graded, tmp / "a.webm"); webm = place(tmp / "a.webm", "webm", ".av1.webm")
        encode_github(clean, dist / "iconflow-film-github-720p.mp4", tmp)
        poster = posters(clean, a.poster_at, tmp)
        caps = captions(cut, tmp)
    master_mb = round(graded.stat().st_size / 1e6)
    shutil.copy2(graded, dist / a.release_master)
    files = {"mp4": mp4, "webm": webm, "posters": poster}
    listed = [mp4, webm, *poster.values(), *(c["file"] for c in caps.values())]
    m = {
        "release": a.release,
        "release_master": a.release_master,
        "release_master_mb": master_mb,
        "release_assets": {a.release_master: sha256(dist / a.release_master),
                           "iconflow-film-github-720p.mp4": sha256(dist / "iconflow-film-github-720p.mp4")},
        "source": {"graded_sha256": sha256(graded), "clean_sha256": sha256(clean), "cut": cut.relative_to(ROOT).as_posix()},
        "files": files,
        "captions": caps,
        "media": {name: {"bytes": (MEDIA / name).stat().st_size, "sha256": sha256(MEDIA / name)} for name in listed},
    }
    # The web deliverables also go up as one zip in the Release, so a clean clone can restore them.
    m["release_assets"]["website-media-film.zip"] = write_bundle(dist / "website-media-film.zip", listed)
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render_page(m)
    prune(keep=set(listed) | previous_names())
    print(f"manifest -> {MANIFEST.relative_to(ROOT)}\nrelease bundle -> {dist.relative_to(ROOT)}")
    print("next: python scripts/build_i18n.py && python scripts/film_publish.py verify")


def write_bundle(bundle: Path, names: list[str]) -> str:
    """Exactly this cut's files, in a fixed order with fixed timestamps, so the zip is reproducible."""
    import zipfile
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_STORED) as z:
        for name in sorted(names):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            z.writestr(info, (MEDIA / name).read_bytes())
    return sha256(bundle)


def previous_names() -> set[str]:
    """Names referenced by the committed manifest at HEAD: kept so a rollback deploy stays whole."""
    out = subprocess.run(["git", "show", f"HEAD:{MANIFEST.relative_to(ROOT).as_posix()}"], cwd=ROOT,
                         capture_output=True, text=True)
    return set(json.loads(out.stdout)["media"]) if out.returncode == 0 else set()


def prune(keep: set[str]) -> None:
    for p in MEDIA.glob("film-*"):
        if p.name not in keep:
            p.unlink(); print(f"  pruned {p.name}")


def verify(_: argparse.Namespace) -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    for name, rec in m["media"].items():
        p = MEDIA / name
        if not p.is_file():
            problems.append(f"missing {name} (run: python scripts/film_publish.py fetch)"); continue
        if p.stat().st_size != rec["bytes"] or sha256(p) != rec["sha256"]:
            problems.append(f"{name} does not match the manifest")
        if p.stat().st_size > 25 * MiB:
            problems.append(f"{name} exceeds Cloudflare Pages' 25 MiB file limit")
    pages = [INDEX] + [ROOT / "website" / d / "index.html" for d in ("es", "ja", "zh-hant", "zh-hans")]
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for name in m["media"]:
            if name.endswith((".mp4", ".webm", ".vtt", ".avif")) and name not in html:
                problems.append(f"{page.relative_to(ROOT)} does not reference {name}")
    if problems:
        sys.exit("\n".join(problems))
    total = sum(r["bytes"] for r in m["media"].values())
    print(f"film {m['release']}: {len(m['media'])} files, {total / MiB:.1f} MiB, all match; pages reference them")


def fetch(_: argparse.Namespace) -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["gh", "release", "download", m["release"], "--repo", REPO, "--pattern", "website-media-film.zip",
                        "--dir", td], check=True)
        z = Path(td) / "website-media-film.zip"
        if sha256(z) != m["release_assets"]["website-media-film.zip"]:
            sys.exit("downloaded bundle does not match the manifest")
        MEDIA.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(z), MEDIA)
    verify(_)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--graded", required=True, help="master with film grain (AV1 source)")
    b.add_argument("--clean", required=True, help="same film without grain (H.264, poster and GitHub source)")
    b.add_argument("--cut", required=True, help="cut directory holding timeline5.json and captions.json")
    b.add_argument("--release", required=True, help="GitHub Release tag, e.g. film-v5")
    b.add_argument("--release-master", default="iconflow-film-4k.mp4")
    b.add_argument("--poster-at", type=float, default=10.25, help="seconds into the clean master for the poster frame")
    b.set_defaults(fn=build)
    sub.add_parser("verify").set_defaults(fn=verify)
    sub.add_parser("fetch").set_defaults(fn=fetch)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
