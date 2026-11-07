"""refine/fea/analyze_r3.py - analyzer for the R3 horn-mount decks.

Same metrics as analyze_tc.py (raw / filtered / patch maxVM, max|U|,
top-5 hotspots) plus, at each hotspot node, the layer-direction split:
  sigma_n   = normal stress through the printed layer stack
             (build direction per part: gf->z(h), l5->x(a), l4->y(b))
  vm_inp    = von Mises of the in-layer stress components only
because the design allowables differ (25 MPa in-layer vs 12.5 MPa
cross-layer sustained, REFINE-LOG materials section).

Run:  python3 analyze_r3.py <part>.frd <part>.inp <layer_axis(x|y|z)> [vtu_stem]
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "cad3", "fea"))
from frd2vtu import read_frd, vonmises, write_vtu


def read_nsets(inp):
    ids, on, name = {}, False, None
    with open(inp) as f:
        for line in f:
            if line.startswith("*"):
                on = False
                u = line.upper()
                if u.startswith("*NSET"):
                    for tok in u.replace(",", " ").split():
                        if tok.startswith("NSET="):
                            name = tok.split("=", 1)[1]
                            on = True
                            ids.setdefault(name, set())
                continue
            if on:
                ids[name].update(
                    int(t) for t in line.replace(",", " ").split())
    return ids


AX = {"x": 0, "y": 1, "z": 2}


def layer_split(s6, axis):
    """s6 = (sxx,syy,szz,sxy,syz,sxz) -> (sigma_n, vm_in_layer)."""
    a = AX[axis]
    full = [[s6[0], s6[3], s6[5]],
            [s6[3], s6[1], s6[4]],
            [s6[5], s6[4], s6[2]]]
    sn = full[a][a]
    inp = [list(r) for r in full]
    # zero the through-layer normal stress; keep in-plane tensor incl.
    # the shear components that lie in the layer plane
    inp[a][a] = 0.0
    for j in range(3):
        if j != a:
            inp[a][j] = inp[j][a] = 0.0
    t = inp
    vm = math.sqrt(max(0.0,
        0.5 * ((t[0][0] - t[1][1]) ** 2 + (t[1][1] - t[2][2]) ** 2 +
               (t[2][2] - t[0][0]) ** 2) +
        3.0 * (t[0][1] ** 2 + t[1][2] ** 2 + t[2][0] ** 2)))
    return sn, vm


def main(frd, inp, laxis, vtu_stem=None):
    nodes, elems, steps = read_frd(frd)
    ns = read_nsets(inp)
    nfix = ns.get("NFIX", set())
    nload = set()
    for k, v in ns.items():
        if k.startswith("NLOAD"):
            nload |= v
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
            filt = vm
        fmax = max(filt.values())
        patch = {n: v for n, v in vm.items() if n in constrained}
        pmax = max(patch.values()) if patch else 0.0
        um = {n: math.sqrt(sum(v * v for v in u[:3]))
              for n, u in disp.items()}
        umax = max(um.values())
        unode = max(um, key=um.get)
        print("step%d: max|U| %.3f mm (@%s) | raw maxVM %.2f | filtered "
              "%.2f | patch %.2f MPa"
              % (si + 1, umax,
                 tuple(round(c, 1) for c in nodes[unode]),
                 raw, fmax, pmax))
        for n, v in sorted(filt.items(), key=lambda kv: -kv[1])[:5]:
            s6 = stress[n][:6]
            sn, vi = layer_split(s6, laxis)
            print("    hot VM %.2f @n%d %s | sig_n(%s) %+.2f VM_in-layer "
                  "%.2f" % (v, n,
                            tuple(round(c, 1) for c in nodes[n]),
                            laxis, sn, vi))
        # also the biggest raw (patch-side) node, for the record
        nraw = max(vm, key=vm.get)
        s6 = stress[nraw][:6]
        sn, vi = layer_split(s6, laxis)
        print("    raw-max VM %.2f @n%d %s | sig_n %+.2f VM_in-layer %.2f"
              % (vm[nraw], nraw,
                 tuple(round(c, 1) for c in nodes[nraw]), sn, vi))
        out = dict(umax=umax,
                   unode=tuple(round(c, 1) for c in nodes[unode]),
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
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         sys.argv[4] if len(sys.argv) > 4 else None)
