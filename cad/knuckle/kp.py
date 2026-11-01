"""cad/knuckle/kp.py - ALL knuckle-arm numbers (mm, deg). Copied verbatim
from ARM_KNUCKLE_V5.md section 3. Never change a number here without
changing the brief. Tags: [S] = SOURCED (see brief section 3 sources),
[D] = design choice derived from [S] numbers, [U] = UNVERIFIED.

G frame (world): origin = drum-recess floor centre on the case lid
(= case.py point (75, 88, 37.5)); +Z up; +X = case +X; +Y = case +Y
(case rear). Home pose: all joints 0, arm horizontal along +X."""

# ---------------- fits / print ----------------
WALL = 2.4; MIN_WALL = 1.6
CLR = 0.3          # rotating gap / loose fit
SLIP = 0.15        # servo pocket clearance per side
PRESS = 0.05       # press-fit plug is this much BIGGER in diameter
FACE_GAP = 0.8     # stationary rim -> rotating face, axial
M3_CLEAR = 3.4; M3_FIT = 3.3; M3_CB_D = 6.2; M3_CB_H = 3.2
M25_CLEAR = 2.9; M25_CB_D = 5.0; M25_CB_H = 2.6
M2_PILOT = 1.6; M2_CLEAR = 2.4
M4_CLEAR = 4.4; M4_CB_D = 8.4; M4_CB_H = 4.2
INS_M3_D = 4.6; INS_M3_L = 6.0     # M3 heat-set insert hole
MAG_D = 6.2; MAG_L = 3.2           # 6x3 disc magnet pocket

# ---------------- GIM modules, module frame ----------------
# module frame: origin = centre of the output face, +Z out of the output
# face, body toward -Z.  [S] STEP files + 2D PDFs in cad/vendor/.
G36_BODY_D = 55.0; G36_BACK_Z = -41.8; G36_CAP_D = 40.0; G36_CAP_Z = -47.81
G36_OUT_D = 37.0;  G36_OUT_Z0 = -0.8
G36_OUT_PCD = 27.0; G36_OUT_ANG = (2.0, 122.0, 242.0)   # 3x M3, 3.7 deep
G36_PIN_PCD = 24.0; G36_PIN_ANG = (62.0, 182.0, 302.0)  # d4 pins, top Z+2.30
G36_PIN_TOP = 2.30
G36_BACK_PCD = 48.0; G36_BACK_ANG = tuple(21.0 + 60.0 * k for k in range(6))  # M3, 4 deep
G10_BODY_D = 53.0; G10_OUT_D = 37.0; G10_OUT_Z0 = -1.0; G10_CAP_D = 40.0
G10_OUT_PCD = 27.0; G10_OUT_ANG = (29.0, 149.0, 269.0)  # 3x M3, 4 deep
G10_BACK_PCD = 47.5; G10_BACK_ANG = tuple(31.0 + 60.0 * k for k in range(6))  # M2.5, 3 deep
G4310_10_BACK_Z = -33.0; G4310_10_CAP_Z = -39.0
G4305_10_BACK_Z = -27.0; G4305_10_CAP_Z = -33.0
PLUG_KEEPOUT = 8.0     # [U] free space behind a GIM cap for its plugs

# ---------------- STS3215, servo frame = STEP file frame ----------------
# shaft = +Y axis through (x=0, z=0).  [S] measured from
# cad/arm/reference/sts3215_servo.step + Feetech STS3215 PDF p.6-7.
SV_X = (-35.12, 10.11); SV_Y = (-28.2, 7.5); SV_Z = (-12.36, 12.36)
SV_HORN_D = 19.2; SV_HORN_Y = (5.1, 9.6)        # horn face at y = +9.6
SV_HORN_PCD = 14.0                              # 4x M3 at 0/90/180/270 in XZ
SV_BACK_BUMP = (-20.5, -12.5, -31.7, -28.0, -8.7, 8.7)  # [S] x0,x1,y0,y1,z0,z1 relief
SV_PLUG = (-22.0, -11.0, -40.2, -28.0, -9.0, 9.0)       # [U] plug zone x0,x1,y0,y1,z0,z1

# ---------------- kinematics (G) ----------------
J2_Z = 150.0; L_UPPER = 150.0; L_FORE = 130.0
J2 = (0.0, 0.0, 150.0); J3 = (150.0, 0.0, 150.0); J4 = (280.0, 0.0, 150.0)
J5_ORIGIN = (359.0, 0.0, 150.0)      # J5 servo frame origin (roll axis = G X at y0,z150)
J6_ORIGIN = (388.61, 10.35, 162.0)   # J6 servo frame origin
J4_ORIGIN = (280.0, 11.35, 150.0)    # J4 servo frame origin
NOSE_X = 368.6                       # J5 horn face
TCP = (438.61, 0.0, 150.0)
L_TIP = 158.61                       # J4 axis -> TCP along X
J5_DX = 79.0                         # J4 axis -> J5 servo origin along X
J1_FACE_Z = 51.0; J2_FACE_Y = -25.0; J3_FACE_Y = -24.2
LIM = {"J1": (-170.0, 170.0), "J2": (-70.0, 35.0), "J3": (-135.0, 90.0),
       "J4": (-95.0, 95.0), "J5": (-160.0, 160.0), "J6": (-35.0, 0.0)}
# CAD sign: J2/J3/J4 rotate about +Y; positive = tip moves DOWN.

# ---------------- base drum (static) ----------------
POSTS = ((-35.0, 44.0), (35.0, 44.0), (0.0, 55.0))   # [S] case.py posts (40,132),(110,132),(75,143) - (75,88)
CABLE_ANG = 104.0     # [D] points at case.py rear channel, G (-17.5, 72)
SKIRT_D = 131.4; SKIRT_Z = (0.0, 10.0)
DRUM_OD = 96.0; DRUM_ID = 91.2; DRUM_Z = (0.0, 74.0)
FLOOR_Z = (0.0, 4.0); FLOOR_HOLE_D = 60.0
J1_BULK_Z = (18.6, 22.6); J1_BULK_HOLE_D = 41.0   # J1 body ends at Z 23.0 (measured in STEP mesh)
SHELF_Z = (61.0, 64.0); SHELF_ID = 70.0
BRG_ID, BRG_OD, BRG_W = 60.0, 78.0, 10.0   # [S] 6812 deep-groove bearing (ISO 15)
BRG_Z = (64.0, 74.0); SEAT_D = 77.95
CAP_Z = (74.0, 79.0); CAP_ID = 70.0; CAP_SCREW_R = 43.5
CAP_SCREW_ANG = (45.0, 135.0, 225.0, 315.0)

# ---------------- turret (rotates with J1) ----------------
HUB_Z = (51.0, 56.0); HUB_D = 59.9
SPIGOT_Z = (56.0, 74.3); SPIGOT_OD = 59.9; SPIGOT_ID = 50.0
SPIGOT_SLOT = (56.0, 61.0, 10.0)        # z0, z1, width; at CABLE_ANG
FLANGE_Z = (74.3, 80.0); FLANGE_D = 64.0
HAT_Z = (80.0, 87.0); HAT_D = 102.0; LIP_Z = (70.0, 80.0); LIP_ID = 97.0
COLUMN_D = 58.0; COLUMN_ID = 53.2; COLUMN_CY = 4.0; COLUMN_Z = (80.0, 150.0)
COLUMN_VOID_Z = (74.3, 118.0)
KN_D = 76.0; KN_Y = (-24.2, 33.0); KN_BORE_D = 55.6
KN_BULK_Y = (17.8, 21.8); KN_BULK_HOLE_D = 41.0   # J2 body ends at y 17.3 (measured in STEP mesh)
KN_CAV_Y = (21.8, 33.0)
KN_ENDCAP = (31.0, 33.0, 35.6)        # spigot ring y31..33, disc y33..35.6
TUNNEL_D = 5.0; TUNNEL_X = -32.0      # along Y at (x=-32, z=150)
RISER = (0.0, 26.0, 10.0, 110.0, 126.0)   # x, y, d, z0, z1 (column void -> cavity)

# ---------------- upper arm (rotates with J2) ----------------
UA_R0 = 38.0; UA_R1 = 33.0; UA_Y = (-25.0, -74.8); UA_COVER_Y = (-74.8, -79.8)
UA_HUB_Y = (-25.0, -32.0); UA_GROOVE = (29.5, 34.5, 4.5)   # r0, r1, depth
J3_BORE_D = 53.6; J3_SLEEVE_OD = 56.8; J3_BULK_Y = (-57.2, -61.2)
J3_NOTCH = (28.6, 31.4, 5.0)        # r0, r1, width; at module angle 180 (G x=120)
UA_PILLARS = ((25.0, 175.0), (25.0, 125.0), (110.0, 175.0), (110.0, 125.0))
UA_PILLAR_D = 10.0

# ---------------- forearm (rotates with J3) ----------------
FA_CAP_D = 66.0; FA_Y = (-24.2, 29.8); FA_HUB_Y = (-24.2, -17.2)
FA_GROOVE = (27.0, 31.0, 4.0)
FA_TUBE_D = 54.0; FA_TUBE_ID = 49.2; FA_TUBE_CY = 2.8; FA_END_X = 298.6
FA_ENDCAP_X = (298.6, 301.0); FA_ELBOW_CAP_D = 50.0
FA_FILLER_X = (242.18, 298.6)
J4_HOLE_D = 34.0
BLISTER_OUT = (255.6, 271.4, -31.25, -17.0, 130.0, 161.4)
BLISTER_IN = (258.0, 269.0, -28.85, -12.0, 134.0, 159.0)
PASS = (255.0, 285.0, -13.0, 21.3, 134.0, 137.49)
CHANNEL = (240.0, 285.0, 17.3, 21.3, 134.0, 139.5)

# ---------------- wrist head (rotates with J4) ----------------
CUP_D = 50.0; CUP_Y = (30.6, 38.6); BOSS_D = 28.0; BOSS_Y = (20.95, 30.6)
CUP_GROOVE = (15.5, 22.0, 4.0); CUP_CAP = (40.0, 2.0)
SEG_A = (280.0, 340.0, 30.6, 38.6, 140.0, 160.0)
SEG_B = (316.4, 340.0, 12.0, 38.6, 140.0, 162.66)
P1 = (296.0, 330.0, 32.6, 36.6, 146.0, 154.0)
P2 = (322.0, 330.0, 14.5, 36.6, 146.0, 154.0)
POD = (316.4, 366.65, -16.11, 20.11, 111.13, 163.86)   # 3.6 walls
POD_POCKET = (330.65, 366.65, -12.51, 12.51, 114.73, 160.26)
POD_PLUG = (318.8, 330.65, -9.0, 12.6, 128.0, 139.0)   # merges into POD_CHANNEL
POD_CHANNEL = (318.8, 366.65, 12.51, 16.51, 114.73, 160.26)
POD_FRONT = (366.65, 368.3)
POD_M2 = ((-6.0, 112.93), (10.0, 112.93), (-6.0, 162.06), (10.0, 162.06))

# ---------------- gripper (rotates with J5) ----------------
GR = (368.6, 404.72, -18.0, 19.65, 124.33, 174.66)      # body; open at y=-18
GR_BACK_X = (368.6, 376.1)                              # back wall, 7.5 thick
GR_POCKET = (376.1, 401.12, -18.5, 18.0, 126.73, 172.26)
GR_SLOT = (373.6, 376.1, -18.5, -12.0, 140.0, 151.0)    # wire slot in back wall
GR_HOLE = (-14.0, 145.5, 4.0)                           # y, z, d: groove -> slot, along X
GR_GROOVE = (12.0, 16.0, 2.5)                           # r0, r1, depth on back face
GR_PLUG = (373.6, 397.61, -29.85, -18.0, 140.0, 151.0)  # cut in lid bump
GR_BUMP = (371.2, 400.01, -32.25, -18.0, 138.0, 153.0)  # added to lid
GR_LID = (368.6, 404.72, -20.4, -18.0, 124.33, 174.66)
GR_PILOTS = ((372.35, 135.0), (402.92, 135.0), (372.35, 165.0), (402.92, 165.0))
FINGER_FIX = (404.72, 448.61, -10.0, 10.0, 141.75, 149.75)
FINGER_MOV = (428.61, 448.61, -10.0, 19.95, 150.25, 158.25)
JAW_Y = (19.95, 26.95); JAW_HUB_D = 26.0; JAW_CAP_D = 21.0

# ---------------- masses (g) [S] vendor tables ----------------
M_4305_10 = 150.0; M_4310_10 = 227.0; M_4310_36 = 310.0; M_STS3215 = 55.0
PAYLOAD_G = 200.0      # [D]
RATED_NM = {"J1": 1.0, "J2": 7.38, "J3": 2.05}   # [S]
PEAK_NM = {"J1": 3.47, "J2": 20.16, "J3": 5.6}   # [S]
STS_STALL_NM = 2.94    # [U] 30 kg.cm at 12 V (seller listings)

# horn centre screw head [S] measured from the servo STEP: d5.7, top at y=+11.25
SV_SCREW_D = 5.7; SV_SCREW_TOP = 11.25
HORN_RECESS = (7.0, 2.2)    # d, depth: cut in EVERY face that touches a horn

J2_RING = (28.6, 2.8)   # d, depth: recess in upper-arm hub for the J2 output ring
                        # (ring d20..d28 protrudes 2.5 past y=-25, measured in STEP mesh) [U vs 2D pdf]
UA_EXIT_D = 4.5         # groove exit hole (4.5 so it does not touch the groove walls)
