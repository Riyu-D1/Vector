"""cad3/checks/print_audit.py - volume + bbox of every printed part in the
final arm2b assembly (38 parts, vendor_* excluded) plus the 2 printed
actuator modules (cad/act2).  Output feeds cad3/PRINT_LIST.md.
Run: /Users/deepakdiwan/soma/.venv/bin/python print_audit.py
"""
import os, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
ARM = os.path.join(ROOT, "cad", "arm2b", "out")
ACT = os.path.join(ROOT, "cad", "act2", "out")

# every printed part in the final assembly + its STL
ARM_PRINTED = [
    "base_plate", "base_link", "j1_cradle", "base_reinf", "yaw_limit", "link1",
    "front_spacer_j2", "flange_j2", "back_spacer_j2",
    "upper_out", "upper_back",
    "front_spacer_j3", "flange_j3", "back_spacer_j3",
    "dogleg_l", "dogleg_r", "fore_l2", "fore_r2",
    "j4_cradle", "link4", "link5", "grip_frame",
    "vendor_rack_u", "vendor_rack_d", "finger_u", "finger_d",
]
ACT_PRINTED = ["housing", "front_ring", "pin_ring", "disc1", "disc2",
               "carrier", "out_flange", "hub", "mag_puck"]


def audit(path):
    m = trimesh.load(path, force="mesh")
    ext = m.extents
    vol = m.volume if m.is_watertight else abs(m.volume)
    return vol, tuple(ext), m.is_watertight


def main():
    print("%-20s %10s  %-28s %s" % ("part", "vol cm3", "bbox XYZ mm", "watertight"))
    tot = 0.0
    for n in ARM_PRINTED:
        v, e, w = audit(os.path.join(ARM, n + ".stl"))
        tot += v
        print("%-20s %10.1f  %6.1f x%6.1f x%6.1f  %s" % (n, v / 1000, e[0], e[1], e[2], w))
    print("arm printed total %.0f cm3" % (tot / 1000))
    t2 = 0.0
    for n in ACT_PRINTED:
        v, e, w = audit(os.path.join(ACT, n + ".stl"))
        t2 += v
        print("%-20s %10.1f  %6.1f x%6.1f x%6.1f  %s" % (n, v / 1000, e[0], e[1], e[2], w))
    print("per-module printed total %.0f cm3; x2 = %.0f" % (t2 / 1000, 2 * t2 / 1000))
    print("grand total %.0f cm3 = %.0f g @ PETG-CF 1.31 g/cm3"
          % ((tot + 2 * t2) / 1000, (tot + 2 * t2) / 1000 * 1.31))


if __name__ == "__main__":
    main()
