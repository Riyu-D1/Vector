"""cad/act2/ap.py - ALL printed-actuator numbers (mm). Copied verbatim from
~/Vector/stages/code/act2/ap.py.  Tags: [S] sourced (study / standard part),
[D] design choice checked by cyc.py or gate.py, [U] unverified - never "fix"
a [U] value, write it in STATUS.
Module frame: origin = centre of the BACK face, +Z toward the output,
output face at Z = L_TOTAL.  Home pose: crank angle 0 (disc 1 centre at +X)."""

RATIO = 40                      # [D] 40 or 50 - the ONLY switch for the fallback
GEAR = {                        # N lobes, NP = N + 1 ring pins, R pin circle radius, RP pin radius, E eccentricity
    40: dict(N=40, R=23.5, RP=1.5, E=0.42),   # [D] K1 0.733, rho_min 1.931 > 1.65, pins 3x10 ISO 8734
    50: dict(N=50, R=23.5, RP=1.25, E=0.30),  # [D] K1 0.651, rho_min 1.748 > 1.40, pins 2.5x10 ISO 8734
}
CLR_TOOTH = 0.15                # [D] disc profile offset beyond the pin radius
DISC_M = 1440                   # [D] points used for the disc outline in CAD

# ---------- envelope / interface (reBot joint end) ----------
OD = 57.0                       # [S rebot-adapt2] R28.5 joint end
L_TOTAL = 55.0                  # [D] back face -> output face, gate limit 55.0
LINK_PCD = 50.0; LINK_N = 6; LINK_ANG0 = 0.0     # [S rebot] 6x M3 back pattern
LINK_PILOT_D = 2.5; LINK_PILOT_L = 3.2           # [D] M3 thread-forming pilot (PETG) [U grip]
OUT_M3_PCD = 27.0; OUT_M3_ANG = (0.0, 120.0, 240.0)      # [S rebot/GIM-36 PCD27, angles D]
OUT_DOWEL_PCD = 24.0; OUT_DOWEL_ANG = (60.0, 180.0, 300.0)  # [S rebot/GIM-36 PCD24, angles D]
OUT_DOWEL_D = 4.0; OUT_DOWEL_HOLE = 4.05; OUT_DOWEL_FLANGE_HOLE = 4.1
OUT_DOWEL_DEPTH = 3.1; OUT_DOWEL_PROUD = 2.3     # [S kp G36_PIN_TOP 2.30]

# ---------- motor: Tarot TL2955 4008 330KV outrunner ----------
MOT_D = 44.5; MOT_H = 22.0; MOT_MASS_G = 85     # [S study] (check with calipers: Q1)
MOT_KV = 330; MOT_R_OHM = 0.145                 # [S study / U xcopterCalc]
SHAFT_D = 4.0                                    # [S study] not hollow
SHAFT_OUT = 12.0                                 # [U] shaft length beyond the stator base face (Q2)
MOT_PCD = 25.0; MOT_SCREW_ANG = (45.0, 135.0, 225.0, 315.0)  # [U] stator base 4x M3 (Q3)
STATOR_HOLE_D = 12.0                             # [U] clearance for the stator bearing boss (Q3)
BELL_CLR = 0.45                                  # [D] bell radius 22.25 -> bore radius 22.7

# ---------- Z stack (module frame) ----------
Z_BACK = (0.0, 3.6)             # [D] housing back wall
Z_ENC_POCKET = (0.0, 1.8)       # [D] AS5600 board pocket, open to the back face (gate fallback: was 2.0, floor 1.6 -> 1.8)
Z_MAG = (5.0, 7.5)              # [D] 6x2.5 diametric magnet glued on bell top centre
Z_MOTOR = (7.5, 29.5)           # [D] bell top -> stator base face (MOT_H 22)
Z_MID = (29.5, 33.5)            # [D] mid_plate (stator mount)
Z_DISC1 = (33.8, 37.8)          # [D] 4.0 thick, on 6702 #1
Z_DISC2 = (38.1, 42.1)          # [D] 4.0 thick, on 6702 #2
Z_RINGPIN = (33.5, 43.5)        # [D] ring pins (10 long) sit on mid_plate front face
Z_HUB = (33.8, 47.2)            # [D] cam1 33.8-37.95, cam2 37.95-42.25, stub 42.25-47.2
Z_CAM_SPLIT = 37.95; Z_STUB0 = 42.25
Z_CARRIER_PLATE = (42.4, 45.4)  # [D]
Z_PIN_RING = (43.5, 45.4)       # [D] spacer: ring pins -> 6808 outer race
Z_6808 = (45.4, 52.4)           # [S 6808 width 7]
Z_SPIGOT = (45.4, 52.4)         # [D] carrier spigot inside the 6808
Z_FRONT_RING = (52.4, 54.4)     # [D] retains 6808 outer race; housing ends at 54.4
Z_FLANGE = (52.4, 55.0)         # [D] out_flange, proud of housing by 0.6
Z_OUTPIN = (34.0, 46.0)         # [D] output pins 3x12, pressed 3.6 deep into carrier
Z_685 = (42.4, 47.4)            # [S 685 width 5]

# ---------- housing bores ----------
BORE_MOTOR = 45.4               # [D] Z_BACK[1] .. Z_MID[0]
BORE_PIN = 47.0                 # [D] = 2*R: ring pins half buried; Z_MID[0] .. Z_RINGPIN[1]
PIN_HOLE_D = 3.05               # [D] ring pin holes (3.0 pins) at radius R (50:1: 2.55)
SEAT_6808 = 52.1                # [D] 6808 OD 52 + 0.1 (PETG prints holes small)
WIRE_ANG = 90.0; WIRE_W = 4.0; WIRE_R = (22.5, 25.2)   # [D] axial phase-wire channel
NOTCH_W = 5.0; NOTCH_Z = (0.0, 8.0)                    # [D] side notch where wires leave
ENC_GROOVE_W = 3.0; ENC_GROOVE_D = 1.2                 # [D] back-face groove pocket -> notch
CSK_Z = 31.5; CSK_ANG = (30.0, 150.0, 270.0)           # [D] 3x radial M3 countersunk into mid_plate
CSK_D = 6.0; CSK_HOLE = 3.4; CSK_PILOT = 2.5; CSK_PILOT_L = 6.0  # [S ISO 10642 M3 head 6.0]

# ---------- mid_plate ----------
MID_D = 46.8                    # [D] slides through BORE_PIN, sits on the 45.4/47.0 step
MID_CB_D = 6.2; MID_CB_H = 1.9  # [S ISO 7380 M3 head 5.7 x 1.65] from the front face
MID_GROOVE = (4.0, 1.5)         # [D] wire groove on back face at WIRE_ANG: width, depth

# ---------- bearings [S standard sizes: d x D x B] ----------
BRG_OUT = (40.0, 52.0, 7.0)     # 6808-2RS  output
BRG_ECC = (15.0, 21.0, 4.0)     # 6702-2RS  x2, eccentric (disc) bearings
BRG_FRONT = (5.0, 11.0, 5.0)    # 685-2RS   hub front support, in carrier
BRG_6808_IN_LAND = 44.5         # [U] inner-ring outer land, must stay < 45.0 (pin_ring ID)
BRG_6808_OUT_LAND = 47.4        # [U] outer-ring inner land, must stay > 46.0 (front_ring ID)

# ---------- hub (input) ----------
CAM_D = 15.0                    # = BRG_ECC d
STUB_D = 4.99                   # 685 bore 5, slip
HUB_BORE = 4.05                 # on 4.0 shaft
HUB_BORE_L = SHAFT_OUT - (Z_HUB[0] - Z_MID[0])   # [U] = 7.7 with SHAFT_OUT 12
GRUB_Z = 35.8; GRUB_PILOT = 2.5 # M3x5 ISO 4026 set screw, radial, at angle 90

# ---------- discs ----------
DISC_BORE = 21.0                # = BRG_ECC D
OUT_PIN_N = 6; OUT_PIN_D = 3.0; OUT_PIN_PCD = 33.0; OUT_PIN_ANG0 = 30.0   # [D] 3x12 ISO 8734
OUT_PIN_PRESS = 2.95            # carrier hole for the 3.0 pin (press)
# disc hole d = OUT_PIN_D + 2*E + 2*CLR_TOOTH  (40:1 -> 4.14, 50:1 -> 3.90)

# ---------- carrier / flange / rings ----------
PLATE_D = 43.0                  # [D] carrier rear plate
SPIGOT_D = 39.95                # [D] 6808 bore 40, slip-press
SEAT_685 = 11.1                 # [D]
INS_M3_D = 4.6; INS_M3_L = 6.0  # [S kp] heat-set insert M3 x 5.7
FLANGE_D = 44.0                 # [D] out_flange (inside FRONT_RING ID)
PIN_RING = (51.9, 45.0)         # [D] OD, ID
FRONT_RING = (52.0, 46.0)       # [D] OD, ID - slip + 2 dots CA after testing

# ---------- encoder ----------
ENC_W = 23.4                    # [U] AS5600 board 23 x 23 + 0.4 (Q4)
ENC_WINDOW_D = 10.0             # [D] chip window through the back wall
MAG = (6.0, 2.5)                # [S] 6 x 2.5 diametric N35 magnet
# chip face at z ~3.75 [U SOIC-8 1.75 tall] -> magnet gap 1.25 (AS5600 wants 0.5-3) [U]
