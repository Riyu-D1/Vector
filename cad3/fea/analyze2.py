"""cad3/fea/analyze2.py - read a CalculiX .frd of a cad3 model and report:
  - raw max von Mises,
  - patch-filtered max VM (nodes in NFIX|NLOAD + every element touching them
    excluded - same convention as fea_link/analyze.py),
  - bolt-region max VM: nodes inside the constraint patches THEMSELVES
    (stage D2: bolt/pin patches stay in the stress ranking - reported
    separately, not silently dropped),
  - top-N hot spots with coordinates,
  - optionally writes per-step .vtu.
Run:  python3 analyze2.py run/x.frd run/x.inp [run/vtu_stem]
"""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from frd2vtu import read_frd, vonmises
import numpy as np


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
    tainted = set(constrained)
    for e in elems:
        if any(n in constrained for n in e):
            tainted.update(e)
    byname = {}
    for i, s in enumerate(steps):
        byname.setdefault(s["name"], []).append(s["data"])
    print("%s: %d nodes %d tets, %d result blocks" % (frd, len(nodes), len(elems), len(steps)))
    print("constrained %d (NFIX %d NLOAD %d); excluded-with-elements %d"
          % (len(constrained), len(nfix), len(nload), len(tainted)))
    for si, disp in enumerate(byname.get("DISP", [])):
        stress = byname["STRESS"][si]
        tag = "step%d" % (si + 1)
        vm = {n: vonmises(s[:6]) for n, s in stress.items()}
        raw = max(vm.values())
        filt = {n: v for n, v in vm.items() if n not in tainted}
        fmax = max(filt.values())
        bolt = {n: v for n, v in vm.items() if n in constrained}
        bmax = max(bolt.values()) if bolt else 0.0
        um = {n: math.sqrt(sum(v * v for v in u[:3])) for n, u in disp.items()}
        umax = max(um.values())
        print("%s: max|U| %.3f mm | raw maxVM %.2f | filtered maxVM %.2f | patch maxVM %.2f MPa"
              % (tag, umax, raw, fmax, bmax))
        top = sorted(filt.items(), key=lambda kv: -kv[1])[:5]
        for n, v in top:
            print("    hot VM %.2f at node %d %s" % (v, n, tuple(round(c, 1) for c in nodes[n])))
        topb = sorted(bolt.items(), key=lambda kv: -kv[1])[:3]
        for n, v in topb:
            print("    patch VM %.2f at node %d %s" % (v, n, tuple(round(c, 1) for c in nodes[n])))
        if vtu_stem:
            from frd2vtu import write_vtu
            ids = sorted(nodes)
            U = np.array([disp.get(n, [0, 0, 0])[:3] for n in ids])
            S = np.array([stress.get(n, [0] * 6)[:6] for n in ids])
            vvm = np.array([vonmises(s) for s in S])
            write_vtu("%s_step%d.vtu" % (vtu_stem, si + 1), nodes, elems,
                      {"DISP": U, "UMAG": np.linalg.norm(U, axis=1), "VM": vvm})
            print("wrote %s_step%d.vtu" % (vtu_stem, si + 1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
