"""cad/knuckle/render_blend.py - 6-view renders. Copied verbatim.
Run:  /usr/local/bin/blender -b -P render_blend.py -- <out_prefix> <list.txt>
list.txt: one line per STL:  <path.stl> <r> <g> <b>   (0..1 floats)
Writes <out_prefix>_{frontiso,backiso,side,top,front,cutaway}.png (1200x750).
Cutaway removes everything with G y < 0 (boolean with a big box)."""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
prefix, listfile = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "OBJECT"
scn.display.shading.show_cavity = True
scn.display.shading.show_shadows = True
scn.render.resolution_x, scn.render.resolution_y = 1200, 750
scn.render.film_transparent = False
scn.world = bpy.data.worlds.new("w")
scn.world.color = (0.93, 0.94, 0.96)

objs = []
for line in open(listfile):
    p = line.split()
    if not p:
        continue
    bpy.ops.wm.stl_import(filepath=p[0])
    o = bpy.context.selected_objects[0]
    o.color = (float(p[1]), float(p[2]), float(p[3]), 1.0)
    objs.append(o)

lo = Vector((min(min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in objs) for i in range(3)))
hi = Vector((max(max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in objs) for i in range(3)))
ctr = (lo + hi) / 2
size = max(hi - lo)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size * 1.4
cam_data.clip_start = 0.1
cam_data.clip_end = size * 20
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam

VIEWS = {  # direction FROM centre TO camera
    "frontiso": Vector((1.0, -1.0, 0.8)),
    "backiso": Vector((-1.0, 1.0, 0.8)),
    "side": Vector((0.0, -1.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "front": Vector((1.0, 0.0, 0.0)),
    "cutaway": Vector((0.3, -1.0, 0.35)),
}


def aim(d):
    d = d.normalized()
    cam.location = ctr + d * size * 3
    up = Vector((0, 1, 0)) if abs(d.z) > 0.99 else Vector((0, 0, 1))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y" if up.y else "Z").to_euler()


for name, d in VIEWS.items():
    if name == "cutaway":
        bpy.ops.mesh.primitive_cube_add(size=1)
        cut = bpy.context.active_object
        cut.scale = (size * 4, size * 2, size * 4)
        cut.location = (ctr.x, -size, ctr.z)      # covers y < 0
        cut.hide_render = True
        for o in objs:
            m = o.modifiers.new("cut", "BOOLEAN")
            m.operation = "DIFFERENCE"
            m.object = cut
    aim(d)
    scn.render.filepath = f"{prefix}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("WROTE", scn.render.filepath)
