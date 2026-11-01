"""Find holes near a joint axis in a structural part (world coords).

Usage: python joint_faces.py <stepfile> <ax> <ay> <az> <dx> <dy> <dz> [maxdist]
Lists cylindrical features whose axis is ~parallel to the joint axis
(the horn bolt face) within maxdist of the axis point.
"""
import sys, math
from build123d import import_step, GeomType, Vector

f = sys.argv[1]
pt = Vector(*map(float, sys.argv[2:5]))
d = Vector(*map(float, sys.argv[5:8])).normalized()
maxd = float(sys.argv[8]) if len(sys.argv) > 8 else 45.0

part = import_step(f)
print("bbox:", part.bounding_box().min, "->", part.bounding_box().max)
for face in part.faces():
    if face.geom_type != GeomType.CYLINDER:
        continue
    r = face.radius
    if r > 15:      # skip big bosses, we want holes
        continue
    loc = face.center()
    ad = face.geom_adaptor()
    ax3 = ad.Axis().Direction()
    ax = Vector(ax3.X(), ax3.Y(), ax3.Z())
    # axis alignment
    if abs(ax.dot(d)) < 0.9:
        continue
    # distance from joint axis (perp component)
    v = loc - pt
    perp = v - d * v.dot(d)
    if perp.length > maxd:
        continue
    print(f"  r={r:5.2f} ctr=({loc.X:8.3f},{loc.Y:8.3f},{loc.Z:8.3f}) "
          f"perp={perp.length:6.2f} axial={v.dot(d):7.2f}")
