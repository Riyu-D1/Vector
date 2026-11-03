"""wrist/export_wrist_asm.py - D5 assembly: same composition as final/export_assembly.py
but the 4 structural wrist parts (j4_cradle, link4, link5, grip_frame) are replaced by
the D5 w_* parts from wrist/out.  Everything else (drops, reposes, cyclo4 modules) is
identical.  Writes: wrist/out_asm/assembly.stl|.step, wrist/renders/_tmp/list.txt.
Run:  PY export_wrist_asm.py"""
import os, sys, math
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(HERE, "out")
OUT = os.path.join(HERE, "out_asm")
TMP = os.path.join(HERE, "renders", "_tmp")
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame"}     # D5 replacements from wrist/out

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
for f in sorted(os.listdir(WR)):                       # D5 wrist parts, posed home
    if f.startswith("w_") and f.endswith(".stl"):
        parts.append((f[:-4], "frame", trimesh.load_mesh(os.path.join(WR, f), force="mesh")))
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

asm = trimesh.util.concatenate([m for _, _, m in parts])
asm.merge_vertices()
asm.export(os.path.join(OUT, "assembly.stl"))
b = asm.bounds
print("assembly.stl %.1f MB  bbox %.0f x %.0f x %.0f mm  watertight %s"
      % (os.path.getsize(os.path.join(OUT, "assembly.stl")) / 1e6,
         *(b[1] - b[0]), asm.is_watertight))

from build123d import import_step, Compound, Pos, Rot, Axis, export_step

def pose_step(s, jn, up):
    jxz = J2 if jn == 2 else J3
    s = (Pos(jxz[0], P.ACT_BACK_Y, jxz[1]) * Rot(90, 0, 0)) * s
    if jn == 3 and not up:
        s = s.rotate(Axis((J3[0], 0, J3[1]), (0, 1, 0)), P.POSE_J3)
    if up or jn == 3:
        s = s.rotate(Axis((J2[0], 0, J2[1]), (0, 1, 0)), P.POSE_J2)
    return s

solids = []
for d, drop in ((A2B, DROP), (C3, set())):
    for f in sorted(os.listdir(d)):
        if f.endswith(".step") and f[:-5] not in drop:
            for s in import_step(os.path.join(d, f)).solids():
                if f[:-5] in REPOSE:
                    if REPOSE[f[:-5]] is FO:
                        s = s.rotate(Axis((J3[0], 0, J3[1]), (0, 1, 0)), P.POSE_J3)
                    s = s.rotate(Axis((J2[0], 0, J2[1]), (0, 1, 0)), P.POSE_J2)
                solids.append(s)
for f in sorted(os.listdir(WR)):
    if f.startswith("w_") and f.endswith(".step"):
        solids.extend(import_step(os.path.join(WR, f)).solids())
cyc_names = [f[:-5] for f in sorted(os.listdir(CYC)) if f.endswith(".step")]
for jn in (2, 3):
    for n in cyc_names:
        for s in import_step(os.path.join(CYC, n + ".step")).solids():
            solids.append(pose_step(s, jn, n in CYC_UP))
export_step(Compound(children=solids), os.path.join(OUT, "assembly.step"))
print("assembly.step %.1f MB  %d solids"
      % (os.path.getsize(os.path.join(OUT, "assembly.step")) / 1e6, len(solids)))
print("DONE")
