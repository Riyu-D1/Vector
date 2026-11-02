"""verify/code/gen_joint_step.py - build the bolted whole-joint solids as STEP
files in the act2 MODULE frame (z = joint axis, module z0 = housing back face).

World->module map: module z -> world -Y, x -> world x, y -> world z, with the
module origin at world y = 23.4 (ACT_BACK_Y):  mod = Rot(-90,0,0)*Pos(-Jx,-23.4,-Jz)*world

J2 stack (Jx=-20):  out side = link1 clip (world y<0 face), back side =
upper_back clip; J3 stack (Jx=106.7): out side = dogleg_l clip (forearm),
back side = upper_back clip at J3 end.

Parts (all from tested-code STEP exports / param sources):
  housing, carrier, out_flange       - act2 module frame as-built (cad3 build)
  dowels x3                        - d4, carrier top z52.4 -3.1 .. +proud 2.3
  front_spacer                     - arm2 front_spacer(J2|J3) rest->module
  link clip                        - arm2 link1 clip (J2) / dogleg_l clip (J3)
  back_spacer                      - cad3/out D2 part rest->module
  upper clip                       - arm2 upper_back clip at the joint
The D2 flange/spring is excluded - the spring path is a parallel assist only
(~0.34 N.m at x2), so bolt loads here are upper bounds (stated in STATUS).

Run:  $PY gen_joint_step.py J2 | J3
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
VER = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(VER, "cad", "act2"))
sys.path.insert(0, os.path.join(VER, "cad", "arm2"))
sys.path.insert(0, os.path.join(VER, "cad", "knuckle"))

from build123d import (import_step, Pos, Rot, Solid, Plane, Compound,
                       export_step, Box)
import ap
import ap2 as P
import p_arm2 as PA


def to_mod(s, jx, jz):
    return Rot(-90, 0, 0) * Pos(-jx, -23.4, -jz) * s


def clip(s, x0, x1, y0, y1, z0, z1):
    return s & Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * \
        Box(x1 - x0, y1 - y0, z1 - z0)


def dowels():
    s = []
    for a in ap.OUT_DOWEL_ANG:
        x, y = ap.OUT_DOWEL_PCD / 2 * math.cos(math.radians(a)), \
            ap.OUT_DOWEL_PCD / 2 * math.sin(math.radians(a))
        s.append(Solid.make_cylinder(ap.OUT_DOWEL_D / 2,
                 ap.OUT_DOWEL_DEPTH + 2.6 + ap.OUT_DOWEL_PROUD,
                 Plane(origin=(x, y, ap.Z_SPIGOT[1] - ap.OUT_DOWEL_DEPTH),
                       z_dir=(0, 0, 1))))
    return Compound(children=s)


def main(which):
    JX, JZ = (P.J2_XZ if which == "J2" else P.J3_XZ)
    outd = os.path.join(HERE, "..", "out", "step", "jt_" + which.lower())
    os.makedirs(outd, exist_ok=True)
    src = os.path.join(HERE, "..", "out", "step")
    d2 = os.path.join(VER, "cad3", "out")

    for p in ("housing", "carrier", "out_flange"):
        s = import_step(os.path.join(src, p + ".step"))
        export_step(s, os.path.join(outd, p + ".step"))
    export_step(dowels(), os.path.join(outd, "dowels.step"))

    # back_spacer (D2, rest frame) -> module
    bs = import_step(os.path.join(d2, "back_spacer_" + which.lower() + ".step"))
    export_step(to_mod(bs, JX, JZ), os.path.join(outd, "back_spacer.step"))

    # front_spacer (arm2, rest frame) -> module; 'fo' group carries sx(DX_UP)
    fs = PA.front_spacer(which.upper())
    if which == "J3":
        fs = fs.moved(__import__("build123d").Location((P.DX_UP, 0, 0)))
    export_step(to_mod(fs, JX, JZ), os.path.join(outd, "front_spacer.step"))

    # upper_back clip at the joint (rest frame) -> module
    ub = PA.upper_back()
    ubc = clip(ub, JX - 25.0, JX + 55.0, -60.0, 60.0, JZ - 60.0, JZ + 60.0)
    export_step(to_mod(ubc, JX, JZ), os.path.join(outd, "upper_clip.step"))

    # link-side clip: J2 -> link1 plates around the joint; J3 -> dogleg_l
    if which == "J2":
        lk = PA.rebot("03_Link1")
        lc = clip(lk, JX - 30.0, JX + 30.0, -60.0, 60.0, JZ - 30.0, JZ + 30.0)
    else:
        dg = PA.rebot("02_Lower_Upper_Link_L")
        dgm = dg.moved(__import__("build123d").Location((P.DX_UP, P.DOGLEG_DY["L"], 0)))
        lc = clip(dgm, JX - 30.0, JX + 30.0, -60.0, 60.0, JZ - 30.0, JZ + 30.0)
    export_step(to_mod(lc, JX, JZ), os.path.join(outd, "link_clip.step"))
    print("wrote %s" % outd)


if __name__ == "__main__":
    main(sys.argv[1].upper())
