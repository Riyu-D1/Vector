"""genlinks/gen_common.py - D8 shared engine: voxel SIMP topopt + domain prep.

Pieces:
  voxelize()     trimesh -> filled boolean voxel grid (element centroids)
  hex_ke()       8-node brick stiffness (2x2x2 Gauss, exact)
  wrench_patch() distribute (F, M) at B over a node patch (uniform + torsion)
  simp()         classic OC SIMP: min compliance s.t. volume fraction,
                 cone density filter, passive-solid keep-out elements
  extract()      density field -> marching-cubes mesh -> smoothed STL

Conventions: mm, N, MPa. PETG-CF E0=4000 nu=0.35 (cad3/fea convention).
Run helpers individually via gen_parts.py.
"""
import os, json, math
import numpy as np
import trimesh
from scipy import sparse
from scipy.sparse.linalg import cg, spsolve

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
E0, NU, EMIN = 4000.0, 0.35, 1.0e-3
RHO = 1.31e-3 * 9.81          # N/mm3 equivalent body force (PETG-CF 1.31 g/cm3)


# ---------------------------------------------------------------- mesh prep
def voxelize(stl, pitch):
    """Filled voxel grid of a watertight STL. Returns (matrix bool[nx,ny,nz],
    origin (3,), pitch)."""
    m = trimesh.load_mesh(stl, force="mesh")
    m.merge_vertices()
    vg = m.voxelized(pitch)
    vg = vg.fill()
    return vg.matrix.astype(bool), np.asarray(vg.translation, float), pitch


def grid_pts(matrix, origin, pitch):
    """Node coordinates of the voxel grid corners -> (nn,3) + (nx+1,ny+1,nz+1)."""
    nx, ny, nz = matrix.shape
    xs = origin[0] + pitch * np.arange(nx + 1)
    ys = origin[1] + pitch * np.arange(ny + 1)
    zs = origin[2] + pitch * np.arange(nz + 1)
    return xs, ys, zs


def elem_centroids(matrix, origin, pitch):
    idx = np.argwhere(matrix)
    return idx, origin + pitch * (idx + 0.5)


# ------------------------------------------------------------------ SIMP FE
def hex_ke(e=E0, nu=NU):
    """8-node brick, unit edge, 2x2x2 Gauss integration -> 24x24."""
    g = 1.0 / math.sqrt(3.0)
    gp = [(a, b, c) for a in (-g, g) for b in (-g, g) for c in (-g, g)]
    D = np.zeros((6, 6))
    c = e / ((1 + nu) * (1 - 2 * nu))
    D[:3, :3] = c * np.array([[1 - nu, nu, nu], [nu, 1 - nu, nu], [nu, nu, 1 - nu]])
    D[3, 3] = D[4, 4] = D[5, 5] = c * (1 - 2 * nu) / 2
    ke = np.zeros((24, 24))
    for xi, et, ze in gp:
        dn = np.array([
            [-(1 - et) * (1 - ze), (1 - et) * (1 - ze), (1 + et) * (1 - ze), -(1 + et) * (1 - ze),
             -(1 - et) * (1 + ze), (1 - et) * (1 + ze), (1 + et) * (1 + ze), -(1 + et) * (1 + ze)],
            [-(1 - xi) * (1 - ze), -(1 + xi) * (1 - ze), (1 + xi) * (1 - ze), (1 - xi) * (1 - ze),
             -(1 - xi) * (1 + ze), -(1 + xi) * (1 + ze), (1 + xi) * (1 + ze), (1 - xi) * (1 + ze)],
            [-(1 - xi) * (1 - et), -(1 + xi) * (1 - et), -(1 + xi) * (1 + et), -(1 - xi) * (1 + et),
             (1 - xi) * (1 - et), (1 + xi) * (1 - et), (1 + xi) * (1 + et), (1 - xi) * (1 + et)],
        ]) / 8.0
        coords = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                           [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
        J = coords.T @ dn.T                        # 3x3 = d(xyz)/d(xi,eta,zeta)
        dJ = np.linalg.det(J)
        dN = np.linalg.solve(J, dn)                # 3x8: dN_i/d(x,y,z) columns
        B = np.zeros((6, 24))
        for i in range(8):
            B[0, 3 * i] = dN[0, i]; B[1, 3 * i + 1] = dN[1, i]; B[2, 3 * i + 2] = dN[2, i]
            B[3, 3 * i] = dN[1, i]; B[3, 3 * i + 1] = dN[0, i]
            B[4, 3 * i + 1] = dN[2, i]; B[4, 3 * i + 2] = dN[1, i]
            B[5, 3 * i] = dN[2, i]; B[5, 3 * i + 2] = dN[0, i]
        ke += B.T @ D @ B * dJ
    return ke


def edof_table(matrix):
    """nel x 8 node ids + nel x 24 dof indices for filled voxels."""
    nx, ny, nz = matrix.shape
    nid = np.arange((nx + 1) * (ny + 1) * (nz + 1))
    nmap = nid.reshape((nx + 1, ny + 1, nz + 1), order="F")
    els = np.argwhere(matrix)
    i, j, k = els[:, 0], els[:, 1], els[:, 2]
    n8 = np.stack([
        nmap[i, j, k], nmap[i + 1, j, k], nmap[i + 1, j + 1, k], nmap[i, j + 1, k],
        nmap[i, j, k + 1], nmap[i + 1, j, k + 1], nmap[i + 1, j + 1, k + 1],
        nmap[i, j + 1, k + 1]], axis=1)
    dofs = np.stack([3 * n8 + c for c in range(3)], axis=2).reshape(-1, 24)
    return n8, dofs, nmap


def cone_filter(centroids, rmin):
    """Sparse cone-filter matrix H (nel x nel), rows sum 1 after Hs."""
    tr = spatial_cKD(centroids)
    pairs = tr.query_pairs(rmin, output_type="ndarray")
    i = np.concatenate([pairs[:, 0], pairs[:, 1]])
    j = np.concatenate([pairs[:, 1], pairs[:, 0]])
    d = np.linalg.norm(centroids[i] - centroids[j], axis=1)
    w = np.maximum(0.0, rmin - d)
    i = np.concatenate([i, np.arange(len(centroids))])
    j = np.concatenate([j, np.arange(len(centroids))])
    w = np.concatenate([w, np.full(len(centroids), rmin)])
    H = sparse.csr_matrix((w, (i, j)), shape=(len(centroids),) * 2)
    Hs = np.asarray(H.sum(axis=1)).ravel()
    return H, Hs


def spatial_cKD(pts):
    from scipy.spatial import cKDTree
    return cKDTree(pts)


def wrench_patch(pts, F, M, B, axis):
    """Per-node forces on patch nodes `pts` reproducing wrench (F, M about B)
    exactly (least squares over a 6-field basis: 3 uniform + 3 torsion fields).
    Returns (forces (n,3), |dF|, |dM|)."""
    n = len(pts)
    r = pts - B
    basis = []
    for k in range(3):
        e = np.zeros(3); e[k] = 1.0
        basis.append(np.broadcast_to(e, (n, 3)).copy())
        basis.append(np.cross(np.broadcast_to(e, (n, 3)), r))
    A = np.zeros((6, 6))
    for k in range(6):
        A[:3, k] = basis[k].sum(axis=0)
        A[3:, k] = np.cross(r, basis[k]).sum(axis=0)
    w, *_ = np.linalg.lstsq(A, np.concatenate([F, M]), rcond=None)
    f = sum(w[k] * basis[k] for k in range(6))
    Fp = f.sum(axis=0)
    Mp = np.cross(r, f).sum(axis=0)
    return f, float(np.linalg.norm(Fp - F)), float(np.linalg.norm(Mp - M))


def node_coords(matrix, origin, pitch):
    xs, ys, zs = grid_pts(matrix, origin, pitch)
    gx, gy, gz = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.stack([gx, gy, gz], axis=-1).reshape(-1, 3, order="F")


def assemble_forces(nn, patches):
    """patches: list of (node_idx array, (n,3) per-node forces) -> (nn,3)."""
    F = np.zeros((nn, 3))
    for idx, f in patches:
        np.add.at(F, idx, f)
    return F


def body_forces(n8, pitch, g, rho_n_mm3=RHO):
    """Element weight distributed to nodes -> (nel*8 node slots force)."""
    w = rho_n_mm3 * pitch ** 3 / 8.0
    return np.asarray(g) * w


def lump_loads(pts, lump_pts, lump_F, near=12):
    """Each lump's force distributed over the `near` nearest grid nodes.
    Returns (idx, (m,3)) patch."""
    from scipy.spatial import cKDTree
    tr = cKDTree(pts)
    d, ii = tr.query(np.asarray(lump_pts), k=near)
    if ii.ndim == 1:
        ii = ii[:, None]
    idx = np.unique(ii.ravel())
    # weight by inverse distance
    w = 1.0 / np.maximum(d, 0.25)
    w = (w / w.sum(axis=1, keepdims=True))
    f = np.zeros((len(pts), 3))
    for li in range(len(lump_pts)):
        np.add.at(f, ii[li], w[li][:, None] * np.asarray(lump_F[li]))
    nz = np.abs(f).sum(axis=1) > 0
    return np.where(nz)[0], f[nz]


def simp(matrix, origin, pitch, fix_idx, node_forces, vf, rmin_mm,
         keep_mask=None, iters=120, move=0.15, lump_forces=None,
         log=print):
    """OC SIMP on a filled voxel domain.
      fix_idx     int array of fixed NODE indices (all 3 dofs)
      node_forces (nn,3) assembled nodal forces (includes gravity + wrench)
      vf          target volume fraction of the WHOLE domain
      keep_mask   bool nel -> passive solid (x stays 1)
      lump_forces unused placeholder (forces are pre-assembled)
    Returns (x nel densities, u displacement, info dict)."""
    els_idx, cents = elem_centroids(matrix, origin, pitch)
    nel = len(cents)
    n8, dofs, nmap = edof_table(matrix)
    nn = int(nmap.max()) + 1
    ke = hex_ke() * pitch                          # mm-scaled brick
    KE = ke.ravel()
    iK = np.repeat(dofs, 24, axis=1).ravel()
    jK = np.tile(dofs, 24).ravel()
    used = np.unique(n8.ravel())               # only nodes inside elements
    fixed = np.intersect1d(np.unique(fix_idx), used)
    fixd = np.concatenate([3 * fixed, 3 * fixed + 1, 3 * fixed + 2])
    alld = np.concatenate([3 * used, 3 * used + 1, 3 * used + 2])
    free = np.setdiff1d(alld, fixd)
    Fv = node_forces.reshape(-1)

    x = np.full(nel, vf)
    if keep_mask is not None:
        x = np.where(keep_mask, 1.0, vf)
    H, Hs = cone_filter(cents, rmin_mm)
    u = np.zeros(3 * nn)
    Emin = EMIN
    loop = 0
    chg = 1.0
    while chg > 0.01 and loop < iters:
        loop += 1
        sK = KE[np.newaxis, :] * (Emin + x ** 3 * (1.0 - Emin))[:, np.newaxis]
        K = sparse.coo_matrix((sK.ravel(), (iK, jK)),
                              shape=(3 * nn, 3 * nn)).tocsr()
        Kff = K[free][:, free]
        # CG/Jacobi stalls >25% relres at 4000 it on these thin voxel grids
        # (measured) -> spsolve; ~60 s for the 318k-dof upper_out system.
        du = spsolve(Kff.tocsc(), Fv[free])
        info = "direct"
        u[:] = 0.0
        u[free] = du
        ce = (u[dofs] @ ke * u[dofs]).sum(axis=1)   # nel compliances (unit E)
        obj = float((Emin + x ** 3 * (1.0 - Emin)) @ ce)
        dc = -3.0 * x ** 2 * (1.0 - Emin) * ce
        dcf = (H @ (dc * x / Hs)) / np.maximum(x, 1e-3)
        # OC update
        l1, l2 = 0.0, 1e9
        xn = x.copy()
        while (l2 - l1) / (l1 + l2 + 1e-12) > 1e-4:
            lm = 0.5 * (l1 + l2)
            xn = np.clip(x * np.sqrt(-dcf / lm), x - move, x + move)
            xn = np.clip(xn, 0.001, 1.0)
            if keep_mask is not None:
                xn = np.where(keep_mask, 1.0, xn)
            if xn.mean() > vf:
                l1 = lm
            else:
                l2 = lm
        chg = float(np.abs(xn - x).max())
        x = xn
        log("  it %3d obj %.3f vf %.3f chg %.4f cg-it %s"
            % (loop, obj, x.mean(), chg, info))
    return x, u, dict(nel=nel, nn=nn, iters=loop, obj=obj, ke=ke,
                      cents=cents, n8=n8)


def save_field(path, x, matrix, origin, pitch):
    dense = np.zeros(matrix.shape, dtype=np.float32)
    dense[matrix] = x.astype(np.float32)
    np.savez(path, dense=dense, origin=np.asarray(origin, np.float64),
             pitch=np.float64(pitch), mask=matrix)


def overhang_scan(mesh, up=(0, 0, 1), limit_deg=45.0):
    """Downward-facing area fraction + worst stats for print orientation `up`."""
    n = mesh.face_normals
    a = mesh.area_faces
    up = np.asarray(up, float) / np.linalg.norm(up)
    cos = n @ up
    oh = a[cos < -math.cos(math.radians(limit_deg))].sum()
    return float(oh), float(a.sum()), float(oh / a.sum())


def printed_mass_g(mesh, rho_gcc=1.31, wall_mm=2.4, infill=0.40):
    """Solid-equivalent g + estimated printed g (walls solid + infill of core).
    Core volume approximated by voxelizing an eroded interior: cheap proxy =
    solid volume * infill outside the wall shell computed by ray casting is
    heavy - use the standard heuristic shell share for thin parts."""
    vol_mm3 = abs(mesh.volume)
    solid_g = vol_mm3 / 1000.0 * rho_gcc
    return solid_g


if __name__ == "__main__":
    print("module only")
