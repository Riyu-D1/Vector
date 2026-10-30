#!/usr/bin/env python3
"""fea_arm/frd2report.py -- parse a CalculiX .frd (C3D10, nodal results per
step) into one .vtu per step plus a text report.

Usage:
    python3 frd2report.py <file.frd> <file.inp> <parts.json> <out_stem>

Writes:
    <out_stem>_step<n>.vtu   DISP vector, UMAG, VM, SXX/SYY/SZZ per step
    <out_stem>.txt           report (also printed to stdout)

read_frd / vonmises / write_vtu are copied (nearly) verbatim from
fea/frd2vtu.py -- tested code.  read_frd only gains three annotation fields
per result block: "pstep" (step number = last int on the 1PSTEP line),
"ncomp" and the literal "hdr" line, used for step grouping and for detecting
a nodal-force / reaction block.  Parsing behaviour is unchanged.
"""
import sys, math, json, re
from pathlib import Path
import numpy as np


# ---------------------------------------------------------------- frd2vtu.py
def read_frd(path):
    nodes, elems, steps = {}, [], []          # steps: list of {name: nid->vals}
    mode = None; cur = None; pstep = None
    with open(path) as f:
        for line in f:
            if line.startswith("    2C"):
                mode = "nodes"; continue
            if line.startswith("    3C"):
                mode = "elems"; continue
            if line.startswith("    1PSTEP"):
                mode = "step"
                try:
                    pstep = int(line.split()[-1])
                except (ValueError, IndexError):
                    pstep = None
                continue
            if mode == "nodes" and line.startswith(" -1"):
                f = [line[i:i + 12] for i in range(13, len(line.rstrip()), 12)]
                nodes[int(line[3:13])] = tuple(float(v) for v in f[:3])
                continue
            if mode == "elems" and line.startswith(" -1"):
                p = line.split()
                cur = (int(p[1]), int(p[2]))                # eid, frd type
                continue
            if mode == "elems" and line.startswith(" -2"):
                if cur[1] == 6:                             # C3D10
                    elems.append([int(t) for t in line.split()[1:]])
                elif cur[1] == 3:                           # C3D4
                    elems.append([int(t) for t in line.split()[1:]])
                cur = None
                continue
            if line.startswith(" -4"):
                p = line.split()
                try:
                    ncomp = int(p[2])
                except (ValueError, IndexError):
                    ncomp = 0
                cur = {"name": p[1].strip(), "data": {},
                       "ncomp": ncomp, "pstep": pstep, "hdr": line.rstrip("\n")}
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
    nn = con.shape[1]
    off = np.arange(nn, nn * len(elems) + 1, nn, dtype=np.int64)
    typ = np.full(len(elems), 24 if nn == 10 else 10, dtype=np.uint8)
    # VTK 24 = QUADRATIC_TETRA (C3D10); VTK 10 = TETRA (C3D4)
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
# ------------------------------------------------------------- end frd2vtu.py


# --------------------------------------------------------------- inp parsing
def read_inp(path):
    """Parse *ELEMENT, TYPE=..., ELSET=<name> blocks (every node of a part's
    elements belongs to that part) and *NSET, NSET=<name> blocks.
    Returns (elsets: name->set(node ids), nsets: name->set(node ids))."""
    elsets, nsets = {}, {}
    cur = None          # ("elem", name) | ("nset", name) | None
    gen = False         # current *NSET has GENERATE -> data lines are ranges
    cont = False        # previous data line ended with ',' -> continuation
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("**"):   # '**' = inp comment
                continue
            if line.startswith("*"):
                up = line.upper()
                if up.startswith("*ELEMENT"):
                    m = re.search(r"ELSET\s*=\s*([^\s,]+)", line, re.I)
                    cur = ("elem", m.group(1).strip('"') if m else "")
                elif up.startswith("*NSET"):
                    m = re.search(r"NSET\s*=\s*([^\s,]+)", line, re.I)
                    cur = ("nset", m.group(1).strip('"') if m else "")
                    gen = "GENERATE" in up
                else:
                    cur = None
                cont = False
                continue
            if cur is None:
                continue
            toks = [t for t in re.split(r"[,\s]+", line) if t]
            nums = []
            ok = True
            for t in toks:
                try:
                    nums.append(int(float(t)))
                except ValueError:
                    ok = False
                    break
            if not ok or not nums:
                continue
            if cur[0] == "nset":
                if gen and len(nums) >= 2:      # start, end[, step]
                    step = nums[2] if len(nums) > 2 and nums[2] else 1
                    nsets.setdefault(cur[1], set()).update(
                        range(nums[0], nums[1] + 1, step))
                else:
                    nsets.setdefault(cur[1], set()).update(nums)
            elif cont:
                # continuation of a wrapped element line: all ints are nodes
                elsets.setdefault(cur[1], set()).update(nums)
            else:
                # element line: first int is the element id, rest are nodes
                elsets.setdefault(cur[1], set()).update(nums[1:])
            cont = line.endswith(",")
    return elsets, nsets


# ------------------------------------------------------------------- helpers
def _pad(v, n):
    v = list(v) if v else []
    return (v + [0.0] * n)[:n]

def _xyz(p):
    return "(%.2f, %.2f, %.2f)" % (p[0], p[1], p[2])

def _fmt(v, nd=2):
    return ("%%.%df" % nd) % v if v is not None else "n/a"

# block names that are never nodal reaction forces
KNOWN_NODAL = {"DISP", "STRESS", "ERROR", "HERMIAN", "ERROR(%)", "ENER",
               "ELSE", "ELKE", "EVOL", "STP", "TIME"}


def pick_rf_block(blocks):
    """Return the name of a nodal-force/reaction block in this step, or None.
    Accepts any -4 block that is not DISP/STRESS/ERROR/HERMIAN/... and has
    >= 3 components; prefers names containing RF/FORC."""
    cands = []
    for nm, b in blocks.items():
        if nm.upper() in KNOWN_NODAL:
            continue
        if b["ncomp"] >= 3 and any(len(v) >= 3 for v in b["data"].values()):
            cands.append(nm)
    for nm in cands:
        if "RF" in nm.upper() or "FORC" in nm.upper():
            return nm
    return cands[0] if cands else None


def main():
    if len(sys.argv) != 5:
        sys.exit("usage: python3 %s <file.frd> <file.inp> <parts.json> <out_stem>"
                 % Path(sys.argv[0]).name)
    frd_p, inp_p, pj_p, stem = sys.argv[1:5]

    cfg = json.loads(Path(pj_p).read_text())
    parts = cfg.get("parts", {}) or {}
    joints = cfg.get("joints", {}) or {}
    tcp = cfg.get("tcp")
    moments_nm = cfg.get("moments_nm", {}) or {}
    payload_n = float(cfg.get("payload_n", 4.905))
    step_mult = cfg.get("step_mult")          # optional [mult per step]

    nodes, elems, steps = read_frd(frd_p)
    elsets, nsets = read_inp(inp_p)
    if not nodes or not elems:
        sys.exit("no nodes/elements parsed from %s" % frd_p)

    ids = sorted(nodes)
    pos = np.array([nodes[n] for n in ids], dtype=np.float64)
    idx = {n: i for i, n in enumerate(ids)}

    # ---- node -> part ------------------------------------------------------
    partnames = set(parts)
    lower = {p.lower(): p for p in partnames}
    def match_part(elset):
        if elset in partnames:
            return elset
        s = re.sub(r"^[pP]_", "", elset)     # gmsh Physical Volume "p_<part>"
        if s in partnames:
            return s
        return lower.get(elset.lower()) or lower.get(s.lower())
    single = next(iter(partnames)) if len(partnames) == 1 else None
    node_part = {}
    elset_map = {}                            # elset -> resolved part name
    for ename, nids in elsets.items():
        p = match_part(ename) or single or ename
        elset_map[ename] = p
        for n in nids:
            node_part[n] = p
    def part_of(n):
        return node_part.get(n, "?")

    # per-part index lists (same ordering as ids / vm / um arrays)
    pidx = {}
    for i, n in enumerate(ids):
        pidx.setdefault(part_of(n), []).append(i)
    pidx = {p: np.asarray(v, dtype=np.int64) for p, v in pidx.items()}

    # ---- NFIX set ----------------------------------------------------------
    nfix = set()
    for k, v in nsets.items():
        if k.upper() == "NFIX":
            nfix |= v
    nfix_src = "*NSET NFIX" if nfix else None
    if not nfix:
        # fallback: nodes with (nearly) zero displacement at the base (lowest z)
        zmin = float(pos[:, 2].min())
        nfix = {n for n in ids if nodes[n][2] <= zmin + 1.5}
        nfix_src = "z<=zmin+1.5 fallback (refined by zero-DISP per step)"
    nfix = {n for n in nfix if n in nodes}

    # ---- group result blocks by step ---------------------------------------
    step_keys, bystep = [], {}
    for s in steps:
        k = s["pstep"] if s["pstep"] is not None else (len(step_keys) + 1)
        if k not in bystep:
            bystep[k] = {}
            step_keys.append(k)
        bystep[k][s["name"]] = s

    # ---- report ------------------------------------------------------------
    out = []
    def emit(s=""):
        print(s)
        out.append(s)

    emit("=" * 74)
    emit("frd2report  %s" % Path(frd_p).name)
    emit("inp=%s  parts=%s" % (Path(inp_p).name, Path(pj_p).name))
    emit("%d nodes, %d tets, %d result block(s) in %d step(s)"
         % (len(nodes), len(elems), len(steps), len(step_keys)))
    emit("result block -4 headers seen:")
    seen = set()
    for s in steps:
        key = (s["name"], s["hdr"])
        if key in seen:
            continue
        seen.add(key)
        tag = ""
        if s["name"].upper() in KNOWN_NODAL:
            tag = "   (known)"
        elif s["ncomp"] >= 3:
            tag = "   (UNKNOWN -> nodal-force candidate)"
        else:
            tag = "   (unknown scalar/aux block)"
        emit("    %s%s" % (s["hdr"].rstrip(), tag))
    emit("elsets -> parts: " + (", ".join("%s->%s(%d)" % (e, p, len(elsets[e]))
                                         for e, p in elset_map.items()) or "none"))
    emit("NFIX: %d nodes (%s)" % (len(nfix), nfix_src))
    emit("payload %.4f N, rated moments J2=3.5 J3=2.25 J4=0.98 N.m" % payload_n)

    for si, k in enumerate(step_keys):
        blk = bystep[k]
        disp = blk.get("DISP", {}).get("data", {})
        stress = blk.get("STRESS", {}).get("data", {})
        U = np.array([_pad(disp.get(n), 3) for n in ids], dtype=np.float64)
        S = np.array([_pad(stress.get(n), 6) for n in ids], dtype=np.float64)
        um = np.linalg.norm(U, axis=1)
        vm = np.array([vonmises(s) for s in S])
        mult = float(step_mult[si]) if step_mult and si < len(step_mult) else float(si + 1)

        vtu = "%s_step%d.vtu" % (stem, si + 1)
        write_vtu(vtu, nodes, elems,
                  {"DISP": U, "UMAG": um, "VM": vm,
                   "SXX": S[:, 0], "SYY": S[:, 1], "SZZ": S[:, 2]})

        emit("")
        emit("=" * 74)
        emit("STEP %d  (frd step %s)   x%g load   ->  %s" % (si + 1, k, mult, vtu))
        emit("-" * 74)

        # --- max von Mises overall
        im = int(np.argmax(vm)); nmax = ids[im]
        emit("max von Mises = %.2f MPa  at node %d %s  part=%s"
             % (vm[im], nmax, _xyz(nodes[nmax]), part_of(nmax)))

        # --- max |U| overall and at TCP
        iu = int(np.argmax(um)); num = ids[iu]
        emit("max |U| = %.4f mm  at node %d %s  part=%s"
             % (um[iu], num, _xyz(nodes[num]), part_of(num)))
        if tcp is not None:
            t = np.asarray(tcp, dtype=np.float64)
            it = int(np.argmin(np.linalg.norm(pos - t, axis=1)))
            nt = ids[it]
            emit("TCP %s -> nearest node %d %s : |U| = %.4f mm  U=(%.4f, %.4f, %.4f)"
                 % (_xyz(t), nt, _xyz(nodes[nt]), um[it], U[it, 0], U[it, 1], U[it, 2]))

        # --- printed-part table, sorted by max VM desc
        emit("")
        emit("%-24s %8s %11s %11s %8s" % ("printed part", "n_nodes", "maxVM(MPa)", "max|U|(mm)", "SF=25/VM"))
        emit("-" * 74)
        rows = []
        for pname, meta in parts.items():
            if meta.get("cls") != "printed":
                continue
            ii = pidx.get(pname)
            if ii is None or len(ii) == 0:
                rows.append((pname, 0, 0.0, 0.0))
                continue
            rows.append((pname, len(ii), float(vm[ii].max()), float(um[ii].max())))
        for pname, nn, mv, mu in sorted(rows, key=lambda r: -r[2]):
            sf = 25.0 / mv if mv > 0 else float("inf")
            emit("%-24s %8d %11.2f %11.4f %8.2f" % (pname, nn, mv, mu, sf))

        # --- reactions ------------------------------------------------------
        nfix_eff = set(nfix)
        if nfix_src and nfix_src.startswith("z<="):
            nfix_eff = {n for n in nfix if um[idx[n]] < 1e-9}
        rfname = pick_rf_block(blk)
        measured = {}
        Fsum = None
        emit("")
        if rfname:
            rf = blk[rfname]["data"]
            fnodes = [n for n in sorted(nfix_eff) if n in rf]
            F = np.array([_pad(rf[n], 3) for n in fnodes], dtype=np.float64)
            R = np.array([nodes[n] for n in fnodes], dtype=np.float64)
            Fsum = F.sum(axis=0)
            emit("reactions (%s block) summed over %d/%d NFIX nodes:"
                 % (rfname, len(fnodes), len(nfix_eff)))
            emit("    Fx = %10.3f N   Fy = %10.3f N   Fz = %10.3f N"
                 % (Fsum[0], Fsum[1], Fsum[2]))
            for j in ("J2", "J3", "J4"):
                if j not in joints:
                    continue
                jp = np.asarray(joints[j]["pos"], dtype=np.float64)
                ja = np.asarray(joints[j]["axis"], dtype=np.float64)
                nrm = np.linalg.norm(ja)
                if nrm == 0:
                    continue
                ja = ja / nrm
                m_nm = float((np.cross(R - jp, F) @ ja).sum()) / 1000.0
                measured[j] = m_nm
                emit("    %s reaction moment about %s = %8.3f N.m"
                     % (j, _xyz(jp), m_nm))
            My = float((R[:, 2] * F[:, 0] - R[:, 0] * F[:, 2]).sum()) / 1000.0
            measured["base_y"] = My
            emit("    total overturning moment about Y through x=0,z=0 = %8.3f N.m" % My)
        else:
            emit("reactions: NO nodal force block in this step "
                 "(only: %s) -- rerun with *NODE FILE/PRINT RF to get them"
                 % ", ".join(sorted(blk)))

        # --- analytic moments vs rated
        emit("joint moments vs actuator rating (N.m):")
        for j, rated in (("J2", 3.5), ("J3", 2.25), ("J4", 0.98)):
            ana = moments_nm.get(j)
            m = measured.get(j)
            use = m if m is not None else ana
            src = "frd" if m is not None else ("analytic" if ana is not None else None)
            if use is not None and abs(use) > 0:
                emit("    %s reaction %7.2f N.m vs rated %.2f (margin %5.2fx)   [%s; analytic %s]"
                     % (j, abs(use), rated, rated / abs(use), src, _fmt(ana)))
            else:
                emit("    %s reaction n/a vs rated %.2f   [analytic %s]"
                     % (j, rated, _fmt(ana)))
        if "base_y" in moments_nm:
            emit("    base_y analytic %.2f N.m%s"
                 % (moments_nm["base_y"],
                    ("  (frd %.2f)" % measured["base_y"]) if "base_y" in measured else ""))

        # --- top-5 highest-stress nodes
        emit("")
        emit("top-5 highest-stress nodes:")
        for rank, h in enumerate(np.argsort(vm)[-5:][::-1], 1):
            n = ids[h]
            emit("    %d. VM %8.2f MPa  node %d %s  part=%s"
                 % (rank, vm[h], n, _xyz(nodes[n]), part_of(n)))

        # --- sanity: RF_z vs expected weight
        w_parts = sum(float(m.get("mass_kg", 0.0)) for m in parts.values()) * 9.81
        w_exp = w_parts + payload_n * mult
        emit("")
        emit("sanity: RF_z %s N  vs  expected total weight %.3f N "
             "(parts %.3f + payload %.3f x%g)"
             % (_fmt(Fsum[2] if Fsum is not None else None, 3),
                w_exp, w_parts, payload_n, mult))

    txt = "%s.txt" % stem
    Path(txt).write_text("\n".join(out) + "\n")
    print("\nwrote %s" % txt)


if __name__ == "__main__":
    main()
