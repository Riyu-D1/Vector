"""Dump the SO-ARM-102 follower assembly structure: children + positions."""
from build123d import import_step, Compound

asm = import_step("/tmp/so102/models/step/SO-ARM102_Follower.STEP")
print(type(asm))

def walk(node, depth=0):
    loc = node.location
    try:
        bb = node.bounding_box()
        size = (bb.size.X, bb.size.Y, bb.size.Z)
        ctr = ((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2,
               (bb.min.Z + bb.max.Z) / 2)
    except Exception:
        size = ctr = (0, 0, 0)
    label = getattr(node, "label", "?")
    print("  " * depth + f"{label[:60]:60s} ctr=({ctr[0]:7.1f},{ctr[1]:7.1f},{ctr[2]:7.1f})"
          f" size=({size[0]:5.1f},{size[1]:5.1f},{size[2]:5.1f})")
    if depth < 2:
        for ch in getattr(node, "children", []):
            walk(ch, depth + 1)

walk(asm)
