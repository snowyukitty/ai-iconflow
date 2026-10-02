<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->
# IconFlow film — cut 5

A 45-second, 4K24 launch film for IconFlow as a whole. It is set in the same
sunlit paper desk as cut 4, but it tells a creation story instead of a
diagnosis.

1. A desk of sixteen ordinary letter-on-a-square icons.
2. They flip over, one by one, into sixteen real cases from the 100-case
   Gallery, chosen for range: cel-shaded, clay, woodcut, chrome, ink brush,
   glass, woven, pixel grid, flat and isometric. The sleeping cat for a focus
   timer lands on "cat", and the hooded hero for a story game (`quiet-hero`,
   the film's hero) lands on "hero".
3. On a laptop, the hero's real master SVG is open in an editor and
   `iconflow check` passes. Then comes the real `iconflow compare` sheet of
   three character finalists: `quiet-hero`, `sky-courier` and
   `forest-familiar`.
4. Real files from one `iconflow build --targets all` of that master rise
   beside it, each under its actual file name. `favicon.ico` lands on
   "favicon" and `trayTemplate.png` on "menu bar".
5. A blade sweeps a row of five different Gallery tiles. Behind it, each
   tile's real 16 px raster rises as 256 blocks.
6. The camera climbs over the hero's blocks, and its tray template sits in a
   giant menu bar.
7. End card: IconFlow, "Still itself at 16 px.", and the URL, beside the hero
   and four other tiles. The free X-ray appears only as the closing entry
   point.

## Why cut 4 was replaced

Snowy rejected cut 4's script for two reasons:

- It opened on "2 failures": the X-ray's verdict for a strawman icon made to
  fail.
- It showed a diagnosis, not the app's appeal.

Snowy chose IconFlow as a whole for the hero, shown through real Gallery cases.

A first cut 5 used the Gallery's koi as the hero. Snowy rejected it on
quality grounds and asked for more range. The hero became `quiet-hero`, and
the film now shows 16 + 5 + 5 cases instead of one.

Grok and Codex then reviewed the draft script independently. They agreed on the
same points:

- Say who holds the pen: a person or their coding agent draws the SVG, and
  IconFlow has no image model.
- Name real cases rather than abstractions.
- Keep the human review gate in the shipping line.
- Drop absolutes such as "proven", "people will remember" and "unmistakably".

## Product-truth lanes

| Lane | Source | Truth |
|---|---|---|
| Gallery tiles | `export_rasters.py` renders each Gallery `master.svg` with the X-ray's canvas path | The real masters, byte-copied into `assets/` |
| Letter tiles | `make_textures.py` | Generic stand-ins, deliberately ordinary but not bad |
| Laptop screen | `screen.html`: a vendor-neutral editor showing the real `quiet-hero.svg`, the real `iconflow check` output, then `assets/compare.png` from a real `iconflow compare` run | Every line of code and every sheet pixel is real |
| File tiles | `make_textures.py` runs a real `iconflow build --targets all`. That build writes 22 files, listed in `tex/build-files.txt` | Textures and labels are the actual output files |
| Tray mark | `assets/quiet-hero-tray.svg`: the master's outer silhouette with the visor and collar notch cut through, so the template keeps a face, framed to 15 of 16 px. The X-ray rates it "Survives, with 1 warning" (fades on a dark tab, irrelevant to a template) | Derived and checked, not invented |
| 3D world | Blender 5.2 Cycles (`shots5.py`, reusing cut 4's `scene.py` and `shots.py` helpers) | Block colours are pixels of the real 16 px raster |
| Type | `film5.html` | Claims match the product: 22 files, the named targets, free, open source and local |

## Sound

- **Voice:** ElevenLabs v2 "Eric" (seed 16, speed 1.04), `narration.txt`.
  - Line 2 is a separate take, recorded with its neighbours as context.
  - Lines are anchored to picture events in `timeline5.py`.
  - Each line is cut at the quietest point before the next line's onset.
- **Music:** an ElevenLabs Music render of the composition plan `iconflow-film-v5`, take `4a28e43f`.
  - Sections follow the film's acts: plain, reveal, craft, ship, pixels and
    resolve.
  - Its commercial-use clearance is recorded with the owner's music library.
- **Effects:**
  - soft landings on the tile flips;
  - ticks as the files rise;
  - one tick per column the blade crosses.
- **Mix:** voice ducks the bed, then two-pass loudnorm to -14 LUFS and
  -1.5 dBTP.

## Rebuild

```sh
python export_rasters.py && python make_textures.py
python screen_frames5.py
blender -b --factory-startup -P shots5.py -- --shot all --res 3840 --spp 64
python timeline5.py --mix
python capture5.py --res 3840 --scale 2
```
