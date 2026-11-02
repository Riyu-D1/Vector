"""disc_dxf.py -- write upload-ready 2D DXFs for the D4 cut-metal parts.

Emits minimal ASCII DXF (entities: POLYLINE/VERTEX + CIRCLE, units mm) for:

  dxf/disc1.dxf          cycloidal disc 1 outline + bore + 6 output-pin holes
  dxf/disc2.dxf          cycloidal disc 2 (180-deg phase-shifted outline)
  dxf/output_pin_plate.dxf  optional flat plate carrying the 6 output pins
                            (carrier plate pattern; the carrier stays printed
                            in the D4 pick - supplied so a metal pin plate
                            can be cut if wear shows in service)

Usage:  $PY disc_dxf.py            -> writes into cyclo4/dxf/
"""

import math
import os

import ap
import cyc

FMT = "{:.4f}"


def _pol(r, a):
    return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))


def _dxf_head():
    return (
        "0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
        "0\nSECTION\n2\nENTITIES\n"
    )


def _circle(x, y, r):
    return (
        "0\nCIRCLE\n8\nCUT\n10\n%s\n20\n%s\n40\n%s\n"
        % (FMT.format(x), FMT.format(y), FMT.format(r))
    )


def _polyline(pts, closed=True):
    s = "0\nPOLYLINE\n8\nCUT\n66\n1\n70\n%d\n" % (1 if closed else 0)
    for x, y in pts:
        s += "0\nVERTEX\n8\nCUT\n10\n%s\n20\n%s\n" % (FMT.format(x), FMT.format(y))
    return s + "0\nSEQEND\n"


def _tail():
    return "0\nENDSEC\n0\nEOF\n"


def disc_dxf(path, second):
    N, NP, R, RP, E = cyc.gear()
    pts = cyc.disc_outline(second=second, m=ap.DISC_M)
    d = _dxf_head() + _polyline(pts) + _circle(0, 0, ap.DISC_BORE / 2)
    hole_r = (ap.OUT_PIN_D + 2 * E + 2 * ap.CLR_OUT) / 2
    for k in range(ap.OUT_PIN_N):
        x, y = _pol(ap.OUT_PIN_PCD / 2, ap.OUT_PIN_ANG0 + 60 * k)
        d += _circle(x, y, hole_r)
    with open(path, "w") as f:
        f.write(d + _tail())
    return path


def pin_plate_dxf(path):
    """Carrier plate pattern, same hole set as p_act.carrier()."""
    d = _dxf_head()
    d += _circle(0, 0, ap.PLATE_D / 2)                    # outline = carrier plate OD
    for k in range(ap.OUT_PIN_N):                         # 6 press holes for the 3 mm pins
        x, y = _pol(ap.OUT_PIN_PCD / 2, ap.OUT_PIN_ANG0 + 60 * k)
        d += _circle(x, y, ap.OUT_PIN_PRESS / 2)
    for a in ap.OUT_M3_ANG:                               # 3x M3 insert holes
        x, y = _pol(ap.OUT_M3_PCD / 2, a)
        d += _circle(x, y, ap.INS_M3_D / 2)
    for a in ap.OUT_DOWEL_ANG:                            # 3x dowel holes
        x, y = _pol(ap.OUT_DOWEL_PCD / 2, a)
        d += _circle(x, y, ap.OUT_DOWEL_HOLE / 2)
    with open(path, "w") as f:
        f.write(d + _tail())
    return path


def main():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dxf")
    os.makedirs(d, exist_ok=True)
    out = [
        disc_dxf(os.path.join(d, "disc1.dxf"), False),
        disc_dxf(os.path.join(d, "disc2.dxf"), True),
        pin_plate_dxf(os.path.join(d, "output_pin_plate.dxf")),
    ]
    for p in out:
        print("wrote", p, "(%d bytes)" % os.path.getsize(p))


if __name__ == "__main__":
    main()
