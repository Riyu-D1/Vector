"""cad/act2/check_act.py - actuator checks that gate.py cannot do.
Run from cad/act2 after build_act.py:  python check_act.py
Copied verbatim. Imports ../knuckle/gate.py as a library (read-only). Prints one line per check
and CHECK PASS or CHECK FAIL (exit code 0 / 1)."""
import math
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "knuckle"))
import gate  # noqa: E402
import ap  # noqa: E402
from cyclo import min_clearance  # noqa: E402

OUT = os.path.join(HERE, "out")
OTHERS = ["act_cam", "act_disc", "act_out", "act_cap",
          "buy_motor", "buy_ringpins", "buy_outpins", "buy_bearings"]
ok = True


def line(name, good, text):
    global ok
    ok &= bool(good)
    print(f"{name}: {text} {'PASS' if good else 'FAIL'}")


# 1. cycloid disc vs ring pins over one full input turn, 360 samples
c = min_clearance(ap.PIN_R, ap.RP, ap.E, ap.N_PINS, ap.D_MOD, steps=360)
line("CYCLO", c >= 0.1, f"ratio {ap.RATIO}:1 min disc-pin clearance {c:.3f} mm (need >= 0.100)")
# 2. output pins vs disc holes (exact: hole r - pin r - e)
oc = ap.DISC_HOLE_D / 2 - ap.OUTPIN_D / 2 - ap.E
line("OUTPIN", oc >= 0.1, f"min output-pin clearance {oc:.3f} mm (need >= 0.100)")
# 3. envelope
line("LENGTH", ap.LENGTH <= 55.0, f"{ap.LENGTH:.1f} mm (need <= 55.0)")
line("OD", ap.OD <= 57.0, f"{ap.OD:.1f} mm (need <= 57.0)")
# 4. ESC fit (information + rule): B-G431B-ESC1 30 x 41 mm
diag = math.hypot(30.0, 41.0)
print(f"ESC: diagonal {diag:.1f} mm > motor bore {ap.MOT_BORE_D:.1f} mm -> ESC mounts on the link, not in the actuator")
# 5. act_body: watertight, min wall outside the ring-pin groove band
m = gate.load(os.path.join(OUT, "act_body.stl"))
line("BODY_WATERTIGHT", m.is_watertight, f"watertight={m.is_watertight}")
pts, fi = trimesh.sample.sample_surface(m, 6000, seed=1)
nrm = m.face_normals[fi]
r = np.hypot(pts[:, 0], pts[:, 1])
band = (r < ap.PIN_R + ap.GROOVE_D / 2 + 0.05) & (r > ap.RING_BORE_R - 0.05) & \
       (pts[:, 2] > ap.Z_GROOVE - 0.05)
o = pts[~band] - nrm[~band] * 0.01
locs, ri, _ = m.ray.intersects_location(o, -nrm[~band], multiple_hits=False)
d = np.linalg.norm(locs - o[ri], axis=1)
mw = float(np.percentile(d, gate.WALL_PCT))
line("BODY_MINWALL", mw >= gate.MIN_WALL,
     f"{mw:.2f} mm outside pin-groove band (need >= {gate.MIN_WALL}); band excluded = {int(band.sum())} of 6000 samples")
# 6. act_body vs every other part (manifold boolean, same limit as gate.py)
mb = gate.to_manifold(m)
for n in OTHERS:
    v = float((mb ^ gate.to_manifold(gate.load(os.path.join(OUT, n + ".stl")))).volume())
    line(f"INTERF act_body x {n}", v <= gate.INTERF_MAX, f"{v:.2f} mm3 (need <= {gate.INTERF_MAX})")
print("CHECK PASS" if ok else "CHECK FAIL")
sys.exit(0 if ok else 1)
