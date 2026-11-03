"""wrist2/envelope_check.py - verify the K-KEEL v2 placement analytically:
servo case bboxes (with plugs), the fixed/moving gap rules, and the J4-sweep
R>19 corner rule for fixed parts in the cradle b-band."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
from build123d import Location, Plane
import ap2b as B
import p_arm2b as PB

SERVOS = {
    "j5": ((30.6, 0.0, 7.6), (0, 0, -1), (-1, 0, 0)),
    "j6": ((57.0, 0.0, -17.0), (1, 0, 0), (0, 0, 1)),
    "g":  ((101.4, 0.0, -17.0), (1, 0, 0), (0, 0, 1)),
}
def servo(key):
    o, ly, lx = SERVOS[key]
    lz = (lx[1]*ly[2]-lx[2]*ly[1], lx[2]*ly[0]-lx[0]*ly[2], lx[0]*ly[1]-lx[1]*ly[0])
    return Location(Plane(origin=o, x_dir=lx, z_dir=lz)) * PB.servo_kp(0.0, 0.0)

for k in SERVOS:
    b = servo(k).bounding_box()
    print("%s case+plug+horn  a %6.2f..%6.2f  b %6.2f..%6.2f  h %6.2f..%6.2f" %
          (k, b.min.X, b.max.X, b.min.Y, b.max.Y, b.min.Z, b.max.Z))
    s = Location(Plane(origin=SERVOS[k][0], x_dir=SERVOS[k][2], z_dir=(0,1,0))) * PB.servo_kp(0.0, 0.0, horn=False)

# case-only (no plug/horn) bboxes
print()
for k in SERVOS:
    o, ly, lx = SERVOS[k]
    lz = (lx[1]*ly[2]-lx[2]*ly[1], lx[2]*ly[0]-lx[0]*ly[2], lx[0]*ly[1]-lx[1]*ly[0])
    s = Location(Plane(origin=o, x_dir=lx, z_dir=lz)) * PB.servo_kp(0.0, 0.0, horn=False)
    s = s - PB.box(-200, -100, -200, 200, -200, 200)   # hack: show plain box only
    b = PB.servo_kp(0.0, 0.0, horn=False).bounding_box()
    print("kp no-horn box x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % (b.min.X,b.max.X,b.min.Y,b.max.Y,b.min.Z,b.max.Z))
    break

# J4-sweep R rule: point (a,h) in the cradle b-band must satisfy
#   R>19.0 to dip below -14.5 before reaching a=12.3, or never reach a<12.3
def r19(a, h):
    R = math.hypot(a, h)
    if R <= 12.3: return "inside circle (never reaches)" if R < 12.29 else "on boundary"
    th = math.degrees(math.acos(12.3 / R))
    hp = -R * math.sin(math.radians(th))
    return "R=%.1f enters a12.3 at %.1f deg, h'=%.1f %s" % (R, th, hp, "CLEAR" if abs(hp) > 14.5 else "HIT")
for nm, a, h in [("fin front-bottom", 19.6, -0.1), ("fin front a20", 20.0, -0.1),
                 ("horn plate tail", 23.6, -6.15), ("rail tail", 21.0, -2.15),
                 ("keel front-top", 28.8, -6.89), ("keel front-bottom", 21.0, -54.0),
                 ("plate front", 36.6, -2.15)]:
    print("%-18s (%.1f, %.1f): %s" % (nm, a, h, r19(a, h)))
