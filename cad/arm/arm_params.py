"""SOMA arm v3 — structure parameters (Stream B).

Every dimension comes from a cited source or a measurement from a STEP
file; anything else is marked UNVERIFIED/ASSUMED and made adjustable.

Frame: Z up, origin at the drum-centre on the recess floor of the case lid.
Arm chain: J1 yaw (vertical actuator) -> J2 shoulder (horizontal actuator)
-> J3 elbow (horizontal actuator) -> J4 wrist pitch + J5 wrist roll
(STS3215) -> J6 gripper (STS3215, compact jaw).

Sources:
  [CASE]   cad/lib/case.py (drum recess geometry, lid, M4 post holes)
  [WV]     Waveshare ST3215 drawing, ST3215-2D.zip (verified hole grid)
  [SO102]  SO-ARM-102 STEP parts, measured (servo body, horn/idler dims,
           gripper concept, joint limits)
  [V3]     ARM_HYBRID_V3.md (actuator choice, link lengths, loads)
  [ASSUME] Placeholder actuator interface until Stream A publishes
           cad/actuator/INTERFACE.md on branch arm-actuator
"""
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Stream A actuator — PLACEHOLDER until cad/actuator/INTERFACE.md lands.
# Everything derived from these numbers is parametric: update this block only.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ActuatorSpec:
    name: str = "cycloidal-5010 (Stream A placeholder)"
    body_d: float = 60.0        # [V3] "60 mm OD x 70 mm placeholder"
    body_l: float = 70.0        # [V3]
    mass_g: float = 380.0       # [ASSUME] 5010 motor ~130g + printed gearbox; UNVERIFIED
    # Output (driven) face: bolt circle that carries the next link.
    out_pcd: float = 36.0       # [ASSUME] 6xM4 on Ø36, ~Ø50 flange face
    out_bolts: int = 6
    out_bolt_d: float = 4.5     # M4 clearance
    out_flange_d: float = 50.0  # [ASSUME] output flange OD
    out_flange_proud: float = 1.5  # [ASSUME] flange face proud of body end
    # Body (fixed) face: bolt circle that ties the body to its cradle.
    fix_pcd: float = 52.0       # [ASSUME] 4xM3 on Ø52 back face
    fix_bolts: int = 4
    fix_bolt_d: float = 3.4     # M3 clearance
    cable_exit_w: float = 12.0  # slot for motor wires + CAN + encoder
    cable_exit_h: float = 8.0
    # torque capability (for the margin report; Stream A owns the real number)
    rated_nm: float = 7.9       # [V3] "about 7.9 N.m available"
    stall_nm: float = 12.0      # [ASSUME] UNVERIFIED


ACTUATOR = ActuatorSpec()


# ---------------------------------------------------------------------------
# Feetech STS3215 12 V — VERIFIED geometry from the SO-ARM-102 assembly STEP
# (servo solid) + Waveshare ST3215 drawing.
#   local axes of the servo model: X = 45.2 length, Y = shaft axis, Z = 24.7
#   Output (horn) face near +Y end; back boss face near -Y end.
#   The two end faces carry DIFFERENT M2 self-tap grids (both in the DXF):
#     24.45 x 20.5 on one face, 20.7 x 20.5 on the other — I use 24.45 grid
#     as the primary mount like the guide says.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ServoSpec:
    name: str = "STS3215-12V"
    body_l: float = 45.2        # [WV][SO102] along X of servo model
    body_t: float = 24.7        # [WV][SO102] thickness
    body_h: float = 35.0        # [WV] case height between end faces
    wheel_d: float = 19.2       # [SO102] output boss OD
    wheel_h: float = 4.5        # [SO102] boss height above output face
    stub_d: float = 19.2        # [SO102] back idler boss OD
    stub_h: float = 3.4         # [SO102]
    axis_to_end: float = 42.5   # [SO102] total height incl. wheels (35+4.5+3.4~43)
    horn_screw_d: float = 3.2   # [SO102] horn centre screw M3
    mass_g: float = 55.0        # [WV]
    stall_kgcm: float = 30.0    # [WV] 30 kg.cm @12 V
    rated_kgcm: float = 10.0    # ~1 N.m usable continuous (BOM.md estimate)
    volts: float = 12.0
    # verified mounting grids (Ø1.6 self-tap, use M2 screws into them)
    hole_d: float = 1.6         # [WV]
    grid_a: tuple = (24.45, 20.5)   # [WV] primary face (guide's pattern)
    grid_b: tuple = (20.7, 20.5)    # [WV] opposite face


SERVO = ServoSpec()
# pocket clearance applied to the servo envelope (guide: >=0.3 mm)
SERVO_CLEAR = 0.35


# ---------------------------------------------------------------------------
# Joint limits — adopted from SO-ARM-102 specs (proven limits for this servo
# family); J2/J3 use the actuators' own limits once Stream A reports them.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class JointSpec:
    name: str
    kind: str                    # "actuator" or "servo"
    range_deg: tuple             # (min, max) in degrees
    axis: tuple                  # unit axis in parent-link frame


# Link-frame conventions: every link's local frame has X along the link
# (proximal->distal joint), Z up at zero pose.
JOINTS = {
    # J1 yaw: actuator vertical, +Z.  [SO102] base rotation +-176 deg.
    "J1": JointSpec("waist yaw",  "actuator", (-170.0, 170.0), (0, 0, 1)),
    # J2 shoulder: axis +Y.  Negative limit: link webs vs the cradle
    # web (~-15); positive: distal plates sweeping over the Ø132 drum
    # (~+30).  Raising either needs a taller turret or larger J2_Z.
    "J2": JointSpec("shoulder",   "actuator", (-15.0, 30.0), (0, 1, 0)),
    # J3 elbow: axis +Y.  Limited by the forearm webs sweeping into the
    # upper-link saddle web beyond ~+-100; verified +-90.
    "J3": JointSpec("elbow",      "actuator", (-90.0, 90.0), (0, 1, 0)),
    # J4 wrist pitch: axis +Y.  [SO102] -99..+97 deg.
    "J4": JointSpec("wrist pitch", "servo",   (-95.0, 95.0),   (0, 1, 0)),
    # J5 wrist roll: axis +X.  [SO102] -165..+163 deg.
    "J5": JointSpec("wrist roll",  "servo",   (-160.0, 160.0), (1, 0, 0)),
    # J6 gripper: servo drives jaws; +-90 travel.
    "J6": JointSpec("gripper",     "servo",   (-90.0, 90.0),   (0, 1, 0)),
}


# ---------------------------------------------------------------------------
# Links — [V3]: shoulder->elbow 120, elbow->wrist 100, wrist->tool 40.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LinkSpec:
    l_upper: float = 120.0      # J2 axis -> J3 axis              [V3]
    l_fore: float = 100.0       # J3 axis -> J4 axis              [V3]
    l_tool: float = 55.0        # J4 axis -> gripper tip; V3 asks 40 mm —
                                # physically impossible below ~50 with a
                                # servo-driven jaw; marked in docs.
    j2_rise: float = 105.0      # J1 seat -> J2 axis height (turret)
    reach_target: float = 260.0 # [V3]
    payload_g: float = 250.0    # [V3] design payload
    payload_check_g: tuple = (300.0, 500.0)   # report both margins


LINKS = LinkSpec()


# ---------------------------------------------------------------------------
# Bearings (standard sizes, code -> (bore, OD, width))
# ---------------------------------------------------------------------------
BEARINGS = {
    "608":  (8.0, 22.0, 7.0),    # idler pivots
    "6804": (20.0, 32.0, 7.0),   # joint back-side idler
    "6808": (40.0, 52.0, 7.0),   # J1 turntable          [CASE guide]
    "MF106": (6.0, 10.0, 3.0),   # gripper rods          [SO102]
}


# ---------------------------------------------------------------------------
# Case interface — [CASE] from cad/lib/case.py (do not modify the case)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CaseSpec:
    drum_d: float = 132.0        # arm drum lands in this recess
    recess_depth: float = 2.5    # seat depth into the 4 mm lid
    lid_t: float = 4.0
    lid_top_z: float = 40.0      # case coords: top of lid
    drum_cxy: tuple = (75.0, 88.0)   # drum centre in case coords
    # M4 hold-down posts inside the drum circle (case coords)
    posts: tuple = ((40, 132), (110, 132), (45, 145), (105, 145), (75, 143))
    post_hole_d: float = 4.4     # lid M4 clearance
    # rear cable channel in the tray wall (case coords) at y~157, z~27
    cable_channel_z: float = 27.0


CASE = CaseSpec()

# drum post positions in ARM coords (x = case_x-75, y = case_y-88)
DRUM_POSTS = tuple((x - CASE.drum_cxy[0], y - CASE.drum_cxy[1])
                   for x, y in CASE.posts)


# ---------------------------------------------------------------------------
# Tolerances / print rules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TolSpec:
    press: float = -0.05
    slip: float = 0.15
    loose: float = 0.30
    servo: float = SERVO_CLEAR
    min_wall: float = 1.6        # [GUIDE] minimum wall check
    wall: float = 2.4
    insert_m3_d: float = 4.6     # M3 heat-set insert bore (typ. 4.2-4.8)
    insert_m4_d: float = 5.6     # M4 heat-set insert bore


TOL = TolSpec()


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CableSpec:
    """Bundle through the arm: CAN to J1-J3 + 12V pair + servo bus to J4-6."""
    n_wires: int = 8
    wire_d: float = 1.8          # ~22 AWG silicone
    channel_w: float = 8.0       # [GUIDE] min channel 8x6 per link
    channel_h: float = 6.0
    slip_d: float = 14.0         # hole through bearing centre for bundle


CABLE = CableSpec()
