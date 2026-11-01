"""Build + export + render the SOMA arm v3 structure.

Usage:  python build.py            (exports + renders)
        python build.py exports    (STEP/STL only)
"""
import os, sys, math
from build123d import export_step, export_stl, Compound, Pos, Rot
import parts
from parts import all_parts, CHAIN, JOINT_AXES, J2_Z, J3_X, J4_X, J5_X

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "export")
RENDERS = os.path.join(HERE, "renders")

# print orientation: (rot_x, rot_y) applied for STL export so the part
# lies flat on the bed; STEP stays in assembly frame.
PRINT_ROT = {
    "base_housing":   (0, 0),
    "bearing_cap":    (0, 0),
    "j1_clamp_ring":  (0, 0),
    "turret":         (0, 0),
    "turret_cap":     (0, 0),
    "upper_link":     (0, -90),     # on its back face
    "upper_link_cap": (0, 0),
    "forearm":        (0, -90),
    "horn_ext_j4":    (0, 0),
    "wrist":          (0, -90),
    "horn_ext_j5":    (0, 0),
    "nose":           (0, -90),
    "jaw_l":          (0, 0),
    "jaw_r":          (0, 0),
}


def pose(joint_angles=None):
    """Return {name: part} with each part rotated by `joint_angles` (deg)
    about the joint axes of its kinematic chain (home-frame axes)."""
    ja = joint_angles or {}
    out = {}
    for name, p in all_parts().items():
        q = p
        for j in reversed(CHAIN[name]):
            ang = math.radians(ja.get(j, 0.0))
            if abs(ang) < 1e-12:
                continue
            o, a = JOINT_AXES[j]
            # rotate q about axis `a` through `o`
            if a == (0, 0, 1):
                q = Pos(*o) * Rot(0, 0, math.degrees(ang)) * Pos(
                    -o[0], -o[1], -o[2]) * q
            elif a == (0, 1, 0):
                q = Pos(*o) * Rot(0, math.degrees(ang), 0) * Pos(
                    -o[0], -o[1], -o[2]) * q
            else:
                q = Pos(*o) * Rot(math.degrees(ang), 0, 0) * Pos(
                    -o[0], -o[1], -o[2]) * q
        out[name] = q
    return out


def export_all():
    os.makedirs(EXPORT, exist_ok=True)
    os.makedirs(os.path.join(EXPORT, "print"), exist_ok=True)
    for name, p in all_parts().items():
        export_step(p, os.path.join(EXPORT, f"{name}.step"))
        export_stl(p, os.path.join(EXPORT, f"{name}.stl"))
        rx, ry = PRINT_ROT[name]
        if rx or ry:
            pp = Rot(rx, ry, 0) * p
            export_stl(pp, os.path.join(EXPORT, "print", f"{name}.stl"))
        print(f"  {name}.step/.stl")
    asm = Compound(children=list(all_parts().values()))
    export_step(asm, os.path.join(EXPORT, "assembly.step"))
    export_stl(asm, os.path.join(EXPORT, "assembly.stl"))
    print("  assembly.step/.stl")


# ---------------------------------------------------------------------------
# Minimal matplotlib renderer (headless) — mesh faces projected to 2D
# ---------------------------------------------------------------------------
def render_view(parts_dict, elev, azim, path, title):
    import trimesh
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    scene = trimesh.Scene()
    for name, p in parts_dict.items():
        verts, faces = p.tessellate(1.0)
        v = [(vtx.X, vtx.Y, vtx.Z) for vtx in verts]
        m = trimesh.Trimesh(v, faces)
        scene.add_geometry(m, geom_name=name)
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")
    for name, geom in scene.geometry.items():
        tris = geom.triangles
        coll = Poly3DCollection(tris, alpha=0.9, facecolor="#7090b8",
                                edgecolor="#2c3e50", linewidths=0.05)
        ax.add_collection3d(coll)
    bb = scene.bounds
    ax.set_xlim(bb[0][0], bb[1][0]); ax.set_ylim(bb[0][1], bb[1][1])
    ax.set_zlim(bb[0][2], bb[1][2])
    ax.set_box_aspect((bb[1][0] - bb[0][0], bb[1][1] - bb[0][1],
                       bb[1][2] - bb[0][2]))
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def render_all():
    os.makedirs(RENDERS, exist_ok=True)
    home = pose()
    render_view(home, 8, -90, f"{RENDERS}/front.png", "front")
    render_view(home, 8, 0, f"{RENDERS}/side.png", "side")
    render_view(home, 89, -90, f"{RENDERS}/top.png", "top")
    render_view(home, 22, -55, f"{RENDERS}/iso_home.png", "home pose")
    reach = pose({"J2": 55, "J3": -70, "J4": 30})
    render_view(reach, 15, -55, f"{RENDERS}/reach.png", "reach-out pose")
    # base section: clip z<55 half (cut view via separate render of base)
    base_only = {k: v for k, v in home.items()
                 if k in ("base_housing", "bearing_cap")}
    render_view(base_only, 10, -45, f"{RENDERS}/base.png", "base section")
    print("  renders/*.png")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "exports"):
        print("exporting:")
        export_all()
    if mode in ("all", "renders"):
        print("rendering:")
        render_all()
