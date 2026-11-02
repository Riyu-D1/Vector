"""fea_contact.py - D4 task 5: 2D plane-stress CalculiX contact cross-check.

One disc flank arc (the REAL profile around the analytical peak pin's contact
point) + the mating Ø3 ring pin.  Hard contact, pin displacement-driven;
reports F(delta) and max CPRESS to compare with load_model's Hertz p0.

Pipeline: fea_arc.npy/fea_pin.npy/fea_n.npy (written by the extraction step in
STATUS-cyc4.md) -> gmsh .geo -> T6 mesh -> ccx .inp -> run -> parse.
Usage:  $PY fea_contact.py          (ccx run capped at ~19 min by the caller)
"""

import math
import os
import subprocess
import sys

import numpy as np

FB = "/Applications/FreeCAD.app/Contents/Resources/bin"
GMSH = os.path.join(FB, "gmsh")
CCX = os.path.join(FB, "ccx")
HERE = os.path.dirname(os.path.abspath(__file__))
JOB = os.path.join(HERE, "fea", "job")

T_DISC = 4.25        # disc thickness (plane-stress section)
DELTA = 0.014        # total pin drive (mm, into the flank)
NINC = 56            # 0.00025 mm/inc -> fine F(delta) near F* = 12.9 N/disc
RP = 1.5

# ---------------- geometry: local frame, .geo -----------------------------

def build_geo():
    arc = np.load(os.path.join(HERE, "fea_arc.npy"))
    pin = np.load(os.path.join(HERE, "fea_pin.npy"))
    u = np.load(os.path.join(HERE, "fea_n.npy"))
    ct = np.load(os.path.join(HERE, "fea_ct.npy"))
    yhat = -u / np.hypot(*u)          # contact -> pin centre
    xhat = np.array([yhat[1], -yhat[0]])
    loc = lambda p: ((p - ct) @ xhat, (p - ct) @ yhat)
    al = np.array([loc(p) for p in arc])
    # decimate to ~0.12 mm spacing, keep endpoints (gmsh speed)
    keep = [0]
    acc = 0.0
    for i in range(1, len(al)):
        acc += np.hypot(*(al[i] - al[keep[-1]]))
        if acc >= 0.12:
            keep.append(i); acc = 0.0
    if keep[-1] != len(al) - 1:
        keep.append(len(al) - 1)
    al = al[keep]
    pc = np.array(loc(pin))
    np.save(os.path.join(HERE, "fea_pc.npy"), pc)
    print("frame: contact at origin, pin at", np.round(pc, 4),
          "| flank pts", len(al), "y range %.3f..%.3f"
          % (al[:, 1].min(), al[:, 1].max()))
    # wedge: flank polyline, then sides to corners OUTSIDE the arc x-extent
    # (guaranteed no side/flank crossing), bottom closed at y=-7
    xl, xr = al[:, 0].min() - 2.5, al[:, 0].max() + 2.5
    first_left = al[0, 0] < al[-1, 0]
    c_first = (xl if first_left else xr, -7.0)
    c_last = (xr if first_left else xl, -7.0)
    pts = []
    lines = []
    pid = lambda x, y: pts.append((x, y)) or len(pts)
    for x, y in al:
        pid(x, y)
    flank_ids = list(range(1, len(al) + 1))
    ic0 = pid(*c_first); ic1 = pid(*c_last)
    for a, b in zip(flank_ids, flank_ids[1:]):
        lines.append((a, b, "FLANK"))
    lines.append((flank_ids[-1], ic1, "FIX"))
    lines.append((ic1, ic0, "FIX"))
    lines.append((ic0, flank_ids[0], "FIX"))
    geo = []
    geo.append('SetFactory("OpenCASCADE");')
    for i, (x, y) in enumerate(pts, 1):
        lc = 0.04 if (abs(x) < 0.9 and y > -0.9) else 0.5
        geo.append("Point(%d) = {%.6f, %.6f, 0, %.3f};" % (i, x, y, lc))
    for i, (a, b, _) in enumerate(lines, 1):
        geo.append("Line(%d) = {%d, %d};" % (i, a, b))
    fl = [i for i, (_, _, t) in enumerate(lines, 1) if t == "FLANK"]
    fx = [i for i, (_, _, t) in enumerate(lines, 1) if t == "FIX"]
    geo.append("Curve Loop(1) = {%s};"
               % ",".join(str(i) for i in range(1, len(lines) + 1)))
    geo.append("Plane Surface(1) = {1};")
    # pin: full circle on centre pc, radius RP (ids kept clear of line ids)
    cid = 900
    geo.append("Point(%d) = {%.6f, %.6f, 0, 0.2};" % (cid, pc[0], pc[1]))
    pn = []
    for k, a in enumerate((0, 90, 180, 270)):
        pn.append(cid + 1 + k)
        geo.append("Point(%d) = {%.6f, %.6f, 0, 0.1};"
                   % (pn[-1], pc[0] + RP * math.cos(math.radians(a)),
                      pc[1] + RP * math.sin(math.radians(a))))
    for k in range(4):
        geo.append("Circle(%d) = {%d, %d, %d};"
                   % (900 + k, pn[k], cid, pn[(k + 1) % 4]))
    geo.append("Curve Loop(2) = {900,901,902,903};")
    geo.append("Plane Surface(2) = {2};")
    geo.append('Physical Surface("LOBE",1) = {1};')
    geo.append('Physical Surface("PIN",2) = {2};')
    geo.append('Physical Curve("FLANK",3) = {%s};' % ",".join(map(str, fl)))
    geo.append('Physical Curve("FIX",4) = {%s};' % ",".join(map(str, fx)))
    geo.append('Physical Curve("PINEDGE",5) = {900,901,902,903};')
    geo.append('Mesh.MeshSizeFromPoints = 1;')
    geo.append('Mesh.MeshSizeExtendFromBoundary = 0;')
    with open(JOB + ".geo", "w") as f:
        f.write("\n".join(geo) + "\n")
    print("wrote", JOB + ".geo")


# ---------------- msh2 -> ccx inp -----------------------------------------

def msh_to_inp():
    sec = None
    nodes = {}
    elems = []          # (id, type, phys, [nodes])
    phys_names = {}
    with open(JOB + ".msh") as f:
        for ln in f:
            ln = ln.strip()
            if ln.startswith("$"):
                sec = ln
                continue
            if sec == "$PhysicalNames":
                continue
            if sec == "$Nodes":
                t = ln.split()
                if len(t) == 4:
                    nodes[int(t[0])] = (float(t[1]), float(t[2]), float(t[3]))
            elif sec == "$Elements":
                t = ln.split()
                if len(t) >= 4:
                    eid, etype = int(t[0]), int(t[1])
                    ntags = int(t[2])
                    phys = int(t[3]) if ntags else 0
                    elems.append((eid, etype, phys,
                                  [int(x) for x in t[3 + ntags:]]))
            elif sec == "$MeshFormat":
                pass
            elif sec == "$PhysicalNames" and ln.isdigit():
                pass
    # second pass for PhysicalNames is skipped: we know our own tags
    LOBE, PIN, FLANK, FIX, PINEDGE = 1, 2, 3, 4, 5
    t6 = [(e, ph, ns) for e, t, ph, ns in elems if t == 9]
    lobe_el = [(e, ns) for e, ph, ns in t6 if ph == LOBE]
    pin_el = [(e, ns) for e, ph, ns in t6 if ph == PIN]
    if not lobe_el or not pin_el:
        # fall back: classify by element position (x of centroid > -2)
        raise SystemExit("no T6 elements by physical - check physical tags")
    # node sets
    flank_nodes = sorted({n for e, t, ph, ns in elems
                          if t in (8,) and ph == FLANK for n in ns})
    fix_nodes = sorted({n for e, t, ph, ns in elems
                        if t == 8 and ph == FIX for n in ns})
    # master surface = pin boundary edges (element faces of PIN T6 elems)
    edge_map = {}     # frozenset(edge nodes) -> (elem, face)
    for e, ns in pin_el:
        for face, (a, b, m) in enumerate(((0, 1, 3), (1, 2, 4), (2, 0, 5)), 1):
            edge_map[frozenset((ns[a], ns[b], ns[m]))] = (e, face)
    master = []
    for e, t, ph, ns in elems:
        if t == 8 and ph == PINEDGE:
            key = frozenset(ns)
            if key in edge_map:
                master.append(edge_map[key])
    ref_id = max(nodes) + 1
    pc = np.load(os.path.join(HERE, "fea_pc.npy"))
    pin_nodes = sorted({n for e, ns in pin_el for n in ns})
    pin_body = [n for n in pin_nodes]

    def wrap(ids):
        return ",\n".join(
            ",".join(map(str, ids[i:i + 15]))
            for i in range(0, len(ids), 15)) + "\n"

    with open(JOB + ".inp", "w") as f:
        w = f.write
        w("*HEADING\nD4 pin+lobe plane-stress contact cross-check\n")
        w("*NODE\n")
        for n in sorted(nodes):
            x, y, z = nodes[n]
            w("%d,%.6f,%.6f\n" % (n, x, y))
        w("%d,%.6f,%.6f\n" % (ref_id, pc[0], pc[1]))
        w("*NSET,NSET=REF\n%d\n" % ref_id)
        w("*ELEMENT,TYPE=CPS6,ELSET=LOBE\n")
        for e, ns in lobe_el:
            w("%d,%s\n" % (e, ",".join(map(str, ns))))
        w("*ELEMENT,TYPE=CPS6,ELSET=PIN\n")
        for e, ns in pin_el:
            w("%d,%s\n" % (e, ",".join(map(str, ns))))
        w("*NSET,NSET=NFIX\n")
        w(wrap(fix_nodes))
        w("*NSET,NSET=NPINBOD\n")
        w(wrap(pin_body))
        w("*NSET,NSET=NSLAVE\n")
        w(wrap(flank_nodes))
        w("*SURFACE,TYPE=NODE,NAME=SLAVE\n")
        for n in flank_nodes:
            w("%d\n" % n)
        w("*SURFACE,NAME=MASTER\n")
        for e, fa in master:
            w("%d,S%d\n" % (e, fa))
        w("*MATERIAL,NAME=PETG\n*ELASTIC\n4000.0,0.35\n")
        w("*MATERIAL,NAME=STEEL\n*ELASTIC\n210000.0,0.3\n")
        w("*SOLID SECTION,ELSET=LOBE,MATERIAL=PETG\n%.2f\n" % T_DISC)
        w("*SOLID SECTION,ELSET=PIN,MATERIAL=STEEL\n%.2f\n" % T_DISC)
        w("*SURFACE INTERACTION,NAME=CI\n")
        w("*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=HARD\n")
        w("*CONTACT PAIR,INTERACTION=CI,TYPE=NODE TO SURFACE\n")
        w("SLAVE,MASTER\n")
        w("*BOUNDARY\n")
        w("NFIX,1,2\n")
        # rigid pin: every pin node tied to REF in x and y
        w("*EQUATION\n")
        for n in pin_body:
            w("2\n%d,1,1.0,%d,1,-1.0\n" % (n, ref_id))
            w("2\n%d,2,1.0,%d,2,-1.0\n" % (n, ref_id))
        w("*STEP,INC=1000\n")
        w("*STATIC,DIRECT\n")
        w("%.4f,1.0\n" % (1.0 / NINC))
        w("*BOUNDARY\nREF,1,1,0.0\nREF,2,2,%.4f\n" % (-DELTA))
        w("*NODE PRINT,NSET=REF\nRF\n")
        w("*NODE FILE\nU\n")
        w("*CONTACT FILE\nCDIS,CSTR\n")
        w("*EL FILE\nS\n")
        w("*END STEP\n")
    print("wrote %s.inp  nodes=%d  lobe=%d pin=%d master faces=%d"
          % (JOB, len(nodes) + 1, len(lobe_el), len(pin_el), len(master)))
    return len(nodes)


# ---------------- parse results -------------------------------------------

def parse():
    rf = []
    dat = JOB + ".dat"
    if os.path.exists(dat):
        blk = False
        for ln in open(dat):
            if "total force" in ln.lower() or "reaction" in ln.lower():
                blk = True
            if blk and ln.split() and ln.split()[0].lstrip("-").isdigit():
                t = ln.split()
                try:
                    rf.append((int(t[0]), float(t[1]), float(t[2])))
                except Exception:
                    pass
    cmax = 0.0
    frd = JOB + ".frd"
    if os.path.exists(frd):
        cur = None
        for ln in open(frd):
            if ln.startswith(" -4"):
                cur = ln.strip()
            elif ln.startswith(" -1") and cur and "CSTR" in cur:
                try:
                    p = float(ln[12:25])
                    cmax = max(cmax, p)
                except Exception:
                    pass
            elif ln.startswith(" -3") or ln.startswith(" -2"):
                pass
    print("reactions (node,dof,RF):", rf[-8:])
    print("max contact pressure read from frd:", cmax)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "fea"), exist_ok=True)
    if "geo" in sys.argv or len(sys.argv) == 1:
        build_geo()
    if "mesh" in sys.argv or len(sys.argv) == 1:
        subprocess.run([GMSH, "-2", "-order", "2", "-format", "msh2",
                        "-o", JOB + ".msh", JOB + ".geo"], check=True)
        print("nodes:", msh_to_inp())
    if "run" in sys.argv or len(sys.argv) == 1:
        r = subprocess.run([CCX, "-i", JOB], capture_output=True, text=True)
        print(r.stdout[-3000:] if r.stdout else r.stderr[-3000:])
    if "parse" in sys.argv or len(sys.argv) == 1:
        parse()
