"""genlinks/render_gen.py - scene lists for Blender renders (D8).

  python3 genlinks/render_gen.py            -> writes list files under
                                             genlinks/renders/_tmp/
Scenes:
  arm_before    full arm, original links (final/export_assembly.py part set)
  arm_after     full arm, generated links swapped in (highlighted orange)
  <part>_ba     per-candidate before + after side by side (after offset +y)

Mesh sources: prebuilt outputs in the sibling final2 worktree (same commit),
generated links in genlinks/out/. Render with:
  /usr/local/bin/blender -b -P genlinks/render_blend.py -- <prefix> <list.txt>
"""
import os, sys, math
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "renders", "_tmp")
os.makedirs(TMP, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P

F2 = "/Users/deepakdiwan/Vector-wt/final2"
A2B, C3, CYC = (os.path.join(F2, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(F2, "wrist2", "out")

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
WR_SKIP = {"vendor_sts3215_j4"}
CYC_UP = {"housing", "pin_ring", "front_ring", "vendor_ringpins", "vendor_motor",
          "mag_puck", "vendor_as5600", "vendor_6808",
          "disc1", "disc2", "hub", "vendor_6702a", "vendor_6702b"}
CYC_OUT = {"carrier", "out_flange", "vendor_dowels", "vendor_outpins", "vendor_685"}
CYC_PRINT = {"housing", "pin_ring", "front_ring", "disc1", "disc2", "carrier",
             "out_flange", "hub", "mag_puck"}
J2, J3 = P.J2_XZ, P.J3_XZ
M_J2 = rotmat(math.radians(P.POSE_J2), (0, 1, 0), (J2[0], 0, J2[1]))
M_J3 = rotmat(math.radians(P.POSE_J3), (0, 1, 0), (J3[0], 0, J3[1]))
RX90 = rotmat(math.radians(90.0), (1, 0, 0))
place = lambda jxz: tmat((jxz[0], P.ACT_BACK_Y, jxz[1])) @ RX90
M2_UP, M2_OUT = M_J2 @ place(J2), place(J2)
M3_UP, M3_OUT = M_J2 @ place(J3), M_J2 @ M_J3 @ place(J3)
FO = M_J2 @ M_J3
REPOSE = {"back_spacer_j2": M_J2, "back_spacer_j3": M_J2,
          "vendor_spring_j2": M_J2, "vendor_spring_j3": M_J2,
          "flange_j3": FO, "vendor_sts3250_j4": FO}

COL = {"frame": "0.30 0.31 0.36", "cyc_print": "0.20 0.26 0.36",
       "cyc_metal": "0.58 0.58 0.62", "servo": "0.78 0.38 0.12",
       "metal": "0.55 0.56 0.60", "gen": "0.90 0.45 0.10",
       "orig": "0.30 0.31 0.36"}


def g_arm(n):
    if n.startswith("vendor_sts"):
        return "servo"
    if n.startswith("vendor_"):
        return "metal"
    return "frame"


def g_cyc(n):
    if n in CYC_PRINT:
        return "cyc_print"
    if n in ("vendor_motor", "vendor_as5600"):
        return "servo"
    return "cyc_metal"


def gen_swaps():
    """generated STLs present in genlinks/out/ -> {orig_name: mesh}."""
    out = {}
    for f in sorted(os.listdir(OUT)):
        if f.endswith("_gen.stl"):
            out[f[:-8]] = trimesh.load_mesh(os.path.join(OUT, f), force="mesh")
    return out


def arm_parts(swap):
    """(name, group, mesh) like export_assembly, with generated links swapped."""
    parts = []
    for d, drop in ((A2B, DROP), (C3, set())):
        for f in sorted(os.listdir(d)):
            if f.endswith(".stl") and f[:-4] not in drop:
                n = f[:-4]
                if n in swap:
                    m = swap[n].copy()
                else:
                    m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
                if n in REPOSE:
                    m.apply_transform(REPOSE[n])
                parts.append((n, "gen" if n in swap else g_arm(n), m))
    for f in sorted(os.listdir(WR)):
        if f.endswith(".stl") and f[:-4] not in WR_SKIP:
            parts.append((f[:-4], g_arm(f[:-4]),
                          trimesh.load_mesh(os.path.join(WR, f), force="mesh")))
    for f in sorted(os.listdir(CYC)):
        if not f.endswith(".stl"):
            continue
        n = f[:-4]
        m = trimesh.load_mesh(os.path.join(CYC, f), force="mesh")
        up = n in CYC_UP
        a = m.copy(); a.apply_transform(M2_UP if up else M2_OUT)
        parts.append(("cy2_" + n, g_cyc(n), a))
        b = m.copy(); b.apply_transform(M3_UP if up else M3_OUT)
        parts.append(("cy3_" + n, g_cyc(n), b))
    return parts


def write_scene(name, parts):
    groups = {}
    for n, g, m in parts:
        groups.setdefault(g, []).append(m)
    lst = os.path.join(TMP, name + "_list.txt")
    with open(lst, "w") as fh:
        for g, ms in groups.items():
            c = trimesh.util.concatenate(ms)
            p = os.path.join(TMP, "%s_%s.stl" % (name, g))
            c.export(p)
            fh.write("%s %s\n" % (p, COL[g]))
    print("%s: %d parts -> %s" % (name, len(parts), lst))
    return lst


def before_after(part):
    """one scene: original at y=0, generated shifted +y so they sit side by side."""
    orig = trimesh.load_mesh(os.path.join(OUT, part + ".stl"), force="mesh")
    gen = trimesh.load_mesh(os.path.join(OUT, part + "_gen.stl"), force="mesh")
    dy = (orig.bounds[1] - orig.bounds[0])[1] + 25.0
    gen = gen.copy(); gen.apply_translation((0.0, dy, 0.0))
    orig.export(os.path.join(TMP, part + "_before.stl"))
    gen.export(os.path.join(TMP, part + "_after.stl"))
    lst = os.path.join(TMP, part + "_ba_list.txt")
    with open(lst, "w") as fh:
        fh.write("%s %s\n" % (os.path.join(TMP, part + "_before.stl"), COL["orig"]))
        fh.write("%s %s\n" % (os.path.join(TMP, part + "_after.stl"), COL["gen"]))
    print("%s before/after -> %s (offset +%.0f mm)" % (part, lst, dy))


def main():
    swap = gen_swaps()
    print("generated links available:", sorted(swap) or "NONE")
    write_scene("arm_before", arm_parts({}))
    if swap:
        write_scene("arm_after", arm_parts(swap))
        for n in swap:
            before_after(n)


if __name__ == "__main__":
    main()
