"""fullcheck/fea/fc_analyze.py - criteria analyzer for the bolted/pinned
per-part SF2 study.

Reads <part>.frd (ccx C3D10 result) + <part>.inp (nsets), evaluates the
PETG-CF allowable set per node (patch-tainted nodes filtered, same
convention as analyze_tc.py: nodes of elements touching NFIX/NLOAD):

  in-layer          von Mises                       vs 25  MPa
  layer-normal      n.Sigma.n tensile               vs 12.5 MPa
                    (n = print-bed normal in the mesh frame)
  compression       max(0, -min principal)          vs 15  MPa
  interlayer shear  |Sigma.n - (n.Sigma.n)n|        vs 8 MPa (and 6.1)

SF = allowable / stress; SF2 pass = SF >= 2.  Also prints max |U| and the
top-5 filtered hot spots for the binding criterion.

Run: python3 fc_analyze.py <part>.frd <part>.inp <nx,ny,nz> [tag]
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "cad3", "fea"))
from frd2vtu import read_frd, vonmises  # noqa

ALLOW = {"vm": 25.0, "norm": 12.5, "comp": 15.0, "shear": 8.0,
         "shear_lb": 6.1}

def read_nsets(inp):
    sets, name = {}, None
    with open(inp) as f:
        for line in f:
            if line.startswith("*"):
                name = None
                if line.upper().startswith("*NSET"):
                    for t in line.upper().replace(",", " ").split():
                        if t.startswith("NSET="):
                            name = t.split("=", 1)[1]
                continue
            if name:
                sets.setdefault(name, set()).update(
                    int(t) for t in line.replace(",", " ").split())
    return sets

def principal(s):
    """s = [sxx,syy,szz,sxy,syz,szx] -> sorted principal stresses."""
    S = np.array([[s[0], s[3], s[5]],
                  [s[3], s[1], s[4]],
                  [s[5], s[4], s[2]]])
    return np.sort(np.linalg.eigvalsh(S))[::-1]

def criteria(s, n):
    vm = vonmises(s[:6])
    S = np.array([[s[0], s[3], s[5]],
                  [s[3], s[1], s[4]],
                  [s[5], s[4], s[2]]])
    sn = S @ n
    snn = float(n @ sn)
    inter = float(np.linalg.norm(sn - snn * n))
    p = principal(s)
    comp = max(0.0, -p[2])
    return vm, max(0.0, snn), comp, inter

def main(frd, inp, nvec, tag=None):
    n = np.asarray(nvec, float); n = n / np.linalg.norm(n)
    sets = read_nsets(inp)
    constrained = set()
    for nm, ids in sets.items():
        if nm.startswith("NFIX") or nm.startswith("NLOAD"):
            constrained |= ids
    nodes, elems, steps = read_frd(frd)
    tainted = set(constrained)
    for e in elems:
        if any(x in constrained for x in e):
            tainted.update(e)
    byname = {}
    for s in steps:
        byname.setdefault(s["name"], []).append(s["data"])
    print("%s: %d nodes %d tets | constrained %d tainted %d"
          % (os.path.basename(frd), len(nodes), len(elems),
             len(constrained), len(tainted)))
    disp = byname.get("DISP", [{}])[-1]
    stress = byname.get("STRESS", [{}])[-1]
    um = {k: math.sqrt(sum(v * v for v in u[:3])) for k, u in disp.items()}
    umax = max(um.values()) if um else 0.0
    vals = {}
    for nid, s in stress.items():
        if nid in tainted:
            continue
        vals[nid] = criteria(s, n)
    if not vals:
        print("  ALL nodes tainted"); return {}
    raw_vm = max(vonmises(s[:6]) for s in stress.values())
    keys = ["vm", "norm", "comp", "shear"]
    res = dict(umax=umax, raw_vm=raw_vm)
    for ki, key in enumerate(keys):
        nid, vv = max(vals.items(), key=lambda kv: kv[1][ki])
        peak = vv[ki]
        allow = ALLOW[key]
        sf = allow / peak if peak > 0 else float("inf")
        res[key] = dict(peak=peak, node=nid, at=nodes[nid], sf=sf)
        extra = ""
        if key == "shear":
            extra = "  | vs 6.1 SF %.2f" % (ALLOW["shear_lb"] / peak
                                            if peak else float("inf"))
        print("  %-5s peak %7.3f MPa SF %6.2f @%s%s"
              % (key, peak, sf,
                 tuple(round(c, 1) for c in nodes[nid]), extra))
    print("  max|U| %.3f mm | raw maxVM %.2f" % (umax, raw_vm))
    bind = min(keys, key=lambda k: res[k]["sf"])
    print("  BINDING: %s (SF %.2f)" % (bind, res[bind]["sf"]))
    return res

if __name__ == "__main__":
    nv = tuple(float(t) for t in sys.argv[3].split(","))
    main(sys.argv[1], sys.argv[2], nv)
