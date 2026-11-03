"""genlinks/report.py - per-candidate numbers for STATUS (D8).

For each <part> with out/<part>_gen.stl:
  - solid-equivalent mass before/after (volume x 1.31 g/cc)
  - estimated printed mass [U]: 1.8 mm wall shell (<=60% vol) + 40% infill
  - interface preservation: enclosed-void (hole/bore) census inside the keep
    zones on source vs result (XZ projection, 0.5 mm voxels): count/position
  - keep-zone solid occupancy: result voxels satisfying the keep predicate
    vs the optimizer's keep count
  - overhang % for the declared print 'up'

Run:  python3 genlinks/report.py <part> [...]
"""
import os, sys, json, math
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "out")
import gen_common as G
import gen_parts as GP
from scipy import ndimage

RHO = 1.31          # g/cc PETG-CF


def printed_mass_g(mesh):
    """[U] walls 1.8 mm equivalent shell (<=60% of vol) + 40% infill core."""
    vol = abs(mesh.volume)
    shell = min(mesh.area * 1.8, 0.60 * vol)
    return (shell + 0.40 * max(vol - shell, 0.0)) / 1000.0 * RHO


def detect_voids(mesh, keep_pred, pitch=0.5):
    """Enclosed voids of the solid in XZ occupancy (holes/bores) whose centre
    satisfies keep_pred. Returns [(cx, cz, r_mm)]."""
    vg = mesh.voxelized(pitch).fill()
    mat = vg.matrix
    ox = np.asarray(vg.translation)
    occ = mat.any(axis=1)                    # XZ projection (plates thin in y)
    lab, n = ndimage.label(~occ)
    border = np.unique(np.concatenate(
        [lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))
    out = []
    for k in range(1, n + 1):
        if k in border:
            continue
        ii = np.argwhere(lab == k)
        if len(ii) < 4:
            continue
        c = np.array([ox[0] + pitch * (ii[:, 0].mean() + 0.5),
                      0.0,
                      ox[2] + pitch * (ii[:, 1].mean() + 0.5)])
        r = pitch * math.sqrt(len(ii) / math.pi)
        if keep_pred(c.reshape(1, 3))[0]:
            out.append((float(c[0]), float(c[2]), float(r)))
    return out


def main(part):
    src = trimesh.load_mesh(os.path.join(OUT, part + ".stl"), force="mesh")
    gen = trimesh.load_mesh(os.path.join(OUT, part + "_gen.stl"), force="mesh")
    S = GP.spec(part)
    keep = S["keep"]
    v_src, v_gen = abs(src.volume), abs(gen.volume)
    oh, atot, frac = G.overhang_scan(gen, S["up"])
    # keep-zone occupancy: result voxels (same pitch) satisfying keep pred
    matrix, origin, _ = G.voxelize(os.path.join(OUT, part + ".stl"), S["pitch"])
    _, cents = G.elem_centroids(matrix, origin, S["pitch"])
    ko = int(keep(cents).sum())
    vg = gen.voxelized(S["pitch"]).fill()
    gc = np.asarray(vg.translation) + S["pitch"] * (np.argwhere(vg.matrix) + 0.5)
    kg = int(keep(gc).sum())
    # hole census inside keep zones on both meshes
    hs = detect_voids(src, keep)
    hg = detect_voids(gen, keep)
    pairs = []
    for cx, cz, r in hs:
        d = [math.hypot(cx - a, cz - b) for a, b, _ in hg]
        j = int(np.argmin(d)) if d else -1
        if j >= 0 and d[j] < 3.0:
            a, b, rg = hg[j]
            pairs.append(dict(src=[round(cx, 1), round(cz, 1), round(r, 1)],
                              gen=[round(a, 1), round(b, 1), round(rg, 1)],
                              dr=round(rg - r, 2)))
        else:
            pairs.append(dict(src=[round(cx, 1), round(cz, 1), round(r, 1)],
                              gen=None))
    rep = dict(part=part,
               vol_src_cm3=round(v_src / 1000, 1), vol_gen_cm3=round(v_gen / 1000, 1),
               solid_g_src=round(v_src / 1000 * RHO, 1),
               solid_g_gen=round(v_gen / 1000 * RHO, 1),
               print_g_src=round(printed_mass_g(src), 1),
               print_g_gen=round(printed_mass_g(gen), 1),
               mass_saved_print_g=round(printed_mass_g(src) - printed_mass_g(gen), 1),
               watertight=bool(gen.is_watertight), tris=len(gen.faces),
               bbox_src=np.round(src.bounds, 1).tolist(),
               bbox_gen=np.round(gen.bounds, 1).tolist(),
               keep_vox_src=ko, keep_vox_gen=kg,
               holes_src=len(hs), holes_gen=len(hg), hole_pairs=pairs,
               overhang_mm2=round(oh, 0), overhang_frac=round(frac, 3))
    print(json.dumps(rep, indent=1))
    with open(os.path.join(OUT, part + "_report.json"), "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
