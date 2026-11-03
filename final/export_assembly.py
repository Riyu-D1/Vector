"""final/export_assembly.py - compose the SOMA arm FINAL assembly (arm-final / D4):
  arm2b posed parts (home L pose)
  - dropped:   vendor_act_j2/j3, vendor_actout_j2/j3   (old actuator proxies, replaced by cyclo4)
               vendor_sts3215_j4                        (D2 swap -> STS3250)
               vendor_6803_j2/j3                        (D2: cavity reclaimed by the springs)
  - overrides: back_spacer_j2/j3, flange_j2/j3         (cad3 D2 versions, already posed)
  - added:     vendor_spring_j2/j3, vendor_sts3250_j4  (cad3 D2)
  - added:     2x cyclo4 actuator modules (cyclo4/out, module frame) at J2 and J3
  - F2:        arm2b wrist parts (j4_cradle, link4, link5, grip_frame + posed
               vendor proxies) swapped for the wrist2/out K-KEEL parts; the
               wrist2 vendor_sts3215_j4 proxy stays skipped (J4 = cad3 STS3250).
Module -> arm frame:  +Z_mod -> -Y_arm, +X_mod -> +X_arm, +Y_mod -> +Z_arm;
back face at ACT_BACK_Y=23.4 (out face lands at ACT_OUT_Y=-31.6), then arm pose:
  housing-side parts  -> group 'up'  (rotate POSE_J2 about the J2 axis)
  output-side parts   -> J2 'fix' / J3 'fo' (flange pattern clocks to the front_spacer,
                         matching the vendor_actout proxies it replaces)
Writes:  final/out/assembly.step, final/out/assembly.stl
         final/renders/_tmp/*.stl + list.txt  (colour groups for render_blend.py)
Run:  PY final/export_assembly.py        (soma venv python)
"""
import os, sys, math
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "wrist2", "out")
OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "renders", "_tmp")
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

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

M2_UP,  M2_OUT  = M_J2 @ place(J2), place(J2)                 # J2 module: up / fix
M3_UP,  M3_OUT  = M_J2 @ place(J3), M_J2 @ M_J3 @ place(J3)   # J3 module: up / fo
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

# cad3/out parts were all exported in the UNROTATED build frame (J2 parts look
# posed only because J2 is the pivot). Re-pose each with its arm2b group transform:
# 'fo' = rotate POSE_J3 about the J3 axis then POSE_J2 about the J2 axis;
# 'up' = POSE_J2 about J2 only; 'fix' = identity (flange_j2 already correct).
FO = M_J2 @ M_J3
REPOSE = {"back_spacer_j2": M_J2, "back_spacer_j3": M_J2,
          "vendor_spring_j2": M_J2, "vendor_spring_j3": M_J2,
          "flange_j3": FO, "vendor_sts3250_j4": FO}

parts = []   # (name, group, mesh)
for d, drop in ((A2B, DROP), (C3, set())):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if f[:-4] in REPOSE:
                m.apply_transform(REPOSE[f[:-4]])
            parts.append((f[:-4], g_arm(f[:-4]), m))
for f in sorted(os.listdir(WR)):                       # D6 wrist2 parts, posed home
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

# ---- render groups ----
groups = {}
for n, g, m in parts:
    groups.setdefault(g, []).append(m)
with open(os.path.join(TMP, "list.txt"), "w") as fh:
    for g, ms in groups.items():
        c = trimesh.util.concatenate(ms)
        p = os.path.join(TMP, g + ".stl"); c.export(p)
        fh.write("%s %s\n" % (p, COL[g]))

# ---- assembly.stl ----
asm = trimesh.util.concatenate([m for _, _, m in parts])
asm.merge_vertices()
asm.export(os.path.join(OUT, "assembly.stl"))
b = asm.bounds
print("assembly.stl %.1f MB  bbox %.0f x %.0f x %.0f mm  watertight %s"
      % (os.path.getsize(os.path.join(OUT, "assembly.stl")) / 1e6,
         *(b[1] - b[0]), asm.is_watertight))

# ---- assembly.step (fresh import per module instance: shared TShapes fail the writer) ----
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
    if f.endswith(".step") and f[:-5] not in WR_SKIP:
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
