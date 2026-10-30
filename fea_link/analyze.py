"""fea_link/analyze.py - read a CalculiX .frd of the link model and report:
  - J2-axis reaction moment summed over the NFIX nodes (FORC block) vs the
    F3 whole-arm reference (case A: 3.39 N.m; B: 6.79) - the load check.
  - max von Mises raw, and away from the constrained patches: nodes in NFIX /
    NLOAD and every element touching them are excluded ("patch-filtered").
  - top-N hot spots (filtered) with coordinates.

Run:  python3 fea_link/analyze.py run/link_5.frd run/link_5.inp [--vtu run/res_5]
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from frd2vtu import read_frd, vonmises

REF = {"step1": 3.39, "step2": 6.79}      # F3 frd-measured J2 moments, N.m


def read_nset(inp, name):
    ids, on = set(), False
    with open(inp) as f:
        for line in f:
            if line.startswith("*"):
                on = line.upper().startswith("*NSET") and ("NSET=" + name) in line.upper()
                continue
            if on:
                ids.update(int(t) for t in line.replace(",", " ").split())
    return ids


def main(frd, inp, vtu_stem=None):
    nodes, elems, steps = read_frd(frd)
    nfix = read_nset(inp, "NFIX")
    nload = read_nset(inp, "NLOAD")
    constrained = nfix | nload
    tainted = set(constrained)                # + all nodes sharing an element
    for e in elems:
        if any(n in constrained for n in e):
            tainted.update(e)
    byname = {}
    for i, s in enumerate(steps):
        byname.setdefault(s["name"], []).append(s["data"])
    print("%s: %d nodes %d tets, %d result blocks" % (frd, len(nodes), len(elems), len(steps)))
    print("constrained nodes %d (NFIX %d NLOAD %d); excluded-with-elements %d"
          % (len(constrained), len(nfix), len(nload), len(tainted)))
    for si, disp in enumerate(byname.get("DISP", [])):
        stress = byname["STRESS"][si]
        tag = "step%d" % (si + 1)
        # reactions -> J2 moment about the +Y axis through (0,0,0)
        forc = byname.get("FORC", byname.get("RF", []))
        m_y = sumr = None
        if forc:
            rf = forc[si] if si < len(forc) else forc[-1]
            m_y = sum(nodes[n][2] * f[0] - nodes[n][0] * f[2]
                      for n, f in rf.items() if n in nfix) * 1e-3
            sumr = tuple(sum(rf[n][k] for n in rf) for k in range(3))
        vm = {n: vonmises(s[:6]) for n, s in stress.items()}
        raw = max(vm.values())
        filt = {n: v for n, v in vm.items() if n not in tainted}
        fmax = max(filt.values())
        um = {n: math.sqrt(sum(v * v for v in u[:3])) for n, u in disp.items()}
        umax = max(um.values())
        print("%s: max|U| %.3f mm | raw maxVM %.2f MPa | patch-filtered maxVM %.2f MPa"
              % (tag, umax, raw, fmax))
        if m_y is not None:
            ref = REF.get(tag)
            pct = "" if ref is None else "  (vs F3 %.2f N.m -> %+.1f%%)" % (ref, (abs(m_y) / ref - 1) * 100)
            print("  J2 reaction moment about +Y through origin = %.3f N.m%s | RF sum (%.2f, %.2f, %.2f) N"
                  % (m_y, pct, *sumr))
        top = sorted(filt.items(), key=lambda kv: -kv[1])[:5]
        for n, v in top:
            print("    hot VM %.2f at node %d %s" % (v, n, tuple(round(c, 1) for c in nodes[n])))
    if vtu_stem:
        import numpy as np
        from frd2vtu import write_vtu
        for si, disp in enumerate(byname.get("DISP", [])):
            stress = byname["STRESS"][si]
            ids = sorted(nodes)
            U = np.array([disp.get(n, [0, 0, 0])[:3] for n in ids])
            S = np.array([stress.get(n, [0] * 6)[:6] for n in ids])
            vm = np.array([vonmises(s) for s in S])
            write_vtu("%s_step%d.vtu" % (vtu_stem, si + 1), nodes, elems,
                      {"DISP": U, "UMAG": np.linalg.norm(U, axis=1), "VM": vm})
            print("wrote %s_step%d.vtu" % (vtu_stem, si + 1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
