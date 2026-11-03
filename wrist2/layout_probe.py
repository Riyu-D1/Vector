"""wrist2/layout_probe.py - D6 candidate layouts compared at servo-case level.

Two candidate placements of the same 4 vendor cases (STS3250-sized J4 case,
3x STS3215 + gripper). For each we report:
  - joint spans (J4->J5, J5->J6, J6->TCP) and TCP (a,h) in the W frame
  - silhouette: top / bottom extreme over a-bins, max b width, bbox volume of
    the case union (= a proxy for shell volume, walls are ~2 mm everywhere)
  - static J4 torque at the 0.5 kg payload with per-case mass distribution
Run: $PY layout_probe.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
import ap2 as P2
import ap2b as B
import p_arm2b as PB
from build123d import Pos

M_STS = B.M_STS3215          # 0.055 kg each servo
M_CASE_PART = 0.020          # ~20 g shell around each case (2 mm walls est.)
PAYLOAD = 0.5
g = 9.81

# ---------- candidate servo placement tables (W frame) ----------
# key: (horn centre (a,b,h), ly dir, lx dir)
LAYOUTS = {
    "D5 (ref)": dict(B.SERVOS),
    "D-DECK": {
        "j4": B.SERVOS["j4"],
        "j5": ((30.0, 0.0, -17.8), (0, 0, 1), (-1, 0, 0)),    # face UP, keel fin
        "j6": ((53.4, 0.0, 0.56), (1, 0, 0), (0, 0, -1)),     # case above axis
        "g":  ((101.4, 0.0, 0.56), (1, 0, 0), (0, 0, -1)),
    },
    "K-KEEL": {
        "j4": B.SERVOS["j4"],
        "j5": ((30.6, 0.0, 7.6), (0, 0, -1), (-1, 0, 0)),     # face DOWN, top fin
        "j6": ((64.0, 0.0, -11.0), (1, 0, 0), (0, 0, 1)),     # case below axis
        "g":  ((100.0, 0.0, -11.0), (1, 0, 0), (0, 0, 1)),
    },
}
# TCP: rack/finger set rides on the grip horn face.  face = o + 9.6*ly; the
# rack cage + fingers add +20.8 a past the face (B: face 111 -> TCP 131.8).
TCP_EXTRA = 20.8

def axes(servos):
    out = {}
    for k, (o, ly, lx) in servos.items():
        ax = PB.Location if False else None
    return out

def axis_point(servos, key):
    o, ly, lx = servos[key]
    return o  # horn centre = point on the joint axis

def report(name, servos):
    j5 = axis_point(servos, "j5"); j6 = axis_point(servos, "j6"); gc = axis_point(servos, "g")
    face_g = gc[0] + 9.6
    tcp_a = face_g + TCP_EXTRA; tcp_h = gc[2]
    s45 = j5[0]; s56 = j6[0] - j5[0]; s6t = tcp_a - j6[0]
    print("\n=== %s ===" % name)
    print(" axes: J5 (a %.1f h %.1f)  J6 (a %.1f h %.1f)  grip c (a %.1f h %.1f)" % (j5[0], j5[2], j6[0], j6[2], gc[0], gc[2]))
    print(" spans J4->J5 %.1f  J5->J6 %.1f  J6->TCP %.1f   TCP (a %.1f, h %.1f)" % (s45, s56, s6t, tcp_a, tcp_h))
    # case bboxes + union volume
    tot = None
    for k in ("j5", "j6", "g"):
        s = PB.servo_w(k) if servos is B.SERVOS else _servo(servos, k)
        b = s.bounding_box()
        print(" case %-3s a %6.1f..%6.1f  b %6.1f..%6.1f  h %6.1f..%6.1f" %
              (k, b.min.X, b.max.X, b.min.Y, b.max.Y, b.min.Z, b.max.Z))
        tot = s if tot is None else tot + s
    bb = tot.bounding_box()
    print(" union bbox a %.1f..%.1f  b %.1f..%.1f  h %.1f..%.1f  vol %.1f cm3" %
          (bb.min.X, bb.max.X, bb.min.Y, bb.max.Y, bb.min.Z, bb.max.Z, tot.volume / 1000))
    # profile: top/bottom per 10mm a-bin, b max
    import numpy as np
    for a0 in range(-20, 140, 10):
        pass
    # J4 static torque at 0.5 kg: servos+grip masses + payload at TCP
    m_wrist = 4 * M_STS + 3 * M_CASE_PART + B.M_GEAR + 2 * B.M_RACK + 0.01  # j5/j6/g shells+racks+fingers
    t4 = g * (m_wrist * 0.075 + PAYLOAD * tcp_a / 1000.0)
    print(" est wrist+grip mass %.3f kg   J4 static @0.5kg ~ %.3f N.m" % (m_wrist + 0.055, t4))
    return tcp_a, tcp_h

def _servo(servos, key):
    o, ly, lx = servos[key]
    lz = (lx[1] * ly[2] - lx[2] * ly[1], lx[2] * ly[0] - lx[0] * ly[2], lx[0] * ly[1] - lx[1] * ly[0])
    from build123d import Location, Plane
    return Location(Plane(origin=o, x_dir=lx, z_dir=lz)) * PB.servo_kp(0.0, 0.0)

for nm, sv in LAYOUTS.items():
    report(nm, sv)
