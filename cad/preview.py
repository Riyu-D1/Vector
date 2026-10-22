"""Render isometric previews of the assembly STL for sanity checking."""
import sys
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

mesh = trimesh.load("export/SOMA_assembly.stl")

fig = plt.figure(figsize=(10, 12))
for i, (elev, azim, title) in enumerate([
    (20, -60, "iso"), (0, -90, "front"), (90, -90, "top"),
]):
    ax = fig.add_subplot(1, 3, i + 1, projection="3d")
    faces = mesh.triangles
    coll = Poly3DCollection(faces, alpha=1.0, facecolor="#8fa3bf",
                            edgecolor="none")
    ax.add_collection3d(coll)
    lim = mesh.bounds
    ax.set_xlim(lim[0][0], lim[1][0]); ax.set_ylim(lim[0][1], lim[1][1])
    ax.set_zlim(lim[0][2], lim[1][2])
    ax.view_init(elev=elev, azim=azim)
    bb = mesh.extents
    ax.set_box_aspect((bb[0] / bb[2], bb[1] / bb[2], 1.0))
    ax.set_title(title); ax.set_axis_off()
plt.tight_layout()
plt.savefig("export/preview.png", dpi=140, bbox_inches="tight")
print("wrote export/preview.png")
print(f"mesh: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
      f"extents {mesh.extents.round(0)}")
