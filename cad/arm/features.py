"""Dump cylindrical + planar face features of a STEP part.

Usage: python features.py <stepfile> [radius_min radius_max]
"""
import sys
from collections import defaultdict
from build123d import import_step, GeomType, Vector

f = sys.argv[1]
rmin = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
rmax = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9

part = import_step(f)
print("bbox:", part.bounding_box().min, "->", part.bounding_box().max)

cyls = defaultdict(list)
for face in part.faces():
    if face.geom_type == GeomType.CYLINDER:
        r = face.radius
        loc = face.center()
        ad = face.geom_adaptor()
        ax3 = ad.Axis().Direction()  # cylinder axis direction
        ax = Vector(ax3.X(), ax3.Y(), ax3.Z())
        cyls[round(r, 2)].append((loc, ax))

for r in sorted(cyls):
    if not (rmin <= r <= rmax):
        continue
    feats = cyls[r]
    print(f"\n--- r={r} (d={2*r}) x{len(feats)}")
    for c, ax in feats:
        print(f"   ctr=({c.X:8.3f},{c.Y:8.3f},{c.Z:8.3f}) ax=({ax.X:5.2f},{ax.Y:5.2f},{ax.Z:5.2f})")
