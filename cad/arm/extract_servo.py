"""Extract the STS3215 servo model (body + wheels) from the follower
assembly -> save a standalone servo STEP + report its real dims.
Also dump cylindrical/planar face features of key structural parts.
"""
import os
from build123d import (import_step, Location, export_step, Part, Axis,
                       GeomType, Vector)

asm = import_step("/tmp/so102/models/step/SO-ARM102_Follower.STEP")

def iter_tree(node, world_loc=Location()):
    wl = world_loc * node.location
    yield node, wl
    for ch in getattr(node, "children", []):
        yield from iter_tree(ch, wl)

# find the J1 servo (has full body, incl. both wheels)
servo_node = None
for node, wl in iter_tree(asm):
    if getattr(node, "label", "") == "STS3215_Servo_Id_1":
        servo_node, servo_wl = node, wl
        break

servo_local = servo_node.located(Location())
bb = servo_local.bounding_box()
print("servo local bbox:", bb.min, "->", bb.max, "size:", bb.size)

os.makedirs("/tmp/arm_ref", exist_ok=True)
export_step(servo_local, "/tmp/arm_ref/sts3215_servo.step")

# union the children into one solid? keep as compound - it has 9 solids
print("children:")
for ch in servo_node.children:
    print("  ", ch.label, ch.bounding_box().size)

# Measure: case extents along each axis vs wheel positions
# Local frame: X=45.2 (length), Y=shaft axis, Z=24.7
EOF = None
