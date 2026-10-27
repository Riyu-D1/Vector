"""Extract every structural part of the follower (world-placed) to
/tmp/arm_ref/<name>.step, and dump hole features near each joint axis.
"""
import os
from build123d import import_step, Location, export_step, Compound, GeomType, Vector

os.makedirs("/tmp/arm_ref", exist_ok=True)
asm = import_step("/tmp/so102/models/step/SO-ARM102_Follower.STEP")

def iter_tree(node, world_loc=Location(), depth=0, path=()):
    wl = world_loc * node.location
    yield node, wl, path
    for ch in getattr(node, "children", []):
        yield from iter_tree(ch, wl, depth + 1, path + (getattr(node, "label", "?"),))

WANTED = ["SO102_01_010_Base_010", "SO102_01_010_Base_020_Base_ring",
          "SO102_01_010_Base_030_Base_washer",
          "SO102_01_040_Rotating_base_040_Bottom_top_plate",
          "SO102_01_040_Rotating_base_050_Bottom_ring",
          "SO102_02_060_Bottom_servo_holder",
          "SO102_03_070_Bottom_arm",
          "SO102_02_080_Upper_arm", "SO102_03_090_Wrist_holder",
          "RB9_01_062_010_Main_frame", "RB9_01_062_020_Clamp",
          "RB9_01_062_030_Gear_rack", "RB9_01_061_040_Gear_for_gripper",
          "RB9_01_062_070_Camera_holder", "RB9_01_060_090_Camera_spacer",
          "RB9_01_062_050_Washer", "RB9_01_062_100_Nail",
          "Bearing_6812", "Rod_d6_125", "Bearing_MF106"]

seen = {}
for node, wl, path in iter_tree(asm):
    label = getattr(node, "label", "")
    for w in WANTED:
        if w in label:
            idx = seen.get(w, 0)
            seen[w] = idx + 1
            placed = node.located(wl)
            out = f"/tmp/arm_ref/{w}_{idx}.step"
            try:
                export_step(placed, out)
                bb = placed.bounding_box()
                print(f"{w}_{idx}: size=({bb.size.X:.1f},{bb.size.Y:.1f},{bb.size.Z:.1f})"
                      f" ctr=({(bb.min.X+bb.max.X)/2:.1f},{(bb.min.Y+bb.max.Y)/2:.1f},{(bb.min.Z+bb.max.Z)/2:.1f})")
            except Exception as e:
                print(f"{w}_{idx}: EXPORT FAIL {e}")
            break
