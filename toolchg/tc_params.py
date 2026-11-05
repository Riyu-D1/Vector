"""toolchg/tc_params.py - D10 automounter numbers (mm, deg).

Automatic quick-change tool mount for the D6 K-KEEL wrist: a 3-lug bayonet
twist-lock on the J6 roll axis, driven by J6 itself (no extra actuator).
Master plate bolts to the J6 horn exactly like w_grip_frame's horn plate;
each tool carries a matching socket plate + body. A docking rack on the
table holds tools by a circumferential groove on the tool plate OD.

W frame (cradlefix/ap6.py): origin on the J4 axis, a = tool direction
(world +X at home), b = world Y, h = up (world +Z).  Roll axis = the line
b = 0, h = J6_AX_H = -17.0.  Everything here is drawn in W.

Tags: [D] design choice, [S] sourced from an existing tested file, [U]
unverified - never "fix" a [U] value, write it in STATUS.
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cradlefix"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
import ap2 as P2          # noqa
import ap2b as B          # noqa
import ap6 as N           # noqa  (D6 wrist numbers: J6_AX_H, GF_PLATE_A ...)

# ---------- print / material rules [stage] ----------
TC_WALL_MIN = 1.8          # min wall anywhere on the coupling
RHO_PETGCF = N.RHO_PETGCF  # 1.31e-3 g/mm3 solid
INFILL_EFF = N.INFILL_EFF  # 0.6 printed/solid [U]
X_STRESS = N.X_STRESS      # 25 MPa cross-layer [U]; along-layer 50 [U]

# ---------- coupling axis / master plate (arm side, J6-out) ----------
H_AX = N.J6_AX_H           # -17.0 roll axis height
TC_PLATE_A = (62.7, 68.7)  # horn plate on the J6 horn face 62.6; +a face
                           # 0.3 mm clear of the socket face (a 69.0)
TC_PLATE_R = 15.0          # OD, same roll clip as GF_PLATE (r15 about (0,-17))
TC_CB_A = N.GF_CB_A        # 67.0 horn-screw counterbore start (as w_grip_frame)

# spigot = pilot cylinder the tool socket rotates about
TC_SPIGOT_R = 13.0         # [D] spigot OD
TC_SPIGOT_TIP = 75.8       # [D] spigot tip face a
TC_BORE_D = 7.2            # [D] centre bore (horn centre-screw access, Ø7 recess)

# male lugs (on the spigot tip, facing -a at lock)
TC_N_LUG = 3
TC_LUG_A = (72.4, 75.8)    # [D] lug band (3.4)
TC_LUG_R = 17.3            # [D] lug tip radius (socket bore 18.2 -> 0.9 gap)
TC_LUG_ARC = 32.0          # [D] lug angular width
TC_LUG_IN = 12.4           # [D] lug root overlaps spigot r13 by 0.6 -> one
                           # fused body for the FEM mesh (tangent = float)
# lug centre phases in the MASTER b,h frame (deg, 0=+b 90=+h, +roll about +a)
TC_LUG_PH = (70.0, 190.0, 310.0)
TC_LUG_LEAD = 0.5          # [D] 45deg entry chamfer reach on lug tip edges

# ---------- tool plate (socket side) ----------
TC_RING_A = (69.0, 78.4)   # [D] socket ring a-range
TC_RING_RIN = 18.2         # [D] bore (clears lug r17.3 by 0.9)
TC_RING_ROUT = 23.0        # [D] OD
TC_CATCH_A = (69.0, 72.2)  # [D] catch band (3.2)
TC_CATCH_R = 13.2          # [D] catch inner radius (clears spigot r13 by 0.2)
TC_CATCH_ARC = 75.0        # [D] catch angular width (3 catches -> 45 deg gaps)
# catch centre phases in the SOCKET b,h frame; gaps between them centred at
# 58/178/298.  Entry roll -12 deg puts the lugs dead centre in the gaps
# (6.5 deg margin each side), twist +60 deg then centres them under the
# catches for maximum capture.
TC_CATCH_PH = (118.0, 238.0, 358.0)
TC_ENTRY_REL = -12.0       # [D] master roll offset: lugs -> gap centres
TC_TWIST = 60.0            # [D] lock rotation (socket frame), + about +a
# net master rotation entry -> lock = ENTRY_REL + TWIST = +48 deg
TC_GROOVE_A = (TC_CATCH_A[1], TC_LUG_A[1] + 0.2)       # 72.2..76.0 rotation space
TC_FLOOR_A = (76.0, 78.4)  # [D] socket floor (2.4)
# resulting fits: lug -a face 72.4 vs catch face 72.2 -> 0.2 running gap;
# spigot tip 75.8 vs floor 76.0 -> 0.2 gap (pogo springs bridge it)

# ---------- dock groove on the ring OD (rack holds the tool here) ----------
TC_DOCK_A = (72.25, 77.25)  # [D] groove band (5.0 for a 4.0 rack plate +-0.5)
TC_DOCK_R = 20.6           # [D] groove floor r -> ring wall 2.4 under it
TC_KEY_PH = 270.0          # [D] anti-rotation notch phase (keel-down)
TC_KEY_W = 4.0             # [D] notch width along arc (mm at r20)
TC_KEY_D = 1.2             # [D] notch depth into groove floor

# ---------- detent (spring plunger in the ring wall) ----------
TC_DET_A = 74.0            # [D] radial spring plunger position (groove zone)
TC_DET_PH = 110.0          # [D] plunger phase, socket frame: lug1 leading
                           # edge sweeps past it at twist ~36, ball then
                           # rides the lug OD ~24 deg and drops into the
                           # dimple at lock
TC_DET_D = 4.2             # [D] plunger bore (M4 spring plunger [U] hardware)
TC_DET_PR = 1.0            # [D] ball tip reaches r17.2: rides lug OD 17.3
# dimple on lug1 OD: master-frame phase where the ball (socket ph 110)
# sits at lock = DET_PH - (ENTRY_REL + TWIST) = 62
TC_DIMPLE_PH = TC_DET_PH - (TC_ENTRY_REL + TC_TWIST)   # 62 deg master frame
TC_DIMPLE_D = 3.0          # [D] dimple dia (for the ~3mm plunger ball)
TC_DIMPLE_DPTH = 0.8       # [D] dimple depth into lug OD

# ---------- electrical pass-through (pogo + pads) ----------
# 5 lines: GND, +12V, DATA (STS3215 half-duplex bus) + SP1, SP2 spare.
# Pogo pins stand on the socket floor pointing -a; pads are arcs of copper
# tape on the master spigot TIP face, spanning the twist sweep so contact
# holds from approach through lock (GND arc longest = first/last mate).
TC_PIN_R = (9.0, 9.0, 11.0, 11.0, 11.0)      # GND 12V DAT S1 S2  [D]
TC_PIN_PH = (30.0, 150.0, 210.0, 270.0, 330.0)  # phases on the floor [D]
TC_PIN_D = 1.8             # [D] bore for ~Ø1.5 pogo barrel [U hardware]
TC_PIN_PR = 0.8            # [D] pin tip proud of floor face (comp 0.6)
TC_PAD_HW = 2.6            # [D] pad width across arc (radial, on tip face)
# pad master-frame arc must span the whole entry->lock sweep (48 deg) so
# contact holds throughout: pad centred at pin_ph - ENTRY_REL - TWIST/2,
# arc >= TWIST + pad_end_margin
TC_PAD_ARC = (72.0, 68.0, 68.0, 68.0, 68.0)  # GND longest [D]

# ---------- tool-body shift ----------
# g servo case front is a 66.8 on the stock grip; the socket floor ends at
# 78.4, so the whole tool body moves +12.0 to keep the case out of the
# socket volume (78.8 >= 78.4 + 0.3 clearance).
TC_SH = 12.0               # [D] tool-body shift vs w_grip_frame geometry
TC_BODY_A = 78.4           # tool plate back face -> body starts here
A_TCP_TC = N.A_TCP + TC_SH          # 149.4 new TCP on a (grip tool)
TCP_W_TC = (A_TCP_TC, 0.0, H_AX)    # TCP in W

# ---------- rack (world frame, on the table) ----------
# Rack plate plane is normal to the tool axis. Dock = groove band.
RACK_PLATE_T = 4.0         # [D] fork plate thickness (fits groove 4.5)
RACK_SLOT_W = 41.7         # [D] slot opening width (groove floor Ø41.2 + 0.5)
RACK_SEAT_R = 20.9         # [D] slot floor radius (groove floor r20.6 + 0.3)
RACK_N_SLOTS = 4           # [D]
RACK_SLOT_PITCH = 46.0     # [D] slot spacing along the rail
RACK_KEY = (2.5, 1.4)      # [D] tab on slot floor: (width, height) into notch
# dock pose: tool axis = world +X at this (y, z) - inside the D6 workspace
RACK_AXIS_Y = -80.0        # [D] mm world y of the tool axes
RACK_AXIS_Z = 110.0        # [D] mm world z of the tool axes (above table)
RACK_PLATE_X = 145.0       # [D] world x of the fork plate centre; the
                           # dock TCP then sits at ~208 mm, inside reach
# W-frame mapping at the dock pose: the tool hangs keel-down, socket facing
# -x (toward the arm); the arm approaches along +x.

# ---------- mass budget / torque [S stage] ----------
M_BUDGET = 0.234           # wrist+gripper modelled budget kg
M_WRIST_D6 = 0.225         # D6 modelled wrist+gripper kg
PAYLOAD = 0.5              # kg at TCP (close) / 0.41 full reach [S final2]

# ---------- pen tool ----------
PEN_D = 8.5                # [D] pen bore (8 mm marker/pointer + 0.5)
PEN_TIP_A = A_TCP_TC       # pen tip aligned with the grip-tool TCP
PEN_BODY_R = 9.5           # [D] pen holder tube OD r (wall ~3 vs bore)
PEN_SET_D = 3.0            # [D] M3 grub self-tap pilot for the pen (not a
                           # heat-set insert; an insert would need ~Ø4.3)
