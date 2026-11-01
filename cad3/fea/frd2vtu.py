"""fea/frd2vtu.py - convert a CalculiX .frd (C3D10, nodal DISP+STRESS per step)
to one .vtu per step, and print the headline numbers.

Run: python3 fea/frd2vtu.py fea/link_c.frd fea/res_c   ->  res_c_step1.vtu, res_c_step2.vtu
"""
import sys, math
import numpy as np

def read_frd(path):
    nodes, elems, steps = {}, [], []          # steps: list of {name: nid->vals}
    mode = None; cur = None
    with open(path) as f:
        for line in f:
            if line.startswith("    2C"):
                mode = "nodes"; continue
            if line.startswith("    3C"):
                mode = "elems"; continue
            if line.startswith("    1PSTEP"):
                mode = "step"; continue
            if mode == "nodes" and line.startswith(" -1"):
                f = [line[i:i + 12] for i in range(13, len(line.rstrip()), 12)]
                nodes[int(line[3:13])] = tuple(float(v) for v in f[:3])
                continue
            if mode == "elems" and line.startswith(" -1"):
                p = line.split()
                cur = (int(p[1]), int(p[2]))                # eid, frd type (6 = C3D10)
                continue
            if mode == "elems" and line.startswith(" -2"):
                if cur[1] == 6:
                    elems.append([int(t) for t in line.split()[1:]])
                cur = None
                continue
            if line.startswith(" -4"):
                name = line.split()[1].strip()
                cur = {"name": name, "data": {}}
                steps.append(cur)
                mode = "data"; continue
            if mode == "data":
                if line.startswith(" -3"):
                    mode = None; cur = None; continue
                if line.startswith(" -1"):
                    f = [line[i:i + 12] for i in range(13, len(line.rstrip()), 12)]
                    cur["data"][int(line[3:13])] = [float(v) for v in f if v.strip()]
                continue
    return nodes, elems, steps

def vonmises(s):
    sxx, syy, szz, sxy, syz, szx = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy * sxy + syz * syz + szx * szx))

def write_vtu(path, nodes, elems, point_data):
    ids = sorted(nodes)
    idx = {n: i for i, n in enumerate(ids)}
    pts = np.array([nodes[n] for n in ids], dtype=np.float64)
    con = np.array([[idx[i] for i in e] for e in elems], dtype=np.int64)
    off = np.arange(10, 10 * len(elems) + 1, 10, dtype=np.int64)
    typ = np.full(len(elems), 24, dtype=np.uint8)       # VTK_QUADRATIC_TETRA
    def arr(a, ncomp):
        a = np.asarray(a, dtype=np.float64)
        flat = " ".join("%.6g" % v for v in a.ravel())
        return '        <DataArray type="Float64" NumberOfComponents="%d" format="ascii">%s</DataArray>\n' % (ncomp, flat)
    with open(path, "w") as f:
        w = f.write
        w('<?xml version="1.0"?>\n<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">\n')
        w('  <UnstructuredGrid>\n    <Piece NumberOfPoints="%d" NumberOfCells="%d">\n' % (len(ids), len(elems)))
        w('      <PointData>\n')
        for name, a in point_data.items():
            ncomp = a.shape[1] if a.ndim > 1 else 1
            w('        <DataArray type="Float64" Name="%s" NumberOfComponents="%d" format="ascii">' % (name, ncomp))
            w(" ".join("%.6g" % v for v in np.asarray(a, dtype=np.float64).ravel()))
            w('</DataArray>\n')
        w('      </PointData>\n      <Points>\n')
        w('        <DataArray type="Float64" NumberOfComponents="3" format="ascii">')
        w(" ".join("%.6g" % v for v in pts.ravel()))
        w('</DataArray>\n      </Points>\n      <Cells>\n')
        for nm, a in (("connectivity", con), ("offsets", off), ("types", typ)):
            w('        <DataArray type="Int64" Name="%s" format="ascii">' % nm)
            w(" ".join(str(v) for v in np.asarray(a).ravel()))
            w('</DataArray>\n')
        w('      </Cells>\n    </Piece>\n  </UnstructuredGrid>\n</VTKFile>\n')

def main(frd, stem):
    nodes, elems, steps = read_frd(frd)
    print("%s: %d nodes %d tets, %d result blocks" % (frd, len(nodes), len(elems), len(steps)))
    byname = {}
    for i, s in enumerate(steps):
        byname.setdefault(s["name"], []).append((i + 1, s["data"]))
    ids = sorted(nodes)
    for blk_i, (nm, lst) in enumerate(byname.items()):
        pass
    step_i = 0
    for nm in ("DISP", "STRESS"):
        pass
    # blocks come in order DISP, STRESS, ERROR per step
    nsteps = len(byname.get("DISP", []))
    for si in range(nsteps):
        disp = byname["DISP"][si][1]
        stress = byname["STRESS"][si][1] if "STRESS" in byname else {}
        U = np.array([disp.get(n, [0, 0, 0])[:3] for n in ids])
        S = np.array([stress.get(n, [0] * 6)[:6] for n in ids])
        um = np.linalg.norm(U, axis=1)
        vm = np.array([vonmises(s) for s in S])
        out = "%s_step%d.vtu" % (stem, si + 1)
        write_vtu(out, nodes, elems,
                  {"DISP": U, "UMAG": um, "VM": vm,
                   "SXX": S[:, 0], "SYY": S[:, 1], "SZZ": S[:, 2]})
        im = int(np.argmax(vm)); iu = int(np.argmax(um))
        nmax = ids[im]; num = ids[iu]
        print("step %d: max VM = %.2f MPa at node %d %s ; max |U| = %.4f mm at node %d"
              % (si + 1, vm[im], nmax, tuple(round(v, 2) for v in nodes[nmax]), um[iu], num))
        hi = np.argsort(vm)[-6:]
        for h in hi[::-1]:
            print("    VM %.2f at %s" % (vm[h], tuple(round(v, 1) for v in nodes[ids[h]])))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
