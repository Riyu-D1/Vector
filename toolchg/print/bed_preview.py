# toolchg/print/bed_preview.py - D13: top-view render of the 3-part
# prototype print pack on the A1 bed (256 x 256 mm usable).
# usage: /usr/local/bin/blender -b -P bed_preview.py -- <out.png>
import bpy, sys
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.light = "STUDIO"
scn.display.shading.color_type = "OBJECT"
scn.display.shading.show_cavity = True
scn.display.shading.show_shadows = True
scn.render.resolution_x = scn.render.resolution_y = 900
if scn.world is not None:
    scn.world.color = (0.93, 0.94, 0.96)

# bed plate 256 x 256 x 6, top at z=0
bpy.ops.mesh.primitive_cube_add(size=1, location=(128, 128, -3.0))
bed = bpy.context.active_object
bed.scale = (256, 256, 3.0)
bed.color = (0.55, 0.57, 0.62, 1.0)

HERE = __file__.rsplit("/", 1)[0]
# (stl, r,g,b, x,y of mesh min corner on the bed)
PARTS = [
    ("tc_master.stl", 0.85, 0.35, 0.20, 40.0, 110.0),
    ("tc_plate.stl", 0.25, 0.55, 0.85, 115.0, 105.0),
    ("tool_pen.stl", 0.30, 0.75, 0.35, 185.0, 105.0),
]
objs = []
for fname, r, g, b, x, y in PARTS:
    bpy.ops.wm.stl_import(filepath=HERE + "/stl/" + fname)
    o = bpy.context.active_object
    o.color = (r, g, b, 1.0)
    o.location = (x, y, 0.0)
    objs.append(o)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 300.0
cam_data.clip_start = 0.1
cam_data.clip_end = 2000.0
cam = bpy.data.objects.new("cam", cam_data)
scn.collection.objects.link(cam)
cam.location = (128, 128, 500)
cam.rotation_euler = (0, 0, 0)
scn.camera = cam

scn.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out)
