"""genlinks/extract.py - density field -> printable STL (pyvista/VTK path,
run with the fea venv python - skimage-free marching cubes).

  .../fea/.venv/bin/python genlinks/extract.py <field.npz> <out.stl> [vol_mm3]

Threshold selection: if vol_mm3 is given, bisect the isolevel until the
contour's measured volume hits the target (+/-4%); else the 0.5 level.
(The voxel domain over-counts thin-wall volume ~40% vs the true STL, so
'vf' targets are matched in true-volume space by bisection.)

Pipeline: vtkImageData (cell data = SIMP density) -> pad 1 void layer ->
contour -> Taubin smooth -> fill small holes -> keep largest + fragments
>8% of it -> STL. Units = mm (origin/pitch from the npz).
"""
import sys
import numpy as np
import pyvista as pv


def contour_vol(dense, origin, pitch, t):
    pad = np.zeros(np.array(dense.shape) + 2, dtype=np.float32)
    pad[1:-1, 1:-1, 1:-1] = dense
    img = pv.ImageData(dimensions=tuple(s + 1 for s in pad.shape),
                       spacing=(pitch,) * 3, origin=origin - pitch)
    img.cell_data["rho"] = pad.ravel(order="F")
    cont = img.cell_data_to_point_data().contour([t])
    return cont


def main(npz, stl, vol_target=None):
    d = np.load(npz)
    dense, origin, pitch = d["dense"], d["origin"], float(d["pitch"])
    x = dense[d["mask"]]
    if vol_target:
        lo, hi = float(np.quantile(x, 0.02)), float(np.quantile(x, 0.99))
        # vol decreases as thresh rises; ~6 bisection steps hit 4% band
        best, bd = None, 1e30
        for _ in range(8):
            t = 0.5 * (lo + hi)
            v = contour_vol(dense, origin, pitch, t).volume
            if abs(v - vol_target) < bd:
                best, bd = t, abs(v - vol_target)
            if v > vol_target:
                lo = t
            else:
                hi = t
        t = best
        print("vol-target %.0f mm3 -> thresh %.3f (est %s mm3)"
              % (vol_target, t, "?",))
    else:
        t = 0.5
    cont = contour_vol(dense, origin, pitch, t)
    print("contour: %d pts %d cells vol %.1f mm3"
          % (cont.n_points, cont.n_cells, cont.volume))
    sm = cont.smooth_taubin(n_iter=12, pass_band=0.08,
                            feature_smoothing=False)
    sm = sm.fill_holes(5.0)
    big = sm.split_bodies()
    if len(big) > 1:
        print("  %d fragments; keeping largest + any >8%% of it (vols %s)"
              % (len(big), [round(b.volume, 0) for b in big[:8]]))
        keep = big[0]
        for b in big[1:]:
            if b.volume > 0.08 * keep.volume:
                keep = keep.merge(b)
        sm = keep
    if not isinstance(sm, pv.PolyData):
        sm = sm.extract_surface()
    sm.save(stl)
    print("wrote %s  %.1f mm3  %.1f g" % (stl, sm.volume, sm.volume / 1000 * 1.31))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2],
         float(sys.argv[3]) if len(sys.argv) > 3 else None)
