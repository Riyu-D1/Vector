import glob, sys, trimesh
P = ["housing","mid_plate","hub","disc1","disc2","carrier","out_flange","pin_ring","front_ring"]
ok = True; zmin, zmax, rmax = 1e9, -1e9, 0.0
for n in P:
    m = trimesh.load_mesh(f"out/{n}.stl", force="mesh"); m.merge_vertices()
    b = m.bounds; zmin = min(zmin, b[0][2]); zmax = max(zmax, b[1][2])
    r = float(((m.vertices[:, :2] ** 2).sum(1) ** 0.5).max()); rmax = max(rmax, r)
    wt = bool(m.is_watertight); ok &= wt
    print(f"{n}: watertight={wt} rmax={r:.2f}")
L = zmax - zmin
print(f"LENGTH {L:.2f} {'OK' if L <= 55.0 + 0.01 else 'BAD'}"); ok &= L <= 55.01
print(f"OD {2*rmax:.2f} {'OK' if 2*rmax <= 57.0 + 0.02 else 'BAD'}"); ok &= 2 * rmax <= 57.02
print("ACT PASS" if ok else "ACT FAIL"); sys.exit(0 if ok else 1)
