"""cad/arm2/ap2.py - ALL A2a numbers (mm, deg). World frame = reBot assembly
reBot_B601_DM_v1.1_20260425.step (Seeed, CERN-OHL-W-2.0, commit 13bebbf), Z up,
base on Z=0, as placed in its folded rest pose.  rebot_src/*.step are reBot parts
re-exported unchanged in that frame.  Tags: [S] sourced, [D] design choice checked
by arm2_checks.py or gate.py, [U] unverified - never "fix" a [U] value, write it in STATUS."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "act2"))
import ap as A                      # printed actuator interface (branch arm-actuator2c, tag act-1c-done)

REBOT_COMMIT = "13bebbf"
# ---------- reBot joint axes (all along world Y) [S measured from the STEP] ----------
J2_XZ = (-20.0, 143.5)
J3_XZ_REBOT = (244.0, 143.5)
J4_XZ_REBOT = (1.4, 197.5)
UP_SPAN_REBOT = 264.0; FORE_SPAN_REBOT = 242.6      # [S rebot URDF]
# ---------- A2 scale: joint ends full size, spans shortened [D] ----------
UP_SPAN = 126.7; FORE_SPAN = 116.4                  # [D] 0.48 x reBot
DX_UP = UP_SPAN - UP_SPAN_REBOT                     # -137.3: everything at J3 moves by this in X
DX_FORE = DX_UP + (FORE_SPAN_REBOT - FORE_SPAN)     # -11.1: forearm J4 end moves by this in X
J3_XZ = (J2_XZ[0] + UP_SPAN, J2_XZ[1])              # (106.7, 143.5)
J4_XZ = (J4_XZ_REBOT[0] + DX_FORE, J4_XZ_REBOT[1])  # (-9.7, 197.5)
J4_OFFSET = J4_XZ_REBOT[1] - J3_XZ_REBOT[1]         # 54.0 [S] dogleg offset, kept
REACH_TARGET = 375.0; REACH_TOL = 10.0              # [D] 0.48 x 780
J4_TCP_A2B = 131.9                                  # [D] A2b must supply J4 -> TCP (0.48 x (78.3+40+155.4) ~ 131.4, rounded to hit 375)

# ---------- actuator placement (J2, J3) [D] ----------
# module +Z -> world -Y, module +X -> world +X, module +Y -> world +Z (module angle a = world XZ angle a from +X toward +Z)
ACT_OUT_Y = -31.6                                   # [S] reBot DM4340P output face (front spacer back face)
ACT_BACK_Y = ACT_OUT_Y + A.L_TOTAL                  # 23.4
ACT_HOUSING_END_Y = ACT_BACK_Y - A.Z_FRONT_RING[1]  # -31.0 housing front edge

# ---------- side plates ----------
PLATE_T = 4.0                                       # [D] printed PETG
UP_R = 30.5                                         # [D] upper plate end radius: ring 57.15 + 1.9 wall
RING_D = 57.15                                      # [D] output-side plate grips the housing OD 57.0 [U slip + CA]
UP_OUT_Y = (-32.1, -28.1)                           # [D] output-side upper plate, 4.0; 0.5 gap to the forearm plate (reBot gap 0.3)
UP_COLLAR_Y = (-28.1, -25.1)                        # [D] ring collar inboard of the plate, both ends
UP_BACK_Y = (28.1, 32.1)                            # [D] back upper plate, 4.0
UP_BACK_HOLE = 38.0                                 # [S rebot Link2 end hole]
WIN_R = 12.0; WIN_INSET = 45.0                      # [D] lightening slot: R12, centres 45 in from each joint
M3_CLR = 3.4; CSK_D = 6.4                           # [D] ISO 10642 M3x10 countersunk, 90 deg: grip 8.7, 1.3 into the 3.2 pilots [U] (M3x12 = 3.3, bottoms out)
BACK_SP_Y = (ACT_BACK_Y, UP_BACK_Y[0])              # (23.4, 28.1) [D] new back spacer, 4.7
BACK_SP_D = 57.0; SEAT_6803 = 26.05; LIP_D = 22.0   # [S rebot back spacer seat 26 / lip 22]
BRG_6803 = (17.0, 26.0, 5.0); BRG_6803_Y = (25.3, 30.3)   # [S] reBot position, kept
FRONT_SP_M3 = 3.2; FRONT_SP_DOWEL = A.OUT_DOWEL_FLANGE_HOLE  # [D] re-drilled reBot front spacer
PLUG_D = 4.6                                        # [D] plug every old spacer hole before re-drilling
FORE_L_Y = (-36.6, -32.6); FORE_R_Y = (32.6, 36.6)  # [D] forearm plates, flat 4.0, 0.5 outboard of the upper plates
DOGLEG_DY = {"L": -1.0, "R": 2.0}                   # [D] reBot doglegs moved out onto the forearm plates (reBot R dogleg overlapped its FLANGE by 1.0)
J3_FRONT_SP_EXTRA = 1.0                             # [D] J3 front spacer 4 -> 5 (reBot spacer unioned with itself moved -1.0 Y)
J3_FLANGE_EXTRA = 1.0                               # [D] J3 FLANGE disc +1.0 toward +Y (unioned with itself moved +1.0 Y)
FLANGE_BORE = 8.0                                   # [D] reBot FLANGE d14 bore plugged and re-drilled d8 (printed: d17 spigot wall 1.5 < 1.6)
FORE_SEC_J3 = {"L": -34.1, "R": 33.1}               # [S] Y of the reBot Link3 J3-end sheet section
FORE_SEC_J4 = {"L": -26.1, "R": 25.1}               # [S] Y of the reBot Link3 J4-end sheet section
FORE_J3_XMIN = 150.0; FORE_J4_XMAX = 100.0          # [D] picks the J3 piece (X > 150) / J4 piece (X < 100) of each section
FORE_BAND_Z = (185.0, 217.0)                        # [S] reBot Link3 neck, 32 tall
FORE_BRIDGE_X = (40.0, 56.0)                        # [D] (after the shift) joins J4 piece (ends 46.0) and J3 piece (starts 50.0)

# ---------- J1: STS3250 in the base [D] ----------
# servo frame (kp.py, STS3215 case, STS3250 assumed identical [U]): output axis = servo +Y, horn face y = +9.6
SV_X = (-35.12, 10.11); SV_Y = (-28.2, 7.5); SV_Z = 12.36
SV_HORN_D = 19.2; SV_HORN_Y = (5.1, 9.6); SV_HORN_PCD = 14.0
SV_PLUG_X = (-22.0, -11.0); SV_PLUG_Y = (-40.2, -28.0); SV_PLUG_Z = 9.0
HORN_RECESS = (7.0, 2.2)                            # [S kp]
J1_HORN_Z = 80.8                                    # [S] reBot yaw-limit bottom face = old DM4340 output face
J1_YAW = 0.0                                        # [D] servo long axis along world X (tested 0 / 90: see STATUS)
SV_CLR = 0.15                                       # [D] pocket clearance per side
CRADLE_D = 57.5; CRADLE_Z0 = 24.2                   # [D] fills the reBot DM4340 pocket (d57.8, motor Z 24.2..80.8); minus 01_BASE_Link itself
CABLE_D = 10.0                                      # [D] cable hole under the plug relief, through the cradle floor
YAW_HORN_HOLE = 3.2; YAW_CB = (6.2, 2.0)            # [D] 4x M3x8 ISO 7380 from the top into the horn [U horn thread]
M_STS3250 = 0.055                                   # [U] same case as STS3215

# ---------- home pose (L pose) [D] ----------
POSE_J2 = -90.0     # deg about +Y through J2: upper arm from +X (reBot rest) to +Z (vertical)
POSE_J3 = -90.0     # deg about +Y through J3: forearm from folded to forward (+X)
ROM_STEP = 10.0; ROM_MIN = {"J2": 150.0, "J3": 150.0}   # [D] free sweep needed around home, total deg

# ---------- torque sanity (rebot_torque.py soma model, A2 masses) ----------
RHO_PETG = 1.27e-3                                  # g/mm^3, solid
INFILL_EFF = 0.6                                    # [U] printed mass / solid mass
M_ACT = 0.300                                       # [U] printed actuator: printed ~0.11 + motor 0.085 + bearings/pins ~0.10
M_WRIST = 3 * 0.055 + 0.020                         # [S rebot_torque soma] 3x STS3215 + wrist bracket
M_GRIP = 0.110; PAYLOAD = 0.25                      # [S rebot_torque soma]
J2_LIMIT = 3.5; J3_LIMIT = 2.25                     # [S study] actuator continuous limits
J2_REF = 2.23; J3_REF = 1.15                        # [S rebot_torque soma at 0.48]
TORQUE_MAX = {"J2": 2.5, "J3": 1.5}                 # [D] sanity: >= 1.4x margin to the limits
