"""verify/code/shock.py - V1 task 3: shock + fatigue estimates.

Shock: rigid-pendulum release from horizontal (AB pose is the horizontal
worst case), free fall through the joint range, hard E-stop in t_stop=0.1 s.
tau_shock = I*domega/dt + tau_g(impact) applied quasi-statically.
Inertia from upgrade1/gravity_up1.py PARTS point masses + 0.5 kg payload
at TCP (x=348.5 mm in AB pose).

Fatigue: Basquin estimate on the FEA stresses (bolt-hole / tooth),
PETG-CF endurance ~0.4x yield at 1e6 cycles [U] (see STATUS for source),
exponent b=-0.08 [U].
"""
import math
import sys
import numpy as np

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/upgrade1")
import gravity_up1 as gu

G = 9.81
PAYLOAD = 0.5          # kg at TCP
TCP_X = 348.5          # mm, AB pose (grip furthest part ~348.5)
J2X, J2Z = -20.0, 143.5
J3X, J3Z = 106.7, 143.5
J4X, J4Z = 223.1, 89.5          # wrist4 origin


def joint_stats(jx, jz, bodies):
    """I about the joint y-axis and gravity torque in the horizontal pose."""
    I = 0.0
    d_num = 0.0
    m_tot = 0.0
    for body, mass, cmm in gu.PARTS:
        if body not in bodies:
            continue
        r2 = (cmm[0] - jx) ** 2 + (cmm[2] - jz) ** 2
        I += mass * r2 / 1e6
        d_num += mass * (cmm[0] - jx)
        m_tot += mass
    I += PAYLOAD * (TCP_X - jx) ** 2 / 1e6
    d_num += PAYLOAD * (TCP_X - jx)
    m_tot += PAYLOAD
    d_cm = d_num / m_tot              # horizontal centroid distance (mm)
    tau_g = m_tot * G * d_cm / 1000.0  # N.m at horizontal
    return I, d_cm, m_tot, tau_g


def shock(jx, jz, bodies, drop_deg, t_stop=0.1):
    I, d_cm, m, tau0 = joint_stats(jx, jz, bodies)
    # pendulum: KE at impact = m*g*d_cm*sin(drop) ; omega = sqrt(2 KE / I)
    ke = m * G * (d_cm / 1000.0) * math.sin(math.radians(drop_deg))
    om = math.sqrt(2.0 * ke / I)
    alpha = om / t_stop
    tau_dec = I * alpha
    tau_imp_g = m * G * (d_cm / 1000.0) * math.cos(math.radians(drop_deg))
    return dict(I=I, d_cm=d_cm, m=m, tau0=tau0, ke=ke, om=om,
                tau_dec=tau_dec, tau_peak=tau_dec + tau_imp_g)


DOWN_J2 = ("upper", "fore", "wrist4", "wrist5", "grip")
DOWN_J3 = ("fore", "wrist4", "wrist5", "grip")
DOWN_J4 = ("wrist4", "wrist5", "grip")

print("=== static gravity torque (AB pose = horizontal) ===")
for nm, jx, jz, b in (("J2", J2X, J2Z, DOWN_J2), ("J3", J3X, J3Z, DOWN_J3),
                     ("J4", J4X, J4Z, DOWN_J4)):
    I, d, m, t = joint_stats(jx, jz, b)
    print("%s: m=%.3f kg  d_cm=%.1f mm  I=%.4f kg.m2  tau_g=%.3f N.m  x2=%.2f N.m"
          % (nm, m, d, I, t, 2 * t))

print("=== shock: release from horizontal through joint range, 0.1 s stop ===")
# J2 range +-70 deg (ROM per up1 spring note); J3 similar; J4 shorter, use 90
for nm, jx, jz, b, drop in (("J2", J2X, J2Z, DOWN_J2, 70.0),
                            ("J3", J3X, J3Z, DOWN_J3, 70.0),
                            ("J4", J4X, J4Z, DOWN_J4, 90.0)):
    r = shock(jx, jz, b, drop)
    print("%s: KE=%.2f J omega=%.1f rad/s tau_dec=%.2f N.m tau_peak=%.2f N.m (static %.2f -> dynamic x%.1f)"
          % (nm, r["ke"], r["om"], r["tau_dec"], r["tau_peak"], r["tau0"],
             r["tau_peak"] / r["tau0"]))

print("=== fatigue (Basquin, PETG-CF) ===")
# [U] endurance: FFF PETG fatigue strength ~0.35-0.45 of yield at 1e6 cyc
# (literature, see STATUS).  yield(allowable) 25 MPa -> Se(1e6) ~ 10 MPa [U].
SE_1E6 = 10.0
B_EXP = -0.08          # [U] Basquin exponent for FFF polymers
for label, s in (("example 20 MPa", 20.0),):
    n = 1e6 * (s / SE_1E6) ** (1.0 / B_EXP)
    print("%s -> N %.2e cycles" % (label, n))
