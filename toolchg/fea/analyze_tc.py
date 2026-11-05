"""toolchg/fea/analyze_tc.py - copy of lighten/fea/analyze_gen.py for the
toolchg decks (NFIX/NLOAD only - no lumps).  Reports raw/filtered/patch
max VM, max |U|, hot spots; writes .vtu when a stem is given.
Run:  python3 analyze_tc.py <part>.frd <part>.inp [vtu_stem]
"""
import os, sys, math
from pathlib import Path
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "cad3", "fea"))
from frd2vtu import read_frd, vonmises, write_vtu


def read_nset(inp, name):
    ids, on = set(), False
    with open(inp) as f:
        for line in f:
            if line.startswith("*"):
                on = line.upper().startswith("*NSET") and \
                    ("NSET=" + name) in line.upper()
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
    print("%s: %d nodes %d tets, %d result blocks"
          % (frd, len(nodes), len(elems), len(steps)))
    print("constrained %d (NFIX %d NLOAD %d); excluded-with-elements %d"
          % (len(constrained), len(nfix), len(nload), len(tainted)))
    out = {}
    for si, disp in enumerate(byname.get("DISP", [])):
        stress = byname["STRESS"][si]
        vm = {n: vonmises(s[:6]) for n, s in stress.items()}
        raw = max(vm.values())
        filt = {n: v for n, v in vm.items() if n not in tainted}
        if not filt:
            print("step%d: all elements touch constraint patches - raw only"
                  % (si + 1))
            filt = vm
        fmax = max(filt.values())
        patch = {n: v for n, v in vm.items() if n in constrained}
        pmax = max(patch.values()) if patch else 0.0
        um = {n: math.sqrt(sum(v * v for v in u[:3]))
              for n, u in disp.items()}
        umax = max(um.values())
        unode = max(um, key=um.get)
        print("step%d: max|U| %.3f mm (@%s) | raw maxVM %.2f | filtered %.2f"
              " | patch %.2f MPa"
              % (si + 1, umax, tuple(round(c, 1) for c in nodes[unode]),
                 raw, fmax, pmax))
        for n, v in sorted(filt.items(), key=lambda kv: -kv[1])[:5]:
            print("    hot VM %.2f at node %d %s"
                  % (v, n, tuple(round(c, 1) for c in nodes[n])))
        out = dict(umax=umax, unode=tuple(round(c, 1) for c in nodes[unode]),
                   raw_vm=raw, filt_vm=fmax, patch_vm=pmax)
        if vtu_stem:
            ids = sorted(nodes)
            U = np.array([disp.get(n, [0, 0, 0])[:3] for n in ids])
            S = np.array([stress.get(n, [0] * 6)[:6] for n in ids])
            write_vtu("%s_step%d.vtu" % (vtu_stem, si + 1), nodes, elems,
                      {"DISP": U, "UMAG": np.linalg.norm(U, axis=1),
                       "VM": np.array([vonmises(s) for s in S])})
            print("wrote %s_step%d.vtu" % (vtu_stem, si + 1))
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
