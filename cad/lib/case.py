"""Electronics plinth — the arm's foot + carrier-board enclosure.

Two-part rounded-rectangle shell under the base drum:
  - tray: floor, walls, PCB standoffs, panel cutouts, corner bosses
  - lid:  top cover, drum landing recess, vent slots, corner screws

Board orientation inside (soma-carrier v1.1, 135x115):
  - north edge (J4/J5/J6 servo ports, y~9-15)  -> REAR: cables exit the
    rear channel straight up into the drum zone
  - south edge (J13 jog, J9 estop, J15, buzzer) -> FRONT rim
  - west edge (XT60, screw terminals, USB)      -> LEFT wall
  - east edge (IR1, J14, J10)                   -> RIGHT wall

User-facing parts are panel-mounted on the front rim — the OLED bezel,
EC11 jog dial and estop button each take a short flying lead to the
matching header on the board's south edge (standard panel wiring, not
loose dupont rats-nest: three keyed 4/2-pin leads, labelled).
"""

import math
from dataclasses import dataclass

from build123d import (
    Axis, Box, Cylinder, Pos, Rot, Part, fillet,
)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import TOL


@dataclass
class CaseParts:
    tray: Part
    lid: Part
    top_z: float            # top of lid (drum lands here)


# --------------------------------------------------------------------------
# Geometry constants (mm)
# --------------------------------------------------------------------------

CASE_W, CASE_D = 150.0, 160.0          # exterior footprint
WALL = 2.6                              # shell wall
FLOOR = 3.0                             # tray floor
LID_T = 4.0                             # lid thickness (drum sits on it)
CASE_H = 36.0                           # tray height to rim
CORNER_R = 8.0

STANDOFF_H = 8.0                        # PCB standoff height
STANDOFF_R = 3.2                        # M3 boss
PCB_W, PCB_H = 135.0, 115.0

# Board -> case mapping: board-x -> case-x; board south edge (y=115) to
# the front rim.  Board spans case x 7.5..142.5, y 7.6..122.6.
PCB_X0 = 7.5
PCB_Y0 = 122.6
DRUM_CX, DRUM_CY = 75.0, 88.0           # drum landing centre on the lid
DRUM_D = 132.0
DRUM_SEAT = 2.5

def _bx(bx):  return PCB_X0 + bx
def _by(by):  return PCB_Y0 - by

FRONT, LEFT, RIGHT = "F", "L", "R"

# wall cutouts: (wall, centre along wall, z centre, w, h)
PANEL_CUTS = [
    # front rim — panel-mounted user parts
    (FRONT, _bx(14.0), 20.0, 7.4, 9.0),    # EC11 jog: M7 shaft + play
    (FRONT, _bx(30.0), 19.0, 16.4, 16.4),  # estop button ø16
    (FRONT, _bx(70.0), 20.0, 24.0, 4.0),   # buzzer grille slot
    (FRONT, _bx(86.0), 18.0, 12.0, 8.0),   # wrist cable exit (J10)
    # left wall — power + programming
    (LEFT, _by(17.0), 16.0, 15.0, 10.0),   # XT60 inlet
    (LEFT, _by(36.0), 14.0, 11.0, 9.0),    # 5V screw terminal (J2 @y36)
    (LEFT, _by(48.0), 14.0, 11.0, 9.0),    # 12V screw terminal (J1 @y48)
    (LEFT, _by(58.0), 16.0, 8.0, 6.0),     # JP1 power-jumper/rocker wire
    (LEFT, _by(39.5), 24.0, 13.0, 7.0),    # USB-C cable slot
    # right wall — sensors + aux
    (RIGHT, _by(36.0), 16.0, 7.5, 7.5),    # IR dome window (IR1 @y36)
    (RIGHT, _by(48.0), 15.0, 9.0, 6.0),    # NeoPixel wire hole (J14)
    (RIGHT, _by(24.0), 18.0, 10.0, 8.0),   # IMU cable (J12 @y24)
]

# OLED bezel: tilted window on the front rim, SSD1306 0.96" PCB is
# ~27x27mm behind a ~24x12mm glass window.
OLED_BEZ_X = _bx(50.0)                  # centred between jog and estop
OLED_BEZ_Z = 20.0


def _rounded_slab(w, d, h, r, z0=0.0):
    """Box with vertical corner edges rounded."""
    slab = Pos(w / 2, d / 2, z0 + h / 2) * Box(w, d, h)
    return fillet(slab.edges().filter_by(Axis.Z), r)


def _wall_cut(part, wall, c, z, w, h):
    if wall == FRONT:
        part -= Pos(c, 0, z) * Box(w, WALL * 3, h)
    elif wall == LEFT:
        part -= Pos(0, c, z) * Box(WALL * 3, w, h)
    else:
        part -= Pos(CASE_W, c, z) * Box(WALL * 3, w, h)
    return part


def make_case() -> CaseParts:
    iw, idd = CASE_W - 2 * WALL, CASE_D - 2 * WALL

    # --- tray -------------------------------------------------------------
    tray = _rounded_slab(CASE_W, CASE_D, CASE_H, CORNER_R)
    tray -= Pos(WALL + iw / 2, WALL + idd / 2, FLOOR
                + (CASE_H - FLOOR) / 2) * Box(iw, idd, CASE_H - FLOOR + 2)

    # Lid seat rebate (1.2 mm deep around the rim).
    tray -= Pos(CASE_W / 2, CASE_D / 2, CASE_H - 0.6) * Box(
        CASE_W - 1.2, CASE_D - 1.2, 1.2)

    # PCB standoffs (M3 self-tap posts).
    for hx, hy in [(4, 4), (131, 4), (4, 111), (131, 111)]:
        post = Pos(_bx(hx), _by(hy), FLOOR + STANDOFF_H / 2) * Cylinder(
            STANDOFF_R, STANDOFF_H)
        post -= Pos(_bx(hx), _by(hy), FLOOR + STANDOFF_H - 1.5
                    ) * Cylinder(1.1, 3.0)
        tray += post

    # Panel cutouts.
    for wall, c, z, w, h in PANEL_CUTS:
        tray = _wall_cut(tray, wall, c, z, w, h)

    # OLED bezel pocket on the front rim: tilted 25 deg, the module's 4-pin
    # header lands inside; glass shows through the window.
    bez = Pos(OLED_BEZ_X, WALL + 1.5, OLED_BEZ_Z) * Box(30, 8, 17)
    bez = bez.rotate(Axis.X, -25)
    tray -= bez
    tray -= Pos(OLED_BEZ_X, 0, OLED_BEZ_Z) * Box(24, WALL * 3, 12)

    # Rear cable channel: servo/encoder/wrist bundle exits up into the
    # drum zone (J4/J5/J6 sit at case y~90-96).
    tray -= Pos(_bx(50), CASE_D - WALL, FLOOR + 24) * Box(76, WALL * 3, 24)

    # Drum-load support posts inside the tray, under the seat circle and
    # clear of the grown board rectangle (x7.5-142.5, y7.6-122.6) — they
    # moved to the free strip north of the board's rear edge.
    for px, py in [(40, 132), (110, 132), (45, 145), (105, 145),
                   (75, 143)]:
        tray += Pos(px, py, FLOOR + (CASE_H - FLOOR - 4) / 2) * Cylinder(
            5.0, CASE_H - FLOOR - 4)
        tray -= Pos(px, py, CASE_H - 5) * Cylinder(1.5, 8)   # M4 pilot

    # Corner screw bosses for the lid.
    for cx, cy in [(10, 10), (CASE_W - 10, 10),
                   (10, CASE_D - 10), (CASE_W - 10, CASE_D - 10)]:
        boss = Pos(cx, cy, FLOOR + (CASE_H - FLOOR) / 2) * Cylinder(
            4.0, CASE_H - FLOOR)
        boss -= Pos(cx, cy, CASE_H - 4) * Cylinder(1.15, 8)
        tray += boss

    # --- lid --------------------------------------------------------------
    lid = _rounded_slab(CASE_W - 2.4, CASE_D - 2.4, LID_T, CORNER_R - 1)
    lid = Pos(1.2, 1.2, 0) * lid

    # Drum landing recess.
    lid -= Pos(DRUM_CX, DRUM_CY, LID_T - DRUM_SEAT / 2) * Cylinder(
        DRUM_D / 2 + 1.0, DRUM_SEAT)

    # Drum hold-down holes over the support posts (M4 clearance).
    for px, py in [(40, 132), (110, 132), (45, 145), (105, 145),
                   (75, 143)]:
        lid -= Pos(px, py, LID_T / 2) * Cylinder(2.2, LID_T + 2)
        lid -= Pos(px, py, LID_T - 1.2) * Cylinder(4.0, 2.5)   # csk

    # Vent slots on the exposed front strip (y < drum front ~y26).
    for i in range(7):
        vx = 35 + i * 13
        lid -= Pos(vx, 14, LID_T / 2) * Box(8, 3, LID_T + 1)

    # Buzzer bleed + front-rim pass-throughs continue into the lid lip:
    # (the front panel parts live in the tray walls — lid stays clear)

    # Lid corner screws.
    for cx, cy in [(10, 10), (CASE_W - 10, 10),
                   (10, CASE_D - 10), (CASE_W - 10, CASE_D - 10)]:
        lid -= Pos(cx, cy, LID_T / 2) * Cylinder(1.8, LID_T + 2)
        lid -= Pos(cx, cy, LID_T - 1.2) * Cylinder(3.4, 2.4)

    return CaseParts(tray, lid, CASE_H + LID_T)


if __name__ == "__main__":
    from build123d import export_step, export_stl
    c = make_case()
    for n, p in [("case_tray", c.tray), ("case_lid", c.lid)]:
        export_stl(p, f"export/{n}.stl")
        export_step(p, f"export/{n}.step")
    print("tray", c.tray.bounding_box().size,
          "| lid", c.lid.bounding_box().size)
