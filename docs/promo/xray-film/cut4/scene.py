# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Cut-4 hero world in Blender/Cycles: a warm paper desk in morning light, the
real icon as an anodized tile, and the real 16 px raster as 256 blocks.

    blender -b --factory-startup -P scene.py -- --stills tile,blocks,slab
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TEX = HERE / "tex"
OUT = HERE / "stills"
OUT.mkdir(exist_ok=True)


# ---------- setup ----------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for d in prefs.devices: d.use = d.type == "OPTIX"
    sc.cycles.device = "GPU"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPTIX"
    sc.cycles.max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.film_transparent = False
    # Standard keeps product colour honest: the icon blue must be the icon blue.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    return sc


def mat(name, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m, b


def paper_material():
    m, b = mat("paper", **{"Roughness": 0.92})
    nt = m.node_tree; n = nt.nodes; l = nt.links
    tc = n.new("ShaderNodeTexCoord")
    fib = n.new("ShaderNodeTexNoise"); fib.inputs["Scale"].default_value = 420; fib.inputs["Detail"].default_value = 6
    blot = n.new("ShaderNodeTexNoise"); blot.inputs["Scale"].default_value = 3; blot.inputs["Detail"].default_value = 2
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.66, 0.58, 0.47, 1)
    ramp.color_ramp.elements[1].color = (0.74, 0.67, 0.56, 1)
    mix = n.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs[0].default_value = 0.25
    l.new(tc.outputs["Object"], fib.inputs["Vector"]); l.new(tc.outputs["Object"], blot.inputs["Vector"])
    l.new(blot.outputs["Fac"], mix.inputs[2]); l.new(fib.outputs["Fac"], mix.inputs[3])
    l.new(mix.outputs[0], ramp.inputs["Fac"]); l.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.14
    l.new(fib.outputs["Fac"], bump.inputs["Height"]); l.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def world(scale=1.0):
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.95, 0.86, 0.72, 1); bg.inputs["Strength"].default_value = 0.30

    bpy.ops.mesh.primitive_plane_add(size=80)
    desk = bpy.context.object; desk.name = "desk"; desk.data.materials.append(paper_material())

    # Morning sun from the left, low and warm, through a window: the mullions
    # cast the soft bars that tell you it is a real room.
    bpy.ops.object.light_add(type="SUN")
    sun = bpy.context.object; sun.data.energy = 6.5; sun.data.angle = math.radians(1.6)
    sun.data.color = (1.0, 0.80, 0.58)
    sun.rotation_euler = (math.radians(66), 0, math.radians(-112))
    # A window between the sun and the desk: a wall with a 2x2 paned opening.
    # It throws broad warm panes of light with soft mullion shadows, the way a
    # real room does, instead of lighting the desk evenly.
    bpy.context.view_layer.update()
    d = (sun.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
    centre = Vector((0.3, 0.2, 0)) * scale - d * 4.5 * scale
    win = bpy.data.objects.new("window", None); bpy.context.collection.objects.link(win)
    win.location = centre
    win.rotation_euler = sun.rotation_euler
    W, H, bar, wall = 3.4 * scale, 3.4 * scale, 0.14 * scale, 40 * scale
    pieces = [  # (x, y, sx, sy) in the window plane
        (0, (H / 2 + wall / 2), wall * 2, wall), (0, -(H / 2 + wall / 2), wall * 2, wall),
        ((W / 2 + wall / 2), 0, wall, H), (-(W / 2 + wall / 2), 0, wall, H),
        (0, 0, bar, H), (0, 0, W, bar),
    ]
    for i, (x, y, sx, sy) in enumerate(pieces):
        bpy.ops.mesh.primitive_cube_add(size=1)
        pc = bpy.context.object; pc.name = f"window{i}"
        pc.scale = (sx, sy, 0.05); pc.location = (x, y, 0); pc.parent = win
        pc.visible_camera = False; pc.visible_glossy = False; pc.visible_transmission = False

    bpy.ops.object.light_add(type="AREA", location=(5, -3, 5))
    fill = bpy.context.object; fill.data.energy = 90; fill.data.size = 6; fill.data.color = (0.86, 0.9, 1.0)
    fill.rotation_euler = (math.radians(45), 0, math.radians(60))


def image_node(nt, path):
    n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(str(path)); n.interpolation = "Cubic"
    return n


def rounded_rect(card, radius, depth, segs=24):
    import bmesh
    bm = bmesh.new(); verts = []
    h = card / 2 - radius
    for cx, cy, a0 in ((h, h, 0), (-h, h, 90), (-h, -h, 180), (h, -h, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            verts.append(bm.verts.new((cx + radius * math.cos(a), cy + radius * math.sin(a), 0)))
    f = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, 0, depth), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    me = bpy.data.meshes.new("rr"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("slab", me); bpy.context.collection.objects.link(ob)
    return ob


def tile(texture, size=2.4):
    card = size * 896 / 1024
    slab = rounded_rect(card, card * 200 / 896, 0.09)
    bev = slab.modifiers.new("bevel", "BEVEL"); bev.width = 0.018; bev.segments = 6; bev.limit_method = "ANGLE"
    m, b = mat("anodized", **{"Base Color": (0.05, 0.11, 0.98, 1), "Metallic": 0.8, "Roughness": 0.3, "Coat Weight": 0.3, "Coat Roughness": 0.18})
    slab.data.materials.append(m)
    for p in slab.data.polygons: p.use_smooth = True

    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0.0905))
    face = bpy.context.object; face.name = "face"
    fm, fb = mat("iconface", **{"Roughness": 0.4, "Coat Weight": 0.5, "Coat Roughness": 0.1})
    tex = image_node(fm.node_tree, texture)
    fm.node_tree.links.new(tex.outputs["Color"], fb.inputs["Base Color"])
    fm.node_tree.links.new(tex.outputs["Alpha"], fb.inputs["Alpha"])
    face.data.materials.append(fm)
    grp = bpy.data.objects.new("tile", None); bpy.context.collection.objects.link(grp)
    slab.parent = grp; face.parent = grp
    return grp


def blocks(raster, size=2.4):
    from array import array
    img = bpy.data.images.load(str(raster)); w, h = img.size
    px = array("f", img.pixels[:])            # bottom-up, linear float RGBA
    cell = size / w
    m, b = mat("block", **{"Roughness": 0.36, "Coat Weight": 0.35, "Coat Roughness": 0.15})
    info = m.node_tree.nodes.new("ShaderNodeObjectInfo")
    m.node_tree.links.new(info.outputs["Color"], b.inputs["Base Color"])
    bpy.ops.mesh.primitive_cube_add(size=1)
    proto = bpy.context.object; proto.scale = (cell * 0.92, cell * 0.92, cell); bpy.ops.object.transform_apply(scale=True)
    bv = proto.modifiers.new("bevel", "BEVEL"); bv.width = cell * 0.1; bv.segments = 4
    proto.data.materials.append(m); bpy.ops.object.shade_smooth()
    out = []
    for y in range(h):
        for x in range(w):
            i = (y * w + x) * 4
            r, g, bl, a = px[i:i + 4]
            if a < 0.5:
                continue
            ob = proto.copy(); bpy.context.collection.objects.link(ob)
            ob.location = ((x - (w - 1) / 2) * cell, (y - (h - 1) / 2) * cell, cell / 2)
            lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            ob.color = (lin(r), lin(g), lin(bl), 1)   # PNG pixels are sRGB; Object Info wants linear
            ob["gx"], ob["gy"] = x, y
            out.append(ob)
    bpy.data.objects.remove(proto)
    return out


def camera(loc, target, lens=85, fstop=2.8):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object; bpy.context.scene.camera = cam
    cam.data.lens = lens; cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
    tgt = bpy.data.objects.new("target", None); bpy.context.collection.objects.link(tgt); tgt.location = target
    c = cam.constraints.new("TRACK_TO"); c.target = tgt
    cam.data.dof.focus_object = tgt
    return cam, tgt


def render(name):
    bpy.context.scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


# ---------- look tests ----------

def still(name):
    reset(); world()
    if name == "tile":
        tile(TEX / "hairline-2048.png")
        camera((-2.4, -3.9, 2.5), (0.15, 0.1, 0.05), lens=70, fstop=2.2)
    elif name == "blocks":
        blocks(TEX / "hairline-16.png")
        camera((-2.2, -3.6, 2.9), (0, 0, 0.1), lens=70, fstop=2.8)
    elif name == "slab":
        for ob in blocks(TEX / "hairline-16.png"):
            ob.color = (0.012, 0.012, 0.014, 1)
        camera((-2.2, -3.6, 2.9), (0, 0, 0.1), lens=70, fstop=2.8)
    elif name == "macro":
        tile(TEX / "hairline-2048.png")
        camera((-0.9, -1.6, 0.55), (0.25, 0.2, 0.09), lens=100, fstop=1.8)
    render(name)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--stills" in argv:
        for n in argv[argv.index("--stills") + 1].split(","):
            still(n)
