"""make_viewer.py - self-contained interactive HTML stress viewer.

One plotly Mesh3d + one peak-marker Scatter3d per part; a dropdown switches
parts.  Same blue->red ramp as the PNG renders (red = 12.5 MPa SF2 gate),
per-vertex von Mises on the deformed shape, hover shows MPa.  plotly.js is
inlined - no CDN.  Reads the decimated surfaces in .mesh/.
"""
import json, os, sys
import numpy as np
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts import PARTS, MODE_LABEL  # noqa: E402

CSCALE = [[0.00, "#0000aa"], [0.18, "#0055ff"], [0.38, "#00c8ff"],
          [0.55, "#00d264"], [0.72, "#ffe600"], [0.88, "#ff9600"],
          [1.00, "#ff0000"]]
VMAX = 12.5


def main():
    fig = go.Figure()
    metas = []
    for i, p in enumerate(PARTS):
        z = np.load(os.path.join(HERE, ".mesh", p["key"] + ".npz"))
        meta = json.loads(str(z["meta"]))
        metas.append(meta)
        v, f, vm = z["verts"], z["faces"], z["vm"]
        if len(f) > 17000:  # keep the single-file budget under 40 MB
            import fast_simplification
            from scipy.spatial import cKDTree
            v2, f = fast_simplification.simplify(
                v.astype(np.float32), f.astype(np.int64),
                target_reduction=1.0 - 17000 / len(f))
            vm = vm[cKDTree(v).query(v2)[1]]
            v = v2.astype(np.float32)
        fig.add_mesh3d(
            x=v[:, 0], y=v[:, 1], z=v[:, 2],
            i=f[:, 0], j=f[:, 1], k=f[:, 2],
            intensity=vm, colorscale=CSCALE, cmin=0, cmax=VMAX,
            colorbar=dict(title="von Mises (MPa)", len=0.8),
            hovertemplate="VM %{intensity:.3f} MPa<br>"
                          "x %{x:.1f} y %{y:.1f} z %{z:.1f}<extra>%{fullData.name}</extra>",
            name=p["key"], showscale=True, visible=(i == 0),
            lighting=dict(ambient=0.55, diffuse=0.85, specular=0.15,
                          roughness=0.6, fresnel=0.05))
        pk = meta["peak"]
        fig.add_scatter3d(
            x=[pk[0], pk[0]], y=[pk[1], pk[1]], z=[pk[2], pk[2]],
            mode="markers", marker=dict(size=[0, 9], color="#ff00ff",
                                        line=dict(color="white", width=2)),
            name="PEAK " + p["key"], visible=(i == 0),
            hoverinfo="skip", showlegend=False)

    n = len(PARTS)
    buttons = []
    for i, (p, m) in enumerate(zip(PARTS, metas)):
        vis = [False] * (2 * n)
        vis[2 * i] = vis[2 * i + 1] = True
        title = ("%s — %s<br>deformation x%.4g (max|U| %.3g mm) · "
                 "BINDING: %s %.3g vs %.3g MPa → SF %s%s" %
                 (p["key"], m["frd"], m["scale"], m["maxu"],
                  MODE_LABEL[m["mode"]], m["mpa"], m["allow"], m["sf"],
                  (" · " + m["note"]) if m["note"] else ""))
        buttons.append(dict(label=p["key"], method="update",
                            args=[{"visible": vis}, {"title.text": title}]))
    fig.update_layout(
        title=dict(text="select a part", y=0.97),
        updatemenus=[dict(buttons=buttons, direction="down", x=0.0, y=1.0,
                          xanchor="left", yanchor="top", showactive=True)],
        scene=dict(aspectmode="data",
                   xaxis=dict(visible=False), yaxis=dict(visible=False),
                   zaxis=dict(visible=False)),
        margin=dict(l=0, r=0, t=60, b=0))
    # initialise title from the first part
    fig.layout.title.text = buttons[0]["args"][1]["title.text"]

    out = os.path.join(HERE, "stress_viewer.html")
    fig.write_html(out, include_plotlyjs=True, full_html=True,
                   config=dict(displaylogo=False))
    print(out, "%.1f MB" % (os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
