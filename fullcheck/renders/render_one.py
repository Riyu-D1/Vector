"""render_one.py - render one FULLCHECK .frd result to a 2-view PNG.

Usage: python3 render_one.py <part_key> [outdir]
Reads the final step's mesh + STRESS, plots von Mises on the deformed
shape (Fusion-style blue->red ramp, red = 12.5 MPa in-layer SF2 gate),
iso + worst-hotspot view, marks the FULLCHECK binding peak, and saves a
decimated surface npz for the interactive viewer.
"""
import gc, json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from frd import read_frd, von_mises, surface_faces, decimate  # noqa: E402
from parts import PARTS, MODE_LABEL  # noqa: E402

VMAX = 12.5  # SF2 gate, MPa
# Fusion-360-style stress ramp: blue -> cyan -> green -> yellow -> red
FUSION = LinearSegmentedColormap.from_list("fusion", [
    (0.00, "#0000aa"), (0.18, "#0055ff"), (0.38, "#00c8ff"),
    (0.55, "#00d264"), (0.72, "#ffe600"), (0.88, "#ff9600"),
    (1.00, "#ff0000")])


def deform_scale(xyz, U):
    u = np.linalg.norm(U, axis=1).max()
    diag = np.linalg.norm(xyz.max(0) - xyz.min(0))
    if u <= 0:
        return 0.0, 0.0
    return u, 0.05 * diag / u


def style(ax, verts):
    lo, hi = verts.min(0), verts.max(0)
    ax.set_box_aspect(hi - lo)
    ax.set_axis_off()
    ax.grid(False)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_alpha(0.0)


def plot(ax, verts, faces, fvm, cmap, norm):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    pc = Poly3DCollection(verts[faces], facecolors=cmap(norm(fvm)),
                          shade=True, edgecolor="none", linewidth=0,
                          antialiased=False)
    pc.set_array(fvm); pc.set_cmap(cmap); pc.set_norm(norm)
    ax.add_collection3d(pc)
    ax.auto_scale_xyz(verts[:, 0], verts[:, 1], verts[:, 2])
    return pc


def hotspot_view(ax, nout):
    """Camera looks at the peak along the local surface normal."""
    d = nout / (np.linalg.norm(nout) + 1e-12)
    elev = np.degrees(np.arcsin(np.clip(d[2], -1, 1)))
    azim = np.degrees(np.arctan2(d[1], d[0]))
    ax.view_init(elev=float(np.clip(elev + 8, -75, 75)), azim=float(azim - 12))


def main():
    key = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else HERE
    meshdir = os.path.join(outdir, ".mesh")
    os.makedirs(meshdir, exist_ok=True)
    P = next(p for p in PARTS if p["key"] == key)
    frd_path = os.path.join(ROOT, P["frd"])

    xyz, tets, U, S = read_frd(frd_path)
    nn, ne = len(xyz), len(tets)
    vm = von_mises(S)
    del S
    maxu, scale = deform_scale(xyz, U)
    peak = np.array(P["xyz"])
    pk_def = peak + scale * U[np.argmin(((xyz - peak) ** 2).sum(1))]
    dxyz = xyz + scale * U
    faces = surface_faces(xyz, tets)
    del tets, U, xyz
    gc.collect()
    fvm = vm[faces].mean(1)
    n_surf = len(faces)
    vx, fx, vmx = decimate(dxyz, faces, vm, 25000)

    norm = Normalize(0, VMAX, clip=True)
    fig = plt.figure(figsize=(20, 10.4), dpi=100)
    fig.patch.set_facecolor("#f4f4f4")

    # callout pin: offset from the peak along the nearest face's normal
    ctr = (dxyz.max(0) + dxyz.min(0)) / 2
    diag = np.linalg.norm(dxyz.max(0) - dxyz.min(0))
    fc = dxyz[faces].mean(1)
    fn = np.cross(dxyz[faces[:, 1]] - dxyz[faces[:, 0]],
                  dxyz[faces[:, 2]] - dxyz[faces[:, 0]])
    nout = fn[np.argmin(((fc - pk_def) ** 2).sum(1))]
    nout = nout / (np.linalg.norm(nout) + 1e-12)

    for i, (title, viewfun, pinlen) in enumerate([
            ("isometric", lambda ax: ax.view_init(elev=22, azim=-62), 0.10),
            ("worst-hotspot view", None, 0.045)]):
        tip = pk_def + nout * pinlen * diag
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        pc = plot(ax, dxyz, faces, fvm, FUSION, norm)
        style(ax, dxyz)
        ax.plot([pk_def[0], tip[0]], [pk_def[1], tip[1]],
                [pk_def[2], tip[2]], color="w", lw=3.4, zorder=11)
        ax.plot([pk_def[0], tip[0]], [pk_def[1], tip[1]],
                [pk_def[2], tip[2]], color="k", lw=1.6, zorder=11)
        ax.scatter(*pk_def, marker="o", s=60, c="#ff00ff",
                   edgecolor="w", linewidth=1.2, depthshade=False, zorder=12)
        ax.scatter(*tip, marker="*", s=480, c="#ff00ff",
                   edgecolor="w", linewidth=1.4, depthshade=False, zorder=12)
        ax.text(*tip, "  PEAK", fontsize=13,
                color="k", weight="bold", zorder=13)
        ax.set_title(title, fontsize=15, pad=6)
        if viewfun:
            viewfun(ax)
        else:
            hotspot_view(ax, nout)
            h = 0.30 * (dxyz.max(0) - dxyz.min(0)).max()
            ax.set_xlim(pk_def[0] - h, pk_def[0] + h)
            ax.set_ylim(pk_def[1] - h, pk_def[1] + h)
            ax.set_zlim(pk_def[2] - h, pk_def[2] + h)

    sf = P.get("sf_disp", "%g" % P["sf"])
    lines = [
        "%s  —  %s" % (P["key"], P["frd"]),
        "%s nodes, %s C3D10 tets (final step)" % (f"{nn:,}", f"{ne:,}"),
        "max|U| = %.3g mm -> deformation scale x%.4g" % (maxu, scale),
        "BINDING: %s  %.3g MPa vs %.3g MPa -> SF %s" % (
            MODE_LABEL[P["mode"]], P["peak"], P["allow"], sf),
        "peak @ (%.1f, %.1f, %.1f)  [* marker]" % tuple(P["xyz"]),
    ]
    if P.get("note"):
        lines.append(P["note"])
    fig.suptitle("%s — von Mises (MPa) on deformed shape;  red = %.1f MPa "
                 "SF2 gate" % (P["key"], VMAX), fontsize=18, y=0.97)
    fig.text(0.012, 0.028, "\n".join(lines), fontsize=11.5, family="monospace",
             va="bottom")
    cax = fig.add_axes([0.925, 0.14, 0.013, 0.72])
    cb = fig.colorbar(pc, cax=cax, extend="max")
    cb.set_label("von Mises (MPa)", fontsize=13)
    cb.ax.tick_params(labelsize=11)
    fig.subplots_adjust(left=0.0, right=0.90, top=0.92, bottom=0.02, wspace=0.0)

    png = os.path.join(outdir, P["key"] + ".png")
    fig.savefig(png, dpi=100)
    plt.close(fig)
    del faces, fvm, dxyz, fig
    gc.collect()

    # decimated surface for the HTML viewer
    np.savez(os.path.join(meshdir, key + ".npz"),
             verts=vx.astype(np.float32), faces=fx.astype(np.int32),
             vm=vmx.astype(np.float32),
             meta=json.dumps(dict(key=key, frd=P["frd"], scale=scale,
                                  maxu=maxu, peak=list(pk_def),
                                  mode=P["mode"], mpa=P["peak"],
                                  allow=P["allow"], sf=sf,
                                  note=P.get("note", ""))))
    print("%s: %d surf-faces -> %d dec | %s" % (key, n_surf, len(fx), png))


if __name__ == "__main__":
    main()
