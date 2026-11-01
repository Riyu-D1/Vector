"""cad3/fea/view_stress.py - colour-gradient PNG + interactive HTML of a result .vtu.
Run with the fea viewer venv:  /Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python
    view_stress.py run/res_J2_step1.vtu J2housing
Writes <stem>.png (2 angles) and <stem>.html (interactive) into cad3/fea/.
"""
import sys
import pyvista as pv

def main(vtu, tag):
    grid = pv.read(vtu)
    grid["disp"] = grid["DISP"]
    warped = grid.warp_by_vector("disp", factor=20.0)
    stem = "cad3_%s" % tag
    # interactive HTML (interactive scene embedded)
    p = pv.Plotter(off_screen=True)
    p.add_mesh(warped, scalars="VM", cmap="turbo", show_edges=False,
               scalar_bar_args={"title": "von Mises [MPa]", "n_labels": 6})
    p.add_text("%s  (disp x20)" % vtu, font_size=10)
    p.export_html(stem + ".html")
    # PNG two angles
    for name, pos in (("iso", None), ("front", "xy")):
        p = pv.Plotter(off_screen=True, window_size=[1100, 800])
        p.add_mesh(warped, scalars="VM", cmap="turbo", show_edges=False,
                   scalar_bar_args={"title": "von Mises [MPa]", "n_labels": 6})
        if pos:
            p.view_vector((0, -1, 0.3))
        else:
            p.view_isometric()
        p.add_text("%s  VM  disp x20" % vtu, font_size=9)
        p.screenshot("%s_%s.png" % (stem, name))
    print("wrote %s.html %s_iso.png %s_front.png" % (stem, stem, stem))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
