"""Measure the community Tarot 4008 STEP (motor axis = Y, stator base face = min Y of the stator)."""
import sys, math
from build123d import import_step, GeomType, Box, Pos
a = import_step(sys.argv[1]); S = sorted(a.solids(), key=lambda s: -s.volume)
bb = a.bounding_box(); print(f"ASSEMBLY x {bb.min.X:.2f}..{bb.max.X:.2f} y {bb.min.Y:.2f}..{bb.max.Y:.2f} z {bb.min.Z:.2f}..{bb.max.Z:.2f}")
big = [s for s in S if s.bounding_box().size.X > 40]
for s in big:
    b = s.bounding_box(); print(f"OD-solid vol={s.volume:.0f} dia={b.size.X:.2f} y {b.min.Y:.2f}..{b.max.Y:.2f}")
# stator = the OD solid with the lowest min Y
st = min(big, key=lambda s: s.bounding_box().min.Y); y0 = st.bounding_box().min.Y
print(f"STATOR_BASE_Y {y0:.2f}")
axis = [s for s in S if abs(s.bounding_box().center().X) < 0.3 and abs(s.bounding_box().center().Z) < 0.3]
for s in axis:
    b = s.bounding_box(); print(f"on-axis solid vol={s.volume:.0f} dia={b.size.X:.2f} y {b.min.Y:.2f}..{b.max.Y:.2f}  below-base={y0 - b.min.Y:.2f}")
sec = st & Pos(0, y0 + 0.15, 0) * Box(60, 0.1, 60)
holes = {}
for e in sec.edges():
    if e.geom_type == GeomType.CIRCLE and e.radius < 20:
        c = e.arc_center; k = (round(e.radius, 2), round(c.X, 2), round(c.Z, 2)); holes[k] = 1
for r, x, z in sorted(holes):
    print(f"BASE_CIRCLE d={2*r:.2f} at x={x:.2f} z={z:.2f}  pcd={2*math.hypot(x, z):.2f} ang={math.degrees(math.atan2(z, x)):.1f}")
