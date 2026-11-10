"""refine/ap9.py - R9 wrist architecture numbers (mm, deg).

Copy of ap7.py (R8 baseline) + the R9 "printed U-yoke" additions at the
bottom: a +b cheek plate on w_link4 that wraps the fin outer face and
reaches a journal boss on the J4 axis, plus a steel dowel pin cantilevered
from a cradle bracket on the +b flange.  The pin gives the rotor a second,
widely-spaced static support (horn at b~-29 <-> pin at b~+16) so the
rolled/lateral wrench couples across ~45 mm instead of bending the 5.45 mm
horn plate and the fin web.
Tags: [S] sourced, [D] design choice, [U] unverified.

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
CR_PLATE_B = (29.5, 32.55)                        # R5: mount flange -1.0 mm (mass trim; mount face unchanged)
CR_PLATE = (-34.0, 0.0, -14.0, 14.0, 5.0)
CR_BOSS_D = 8.0; CR_BOSS_B = (12.9, 29.5)          # bosses extended to the thinned flange
CR_SLOT = (-22.3, -10.7, 11.0, 25.5, 4.0, 16.0)          # J4 plug exit slot
CR_GROOVE = (-36.0, -10.0, 14.0, 18.5, 13.6, 14.8)       # cable guide groove

# ---------- w_link4: J4 horn plate + strut + dorsal fin (J5 case) [D] ----------
# L4_B set below next to the strut-band comment (R8 outboard thickening).
L4_PLATE = (-15.0, 15.0, -15.0, 15.0, 5.0)      # horn plate a-h profile
# R9: clip the two -a corners (dead rim mass outside the horn clamp disc
# and the strut weld); profile replaces the rounded box.
L4_PLATE_P = ((-15.0, -6.0), (-15.0, 6.0), (-6.0, 15.0), (15.0, 15.0),
              (15.0, -15.0), (-6.0, -15.0))
# R-fix: stock strut polygon self-intersects at TWO sections (trailing edge
# (14,0)->(5,-12) crosses the leading edge at a~8.8; the (24,10)->(30,22)
# segment also inverts vs the outer edge at a~21) -> the rib builds as
# disconnected fragments and the J4 horn plate is a detached island.
# Re-profiled as a clean 6-point tapered rib over the same envelope
# (a 5..40, h -13..38.2, b -30.65..-26.65): plate-side weld a 5..15,
# rib-box weld a 16+.
# R3: scrann/pilot FEA showed the strut is the ONLY horn->fin load path and
# its ~9 mm plate-edge weld is a re-entrant notch (in-layer VM ~80-105 MPa at
# cl 1.5-0.8, not converged -> notch indication, plus a CONVERGED 6.4 mm
# tail deflection at the 0.5 kg wrench -> J4-axis compliance ~5.5 deg).
# Widen the weld to h -11..+13 at the plate edge (exits sit in the plate
# corner radius) and widen the rib in b (L4_STRUT_B: -22.65 inner face keeps
# 2.65 mm clear of the cradle -b end at -20).
L4_STRUT = ((5.0, -13.0), (14.0, -13.0), (40.0, 38.2),
            (36.0, 38.2), (14.0, 12.0), (8.0, -8.0))   # rib silhouette a-h, b = L4_STRUT_B
L4_STRUT_B = (-32.1, -27.0)                         # R3: 8 mm rib (was plate 4 mm);
                                                    # R8: outer face follows the plate to -32.1
                                                    # R9: inner face -22.65 -> -26.6 - the pin
                                                    # carries the far-side share; face gains
                                                    # clearance to the case front (~0.8 mm)
# R8: the J4 horn mounts the plate's INBOARD face (J4_FACE_B=-26.6; the kp
# horn disc fills b -21.6..-26.6), so a boss there would collide with the
# horn.  The only free direction is outboard: the plate face -30.65 ->
# -32.1, leaving 0.5 mm to the fore_l inner face at -32.6.  The rim punch
# section grows 4.0 -> 5.45 mm.  Screws need +1.5 mm reach (M3x14).
L4_B = (-32.1, -26.65)                              # was (-30.65,-26.65)
L4_CHEEK_B = (12.51, 14.91)                     # fin cheeks +-b (case b +-12.36 + clr)
# R4: the R3 tailwall could only exist for a > 65.87 (the j5 case pocket cuts
# every |-b| < 12.51 feature up to a 65.87), so it built as a ~0.13 mm
# transverse membrane -> +15 MPa layer-NORMAL (b) tension at its top corner
# vs the 12.5 MPa allowable at the 0.5 kg wrench (T-notch, BC-insensitive).
# Replaced by an external tail COLLAR: side plates that overlap the cheek
# outer faces through their whole thickness (the pocket trims the inner
# intrusion back to 12.51) + a back plate that closes the tail and ties the
# cheek tail tips.  Lap/shear joint over ~50x the membrane weld area; no
# b-normal T-junction remains on the cheek inner faces.
L4_COLSIDE = ((59.0, 4.0), (59.0, 26.0), (61.0, 34.6), (62.2, 33.2),
              (64.9, 26.8), (66.6, 24.6), (66.6, 4.0))    # collar side a-h
L4_COLB = (12.3, 16.41)                                 # collar plate b band
L4_COLBACK = (66.0, 66.7, -16.41, 16.41, 4.0, 27.0)     # a0,a1,b0,b1,h0,h1
# fin a-h outline: full height a<=61.05; tail above h 7.5 only (clears the grip-plug
# roll tube: plug sweeps r 24.2 about h -17 -> reaches h +7.2 at a 61.2..66)
# R-fix: bottom edge -0.1 -> -1.0 so the cheek sinks ~0.9 mm into the bottom
# web (stock overlap was a 0.05 mm hair-weld).
L4_FIN = ((20.0, -1.0), (20.0, 10.0), (23.0, 22.0), (28.0, 32.0), (36.0, 37.8),
          (56.0, 37.8), (61.0, 34.0), (63.0, 30.0), (64.5, 26.0), (66.0, 24.0),
          (66.0, 20.0), (61.05, 7.5), (61.05, -1.0))
# R4: L4_TAILWALL deleted - replaced by the external tail collar above.
L4_RIBS = ((26.0, 42.0, 32.0, 37.8),)           # shoulder rib a0,a1,h0,h1 (b -30.65..-12.7)
# R4v3 mid rib: polygon with a tapered -a end reaching into the plate's
# interior (a~4-6 sits near the horn clamp centre, low free-edge stress);
# buries the strut (14,12) vertex and the old rib weld-end (~26,11).  The
# square -a end of the v2 box read ~12.4 MPa in-layer at cl0.8.
L4_RIBMID = ((4.0, 11.0), (10.0, 8.0), (31.0, 8.0),
             (31.0, 16.0), (10.0, 16.0), (4.0, 13.0))   # a-h polygon, b -30.65..-12.7

# ---------- w_link5: J5 horn plate + J6 ventral keel cage [D] ----------
# R4: the plate cheek weld was a ~1 mm T-junction (plate edge +-13.5 vs cheek
# band 12.51..14.91) with a sharp inside corner at (+-12.51, -6.15); the J6
# pocket wall sits flush at 12.51 -> no internal fillet possible.  Widened
# the plate to +-16.41 (full cheek width + a 1.5 mm ledge past each cheek),
# extended it a 37.6->41.5 so the cheek flat's end vertex is buried in plate
# material (R4 mesh run showed the exposed vertex was itself a ~+19-24 MPa
# a-tension notch), and ran the cheek top flat 0.85 below the plate top
# (weld ~11x2.4 mm per side, fully inside the plate band).  External
# longeron ribs on the cheek outer faces pick up the ledges and run 4 mm
# past the plate's +a edge: the weld line ends shed the cheek top-fibre
# a-tension gradually instead of at one corner.  Plate top (-2.15)
# unchanged -> the J5-yaw/fin-web gap stays 0.75.
L5_PLATE = (23.6, 41.5, -16.41, 16.41, 4.0)     # J5 horn plate a0,a1,b0,b1,r, h L5_TOP
L5_TOP = (-6.15, -2.15)                          # plate h (face -2.0, 0.15 under)
L5_CHEEK_B = (12.51, 14.91)
# R4: external longeron ribs under the plate ledges (outer face of each
# cheek); top edge penetrates into the plate band -> volumetric weld (no
# tangent contact, cf. F9c).  The rib bypasses the inside corner and caps
# the cheek edge where it exits the plate: load flows plate -> ledge ->
# rib -> cheek outer face over a 28..46 instead of one weld-end vertex.
L5_GUSSET = ((28.0, -3.0), (46.0, -3.0), (44.5, -9.0), (28.0, -13.0))
L5_GUS_B = (12.3, 16.41)                                  # gusset/longeron b band
# keel cheek a-h outline; for a > 61.05 only h < -41.4 exists (clears the grip-plug
# roll tube r 24.2 about h -17 -> h -41.2..+7.2 at a 61.2+)
# R-fix: bottom edge -52.4 -> -54.0 sinks the cheek 1.6 mm into the keel web
# (stock: zero-volume tangent butt face at -52.4).
# R4: top edge runs flat 0.85 under the plate top a 28..40 (was a 33..37.6 at
# -2.15; the exposed flat-end vertex was the R4-mesh hotspot) and the
# a 40..61.05 edge is raised ~2-5 mm -> the cheek top underlaps the widened
# plate for the full weld run and every polygon corner in the weld zone is
# buried.  a <= 61.05, h <= -2.15 -> clear of the fin (>=0.75 mm vertical)
# and the grip-plug roll tube (a > 61 unchanged).
L5_CAGE = ((14.5, -26.0), (14.5, -47.0), (17.0, -54.0), (58.0, -54.0),
           (64.7, -44.0), (64.7, -41.4), (61.05, -41.4), (61.05, -10.0),
           (40.0, -3.0), (28.0, -3.0), (21.0, -15.5),
           (21.0, -24.0))                                           # D7: cheek top-front corner cut below the cradle/J4-case sweep footprint
L5_BOTTOM = -52.4                                # cage bottom (case -52.27 + clr)
L5_BACK = (14.5, 16.65, -52.4, -40.0)            # back-bottom wall a0,a1,h0,h1 (below plug)
L5_WIN = ((34.0, 10.0, -34.0, 20.0), (50.0, 8.0, -30.0, 16.0))   # window openings a_c,a_hw,h_c,h_hw
# R6: lateral-mode fix - the open windows left only cantilever strips to
# carry +-b (lateral) bending about a, which reads as cross-layer sigma_hh
# +-33 MPa at the strip/window-top corners (R5 _lat bound).  Each opening
# now keeps a continuous outer-face SKIN (L5_SKIN thick) so the cheek
# works as a closed membrane/shear panel + the case side stays open to
# the pocket (case clearance at |b|=12.51 is untouched).  No cable notch:
# the J6 cable exits the open pocket mouth (a<17), not the windows.
L5_SKIN = 1.0                                    # closure skin thickness (outer face)
L5_SKIN_R = 3.0                                  # recess corner radius (smooths 2.4->skin step)
# R7v3: relief variant under screen - "r6" control / "r6f" r2.5 corner
# round / "flush" funnel flush with the cheek inner face.  R7v2 funnel
# (smooth taper 11.5->16.45) read WORSE than the R6 step on every scrann
# metric (-20.5/14.9/9.6 vs -6.4/9.4/5.3 @ (26.1,+-12.9,-6.2) plate-bottom
# edge) - the long free edge over the cheek inner face is the riser.
# R8: "loft" = swept-envelope relief.  The J4xJ5 swept phantom
# (cradle+j4case+fore plates, point-cloud 0.6 mm gate, checks/bake_loft.py)
# only grazes the TOP of the plate over much of the band - the box notch
# threw away keepable material.  LOFT keeps the full plate out to the
# true envelope plus a bottom lip where the intrusion is shallow.  The
# funnel section under the annulus grows ~10x vs the r6 notch.
L5_RELIEF = "loft"
# per-(a,|b|) keep-top h; None = keep full plate; -99 = full cut.
# a rows 23.6..28.4 step 0.4; |b| cols 9.5..16.4 step 0.3.  +-b symmetrized.
L5_LOFT = (
    (23.6, (None,)*8 + (-3.38, -4.63, -5.38) + (-99.0,)*13),
    (24.0, (None,)*9 + (-3.63, -4.88, -5.63) + (-99.0,)*12),
    (24.4, (None,)*9 + (-2.88, -4.13, -5.13, -5.88) + (-99.0,)*11),
    (24.8, (None,)*10 + (-3.38, -4.38, -5.38) + (-99.0,)*11),
    (25.2, (None,)*10 + (-2.38, -4.13, -4.88, -5.63) + (-99.0,)*10),
    (25.6, (None,)*11 + (-3.13, -4.38, -5.38, -6.13) + (-99.0,)*9),
    (26.0, (None,)*11 + (-2.38, -3.88, -5.13, -5.88) + (-99.0,)*9),
    (26.4, (None,)*12 + (-3.13, -4.38, -5.63) + (-99.0,)*9),
    (26.8, (None,)*12 + (-2.38, -4.13, -5.13, -5.88) + (-99.0,)*8),
    (27.2, (None,)*13 + (-3.38, -4.63, -5.63) + (-99.0,)*8),
    (27.6, (None,)*13 + (-3.13, -4.38, -5.38, -5.88) + (-99.0,)*7),
    (28.0, (None,)*13 + (-2.38, -3.63, -4.88, -5.88) + (-99.0,)*7),
    (28.4, (None,)*14 + (-3.38, -4.38, -5.63, -6.13) + (-99.0,)*6),
)
L5_CLEATS = ((24.0, -20.0), (24.0, -42.0))       # cable cleats (a,h) on the -b cheek outer face
                                                 # (R6: -34 -> -42, clears the window band)

# ---------- w_grip_frame: J6 horn plate + grip keel cage + rack cage [D] ----------
GF_PLATE_A = (62.7, 74.0)                        # J6 horn plate (face 62.6; ends < plug band 65.8)
                                                 # R7v2: rear reach 69->74 - past the g-pocket
                                                 # face (~66.4) the pocket cut keeps only the
                                                 # side tabs (|b|>12.66): longer cheek welds,
                                                 # less pressure at the (67,+-12.5,-25) notch.
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
# R7: outer-face brace rib on each cheek at the horn-plate longitude -
# T-flanges the 2.4 mm cheek wall across the (67,+-12.5,-25) notch band
# and the pocket-floor corner below it (same strategy as the l5 R6
# longerons: the inner face is case channel, so deepen outward).
# a>=67.5 keeps ~0.8 mm off the l4 tail collar back plate (ends a=66.7)
# under J6 roll; b band clears the pocket cut (|b|<=~12.8).  A forward
# cheek nose (a 62.7..67) was tried and REVERTED: rolled it grazes the
# j5 servo plug (a<=65.9, r~17 about J6) to ~0.1 mm.
GF_RIB = (67.5, 74.5, 14.91, 17.0, -51.4, -10.0)  # a0,a1,b_in,b_out,h0,h1
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
X_STRESS = 25.0                  # [U] PETG-CF in-layer allowable MPa (order/STRESS_SANITY.md: TDS 35 XY/29 Z -> design 25 in-layer / 12.5 cross-layer)

# ---------- ROM ----------
ROM_STEP = 5.0                   # finer than B's 10 (fin edge cases)
ROM_MIN = {"J4": 140.0, "J5": 140.0, "J6": 300.0}   # J6 "free" ~ +-150

# ===================== R9: printed U-yoke =====================
# +b cheek plate on w_link4: wraps the fin +b cheek outer face and reaches
# -a to a journal boss centred ON the J4 axis.  A steel dowel pin on the
# cradle (+b flange inner face) is the static anchor -> the rotor's
# J4-side loads gain a second support ~45 mm outboard of the horn.
#
# Swept-clearance budget that shaped the plate (probe: _probe_arm.py,
# J4xJ5 point-cloud sweep):
#   - plate inner face 13.5: 0.5 mm off the cradle sleeve outer face (b 13)
#   - journal boss torus r 9.5 at b 14.2..19.6 -> cradle -6 pilot bosses
#     relieved at b < 20.15 (pilot bores at b 24.55+ untouched)
#   - near-axis plate material at radius 11..24 keeps |angle| < ~55 deg
#     from +a so the J4 plug (a -22..-11, b 11..23.2) and the plug-slot
#     cable region stay clear over the +-80 deg J4 sweep
#   - plate bottom edge >= -6.4 outside the J5 swept disc r17.8 (J6 case
#     annulus r 17.8..33 at h <= -6.89); >= -1.6 inside it (l5 plate disc)
L4_ARM_B = (13.5, 16.3)                      # +b yoke plate band (2.8 mm)
L4_ARM = ((-6.0, -6.5), (10.0, -6.4), (14.0, -1.6), (34.0, -1.4),
          (34.0, 4.0), (28.0, 16.0), (18.0, 17.5), (14.0, 12.8),
          (11.0, 10.5), (8.0, 8.8), (0.0, 8.8), (-6.0, 6.5))  # diagonal arm
                                                                # + fin-root wedge
L4_ARM_WIN = ()                             # R9v2: window deleted - its
                                            # sharp re-entrant corners were
                                            # the FEA singularity (VM 105 MPa
                                            # corner vs ~2-6 MPa nominal arm
                                            # field).  Solid arm plate; mass
                                            # recovered via boss r7.5->7.0.
L4_BOSS_R = 7.0                               # journal boss outer radius
L4_BOSS_B = (14.7, 19.2)                      # journal band on the pin
L4_BOSS_BORE = 3.4                            # journal bore d (pin d3 + clr)
# dowel pin (steel, [S] standard hardware): slip fit + adhesive in the
# cradle bracket boss + flange bore, slip-journaled in the link4 boss.
# No axial retainer: the J4 horn fixes the rotor in b; the pin is trapped
# between the J4 case face and the flange bore.
PIN_D = 3.0; PIN_B = (14.4, 31.5)             # pin span in b (d3x18 dowel)
# cradle mods:
#   CR_RELIEVE: cut the -6 pilot bosses at b<20.15 (the rotating boss
#     sweeps a r7.0 torus there).  Pilot bores (24.55..33.55) unaffected;
#     the bolt stack keeps the sleeve<->flange tie.
#   CR_PINBOSS: pad stub on the axis welded into the +b flange (the pin
#     seats in pad + flange bores - no separate web needed).
CR_RELIEVE = (-12.5, 4.0, 12.85, 22.0, -15.0, 15.0)   # a0,a1,b0,b1,h0,h1
CR_PINBOSS = 8.5                            # pin seat pad dia at the axis
CR_PINBOSS_B = (25.5, 32.0)                 # pad stub welding into the flange
CR_PINBORE = 3.1                            # bore d (d3 dowel slip + glue)
