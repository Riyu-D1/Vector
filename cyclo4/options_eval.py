"""cyclo4/options_eval.py - D4 task 2: run every option through load_model.

Revised brief (user, D4 mid-stage): PETG-CF printed discs only (steel dowel
ring pins stay - already the BOM pin), design torque = worst-case STATIC
torque at 0.5 kg payload (upgrade1/gravity_up1.py sweep: J2 2.616 / J3 1.837
N*m -> design at 2.7 / 1.85).  Target: lobe contact SF >= 2 at that design
torque; no x2 dynamic factor, no slam shock - instead the design adds a
firmware output-torque cap + soft E-stop ramp (see STATUS-cyc4.md).

Levers swept here (OD <= 57 mm always):
 (a) disc thickness / 3-disc stack in the same 10 mm pin span
 (b) flank clearance (equidistant profile offset) - print-feasible >= 0.05
 (c) ring pin size - Ø3 dowels already; pitch caps RP <= ~1.6
 (d) tooth count N (with the standard NP = N+1 matched pair)
 (e) eccentricity E
 (f) combinations of the above
"""
import sys

import numpy as np

import ap
import cyc
import load_model as lm

LOADS = [("J2 2.7", 2.70), ("J3 1.85", 1.85)]
NTH = 13
GEAR_KEY = 99   # scratch key injected into ap.GEAR for hypothetical sets


def gear_check(N, NP, R, RP, E, clr):
    """Manufacturability of a hypothetical gear set (cyc.checks-style)."""
    k1 = E * NP / R
    pitch = 2 * R * np.sin(np.pi / NP)
    gap = pitch - 2 * RP
    return dict(k1=k1, gap=gap,
                ok=k1 < 0.95 and E <= 0.5 * RP and gap >= 0.3)


def set_gear(N, R, RP, E):
    ap.GEAR[GEAR_KEY] = dict(N=N, R=R, RP=RP, E=E)


def clear_gear():
    ap.GEAR.pop(GEAR_KEY, None)


def run(label, t=4.0, clr=None, ratio=40, nd=2):
    lm._N_DISC = nd
    out = []
    for nm, T in LOADS:
        out.append(lm.stress_block(nm, T, "PETG-CF", t_disc=t, clr=clr,
                                   ratio=ratio, n_theta=NTH))
    lm._N_DISC = 2
    one_line(label, out)
    return out


def one_line(label, rows):
    s = " | ".join("%s n%d F%.0f p0 %.0f seq %.0f SF %.2f" %
                   (nm, r["n_med"], r["Fmax"], r["p0"], r["seq"], r["sf"])
                   for (nm, _), r in zip(LOADS, rows))
    print("%-46s %s" % (label, s))


if __name__ == "__main__":
    print("=== D4 options matrix v2 (n_theta=%d) ===" % NTH)
    print("design loads: J2 %.2f / J3 %.2f N*m (worst static @0.5 kg),"
          " PETG-CF, target SF>=2" % (LOADS[0][1], LOADS[1][1]))
    print("--- baseline ---")
    run("2x4.0 clr0.15 N40 E0.42 RP1.50")
    print("--- (b) clearance sweep ---")
    for c in (0.12, 0.10, 0.08, 0.05, 0.03):
        run("2x4.0 clr%.2f" % c, clr=c)
    print("--- (a) disc stack ---")
    run("2x4.85 clr0.15", t=4.85)
    for c in (0.10, 0.08, 0.05):
        run("3x3.0 clr%.2f" % c, t=3.0, clr=c, nd=3)
        run("2x4.85 clr%.2f" % c, t=4.85, clr=c)
    print("--- (d) tooth count ---")
    for (N, RP, E) in ((50, 1.25, 0.30), (45, 1.375, 0.36)):
        NP = N + 1
        set_gear(N, 23.5, RP, E)
        gc = gear_check(N, NP, 23.5, RP, E, 0.15)
        print("   gear %d:1 RP%.3f E%.2f: K1 %.2f gap %.3f %s"
              % (N, RP, E, gc["k1"], gc["gap"],
                 "mfg OK" if gc["ok"] else "MFG FAIL"))
        if gc["ok"]:
            for c in (0.10, 0.05):
                run("2x4.0 clr%.2f N%d" % (c, N), clr=c, ratio=GEAR_KEY)
        clear_gear()
    print("--- (e) eccentricity ---")
    for E in (0.35, 0.30):
        set_gear(40, 23.5, 1.5, E)
        gc = gear_check(40, 41, 23.5, 1.5, E, 0.15)
        print("   N40 RP1.5 E%.2f: K1 %.2f gap %.3f %s"
              % (E, gc["k1"], gc["gap"], "mfg OK" if gc["ok"] else "MFG FAIL"))
        if gc["ok"]:
            for c in (0.08, 0.05):
                run("2x4.0 clr%.2f N40 E%.2f" % (c, E), clr=c, ratio=GEAR_KEY)
        clear_gear()
    print("--- (c) pin radius (RP=1.6, pitch-gap floor) ---")
    set_gear(40, 23.5, 1.6, 0.42)
    gc = gear_check(40, 41, 23.5, 1.6, 0.42, 0.15)
    print("   N40 RP1.6 E0.42: K1 %.2f gap %.3f %s"
          % (gc["k1"], gc["gap"], "mfg OK" if gc["ok"] else "MFG FAIL"))
    if gc["ok"]:
        for c in (0.08, 0.05):
            run("2x4.0 clr%.2f RP1.60" % c, clr=c, ratio=GEAR_KEY)
    clear_gear()
    print("--- (f) combos: clearance + stack + E ---")
    for E in (0.42, 0.35):
        set_gear(40, 23.5, 1.5, E)
        for c in (0.08, 0.05):
            run("3x3.0 clr%.2f E%.2f" % (c, E), t=3.0, clr=c, nd=3,
                ratio=GEAR_KEY)
            run("2x4.85 clr%.2f E%.2f" % (c, E), t=4.85, clr=c, ratio=GEAR_KEY)
        clear_gear()
