"""refine/mass_r5.py - R5 correction of the upgrade1 wrist mass model.

gravity_up1.py's wrist entries were a stale D6 snapshot (pre R-round
re-layout): wrist5/grip body origins and all wrist centroids referenced
the OLD joint positions (J4_J5 = 37.6-era, wrist ~17 mm higher).  Every
vendor-part AB centroid in the PRODUCT gravity.py matches the measured
arm2b W-frame centroid to <=0.01 mm via AB = W + (223.1, 0, 89.5), so
the correct origins are the product (kinematics-consistent) ones:

    AB pose: q = [0, +90, -90, 0, 0, 0]; W -> world = + (223.1, 0, 89.5)
    wrist5 origin = J4 + W_J5 = (223.1+30.6, 0, 89.5+7.6) = (253.7, 0, 97.1)
    grip   origin = + W_J6 = (253.7+22.4, 0, 97.1-24.6) = (276.1, 0, 72.5)

Corrections applied here:
  1. _ORIGIN_AB wrist5/grip restored to the kinematic values.
  2. w_j4_cradle moves back to the "fore" body (it clamps the J4 case /
     stator side, bolted to the fore plates - product convention; R4 had
     lumped it into wrist4 which also double-located it).
  3. Plastic entries = measured solid volumes x rho(1.31e-3 g/mm3)
     x INFILL_EFF 0.6 at measured W centroids (+223.1, 0, +89.5).
     R5 post-trim values (build123d .volume/.center on the p_wrist7
     solids; R4 pre-trim in brackets):
       cradle 16.27 cc -> 12.79 g @ (209.07,  8.62, 89.42)  [fore]  (was 17.00 cc)
       l4     16.77 cc -> 13.18 g @ (252.33,-15.10,101.83)  [wrist4](was 19.79 cc;
             filleted windows; collar-window cut reverted after its
             rim reached sigma_n +9.6 tensile at (66.4,+-11.4,22))
       l5      8.64 cc ->  6.79 g @ (259.19, -0.13, 59.47)  [wrist5]
       gf     17.54 cc -> 13.79 g @ (321.62, -0.03, 63.41)  [grip] (R5 window
             REVERTED - it put sigma_n +-28 MPa at the existing (67,+-12.5,-25)
             notch; gf stays at R3/R4 geometry)
  4. Vendor part centroids restored to product/measured positions
     (j5/j6/g servos, gear, racks, fingers); masses unchanged.

apply(G1) mutates the imported gravity_up1 module before use.
"""
import sys, os
import numpy as np

# (body, mass kg, AB-pose centroid mm) - measured R5 geometry
PLASTIC = [
    ("fore",   0.01279, (209.07,   8.62,  89.42)),   # cradle 16.27 cc
    ("wrist4", 0.01318, (252.33, -15.10, 101.83)),   # l4 16.77 cc (filleted; collar window reverted)
    ("wrist5", 0.00679, (259.19,  -0.13,  59.47)),   # l5 8.64 cc
    ("grip",   0.01379, (321.62,  -0.03,  63.41)),   # gf 17.54 cc (window reverted)
]
RHO6 = 1.31e-3 * 0.6          # g/mm3 effective (60 % infill convention)

VENDOR = [
    ("wrist4", 0.05500, (266.29,   0.00, 108.57)),   # j5 servo
    ("wrist5", 0.05500, (264.63,   0.00,  59.91)),   # j6 servo
    ("grip",   0.05500, (318.63,   0.00,  59.91)),   # g servo
    ("grip",   0.00800, (342.80,   0.00,  72.50)),   # gear
    ("grip",   0.01200, (343.00, -12.99,  86.22)),   # rack_u
    ("grip",   0.01200, (343.00,  12.99,  58.78)),   # rack_d
    ("grip",   0.00097, (354.18,   3.00,  72.88)),   # finger_u
    ("grip",   0.00097, (354.18,  -3.00,  72.12)),   # finger_d
]

ORIGINS = {"wrist5": (253.7, 0.0, 97.1), "grip": (276.1, 0.0, 72.5)}

# stale up1 wrist entries to drop (matched by (body, mass))
DROP = [
    ("wrist4", 0.02810000), ("wrist4", 0.05500000),
    ("wrist5", 0.00660000), ("wrist5", 0.05500000),
    ("grip",   0.01340000), ("grip",   0.05500000), ("grip", 0.00800000),
    ("grip",   0.01200000), ("grip",   0.01200000),
    ("grip",   0.00096585), ("grip",   0.00096585),
]


def apply(G1):
    """Patch gravity_up1 in place: corrected origins + measured
    wrist/fore entries (R5 post-trim PLASTIC + VENDOR)."""
    drop = set(DROP)
    G1.PARTS = [p for p in G1.PARTS
                if not any(p[0] == b and abs(p[1] - m) < 2e-5
                           for b, m in drop)]
    G1.PARTS += PLASTIC + VENDOR
    G1._ORIGIN_AB_MM.update(ORIGINS)
    G1._LOCAL = G1._local_parts()
    return G1
