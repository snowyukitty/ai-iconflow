# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Cut-5 animated 3D shots: IconFlow as a whole, told with real gallery cases.

Same sunlit paper desk as cut 4 (its world, blocks, blade, laptop and menu bar
are imported from ../cut4). Every frame is a pure function of its time.

    blender -b --factory-startup -P shots5.py -- --shot flip --res 960 --spp 32 --frames 0,96,150
    blender -b --factory-startup -P shots5.py -- --shot all --res 3840 --spp 64

Shots (seconds are shot-local; timeline5.py places them):
  flip     10.5 s  a 4x4 grid of letter-on-a-square tiles flips over into sixteen real gallery icons
  laptop   10.0 s  the hero SVG in an editor, `iconflow check`, then the real `compare` sheet
  family    6.5 s  the hero master, then real files from one `iconflow build` rise beside it
  pixels    5.5 s  a blade sweeps a row of five gallery tiles; behind it each real 16 px raster rises as blocks
  topdown   3.0 s  the camera climbs over the hero's 16 px blocks, its neighbours at the edges
  traybar   3.0 s  the hero's tray template, as blocks, in a giant menu bar
  endtile   6.5 s  the hero tile among a few others in morning light for the end card
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cut4"))
import scene as S  # noqa: E402
import shots as K  # noqa: E402  (cut-4 helpers)

S.TEX = HERE / "tex"
ROOT = HERE.parents[3]
OUTROOT = ROOT / "work" / "promo-xray" / "cg5"
FPS = 24
SIZE = K.SIZE

SHOTS = {"flip": 10.5, "laptop": 10.0, "family": 6.5, "pixels": 5.5, "topdown": 3.0, "traybar": 3.0, "endtile": 6.5}

clamp, prog, ease, inout, back, lerp, vlerp = K.clamp, K.prog, K.ease, K.inout, K.back, K.lerp, K.vlerp
lin = K.srgb_to_lin


def hexlin(h): return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5)) + (1,)


CREAM = "#F1EADC"
# Gallery case -> (card colour, card corner radius in the 944 px card). Cases
# without a card of their own sit on a cream ceramic tile.
CARDS = {"catnap-focus": ("#CFE6E1", 244), "forest-familiar": ("#E7C58E", 212), "quiet-hero": ("#F4EADA", 212),
         "boss-helm": ("#11151E", 212), "keepsake-knot": ("#251D32", 212), "sky-courier": ("#F2E7D2", 212),
         "co-op-lock": ("#151927", 212)}
HERO = "quiet-hero"


def card_of(name): return CARDS.get(name, (CREAM, 212))


# ---------- a two-sided physical tile ----------

def face_plane(name, texture, size, z, flip=False, closest=False, full=False):
    # Inset so the printed card stops just inside the slab's bevel.
    c = size if full else size * 944 / 1024
    bpy.ops.mesh.primitive_plane_add(size=size * (c - 0.03) / c, location=(0, 0, z))
    face = bpy.context.object; face.name = name
    if flip: face.rotation_euler = (math.pi, 0, 0)
    fm, fb = S.mat(name, **{"Roughness": 0.4, "Coat Weight": 0.5, "Coat Roughness": 0.1})
    tex = S.image_node(fm.node_tree, texture)
    if closest: tex.interpolation = "Closest"
    fm.node_tree.links.new(tex.outputs["Color"], fb.inputs["Base Color"])
    fm.node_tree.links.new(tex.outputs["Alpha"], fb.inputs["Alpha"])
    face.data.materials.append(fm)
    return face


def tile5(name, texture, size=SIZE, back_texture=None, closest=False, card=None, full=False):
    """A ceramic tile the size of the icon's own card, its face printed with the
    real raster. With back_texture the tile is two-sided and centred on its
    pivot, so it can flip over in place."""
    colour, rx = card or card_of(name)
    c = size if full else size * 944 / 1024; depth = 0.09
    slab = S.rounded_rect(c, c * rx / 944, depth); slab.name = f"slab-{name}"
    bev = slab.modifiers.new("bevel", "BEVEL"); bev.width = 0.018; bev.segments = 6; bev.limit_method = "ANGLE"
    m, _ = S.mat(f"ceramic-{name}", **{"Base Color": hexlin(colour), "Roughness": 0.32, "Coat Weight": 0.4, "Coat Roughness": 0.12})
    slab.data.materials.append(m)
    for p in slab.data.polygons: p.use_smooth = True
    grp = bpy.data.objects.new(f"tile-{name}", None); bpy.context.collection.objects.link(grp)
    if back_texture is None:
        face = face_plane(f"face-{name}", texture, size, depth + 0.0005, closest=closest, full=full)
        slab.parent = grp; face.parent = grp
    else:
        slab.location.z = -depth / 2
        top = face_plane(f"face-{name}-letter", back_texture, size, depth / 2 + 0.0005)
        bottom = face_plane(f"face-{name}", texture, size, -depth / 2 - 0.0005, flip=True)
        for o in (slab, top, bottom): o.parent = grp
        grp["half"] = depth / 2; grp["card"] = c
    return grp


def label(txt, loc, size=0.16, weight="Medium", align="CENTER", ink=(0.03, 0.028, 0.025, 1)):
    cu = bpy.data.curves.new(txt, "FONT"); cu.body = txt; cu.size = size
    cu.align_x = align; cu.align_y = "CENTER"
    cu.font = bpy.data.fonts.load(str(K.FONTS / f"Inter-{weight}.ttf"), check_existing=True); cu.extrude = 0.002
    ob = bpy.data.objects.new(txt, cu); bpy.context.collection.objects.link(ob)
    ob.location = loc
    tm, _ = S.mat("ink-" + txt, **{"Base Color": ink, "Roughness": 0.6})
    ob.data.materials.append(tm)
    return ob


# ---------- camera paths ----------

def hermite(keys, t):
    """Catmull-Rom through (time, value) keys with eased ends: smooth, never stops mid-path."""
    if t <= keys[0][0]: return Vector(keys[0][1])
    if t >= keys[-1][0]: return Vector(keys[-1][1])
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= t)
    (t0, p0), (t1, p1) = keys[i], keys[i + 1]
    pm = Vector(keys[i - 1][1]) if i > 0 else Vector(p0)
    pp = Vector(keys[i + 2][1]) if i + 2 < len(keys) else Vector(p1)
    p0, p1 = Vector(p0), Vector(p1)
    u = (t - t0) / (t1 - t0)
    if i == 0: u = u * u * (2 - u) if False else u          # keep linear inside; ends are eased by tangents
    m0 = (p1 - pm) * 0.5 if i > 0 else Vector((0, 0, 0))
    m1 = (pp - p0) * 0.5 if i + 2 < len(keys) else Vector((0, 0, 0))
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * m1


# ---------- shots ----------

# Sixteen cases chosen for range: cel-shaded, clay, woodcut, chrome, ink brush,
# glass, woven, pixel grid, flat geometry and isometric.
GRID = ["sky-courier", "forest-familiar", "co-op-lock", "record-sleeve",
        "tomato-pincushion", "boss-helm", "keepsake-knot", "octopus-curl",
        "save-cartridge", "catnap-focus", "quiet-hero", "sunflower-disc",
        "storm-parasol", "folded-map-folio", "mech-pauldron", "accordion-bellows"]
LETTERS = "KMTASPNRDLFCGBHE"
FLIP_DUR = 0.72
FLIP_AT = {"catnap-focus": 4.33 - FLIP_DUR, "quiet-hero": 6.30 - FLIP_DUR}    # land on "cat" and "hero"
CASCADE = ["octopus-curl", "boss-helm", "folded-map-folio", "sky-courier", "save-cartridge", "keepsake-knot",
           "storm-parasol", "forest-familiar", "sunflower-disc", "record-sleeve", "tomato-pincushion",
           "mech-pauldron", "co-op-lock", "accordion-bellows"]
for n, name in enumerate(CASCADE):
    FLIP_AT[name] = 6.6 + n * 0.14
PITCH = 2.45


def grid_pos(i):
    col, row = i % 4, i // 4
    return Vector(((col - 1.5) * PITCH, (1.5 - row) * PITCH, 0))


def flip_state(grp, t, t0):
    k = inout(prog(t, t0, t0 + FLIP_DUR))
    th = math.pi * k
    half, card = grp["half"], grp["card"]
    lift = 0.06 * math.sin(math.pi * k)
    grp.rotation_euler = (-th, 0, 0)                            # the far edge rises and comes toward camera
    grp.location.z = half * abs(math.cos(th)) + card / 2 * math.sin(th) + lift
    return k


def shot_flip(frames, render):
    S.reset(); S.world(scale=1.8)
    tiles = []
    for i, name in enumerate(GRID):
        g = tile5(name, S.TEX / f"{name}-1024.png", size=2.0, back_texture=S.TEX / f"letter-{LETTERS[i]}.png")
        g.location = grid_pos(i); tiles.append((name, g))
    cam, tgt = K.cam_rig(55, 2.4)
    # Low across the plain letters, onto the cat, across to the hero, then up over all sixteen.
    P = [(0.0, (-5.6, -7.6, 1.5)), (3.4, (-3.4, -6.9, 2.2)), (5.8, (-0.6, -6.8, 2.6)), (8.3, (0.4, -10.0, 7.0)), (10.5, (0.5, -12.6, 11.2))]
    L = [(0.0, (-2.8, -2.6, 0.0)), (3.4, (-1.6, -1.4, 0.0)), (5.8, (0.9, -1.2, 0.0)), (8.3, (0.2, -0.6, 0.0)), (10.5, (0.0, -0.2, 0.0))]
    for f in frames:
        t = f / FPS
        for name, g in tiles:
            flip_state(g, t, FLIP_AT[name])
        lens = lerp(55, 42, inout(prog(t, 5.8, 10.5)))
        K.place(cam, tgt, hermite(P, t), hermite(L, t), lens=lens, fstop=lerp(2.4, 4.8, inout(prog(t, 5.2, 10.5))))
        render(f)


def shot_laptop(frames, render):
    S.reset(); S.world(scale=4.0)
    tex = K.laptop()
    seq = ROOT / "work" / "promo-xray" / "screen5-seq"
    cam, tgt = K.cam_rig(50, 2.2)
    centre = Vector((0, 4.15 + 4.1 * math.cos(math.radians(72)), 0.28 + 4.1 * math.sin(math.radians(72))))
    for f in frames:
        t = f / FPS
        tex.image = bpy.data.images.load(str(seq / f"{min(f, 239):04d}.png"), check_existing=True)
        k = inout(prog(t, 0.0, 10.0))
        pos = vlerp((-4.6, -11.6, 6.9), (-1.7, -10.4, 6.2), k)
        K.place(cam, tgt, pos, centre + Vector((lerp(-0.6, 0.2, k), 0, 0.35)), lens=lerp(44, 50, k))
        render(f)
        old = bpy.data.images.get(f"{f - 3:04d}.png")
        if old: bpy.data.images.remove(old)


# The master, then real files from one `iconflow build` of it (see tex/build-files.txt).
FAMILY = [  # (texture under tex/, label, physical size, pixel-exact)
    (f"{HERO}-2048.png", f"{HERO}.svg", 2.4, False),
    ("build/icon-512-maskable.png", "icon-512-maskable.png", 1.9, False),
    ("build/apple-touch-icon.png", "apple-touch-icon.png", 1.6, False),
    ("build/icons/64x64.png", "icons/64x64.png", 1.35, True),
    ("build/icons/32x32.png", "icons/32x32.png", 1.15, True),
    ("favicon-16.png", "favicon.ico", 1.0, True),
    ("build/tray/trayTemplate.png", "trayTemplate.png", 1.0, True),
]
FAMILY_RISE = [None, 0.9, 1.4, 1.85, 2.2, 2.45, 4.6]           # favicon.ico lands on "favicon", the tray mark on "menu bar"


def family_layout():
    xs, x = [], 0.0
    for n, (_, _, s, _) in enumerate(FAMILY):
        if n: x += FAMILY[n - 1][2] / 2 + 0.55 + s / 2
        xs.append(x)
    return xs


def shot_family(frames, render):
    S.reset(); S.world(scale=2.4)
    xs = family_layout(); objs = []
    for n, ((tex, text, size, exact), x) in enumerate(zip(FAMILY, xs)):
        full = "maskable" in tex or "apple-touch" in tex          # full-bleed squares; the platform rounds them
        card = ("#F4EFE6", 212) if "trayTemplate" in tex else ((card_of(HERO)[0], 60) if full else card_of(HERO))
        g = tile5(f"fam{n}", S.TEX / tex, size=size * (944 / 1024 if full else 1), closest=exact, card=card, full=full)
        g.location = (x, 0, 0)
        lb = label(text, (x, -size * 944 / 1024 / 2 - 0.32, 0.001), size=0.15, weight="Medium")
        objs.append((g, lb))
    cam, tgt = K.cam_rig(50, 3.2)
    for f in frames:
        t = f / FPS
        for n, (g, lb) in enumerate(objs):
            if FAMILY_RISE[n] is None: continue
            k = prog(t, FAMILY_RISE[n], FAMILY_RISE[n] + 0.5)
            g.hide_render = lb.hide_render = k <= 0
            g.location.z = lerp(-0.12, 0.0, back(k, 1.2))
            lb.location.z = -0.01 + 0.011 * ease(prog(t, FAMILY_RISE[n] + 0.25, FAMILY_RISE[n] + 0.6))
        k = inout(prog(t, 0.0, 6.5))
        look = Vector((lerp(0.6, xs[-1] - 1.0, k), lerp(0.05, -0.25, k), 0))
        pos = look + Vector((lerp(-2.0, -1.0, k), lerp(-6.2, -5.4, k), lerp(4.6, 3.9, k)))
        K.place(cam, tgt, pos, look, lens=lerp(45, 50, k))
        render(f)


# ---------- a row of icons, each rising as its own 16 px blocks ----------

ROW = ["save-cartridge", "octopus-curl", HERO, "boss-helm", "record-sleeve"]
ROW_PITCH = 3.0
CELL = K.CELL
SCAN = (0.5, 3.6)                       # the blade crosses the whole row at a constant speed


def row_x(i): return (i - (len(ROW) - 1) / 2) * ROW_PITCH


def row_blocks():
    """Five 16x16 block fields, one per ROW icon, with the real raster of each."""
    fields = []
    for i, name in enumerate(ROW):
        blocks = K.block_field(); src = K.raster(f"{name}-16.png")
        fields.append((row_x(i), blocks, src))
    return fields


def put_block(ob, ox, x, y, rise, colour, alpha):
    K.set_block(ob, x, y, rise, colour, alpha=alpha)
    ob.location.x += ox


def blade_x(t):
    x0, x1 = row_x(0) - SIZE / 2 - 0.15, row_x(len(ROW) - 1) + SIZE / 2 + 0.15
    return x0, x1, lerp(x0, x1, prog(t, *SCAN))


def shot_pixels(frames, render):
    S.reset(); S.world(scale=1.6)
    tiles = []
    for i, name in enumerate(ROW):
        tl = tile5(name, S.TEX / f"{name}-2048.png"); tl.location.x = row_x(i)
        cut, _ = K.face_mask(tl); cutter = K.slab_cutter(tl)
        tiles.append((cut, cutter))
    fields = row_blocks(); bl = K.blade()
    cam, tgt = K.cam_rig(40, 4.0)
    for f in frames:
        t = f / FPS
        x0, x1, bx = blade_x(t)
        bl.location = (bx, 0, 0.30); bl.hide_render = not (SCAN[0] - 0.2 < t < SCAN[1] + 0.15)
        for cut, cutter in tiles:
            cut.inputs[1].default_value = bx; cutter.location = (bx - 10, 0, 0)
        for ox, blocks, src in fields:
            for (x, y), ob in blocks.items():
                cx = ox + (x - 7.5) * CELL
                passed = (t + 0.06 - lerp(SCAN[0], SCAN[1], prog(cx, x0, x1))) / 0.22
                r, g, b, a = src[(x, y)]
                put_block(ob, ox, x, y, back(clamp(passed)), (r, g, b, 1), a)
        # All five in frame while the blade crosses them, then a push in onto the hero in the middle.
        k = inout(prog(t, 2.6, 5.5))
        look = Vector((0.0, lerp(1.6, 0.0, k), 0.05))
        K.place(cam, tgt, look + Vector((lerp(-1.4, -1.2, k), lerp(-13.2, -6.4, k), lerp(5.9, 5.0, k))), look, lens=lerp(30, 42, k))
        render(f)


def shot_topdown(frames, render):
    S.reset(); S.world(scale=1.6)
    for ox, blocks, src in row_blocks():
        for (x, y), ob in blocks.items():
            put_block(ob, ox, x, y, 1, src[(x, y)][:3] + (1,), src[(x, y)][3])
    cam, tgt = K.cam_rig(50, 4.0)
    for f in frames:
        t = f / FPS
        k = inout(prog(t, 0, 1.8)); push = ease(prog(t, 1.8, 3.0))
        K.place(cam, tgt, vlerp((-1.2, -6.4, 5.0), (0.0, -0.02, 7.4 - 0.5 * push), k), vlerp((0, 0, 0.05), (0, 0, 0), k))
        render(f)


def shot_traybar(frames, render):
    S.reset(); S.world()
    blocks = K.block_field(); tray = K.raster(f"{HERO}-tray-16.png"); K.menubar()
    for (x, y), ob in blocks.items():
        K.set_block(ob, x, y, 1, (0.004, 0.004, 0.005, 1), gap=0.0, alpha=tray[(x, y)][3])   # template: alpha only
        ob.location.z += 0.12
    cam, tgt = K.cam_rig(42, 5.6)
    for f in frames:
        t = f / FPS
        k = ease(prog(t, 0, 3.0))
        K.place(cam, tgt, vlerp((-2.2, -9.0, 6.6), (-1.6, -7.6, 5.9), k), (-1.6, 0.3, 0))
        render(f)


END_TILES = [  # (case, x, y, size, z-rotation in degrees)
    (HERO, 2.4, 0.2, 2.4, 0),
    ("catnap-focus", 4.7, 2.3, 1.8, -9),
    ("boss-helm", 2.2, 2.75, 1.6, 7),
    ("octopus-curl", 5.0, -0.3, 1.7, 11),
    ("save-cartridge", 4.0, -2.4, 1.5, -6),
]


def shot_endtile(frames, render):
    S.reset(); S.world()
    for name, x, y, size, rz in END_TILES:
        tex = S.TEX / (f"{HERO}-2048.png" if name == HERO else f"{name}-1024.png")
        tl = tile5(name, tex, size=size)
        tl.location = (x, y, 0); tl.rotation_euler = (0, 0, math.radians(rz))
    cam, tgt = K.cam_rig(50, 2.8)
    for f in frames:
        t = f / FPS
        k = inout(prog(t, 0, 6.5))
        K.place(cam, tgt, vlerp((0.6, -7.0, 7.6), (0.4, -6.4, 7.0), k), (1.4, 0.3, 0))
        render(f)


SHOT_FN = {"flip": shot_flip, "laptop": shot_laptop, "family": shot_family, "pixels": shot_pixels,
           "topdown": shot_topdown, "traybar": shot_traybar, "endtile": shot_endtile}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
    names = list(SHOTS) if opt.get("shot", "all") == "all" else opt["shot"].split(",")
    res = int(opt.get("res", 960)); spp = int(opt.get("spp", 32))
    only = opt.get("frames")
    for name in names:
        total = int(round(SHOTS[name] * FPS))
        frames = [int(v) for v in only.split(",")] if only else list(range(total))
        out = OUTROOT / f"{name}-{res}"; out.mkdir(parents=True, exist_ok=True)

        def render(f, out=out):
            sc = bpy.context.scene
            sc.render.resolution_x, sc.render.resolution_y = res, res * 9 // 16
            sc.cycles.samples = spp
            sc.render.filepath = str(out / f"{f:04d}.png")
            bpy.ops.render.render(write_still=True)
        SHOT_FN[name](frames, render)
        print(f"shot {name}: {len(frames)} frames -> {out}", flush=True)


if __name__ == "__main__":
    main()
