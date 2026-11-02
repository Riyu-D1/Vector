"""verify/code/gen_cyc_step.py - build the cycloidal-stage contact-FEA solids
as STEP files for one crank phase angle th (deg).

Assembly (act2 module frame, ap.py): the two cycloid discs posed at crank th:
  disc1 centre E*(cos th, sin th), disc2 centre -E*(cos th, sin th), both
  rotated -th/N about their own centre (same kinematics as cyc.mesh_clearance).
  Ring pins (41 x d3 at R=23.5, z 33.5..43.5) and output pins (6 x d3 at
  PCD 33, z 34..46) are fixed to the housing/carrier frame - they do NOT move
  with th (output held, ring grounded).

Writes:  out/step/cyc_th<tag>/disc1.step disc2.step ringpins.step outpins.step

Run:  $PY gen_cyc_step.py <th_deg>   (from verify/code)
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
VER = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(VER, "cad", "act2"))
sys.path.insert(0, os.path.join(VER, "cad", "knuckle"))

from build123d import import_step, Pos, Rot, Solid, Plane, Compound, export_step
import ap


def pol(r, a):
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))


def load_parts():
    """disc1/disc2 solids (module frame, th=0) from the tested-code STEP export."""
    d1 = import_step(os.path.join(HERE, "..", "out", "step", "disc1.step"))
    d2 = import_step(os.path.join(HERE, "..", "out", "step", "disc2.step"))
    return d1, d2


def repose(disc, cx0, cx1, cy0, cy1, z0, drot):
    """Move a disc centred at (cx0, cy0) to (cx1, cy1), rotating drot deg about Z."""
    return Pos(cx1, cy1, z0) * Rot(0, 0, drot) * Pos(-cx0, -cy0, -z0) * disc


def ring_pins():
    s = []
    for k in range(41):
        x, y = pol(23.5, 360.0 * k / 41)
        s.append(Solid.make_cylinder(1.5, 10.0,
                 Plane(origin=(x, y, 33.5), z_dir=(0, 0, 1))))
    return Compound(children=s)


def out_pins():
    s = []
    for k in range(ap.OUT_PIN_N):
        x, y = pol(ap.OUT_PIN_PCD / 2, ap.OUT_PIN_ANG0 + 60 * k)
        s.append(Solid.make_cylinder(1.5, 12.0,
                 Plane(origin=(x, y, 34.0), z_dir=(0, 0, 1))))
    return Compound(children=s)


def main(th):
    N, NP, R, RP, E = (ap.GEAR[ap.RATIO][k] for k in ("N", "R", "RP", "E")), None, None, None, None
    N = ap.GEAR[ap.RATIO]["N"]; E = ap.GEAR[ap.RATIO]["E"]
    drot = -th / N                                    # disc rotation about own centre
    cx, cy = E * math.cos(math.radians(th)), E * math.sin(math.radians(th))
    tag = ("%g" % th).replace(".", "p").replace("-", "m")
    outd = os.path.join(HERE, "..", "out", "step", "cyc_th" + tag)
    os.makedirs(outd, exist_ok=True)
    d1, d2 = load_parts()
    # disc1 as-built: centre (+E, 0), z0 = Z_DISC1[0]; disc2: centre (-E, 0), Z_DISC2[0]
    export_step(repose(d1, E, cx, 0.0, cy, ap.Z_DISC1[0], drot),
                os.path.join(outd, "disc1.step"))
    export_step(repose(d2, -E, -cx, 0.0, -cy, ap.Z_DISC2[0], drot),
                os.path.join(outd, "disc2.step"))
    export_step(ring_pins(), os.path.join(outd, "ringpins.step"))
    export_step(out_pins(), os.path.join(outd, "outpins.step"))
    print("wrote %s (th=%g drot=%.4f c=(%.3f, %.3f))" % (outd, th, drot, cx, cy))


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.0)
