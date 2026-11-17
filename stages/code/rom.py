"""cad/knuckle/rom.py - single-joint range-of-motion collision sweep.
Copied verbatim. Usage (from cad/knuckle):  python rom.py [J2 J3 ...]
Reads out/*.stl (home pose, written by build.py). For each joint, rotates
that joint's downstream groups in 5 deg steps over kp.LIM and intersects
every moving part with every non-moving part (manifold3d).  Pairs in
SKIP are the actuator vs the link it drives (output parts touch/rotate).
Prints per joint:  J3: lo=-135 hi=90 safe=[-135, 90] OK   or  ... BAD
and finally ROM PASS / ROM FAIL."""
import math
import os
import sys

import numpy as np
import trimesh

import kp
from gate import PRESS_PAIRS, to_manifold

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
STEP = 5
INTERF_MAX = 0.5
# group order = kinematic chain. Every name is an STL stem in out/.
GROUPS = [
    ("base", ["drum", "drum_cap", "vendor_J1"]),
    ("J1", ["turret", "kn_endcap", "vendor_J2"]),
    ("J2", ["upper_arm", "upper_cover", "vendor_J3"]),
    ("J3", ["forearm", "fa_endcap", "fa_elbow_cap", "vendor_J4"]),
    ("J4", ["head", "cup_cap", "pod_front", "vendor_J5"]),
    ("J5", ["gripper", "grip_lid", "vendor_J6"]),
    ("J6", ["jaw", "jaw_cap"]),
]
AXES = {  # joint: (axis direction, point on axis), G frame
    "J1": ((0, 0, 1), (0, 0, 0)),
    "J2": ((0, 1, 0), kp.J2),
    "J3": ((0, 1, 0), kp.J3),
    "J4": ((0, 1, 0), kp.J4),
    "J5": ((1, 0, 0), (0, 0, 150.0)),
    "J6": ((0, 1, 0), (kp.J6_ORIGIN[0], 0, kp.J6_ORIGIN[2])),
}
SKIP = {("vendor_J1", "turret"), ("vendor_J2", "upper_arm"),
        ("vendor_J3", "forearm"), ("vendor_J4", "head"),
        ("vendor_J5", "gripper"), ("vendor_J6", "jaw"),
        ("vendor_J6", "jaw_cap")}


_CACHE = {}


def man(m):
    return to_manifold(m)


def load_all():
    meshes = {}
    for _, names in GROUPS:
        for n in names:
            p = os.path.join(OUT, n + ".stl")
            if os.path.exists(p):
                meshes[n] = trimesh.load_mesh(p, force="mesh")
    return meshes


def overlap_any(moving, fixed):
    """moving/fixed: {name: (trimesh, manifold)}"""
    worst = (0.0, None)
    for na, (a, ma) in moving.items():
        for nb, (b, mb) in fixed.items():
            if {(na, nb), (nb, na)} & (SKIP | PRESS_PAIRS):
                continue
            lo = np.maximum(a.bounds[0], b.bounds[0])
            hi = np.minimum(a.bounds[1], b.bounds[1])
            if np.any(lo >= hi):
                continue
            v = (ma ^ mb).volume()
            if v > worst[0]:
                worst = (v, f"{na} x {nb}")
    return worst


def sweep(joint, meshes):
    gi = [g for g, _ in GROUPS].index(joint)
    fixed = {n: (meshes[n], man(meshes[n])) for g, ns in GROUPS[:gi] for n in ns if n in meshes}
    mov0 = {n: (meshes[n], man(meshes[n])) for g, ns in GROUPS[gi:] for n in ns if n in meshes}
    if not mov0 or not fixed:
        print(f"{joint}: no parts to test (skipped)")
        return True
    axis, pt = AXES[joint]
    lo, hi = kp.LIM[joint]
    step = 10 if joint == "J1" else STEP
    bad = []
    a = lo
    while a <= hi + 1e-9:
        T = trimesh.transformations.rotation_matrix(math.radians(a), axis, pt)
        mov = {n: (m.copy().apply_transform(T), mm.transform(T[:3, :4].tolist()))
               for n, (m, mm) in mov0.items()}
        v, pair = overlap_any(mov, fixed)
        if v > INTERF_MAX:
            bad.append((a, v, pair))
        a += step
    if not bad:
        print(f"{joint}: lo={lo:g} hi={hi:g} safe=[{lo:g}, {hi:g}] OK")
        return True
    neg = [b[0] for b in bad if b[0] < 0]
    pos = [b[0] for b in bad if b[0] >= 0]
    s_lo = (max(neg) + step) if neg else lo
    s_hi = (min(pos) - step) if pos else hi
    for b in bad[:6]:
        print(f"   {joint} at {b[0]:g} deg: {b[1]:.1f} mm3 {b[2]}")
    print(f"{joint}: lo={lo:g} hi={hi:g} safe=[{s_lo:g}, {s_hi:g}] BAD")
    return False


def main(argv):
    joints = argv or ["J1", "J2", "J3", "J4", "J5", "J6"]
    meshes = load_all()
    if len(meshes) < 20:
        print(f"only {len(meshes)} STLs in out/ - run build.py first")
        print("ROM FAIL")
        return 1
    ok = all([sweep(j, meshes) for j in joints])
    print("ROM PASS" if ok else "ROM FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
