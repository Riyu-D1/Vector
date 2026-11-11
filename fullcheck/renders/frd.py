"""frd.py - CalculiX .frd reader + surface/VM extraction for FULLCHECK renders.

Fixed-width ASCII .frd layout (ccx 2.23):
    2C <nnodes> ...          node block: ' -1' + id(10) + 3xE12.5
    3C <nelems> ...          element block: ' -1' eid/type header, ' -2' + 10xI10
    1PSTEP / -4 NAME / -5 comp ...   result blocks: ' -1' + id(10) + n*E12.5
Only C3D10 tets (frd type 6) are consumed; mid-edge nodes are ignored for
surface display.  Last DISP and last STRESS block are returned.
"""
import numpy as np


def _fwf(buf, cols):
    """Parse fixed-width float/int columns from a bytes block of uniform
    lines.  cols = list of (start, stop, dtype)."""
    L = buf.find(b"\n") + 1
    assert L > 1 and len(buf) % L == 0, "non-uniform .frd line length"
    a = np.frombuffer(buf, np.uint8).reshape(-1, L)
    out = []
    for s, e, dt in cols:
        out.append(a[:, s:e].copy().view("S%d" % (e - s)).ravel().astype(dt))
    return out


def _result_blocks(data):
    """Yield (name, byte_start, byte_end) for each ' -1' data section."""
    pos = 0
    while True:
        h = data.find(b" -4  ", pos)
        if h < 0:
            return
        nl = data.find(b"\n", h)
        name = data[h + 2:nl].split()[1].decode()
        # skip the -5 component header lines to the first ' -1' line
        p = data.find(b" -1", nl)
        e = data.find(b" -3\n", p)
        yield name, p, e
        pos = e


def read_frd(path):
    data = open(path, "rb").read()

    # nodes
    i = data.find(b"    2C")
    nl = data.find(b"\n", i)
    nn = int(data[i:nl].split()[1])
    blk = data[nl + 1:data.find(b" -3\n", nl)]
    ids, x, y, z = _fwf(blk, [(3, 13, np.int64), (13, 25, np.float64),
                              (25, 37, np.float64), (37, 49, np.float64)])
    assert len(ids) == nn
    idx = np.empty(ids.max() + 1, np.int64)
    idx[ids] = np.arange(nn)
    xyz = np.stack([x, y, z], 1)

    # elements (C3D10 = frd type 6); ' -2' lines carry the 10 node ids
    i = data.find(b"    3C")
    nl = data.find(b"\n", i)
    e_end = data.find(b" -3\n", nl)
    lines = data[nl + 1:e_end].split(b"\n")
    l1 = [l for l in lines if l.startswith(b" -1")]
    l2 = [l for l in lines if l.startswith(b" -2")]
    etype = np.array([int(l[13:18]) for l in l1])
    keep = np.where(etype == 6)[0]
    cols = [(3 + 10 * k, 13 + 10 * k, np.int64) for k in range(10)]
    enodes = np.stack(_fwf(b"\n".join(l2[k] for k in keep) + b"\n", cols), 1)
    tets = idx[enodes]

    # last DISP + STRESS blocks
    disp = stress = None
    for name, s, e in _result_blocks(data):
        blk = data[s:e]
        nval = blk[3 + 10:].find(b"\n") // 12
        cols = [(3, 13, np.int64)] + [(13 + 12 * k, 25 + 12 * k, np.float64)
                                      for k in range(nval)]
        vals = _fwf(blk, cols)
        loc = idx[vals[0]]
        if name == "DISP":
            disp = np.zeros((nn, 3)); disp[loc] = np.stack(vals[1:], 1)
        elif name == "STRESS":
            stress = np.zeros((nn, 6)); stress[loc] = np.stack(vals[1:], 1)
    return xyz, tets, disp, stress


def von_mises(s):
    return np.sqrt(0.5 * ((s[:, 0] - s[:, 1]) ** 2 +
                          (s[:, 1] - s[:, 2]) ** 2 +
                          (s[:, 2] - s[:, 0]) ** 2 +
                          6.0 * (s[:, 3] ** 2 + s[:, 4] ** 2 + s[:, 5] ** 2)))


def surface_faces(xyz, tets):
    """Boundary triangle faces (corner nodes), oriented outward."""
    c = tets[:, :4]
    # outward orientation wrt tet corner ordering (det>0 convention below)
    f = np.concatenate([c[:, [0, 2, 1]], c[:, [0, 1, 3]],
                        c[:, [1, 2, 3]], c[:, [0, 3, 2]]])
    key = np.sort(f, 1)
    packed = key[:, 0] * (xyz.shape[0] ** 2) + \
        key[:, 1] * xyz.shape[0] + key[:, 2]
    upk, uidx, cnt = np.unique(packed, return_index=True, return_counts=True)
    bf = f[uidx[cnt == 1]]
    # orient outward: face normal must point away from its tet centroid
    tet_id = uidx[cnt == 1] // 4
    tc = xyz[c[tet_id]].mean(1)
    fc = xyz[bf].mean(1)
    n = np.cross(xyz[bf[:, 1]] - xyz[bf[:, 0]],
                 xyz[bf[:, 2]] - xyz[bf[:, 0]])
    flip = np.einsum("ij,ij->i", n, fc - tc) < 0
    bf[flip] = bf[flip][:, [0, 2, 1]]
    return bf


def decimate(xyz, faces, vm, target=25000):
    """Quadric-decimate surface; VM re-sampled by nearest node."""
    if len(faces) <= target:
        return xyz, faces, vm
    import fast_simplification
    pts, fcs = fast_simplification.simplify(
        xyz.astype(np.float32), faces.astype(np.int64),
        target_reduction=1.0 - target / len(faces))
    from scipy.spatial import cKDTree
    nn = cKDTree(xyz).query(pts)[1]
    return pts.astype(np.float64), fcs.astype(np.int64), vm[nn]
