"""final2/render_wrist.py - wrist close-up render (F2 stage requirement).
Adapted from wrist2/render_blend.py: same group STLs, camera framed on the
wrist region (x > 85 mm) instead of the whole arm.
Run:  /usr/local/bin/blender -b -P final2/render_wrist.py -- <out_prefix> <list.txt>
"""
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

# wrist centre from D6 geometry: wrist spans x ~96..234, z ~165..240
ctr = Vector((165.0, 0.0, 200.0))
size = 170.0

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size * 1.25
cam_data.clip_start = 0.1
cam_data.clip_end = 4000
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam


def aim(d):
    d = d.normalized()
    cam.location = ctr + d * size * 4
    up = Vector((0, 1, 0)) if abs(d.z) > 0.99 else Vector((0, 0, 1))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y" if up.y else "Z").to_euler()


aim(Vector((1.0, -1.0, 0.7)))
scn.render.filepath = f"{prefix}_wrist.png"
bpy.ops.render.render(write_still=True)
