"""lighten/l_census.py - D9 free-material census per candidate plate.

Voxelises each stock STL at 0.5 mm and counts how much solid sits OUTSIDE
the keep-out zones (bolt/bearing/horn lands + joint interfaces). This is
the upper bound on what windows/pockets could remove; the FEM decides the
real cut.

Keep-outs (posed STL frame, same predicates as genlinks/gen_parts.spec):
  upper_out/upper_back: r<33 around J2 or J3 (ring lands + M3 PCD r25).
  fore_l2/fore_r2:      x<33.6 (J3 dogleg overlap) | r<42 around J4
                        + 5 mm land around every detected hole axis.
  dogleg_l/r:           5 mm land around every detected hole axis (the
                        plate is one big interface - nothing else known).

Hole axes are auto-detected: cells in the thin direction's occupancy map
that are void but fully enclosed by material (a through-hole).

Run:  python3 lighten/l_census.py           (from the worktree root)
"""
import os, sys, math
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
A2B = os.path.join(ROOT, "cad", "arm2b", "out")

J2 = np.array([-20.0, 0.0, 143.5])
J3 = np.array([-20.0, 0.0, 270.2])
J4 = np.array([96.4, 0.0, 216.2])
RHO, INFILL = 1.27e-3, 0.6          # repo mass convention (g/mm3, print factor)


def rxz(p, j):
    return np.hypot(p[..., 0] - j[0], p[..., 2] - j[2])


def hole_axes(m, thin_axis=1):
    """Detect through-hole axis positions on a thin plate (occupied 2D
    projection, void cells enclosed by material -> hole centre)."""
    vg = m.voxelized(0.5).fill()
    mat = vg.matrix
    occ = mat.any(axis=thin_axis)                     # 2D occupancy
    # flood fill "outside" from the border in the 2D map
    from scipy import ndimage
    lab, _ = ndimage.label(~occ)
    border = set(np.unique(np.concatenate(
        [lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])))
    enclosed = (lab > 0) & ~np.isin(lab, list(border))
    axes = []                                     # (centre3, equiv_radius)
    other = [i for i in range(3) if i != thin_axis]
    org = np.asarray(vg.translation)
    pitch = float(np.asarray(vg.pitch).ravel()[0])
    hlab, nh = ndimage.label(enclosed)
    for h in range(1, nh + 1):
        cells = np.argwhere(hlab == h)
        cc = cells.mean(axis=0)
        p = np.zeros(3)
        p[other[0]] = org[other[0]] + (cc[0] + 0.5) * pitch
        p[other[1]] = org[other[1]] + (cc[1] + 0.5) * pitch
        r = math.sqrt(len(cells) * pitch * pitch / math.pi)
        axes.append((p, r))
    return axes, vg


def census(name, keep_fn=None, hole_r=5.0):
    m = trimesh.load_mesh(os.path.join(A2B, name + ".stl"), force="mesh")
    m.merge_vertices()
    axes, vg = hole_axes(m)
    mat = vg.matrix
    cents = np.asarray(vg.as_boxes().centers) if False else None
    idx = np.argwhere(mat)
    org = np.asarray(vg.translation)
    pitch = float(np.asarray(vg.pitch).ravel()[0])
    pts = org + (idx + 0.5) * pitch
    free = np.ones(len(pts), bool)
    if keep_fn is not None:
        free &= ~keep_fn(pts)
    for a, r in axes:
        d = np.hypot(pts[:, 0] - a[0], pts[:, 2] - a[2])
        free &= d > r + 5.0                       # hole edge + 5 mm land
    vol = float(m.volume)
    fv = free.sum() * pitch ** 3
    print("%-10s vol %6.1f cm3 | holes detected %2d | free %5.1f cm3 "
          "(%4.1f%%) -> <= %4.1f g print" %
          (name, vol / 1000, len(axes), fv / 1000, 100 * fv / vol,
           fv * RHO * INFILL))
    return fv


print("candidate | stock cm3 | hole axes | free cm3 (%%) -> max printed g")
census("upper_out", lambda p: (rxz(p, J2) < 33) | (rxz(p, J3) < 33))
census("upper_back", lambda p: (rxz(p, J2) < 33) | (rxz(p, J3) < 33))
census("fore_l2", lambda p: (p[:, 0] < 33.6) | (rxz(p, J4) < 42))
census("fore_r2", lambda p: (p[:, 0] < 33.6) | (rxz(p, J4) < 42))
census("dogleg_l", lambda p: rxz(p, J3) < 30)
census("dogleg_r", lambda p: rxz(p, J3) < 30)
