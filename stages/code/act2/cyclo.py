"""cad/act2/cyclo.py - cycloid disc profile + clearance check (numpy only).
Copied verbatim from ~/Vector/stages/code/act2/. Do not edit.
Profile (pin-circle radius R, pin radius rp, eccentricity e, N ring pins,
lobes N-1, clearance d added to rp), t = 0..2pi:
  psi = atan2(sin((1-N)t), R/(e N) - cos((1-N)t))
  x = R cos t - (rp+d) cos(t+psi) - e cos(N t)
  y = -R sin t + (rp+d) sin(t+psi) + e sin(N t)"""
import math
import numpy as np

def disc_profile(R, rp, e, n_pins, d_mod, n=2160):
    """Epitrochoid disc outline, disc frame (disc centre = origin).
    R pin-circle radius, rp pin radius, e eccentricity, n_pins ring pins
    (lobes = n_pins-1), d_mod equidistant clearance added to rp. Returns (n,2)."""
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    r = rp + d_mod
    psi = np.arctan2(np.sin((1 - n_pins) * t), R / (e * n_pins) - np.cos((1 - n_pins) * t))
    x = R * np.cos(t) - r * np.cos(t + psi) - e * np.cos(n_pins * t)
    y = -R * np.sin(t) + r * np.sin(t + psi) + e * np.sin(n_pins * t)
    return np.column_stack([x, y])

def _seg_dist(p, a, b):
    ab = b - a
    tt = np.clip(((p - a) * ab).sum(1) / (ab * ab).sum(1), 0, 1)
    q = a + ab * tt[:, None]
    return np.sqrt(((p - q) ** 2).sum(1)).min()

def _inside(p, poly):
    x, y = p; xs, ys = poly[:, 0], poly[:, 1]
    xs2, ys2 = np.roll(xs, -1), np.roll(ys, -1)
    c = ((ys > y) != (ys2 > y)) & (x < (xs2 - xs) * (y - ys) / (ys2 - ys + 1e-30) + xs)
    return bool(c.sum() % 2)

def min_clearance(R, rp, e, n_pins, d_mod, steps=360):
    """Min gap (mm) between disc outline and ring-pin surfaces over one full
    input turn, sampled at `steps` positions. Negative = interference."""
    prof = disc_profile(R, rp, e, n_pins, d_mod)
    a, b = prof, np.roll(prof, -1, axis=0)
    lobes = n_pins - 1
    pins = [(R * math.cos(2 * math.pi * k / n_pins), R * math.sin(2 * math.pi * k / n_pins)) for k in range(n_pins)]
    worst = 1e9
    for i in range(steps):
        th = 2 * math.pi * i / steps
        ph = -th / lobes
        c, s = math.cos(-ph), math.sin(-ph)
        for px, py in pins:
            qx, qy = px - e * math.cos(th), py - e * math.sin(th)
            q = np.array([c * qx - s * qy, s * qx + c * qy])   # pin centre in disc frame
            d = _seg_dist(q[None, :], a, b) - rp
            if _inside(q, prof):
                d = -d - 2 * rp
            worst = min(worst, d)
    return worst
