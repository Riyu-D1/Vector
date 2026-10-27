"""Extract joint axes from the SO-ARM-102 follower assembly.

Compose world transforms: each node.location is local to its parent, so
accumulate the product down the tree. For every servo subassembly, get the
world bbox of the servo body and of its Main_Wheel (output horn boss) and
Second_Wheel (idler boss) -> joint axis point + direction.
"""
from build123d import import_step, Location

asm = import_step("/tmp/so102/models/step/SO-ARM102_Follower.STEP")


def iter_tree(node, world_loc=Location(), parents=()):
    wl = world_loc * node.location
    yield node, wl, parents
    for ch in getattr(node, "children", []):
        yield from iter_tree(ch, wl, parents + (node,))


def world_bbox(node, world_loc):
    return node.location  # unused


servos = []
for node, wl, parents in iter_tree(asm):
    label = getattr(node, "label", "")
    if "STS3215" in label and any(
        "Main_Wheel" in getattr(c, "label", "")
        for c in getattr(node, "children", [])
    ):
        servos.append((node, wl))

for i, (sv, wl) in enumerate(servos):
    sbb = (sv).bounding_box()  # local
    ws = sv.wrapped  # noqa
    # world bbox: transform the local-solid copy
    world = sv.located(wl)
    wbb = world.bounding_box()
    print(f"--- servo {i}: {getattr(sv,'label','?')[:50]}")
    print(f"    world body ctr=({(wbb.min.X+wbb.max.X)/2:7.2f},{(wbb.min.Y+wbb.max.Y)/2:7.2f},{(wbb.min.Z+wbb.max.Z)/2:7.2f})"
          f" size=({wbb.size.X:5.1f},{wbb.size.Y:5.1f},{wbb.size.Z:5.1f})")
    for ch in getattr(sv, "children", []):
        lab = getattr(ch, "label", "")
        if "Wheel" in lab or "Gear" in lab or "GE_27" in lab:
            wch = ch.located(wl * ch.location)
            wcb = wch.bounding_box()
            cx, cy, cz = (wcb.min.X+wcb.max.X)/2, (wcb.min.Y+wcb.max.Y)/2, (wcb.min.Z+wcb.max.Z)/2
            dims = sorted([("X", wcb.size.X), ("Y", wcb.size.Y), ("Z", wcb.size.Z)], key=lambda t: t[1])
            print(f"    {lab[:28]:28s} ctr=({cx:7.2f},{cy:7.2f},{cz:7.2f})"
                  f" size=({wcb.size.X:5.1f},{wcb.size.Y:5.1f},{wcb.size.Z:5.1f})"
                  f"  axis~{dims[0][0]}")

# also structural parts world placement
print("\n=== structural parts (world) ===")
for node, wl, parents in iter_tree(asm):
    label = getattr(node, "label", "")
    if ("SO102" in label or "RB9" in label) and not getattr(node, "children", []):
        w = node.located(wl)
        bb = w.bounding_box()
        cx, cy, cz = (bb.min.X+bb.max.X)/2, (bb.min.Y+bb.max.Y)/2, (bb.min.Z+bb.max.Z)/2
        print(f"{label[:55]:55s} ctr=({cx:7.2f},{cy:7.2f},{cz:7.2f}) size=({bb.size.X:5.1f},{bb.size.Y:5.1f},{bb.size.Z:5.1f})")
