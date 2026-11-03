"""genlinks/gen_parts.py - D8 driver: per-part SIMP run + extraction.

Usage:
  python3 genlinks/gen_parts.py <part> [pitch] [iters] [vf]
  python3 genlinks/gen_parts.py all            (default pitches)

Part specs: keep-out (passive solid) zones, NFIX node predicate, NLOAD node
predicate (wrench patch), joint axis/point for the moment arm, print `up`.
Selectors are plain predicates on node/centroid coordinates - the SAME
predicates are reused for the CalculiX verification mesh in fea/msh2gen.py.
"""
import os, sys, json, math, time
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_common as G

OUT = os.path.join(HERE, "out")
LOADS = json.load(open(os.path.join(OUT, "loads.json")))

J2 = np.array([-20.0, 0.0, 143.5])
J3 = np.array([-20.0, 0.0, 270.2])
J4 = np.array([96.4, 0.0, 216.2])
J1 = np.array([0.0, 0.0, 80.8])


def rxz(p, j):
    return np.hypot(p[:, 0] - j[0], p[:, 2] - j[2])


def rxy(p, j):
    return np.hypot(p[:, 0] - j[0], p[:, 1] - j[1])


# spec: stl, link-key in loads.json, keep(cents)->bool, fix(pts)->bool,
#       load(pts)->bool, moment axis, wrench point, pitch, vf, up
def spec(name):
    S = {}
    if name == "upper_out":
        S.update(stl="upper_out.stl", link="upper_plate", pitch=1.0, vf=0.45,
                 axis=(0, 1, 0), B=J3, up=(0, -1, 0),
                 keep=lambda c: (rxz(c, J2) < 33) | (rxz(c, J3) < 33),
                 fix=lambda p: rxz(p, J2) < 31.5,
                 load=lambda p: rxz(p, J3) < 31.5)
    elif name == "upper_back":
        S.update(stl="upper_back.stl", link="upper_plate", pitch=1.0, vf=0.45,
                 axis=(0, 1, 0), B=J3, up=(0, 1, 0),
                 keep=lambda c: (rxz(c, J2) < 33) | (rxz(c, J3) < 33),
                 fix=lambda p: rxz(p, J2) < 31.5,
                 load=lambda p: rxz(p, J3) < 31.5)
    elif name in ("fore_l2", "fore_r2"):
        S.update(stl=name + ".stl", link="fore_plate", pitch=1.0, vf=0.50,
                 axis=(0, 1, 0), B=J4, up=(0, 1, 0) if name == "fore_r2" else (0, -1, 0),
                 keep=lambda c: (c[:, 0] < 33.6) | (rxz(c, J4) < 42),
                 fix=lambda p: (p[:, 0] < 30.0) & bolt_hole_lands(p, name),
                 load=lambda p: rxz(p, J4) < 40)
    elif name == "link1":
        S.update(stl="link1.stl", link="link1", pitch=1.5, vf=0.45,
                 axis=(0, 1, 0), B=J2, up=(0, 0, 1),
                 keep=lambda c: ((rxy(c, J1) < 16) & (c[:, 2] < 92)) | (rxz(c, J2) < 32),
                 fix=lambda p: (rxy(p, J1) < 15) & (p[:, 2] < 91),
                 load=lambda p: (rxz(p, J2) < 30) & (p[:, 1] < -15))
    return S


_BOLT_CACHE = {}


def bolt_hole_lands(pts, name):
    """fore plates: hole axes detected from the plate's own occupancy map
    in the J3-end dogleg overlap strip; lands = within 5 mm of an axis."""
    if name not in _BOLT_CACHE:
        m = trimesh.load_mesh(os.path.join(OUT, name + ".stl"), force="mesh")
        vg = m.voxelized(0.5).fill()
        mat = vg.matrix
        ox = np.asarray(vg.translation)
        # occupancy in XZ (plate is thin in Y): void cells inside material shell
        occ = mat.any(axis=1)
        from scipy import ndimage
        lab, n = ndimage.label(~occ)
        outside = np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))
        holes = []
        for k in range(1, n + 1):
            if k in outside:
                continue
            ii = np.argwhere(lab == k)
            if len(ii) < 4:
                continue
            cx = ox[0] + 0.5 * (ii[:, 0].mean() + 0.5)   # occ is XZ: cols = x,z
            cz = ox[2] + 0.5 * (ii[:, 1].mean() + 0.5)
            r = 0.5 * math.sqrt(len(ii) / math.pi)       # mm (0.5 pitch)
            holes.append((cx, cz, r))
        _BOLT_CACHE[name] = [h for h in holes if h[2] < 6.0 and h[0] < 33.6]
        print("  %s bolt holes in dogleg strip: %s"
              % (name, [(round(a, 1), round(b, 1), round(r, 1))
                        for a, b, r in _BOLT_CACHE[name]]))
    holes = _BOLT_CACHE[name]
    if not holes:
        return np.zeros(len(pts), bool)
    sel = np.zeros(len(pts), bool)
    for cx, cz, _ in holes:
        sel |= np.hypot(pts[:, 0] - cx, pts[:, 2] - cz) < 5.0
    return sel


def run(name, pitch=None, iters=100, vf=None):
    S = spec(name)
    pitch = pitch or S["pitch"]
    vf = vf or S["vf"]
    ld = LOADS["links"][S["link"]]
    F = np.asarray(ld["F"]); M = np.asarray(ld["M"]); g = np.asarray(ld["g"])
    t0 = time.time()
    matrix, origin, p = G.voxelize(os.path.join(OUT, S["stl"]), pitch)
    assert abs(p - pitch) < 1e-9
    els_idx, cents = G.elem_centroids(matrix, origin, pitch)
    nel = len(cents)
    keep = S["keep"](cents)
    pts = G.node_coords(matrix, origin, pitch)
    n8, _, _ = G.edof_table(matrix)
    used = np.unique(n8.ravel())
    fix = np.intersect1d(np.where(S["fix"](pts))[0], used)
    lpatch = np.intersect1d(np.where(S["load"](pts))[0], used)
    print("%s: grid %s nel=%d keep=%d fix_nodes=%d load_nodes=%d"
          % (name, matrix.shape, nel, int(keep.sum()), len(fix), len(lpatch)))
    assert len(fix) and len(lpatch), "empty BC patch"
    f_load, rF, rM = G.wrench_patch(pts[lpatch], F, M, S["B"], S["axis"])
    print("  wrench residual |dF|=%.3f N |dM|=%.3f N.mm" % (rF, rM))
    # own-body lumped masses: drop lumps inside/near the printed part itself
    mesh = trimesh.load_mesh(os.path.join(OUT, S["stl"]), force="mesh")
    lp_pts, lp_F = [], []
    for mass, ch, fv in ld["lumps"]:
        if mesh.contains([ch])[0]:
            continue
        lp_pts.append(ch); lp_F.append(fv)
    patches = [(lpatch, f_load)]
    if lp_pts:
        li, lf = G.lump_loads(pts, lp_pts, lp_F, near=12)
        patches.append((li, lf))
        print("  %d external lumps -> %d nodes" % (len(lp_pts), len(li)))
    Fvec = G.assemble_forces(len(pts), patches)
    np.add.at(Fvec, n8.ravel(), np.broadcast_to(G.body_forces(n8, pitch, g),
                                              (n8.size, 3)))
    # vf applies to the FREE design volume: keep els are pinned solid, so the
    # domain-mean target is kf + vf*(1-kf); a raw vf < kf is infeasible and
    # would void the design space entirely (part splits).
    kf = float(keep.sum()) / nel
    vtgt = kf + vf * (1.0 - kf)
    print("  keep-frac %.3f -> domain vf target %.3f (design vf %.2f)"
          % (kf, vtgt, vf))
    x, u, info = G.simp(matrix, origin, pitch, fix, Fvec, vtgt,
                        rmin_mm=max(2.2 * pitch, 2.0), keep_mask=keep,
                        iters=iters)
    np.save(os.path.join(OUT, name + "_x.npy"), x)
    np.save(os.path.join(OUT, name + "_u.npy"), u)
    G.save_field(os.path.join(OUT, name + "_field.npz"), x, matrix, origin, pitch)
    # true-volume target: voxel-domain vf over-counts thin walls ~40%;
    # keep_true measured on a fine (pitch/2) voxelization of the source.
    vg2 = mesh.voxelized(pitch / 2.0).fill()
    c2 = np.asarray(vg2.translation) + (pitch / 2.0) * (np.argwhere(vg2.matrix) + 0.5)
    keep_true = float(S["keep"](c2).sum()) * (pitch / 2.0) ** 3
    vol_true = abs(mesh.volume)
    vol_tgt = keep_true + vf * (vol_true - keep_true)
    print("  vol_true %.0f keep_true %.0f -> extract target %.0f mm3"
          % (vol_true, keep_true, vol_tgt))
    PV = "/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python"
    import subprocess
    subprocess.run([PV, os.path.join(HERE, "extract.py"),
                    os.path.join(OUT, name + "_field.npz"),
                    os.path.join(OUT, name + "_gen.stl"),
                    "%.0f" % vol_tgt], check=True)
    m = trimesh.load_mesh(os.path.join(OUT, name + "_gen.stl"), force="mesh")
    oh, atot, frac = G.overhang_scan(m, S["up"])
    rep = dict(part=name, nel=nel, iters=info["iters"], vf=float(x.mean()),
               vol_gen=abs(m.volume) / 1000.0, mass_g=abs(m.volume) / 1000.0 * 1.31,
               watertight=bool(m.is_watertight), tris=len(m.faces),
               overhang_mm2=oh, overhang_frac=frac,
               wall_s=round(time.time() - t0, 1))
    print(json.dumps(rep, indent=1))
    with open(os.path.join(OUT, name + "_rep.json"), "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        for n in ("upper_out", "upper_back", "fore_l2", "fore_r2", "link1"):
            run(n)
    else:
        run(sys.argv[1],
            float(sys.argv[2]) if len(sys.argv) > 2 else None,
            int(sys.argv[3]) if len(sys.argv) > 3 else 100,
            float(sys.argv[4]) if len(sys.argv) > 4 else None)
