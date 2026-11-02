"""verify/code/view.py - frd -> vtu -> interactive HTML + PNG stress views.
Run with the fea viewer venv:  /Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python
    view.py <case> <frd> [step]
Writes verify/fea/<case>_stepN.vtu, <case>_stepN.html, <case>_stepN_iso.png,
<case>_stepN_front.png  (turbo blue->red von Mises, warp x20 like cad3).
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
FEA = os.path.abspath(os.path.join(HERE, "..", "fea"))
os.makedirs(FEA, exist_ok=True)

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/fea/fea_link")
from frd2vtu import read_frd, vonmises, write_vtu
import numpy as np
import pyvista as pv


def main(case, frd, want=0):
    nodes, elems, steps = read_frd(frd)
    byname = {}
    for i, s in enumerate(steps):
        byname.setdefault(s["name"].upper(), []).append(s["data"])
    ids = sorted(nodes)
    nsol = len(byname.get("DISP", []))
    for si in range(nsol):
        if want and si + 1 != want:
            continue
        disp = byname["DISP"][si]
        stress = byname["STRESS"][si] if "STRESS" in byname else {}
        U = np.array([disp.get(n, [0, 0, 0])[:3] for n in ids])
        S = np.array([stress.get(n, [0] * 6)[:6] for n in ids])
        um = np.linalg.norm(U, axis=1)
        vm = np.array([vonmises(s) for s in S])
        stem = os.path.join(FEA, "%s_step%d" % (case, si + 1))
        write_vtu(stem + ".vtu", nodes, elems,
                  {"DISP": U, "UMAG": um, "VM": vm})
        grid = pv.read(stem + ".vtu")
        grid["disp"] = grid["DISP"]
        warped = grid.warp_by_vector("disp", factor=20.0)
        p = pv.Plotter(off_screen=True)
        p.add_mesh(warped, scalars="VM", cmap="turbo", show_edges=False,
                   scalar_bar_args={"title": "von Mises [MPa]", "n_labels": 6})
        p.add_text("%s step%d (disp x20)" % (case, si + 1), font_size=10)
        p.export_html(stem + ".html")
        for name in ("iso", "front"):
            p2 = pv.Plotter(off_screen=True, window_size=[1100, 800])
            p2.add_mesh(warped, scalars="VM", cmap="turbo", show_edges=False,
                        scalar_bar_args={"title": "von Mises [MPa]", "n_labels": 6})
            if name == "front":
                p2.view_vector((0, -1, 0.3))
            else:
                p2.view_isometric()
            p2.add_text("%s step%d VM x20" % (case, si + 1), font_size=9)
            p2.screenshot("%s_%s.png" % (stem, name))
        im = int(np.argmax(vm))
        print("%s step%d: max VM %.2f MPa at %s -> %s.vtu/.html/.png"
              % (case, si + 1, vm[im], tuple(round(v, 1) for v in nodes[ids[im]]), stem))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
