"""refine/ap7.py - D6 wrist+gripper v2 numbers (mm, deg) - layout K "keel",
WITH the R1/R2 repairs applied.  Copy of cradlefix/ap6.py; the only changed
values are marked `# R-fix`.

Bolder pass over D5: the wrist narrows and tapers into the gripper.
  - J5 yaw servo lies along the tool axis as a slim dorsal FIN above the wrist
    (case 45 long in a, 25 wide in b, face DOWN at h -2.0).
  - J6 + gripper servos hang inline BELOW the axis as a continuous ventral keel;
    the whole gripper rolls about the line h = -17.0 (TCP drops 17 mm vs D5,
    x-reach unchanged at 374.9).
  - Every case is +/-12.4 in b: the D5 +35 mm side poke is gone.
Interface numbers (J4 cradle bolts, horn PCD, rack/gear/finger solids, case
dims) come from cad/arm2b/ap2b.py (B) and cad/arm2/ap2.py (P2), imported.
Tags: [S] sourced, [D] design choice, [U] unverified.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
import ap2 as P2          # noqa
import ap2b as B          # noqa

# ---------- shared shell rules [D] ----------
WALL = 2.0                 # shell wall on a servo pocket (same as D5)
RR = 5.0                   # default outside corner radius
RHO_PETGCF = 1.31e-3       # g/mm^3 solid PETG-CF
INFILL_EFF = 0.6           # [U] printed/solid mass factor (ap2 convention)

# ---------- joint axes / spans [D] ----------
# W frame (ap2b): origin on the J4 axis, a = tool direction, b = world Y, h = up.
A_J5 = 30.6                # J5 yaw axis position on a (case a0 = 20.49 needs R>19 rule)
H_J5 = 7.6                 # J5 horn centre height; face at -2.0 (down)
J5_FACE_H = -2.0
J6_AX_H = -17.0            # J6 + gripper roll line height (TCP line)
A_J6 = 53.0                # J6 horn centre on a (face 62.6; g plug -a end 66.8 clears j6 case ~60.2 and j5 case 65.7)
A_G = 107.0                # gripper servo horn centre on a (+5.6 vs B: the g plug's roll
                           # tube must start past the j5 case end a 65.7 for a free J6)
A_SH = A_G - 101.4         # +5.6 a-shift on every B rack-cage/gear/finger position
A_TCP = 137.4              # TCP on a (B 131.8 + A_SH)
H_TCP = J6_AX_H
J4_J5 = A_J5               # 30.6 (was 37.6)
J5_J6 = A_J6 - A_J5        # 26.4 frame span (J6 horn centre)
J6_TCP = A_TCP - A_J6      # 74.8

# ---------- servo poses in W: (horn centre, ly dir, lx dir) [D] ----------
SERVOS = {
    "j4": B.SERVOS["j4"],                                  # unchanged
    "j5": ((A_J5, 0.0, H_J5), (0, 0, -1), (-1, 0, 0)),     # face down, case +a
    "j6": ((A_J6, 0.0, J6_AX_H), (1, 0, 0), (0, 0, 1)),    # case below axis
    "g":  ((A_G, 0.0, J6_AX_H), (1, 0, 0), (0, 0, 1)),
}
# case boxes (nominal, incl plug+horn; measured by envelope_check):
#   j5: a 20.49..65.72  b +-12.36  h -1.5(horn)..47.8(plug)   [case h 0.10..35.80]
#   j6: a 12.8..62.1    b +-12.36  h -52.12..-6.89            [plug a 12.8..24.8 h -39..-28]
#   g:  a 66.8..116.1   b +-12.36  h -52.12..-6.89            [plug a 66.8..78.8, face 116.6]

# ---------- w_j4_cradle (J4 servo sleeve + bolt plate, D5 interface kept) [D] ----------
CR_OUT = (-37.3, 12.3, -14.5, 14.5, 6.0)        # sleeve outer a0,a1,h0,h1,r
CR_B = (-20.0, 13.0)
CR_PLATE_B = (28.5, 32.55)
CR_PLATE = (-34.0, 0.0, -14.0, 14.0, 5.0)
CR_BOSS_D = 8.0; CR_BOSS_B = (12.9, 28.5)
CR_SLOT = (-22.3, -10.7, 11.0, 25.5, 4.0, 16.0)          # J4 plug exit slot
CR_GROOVE = (-36.0, -10.0, 14.0, 18.5, 13.6, 14.8)       # cable guide groove

# ---------- w_link4: J4 horn plate + strut + dorsal fin (J5 case) [D] ----------
L4_B = B.L4_B                                   # (-30.65, -26.65) horn plate b
L4_PLATE = (-15.0, 15.0, -15.0, 15.0, 5.0)      # horn plate a-h profile
# R-fix: stock strut polygon self-intersects at TWO sections (trailing edge
# (14,0)->(5,-12) crosses the leading edge at a~8.8; the (24,10)->(30,22)
# segment also inverts vs the outer edge at a~21) -> the rib builds as
# disconnected fragments and the J4 horn plate is a detached island.
# Re-profiled as a clean 6-point tapered rib over the same envelope
# (a 5..40, h -13..38.2, b -30.65..-26.65): plate-side weld a 5..15,
# rib-box weld a 16+.
L4_STRUT = ((5.0, -13.0), (14.0, -4.0), (40.0, 38.2),
            (36.0, 38.2), (14.0, 4.0), (8.0, -4.0))   # rib silhouette a-h, b = L4_B
L4_CHEEK_B = (12.51, 14.91)                     # fin cheeks +-b (case b +-12.36 + clr)
# fin a-h outline: full height a<=61.05; tail above h 7.5 only (clears the grip-plug
# roll tube: plug sweeps r 24.2 about h -17 -> reaches h +7.2 at a 61.2..66)
# R-fix: bottom edge -0.1 -> -1.0 so the cheek sinks ~0.9 mm into the bottom
# web (stock overlap was a 0.05 mm hair-weld).
L4_FIN = ((20.0, -1.0), (20.0, 10.0), (23.0, 22.0), (28.0, 32.0), (36.0, 37.8),
          (56.0, 37.8), (61.0, 34.0), (63.0, 30.0), (64.5, 26.0), (66.0, 24.0),
          (66.0, 20.0), (61.05, 7.5), (61.05, -1.0))
L4_TAILWALL = (65.72, 66.0, 7.5, 24.0)          # a0,a1,h0,h1 tail wall between cheeks
L4_RIBS = ((26.0, 42.0, 32.0, 37.8),            # shoulder rib a0,a1,h0,h1 (b -30.65..-12.7)
           (16.0, 32.0, 12.0, 17.8))            # mid rib    a0,a1,h0,h1

# ---------- w_link5: J5 horn plate + J6 ventral keel cage [D] ----------
L5_PLATE = (23.6, 37.6, -13.5, 13.5, 4.0)       # J5 horn plate a0,a1,b0,b1,r, h L5_TOP
L5_TOP = (-6.15, -2.15)                          # plate h (face -2.0, 0.15 under)
L5_CHEEK_B = (12.51, 14.91)
# keel cheek a-h outline; for a > 61.05 only h < -41.4 exists (clears the grip-plug
# roll tube r 24.2 about h -17 -> h -41.2..+7.2 at a 61.2+)
# R-fix: bottom edge -52.4 -> -54.0 sinks the cheek 1.6 mm into the keel web
# (stock: zero-volume tangent butt face at -52.4).
L5_CAGE = ((14.5, -26.0), (14.5, -47.0), (17.0, -54.0), (58.0, -54.0),
           (64.7, -44.0), (64.7, -41.4), (61.05, -41.4), (61.05, -10.0),
           (40.0, -5.0), (37.6, -2.15), (33.0, -2.15), (21.0, -15.5),
           (21.0, -24.0))                                           # D7: cheek top-front corner cut below the cradle/J4-case sweep footprint
L5_BOTTOM = -52.4                                # cage bottom (case -52.27 + clr)
L5_BACK = (14.5, 16.65, -52.4, -40.0)            # back-bottom wall a0,a1,h0,h1 (below plug)
L5_WIN = ((34.0, 10.0, -34.0, 20.0), (50.0, 8.0, -30.0, 16.0))   # windows a_c,a_hw,h_c,h_hw
L5_CLEATS = ((24.0, -20.0), (24.0, -34.0))       # cable cleats (a,h) on the -b cheek outer face

# ---------- w_grip_frame: J6 horn plate + grip keel cage + rack cage [D] ----------
GF_PLATE_A = (62.7, 69.0)                        # J6 horn plate (face 62.6; ends < plug band 65.8)
# plate outline (b,h): rect +-14.5 x -26.5..-8.5 clipped to r 15.0 about the
# roll axis (0,-17) so its rolled silhouette stays < h -2.0 (D7: clears the
# fin bottom web h -1.4..-0.05 by 0.6; r 16.2 -> -0.8 grazed the web)
GF_PLATE = ((12.36, -8.5), (14.5, -13.16), (14.5, -20.84), (11.61, -26.5),
            (-11.61, -26.5), (-14.5, -20.84), (-14.5, -13.16), (-12.36, -8.5))
GF_CB_A = 67.0                                   # horn screw counterbore from +a face
GF_CHEEK_B = (12.51, 14.91)
# R-fix: back edge raised/moved 68.8->67.0 and -26->-8.5 so the cheek overlaps
# the horn plate side bands (a 67..69 x h -26.5..-8.5 x b 12.51..14.5 -> real
# ~72 mm3/side weld; stock was a 0.3 mm3 knife-edge).  Bottom edge -52.4 ->
# -54.0 sinks the cheek into the keel web (stock: tangent butt face).
# R-fix also: front-top corner raised (115.5,-22)->(115.5,-12), (104,-14)->
# (104,-12) so the outline stays >=4 mm above the win2 top edge everywhere;
# stock dipped through the window band and pinched off a floating wedge
# sliver.  Rolled radius of the new corner about (0,-17) is ~16 mm - clears
# all w4/w5 statics (a <= 64.7).
GF_CAGE = ((67.0, -8.5), (67.0, -45.0), (73.4, -54.0), (104.0, -54.0),
           (115.5, -44.0), (115.5, -12.0), (104.0, -12.0), (80.0, -8.0),
           (73.4, -6.9))                         # grip keel cheek a-h outline
GF_BOTTOM = -52.4
GF_BACKWALL = (70.0, 73.5, -52.4, -40.0)         # back-bottom wall a0,a1,h0,h1 (under the plug; its roll tube clears fin+j5 only for a > 66)
# R-fix: stock win2 top edge (-14) pinched against the sloped cage outline at
# a~104, leaving a floating ~1.5 mm wedge sliver.  Lowered to give a >=2 mm
# continuous top ligament.
GF_WIN = ((86.0, 12.0, -32.0, 20.0), (104.0, 8.0, -31.0, 15.0))  # a_c,a_hw,h_c,h_hw
GF_CLEAT = (74.0, -14.91, -20.0)                 # cable cleat on the -b cheek (a,b,h)
GF_LIP_CH = 3.0                                  # 45 deg lip chamfer reach (mm)
GF_BRACKET_R = 8.0                               # rack bracket outside corner radius

# ---------- rack cage (B geometry shifted h -17, a +4.6) [S B / D shifts] ----------
H_SH = J6_AX_H            # -17.0 shift applied to every h of the B rack cage
# B: BR_A (109.2,111.1), BR_B 32, BR_HOLE 21.2, CH_H (19.4,22.4), CH_A1 119.5,
#    LIP (117.5,18.0), GEAR (18,111.1,117.1) - used with h += H_SH, a += A_SH.

# ---------- masses / torques ----------
M_STS3215 = B.M_STS3215          # 0.055
M_STS3250 = 0.0745               # [S cad3] J4 servo (STS3250-C001, 16 kg.cm rated)
STS3250_RATED = 1.569            # [S cad3] N.m
STS3215_RATED = B.STS3215_RATED  # 0.98 [U]
M_GEAR = B.M_GEAR; M_RACK = B.M_RACK
PAYLOAD6 = 0.5                   # [stage] kg at TCP
J2_CAP = 3.0; J3_CAP = 2.0       # [stage] N.m printed-disc caps
J4_RATED = STS3250_RATED
X_STRESS = 25.0                  # [U] PETG-CF cross-layer MPa

# ---------- ROM ----------
ROM_STEP = 5.0                   # finer than B's 10 (fin edge cases)
ROM_MIN = {"J4": 140.0, "J5": 140.0, "J6": 300.0}   # J6 "free" ~ +-150
