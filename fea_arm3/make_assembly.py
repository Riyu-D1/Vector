"""fea_arm/make_assembly.py - stage F2 assembly builder (contract: fea_arm/SPEC.md).

Builds all 38 home solids via cad/arm2b/p_arm2b.py, exports STEP+STL per case,
detects contact/mount pairs, writes parts/contacts manifests and gmsh .geo files.
Run:  $PY fea_arm/make_assembly.py
"""
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent              # fea_arm/
ROOT = HERE.parent                                  # worktree root (fea/)
sys.path.insert(0, str(ROOT / "cad" / "arm2"))
sys.path.insert(0, str(ROOT / "cad" / "arm2b"))

import trimesh                                       # noqa: E402
from build123d import Axis, Pos, export_step, export_stl  # noqa: E402
import p_arm2b as PB                                 # noqa: E402

INP = HERE / "input"
HOME = INP / "step_home"
SIM_MESHES = INP / "sim_meshes"
RUN = HERE / "run"
CASE_DIR = {"AB": INP / "posed_AB", "C": HOME}      # case C reuses home pose (identity)

# ---------------- SPEC.md data (home-pose coords, mm) ----------------
BODIES = [
    ("base",       None,  ["base_plate", "base_link", "j1_cradle", "vendor_sts3250_j1", "base_reinf"]),
    ("upper_base", "J1",  ["yaw_limit", "link1", "front_spacer_j2", "flange_j2", "vendor_actout_j2"]),
    ("upper",      "J2",  ["vendor_act_j2", "back_spacer_j2", "vendor_6803_j2", "upper_out", "upper_back",
                           "vendor_act_j3", "back_spacer_j3", "vendor_6803_j3"]),
    ("fore",       "J3",  ["front_spacer_j3", "flange_j3", "vendor_actout_j3", "dogleg_l", "dogleg_r",
                           "fore_l2", "fore_r2", "j4_cradle", "vendor_sts3215_j4"]),
    ("wrist4",     "J4",  ["link4", "vendor_sts3215_j5"]),
    ("wrist5",     "J5",  ["link5", "vendor_sts3215_j6"]),
    ("grip",       "J6",  ["grip_frame", "vendor_sts3215_g", "vendor_gear_grip", "vendor_rack_u", "vendor_rack_d"]),
    ("finger_u",   "FU",  ["finger_u"]),
    ("finger_d",   "FD",  ["finger_d"]),
]
PARENT = {"upper_base": "base", "upper": "upper_base", "fore": "upper", "wrist4": "fore",
          "wrist5": "wrist4", "grip": "wrist5", "finger_u": "grip", "finger_d": "grip"}
BODJOINT = {b: j for b, j, _ in BODIES}
PART_BODY = {p: b for b, _, ps in BODIES for p in ps}
JOINT_BODY = {j: b for b, j, _ in BODIES if j}

JOINTS = {                                   # name: (home anchor, home axis)
    "J1": ((0.0, 0.0, 80.8),    (0, 0, 1)),
    "J2": ((-20.0, 0.0, 143.5), (0, 1, 0)),
    "J3": ((-20.0, 0.0, 270.2), (0, 1, 0)),
    "J4": ((96.4, 0.0, 216.2),  (0, 1, 0)),
    "J5": ((134.0, 0.0, 240.4), (0, 0, 1)),
    "J6": ((153.2, 0.0, 216.2), (1, 0, 0)),
    "FU": ((125.0, 0.0, 216.2), (0, 1, 0)),    # slide +Y, q mm
    "FD": ((125.0, 0.0, 216.2), (0, -1, 0)),   # slide -Y, q mm
}
SLIDES = {"FU", "FD"}
TCP_HOME = np.array([228.2, 0.0, 216.2])
PAYLOAD_KG = 0.5

CASES = {"AB": {"J2": 90.0, "J3": -90.0}, "C": {}}

MASS = {"vendor_sts3250_j1": 0.075,
        "vendor_sts3215_j4": 0.055, "vendor_sts3215_j5": 0.055, "vendor_sts3215_j6": 0.055,
        "vendor_sts3215_g": 0.055,
        "vendor_act_j2": 0.300, "vendor_act_j3": 0.300,
        "vendor_gear_grip": 0.008, "vendor_rack_u": 0.012, "vendor_rack_d": 0.012,
        "vendor_6803_j2": 0.0075, "vendor_6803_j3": 0.0075}
RHO_PRINTED = 1.27e-3 * 0.6                     # g/mm3 (PETG x fill)
G = 9.81                                       # m/s2 for moments

# mount pairs from SPEC.md (unordered); tolerate up to 3.0 mm for pocket fits
MOUNT = [tuple(sorted(p)) for p in [
    ("vendor_sts3250_j1", "j1_cradle"), ("vendor_sts3250_j1", "yaw_limit"), ("vendor_sts3250_j1", "base_link"),
    ("vendor_act_j2", "vendor_actout_j2"), ("vendor_act_j2", "upper_out"), ("vendor_act_j2", "upper_back"),
    ("vendor_act_j2", "back_spacer_j2"), ("vendor_6803_j2", "back_spacer_j2"), ("vendor_6803_j2", "link1"),
    ("vendor_act_j3", "vendor_actout_j3"), ("vendor_act_j3", "upper_out"), ("vendor_act_j3", "upper_back"),
    ("vendor_act_j3", "back_spacer_j3"), ("vendor_6803_j3", "back_spacer_j3"),
    ("vendor_6803_j3", "fore_l2"), ("vendor_6803_j3", "fore_r2"),
    ("vendor_actout_j2", "front_spacer_j2"), ("vendor_actout_j2", "link1"), ("vendor_actout_j2", "flange_j2"),
    ("vendor_actout_j3", "front_spacer_j3"), ("vendor_actout_j3", "flange_j3"),
    ("vendor_actout_j3", "dogleg_l"), ("vendor_actout_j3", "dogleg_r"),
    ("vendor_sts3215_j4", "j4_cradle"), ("vendor_sts3215_j4", "link4"),
    ("vendor_sts3215_j4", "fore_l2"), ("vendor_sts3215_j4", "fore_r2"),
    ("vendor_sts3215_j5", "link4"), ("vendor_sts3215_j5", "link5"),
    ("vendor_sts3215_j6", "link5"), ("vendor_sts3215_j6", "grip_frame"),
    ("vendor_sts3215_g", "grip_frame"), ("vendor_gear_grip", "grip_frame"),
    ("vendor_gear_grip", "vendor_sts3215_g"), ("vendor_gear_grip", "vendor_rack_u"),
    ("vendor_gear_grip", "vendor_rack_d"), ("vendor_rack_u", "grip_frame"), ("vendor_rack_d", "grip_frame"),
    ("vendor_rack_u", "finger_u"), ("vendor_rack_d", "finger_d"),
    ("finger_u", "grip_frame"), ("finger_d", "grip_frame"),
]]
MOUNT_SET = set(MOUNT)

TOL_AUTO = 0.3            # mm: auto contact threshold (SPEC: ~0.3)
TOL_MOUNT = [0.6, 1.0, 1.5, 2.0, 2.5, 3.0]
MAX_PTS = 400
BBOX_PAD = 2.0            # mm prefilter


# ---------------- transforms ----------------
def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot4(anchor, axis, deg):
    """4x4: rotate `deg` about `axis` through home `anchor` (right-hand rule)."""
    a = math.radians(deg)
    ax = _unit(axis)
    x, y, z = ax
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    R = np.eye(3) * math.cos(a) + (1 - math.cos(a)) * np.outer(ax, ax) + math.sin(a) * K
    M = np.eye(4)
    M[:3, :3] = R
    p = np.asarray(anchor, float)
    M[:3, 3] = p - R @ p
    return M


def slide4(axis, q_mm):
    M = np.eye(4)
    M[:3, 3] = _unit(axis) * q_mm
    return M


def chain(body):
    """ancestor joints leaf->root for `body` (its own joint first)."""
    out = []
    b = body
    while b is not None:
        j = BODJOINT[b]
        if j:
            out.append(j)
        b = PARENT.get(b)
    return out


def body_matrix(body, q):
    """world transform = leaf joint applied FIRST then toward root (serial chain rule)."""
    T = np.eye(4)
    for j in chain(body):                       # leaf -> root
        a = q.get(j, 0.0)
        if abs(a) < 1e-12:
            continue
        anc, ax = JOINTS[j]
        M = slide4(ax, a) if j in SLIDES else rot4(anc, ax, a)
        T = M @ T                               # leaf ends up rightmost (applied first)
    return T


def apply_T(T, pts):
    pts = np.atleast_2d(np.asarray(pts, float))
    return pts @ T[:3, :3].T + T[:3, 3]


def pose_solid(s, body, q):
    """same chain order on a build123d shape: leaf joint rotation first, then toward root."""
    for j in chain(body):
        a = q.get(j, 0.0)
        if abs(a) < 1e-12:
            continue
        anc, ax = JOINTS[j]
        if j in SLIDES:
            d = _unit(ax) * a
            s = Pos(float(d[0]), float(d[1]), float(d[2])) * s
        else:
            s = s.rotate(Axis(tuple(anc), tuple(ax)), a)
    return s


def xform_dir(T, v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return T[:3, :3] @ (v / n)


# ---------------- part build / export ----------------
def build_home():
    t0 = time.time()
    solids = {}
    order = []
    for name, grp, fn in PB.parts():
        s = PB.pose(fn(), grp)
        solids[name] = s
        order.append(name)
        print("  built %-20s grp=%-2s vol=%.0f mm3" % (name, grp, s.volume))
    names = set(order)
    assert len(order) == 38, "expected 38 parts, got %d" % len(order)
    assert names == set(PART_BODY), ("part name mismatch vs BODIES",
                                     sorted(names ^ set(PART_BODY)))
    print("BUILT %d parts in %.1f s" % (len(order), time.time() - t0))
    return solids, order


def export_all(solids, order, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for name in order:
        s = solids[name]
        export_step(s, str(outdir / (name + ".step")))
        if name.startswith("vendor_"):
            export_stl(s, str(outdir / (name + ".stl")), tolerance=0.2, angular_tolerance=0.5)
        else:
            export_stl(s, str(outdir / (name + ".stl")), tolerance=0.05, angular_tolerance=0.4)


def copy_sim_meshes():
    SIM_MESHES.mkdir(parents=True, exist_ok=True)
    src = ROOT / "sim" / "meshes"
    n = 0
    for f in sorted(src.glob("*.stl")):
        shutil.copy2(f, SIM_MESHES / f.name)
        n += 1
    print("COPIED %d sim meshes -> %s" % (n, SIM_MESHES))


# ---------------- contact detection ----------------
def load_meshes(order, mdir):
    meshes = {}
    for name in order:
        m = trimesh.load_mesh(str(mdir / (name + ".stl")), force="mesh")
        meshes[name] = m
    return meshes


def signed_d(mb, pts):
    """signed distance pts->mesh b (negative = inside b)."""
    try:
        return np.asarray(trimesh.proximity.signed_distance(mb, pts))
    except Exception:
        _, dist, _ = trimesh.proximity.closest_point(mb, pts)
        inside = mb.contains(pts)
        return np.where(inside, -np.abs(dist), np.abs(dist))


def subsample(pts, cap=MAX_PTS):
    if len(pts) <= cap:
        return pts
    idx = np.linspace(0, len(pts) - 1, cap).astype(int)
    return pts[idx]


def detect_contacts(order, meshes):
    """returns sorted contact list per SPEC schema."""
    bboxes = {n: meshes[n].bounds for n in order}
    contacts = []
    warnings = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b = order[i], order[j]
            pair = (a, b) if a < b else (b, a)
            in_mount = pair in MOUNT_SET
            ba, bb = bboxes[a], bboxes[b]
            near = bool(np.all(ba[0] <= bb[1] + BBOX_PAD) and np.all(bb[0] <= ba[1] + BBOX_PAD))
            if not near and not in_mount:
                continue
            ma, mb = meshes[a], meshes[b]
            da = signed_d(mb, ma.vertices)       # verts of a -> surface b
            db = signed_d(ma, mb.vertices)       # verts of b -> surface a
            inside = bool((da < 0).any() or (db < 0).any())
            dmin = float(min(np.abs(da).min(), np.abs(db).min()))
            auto_hit = inside or dmin < TOL_AUTO

            def collect(tol):
                pa = ma.vertices[da <= tol]
                pb = mb.vertices[db <= tol]
                if len(pa) and len(pb):
                    return np.vstack([pa, pb])
                return pa if len(pa) else pb

            if in_mount:
                pts = np.empty((0, 3))
                used_tol = TOL_MOUNT[-1]
                for tol in TOL_MOUNT:
                    pts = collect(tol)
                    used_tol = tol
                    if len(pts) >= 6:
                        break
                if len(pts) == 0:
                    warnings.append("MOUNT-EMPTY %s %s (no pts within %.1f mm)" % (a, b, used_tol))
                    contacts.append({"a": pair[0], "b": pair[1], "kind": "mount-empty", "pts": []})
                    continue
                kind = "auto" if auto_hit else "mount"
                contacts.append({"a": pair[0], "b": pair[1], "kind": kind,
                                 "pts": np.round(subsample(pts), 4).tolist()})
            elif auto_hit:
                pts = collect(TOL_AUTO)
                contacts.append({"a": pair[0], "b": pair[1], "kind": "auto",
                                 "pts": np.round(subsample(pts), 4).tolist()})
    contacts.sort(key=lambda c: (c["a"], c["b"]))
    return contacts, warnings


# ---------------- connectivity ----------------
def union_find_orphans(order, contacts):
    par = {n: n for n in order}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[rb] = ra

    for c in contacts:
        if c["pts"]:
            union(c["a"], c["b"])
    root = find("base_plate")
    orphans = sorted(n for n in order if find(n) != root)
    return orphans


# ---------------- per-case pipeline ----------------
def run_case(case, solids, order, export_posed):
    q = CASES[case]
    mdir = CASE_DIR[case]
    print("\n=== CASE %s  q=%s ===" % (case, {k: v for k, v in q.items()}))

    # 1) pose solids + export (case C reuses home dir)
    if export_posed:
        posed = {}
        for name in order:
            posed[name] = pose_solid(solids[name], PART_BODY[name], q)
        export_all(posed, order, mdir)
        print("EXPORTED posed_%s -> %s" % (case, mdir))

    T = {b: body_matrix(b, q) for b, _, _ in BODIES}

    # TCP verification (grip chain on home TCP)
    tcp = apply_T(T["grip"], TCP_HOME)[0]
    print("TCP %-2s = (%.4f, %.4f, %.4f)" % (case, tcp[0], tcp[1], tcp[2]))
    if case == "AB":
        exp = np.array([354.9, 0.0, 89.5])
        err = float(np.linalg.norm(tcp - exp))
        print("VERIFY AB tcp err vs (354.9,0,89.5) = %.4f mm" % err)
        assert err < 0.5, "TCP chain transform mismatch: %s" % (tcp,)

    # 2) meshes for this case
    meshes = load_meshes(order, mdir)

    # 3) contacts
    t0 = time.time()
    contacts, warnings = detect_contacts(order, meshes)
    for w in warnings:
        print("  WARN " + w)
    print("CONTACTS %s: %d pairs in %.1f s" % (case, len(contacts), time.time() - t0))
    cj = {"contacts": contacts}
    with open(INP / ("contacts_%s.json" % case), "w") as fh:
        json.dump(cj, fh, indent=1)

    # 4) parts manifest
    parts = {}
    for name in order:
        m = meshes[name]
        vol = float(m.volume)
        cls = "vendor" if name.startswith("vendor_") else "printed"
        mass = MASS[name] if name in MASS else vol * RHO_PRINTED / 1000.0
        rho = mass * 1e-3 / vol                     # t/mm3
        parts[name] = {"body": PART_BODY[name], "cls": cls, "mass_kg": mass, "rho": rho,
                       "centroid": [float(x) for x in m.centroid],
                       "bbox": [[float(x) for x in m.bounds[0]], [float(x) for x in m.bounds[1]]]}

    joints = {}
    for jn in ("J1", "J2", "J3", "J4", "J5", "J6"):
        body = JOINT_BODY[jn]
        anc, ax = JOINTS[jn]
        pos = apply_T(T[body], np.asarray(anc))[0]
        joints[jn] = {"pos": [float(x) for x in pos], "axis": [float(x) for x in xform_dir(T[body], ax)]}

    def moment(bodies, axis_x):
        s = 0.0
        for bname in bodies:
            for pn in [p for b, _, ps in BODIES for p in ps if b == bname]:
                s += parts[pn]["mass_kg"] * G * (parts[pn]["centroid"][0] - axis_x) / 1000.0
        s += PAYLOAD_KG * G * (tcp[0] - axis_x) / 1000.0
        return s

    moments = {
        "J2": moment(["upper", "fore", "wrist4", "wrist5", "grip", "finger_u", "finger_d"], joints["J2"]["pos"][0]),
        "J3": moment(["fore", "wrist4", "wrist5", "grip", "finger_u", "finger_d"], joints["J3"]["pos"][0]),
        "J4": moment(["wrist4", "wrist5", "grip", "finger_u", "finger_d"], joints["J4"]["pos"][0]),
        "base_y": moment([b for b, _, _ in BODIES], 0.0),
    }

    pj = {"parts": parts, "joints": joints, "tcp": [float(x) for x in tcp], "moments_nm": moments}
    with open(INP / ("parts_%s.json" % case), "w") as fh:
        json.dump(pj, fh, indent=1)

    orphans = union_find_orphans(order, contacts)
    return {"contacts": contacts, "warnings": warnings, "tcp": tcp, "joints": joints,
            "moments": moments, "orphans": orphans,
            "total_mass": sum(p["mass_kg"] for p in parts.values())}


# ---------------- gmsh .geo ----------------
def write_geo(case, order):
    mdir = CASE_DIR[case]
    lines = [
        "SetFactory(\"OpenCASCADE\");",
        "Mesh.ElementOrder = 2;",
        "Mesh.MshFileVersion = 2.2;",
        "",
    ]
    for i, name in enumerate(order, start=1):
        lines.append("v_%d() = ShapeFromFile(\"%s\");" % (i, mdir / (name + ".step")))
    lines.append("")
    for i, name in enumerate(order, start=1):
        lines.append("Physical Volume(\"p_%s\") = v_%d();" % (name, i))
    lines.append("")
    printed = ["v_%d()" % i for i, n in enumerate(order, start=1) if not n.startswith("vendor_")]
    lines.append("pp() = {%s};" % ", ".join(printed))
    lines += [
        "If (clp > 0)",
        "  ptags() = {};",
        "  For i In {0:#pp()-1}",
        "    ppv() = pp(i);",
        "    For j In {0:#ppv()-1}",
        "      ptags() += ppv(j);",
        "    EndFor",
        "  EndFor",
        "  Characteristic Length{ PointsOf{ Volume{ptags()}; } } = clp;",
        "EndIf",
        "",
        "Mesh.CharacteristicLengthMax = cl;",
        "Mesh.CharacteristicLengthMin = 0.8;",
        "Mesh.MinimumElementsPerTwoPi = 10;",
        "Mesh 3;",
        "Save \"%s\";" % (RUN / ("arm_%s.msh" % case)),
        "Printf(\"GMSH DONE nodes=%g elems=%g\", Mesh.NbNodes, Mesh.NbElements);",
        "Exit;",
        "",
    ]
    path = HERE / ("arm_%s.geo" % case)
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    print("WROTE %s" % path)


# ---------------- main ----------------
def main():
    for d in (HOME, SIM_MESHES, RUN, CASE_DIR["AB"]):
        d.mkdir(parents=True, exist_ok=True)
    print("== build home solids ==")
    solids, order = build_home()

    print("== export step_home ==")
    export_all(solids, order, HOME)
    copy_sim_meshes()

    res = {}
    for case in ("AB", "C"):
        res[case] = run_case(case, solids, order, export_posed=(case == "AB"))

    for case in ("AB", "C"):
        write_geo(case, order)

    # ---------------- final summary ----------------
    print("\n================ SUMMARY ================")
    print("parts: %d" % len(order))
    for case in ("AB", "C"):
        r = res[case]
        print("\n--- CASE %s ---" % case)
        print("contacts: %d" % len(r["contacts"]))
        for c in r["contacts"]:
            print("  %-20s %-20s %-11s pts=%d" % (c["a"], c["b"], c["kind"], len(c["pts"])))
        if r["warnings"]:
            print("warnings:")
            for w in r["warnings"]:
                print("  " + w)
        print("connectivity (root=base_plate): %s" %
              ("OK all connected" if not r["orphans"] else "ORPHANS: %s" % ", ".join(r["orphans"])))
        t = r["tcp"]
        print("TCP = (%.4f, %.4f, %.4f)" % (t[0], t[1], t[2]))
        print("total mass = %.4f kg" % r["total_mass"])
        for k in ("J2", "J3", "J4", "base_y"):
            print("  moment %-6s = %+.3f N.m" % (k, r["moments"][k]))
        for jn in ("J1", "J2", "J3", "J4", "J5", "J6"):
            p = r["joints"][jn]["pos"]
            a = r["joints"][jn]["axis"]
            print("  %s pos=(%.3f, %.3f, %.3f) axis=(%.3f, %.3f, %.3f)" % (jn, p[0], p[1], p[2], a[0], a[1], a[2]))
    print("=========================================")


if __name__ == "__main__":
    main()
