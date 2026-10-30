"""fea_link/view_link_stress.py - interactive von Mises viewer (jet gradient)
for the F4 shoulder-link results, based on fea/view_stress.py.

  Interactive window (rotatable):
    fea/.venv/bin/python fea_link/view_link_stress.py fea_link/run/res_25_step1.vtu
  Off-screen PNG, TWO angles side by side + hot-spot marker (disp x20):
    fea/.venv/bin/python fea_link/view_link_stress.py fea_link/run/res_25_step1.vtu \
        --png fea_link/link_caseA.png --hotspot 16.5,32.1,23.1 --hotvm 0.83

mesh point data: VM (MPa), DISP (mm vector), UMAG (mm)  -- written by frd2vtu.py
(res_25_step2.vtu = step1 fields x2, exact for the 2x linear case B).
"""
import sys, argparse
import pyvista as pv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vtu")
    ap.add_argument("--png", help="write this PNG instead of / in addition to opening a window")
    ap.add_argument("--scale", type=float, default=20.0, help="displacement exaggeration")
    ap.add_argument("--no-window", action="store_true", help="do not open the interactive window")
    ap.add_argument("--hotspot", help="x,y,z of the (filtered) hot spot to mark")
    ap.add_argument("--hotvm", type=float, help="filtered hot-spot VM [MPa] for the label")
    a = ap.parse_args()

    mesh = pv.read(a.vtu)
    vmax = float(mesh["VM"].max())
    warped = mesh.warp_by_vector("DISP", factor=a.scale)
    hs = [float(v) for v in a.hotspot.split(",")] if a.hotspot else None
    hot_lbl = "hot spot %.2f MPa" % a.hotvm if a.hotvm else "hot spot"

    def style(p, bar):
        p.add_mesh(warped, scalars="VM", cmap="jet", clim=[0, vmax],
                   show_scalar_bar=bar,
                   scalar_bar_args={"title": "von Mises [MPa]", "fmt": "%.2f",
                                    "n_labels": 6, "vertical": True,
                                    "position_x": 0.78, "position_y": 0.25,
                                    "width": 0.12, "height": 0.5})
        p.add_text("von Mises [MPa]  max %.2f   (disp x%.0f)" % (vmax, a.scale),
                   position="upper_left", font_size=11)
        if hs:
            # node is on the undeformed mesh -> move marker by the warped delta
            import numpy as np
            i = int(np.argmin(np.sum((mesh.points - np.asarray(hs)) ** 2, axis=1)))
            p.add_mesh(pv.Sphere(radius=2.0, center=warped.points[i]),
                       color="red")
            p.add_point_labels([warped.points[i]], [hot_lbl], font_size=12,
                               text_color="red", shape=None, show_points=False)

    def view(off):
        p = pv.Plotter(off_screen=off, window_size=(1280, 900), shape=(1, 2))
        p.subplot(0, 0)
        style(p, False)
        p.add_text("iso (front)", position="lower_left", font_size=10)
        p.view_isometric(); p.camera.zoom(1.25)
        p.subplot(0, 1)
        style(p, True)
        p.add_text("side (+Y)", position="lower_left", font_size=10)
        p.view_yz(); p.camera.zoom(1.25)
        p.link_views()
        return p

    if a.png:
        p = view(True)
        p.screenshot(a.png, transparent_background=False)
        print("WROTE %s (max VM %.2f MPa, disp x%.0f)" % (a.png, vmax, a.scale))
        p.close()
    if not a.no_window:
        view(False).show()

if __name__ == "__main__":
    main()
