"""Cycloidal disc profile generator (pin-mesh, offset-epitrochoid).

The disc profile is the base curtate epitrochoid offset inward by the ring
pin radius rr along the curve normal.  With Rp = 29, e = 1.5, rr = 3.0,
Np = 16 this reproduces the Berkeley Humanoid Lite `5010_profile.dxf`
(extracted from the public Onshape document) to 0.007 mm RMS — see
check.py for the verification routine.

Standard derivation: relative to the disc, each ring pin centre traces the
curtate epitrochoid
    x0(t) = Rp*cos(t) - e*cos(Np*t)
    y0(t) = -Rp*sin(t) + e*sin(Np*t)      (Np = Z = lobes + 1)
and the disc flank is the envelope of the pin circles, i.e. the base curve
offset by -rr along the inward normal.
"""

import numpy as np

from params import GearSpec, P


def base_curve(t, Rp, e, Np):
    """Pin-centre locus in disc coordinates (un-offset epitrochoid)."""
    x = Rp * np.cos(t) - e * np.cos(Np * t)
    y = -Rp * np.sin(t) + e * np.sin(Np * t)
    return x, y


def disc_profile(n=2000, gear: GearSpec = P.gear):
    """Disc outline as (x, y) arrays, centred on the disc centre."""
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    x, y = base_curve(t, gear.pin_pitch_r, gear.eccentricity, gear.ring_pins)
    dx = np.gradient(x, t)
    dy = np.gradient(y, t)
    L = np.hypot(dx, dy)
    nx, ny = -dy / L, dx / L            # normal candidates
    # choose the inward direction (toward curve centroid)
    cx, cy = x.mean(), y.mean()
    s = np.sign((cx - x) * nx + (cy - y) * ny)
    rr = gear.pin_radius + gear.clearance  # FDM clearance added on the flank
    xo = x + s * rr * nx
    yo = y + s * rr * ny
    return xo, yo


def disc_profile_design(n=2000, gear: GearSpec = P.gear):
    """Disc outline WITHOUT the FDM flank clearance (theoretical)."""
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    x, y = base_curve(t, gear.pin_pitch_r, gear.eccentricity, gear.ring_pins)
    dx = np.gradient(x, t)
    dy = np.gradient(y, t)
    L = np.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    cx, cy = x.mean(), y.mean()
    s = np.sign((cx - x) * nx + (cy - y) * ny)
    return x + s * gear.pin_radius * nx, y + s * gear.pin_radius * ny


def pin_centres(gear: GearSpec = P.gear):
    """(x, y) of the Z ring pins in housing coordinates."""
    a = np.linspace(0.0, 2.0 * np.pi, gear.ring_pins, endpoint=False)
    return gear.pin_pitch_r * np.cos(a), gear.pin_pitch_r * np.sin(a)


def disc_pose(angle_in, gear: GearSpec = P.gear):
    """Disc centre offset + rotation for a given input-shaft angle (rad).

    Returns (ex, ey, phi): the wobble centre position and the disc spin angle.
    Disc spin = -angle_in / ratio * (Np-1) ... for a fixed ring, one input rev
    rotates the disc by -1/lobes rev (backdriving sign convention).
    """
    e = gear.eccentricity
    ex, ey = e * np.cos(angle_in), e * np.sin(angle_in)
    phi = -angle_in / gear.disc_lobes      # 15:1, opposite sense
    return ex, ey, phi


def pin_contact(gear: GearSpec = P.gear, n=360):
    """Clearance between disc flank and each ring pin over one input rev.

    Returns (min_gap, max_contact_depth): min gap >= 0 means no interference;
    negative values would be pin biting into the flank.
    """
    xs, ys = disc_profile_design(n * 4, gear)
    px, py = pin_centres(gear)
    worst_min = np.inf
    for k in range(n):
        a = 2 * np.pi * k / n
        ex, ey, phi = disc_pose(a, gear)
        c, s = np.cos(phi), np.sin(phi)
        xd = ex + xs * c - ys * s
        yd = ey + xs * s + ys * c
        # distance of each pin centre to the disc polygon -> min over pins
        d = np.inf
        for i in range(gear.ring_pins):
            dd = np.hypot(xd - px[i], yd - py[i]).min()
            d = min(d, dd)
        worst_min = min(worst_min, d - gear.pin_radius)
    return worst_min


if __name__ == "__main__":
    import sys
    xs, ys = disc_profile(400)
    r = np.hypot(xs, ys)
    print(f"disc profile: rmin={r.min():.3f} rmax={r.max():.3f} (expect 24.5/27.5)")
    if "-v" in sys.argv:
        print("pin contact min gap:", round(pin_contact(P.gear, 120), 4), "mm")
