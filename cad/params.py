"""SOMA arm — single source of truth for every dimension.

EVERYTHING is parametric. To retarget the arm at different servos or a
different size, edit this file and regenerate — no geometry is hardcoded
in the part modules.

Conventions
-----------
- Units are millimetres throughout.
- Joint axes: J1 = Z (yaw at base), J2 = shoulder pitch, J3 = elbow pitch,
  J4 = wrist pitch, J5 = wrist roll. Gripper = tendon-driven.
- "VERIFY" flags mark dimensions that must be checked against the vendor
  drawing of whichever servo is finally purchased.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Servo envelopes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ServoSpec:
    """Mechanical envelope of a serial bus servo.

    body_w  = width across the flat faces (X, perpendicular to shaft axis)
    body_d  = depth along output shaft axis (Y)
    body_h  = height along the arm axis (Z of the servo itself)
    spline  = output spline boss diameter (25T ≈ 5.9–6.0 mm on these servos)
    tab_*   = mounting ear/tab geometry (verify against vendor drawing)
    """
    name: str
    body_w: float
    body_d: float
    body_h: float
    spline_d: float = 5.9          # 25T spline OD
    spline_h: float = 4.0          # boss height above case
    stub_d: float = 20.0           # idler stub on back face (dual-axis servos)
    mass_g: float = 55.0
    stall_kgcm: float = 19.5
    tab_hole_d: float = 2.8        # M2.5 clearance, VERIFY
    tab_hole_pitch_w: float = 30.0  # VERIFY
    tab_hole_pitch_h: float = 40.0  # VERIFY
    bus: str = "TTL"               # TTL (STS) or RS485 (SM)
    volts: float = 7.4


# Feetech STS3215: 45.2 x 24.7 x 35 mm, 55 g, 19.5 kg·cm @7.4 V, TTL.
SERVO_SM = ServoSpec(
    name="STS3215",
    body_w=45.2, body_d=24.7, body_h=35.0,
    mass_g=55.0, stall_kgcm=19.5,
    bus="TTL", volts=7.4,
)

# Feetech SM40BL class: ~46.5 x 28.5 x 34 mm, ~100 g, 40 kg·cm @12 V, RS485.
SERVO_LG = ServoSpec(
    name="SM40BL-class",
    body_w=46.5, body_d=28.5, body_h=34.0,
    mass_g=100.0, stall_kgcm=40.0,
    tab_hole_pitch_w=32.0, tab_hole_pitch_h=42.0,   # VERIFY
    bus="RS485", volts=12.0,
)

# Feetech SM60CL class: 60 kg·cm @12 V — larger case, VERIFY envelope.
SERVO_XL = ServoSpec(
    name="SM60CL-class",
    body_w=58.0, body_d=30.0, body_h=42.0,
    mass_g=150.0, stall_kgcm=60.0,
    tab_hole_pitch_w=40.0, tab_hole_pitch_h=50.0,   # VERIFY
    bus="RS485", volts=12.0,
)


# ---------------------------------------------------------------------------
# Joint assignment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class JointSpec:
    name: str
    servo: ServoSpec
    has_sea: bool           # series-elastic cartridge on this joint
    range_deg: tuple = (-150.0, 150.0)


JOINTS = {
    "J1": JointSpec("waist yaw",   SERVO_SM, has_sea=False),
    "J2": JointSpec("shoulder",    SERVO_XL, has_sea=True),
    "J3": JointSpec("elbow",       SERVO_LG, has_sea=True),
    "J4": JointSpec("wrist pitch", SERVO_SM, has_sea=False),
    "J5": JointSpec("wrist roll",  SERVO_SM, has_sea=False),
    "GRIP": JointSpec("gripper",   SERVO_SM, has_sea=False),
}


# ---------------------------------------------------------------------------
# Links / workspace
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LinkSpec:
    upper_arm: float = 180.0    # J2 axis → J3 axis
    forearm: float = 160.0      # J3 axis → J4 axis
    wrist: float = 60.0         # J4 axis → flange
    payload_g: float = 300.0
    reach_mm: float = 400.0     # horizontal reach spec


LINKS = LinkSpec()


# ---------------------------------------------------------------------------
# Series-elastic cartridge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SEASpec:
    """Torsion-spring cartridge between servo horn and output link.

    Inner hub bolts to the servo horn; N spiral arms connect hub to an
    output ring. Output ring carries the next link + encoder magnet.
    AS5600 on the fixed side reads magnet position → deflection → torque.
    """
    disc_r: float          # outer radius of spring disc
    hub_r: float           # inner hub radius (spline adapter)
    disc_t: float          # axial thickness of the spring disc
    n_arms: int            # spiral arm count
    arm_w: float           # spiral arm radial width
    ring_w: float          # output ring radial width
    bearing: str           # output ring support bearing code
    magnet_d: float = 6.0  # diametric magnet for AS5600
    magnet_h: float = 3.0


# Sized per joint from the torque analysis:
#   J2: k ≈ 24 N·m/rad  → stiffer arms, thicker disc
#   J3: k ≈ 10 N·m/rad
SEA_J2 = SEASpec(
    disc_r=30.0, hub_r=9.0, disc_t=6.0,
    n_arms=4, arm_w=5.0, ring_w=6.0,
    bearing="6804",                    # 20×32×7
)
SEA_J3 = SEASpec(
    disc_r=24.0, hub_r=9.0, disc_t=5.0,
    n_arms=4, arm_w=4.0, ring_w=5.0,
    bearing="6704",                    # 20×27×4
)


# ---------------------------------------------------------------------------
# Bearings (code → (inner_d, outer_d, width))
# ---------------------------------------------------------------------------

BEARINGS = {
    "608":  (8.0, 22.0, 7.0),
    "6704": (20.0, 27.0, 4.0),
    "6804": (20.0, 32.0, 7.0),
    "6706": (30.0, 37.0, 4.0),
    "6806": (30.0, 42.0, 7.0),
    "6808": (40.0, 52.0, 7.0),
}


# ---------------------------------------------------------------------------
# Print / assembly tolerances
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TolSpec:
    press: float = -0.05      # press-fit allowance (interference)
    slip: float = 0.15        # slip fit clearance (diameter)
    loose: float = 0.30       # running clearance
    wall: float = 2.4         # min structural wall
    shell: float = 1.6        # cosmetic shell wall


TOL = TolSpec()


# ---------------------------------------------------------------------------
# Fasteners
# ---------------------------------------------------------------------------

HEAT_SET = {"M2": 2.0, "M2.5": 2.5, "M3": 3.0, "M4": 4.0, "M5": 5.0}


# ---------------------------------------------------------------------------
# Electronics envelopes (for the face/wrist module)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ElecSpec:
    gc9a01_d: float = 33.0       # 1.28" round LCD module OD
    gc9a01_t: float = 4.0
    usb_cam_w: float = 25.0      # micro USB camera board envelope
    usb_cam_d: float = 8.0
    as5600_w: float = 22.0       # encoder breakout envelope
    as5600_t: float = 3.0
    bmp390_w: float = 14.0       # breakout envelope on fingertip
    esp32_mini_w: float = 25.5   # ESP32-S3-MINI-class dev board width


ELEC = ElecSpec()
