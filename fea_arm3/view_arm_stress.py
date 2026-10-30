"""fea_arm3/view_arm_stress.py - whole-arm von Mises viewer (Fusion-style jet
gradient, displacement exaggerated x20, scalar bar in MPa).

Interactive window (rotatable):
  fea/.venv/bin/python fea_arm3/view_arm_stress.py --case A

Off-screen PNG, ONE image with TWO viewports (front = looking along -Y at the
XZ plane | side = looking along -X at the YZ plane):
  fea/.venv/bin/python fea_arm3/view_arm_stress.py --case A --png fea_arm3/arm_caseA.png --no-window

Any vtu with point arrays VM [MPa] and DISP [mm vector] works:
  fea/.venv/bin/python fea_arm3/view_arm_stress.py --vtu /path/res.vtu --png /tmp/x.png --no-window

Cases (resolved under <this dir>/run/):
  A  report_AB_step1.vtu    B  report_AB_step2.vtu    C  report_C_step1.vtu
"""
import argparse
import sys
from pathlib import Path

import pyvista as pv

BASE = Path(__file__).resolve().parent

CASES = {
    "A": "report_AB_step1.vtu",
    "B": "report_AB_step2.vtu",
    "C": "report_C_step1.vtu",
}

SCALAR_BAR = {
    "title": "von Mises [MPa]",
    "fmt": "%.2f",
    "n_labels": 5,
    "position_x": 0.72,
    "width": 0.24,
    "height": 0.06,
    "position_y": 0.04,
}


def set_view(p, warped, which):
    """Camera for one viewport: 'front' looks along -Y at the XZ plane,
    'side' looks along -X at the YZ plane. +Z is up in both."""
    b = warped.bounds  # (xmin, xmax, ymin, ymax, zmin, zmax)
    c = [(b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0]
    diag = max(1e-9, ((b[1] - b[0]) ** 2 + (b[3] - b[2]) ** 2 + (b[5] - b[4]) ** 2) ** 0.5)
    d = 2.0 * diag
    if which == "front":       # camera on +Y, view direction -Y
        p.camera_position = [(c[0], c[1] + d, c[2]), tuple(c), (0.0, 0.0, 1.0)]
    else:                      # 'side': camera on +X, view direction -X
        p.camera_position = [(c[0] + d, c[1], c[2]), tuple(c), (0.0, 0.0, 1.0)]
    p.reset_camera()           # refit along the same view direction
    p.camera.zoom(1.15)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default="A", choices=sorted(CASES),
                    help="which run/*.vtu result to show (default A)")
    ap.add_argument("--vtu", help="explicit .vtu path; overrides --case")
    ap.add_argument("--png", help="write a side-by-side front|side PNG (offscreen)")
    ap.add_argument("--scale", type=float, default=20.0,
                    help="displacement exaggeration (default 20)")
    ap.add_argument("--vmax", type=float, default=None,
                    help="cap the colour range at this MPa value")
    ap.add_argument("--no-window", action="store_true",
                    help="do not open the interactive window")
    a = ap.parse_args()

    if a.vtu:
        vtu = Path(a.vtu)
        case = vtu.stem
    else:
        vtu = BASE / "run" / CASES[a.case]
        case = a.case
    if not vtu.is_file():
        sys.exit("ERROR: vtu not found: %s" % vtu)

    mesh = pv.read(str(vtu))
    for key in ("VM", "DISP"):
        if key not in mesh.point_data:
            sys.exit("ERROR: %s has no point array %r (need VM, DISP)" % (vtu, key))

    data_vmax = float(mesh["VM"].max())
    clim_hi = min(data_vmax, a.vmax) if a.vmax is not None else data_vmax
    warped = mesh.warp_by_vector("DISP", factor=a.scale)
    title = "%s von Mises MPa max %.2f (disp x%g)" % (case, data_vmax, a.scale)
    print("%s: max VM %.2f MPa, clim [0, %.2f], disp x%g" % (vtu, data_vmax, clim_hi, a.scale))

    def add_body(p, with_bar):
        p.add_mesh(warped, scalars="VM", cmap="jet", clim=[0.0, clim_hi],
                   show_scalar_bar=with_bar,
                   scalar_bar_args=dict(SCALAR_BAR) if with_bar else None)

    def render_png(path):
        p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1920, 900))
        p.subplot(0, 0)                                # left: front, no bar
        add_body(p, with_bar=False)
        p.add_text(title + "  front", position="upper_left", font_size=11)
        set_view(p, warped, "front")
        p.subplot(0, 1)                                # right: side + the one scalar bar
        add_body(p, with_bar=True)
        p.add_text(title + "  side", position="upper_left", font_size=11)
        set_view(p, warped, "side")
        p.screenshot(str(path), transparent_background=False)
        p.close()
        print("WROTE %s" % path)

    def interactive():
        p = pv.Plotter(window_size=(1280, 900))
        add_body(p, with_bar=True)
        p.add_text(title, position="upper_left", font_size=12)
        p.add_axes()
        p.view_isometric()
        p.camera.zoom(1.3)
        p.show()

    if a.png:
        render_png(a.png)
    if not a.no_window:
        interactive()


if __name__ == "__main__":
    main()
