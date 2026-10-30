#!/usr/bin/env python3
"""fea_arm3/mesh_parts.py - per-part gmsh meshing + merge into one .msh.

One gmsh process per part STEP (38 runs), then the partial .msh files are
merged with renumbered node/element ids into run/arm_<case>.msh.  Per-part
runs isolate every failure to the exact part (the whole-model PLC errors in
the log came from neighbouring surfaces, not the part itself), and each
part gets its own mesh size: --clp for printed, --clv for vendor, --cl
fallback.  Retry ladder per part: algo3d {given}, then 10, 1, 4, then
0.5x size -- the first that writes tets wins.

    python3 mesh_parts.py --case AB --clp 4 --clv 8   # production
    python3 mesh_parts.py --case AB --cl 20           # pilot
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INP = HERE / "input"
RUN = HERE / "run"
GMSH = "/Applications/FreeCAD.app/Contents/Resources/bin/gmsh"
CASE_DIR = {"AB": INP / "posed_AB", "C": INP / "step_home"}

GEO_TMPL = """SetFactory("OpenCASCADE");
Mesh.MshFileVersion = 2.2;
Mesh.ElementOrder = {order};
Mesh.Algorithm3D = {algo};
v_1() = ShapeFromFile("{step}");
Physical Volume("p_{part}") = v_1();
Mesh.CharacteristicLengthMax = {cl};
Mesh.CharacteristicLengthMin = 0.8;
Mesh.MinimumElementsPerTwoPi = 6;
Mesh 3;
Save "{out}";
Printf("DONE {part} nodes=%g tets=%g", Mesh.NbNodes, Mesh.NbTetrahedra);
Exit;
"""


def read_msh(path):
    """v2.2 ascii -> (phys{tag:name}, nodes{id:(x,y,z)}, tets[(etag,[n])])."""
    phys, nodes, tets = {}, {}, []
    with open(path) as f:
        lines = [l.strip() for l in f]
    i = 0
    while i < len(lines):
        l = lines[i]
        if l == "$PhysicalNames":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
                d, t, nm = lines[i].split(None, 2)
                phys[int(t)] = nm.strip('"')
                i += 1
        elif l == "$Nodes":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
                p = lines[i].split()
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
                i += 1
        elif l == "$Elements":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
                p = lines[i].split()
                etype, ntags = int(p[1]), int(p[2])
                if etype in (4, 11):
                    tags = [int(t) for t in p[3:3 + ntags]]
                    tets.append((tags[0] if tags else 0,
                                 [int(t) for t in p[3 + ntags:]]))
                i += 1
        else:
            i += 1
    return phys, nodes, tets


def mesh_one(part, step, outdir, cl, order, algos, logdir):
    """try each algo in order; return (msh path or None, algo, cl_used)."""
    for algo in algos:
        for scale in (1.0, 0.5):
            geo = GEO_TMPL.format(order=order, algo=algo, step=step,
                                  part=part, cl=cl * scale,
                                  out=outdir / (part + ".msh"))
            gpath = logdir / ("%s_a%d_s%g.geo" % (part, algo, scale))
            gpath.write_text(geo)
            r = subprocess.run([GMSH, str(gpath), "-"], capture_output=True,
                               text=True, timeout=900)
            txt = r.stdout + r.stderr
            (logdir / (gpath.stem + ".log")).write_text(txt)
            m = re.search(r"DONE %s nodes=(\d+) tets=(\d+)" % part, txt)
            if m and int(m.group(2)) > 0 and (outdir / (part + ".msh")).is_file():
                return outdir / (part + ".msh"), algo, cl * scale
    return None, None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, choices=sorted(CASE_DIR))
    ap.add_argument("--cl", type=float, default=8.0)
    ap.add_argument("--clp", type=float, default=0.0,
                    help="mesh size for printed parts (0 = use --cl)")
    ap.add_argument("--clv", type=float, default=0.0,
                    help="mesh size for vendor parts (0 = use --cl)")
    ap.add_argument("--order", type=int, default=1, choices=(1, 2))
    ap.add_argument("--algo", type=int, default=10)
    ap.add_argument("--only", default="", help="comma list: mesh only these")
    ap.add_argument("--merge-only", action="store_true",
                    help="skip meshing, just merge existing parts_msh")
    a = ap.parse_args()

    mdir = CASE_DIR[a.case]
    pj = json.loads((INP / ("parts_%s.json" % a.case)).read_text())
    steps = {s.stem: s for s in sorted(mdir.glob("*.step"))}
    only = set(t for t in a.only.split(",") if t)
    if only:
        steps = {k: v for k, v in steps.items() if k in only}
    assert steps, "no STEPs selected"
    algos = [a.algo] + [x for x in (10, 1, 4) if x != a.algo]

    parts_dir = RUN / "parts_msh"
    log_dir = RUN / "geo_logs"
    parts_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    if not a.merge_only:
        for part, step in sorted(steps.items()):
            cls = pj["parts"][part]["cls"]
            cl = (a.clp if a.clp else a.cl) if cls == "printed" else \
                 (a.clv if a.clv else a.cl)
            path, algo, clu = mesh_one(part, step, parts_dir, cl,
                                       a.order, algos, log_dir)
            if path:
                results[part] = (algo, clu)
                print("  meshed %-24s algo=%d cl=%.1f" % (part, algo, clu))
            else:
                print("  FAILED %-23s (all algos)" % part)
        missing = sorted(set(steps) - set(results))
        if missing:
            print("MISSING parts (no tets): %s" % ", ".join(missing))

    # ---- merge ----
    out = RUN / ("arm_%s.msh" % a.case)
    n_off = e_off = 0
    merged_phys = {}
    buf_nodes, buf_elems = [], []
    total_parts = 0
    for part, step in sorted(steps.items()):
        f = parts_dir / (part + ".msh")
        if not f.is_file():
            continue
        phys, nodes, tets = read_msh(f)
        if not tets:
            print("WARN: %s has no tets, skipped" % part)
            continue
        tagmap = {}
        for t, nm in phys.items():
            if nm.startswith("p_"):
                tagmap[t] = None
        if not tagmap:                      # single-volume part: take it
            tagmap = {t: None for t in phys} or {0: None}
        ptag = len(merged_phys) + 1
        merged_phys[ptag] = "p_%s" % part
        idmap = {}
        for nid, xyz in nodes.items():
            n_off += 1
            idmap[nid] = n_off
            buf_nodes.append((n_off,) + xyz)
        for etag, conn in tets:
            e_off += 1
            buf_elems.append((e_off, 4 if len(conn) == 4 else 11,
                              ptag, [idmap[n] for n in conn]))
        total_parts += 1
    assert buf_nodes and buf_elems, "nothing merged: no tets in any part"
    with open(out, "w") as f:
        w = f.write
        w("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n")
        w("$PhysicalNames\n%d\n" % len(merged_phys))
        for t, nm in merged_phys.items():
            w("3 %d \"%s\"\n" % (t, nm))
        w("$Nodes\n%d\n" % len(buf_nodes))
        for nid, x, y, z in buf_nodes:
            w("%d %.8f %.8f %.8f\n" % (nid, x, y, z))
        w("$EndNodes\n$Elements\n%d\n" % len(buf_elems))
        for eid, etype, ptag, conn in buf_elems:
            w("%d %d 2 %d %d %s\n" % (eid, etype, ptag, ptag,
                                     " ".join(str(n) for n in conn)))
        w("$EndElements\n")
    print("MERGED %d parts -> %s : %d nodes, %d tets"
          % (total_parts, out, len(buf_nodes), len(buf_elems)))
    if total_parts < len(steps):
        sys.exit("FATAL: %d parts missing from merged mesh"
                 % (len(steps) - total_parts))


if __name__ == "__main__":
    main()
