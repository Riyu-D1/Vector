"""final/make_coupon.py - D4 flank-clearance calibration coupon (stage F1).

One plate carrying FOUR mesh stations at CLR_TOOTH = 0.00 / 0.05 / 0.10 /
0.15 mm. Each station replicates the real pin-vs-flank mesh at crank
angle 0 (disc centre at +E on +X, ring fixed):
  - 5 pin bores at the TRUE ring-pin positions (k = -2..+2), diameter
    ap.PIN_HOLE_D = the same hole the housing gets, blind 5.5 deep;
  - the disc flank arc segment at that CLR, extruded at the real disc
    thickness (4.25 mm), standing next to the bores.

Use: print flat in PETG-CF (~20 min), drop ISO 8734 3x10 dowels in the
bores, push each pin gently toward the flank and feeler-gauge the radial
gap = the printer's real as-printed clearance. Do this BEFORE printing
the 4 gearbox discs (see final/PRINT_LIST.md for pass criteria).

Geometry comes verbatim from cyclo4/cyc.py + cyclo4/ap.py (tested code).
Run from final/:  $PY make_coupon.py
Writes out/coupon.stl + out/coupon.step and prints the nominal per-pin
gap table (for PRINT_LIST.md).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cyclo4"))
sys.path.insert(0, os.path.join(ROOT, "cad", "knuckle"))

from build123d import Box, Polygon, Pos, extrude, export_stl, export_step
from frames import bb, zcyl
import ap
import cyc

CLRS = (0.00, 0.05, 0.10, 0.15)   # the four stations, left -> right
PINS = (-2, -1, 0, 1, 2)          # ring-pin indices around the +X mesh
SEG_HALF_DEG = 34.0               # flank arc half-window about +X (from C)
SEG_R_IN = 19.0                   # segment inner radius about C
PLATE_T = 6.0                     # base thickness = dowel seat depth
BORE_FLOOR = 0.5                  # blind-hole floor left in the plate
SPACING = 32.0                    # station pitch along X
MARGIN = 4.0                      # plate margin around station extents
DISC_T = ap.Z_DISC1[1] - ap.Z_DISC1[0]    # 4.25 — real disc thickness

N, NP, R, RP, E = cyc.gear()      # 40, 41, 23.5, 1.5, 0.42
C = np.array([E, 0.0])            # disc centre at crank angle 0


def pin_xy(k):
    a = 2.0 * math.pi * k / NP
    return np.array([R * math.cos(a), R * math.sin(a)])


def flank_arc(clr, half_deg=SEG_HALF_DEG):
    """Disc outline segment (housing frame) within +-half_deg of +X seen
    from the disc centre C — the arc the 5 coupon pins engage."""
    pts = cyc.profile(clr=clr, m=4000) + C
    ang = np.degrees(np.arctan2(pts[:, 1] - C[1], pts[:, 0] - C[0]))
    sel = pts[np.abs(ang) <= half_deg]
    sel = sel[np.argsort(np.arctan2(sel[:, 1] - C[1],
                                   sel[:, 0] - C[0]))]
    return sel


def station(clr, x_off):
    """One station: flank segment solid (on the plate top) translated
    x_off, plus the 5 pin bores to subtract."""
    arc = flank_arc(clr)
    inner = np.array([[C[0] + SEG_R_IN * math.cos(math.radians(a)),
                       C[1] + SEG_R_IN * math.sin(math.radians(a))]
                      for a in np.linspace(SEG_HALF_DEG, -SEG_HALF_DEG, 48)])
    poly = np.vstack([arc, inner])
    seg = Pos(x_off, 0, PLATE_T) * extrude(
        Polygon(*[(float(p[0]), float(p[1])) for p in poly], align=None),
        amount=DISC_T)
    bores = None
    for k in PINS:
        p = pin_xy(k)
        b = Pos(x_off, 0, 0) * zcyl(float(p[0]), float(p[1]),
                                    ap.PIN_HOLE_D, BORE_FLOOR,
                                    PLATE_T + 0.01)
        bores = b if bores is None else bores + b
    return seg, bores


def nominal_gaps():
    """Pin-surface -> flank clearance at crank 0 per station (mm) — what
    a perfect print would measure. m=20000 outline for accuracy."""
    out = {}
    for c in CLRS:
        poly = cyc.profile(clr=c, m=20000) + C
        row = []
        for k in PINS:
            p = pin_xy(k)[None, :]
            d = float(cyc.seg_dist(p, poly)[0]) - RP
            if cyc.inside(p, poly)[0]:
                d = -d
            row.append(d)
        out[c] = row
    return out


def main():
    body = None
    bores = None
    for i, c in enumerate(CLRS):
        seg, b = station(c, i * SPACING)
        body = seg if body is None else body + seg
        bores = b if bores is None else bores + b
    b = bb(body)
    plate = Pos((b[0] + b[1]) / 2 - MARGIN / 2 + MARGIN / 2,
                0, PLATE_T / 2) * \
        Box(b[1] - b[0] + 2 * MARGIN, b[3] - b[2] + 2 * MARGIN, PLATE_T)
    coupon = plate + body - bores
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    export_stl(coupon, os.path.join(HERE, "out", "coupon.stl"),
               tolerance=0.02, angular_tolerance=0.2)
    export_step(coupon, os.path.join(HERE, "out", "coupon.step"))
    print(f"coupon: bbox={bb(coupon)} vol={coupon.volume / 1000:.1f} cm3")
    print(f"stations L->R: CLR {CLRS}; pins k={PINS}; bores d"
          f"{ap.PIN_HOLE_D} x {PLATE_T - BORE_FLOOR:.1f} deep")
    print("nominal pin-surface -> flank gap at crank 0 (mm):")
    gaps = nominal_gaps()
    print("  clr    k=-2     k=-1     k=0      k=+1     k=+2")
    for c in CLRS:
        print(f"  {c:4.2f}  " + "  ".join(f"{d:+.3f}" for d in gaps[c]))


if __name__ == "__main__":
    main()
