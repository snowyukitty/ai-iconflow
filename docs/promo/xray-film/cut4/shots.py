# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Cut-4 animated 3D shots. Every frame is a pure function of its time.

    blender -b --factory-startup -P shots.py -- --shot scan --res 960 --spp 32
    blender -b --factory-startup -P shots.py -- --shot all --res 3840 --spp 128

Shots (seconds are shot-local; the film timeline places them):
  macro    4.5 s  the icon develops on the tile face; macro dolly across the chart
  scan     5.0 s  a light blade sweeps the tile; behind it the real 16 px raster rises as blocks
  topdown  4.5 s  the camera climbs to look straight down on the 16 px field
  square   6.5 s  colour drains, the gaps close, and a giant menu bar is revealed under it
  fix      4.5 s  the blade sweeps again and the blocks rebuild as the bold favicon
  traybar  2.5 s  the menu bar again, with the dedicated tray mark built from blocks
  endtile  5.0 s  the rebuilt tile in morning light for the end card
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scene as S  # noqa: E402

ROOT = HERE.parents[3]
FONTS = ROOT / "work" / "tools" / "fonts" / "extras" / "ttf"
OUTROOT = ROOT / "work" / "promo-xray" / "cg"
FPS = 24
SIZE = 2.4
CELL = SIZE / 16

SHOTS = {"macro": 4.5, "scan": 5.0, "topdown": 3.5, "square": 6.5, "laptop": 8.0, "fix": 3.0, "traybar": 3.0, "endtile": 6.0}


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def ease(x): return 1 - (1 - x) ** 3
def inout(x): return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.4): x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k
def vlerp(a, b, k): return Vector(a).lerp(Vector(b), k)


def srgb_to_lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def raster(name):
    img = bpy.data.images.load(str(S.TEX / name)); w, h = img.size
    px = list(img.pixels[:]); grid = {}
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[(y * w + x) * 4:(y * w + x) * 4 + 4]
            grid[(x, y)] = (srgb_to_lin(r), srgb_to_lin(g), srgb_to_lin(b), a)
    return grid


# ---------- objects ----------

def block_field():
    m, b = S.mat("block", **{"Roughness": 0.34, "Coat Weight": 0.35, "Coat Roughness": 0.14})
    info = m.node_tree.nodes.new("ShaderNodeObjectInfo")
    m.node_tree.links.new(info.outputs["Color"], b.inputs["Base Color"])
    bpy.ops.mesh.primitive_cube_add(size=1)
    proto = bpy.context.object; proto.scale = (CELL, CELL, CELL); bpy.ops.object.transform_apply(scale=True)
    bv = proto.modifiers.new("bevel", "BEVEL"); bv.width = CELL * 0.1; bv.segments = 4
    proto.data.materials.append(m)
    for p in proto.data.polygons: p.use_smooth = True
    blocks = {}
    for y in range(16):
        for x in range(16):
            ob = proto.copy(); bpy.context.collection.objects.link(ob)
            ob.location = ((x - 7.5) * CELL, (y - 7.5) * CELL, -CELL)
            blocks[(x, y)] = ob
    bpy.data.objects.remove(proto)
    return blocks


def set_block(ob, x, y, rise, color, gap=0.08, alpha=1.0):
    """rise 0 = sunk in the desk, 1 = standing; alpha < 0.5 keeps it hidden."""
    s = 1 - gap
    if alpha < 0.5 or rise <= 0:
        ob.hide_render = True; return
    ob.hide_render = False
    ob.scale = (s, s, 1)
    ob.location = ((x - 7.5) * CELL, (y - 7.5) * CELL, lerp(-CELL / 2, CELL / 2, rise))
    ob.color = color


def blade():
    """A thin pane of light that does the scanning."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object; ob.name = "blade"; ob.scale = (0.014, 2.9, 0.014)
    m, b = S.mat("blade", **{"Base Color": (1, 1, 1, 1), "Emission Color": (0.80, 0.90, 1.0, 1), "Emission Strength": 22.0, "Roughness": 0.2})
    ob.data.materials.append(m)
    ob.visible_shadow = False
    return ob


def face_mask(tile_grp):
    """Make the icon face transparent left of a world-space x, so the blade can eat it."""
    face = [c for c in tile_grp.children if c.name.startswith("face")][0]
    nt = face.active_material.node_tree; n = nt.nodes; l = nt.links
    bsdf = n["Principled BSDF"]
    tex = [x for x in n if x.type == "TEX_IMAGE"][0]
    geo = n.new("ShaderNodeNewGeometry"); sep = n.new("ShaderNodeSeparateXYZ")
    cmp = n.new("ShaderNodeMath"); cmp.operation = "GREATER_THAN"; cmp.name = "cut"; cmp.inputs[1].default_value = -99
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    dev = n.new("ShaderNodeMath"); dev.operation = "MULTIPLY"; dev.name = "develop"; dev.inputs[1].default_value = 1.0
    l.new(geo.outputs["Position"], sep.inputs["Vector"]); l.new(sep.outputs["X"], cmp.inputs[0])
    l.new(tex.outputs["Alpha"], mul.inputs[0]); l.new(cmp.outputs[0], mul.inputs[1])
    l.new(mul.outputs[0], dev.inputs[0]); l.new(dev.outputs[0], bsdf.inputs["Alpha"])
    return n["cut"], n["develop"]


def slab_cutter(tile_grp):
    slab = [c for c in tile_grp.children if c.name.startswith("slab")][0]
    bpy.ops.mesh.primitive_cube_add(size=1)
    cutter = bpy.context.object; cutter.name = "cutter"; cutter.scale = (20, 20, 4); cutter.hide_render = True
    cutter.location = (-10 - 99, 0, 0)
    mod = slab.modifiers.new("cut", "BOOLEAN"); mod.operation = "DIFFERENCE"; mod.object = cutter; mod.solver = "EXACT"
    return cutter


def menubar(length=17.0, height=3.2):
    """A giant, physical macOS-style menu bar lying on the desk (no vendor marks)."""
    bar = S.rounded_rect(height * 4, 0.3, 0.12)   # placeholder geometry, rescaled below
    bar.name = "menubar"
    bar.scale = (length / (height * 4), height / (height * 4), 1)
    m, b = S.mat("menubar", **{"Base Color": (0.80, 0.80, 0.82, 1), "Roughness": 0.38, "Coat Weight": 0.5, "Coat Roughness": 0.1})
    bar.data.materials.append(m)
    for p in bar.data.polygons: p.use_smooth = True
    bar.location = (-(length / 2) + SIZE / 2 + 3.4, 0, 0)

    def label(txt, x, align, weight="Medium", size=1.0):
        cu = bpy.data.curves.new(txt, "FONT"); cu.body = txt; cu.size = size
        cu.align_x = align; cu.align_y = "CENTER"
        cu.font = bpy.data.fonts.load(str(FONTS / f"Inter-{weight}.ttf")); cu.extrude = 0.012
        ob = bpy.data.objects.new(txt, cu); bpy.context.collection.objects.link(ob)
        ob.location = (x, 0, 0.125)
        tm, _ = S.mat("ink", **{"Base Color": (0.02, 0.02, 0.025, 1), "Roughness": 0.5})
        ob.data.materials.append(tm)
        return ob
    # Icon slot is at x = 0. Status items sit either side of it; app menus far left.
    label("10:42", SIZE / 2 + 0.75, "LEFT", "SemiBold")
    label("Wi-Fi", -SIZE / 2 - 0.75, "RIGHT")
    label("View", -5.0, "RIGHT"); label("Edit", -6.7, "RIGHT"); label("File", -8.3, "RIGHT")
    label("Dashboard", -9.3, "RIGHT", "SemiBold")
    return bar


# ---------- cameras ----------

def cam_rig(lens, fstop):
    cam, tgt = S.camera((0, -5, 3), (0, 0, 0), lens=lens, fstop=fstop)
    return cam, tgt


def place(cam, tgt, pos, look, lens=None, fstop=None, focus=None):
    cam.location = Vector(pos); tgt.location = Vector(look)
    if lens: cam.data.lens = lens
    if fstop: cam.data.dof.aperture_fstop = fstop
    if focus is not None:
        cam.data.dof.focus_object = None; cam.data.dof.focus_distance = focus
    else:
        cam.data.dof.focus_object = tgt


# ---------- shots ----------

def shot_macro(frames, render):
    S.reset(); S.world()
    tl = S.tile(S.TEX / "hairline-2048.png"); cut, dev = face_mask(tl)
    cam, tgt = cam_rig(100, 1.8)
    for f in frames:
        t = f / FPS
        dev.inputs[1].default_value = ease(prog(t, 0.0, 1.2))         # the icon develops onto the blank tile
        k = inout(prog(t, 0, 4.5))
        place(cam, tgt, vlerp((-1.45, -1.95, 0.52), (-0.55, -1.55, 0.44), k), vlerp((-0.1, -0.1, 0.09), (0.55, 0.45, 0.09), k))
        render(f)


def scan_state(t, blocks, src, cutter, cut, bladeob, t0, t1, rebuild_from=None):
    """Blade position x and each block's state at time t."""
    x0, x1 = -SIZE / 2 - 0.15, SIZE / 2 + 0.15
    bx = lerp(x0, x1, inout(prog(t, t0, t1)))
    if bladeob:
        bladeob.location = (bx, 0, 0.30); bladeob.hide_render = not (t0 - 0.2 < t < t1 + 0.15)
    if cut is not None: cut.inputs[1].default_value = bx
    if cutter is not None: cutter.location = (bx - 10, 0, 0)
    for (x, y), ob in blocks.items():
        cx = (x - 7.5) * CELL
        passed = (t + 0.06 - (t0 + (t1 - t0) * prog(cx, x0, x1))) / 0.22
        r, g, b, a = src[(x, y)]
        if rebuild_from is None:
            set_block(ob, x, y, back(clamp(passed)), (r, g, b, 1), alpha=a)
        else:
            pr, pg, pb, pa = rebuild_from[(x, y)]
            k = clamp(passed)
            if k <= 0: set_block(ob, x, y, 1, (pr, pg, pb, 1), alpha=pa)
            else:
                pop = 1 + 0.25 * math.sin(math.pi * k)                 # a small lift as it rebuilds
                set_block(ob, x, y, pop if a >= 0.5 else 1 - k, (lerp(pr, r, k), lerp(pg, g, k), lerp(pb, b, k), 1), alpha=a if k > 0.5 else max(a, pa))
    return bx


def shot_scan(frames, render):
    S.reset(); S.world()
    tl = S.tile(S.TEX / "hairline-2048.png"); cut, dev = face_mask(tl); cutter = slab_cutter(tl)
    blocks = block_field(); src = raster("hairline-16.png"); bl = blade()
    cam, tgt = cam_rig(60, 2.8)
    for f in frames:
        t = f / FPS
        scan_state(t, blocks, src, cutter, cut, bl, 0.8, 3.5)
        k = inout(prog(t, 0, 5.0))
        place(cam, tgt, vlerp((-2.7, -3.7, 2.4), (-1.3, -3.9, 3.5), k), (0, 0, 0.05))
        render(f)


def shot_topdown(frames, render):
    S.reset(); S.world()
    blocks = block_field(); src = raster("hairline-16.png")
    for (x, y), ob in blocks.items(): set_block(ob, x, y, 1, src[(x, y)][:3] + (1,), alpha=src[(x, y)][3])
    cam, tgt = cam_rig(50, 4.0)
    for f in frames:
        t = f / FPS
        k = inout(prog(t, 0, 1.8)); push = ease(prog(t, 1.8, 3.5))
        place(cam, tgt, vlerp((-1.3, -3.9, 3.5), (0.0, -0.02, 6.6 - 0.5 * push), k), vlerp((0, 0, 0.05), (0, 0, 0), k))
        render(f)


def shot_square(frames, render):
    S.reset(); S.world()
    blocks = block_field(); src = raster("hairline-16.png")
    bar = menubar()
    cam, tgt = cam_rig(50, 4.0)
    black = (0.004, 0.004, 0.005, 1)
    for f in frames:
        t = f / FPS
        for (x, y), ob in blocks.items():
            r, g, b, a = src[(x, y)]
            wave = prog(t, 0.3 + (x + y) / 30 * 1.1, 0.7 + (x + y) / 30 * 1.1)   # colour drains corner to corner
            col = (lerp(r, black[0], wave), lerp(g, black[1], wave), lerp(b, black[2], wave), 1)
            gap = lerp(0.08, 0.0, ease(prog(t, 1.9, 2.6)))                        # the gaps close: one slab
            set_block(ob, x, y, 1, col, gap=gap, alpha=a)
        # The menu bar slides in under the slab as the camera pulls back.
        rise = ease(prog(t, 3.3, 4.1))
        bar.location.z = lerp(-0.12, 0.0, rise)                 # the bar rises out of the desk under the slab
        bar.hide_render = rise <= 0
        for o in bpy.data.objects:
            if o.type == "FONT": o.location.z = bar.location.z + 0.125; o.hide_render = rise <= 0
        for ob in blocks.values(): ob.location.z += 0.12 * rise
        k = inout(prog(t, 2.0, 5.4))
        place(cam, tgt, vlerp((0.0, -0.02, 6.1), (-2.6, -9.5, 7.0), k), vlerp((0, 0, 0), (-2.4, 0.3, 0), k), lens=lerp(50, 42, k), fstop=lerp(4.0, 5.6, k))
        render(f)


def shot_fix(frames, render):
    S.reset(); S.world()
    blocks = block_field(); old = raster("hairline-16.png"); new = raster("fixed-card-16.png"); bl = blade()
    cam, tgt = cam_rig(50, 4.0)
    for f in frames:
        t = f / FPS
        scan_state(t, blocks, new, None, None, bl, 0.25, 2.2, rebuild_from=old)
        k = inout(prog(t, 0, 3.0))
        place(cam, tgt, vlerp((-1.2, -3.6, 3.6), (-0.4, -1.2, 5.6), k), (0, 0, 0.05))
        render(f)


def shot_traybar(frames, render):
    S.reset(); S.world()
    blocks = block_field(); tray = raster("fixed-tray-16.png"); bar = menubar()
    for (x, y), ob in blocks.items():
        a = tray[(x, y)][3]
        set_block(ob, x, y, 1, (0.004, 0.004, 0.005, 1), gap=0.0, alpha=a)   # template image: alpha only
        ob.location.z += 0.12
    cam, tgt = cam_rig(42, 5.6)
    for f in frames:
        t = f / FPS
        k = ease(prog(t, 0, 3.0))
        place(cam, tgt, vlerp((-2.2, -9.0, 6.6), (-1.6, -7.6, 5.9), k), (-1.6, 0.3, 0))
        render(f)


def shot_endtile(frames, render):
    S.reset(); S.world()
    tl = S.tile(S.TEX / "fixed-card-2048.png"); tl.location = (2.2, 0.3, 0)
    cam, tgt = cam_rig(50, 2.8)
    for f in frames:
        t = f / FPS
        k = inout(prog(t, 0, 6.0))
        place(cam, tgt, vlerp((0.4, -4.6, 5.4), (0.2, -4.2, 5.0), k), (0.6, 0.1, 0))
        render(f)


# ---------- the laptop ----------

def rounded_box(name, w, d, h, r, material, bevel=0.01):
    import bmesh
    bm = bmesh.new(); verts = []; segs = 16
    hw, hd = w / 2 - r, d / 2 - r
    for cx, cy, a0 in ((hw, hd, 0), (-hw, hd, 90), (-hw, -hd, 180), (hw, -hd, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            verts.append(bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), 0)))
    f = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, 0, h), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    if bevel:
        bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 4; bv.limit_method = "ANGLE"
    ob.data.materials.append(material)
    for p in ob.data.polygons: p.use_smooth = True
    return ob


def laptop(open_deg=108):
    """An unbranded aluminium laptop, 12 units wide. Returns the screen material's image node."""
    alu, _ = S.mat("alu", **{"Base Color": (0.70, 0.71, 0.73, 1), "Metallic": 1.0, "Roughness": 0.3})
    dark, _ = S.mat("keys", **{"Base Color": (0.05, 0.05, 0.055, 1), "Roughness": 0.55})
    pad, _ = S.mat("pad", **{"Base Color": (0.62, 0.63, 0.65, 1), "Metallic": 1.0, "Roughness": 0.18})
    bezel, _ = S.mat("bezel", **{"Base Color": (0.01, 0.01, 0.012, 1), "Roughness": 0.25, "Coat Weight": 1.0, "Coat Roughness": 0.03})
    W, D = 12.0, 8.4
    base = rounded_box("base", W, D, 0.28, 0.5, alu, 0.06)
    keys = rounded_box("keys", W * 0.86, D * 0.40, 0.012, 0.12, dark, 0)
    keys.location = (0, D * 0.17, 0.28)
    tpad = rounded_box("trackpad", W * 0.40, D * 0.30, 0.008, 0.14, pad, 0)
    tpad.location = (0, -D * 0.25, 0.28)
    hinge = bpy.data.objects.new("hinge", None); bpy.context.collection.objects.link(hinge)
    hinge.location = (0, D / 2 - 0.05, 0.28)
    lid = rounded_box("lid", W, D * 0.98, 0.16, 0.5, alu, 0.05)
    lid.parent = hinge; lid.location = (0, -(D * 0.98) / 2, 0)
    glass = rounded_box("glass", W - 0.08, D * 0.98 - 0.08, 0.01, 0.46, bezel, 0)
    glass.parent = hinge; glass.location = (0, -(D * 0.98) / 2, -0.012)
    # The screen: an emissive plane carrying the real page, 16:10.
    sw = W - 0.62; sh = sw * 10 / 16
    bpy.ops.mesh.primitive_plane_add(size=1)
    scr = bpy.context.object; scr.name = "screen"; scr.scale = (sw, sh, 1)
    scr.parent = hinge; scr.location = (0, -(D * 0.98) / 2 - 0.22, -0.0135); scr.rotation_euler = (math.pi, 0, 0)
    m = bpy.data.materials.new("screen"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); emi = nt.nodes.new("ShaderNodeEmission"); tex = nt.nodes.new("ShaderNodeTexImage")
    mix = nt.nodes.new("ShaderNodeAddShader"); gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.04
    tex.interpolation = "Cubic"; emi.inputs["Strength"].default_value = 1.05
    nt.links.new(tex.outputs["Color"], emi.inputs["Color"]); nt.links.new(emi.outputs[0], mix.inputs[0])
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.08
    mul = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(lw.outputs["Fresnel"], mul.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    nt.links.new(tr.outputs[0], mul.inputs[1]); nt.links.new(gl.outputs[0], mul.inputs[2])
    nt.links.new(mul.outputs[0], mix.inputs[1]); nt.links.new(mix.outputs[0], out.inputs["Surface"])
    scr.data.materials.append(m)
    hinge.rotation_euler = (-math.radians(open_deg), 0, 0)   # lid swings up and slightly back
    return tex


def shot_laptop(frames, render):
    S.reset(); S.world(scale=4.0)
    tex = laptop()
    seq = ROOT / "work" / "promo-xray" / "screen-seq"
    cam, tgt = cam_rig(50, 2.0)
    centre = Vector((0, 4.15 + 4.1 * math.cos(math.radians(72)), 0.28 + 4.1 * math.sin(math.radians(72))))
    for f in frames:
        t = f / FPS
        tex.image = bpy.data.images.load(str(seq / f"{min(f, 191):04d}.png"), check_existing=True)
        # Close on the drop and the verdict, then pull back to reveal the room:
        # the laptop settles to the right and the desk and wall open on the left.
        hold = inout(prog(t, 0.0, 3.0)); back = inout(prog(t, 3.0, 6.2))
        near = vlerp((-2.9, -10.6, 6.1), (-2.3, -9.6, 5.8), hold)
        pos = vlerp(near, (-11.5, -19.5, 8.6), back)
        look = vlerp(centre + Vector((0.0, 0, -0.1)), centre + Vector((-3.6, -1.0, -1.4)), back)
        place(cam, tgt, pos, look, lens=lerp(50, 40, back), fstop=lerp(2.0, 3.2, back))
        render(f)
        old = bpy.data.images.get(f"{f - 3:04d}.png")
        if old: bpy.data.images.remove(old)

SHOT_FN = {"macro": shot_macro, "scan": shot_scan, "topdown": shot_topdown, "square": shot_square,
           "laptop": shot_laptop, "fix": shot_fix, "traybar": shot_traybar, "endtile": shot_endtile}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
    names = list(SHOTS) if opt.get("shot", "all") == "all" else opt["shot"].split(",")
    res = int(opt.get("res", 960)); spp = int(opt.get("spp", 32))
    only = opt.get("frames")                     # e.g. "0,30,60" for review stills
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
