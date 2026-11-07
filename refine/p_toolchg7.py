"""refine/p_toolchg7.py - R1+R2 fix applied to the D10 tool_grip.

tool_grip inherits the w_grip_frame keel cage and therefore the same
mirrored-cheek defect (F9) and the same tangent rear weld.  Everything
comes from toolchg/p_toolchg.py except the cage, which is rebuilt with
the cheek fix and the ap7 (R-fix) cage outline.  No interface dimension
changes.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "toolchg"))
from p_toolchg import *          # noqa  (helpers, params, tc_plate, _neck, g_pocket...)
import p_toolchg as PT
import ap7 as N7                 # refine params (R-fix cage); p_toolchg's N stays stock

def tool_grip_r():
    s = PT.tc_plate() + PT._neck()
    for sg in (1, -1):        # cage cheeks (GF_CAGE shifted) - R1/R2 fix
        pts = tuple((a + PT.SH, h) for a, h in N7.GF_CAGE)
        b_lo, b_hi = sorted((sg * N7.GF_CHEEK_B[0], sg * N7.GF_CHEEK_B[1]))
        s = s + PT.xb(PT.poly_ah(b_lo, pts), b_lo, b_hi)
    s = s + PT.box(71.5 + PT.SH, 114.7 + PT.SH, -N7.GF_CHEEK_B[1],
                   N7.GF_CHEEK_B[1], N7.GF_BOTTOM - 2.0, N7.GF_BOTTOM)
    a0w, a1w, bh0, bh1 = N7.GF_BACKWALL
    s = s + PT.box(a0w + PT.SH, a1w + PT.SH, -N7.GF_CHEEK_B[1],
                   N7.GF_CHEEK_B[1], bh0, bh1)
    s = s - PT.g_pocket()
    hs, sh = N7.H_SH, N7.A_SH + PT.SH
    for sg in (1, -1):
        s = s + PT.box(PT.B.BR_A[0] + sh, PT.B.CH_A1 + sh, -PT.B.BR_B,
                       PT.B.BR_B,
                       *sorted((sg * PT.B.CH_H[0] + hs, sg * PT.B.CH_H[1] + hs)))
        s = s + PT.box(PT.B.LIP[0] + sh, PT.B.CH_A1 + sh, -PT.B.BR_B,
                       PT.B.BR_B,
                       *sorted((sg * PT.B.LIP[1] + hs, sg * PT.B.CH_H[0] + hs)))
    s = s + PT.xa(PT.bh(PT.B.BR_A[0] + sh, -PT.B.BR_B, PT.B.BR_B,
                        -PT.B.CH_H[1] + hs, PT.B.CH_H[1] + hs,
                        N7.GF_BRACKET_R),
                  PT.B.BR_A[0] + sh, PT.B.BR_A[1] + sh)
    s = s - PT.cyl((0, hs), PT.B.BR_HOLE, "a",
                   PT.B.BR_A[0] + sh - 1, PT.B.BR_A[1] + sh + 1)
    for sg in (1, -1):
        tri = PT.poly_ah(-PT.B.BR_B - 1,
                         ((PT.B.LIP[0] + sh, sg * PT.B.LIP[1] + hs),
                          (PT.B.LIP[0] + sh, sg * PT.B.CH_H[0] + hs),
                          (PT.B.LIP[0] + sh - N7.GF_LIP_CH,
                           sg * PT.B.LIP[1] + hs)))
        s = s - PT.xb(tri, -PT.B.BR_B - 1, PT.B.BR_B + 1)
    for ac, ahw, hc, hhw in N7.GF_WIN:
        s = s - PT.box(ac - ahw + PT.SH, ac + ahw + PT.SH,
                       -N7.GF_CHEEK_B[1] - 1, N7.GF_CHEEK_B[1] + 1,
                       hc - hhw, hc + hhw)
    s = s + PT.PB.cyl((N7.GF_CLEAT[0] + PT.SH, N7.GF_CLEAT[2]), 2.6, "b",
                      -N7.GF_CHEEK_B[1] - 3.0, -N7.GF_CHEEK_B[1] + 0.5)
    s = s + PT.PB.cyl((N7.GF_CLEAT[0] + PT.SH, N7.GF_CLEAT[2]), 4.4, "b",
                      -N7.GF_CHEEK_B[1] - 4.0, -N7.GF_CHEEK_B[1] - 3.0)
    return s
