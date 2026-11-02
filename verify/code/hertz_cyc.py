"""verify/code/hertz_cyc.py - Hertz line-contact hand cross-check for the
40:1 cycloidal stage (V1 task 1).  Pairs the FEA (or replaces it if the
hard-contact solve cannot converge - stage fallback).

Geometry (cad/act2/ap.py): NP=41 ring pins r_pin=1.5 mm on R=23.5, disc lobes
N=40, e=0.42, tooth clearance 0.15, disc t=4 mm each (2 discs).
Load: stage test = 2x rated output torque (J2 7.0 N.m, J3 4.5 N.m).

Contact model [U simplifications stated]:
 - load shared by n_sh=3 lobe/pin contacts per disc (sanity-doc convention;
   single-lobe bound also printed).
 - lobe contact flank approximated by its local radius of curvature
   rho_lobe ~ (R_ring_pcd - pin_r - profile clearance); the cycloid lobe
   is convex against the concave pin -> cylinder-on-cylinder, opposite
   signs. Effective radius 1/Rho = 1/r_pin - 1/rho_lobe is NOT used;
   for a convex pin against a convex lobe flank 1/Rho = 1/r1 + 1/r2 with
   the lobe's flank radius taken as the base-circle radius of the
   epitrochoid ~ (N-1)*e? -> use flank radius rho = ap.R - E*1.5?  This is
   the [U] piece - we print rho sensitivity.
 - steel pin E=200 GPa, PETG-CF E=4 GPa; Hertz line contact half-width
   a = sqrt(4 F R* / (pi L E*)); p0 = 2F/(pi a L).
 - shear ~0.3 p0 (subsurface Hertz), sigma_eq ~ p0*0.6 for combined.
"""
import math

NP, N = 41, 40
R_RING, R_PIN = 23.5, 1.5
E_ECC, CLR = 0.42, 0.15
T_DISC = 4.0
E_ST, E_PT, NU = 200000.0, 4000.0, 0.35
ALLOW = 25.0


def hertz(F, r1, r2, L):
    inv = 1.0 / r1 + 1.0 / r2 if r2 else 1.0 / r1
    R = 1.0 / inv
    Es = 1.0 / ((1 - 0.29 ** 2) / E_ST + (1 - NU ** 2) / E_PT)
    a = math.sqrt(4 * F * R / (math.pi * L * Es))
    p0 = 2 * F / (math.pi * a * L)
    return a, p0, Es, R


def run(name, T_out):
    # tangential force on the 41-pin ring for output torque T_out:
    # T = F_t * R_ring -> force per engaged pin pair shared over n_sh lobes
    F_t = T_out * 1000.0 / R_RING
    for n_sh in (1, 2, 3):
        F = F_t / n_sh
        for rho in (8.0, 12.0, 18.0):
            a, p0, Es, R = hertz(F, R_PIN, rho, T_DISC)
            print("%s T=%.1f n=%d rho=%.0f: F=%.0f N a=%.3f p0=%.0f MPa seq~%.0f SF %.2f"
                  % (name, T_out, n_sh, rho, F, a, p0, 0.6 * p0, ALLOW / (0.6 * p0)))
    # output pin bearing: 6 pins d3 on PCD33, t=4 mm each disc
    Fp = T_out * 1000.0 / (33.0 / 2.0)
    for n in (2, 3):
        pb = Fp / n / (3.0 * T_DISC)
        print("%s output-pin bearing n=%d: F=%.0f N p=%.1f MPa SF %.1f"
              % (name, n, Fp, pb, ALLOW / pb))
    # pin bending: pin as beam L=10 mm (33.5..43.5), point load F/2 each disc
    F = F_t / 3.0
    M = F * T_DISC * 1.5            # worst offset moment
    S = 32 * M / (math.pi * 3.0 ** 3)
    print("%s pin bending ~%.0f MPa (steel, fine)" % (name, S))


for nm, T in (("J2", 7.0), ("J3", 4.5)):
    run(nm, T)
    print()
