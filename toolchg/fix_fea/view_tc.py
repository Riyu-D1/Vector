"""toolchg/fea/view_tc.py - PNG + interactive HTML of a toolchg .vtu
result.  Copy of lighten/fea/view_gen.py (turbo gradient, warped disp).
D12: verbatim copy of toolchg/check/fea/view_tc.py - writes beside
itself, so outputs land under toolchg/fix_fea/.
Run:  /Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python view_tc.py <vtu> <tag>
"""
import os, sys
import pyvista as pv

HERE = os.path.dirname(os.path.abspath(__file__))


def main(vtu, tag, warp=20.0):
    grid = pv.read(vtu)
    grid["disp"] = grid["DISP"]
    warped = grid.warp_by_vector("disp", factor=warp)
    stem = os.path.join(HERE, tag)
    p = pv.Plotter(off_screen=True)
    p.add_mesh(warped, scalars="VM", cmap="turbo", show_edges=False,
               scalar_bar_args={"title": "von Mises [MPa]", "n_labels": 6})
    p.add_text("%s  (disp x%g)" % (os.path.basename(vtu), warp), font_size=10)
    p.export_html(stem + ".html")
    for name, pos in (("iso", None), ("front", "y")):
        p = pv.Plotter(off_screen=True, window_size=[1100, 800])
        p.add_mesh(warped, scalars="VM", cmap="turbo", show_edges=False,
                   scalar_bar_args={"title": "von Mises [MPa]",
                                    "n_labels": 6})
        if pos:
            p.view_vector((0, -1, 0.3))
        else:
            p.view_isometric()
        p.add_text("%s  VM  disp x%g" % (os.path.basename(vtu), warp),
                   font_size=9)
        p.screenshot("%s_%s.png" % (stem, name))
    print("wrote %s.html %s_iso.png %s_front.png" % (stem, stem, stem))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
