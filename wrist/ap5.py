"""wrist/ap5.py - D5 wrist+gripper redesign numbers (mm, deg).

ALL interface numbers come from cad/arm2b/ap2b.py (imported as B): joint axes,
servo placements (B.SERVOS), horn faces, bolt patterns, rack/gear/finger
geometry and TCP are IDENTICAL to A2b - kinematics and robot-os config are
untouched.  Only the four structural parts are redrawn as thin contoured
shells.  Tags: [S] sourced, [D] design choice, [U] unverified.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
import ap2 as P2          # noqa
import ap2b as B          # noqa  every interface number

# ---------- shared shell rules [D] ----------
WALL = 2.0                # shell wall on a servo pocket (was B.SV_WALL 2.5)
RR = 5.0                  # default outside corner radius on profiles
RHO_PETGCF = 1.31e-3      # g/mm^3 solid PETG-CF (PRINT_LIST)
INFILL_EFF = 0.6          # [U] printed/solid mass factor (ap2 convention)

# ---------- w_j4_cradle (J4 servo sleeve + bolt plate) [D] ----------
CR_OUT = (-37.3, 12.3, -14.5, 14.5, 6.0)      # sleeve outer a0,a1,h0,h1,r (case a -35.27..10.27 h +-12.51 + WALL)
CR_B = (-20.0, 13.0)                        # sleeve b range (mouth at -20; case void ends 11.35 -> 1.6 floor)
CR_PLATE_B = (28.5, 32.55)                  # bolt plate b range (same bolt line to fore_r)
CR_PLATE = (-34.0, 0.0, -14.0, 14.0, 5.0)   # bolt plate profile: covers the 4 bolt bosses only
CR_BOSS_D = 8.0; CR_BOSS_B = (12.9, 28.5)   # pillars sleeve->plate; pilots continue B.J4_BOLTS depth (>=24.55)
CR_SLOT = (-22.3, -10.7, 11.0, 25.5, 4.0, 16.0)   # cable slot a0,a1,b0,b1,h0,h1 (was h 0..16.86)
CR_GROOVE = (-36.0, -10.0, 14.0, 18.5, 13.6, 14.8)  # cable guide groove cut in the sleeve +h face (a0,a1,b0,b1,h0,h1)

# ---------- w_link4 (J4 horn -> J5 cage) [D] ----------
L4_PLATE = (-14.5, 14.5, -14.5, 14.5, 5.0)  # J4 horn plate profile (was disc R14), same b -30.65..-26.65
L4_PANEL = (23.0, 52.2, 15.2, 54.6, 5.0)    # J5 cage outer a-h profile; bottom face at B.J5_POCKET_H0 (0.59 over link5)
L4_RIB = ((2.0, -4.0), (10.0, -6.0), (18.0, 4.0), (22.0, 14.0), (24.0, 22.0),
          (24.0, 42.0), (17.0, 36.0), (12.0, 22.0), (8.0, 10.0), (0.0, 2.0))   # spine rib silhouette a-h (b -30.65..-26.65)
L4_TUBE_B = (-26.65, 31.0)                  # cage tube b range (mouth +b; case end 35.12, 4.1 exposed as before)
L4_BORE = (25.09, 50.11, 16.56, 52.56, 4.0) # case+clr bore (floor = 4 mm panel)
L4_WIN = ((22.0, 26.0, -14.0, 27.0, 24.0, 49.0),        # lightening window through each +-a wall:
          (49.0, 53.0, -14.0, 27.0, 24.0, 49.0))        #  a0,a1,b0,b1,h0,h1
L4_CLEATS = ((-20.0, 30.0), (-20.0, 44.0))  # cable cleats on the -a wall: (b,h) pairs

# ---------- w_link5 (J5 horn -> J6 cage) [D] ----------
L5_PLATE = (25.0, 50.0, -14.0, 14.0, 4.0)   # J5 horn plate a0,a1,b0,b1,r at h 10.61..14.61 (same)
L5_TUBE = (22.9, 60.6)                      # cage a range = B.L5_FRONT_A (stops 0.6 before the grip-servo plug sweep)
L5_PROF = (-14.51, 14.51, -37.27, 12.26, 5.5)  # cage outer b0,b1,h0,h1,r = case b +-12.51 h -35.27..10.26 + WALL
L5_BORE = (-12.51, 12.51, -35.27, 10.26, 4.0)  # case+clr bore from a 25.2 (floor ~2.3)
L5_BACK_H = 10.5                            # -a floor remnant height; plug slot above it
L5_PLUG = (12.0, 25.6, -10.0, 10.0, 10.5, 23.0)  # plug slot a0,a1,b0,b1,h0,h1 (plug a 12.9..25.55 h 10.85..22.15)
L5_WIN = (30.0, 57.0, -30.0, 4.0, 4.0)      # cheek window a0,a1,h0,h1,r through each +-b wall
L5_CLEATS = ((-6.0, 0.0), (6.0, 0.0))       # cable cleats on the -a face under the plug slot: (b,h) pairs

# ---------- w_grip_frame (J6 horn -> gripper cage) [D] ----------
GF_PLATE = (-14.5, 14.5, -10.5, 10.5, 4.0)  # J6 horn plate b0,b1,h0,h1,r at a 63.1..73.05 (same dims, rounded)
GF_CHEEK_B = (-14.51, -12.51, 12.51, 14.51) # cheek b ranges (2.0 walls on the case +-12.51)
GF_CHEEK = ((71.8, -6.0), (71.8, 11.5), (109.0, 11.5), (109.2, -37.0), (73.4, -37.0))  # a-h outline
GF_WEB = (72.0, 108.5, -13.5, 13.5, -37.27, -35.27)     # bottom web a0,a1,b0,b1,h0,h1
GF_WIN = (78.0, 102.0, -30.0, 0.0, 4.0)     # cheek window a0,a1,h0,h1,r
GF_BRACKET_R = 6.0                          # bracket plate corner radius (was square)
GF_LIP_CH = 1.4                             # 45 deg chamfer under the rack lips (kills their overhang)
GF_CLEAT = (74.0, -14.51, 8.0)              # cable cleat on the -b cheek (a,b,h)

# ---------- unchanged gripper + interfaces (all from B) ----------
# horn plates: B.L4_B, B.L5_TOP, B.GB_A, B.HORN_* ; bolts: B.J4_BOLTS, B.M3_PILOT
# rack cage: B.BR_A, B.BR_B, B.CH_H, B.CH_A1, B.LIP, B.BR_HOLE, B.GEAR
# servos: B.SERVOS via PB.pocket(key) ; stroke: B.STROKE ; TCP: B.A_TCP
