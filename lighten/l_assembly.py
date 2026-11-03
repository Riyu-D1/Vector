"""lighten/l_assembly.py - render-list for the full-arm iso (D9).

Mesh set + transforms copied verbatim from cradlefix/cf_export_assembly.py
(itself final/export_assembly.py): arm2b minus DROP, cad3 overrides, wrist2
D6 parts, 2x cyclo4 modules.  D9 swapped nothing (no plate variant passed
the FEA gate) so the set is the proven stock set.
Writes: lighten/rend/_tmp/<group>.stl + list.txt for l_render.py.
Run:  ~/Vector-wt/cradlefix/.venv/bin/python lighten/l_assembly.py
"""
import os, sys, math
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "wrist2", "out")
TMP = os.path.join(HERE, "rend", "_tmp")
os.makedirs(TMP, exist_ok=True)

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
WR_SKIP = {"vendor_sts3215_j4"}              # real J4 = cad3 vendor_sts3250_j4

CYC_UP = {"housing", "pin_ring", "front_ring", "vendor_ringpins", "vendor_motor",
          "mag_puck", "vendor_magnet", "vendor_as5600", "vendor_6808",
          "disc1", "disc2", "hub", "vendor_6702a", "vendor_6702b"}
CYC_OUT = {"carrier", "out_flange", "vendor_dowels", "vendor_outpins", "vendor_685"}
CYC_PRINT = {"housing", "pin_ring", "front_ring", "disc1", "disc2", "carrier", "out_flange", "hub", "mag_puck"}

J2, J3 = P.J2_XZ, P.J3_XZ
M_J2 = rotmat(math.radians(P.POSE_J2), (0, 1, 0), (J2[0], 0, J2[1]))
M_J3 = rotmat(math.radians(P.POSE_J3), (0, 1, 0), (J3[0], 0, J3[1]))
RX90 = rotmat(math.radians(90.0), (1, 0, 0))

def place(jxz):
    return tmat((jxz[0], P.ACT_BACK_Y, jxz[1])) @ RX90

M2_UP,  M2_OUT  = M_J2 @ place(J2), place(J2)
M3_UP,  M3_OUT  = M_J2 @ place(J3), M_J2 @ M_J3 @ place(J3)
assert CYC_UP | CYC_OUT == {f[:-4] for f in os.listdir(CYC) if f.endswith(".stl")}

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

COL = {"frame": "0.30 0.31 0.36", "cyc_print": "0.20 0.26 0.36",
       "cyc_metal": "0.58 0.58 0.62", "servo": "0.78 0.38 0.12", "metal": "0.55 0.56 0.60"}

FO = M_J2 @ M_J3
REPOSE = {"back_spacer_j2": M_J2, "back_spacer_j3": M_J2,
          "vendor_spring_j2": M_J2, "vendor_spring_j3": M_J2,
          "flange_j3": FO, "vendor_sts3250_j4": FO}

parts = []
for d, drop in ((A2B, DROP), (C3, set())):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if f[:-4] in REPOSE:
                m.apply_transform(REPOSE[f[:-4]])
            parts.append((f[:-4], g_arm(f[:-4]), m))
for f in sorted(os.listdir(WR)):
    if f.endswith(".stl") and f[:-4] not in WR_SKIP:
        parts.append((f[:-4], g_arm(f[:-4]), trimesh.load_mesh(os.path.join(WR, f), force="mesh")))
for f in sorted(os.listdir(CYC)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    m = trimesh.load_mesh(os.path.join(CYC, f), force="mesh")
    up = n in CYC_UP
    a = m.copy(); a.apply_transform(M2_UP if up else M2_OUT); parts.append(("cy2_" + n, g_cyc(n), a))
    b = m.copy(); b.apply_transform(M3_UP if up else M3_OUT); parts.append(("cy3_" + n, g_cyc(n), b))

print("parts %d  tris %d" % (len(parts), sum(len(m.faces) for _, _, m in parts)))

groups = {}
for n, g, m in parts:
    groups.setdefault(g, []).append(m)
with open(os.path.join(TMP, "list.txt"), "w") as fh:
    for g, ms in groups.items():
        c = trimesh.util.concatenate(ms)
        p = os.path.join(TMP, g + ".stl"); c.export(p)
        fh.write("%s %s\n" % (p, COL[g]))
print("wrote %s" % os.path.join(TMP, "list.txt"))
