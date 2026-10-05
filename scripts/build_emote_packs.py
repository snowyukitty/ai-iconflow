# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Build the downloadable IconFlow emote packs for /emotes/.

Every PNG comes from the same `emote` build target the CLI ships
(`iconflow build --targets emote`), so a pack cannot drift from what the tool
would write for anyone else's emotes. Writes into website/emotes/:

    svg/<slug>.svg                       byte-identical copies of emotes/*.svg
    png/<slug>-128.png                   what the page shows, as platforms store it
    family-sheet.png                     `iconflow family` proof of the set
    iconflow-emotes-twitch.zip           <slug>/<slug>-28|56|112.png
    iconflow-emotes-discord-slack.zip    <slug>.png at 128
    iconflow-emotes-svg.zip              the editable sources, catalog and licence
    catalog.json                         the catalog, plus file paths and sizes

Zips are deterministic (fixed timestamps, sorted members), so rebuilding an
unchanged set changes no bytes.

    python scripts/build_emote_packs.py           # render and write (needs Chromium)
    python scripts/build_emote_packs.py --check   # fail if the packs no longer match emotes/
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "emotes"
OUT = ROOT / "website" / "emotes"
STAMP = (2026, 10, 5, 0, 0, 0)
PACKS = ("iconflow-emotes-twitch.zip", "iconflow-emotes-discord-slack.zip", "iconflow-emotes-svg.zip")
README = """IconFlow emotes — {count} chat reactions, public domain (CC0 1.0).
https://ai-iconflow.com/emotes/

{body}
No attribution and no conditions: upload them, change them, sell what you
make with them. The IconFlow name and mark are not part of the dedication.
"""


def catalog() -> dict:
    return json.loads((SOURCE / "catalog.json").read_text(encoding="utf-8"))


def _zip(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, members[name])
    return buffer.getvalue()


def render() -> dict[str, bytes]:
    """Every file under website/emotes/, as bytes, keyed by relative path."""
    from iconflow import family
    from iconflow.build import RenderCache, preview_assets
    from iconflow.rasterize import Rasterizer, load_svg

    cat = catalog()
    slugs = [e["slug"] for e in cat["emotes"]]
    files: dict[str, bytes] = {}
    twitch: dict[str, bytes] = {}
    chat: dict[str, bytes] = {}
    sources: dict[str, bytes] = {}
    with Rasterizer() as rasterizer:
        for slug in slugs:
            path = SOURCE / f"{slug}.svg"
            assets = preview_assets(RenderCache(load_svg(path), rasterizer), "emote")
            for size in (28, 56, 112):
                twitch[f"{slug}/{slug}-{size}.png"] = assets[f"emote/{size}.png"]
            chat[f"{slug}.png"] = assets["emote/128.png"]
            files[f"png/{slug}-128.png"] = assets["emote/128.png"]
            files[f"svg/{slug}.svg"] = path.read_bytes()
            sources[f"svg/{slug}.svg"] = path.read_bytes()
        fam = family.audit([SOURCE / f"{slug}.svg" for slug in slugs], rasterizer=rasterizer)
        sheet = family.family_sheet(fam, ROOT / "work" / "emotes" / "family-sheet.png", rasterizer=rasterizer)
    files["family-sheet.png"] = sheet.read_bytes()

    licence = (SOURCE / "LICENSE").read_bytes()
    readme = lambda body: README.format(count=len(slugs), body=body).encode("utf-8")  # noqa: E731
    twitch["README.txt"] = readme("Twitch: each folder holds the 28, 56 and 112 px PNGs Twitch asks for in one upload.")
    chat["README.txt"] = readme("Discord and Slack: one 128 px PNG per emote. Upload it as a custom emoji.")
    sources.update({"README.txt": readme("Editable SVG sources on a 1024 grid. Build platform sizes with\n"
                                         "  iconflow build <emote>.svg --targets emote"),
                    "LICENSE": licence, "catalog.json": (SOURCE / "catalog.json").read_bytes()})
    for member in (twitch, chat):
        member["LICENSE"] = licence
    files["iconflow-emotes-twitch.zip"] = _zip(twitch)
    files["iconflow-emotes-discord-slack.zip"] = _zip(chat)
    files["iconflow-emotes-svg.zip"] = _zip(sources)

    published = dict(cat)
    published["emotes"] = [
        {**e, "svg": f"/emotes/svg/{e['slug']}.svg", "png": f"/emotes/png/{e['slug']}-128.png"} for e in cat["emotes"]
    ]
    published["packs"] = {name: len(files[name]) for name in PACKS}
    published["family"] = {"groups": [[Path(m.source).stem for m in g] for g in fam.groups if len(g) > 1],
                           "closest": [{"a": Path(p.a.source).stem, "b": Path(p.b.source).stem,
                                        "residual": round(p.residual, 3)} for p in fam.nearest(3)],
                           "twins": len(fam.twins)}
    files["catalog.json"] = (json.dumps(published, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    files["index.html"] = render_page(published).encode("utf-8")
    files["LICENSE"] = licence
    return files


def _kb(n: int) -> str:
    return f"{round(n / 1024)} KB"


def render_page(published: dict) -> str:
    """website/emotes/index.html, generated from the published catalog."""
    from html import escape

    emotes = published["emotes"]
    by = {e["slug"]: e for e in emotes}
    packs = published["packs"]
    fam = published["family"]
    closest = fam["closest"]

    def img(slug: str, size: int, cls: str = "") -> str:
        e = by[slug]
        klass = f' class="{cls}"' if cls else ""
        return (f'<img{klass} src="{e["png"]}" width="{size}" height="{size}" '
                f'alt=":{slug}:" title=":{slug}:" loading="lazy" decoding="async">')

    def line(name: str, text: str, *slugs: str) -> str:
        inline = " ".join(img(s, 22) for s in slugs)
        return f'<p class="emo-msg"><b>{name}</b> {escape(text)} {inline}</p>'

    def chat(theme: str, label: str) -> str:
        return f"""        <figure class="emo-chat emo-chat-{theme}">
          <figcaption>{label}</figcaption>
          {line("mika", "we shipped the release", "rocket", "tada")}
          {line("jo", "the build was green on the first try?", "shock")}
          {line("mika", "first try. no rebase.", "cool", "sparkles")}
          {line("sam", "i have been staring at the diff for an hour", "melting")}
          {line("jo", "standup is cancelled", "salute")}
          <p class="emo-reactions">{"".join(f'<span>{img(s, 22)}<i>{n}</i></span>' for s, n in (("thumbsup", 12), ("check", 9), ("heart", 7), ("joy", 4), ("eyes", 2)))}</p>
        </figure>"""

    def tile(e: dict) -> str:
        return f"""        <li class="emo-tile">
          <div class="emo-big">{img(e['slug'], 112)}</div>
          <div class="emo-small" aria-hidden="true"><span class="emo-on-light">{img(e['slug'], 22)}{img(e['slug'], 28)}</span><span class="emo-on-dark">{img(e['slug'], 22)}{img(e['slug'], 28)}</span></div>
          <p class="emo-name">{escape(e['title'])} <code>:{e['slug']}:</code></p>
          <p class="emo-links"><a href="{e['svg']}" download>SVG</a><a href="{e['png']}" download>PNG 128</a></p>
        </li>"""

    kinds = (("face", "Faces"), ("hand", "Hands"), ("symbol", "Symbols"))
    sections = "\n".join(
        f"""      <h3 class="emo-kind" id="{kind}s">{label} <span>{sum(1 for e in emotes if e['kind'] == kind)}</span></h3>
      <ul class="emo-grid">
""" + "\n".join(tile(e) for e in emotes if e["kind"] == kind) + """
      </ul>"""
        for kind, label in kinds if any(e["kind"] == kind for e in emotes)
    )
    pairs = ", ".join(f"<em>{escape(by[c['a']]['title'].lower())} / {escape(by[c['b']]['title'].lower())}</em> at {c['residual']:.2f}"
                      for c in closest[:2])
    carried = fam["groups"][0] if fam["groups"] else []
    faces = len(carried)
    guests = [by[slug]["title"].lower() for slug in carried if by[slug]["kind"] != "face"]
    joined = "every face" + (f", and the {' and the '.join(guests)} drawn on the same card" if guests else "")
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage", "name": "IconFlow emotes",
        "url": "https://ai-iconflow.com/emotes/", "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "description": f"{len(emotes)} chat emotes drawn as one family, public domain, with upload packs for Twitch, Discord and Slack.",
        "isPartOf": {"@type": "WebSite", "name": "IconFlow", "url": "https://ai-iconflow.com/"},
        "hasPart": [{"@type": "ImageObject", "name": e["title"], "contentUrl": f"https://ai-iconflow.com{e['svg']}",
                     "license": "https://creativecommons.org/publicdomain/zero/1.0/"} for e in emotes],
    }, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<!-- Generated by scripts/build_emote_packs.py from emotes/catalog.json. Do not edit; rebuild. -->
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IconFlow emotes — {len(emotes)} free chat emotes for Twitch, Discord and Slack | IconFlow</title>
  <meta name="description" content="{len(emotes)} chat reactions drawn as one family and checked at the 22 and 28 pixels chat actually uses. Public domain (CC0), with ready upload packs for Twitch, Discord and Slack.">
  <meta name="theme-color" content="#111216">
  <meta name="color-scheme" content="dark">
  <meta property="og:type" content="website">
  <meta property="og:title" content="IconFlow emotes: {len(emotes)} reactions, still themselves at 22px">
  <meta property="og:description" content="One family of chat emotes on IconFlow's app-icon card. Free to use for anything (CC0), with upload packs for Twitch, Discord and Slack.">
  <meta property="og:url" content="https://ai-iconflow.com/emotes/">
  <meta property="og:image" content="https://ai-iconflow.com/assets/marketing/emotes-1200x630.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="The IconFlow emote set: {len(emotes)} chat reactions on rounded-square heads, shown in light and dark chat.">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://ai-iconflow.com/assets/marketing/emotes-1200x630.png">
  <link rel="canonical" href="https://ai-iconflow.com/emotes/">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <link rel="stylesheet" href="/styles.css?v=20261001a">
  <link rel="stylesheet" href="/emotes/emotes.css?v=20261005a">
  <script src="/app.js?v=20261001a" defer></script>
  <script type="application/ld+json">{jsonld}</script>
</head>
<body class="emo-body">
  <a class="skip-link" href="#main">Skip to content</a>

  <header class="site-header" data-header>
    <a class="brand" href="/" aria-label="IconFlow home"><img src="/assets/iconflow-mark.svg" width="34" height="34" alt=""><span>IconFlow</span></a>
    <button class="menu-button" type="button" aria-expanded="false" aria-controls="site-nav" data-menu data-label-open="Open navigation" data-label-close="Close navigation"><span class="sr-only">Toggle navigation</span><span></span><span></span></button>
    <nav id="site-nav" class="site-nav" aria-label="Primary navigation"><a href="/emotes/" aria-current="page">Emotes</a><a href="/forge/">Icon Forge</a><a href="/xray/">16px X-ray</a><a href="/gallery/">Gallery</a><a href="/getting-started/">Get started</a></nav>
  </header>

  <main id="main">
    <section class="emo-hero section-shell">
      <div class="emo-hero-copy">
        <p class="section-kicker">IconFlow emotes · {len(emotes)} reactions · public domain</p>
        <h1>Emotes that are still <em>themselves</em> at 22 pixels.</h1>
        <p class="emo-lede">Chat draws an emote at 22 to 28 pixels, on white and on dark, from the file you uploaded. So this set was drawn for those pixels: every face sits on the rounded-square card IconFlow ships as an app icon, every line is thick enough to survive, and no two members read as the same reaction.</p>
        <div class="emo-actions">
          <a class="button button-primary" href="/emotes/iconflow-emotes-twitch.zip" download>Twitch pack <span class="emo-size">28 · 56 · 112 px · {_kb(packs['iconflow-emotes-twitch.zip'])}</span></a>
          <a class="button button-quiet" href="/emotes/iconflow-emotes-discord-slack.zip" download>Discord &amp; Slack pack <span class="emo-size">128 px · {_kb(packs['iconflow-emotes-discord-slack.zip'])}</span></a>
          <a class="button button-quiet" href="/emotes/iconflow-emotes-svg.zip" download>SVG sources <span class="emo-size">{_kb(packs['iconflow-emotes-svg.zip'])}</span></a>
        </div>
        <p class="emo-licence">CC0: use them anywhere, change them, sell what you make. No credit needed.</p>
      </div>
      <div class="emo-chats">
{chat("light", "Light chat")}
{chat("dark", "Dark chat")}
      </div>
    </section>

    <section class="emo-set section-shell" aria-labelledby="emo-set-title">
      <h2 id="emo-set-title">The set</h2>
      <p class="emo-note">Shown as platforms show them: each image is the 128-pixel upload, scaled down by your browser. The small pair under each one is 22 and 28 pixels on light and dark chat.</p>
{sections}
    </section>

    <section class="emo-family section-shell">
      <div>
        <p class="section-kicker">Proven as a family</p>
        <h2>One family. No twins.</h2>
        <p>A set has to pass two tests that pull in opposite directions: its members must look related, and no two may be the same reaction at chat size. <code>iconflow family</code> measures both. It finds the card {faces} members share from their 16-pixel fields alone — {joined} — sets it aside, and compares what is left. The closest siblings are {pairs}, against a floor of 0.33.</p>
        <p>The first draft's wink was the smile with one eye closed. It came back at 0.31 — a twin — and at 22 pixels it was: one eye is two pixels. The wink you see squeezes its eye shut <em>and</em> opens its grin.</p>
        <p><a href="https://github.com/snowyukitty/ai-iconflow/blob/main/docs/FAMILY.md">How the family check works</a> · <a href="https://github.com/snowyukitty/ai-iconflow/blob/main/docs/EMOTES.md">The emote grammar</a></p>
      </div>
      <figure class="emo-sheet">
        <img src="/emotes/family-sheet.png" width="958" height="1024" alt="The iconflow family proof sheet: the closest pairs of emotes side by side at 22 and 28 pixels, each with a residual distance above the twin floor." loading="lazy" decoding="async">
        <figcaption>The proof sheet <code>iconflow family</code> wrote for this set.</figcaption>
      </figure>
    </section>

    <section class="emo-make section-shell">
      <div>
        <p class="section-kicker">Make your own</p>
        <h2>Same checks, your emotes.</h2>
        <p>The packs above come out of the same build target anyone can run. Draw on the 1024 grid, then let IconFlow write every platform size, refuse a file over its upload limit, and tell you which of your emotes are twins.</p>
        <p class="emo-note">The <code>emote</code> target and <code>iconflow family</code> are newer than the release on PyPI (0.5.0). Until the next release, install IconFlow from GitHub as shown.</p>
      </div>
<pre><code>pip install "git+https://github.com/snowyukitty/ai-iconflow"
iconflow setup
iconflow build my-emote.svg --targets emote --out out
iconflow family "emotes/*.svg" --sheet family.png</code></pre>
    </section>
  </main>

  <footer class="site-footer section-shell">
    <div class="footer-brand"><img src="/assets/iconflow-mark.svg" width="40" height="40" alt=""><div><strong>IconFlow</strong><span>One master. Every surface.</span></div></div>
    <p>The IconFlow emotes are public domain (CC0 1.0). The IconFlow name and mark are not.</p>
    <nav aria-label="Footer navigation"><a href="/">Home</a><a href="/forge/">Icon Forge</a><a href="/xray/">16px X-ray</a><a href="/reference/icon-sizes/#emote">Emote sizes</a><a href="https://github.com/snowyukitty/ai-iconflow/tree/main/emotes">Source</a></nav>
  </footer>
</body>
</html>
"""


def check() -> int:
    """Without a browser: sources copied byte for byte, packs complete."""
    cat = catalog()
    slugs = sorted(e["slug"] for e in cat["emotes"])
    problems = []
    for slug in slugs:
        published = OUT / "svg" / f"{slug}.svg"
        if not published.is_file() or published.read_bytes() != (SOURCE / f"{slug}.svg").read_bytes():
            problems.append(f"svg/{slug}.svg differs from emotes/{slug}.svg")
        if not (OUT / "png" / f"{slug}-128.png").is_file():
            problems.append(f"png/{slug}-128.png missing")
    expected = {
        "iconflow-emotes-twitch.zip": {f"{s}/{s}-{n}.png" for s in slugs for n in (28, 56, 112)} | {"README.txt", "LICENSE"},
        "iconflow-emotes-discord-slack.zip": {f"{s}.png" for s in slugs} | {"README.txt", "LICENSE"},
        "iconflow-emotes-svg.zip": {f"svg/{s}.svg" for s in slugs} | {"README.txt", "LICENSE", "catalog.json"},
    }
    for name, members in expected.items():
        path = OUT / name
        if not path.is_file():
            problems.append(f"{name} missing")
            continue
        with zipfile.ZipFile(path) as archive:
            if set(archive.namelist()) != members:
                problems.append(f"{name} does not hold exactly the current set")
            if name == "iconflow-emotes-svg.zip":
                for s in slugs:
                    if archive.read(f"svg/{s}.svg") != (SOURCE / f"{s}.svg").read_bytes():
                        problems.append(f"{name}: svg/{s}.svg is stale")
    published = json.loads((OUT / "catalog.json").read_text(encoding="utf-8")) if (OUT / "catalog.json").is_file() else {}
    if [e.get("slug") for e in published.get("emotes", [])] != [e["slug"] for e in cat["emotes"]]:
        problems.append("catalog.json does not list the current set")
    elif (OUT / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n") != render_page(published):
        problems.append("index.html is not the page this catalog renders")
    for problem in problems:
        print(f"  {problem}")
    if problems:
        print("emote packs are stale; run python scripts/build_emote_packs.py")
        return 1
    print(f"emote packs verify: OK - {len(slugs)} emotes, {len(PACKS)} packs")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify without rendering")
    args = parser.parse_args(argv)
    if args.check:
        return check()
    files = render()
    for rel, data in files.items():
        target = OUT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f"wrote {len(files)} files to {OUT.relative_to(ROOT)}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
