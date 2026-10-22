"""Render the assembly STL — shaded hero view + orthographic insets."""
import sys
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

mesh = trimesh.load("export/SOMA_assembly.stl")
faces = mesh.triangles

# Face-normal shading: warm shell colour keyed to a key light.
n = mesh.face_normals
light = np.array([0.5, -0.4, 0.75]); light = light / np.linalg.norm(light)
b = np.clip(n @ light, 0, 1)
base_col = np.array([0.88, 0.86, 0.82])
dark = np.array([0.16, 0.17, 0.20])
cols = dark[None, :] + (base_col - dark)[None, :] * (0.35 + 0.65 * b[:, None])

fig = plt.figure(figsize=(13, 10), facecolor="#101114")
gs = fig.add_gridspec(2, 3, height_ratios=[3, 1.4], hspace=0.02, wspace=0.02)


def draw(ax, elev, azim, title=None):
    coll = Poly3DCollection(faces, facecolor=cols, edgecolor="none")
    ax.add_collection3d(coll)
    lim = mesh.bounds
    ax.set_xlim(lim[0][0] - 8, lim[1][0] + 8)
    ax.set_ylim(lim[0][1] - 8, lim[1][1] + 8)
    ax.set_zlim(lim[0][2], lim[1][2] + 8)
    ax.view_init(elev=elev, azim=azim)
    bb = mesh.extents
    ax.set_box_aspect((bb[0] / bb[2], bb[1] / bb[2], 1.0))
    ax.set_axis_off()
    if title:
        ax.set_title(title, color="#8a8f98", fontsize=9)


ax = fig.add_subplot(gs[0, :], projection="3d")
draw(ax, elev=16, azim=-62, title="SOMA v2")
ax2 = fig.add_subplot(gs[1, 0], projection="3d"); draw(ax2, 8, -90, "front")
ax3 = fig.add_subplot(gs[1, 1], projection="3d"); draw(ax3, 10, 0, "side")
ax4 = fig.add_subplot(gs[1, 2], projection="3d"); draw(ax4, 60, -60, "high")

plt.savefig("export/preview.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("wrote export/preview.png")
print(f"mesh: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
      f"extents {mesh.extents.round(0)}")
