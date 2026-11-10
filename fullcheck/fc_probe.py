"""fullcheck/fc_probe.py - exact min-distance probes at the home pose.

Loads the same posed STL set as fc_collision.py (R9 wrist), but only at
q=0 - no sweep. Reports surface-sampled min distances on the tightest
pairs so the 0.5 mm clearance question has real numbers, not bbox gaps.

Run: $PY fullcheck/fc_probe.py [--tc]
"""
import math, os, sys
import numpy as np
import trimesh
from trimesh.proximity import closest_point
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "refine", "out")
TC_OUT = os.path.join(ROOT, "toolchg", "out")
TC = "--tc" in sys.argv

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
WR_PARTS = ["w_j4_cradle", "w_link4", "w_link5",
            "vendor_sts3215_j5", "vendor_sts3215_j6"]
if TC:
    WR_PARTS += ["tc_master", "fix_tool_grip_posed", "tc_vendor_g", "tc_gear",
                 "tc_rack_u", "tc_rack_d", "tc_finger_u", "tc_finger_d"]
else:
    WR_PARTS += ["wrist_pin", "w_grip_frame", "vendor_sts3215_g",
                 "vendor_gear_grip", "vendor_rack_u", "vendor_rack_d",
                 "finger_u", "finger_d"]
CYC_UP = {"housing", "pin_ring", "front_ring", "vendor_ringpins", "vendor_motor",
          "mag_puck", "vendor_magnet", "vendor_as5600", "vendor_6808",
          "disc1", "disc2", "hub", "vendor_6702a", "vendor_6702b"}
CYC_OUT = {"carrier", "out_flange", "vendor_dowels", "vendor_outpins", "vendor_685"}
J2, J3 = P.J2_XZ, P.J3_XZ
M_J2 = rotmat(math.radians(P.POSE_J2), (0, 1, 0), (J2[0], 0, J2[1]))
M_J3 = rotmat(math.radians(P.POSE_J3), (0, 1, 0), (J3[0], 0, J3[1]))
RX90 = rotmat(math.radians(90.0), (1, 0, 0))
def place(jxz):
    return tmat((jxz[0], P.ACT_BACK_Y, jxz[1])) @ RX90
M2_UP, M2_OUT = M_J2 @ place(J2), place(J2)
M3_UP, M3_OUT = M_J2 @ place(J3), M_J2 @ M_J3 @ place(J3)
FO = M_J2 @ M_J3
REPOSE = {"back_spacer_j2": M_J2, "back_spacer_j3": M_J2,
          "vendor_spring_j2": M_J2, "vendor_spring_j3": M_J2,
          "flange_j3": FO, "vendor_sts3250_j4": FO}

MESH = {}
for d, drop in ((A2B, DROP), (C3, set())):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if f[:-4] in REPOSE:
                m.apply_transform(REPOSE[f[:-4]])
            m.merge_vertices()
            MESH[f[:-4]] = m
wrd = TC_OUT if TC else WR
for n in WR_PARTS:
    p = os.path.join(wrd, n + ".stl")
    if not os.path.exists(p):
        p = os.path.join(WR, n + ".stl")
    m = trimesh.load_mesh(p, force="mesh"); m.merge_vertices()
    MESH[n] = m
for f in sorted(os.listdir(CYC)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    m = trimesh.load_mesh(os.path.join(CYC, f), force="mesh"); m.merge_vertices()
    up = n in CYC_UP
    a = m.copy(); a.apply_transform(M2_UP if up else M2_OUT); MESH["cy2_" + n] = a
    b = m.copy(); b.apply_transform(M3_UP if up else M3_OUT); MESH["cy3_" + n] = b

# plug proxies (same numbers as fc_collision)
def _plug(a0, a1, h0, h1, name):
    b = trimesh.creation.box(extents=(a1 - a0, 18.0, h1 - h0))
    b.apply_translation((96.4 + (a0 + a1) / 2.0, 0.0, 216.2 + (h0 + h1) / 2.0))
    MESH[name] = b
_plug(41.6, 52.6, 35.6, 47.8, "plug_j5")
_plug(12.8, 25.0, -39.0, -28.0, "plug_j6")
if not TC:
    _plug(66.8, 79.0, -39.0, -28.0, "plug_g")

def mind(a, b):
    ma, mb = MESH[a], MESH[b]
    pa = np.vstack([ma.vertices, ma.sample(4000)])
    pb = np.vstack([mb.vertices, mb.sample(4000)])
    d1 = closest_point(mb, pa)[1].min()
    d2 = closest_point(ma, pb)[1].min()
    return min(float(d1), float(d2))

PROBE = [("w_link4", "w_j4_cradle", "l4 yoke/boss vs cradle (0.2 rad / 0.5 face design)"),
         ("wrist_pin", "w_link4", "pin in journal bore (0.20 rad design)"),
         ("wrist_pin", "w_j4_cradle", "pin in cradle pad (glue fit)"),
         ("wrist_pin", "fore_r2", "pin tail vs fore plate"),
         ("w_link4", "fore_r2", "l4 vs fore_r2 plate"),
         ("w_link4", "vendor_sts3250_j4", "l4 plate vs J4 case (horn zone)"),
         ("w_link5", "w_link4", "l5 vs l4 (J5 interface)"),
         ("w_link5", "vendor_sts3215_j5", "l5 plate vs J5 case"),
         ("vendor_sts3215_j6", "w_link5", "j6 case in l5 pocket"),
         ("w_j4_cradle", "fore_r2", "cradle flange vs fore_r2 (mount face)"),
         ("w_j4_cradle", "fore_l2", "cradle vs fore_l2"),
         ("w_j4_cradle", "vendor_sts3250_j4", "cradle vs J4 case"),
         ("w_link5", "cy3_out_flange", "l5 vs J3 out flange"),
         ("w_j4_cradle", "cy3_out_flange", "cradle vs J3 out flange"),
         ("w_link4", "cy3_out_flange", "l4 vs J3 out flange")]
if not TC:
    PROBE += [("w_grip_frame", "w_link5", "gf horn plate vs l5 (~0.8 design)"),
              ("w_grip_frame", "w_link4", "gf ribs vs l4 collar (~0.8)"),
              ("w_grip_frame", "vendor_sts3215_j6", "gf plate vs J6 case"),
              ("vendor_gear_grip", "w_grip_frame", "gear in cage bore"),
              ("vendor_rack_u", "w_grip_frame", "rack in cage slot"),
              ("finger_u", "vendor_rack_u", "finger on rack"),
              ("plug_j5", "w_link5", "j5 cable plug vs l5"),
              ("plug_j6", "w_grip_frame", "j6 plug vs gf"),
              ("plug_g", "w_link5", "g plug vs l5"),
              ("plug_g", "w_grip_frame", "g plug vs gf")]
else:
    PROBE += [("tc_master", "w_link5", "master plate vs l5"),
              ("tc_master", "vendor_sts3215_j6", "master vs J6 case"),
              ("fix_tool_grip_posed", "w_link5", "tool cage vs l5"),
              ("fix_tool_grip_posed", "w_link4", "tool cage vs l4 collar"),
              ("fix_tool_grip_posed", "tc_master", "tool docked to master (designed)"),
              ("tc_gear", "fix_tool_grip_posed", "tool gear in cage"),
              ("tc_rack_u", "fix_tool_grip_posed", "tool rack in cage")]

print("== home-pose exact min distances (verts + 4000 surface pts/direction) ==")
for a, b, note in PROBE:
    if a not in MESH or b not in MESH:
        print("   %-22s x %-22s  MISSING" % (a, b))
        continue
    d = mind(a, b)
    print("   %-22s x %-22s %7.3f mm   %s" % (a, b, d, note))
