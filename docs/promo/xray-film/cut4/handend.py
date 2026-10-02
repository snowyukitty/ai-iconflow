# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The last frame of the hand plate: a blank tile on the desk, rendered in the
film's own world, used as the Flow end frame so live action lands on CG."""
import sys
from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene as S
S.reset(); S.world()
tl = S.tile(S.TEX / "hairline-2048.png")
for c in tl.children:
    if c.name.startswith("face"): c.hide_render = True        # blank: the icon develops in the next shot
S.camera((-2.9, -4.6, 3.1), (0.1, 0.1, 0.05), lens=45, fstop=4.0)
sc = bpy.context.scene; sc.cycles.samples = 256
sc.render.filepath = str(Path(__file__).resolve().parent / "stills" / "handend.png")
bpy.ops.render.render(write_still=True)
