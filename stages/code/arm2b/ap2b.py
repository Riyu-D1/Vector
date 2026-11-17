"""cad/arm2b/ap2b.py - ALL A2b numbers (mm, deg): wrist J4-J6 (3x Feetech STS3215) + gripper (4th STS3215).
Wrist frame W (used for every A2b part): origin on the J4 axis, a = tool direction, b = world Y, h = 'up' in the
home (L) pose.  In the reBot rest frame: X = J4_X - a, Y = b, Z = J4_Z - h (a 180 deg turn about Y), so after
build_arm2b.py poses the arm, W is the world frame moved to J4.  Tags: [S] sourced, [D] design choice checked by
arm2b_checks.py or gate.py, [U] unverified - never "fix" a [U] value, write it in STATUS."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "arm2"))
import ap2 as P2                    # A2a numbers (and ap2.A = actuator interface)

# ---------- chain along the tool axis [S brief / D] ----------
J4_J5 = 37.6                        # [S] 0.48 x reBot 78.3: J5 axis (along h) at a = 37.6
J5_J6 = 19.2                        # [S] 0.48 x 40: J6 frame on the tool axis at a = 56.8
J6_TCP = 75.0                       # [S] tool: TCP (finger tips) at a = 131.8
A_J5 = J4_J5; A_J6 = J4_J5 + J5_J6; A_TCP = A_J6 + J6_TCP      # 37.6, 56.8, 131.8
REACH_TOL = 0.1                     # [D] measured spans must match these within 0.1

# ---------- STS3215 case, kp.py servo frame [S kp / ap2 SV_*]: lx long axis (horn at 0), ly output axis, lz width ----------
SV_X = P2.SV_X; SV_Y = P2.SV_Y; SV_Z = P2.SV_Z                  # (-35.12, 10.11), (-28.2, 7.5), 12.36
SV_HORN_D = P2.SV_HORN_D; SV_HORN_Y = P2.SV_HORN_Y; SV_HORN_PCD = P2.SV_HORN_PCD   # 19.2, (5.1, 9.6), 14.0
SV_PLUG_X = P2.SV_PLUG_X; SV_PLUG_Y = P2.SV_PLUG_Y; SV_PLUG_Z = P2.SV_PLUG_Z       # cable plug behind the case
SV_CLR = 0.15                       # [D] pocket clearance per side
SV_WALL = 2.5                       # [D] printed pocket wall
HORN_HOLE = 3.4; HORN_CB = (6.2, 2.0); HORN_RECESS = (7.0, 2.2)   # [D] 4x M3 ISO 7380 into the horn [U horn thread], horn centre screw recess [S kp]
HORN_ANG = (45.0, 135.0, 225.0, 315.0)          # [D] horn hole pattern turned 45 deg (horn spline position is free)

# ---------- servo placement in W: (horn centre, ly axis dir, lx dir) [D] ----------
# J4: horn face on the -b side, case runs back into the forearm.  J5: on top, horn down, case runs to +b.
# J6: under J5 (inside link5), horn forward.  G (gripper): horn forward on the tool axis.
J4_FACE_B = -26.6                   # [D] J4 horn face; link4 plate b -30.65..-26.65 (2.05 to fore_l)
J5_FACE_H = 14.61                   # [D] J5 horn face = link5 top; J6 case top 10.11 + 0.5 gap + 4.0 plate
A6_FACE = 63.0                      # [D] J6 horn face (J6 plug must stay >= 16.5 from the J4 axis)
AG_FACE = 111.0                     # [D] gripper servo horn face; its plug starts at a 61.2 (in front of the J6 case at 60.9)
SERVOS = {  # name: (horn centre (a,b,h), ly dir, lx dir, horn-face offset along ly from the centre)
    "j4": ((0.0, J4_FACE_B + SV_HORN_Y[1], 0.0), (0, -1, 0), (1, 0, 0)),
    "j5": ((A_J5, 0.0, J5_FACE_H + SV_HORN_Y[1]), (0, 0, -1), (0, -1, 0)),
    "j6": ((A6_FACE - SV_HORN_Y[1], 0.0, 0.0), (1, 0, 0), (0, 0, 1)),
    "g":  ((AG_FACE - SV_HORN_Y[1], 0.0, 0.0), (1, 0, 0), (0, 0, 1)),
}
M_STS3215 = 0.055                   # [S rebot_torque soma] kg
STS3215_RATED = 0.98                # [U] N.m rated (12 V); stall 2.94 [S Feetech C018 30 kg.cm]
TORQUE_SF = 1.4                     # [S brief] J4 torque <= rated / 1.4

# ---------- forearm J4 ends (A2a fore_l / fore_r re-cut) [D] ----------
FORE_PLUG_D = 38.4                  # plug the reBot DM4310 d38 pilot
J4_CRADLE_B = (-20.0, 32.55)        # J4 cradle: b range (0.05 to fore_r at 32.6)
J4_CRADLE_A0 = -38.0                # cradle back end (case back -35.12 - clr - wall)
J4_BOLTS = ((-6.0, 9.0), (-6.0, -9.0), (-28.0, 9.0), (-28.0, -9.0))   # (a, h) 4x M3x10 ISO 7380: fore_r -> cradle pilots
M3_CLR = 3.4; M3_PILOT = 2.5        # [D] clearance in the plate, thread-forming pilot in the cradle [U grip]

# ---------- link4 (J4 horn -> J5 case) [D] ----------
L4_B = (-30.65, -26.65)             # 4.0 plate on the J4 horn
L4_R = 14.0                         # plate end radius round J4
L4_STRUT = (0.0, 23.0, 0.0, 30.0)   # a0, a1, h0, h1: plate strut from the J4 end, 0.41 into the J5 block (a 22.59)
J5_POCKET_H0 = 15.2                 # J5 pocket walls stop 0.59 above link5 (h 14.61); pocket bottom open (case face h 16.71)
L4_WIN = (-24.5, -14.0, 20.0, 48.0) # b0, b1, h0, h1 lightening window through the J5 block (along a)
J5_OPEN_B = 30.0                    # J5 pocket walls stop at b 30.0 (case end b 35.12 stays exposed: clears fore_r)

# ---------- link5 (J5 horn -> J6 case) [D] ----------
L5_TOP = (10.61, 14.61)             # top plate h
L5_CHEEK_H0 = -20.0                 # side cheeks (b +-12.51..15.01) down to h -20
L5_BACK_H0 = -10.5                  # back wall h -10.5..14.61 (J6 plug below at h -22..-11)
L5_FRONT_A = 60.6                   # cheeks and plate end 0.3 behind the J6 case front (60.9)

# ---------- gripper (reBot rack-and-pinion concept, STS3215 drive) [D] ----------
GB_A = (63.1, 73.05)                # grip_frame back plate on the J6 horn (gripper servo back face 73.2 - 0.15)
GB_H = 10.5                         # back plate h +-10.5 (gripper plug below at h -22..-11)
GB_CB_A = 66.1                      # horn screw counterbores from the front face down to a 66.1 (3.0 clamp)
GW_H = (-30.0, 10.26)               # side walls b +-12.51..15.01, back plate -> bracket
BR_A = (109.2, 111.1); BR_B = 32.0; BR_HOLE = 21.2     # rail bracket plate (reBot 01_Rail_Bracket idea), hole round the horn boss
CH_H = (19.4, 22.4); CH_A1 = 119.5; LIP = (117.5, 18.0)   # rack channels (top, mirrored bottom), front lips a 117.5..119.5 down to h 18.0
GEAR = (18.0, 111.1, 117.1)         # [S rebot GEAR-1M16C] m1 16T on the horn: OD, a0, a1 (proxy = OD cylinder); 4x M3 csk through its hub [U]
RACK_X_REF = -60.4                  # reBot rest X -> a = RACK_X_REF - X puts the 02_Rack cut at a 111.3..117.3
RACK_AXIS_Z = 195.0                 # [S] reBot gear axis Z in the rest assembly
RACK_U_B = (-31.0, 5.0); RACK_D_B = (-5.0, 31.0)   # [D] 36 mm cuts of the reBot 02_Rack (m1, 6 x 12), closed position
FINGER_T = 4.0; FINGER_GAP = 1.0    # finger plate thickness; inner faces at b +-1.0 when closed (home)
FINGER_A = (119.7, A_TCP); FINGER_H = 12.6          # finger plate a range (tips = TCP), h +-12.6
TAB_A0 = 117.4; TAB_H = (7.4, 12.6) # finger tab back to the rack front face (117.3), under the lip
STROKE = 25.0                       # [D] full opening (12.5 per finger = 90 deg of the 16T pinion)

# ---------- masses / torque (rebot_torque soma model, measured printed masses) ----------
M_GEAR = 0.008; M_RACK = 0.012      # [U] steel m1 16T gear, 36 mm m1 rack
PAYLOAD = P2.PAYLOAD                # 0.25 kg at the TCP

# ---------- ROM sweeps from the home pose [D] ----------
ROM_STEP = 10.0
ROM_MIN = {"J4": 140.0, "J5": 140.0, "J6": 360.0}   # [D] set from the measured sweep (A2b): J4 and J5 stop at +-80 (servo cases / bracket on the forearm)
