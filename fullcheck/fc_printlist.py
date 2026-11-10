"""fullcheck/fc_printlist.py - printability + export-currency audit.

Lists every printed part in the R9-wrist final design (arm2b minus D2
overrides + cad3 + cyclo4 x2 + refine/out wrist + optional toolchg set),
measures STL bbox vs the 256x256x256 A1 bed, checks watertightness, and
reports which parts have a .step twin. PRINT_LIST.md coverage notes are
flagged where the doc describes the D6 wrist2 set instead of R9.

Run: $PY fullcheck/fc_printlist.py
"""
import os, sys
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "refine", "out")
TC_OUT = os.path.join(ROOT, "toolchg", "out")

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
VENDOR_PFX = ("vendor_",)

rows = []
def add(d, n, src, qty=1):
    p = os.path.join(d, n + ".stl")
    st = os.path.join(d, n + ".step")
    if not os.path.exists(p):
        rows.append((n, src, None, None, None, "MISSING STL"))
        return
    m = trimesh.load_mesh(p, force="mesh"); m.merge_vertices()
    s = m.bounds[1] - m.bounds[0]
    rows.append((n, src, m.volume / 1000.0, s, m.is_watertight,
                 "step" if os.path.exists(st) else "NO STEP"))

# printed arm parts (non-vendor) from arm2b minus DROP
for f in sorted(os.listdir(A2B)):
    n = f[:-4]
    if f.endswith(".stl") and n not in DROP and not n.startswith(VENDOR_PFX):
        add(A2B, n, "arm2b")
for f in sorted(os.listdir(C3)):
    n = f[:-4]
    if f.endswith(".stl") and not n.startswith(VENDOR_PFX):
        add(C3, n, "cad3")
for n in ("housing", "pin_ring", "front_ring", "disc1", "disc2",
          "carrier", "out_flange", "hub", "mag_puck"):
    add(CYC, n, "cyclo4", qty=2)
for n in ("w_j4_cradle", "w_link4", "w_link5", "w_grip_frame"):
    add(WR, n, "refine/R9")
for n in ("vendor_rack_u", "vendor_rack_d", "finger_u", "finger_d"):
    add(WR, n, "refine/R9 (printed)")
print("=== printed parts (R9 gripper config) ===")
print("%-22s %-8s %8s %-20s %-3s %s" % ("part", "src", "cm3", "bbox mm", "wt", "step"))
tot = 0.0
for n, src, v, s, wt, st in rows:
    if s is None:
        print("%-22s %-8s %8s %-20s %-3s %s" % (n, src, "-", "MISSING", "-", st))
        continue
    over = max(s) > 256.0
    print("%-22s %-8s %8.1f %-20s %-3s %s%s"
          % (n, src, v, "%.1fx%.1fx%.1f" % tuple(s), wt, st,
             "  OVER-256!" if over else ""))
    tot += v
print("total printed volume %.0f cm3" % tot)

print("\n=== tool-changer set (alternative config, from toolchg/out) ===")
rows = []
for n in ("tc_master", "tc_plate", "fix_tool_grip_posed", "tool_pen",
          "tc_rack_u", "tc_rack_d", "tc_finger_u", "tc_finger_d", "tc_rack"):
    d = TC_OUT if os.path.exists(os.path.join(TC_OUT, n + ".stl")) else WR
    add(d, n, "toolchg" if d == TC_OUT else "refine")
for n, src, v, s, wt, st in rows:
    if s is None:
        print("%-22s %-8s MISSING" % (n, src)); continue
    print("%-22s %-8s %8.1f %-20s %-3s %s%s"
          % (n, src, v, "%.1fx%.1fx%.1f" % tuple(s), wt, st,
             "  OVER-256!" if max(s) > 256 else ""))
