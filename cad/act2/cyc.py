"""cad/act2/cyc.py - cycloid disc maths + gear gates (numpy only). Copied verbatim.
Usage (from cad/act2):  python cyc.py [40|50]   (default ap.RATIO)"""
import math
import sys

import numpy as np

import ap


def gear(ratio=None):
    """Parameter set for the chosen ratio: (N lobes, NP pins, R, RP, E)."""
    g = ap.GEAR[ratio or ap.RATIO]
    return g["N"], g["N"] + 1, g["R"], g["RP"], g["E"]


def profile(ratio=None, m=4000, clr=None):
    """Disc outline in the DISC frame, (m, 2) array, closed (first != last).
    Equidistant of the epitrochoid, offset by RP + CLR_TOOTH:
      psi(t) = atan2(sin(N t), R/(E NP) - cos(N t))
      x(t) = R cos t - E cos(NP t) - r cos(t - psi)
      y(t) = R sin t - E sin(NP t) - r sin(t - psi)
    with r = RP + CLR_TOOTH and t in [0, 2 pi)."""
    N, NP, R, RP, E = gear(ratio)
    r = RP + (ap.CLR_TOOTH if clr is None else clr)
    t = np.linspace(0.0, 2 * math.pi, m, endpoint=False)
    psi = np.arctan2(np.sin(N * t), R / (E * NP) - np.cos(N * t))
    x = R * np.cos(t) - E * np.cos(NP * t) - r * np.cos(t - psi)
    y = R * np.sin(t) - E * np.sin(NP * t) - r * np.sin(t - psi)
    return np.column_stack([x, y])


def seg_dist(p, poly):
    """Min distance from points p (k,2) to closed polyline poly (m,2)."""
    a = poly
    b = np.roll(poly, -1, axis=0)
    ab = b - a
    L2 = (ab ** 2).sum(1)
    out = np.empty(len(p))
    for i, q in enumerate(p):
        t = np.clip(((q - a) * ab).sum(1) / L2, 0, 1)
        d = a + ab * t[:, None] - q
        out[i] = np.sqrt((d ** 2).sum(1)).min()
    return out


def inside(p, poly):
    """Even-odd point-in-polygon for points p (k,2)."""
    x, y = p[:, 0][:, None], p[:, 1][:, None]
    x0, y0 = poly[:, 0][None, :], poly[:, 1][None, :]
    x1, y1 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
    c = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-30) + x0)
    return (c.sum(1) % 2) == 1


def disc_outline(ratio=None, second=False, m=4000):
    """Disc 1 = profile(); disc 2 (on the -E cam) = the same outline turned
    by +180/N deg about its own centre (half a lobe); its output-pin holes
    are NOT turned."""
    N = gear(ratio)[0]
    p = profile(ratio, m=m)
    if not second:
        return p
    a = math.pi / N
    return p @ np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])


def mesh_clearance(ratio=None, steps=360, second=False):
    """Simulate: ring pins fixed, crank angle th (input), disc centre at
    E(cos th, sin th) (disc 2: -E(cos th, sin th)), both discs turn -th/N.
    Returns (min, max-of-per-step-min) clearance pin-surface -> disc outline
    over `steps` crank positions."""
    N, NP, R, RP, E = gear(ratio)
    poly = disc_outline(ratio, second)
    sg = -1.0 if second else 1.0
    k = np.arange(NP)
    pins = np.column_stack([R * np.cos(2 * math.pi * k / NP), R * np.sin(2 * math.pi * k / NP)])
    mins = []
    for s in range(steps):
        th = 2 * math.pi * s / steps
        c = sg * np.array([E * math.cos(th), E * math.sin(th)])
        a = -th / N
        ca, sa = math.cos(-a), math.sin(-a)
        q = (pins - c) @ np.array([[ca, sa], [-sa, ca]])   # pins into disc frame
        d = seg_dist(q, poly) - RP
        d[inside(q, poly)] *= -1.0                         # pin centre inside disc = collision
        mins.append(d.min())
    mins = np.array(mins)
    return float(mins.min()), float(mins.max())


def ratio_check(ratio=None):
    """Output (carrier) turns per input turn, from the kinematics, ring fixed.
    Disc turns -1/N per crank turn; output pins follow the disc."""
    N, NP, R, RP, E = gear(ratio)
    return N / (NP - N)


def checks(ratio=None):
    N, NP, R, RP, E = gear(ratio)
    k1 = E * NP / R                                   # shortening coefficient, must be < 1
    pitch = 2 * R * math.sin(math.pi / NP)            # pin centre spacing
    gap = pitch - 2 * RP                              # steel between pins
    poly = profile(ratio, clr=0.0)
    rr = np.hypot(poly[:, 0], poly[:, 1])
    # radius of curvature of the theoretical curve (pin-centre path, r = 0),
    # convex parts only (signed curvature > 0 for this CCW curve)
    th = profile(ratio, m=20000, clr=-RP)
    d1 = (np.roll(th, -1, 0) - np.roll(th, 1, 0)) / 2
    d2 = np.roll(th, -1, 0) - 2 * th + np.roll(th, 1, 0)
    kap = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) / np.hypot(d1[:, 0], d1[:, 1]) ** 3
    rho_min = float(1.0 / kap.max()) if kap.max() > 0 else 1e9
    hole_d = ap.OUT_PIN_D + 2 * E + 2 * ap.CLR_TOOTH
    return dict(N=N, NP=NP, R=R, RP=RP, E=E, k1=k1, pitch=pitch, gap=gap,
                r_min=float(rr.min()), r_max=float(rr.max()), rho_min=rho_min, hole_d=hole_d, e_lim=0.5 * RP)


def main(argv):
    ratio = int(argv[0]) if argv else ap.RATIO
    c = checks(ratio)
    ok = True
    print(f"RATIO {ratio_check(ratio):.1f}")
    for key in ("N", "NP", "R", "RP", "E"):
        print(f"{key} = {c[key]}")
    t = [("K1 e*NP/R < 0.95", c["k1"], c["k1"] < 0.95),
         ("E <= 0.5*RP (e_lim)", c["E"], c["E"] <= c["e_lim"] + 1e-9),
         ("pin gap >= 0.3", c["gap"], c["gap"] >= 0.3),
         ("rho_min > RP + CLR_TOOTH (no undercut)", c["rho_min"], c["rho_min"] > c["RP"] + ap.CLR_TOOTH),
         ("disc r_min - hole outer >= 1.6", c["r_min"] - (ap.OUT_PIN_PCD / 2 + c["hole_d"] / 2),
          c["r_min"] - (ap.OUT_PIN_PCD / 2 + c["hole_d"] / 2) >= 1.6)]
    for disc, sec in (("disc1", False), ("disc2", True)):
        lo, hi = mesh_clearance(ratio, second=sec)
        t.append((f"{disc} mesh clearance min >= 0.10 (360 steps)", lo, lo >= 0.10))
        t.append((f"{disc} mesh clearance worst-step <= 0.25", hi, hi <= 0.25))
    for name, v, good in t:
        ok &= bool(good)
        print(f"{name}: {v:.3f} {'OK' if good else 'BAD'}")
    print(f"disc r_min {c['r_min']:.3f} r_max {c['r_max']:.3f}  out-pin hole d {c['hole_d']:.2f}  pin pitch {c['pitch']:.3f}")
    print("CYC PASS" if ok else "CYC FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
