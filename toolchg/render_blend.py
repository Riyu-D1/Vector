# toolchg/render_blend.py - D10 renders, wrist2/render_blend.py pattern.
# usage: blender -b -P render_blend.py -- <list.txt> <out_prefix> [views...]
#   list.txt: one line per STL:  <path.stl> <r> <g> <b>   (0..1 floats)
#   views: subset of frontiso backiso side top front (default: frontiso)
import bpy, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
listfile, prefix = argv[0], argv[1]
want = argv[2:] or ["frontiso"]

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "OBJECT"
scn.display.shading.show_cavity = True
scn.display.shading.show_shadows = True
scn.render.resolution_x, scn.render.resolution_y = 1200, 750
if scn.world is not None:
    scn.world.color = (0.93, 0.94, 0.96)

objs = []
for ln in open(listfile):
    ln = ln.strip()
    if not ln or ln.startswith("#"):
        continue
    p = ln.split()
    bpy.ops.wm.stl_import(filepath=p[0])
    o = bpy.context.active_object
    o.color = (float(p[1]), float(p[2]), float(p[3]), 1.0)
    objs.append(o)

lo = Vector((1e9, 1e9, 1e9))
hi = -lo
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
ctr, size = (lo + hi) / 2, (hi - lo).length / 2

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size * 2.1
cam_data.clip_start = 0.1
cam_data.clip_end = size * 20
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam

VIEWS = {
    "frontiso": Vector((1.0, -1.0, 0.8)),
    "backiso": Vector((-1.0, 1.0, 0.8)),
    "side": Vector((0.0, -1.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "front": Vector((1.0, 0.0, 0.0)),
}

def aim(d):
    d = d.normalized()
    cam.location = ctr + d * size * 3
    up = Vector((0, 1, 0)) if abs(d.z) > 0.99 else Vector((0, 0, 1))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y" if up.y else "Z").to_euler()

for name in want:
    aim(VIEWS[name])
    scn.render.filepath = "%s_%s.png" % (prefix, name)
    bpy.ops.render.render(write_still=True)
    print("WROTE", scn.render.filepath)
