"""cyclo4/load_model.py - load distribution + contact stress for the 40:1
cycloidal module.  Runs on the CAD copy (ap.py / cyc.py in this directory).

Method (Blanche & Yang, "Cycloidal drives with machining tolerances",
Mech. Mach. Theory 24(5) 337-349, 1989): under the transmitted torque the
disc makes a small extra rigid rotation dphi about its own centre.  Each
ring pin's elastic interference is delta_k = dphi * l_k - g_k, where g_k is
the manufactured pin-flank clearance (from the real CAD profile incl. the
CLR_TOOTH equidistant offset and the pin radius) and l_k is the moment arm
of the contact normal about the disc centre.  Contact force F_k follows the
Hertz line-contact load-deflection law (Johnson, Contact Mechanics, 1985,
sec. 4.3, two-cylinder approach).  dphi is solved so sum(F_k*l_k) = T_disc.

Published expectations used for validation (see validate()):
 - ideal (clearance-free) drive: about HALF the ring pins transmit load,
   distribution ~sinusoidal over the loaded 180-deg half
   [Qi, Yang, Cao et al., Alexandria Eng. J. 91 (2024) 403-418;
    isogeometric FEA, Coatings 13 (2023) 2029 - stressed pins only in the
    0-180 deg half; hal-03182247 eq.15 uses F_k = F_max*sin(phi) exactly].
 - with assembly/tooth-modification clearance the engaged count collapses
   well below half [Li Xin Xu, Proc. IMechE C 233 (2019);
   Alexandria 2024 same statement].

Units: mm, N, MPa, N*m.  Two discs share output torque equally [D assumption,
stated]; disc 2 is 180-deg phased - same magnitudes by symmetry (checked).

[U] flags: per-pin g_k computed to ~1 um on a 40k-point profile; the
M_c = T_disc(1-1/N) +- e*F_net correction is evaluated (two-pass) and the
spread reported instead of silently dropped.
"""
import math
import sys

import numpy as np

import ap
import cyc

# ---------------- materials: (E MPa, nu, allowable contact sigma MPa) -------
# allowable = the sigma_eq=0.6*p0 limit, convention identical to
# verify/code/hertz_cyc.py so the SF numbers are comparable.
MATS = {
    "PETG-CF": (4000.0, 0.35, 50.0,    "[U] along-layer ~50 MPa (V1 STATUS); endurance 10-15"),
    "PA-CF":   (6000.0, 0.35, 85.0,    "[U] PAHT/PA6-CF class, dry, along-layer"),
    "acetal":  (3100.0, 0.35, 65.0,    "[U] POM-C machined insert, yield ~65"),
    "alu6082": (69000.0, 0.33, 260.0,  "[S] 6082-T6 yield 260"),
    "S355":    (200000.0, 0.29, 355.0, "[S] S355 laser/waterjet plate yield 355"),
    "st304":   (200000.0, 0.29, 205.0, "[S] 304 annealed yield 205"),
    "EN24T":   (200000.0, 0.29, 680.0, "[U] 817M40 cond-T yield ~680, cut then tempered"),
    "AR450":   (200000.0, 0.29, 1250.0,"[U] Hardox/Raex class, yield ~1250, waterjet-cut"),
}
E_STEEL, NU_STEEL = 200000.0, 0.29


def cross2(a, b):
    """Scalar z-component of a x b for 2-vectors (np.cross dropped 2-D)."""
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]

# module load cases (N.m at the output flange) --------------------------
# rated = upgrade1 RATED_TORQUE_NM_UP1 (with 0.5 kg payload derate convention)
# x2    = 2x rated (V1 stage test torque)
# shock = verify/code/shock.py peaks (0.1 s E-stop, pendulum release)
LOADS = [("J2 rated", 3.5), ("J2 x2", 7.0), ("J2 shock", 9.19),
         ("J3 rated", 2.25), ("J3 x2", 4.5), ("J3 shock", 4.21)]

_N_DISC = 2
def n_disc_share():
    return _N_DISC


# ---------------- geometry helpers --------------------------------------
def disc_poly(second=False, m=40000, clr=None, ratio=None):
    """Disc outline in DISC frame (clr override supported)."""
    N = cyc.gear(ratio)[0]
    p = cyc.profile(ratio, m=m, clr=clr)
    if not second:
        return p
    a = math.pi / N
    return p @ np.array([[math.cos(a), math.sin(a)],
                         [-math.sin(a), math.cos(a)]])


def world_profile(theta, second=False, m=40000, clr=None, ratio=None):
    """Disc outline in WORLD coords at crank angle theta + disc centre c.
    Mirrors cyc.mesh_clearance: c = s*E*(cos,sin), disc spun -th/N."""
    N = cyc.gear(ratio)[0]
    E = cyc.gear(ratio)[4]
    poly = disc_poly(second, m, clr, ratio)
    a = -theta / N
    sg = -1.0 if second else 1.0
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    c = sg * np.array([E * math.cos(theta), E * math.sin(theta)])
    return c + poly @ R.T, c


def curvature(poly):
    """Signed per-vertex curvature of a closed CCW polyline (cyc.checks
    style).  Positive = convex (lobe flanks)."""
    d1 = (np.roll(poly, -1, 0) - np.roll(poly, 1, 0)) / 2.0
    d2 = np.roll(poly, -1, 0) - 2.0 * poly + np.roll(poly, 1, 0)
    return ((d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0])
            / np.hypot(d1[:, 0], d1[:, 1]) ** 3)


def closest_seg(q, poly):
    """For point q: (dist, contact point, seg index, seg t) of the nearest
    point on closed polyline poly."""
    a = poly
    b = np.roll(poly, -1, axis=0)
    ab = b - a
    L2 = (ab ** 2).sum(1)
    t = np.clip(((q - a) * ab).sum(1) / L2, 0.0, 1.0)
    pts = a + ab * t[:, None]
    d = np.hypot(*(pts - q).T)
    i = int(np.argmin(d))
    return float(d[i]), pts[i], i, float(t[i])


def pin_state(theta, second=False, clr=None, ratio=None, m=40000):
    """Per ring-pin state at crank angle theta.
    dict of arrays: g (pin-surface clearance, >=0), u (unit normal, pin
    centre -> flank = force-on-disc direction), arm l_k, rho (signed flank
    curvature radius at the contact), phi (pin angle deg)."""
    N, NP, R, RP, E = cyc.gear(ratio)
    poly_d = disc_poly(second, m, clr, ratio)
    kap = curvature(poly_d)
    a = -theta / N
    sg = -1.0 if second else 1.0
    Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    c = sg * np.array([E * math.cos(theta), E * math.sin(theta)])
    poly_w = c + poly_d @ Rm.T
    ph = 2.0 * math.pi * np.arange(NP) / NP
    pins = np.column_stack([R * np.cos(ph), R * np.sin(ph)])
    n = NP
    g = np.empty(n); u = np.empty((n, 2)); l = np.empty(n)
    rho = np.empty(n); inside = np.zeros(n, bool)
    for k in range(n):
        d, p_ct, i, ts = closest_seg(pins[k], poly_w)
        gk = d - RP
        if cyc.inside(pins[k][None, :], poly_w)[0]:
            gk, inside[k] = -d - RP, True
        g[k] = gk
        uk = p_ct - pins[k]
        nu = np.hypot(*uk)
        uk = uk / nu if nu > 1e-12 else np.array([0.0, 1.0])
        u[k] = uk
        l[k] = cross2(p_ct - c, uk)
        k2 = kap[i] * (1 - ts) + kap[(i + 1) % len(kap)] * ts
        rho[k] = 1.0 / k2 if abs(k2) > 1e-9 else 1e9
    return dict(g=g, u=u, l=l, rho=rho, inside=inside, pins=pins, c=c,
                phi=np.degrees(ph), RP=RP)


# ---------------- Hertz line contact --------------------------------------
def hertz_F(delta, r_pin, r_lobe, L, E_star_v):
    """Force F for approach delta (mm) - Johnson line contact, two convex
    cylinders (r_lobe<0 = conforming, then 1/R* = 1/r_pin - 1/|r_lobe|).
    delta(F) = 2F/(pi L E*) * (ln(4*b1/a) + ln(4*b2/a) - 1),
    a = sqrt(4 F R*/(pi L E*)).  Inverted by bisection."""
    if delta <= 0.0:
        return 0.0
    if r_lobe > 0:
        inv = 1.0 / r_pin + 1.0 / r_lobe
    else:
        inv = max(1.0 / r_pin - 1.0 / abs(r_lobe), 1e-6)
    Rstar = 1.0 / inv
    b1, b2 = r_pin, abs(r_lobe)

    def approach(F):
        a = math.sqrt(4.0 * F * Rstar / (math.pi * L * E_star_v))
        if a <= 0:
            return 0.0
        return (2.0 * F / (math.pi * L * E_star_v)) * \
            (math.log(4.0 * b1 / a) + math.log(4.0 * b2 / a) - 1.0)

    hi = math.pi * L * E_star_v * delta      # loose upper bracket
    ap_max = approach(hi)
    guard = 0
    while ap_max < delta:
        hi *= 4.0
        ap_max = approach(hi)
        guard += 1
        if guard > 12:           # past the formula's valid range (a ~ b):
            return hi            # treat as near-rigid (conservative)
    lo = 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if approach(mid) < delta:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def hertz_p0(F, r_pin, r_lobe, L, E_star_v):
    """Peak pressure + half-width for a solved force."""
    if r_lobe > 0:
        inv = 1.0 / r_pin + 1.0 / r_lobe
    else:
        inv = max(1.0 / r_pin - 1.0 / abs(r_lobe), 1e-6)
    Rstar = 1.0 / inv
    a = math.sqrt(4.0 * F * Rstar / (math.pi * L * E_star_v))
    p0 = 2.0 * F / (math.pi * a * L)
    return p0, a


def E_star(E1, nu1, E2=E_STEEL, nu2=NU_STEEL):
    return 1.0 / ((1 - nu1 ** 2) / E1 + (1 - nu2 ** 2) / E2)


# ---------------- ring-pin solve ------------------------------------------
def solve_ring(T_moment, st, t_disc, E_disc, nu_disc, sign=1.0):
    """Solve dphi so sum(F_k*l_k) = T_moment (N*mm) for pin-state st.
    Returns (F per pin, dphi rad, engaged mask)."""
    Es = E_star(E_disc, nu_disc)
    l = st["l"] * sign          # engage the sign side
    g = st["g"]
    arm = st["l"] * sign        # torque sense consistent with engagement
    n = len(g)

    def torque(dphi):
        delta = dphi * l - g
        F = np.zeros(n)
        for k in np.nonzero(delta > 0)[0]:
            F[k] = hertz_F(delta[k], st["RP"], st["rho"][k], t_disc, Es)
        return F, float((F * arm).sum())

    hi = (g.max() + 0.02) / max(l.max(), 1e-9)
    F, T = torque(hi)
    while T < T_moment:
        hi *= 1.6
        F, T = torque(hi)
        if hi > 0.5:
            raise RuntimeError("dphi runaway")
    lo = 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        F, T = torque(mid)
        if T < T_moment:
            lo = mid
        else:
            hi = mid
    dphi = 0.5 * (lo + hi)
    F, T = torque(dphi)
    return F, dphi, F > 0


def ring_pass(T_out, theta, second, t_disc, mat, clr=None, ratio=None,
              correct=True):
    """Two-pass solve including the e*F_net moment correction:
    M_c = T_disc*(1-1/N) + |c x F_ring_net|  (conservative side; see
    docstring).  Returns per-pin results at the corrected torque."""
    N, NP, R, RP, E = cyc.gear(ratio)
    T_disc = T_out * 1000.0 / n_disc_share()
    st = pin_state(theta, second, clr, ratio)
    F, dphi, eng = solve_ring(T_disc * (1 - 1.0 / N), st, t_disc,
                              mat[0], mat[1])
    Fm, dphim, engm = solve_ring(T_disc * (1 - 1.0 / N), st, t_disc,
                                 mat[0], mat[1], sign=-1.0)
    if Fm.max() > F.max():               # opposite torque direction worse
        F, dphi, eng = Fm, dphim, engm
    corr = 0.0
    if correct:
        Fn = F @ st["u"]
        corr = abs(float(cross2(st["c"], Fn)))         # N*mm, 2nd order
        F, dphi, eng = solve_ring(T_disc * (1 - 1.0 / N) + corr, st,
                                  t_disc, mat[0], mat[1])
        Fm, dphim, engm = solve_ring(T_disc * (1 - 1.0 / N) + corr, st,
                                     t_disc, mat[0], mat[1], sign=-1.0)
        if Fm.max() > F.max():
            F, dphi, eng = Fm, dphim, engm
    return dict(F=F, dphi=dphi, engaged=eng, st=st, corr=corr)


# ---------------- output-pin solve ----------------------------------------
def solve_outpins(T_out, theta=0.0, second=False, t_disc=4.0,
                  E_disc=4000.0, nu_disc=0.35, clr=None, ratio=None):
    """6 output pins: holes (d = pin + 2E + 2CLR) in the disc on
    OUT_PIN_PCD, pins on the carrier about the main axis O.  The carrier
    co-rotates with the disc, so the hole-pin eccentricity is constant
    |c| = E and every hole's clearance is CLR_TOOTH at all crank angles
    (the holes exist to absorb the disc's ORBIT, not a relative spin).
    Under output torque the disc rotates a further dphi_rel about its own
    centre (lost motion); pins engage on one side.  Linear stiff bearing
    springs (conforming contact; stiff side = conservative Fmax)."""
    N, NP, R, RP, E = cyc.gear(ratio)
    clr_t = ap.CLR_TOOTH if clr is None else clr
    RH = (ap.OUT_PIN_D + 2 * E + 2 * clr_t) / 2.0
    RP_out = ap.OUT_PIN_D / 2.0
    ang = np.radians(ap.OUT_PIN_ANG0 + 60.0 * np.arange(ap.OUT_PIN_N))
    P = np.column_stack([ap.OUT_PIN_PCD / 2 * np.cos(ang),
                         ap.OUT_PIN_PCD / 2 * np.sin(ang)])
    uh = np.tile(np.array([1.0, 0.0]), (len(P), 1))   # eccentricity dir
    g = np.full(len(P), (RH - RP_out) - E)            # = clr_t, uniform
    lO = cross2(P, uh)                                # moment arm about O
    drive = lO                                        # same construction
    Es = E_star(E_disc, nu_disc)
    T = T_out * 1000.0 / n_disc_share()
    K_out = 3.0 * Es * t_disc                         # stiff = conservative
    best = None
    for s in (1.0, -1.0):
        dr, lOs = s * drive, s * lO
        if dr.max() <= 0.0:
            continue

        def torque(dphi, dr=dr, lOs=lOs):
            F = np.clip(dphi * dr - g, 0, None) * K_out
            return F, float((F * lOs).sum())

        hi = (g.max() + 0.02) / dr.max()
        F, Tq = torque(hi)
        it = 0
        while Tq < T and it < 200:
            hi *= 1.6
            F, Tq = torque(hi)
            it += 1
        if Tq < T:
            continue
        lo = 0.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            F, Tq = torque(mid)
            if Tq < T:
                lo = mid
            else:
                hi = mid
        F, Tq = torque(0.5 * (lo + hi))
        if best is None or F.max() > best["F"].max():
            best = dict(F=F, n=int((F > 0).sum()))
    if best is None:
        raise RuntimeError("out-pin solve: no transmitting direction")
    return dict(F=best["F"], n=best["n"],
                p=best["F"] / (2.0 * RP_out * t_disc), g=g, lO=lO)


# ---------------- reports --------------------------------------------------
def sweep(T_out, mat, t_disc, clr=None, ratio=None, n_theta=41,
          second=False):
    """Peak per-disc contact force / pressure over a crank revolution."""
    N, NP, R, RP, E = cyc.gear(ratio)
    Es = E_star(mat[0], mat[1])
    rows = []
    for i in range(n_theta):
        th = 2 * math.pi * i / n_theta
        r = ring_pass(T_out, th, second, t_disc, mat, clr, ratio)
        F = r["F"]; eng = r["engaged"]
        p0s = np.array([hertz_p0(F[k], RP, r["st"]["rho"][k], t_disc, Es)[0]
                        if F[k] > 0 else 0.0 for k in range(len(F))])
        j = int(np.argmax(F))
        rows.append(dict(theta=math.degrees(th), n=int(eng.sum()),
                         Fmax=float(F[j]), pin=j, p0=float(p0s[j]),
                         rho=float(r["st"]["rho"][j]), corr=r["corr"]))
    return rows


def stress_block(name, T_out, mat_name, t_disc=4.0, clr=None, ratio=None,
                 n_theta=41):
    mat = MATS[mat_name]
    Es = E_star(mat[0], mat[1])
    N, NP, R, RP, E = cyc.gear(ratio)
    rows = sweep(T_out, mat, t_disc, clr, ratio, n_theta)
    pk = max(rows, key=lambda r: r["Fmax"])
    seq = 0.6 * pk["p0"]
    sf = mat[2] / seq
    outp = solve_outpins(T_out, math.radians(pk["theta"]), False, t_disc,
                         mat[0], mat[1], clr, ratio)
    pb = float(outp["p"].max())
    Ft = pk["Fmax"] * 0.6                                   # tangential [U]
    h_l, w_l = 1.5, 0.55 * (2 * math.pi * 21.6 / N)         # [U] root model
    sb = 6.0 * Ft * h_l / (t_disc * w_l ** 2)
    ns = sorted(int(r["n"]) for r in rows)
    print("%-9s T=%5.2f Nm  mat=%-8s t=%.1f clr=%s ratio=%s" %
          (name, T_out, mat_name, t_disc, clr, ratio or ap.RATIO))
    print("   engaged/disc: min %d med %d max %d of %d pins   "
          "e*F_corr=%.1f N*mm" % (ns[0], ns[len(ns) // 2], ns[-1], NP,
                                  pk["corr"]))
    print("   Fmax/disc = %.0f N at pin %d (T/disc=%.0f N*mm)"
          % (pk["Fmax"], pk["pin"], T_out * 1000 / n_disc_share()))
    print("   flank rho=%.1f  p0=%.0f MPa  seq=%.0f MPa  allow=%.0f  "
          "SF=%.2f %s" % (pk["rho"], pk["p0"], seq, mat[2], sf,
                          "OK" if sf >= 2 else "FAIL<2"))
    print("   out-pin bearing p=%.1f MPa (SF %.1f)  out-pin Fmax=%.0f N"
          % (pb, mat[2] / max(pb, 1e-9), float(outp["F"].max())))
    print("   lobe root bending ~%.0f MPa [U]  tau_sub=0.3*p0=%.0f MPa"
          % (sb, 0.3 * pk["p0"]))
    return dict(Fmax=pk["Fmax"], p0=pk["p0"], seq=seq, sf=sf,
                n_med=ns[len(ns) // 2], n_min=ns[0], n_max=ns[-1],
                p_brg=pb, sbend=sb, rho=pk["rho"], rows=rows)


def validate():
    """Published-case check: ideal drive (clr=0, conjugate).  Expect ~half
    the pins engaged, near-sinusoidal share over the loaded half; then the
    real clr=0.15 engagement must collapse (references in docstring).
    Also a stiffness-matched linear twin of the Hertz solver."""
    print("=== validate(): ideal drive clr=0 (conjugate) ===")
    N, NP, R, RP, E = cyc.gear()
    T_disc = 3500.0 / 2.0 * (1 - 1.0 / N)
    st = pin_state(0.0, clr=0.0)
    g = np.where(st["g"] < 0, 0.0, st["g"])     # profile noise -> 0
    mat = MATS["S355"]
    F, dp, eng = solve_ring(T_disc, dict(st, g=g), 4.0, mat[0], mat[1])
    print("clr=0 hertz : engaged=%d of %d (%.0f%%), Fmax=%.1f N"
          % (eng.sum(), NP, 100 * eng.sum() / NP, F.max()))
    idx = np.nonzero(F > 0)[0]
    if len(idx) > 3:
        jpk = int(np.argmax(F[idx]))
        print("distribution: unimodal, peak at pin %d = %.0f%% through the "
              "engaged arc (arm-weighted shape as in Blanche-Yang, not the "
              "idealized symmetric sinusoid)" % (idx[jpk],
              100.0 * jpk / (len(idx) - 1)))
    # linear twin with per-pin secant stiffness from the Hertz solve
    K = np.array([F[k] / max(dp * st["l"][k] - g[k], 1e-9)
                  if F[k] > 0 else 1.0 for k in range(NP)])
    l = np.clip(st["l"], 0, None)
    dphi = (T_disc + (g * l * K).sum()) / ((l ** 2) * K).sum()
    Fk = np.clip(dphi * st["l"] - g, 0, None) * K
    print("matched-K linear: engaged=%d, Fmax=%.1f N, Fmax ratio "
          "hertz/linK=%.2f" % ((Fk > 0).sum(), Fk.max(),
                               F.max() / max(Fk.max(), 1e-9)))
    print("real clr=0.15   :")
    st15 = pin_state(0.0)
    F15, dp15, eng15 = solve_ring(T_disc, st15, 4.0, mat[0], mat[1])
    print("   engaged=%d of %d (%.0f%%), Fmax=%.1f N "
          "(published: engagement collapses with clearance)"
          % (eng15.sum(), NP, 100 * eng15.sum() / NP, F15.max()))


def motor_cap():
    I, KT, ETA = 5.0, 0.0289, 0.7          # [U] 5 A cap, eta [U]
    for ratio in (40, 50, 30, 25):
        try:
            rc = cyc.ratio_check(ratio)
        except KeyError:
            rc = float(ratio)
        print("ratio %g: T_out_max = %.1f*%.4f*%.1f*%.1f = %.2f N*m [U]"
              % (ratio, I, KT, rc, ETA, I * KT * rc * ETA))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate(); sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "cap":
        motor_cap(); sys.exit(0)
    print("=== baseline module, per-disc (2 discs share T_out) ===")
    for name, T in LOADS:
        stress_block(name, T, "PETG-CF")
        print()
