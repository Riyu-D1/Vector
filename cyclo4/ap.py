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
CLR_TOOTH = 0.01                # [D4] disc flank offset beyond the pin radius:
                                #   near-zero-clearance mesh -> pins engage the
                                #   flat conjugate flank, SF 2.25 @ J2 design
                                #   (load_model.py).  Print tolerance >> 0.01, so
                                #   this is a run-in / selective-pin-fit design:
                                #   effective working clearance ends ~0-0.02.
CLR_OUT = 0.12                  # [D4] out-pin hole radial clearance: the disc's
                                #   orbit needs a print-safe gap; NOT tied to
                                #   CLR_TOOTH or the printed hole binds.
DISC_M = 1440                   # [D] points used for the disc outline in CAD
DISC_MAT = "PETG-CF printed (A1)" # [D4] printed discs stay; pins are the only
                                #   non-printed part (ISO 8734 steel dowels)

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
MOT_D = 44.5; MOT_H = 19.0; MOT_MASS_G = 85     # [U] A1c: stator base face -> bell top (community STEP 19.0; Tarot spec 22.0 maybe incl. prop seat)
DZ = MOT_H - 19.0               # A1c: shifts every part in front of the motor. MOT_H 22.0 -> DZ 3.0 -> length 58.0 (gate limit 55)
MOT_KV = 330; MOT_R_OHM = 0.145                 # [S study / U xcopterCalc]
SHAFT_D = 4.0                                    # [S study] not hollow
ROTOR_PCD = 34.0; ROTOR_ANG = (90.0, 270.0)      # [S Tarot prop mount 34 mm, Dongil adapter +-17] [U positions on the real bell]
ROTOR_HOLE = 3.4; ROTOR_CB_D = 6.2; ROTOR_CB_H = 1.9   # [D] A1c: 2x M3x5 ISO 7380 hub -> bell top [U thread depth in the bell]
MOT_PCD = 32.0; MOT_SCREW_ANG = (30.0, 150.0, 270.0)  # [S BOPP Tarot 4008 STEP] stator base 3x M3 on PCD 32 (= 27.7 triangle); was [U] 4x PCD25
MOT_PLATE = 3.0; MOT_CB_D = 6.2  # [D] A1c: back plate under the stator screw heads; 3x M3x6 ISO 7380 from the back [U thread depth]
BELL_CLR = 0.45                                  # [D] bell radius 22.25 -> bore radius 22.7

# ---------- Z stack (module frame) ----------
Z_BACK = (0.0, 3.6)             # [D] housing back wall
Z_ENC_POCKET = (0.0, 1.8)       # [D] AS5600 board pocket, open to the back face (gate fallback: was 2.0, floor 1.6 -> 1.8)
Z_MAG = (4.7, 7.2)              # [D] A1c: 6x2.5 magnet in mag_puck, faces the AS5600 (gap 0.95 [U chip height])
Z_STATOR = 10.2                 # [D] A1c: stator base face on the housing back plate
Z_PUCK = (4.7, Z_STATOR + 0.5)  # [D] A1c: mag_puck; its d8 nose enters the stator washer recess by 0.5 [U]
PUCK_D = 12.0; PUCK_NOSE = (8.0, 0.8); PUCK_HOLE = 3.2; PUCK_POCKET = (6.05, 4.15)  # [S Dongil puck 12x6, pocket 6.05, hole 3.2] pocket depth = magnet 2.5 + M3 button head 1.65
PUCK_CAV_D = 13.0               # [D] A1c: housing cavity around the spinning puck
MOT_RECESS = (9.1, 0.6)         # [S BOPP STEP: retaining washer d9.07, 0.5 inside the base] vendor_motor proxy only
Z_MOTOR = (Z_STATOR, Z_STATOR + MOT_H)   # [D] A1c: stator base -> bell top (bell top faces the gearbox)
Z_ADAPT = (Z_MOTOR[1], Z_MOTOR[1] + 4.0)  # [D] A1c: hub rotor flange, 4.0 thick, clamped on the bell top
ADAPT_L = 44.0; ADAPT_W = 20.0; ADAPT_CTR = (3.0, 4.0)  # [S Dongil adapter 44x20 bar] ends trimmed to d44; centre clearance d, depth [U bell centre]
Z_DISC1 = (33.65 + DZ, 37.90 + DZ)  # [D4] 4.25 thick (was 4.0) - thicker lobes
Z_DISC2 = (38.05 + DZ, 42.30 + DZ)  # [D4] 4.25 thick; top clears carrier plate 42.4
Z_B6702_1 = (33.85 + DZ, 37.85 + DZ)  # [D4] 6702 #1 (4.0 w) centred under disc1
Z_B6702_2 = (38.15 + DZ, 42.15 + DZ)  # [D4] 6702 #2 (4.0 w) centred under disc2
Z_RINGPIN = (33.5 + DZ, 43.5 + DZ)  # [D] A1c: ring pins (10 long) stand on the blind housing groove floors
Z_HUB = (Z_ADAPT[0], 47.2 + DZ)  # [D] A1c: rotor flange Z_ADAPT, cam1 to Z_CAM_SPLIT, cam2 to Z_STUB0, stub to 47.2
Z_CAM_SPLIT = 37.95 + DZ; Z_STUB0 = 42.25 + DZ
Z_CARRIER_PLATE = (42.4 + DZ, 45.4 + DZ)  # [D]
Z_PIN_RING = (43.5 + DZ, 45.4 + DZ)  # [D] spacer: ring pins -> 6808 outer race
Z_6808 = (45.4 + DZ, 52.4 + DZ)  # [S 6808 width 7]
Z_SPIGOT = (45.4 + DZ, 52.4 + DZ)  # [D] carrier spigot inside the 6808
Z_FRONT_RING = (52.4 + DZ, 54.4 + DZ)  # [D] retains 6808 outer race; housing ends at 54.4
Z_FLANGE = (52.4 + DZ, 55.0 + DZ)  # [D] out_flange, proud of housing by 0.6
Z_OUTPIN = (34.0 + DZ, 46.0 + DZ)  # [D] output pins 3x12, pressed 3.6 deep into carrier
Z_685 = (42.4 + DZ, 47.4 + DZ)  # [S 685 width 5]

# ---------- housing bores ----------
BORE_MOTOR = 45.4               # [D] A1c: Z_STATOR .. Z_RINGPIN[0]
BORE_PIN = 47.4                 # [D] A1b: was 47.0 (=2R); +0.2 radius trims the thin pin-web tips (minwall)
PIN_HOLE_D = 3.05               # [D] ring pin holes (3.0 pins) at radius R (50:1: 2.55)
SEAT_6808 = 52.1                # [D] 6808 OD 52 + 0.1 (PETG prints holes small)
WIRE_ANG = 90.0; WIRE_W = 4.0; WIRE_R = (22.5, 25.2)   # [D] axial phase-wire channel
NOTCH_W = 5.0; NOTCH_Z = (0.0, 8.0)                    # [D] side notch where wires leave
ENC_GROOVE_W = 3.0; ENC_GROOVE_D = 1.2                 # [D] back-face groove pocket -> notch

WIRE_GROOVE = (4.0, 1.5)        # [D] A1c: phase-wire groove in the back-plate front face at WIRE_ANG: width, depth [U wire exit]

# ---------- bearings [S standard sizes: d x D x B] ----------
BRG_OUT = (40.0, 52.0, 7.0)     # 6808-2RS  output
BRG_ECC = (15.0, 21.0, 4.0)     # 6702-2RS  x2, eccentric (disc) bearings
BRG_FRONT = (5.0, 11.0, 5.0)    # 685-2RS   hub front support, in carrier
BRG_6808_IN_LAND = 44.5         # [U] inner-ring outer land, must stay < 45.0 (pin_ring ID)
BRG_6808_OUT_LAND = 47.4        # [U] outer-ring inner land, must stay > 46.0 (front_ring ID)

# ---------- hub (input) ----------
CAM_D = 15.0                    # = BRG_ECC d
STUB_D = 4.99                   # 685 bore 5, slip

# ---------- discs ----------
DISC_BORE = 21.0                # = BRG_ECC D
OUT_PIN_N = 6; OUT_PIN_D = 3.0; OUT_PIN_PCD = 33.0; OUT_PIN_ANG0 = 30.0   # [D] 3x12 ISO 8734
OUT_PIN_PRESS = 2.95            # carrier hole for the 3.0 pin (press)
# disc hole d = OUT_PIN_D + 2*E + 2*CLR_OUT   (40:1 -> 4.08, 50:1 -> 3.84)

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
# chip face at z ~3.75 [U SOIC-8 1.75 tall] -> magnet gap 0.95 (AS5600 wants 0.5-3) [U]
