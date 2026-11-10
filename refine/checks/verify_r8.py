"""refine/checks/verify_r8.py - R8 reproducible verification snippets.

Re-runs the arithmetic that motivated two R8 deck corrections, without
needing ccx:

  1. The legacy wrench reference points understate the applied moment
     about each horn vs the true mass-weighted stack COM - prints the
     error table cited in fea/msh2_r3.py (R8 comment).
  2. The L5_LOFT keep-top table in ap7.py preserves a bottom lip:
     prints kept-depth stats vs the R6/R7 full-depth box notch.

Run from refine/refine:  python3 checks/verify_r8.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ap7 as N

# carried stack + payload COM - same table as fea/msh2_r3.py:_L5_STACK
STACK = [(0.05500, (41.53, 0.00, -29.59)), (0.01598, (94.77, -0.02, -25.68)),
         (0.05500, (95.53, 0.00, -29.59)), (0.00800, (119.70, 0.00, -17.00)),
         (0.01200, (119.90, -12.99, -3.28)), (0.01200, (119.90, 12.99, -30.72)),
         (0.00097, (131.08, 3.00, -16.62)), (0.00097, (131.08, -3.00, -17.38)),
         (0.01939, (100.19, -0.01, -23.81))]
SELF_L5 = 1.965            # N, fixed carried-stack gravity term (l5 decks)
SELF_L4 = 2.255            # N, l4 decks
SELF_GF = 1.1              # N, gf decks

L5_HORN = (30.6, -2.05)    # J5 horn axis (a, h) - moment arm origin
L4_HORN = (0.0, 0.0)       # J4 horn axis


def stack_com(pay):
    sx = sum(m * c[0] for m, c in STACK) + pay * 137.4
    sz = sum(m * c[2] for m, c in STACK) - pay * 17.0
    M = sum(m for m, _ in STACK) + pay
    return np.array((sx / M, 0.0, sz / M))


def moment_z(ref, F):
    """wrist-frame overturning moment about the horn b-axis for a keel-down
    force F<0 at ref (a, b, h):  M = (a_ref - a_horn)*Fz - (h_ref - h_horn)*Fa"""
    return (ref[0] - L5_HORN[0]) * F


def check_moment():
    print("== 1. legacy-ref vs COM moment, l5 decks ==")
    print("%-8s %-8s %-9s %-9s %-9s %-6s" %
          ("case", "Fz(N)", "M_legacy", "M_com", "ratio", "err"))
    for tag, pay, self_n in (("p50", 0.5, SELF_L5), ("p38", 0.38, SELF_L5),
                             ("p25", 0.25, SELF_L5)):
        F = -(9.81 * pay + self_n)
        com = stack_com(pay)
        m_com = (com[0] - L5_HORN[0]) * F          # force at true COM
        leg = (113.7 - L5_HORN[0]) * F            # legacy ref a=113.7
        # legacy also sat at h=-30: same -z force, no extra moment (Fa=0)
        err = (abs(leg) - abs(m_com)) / abs(m_com) * 100
        print("%-8s %-8.2f %-9.0f %-9.0f %-9.3f %+.0f%%"
              % (tag, F, leg, m_com, leg / m_com, err))
    print("== l4 decks (legacy ref a=106, h=-5) ==")
    for tag, pay in (("p50", 0.5), ("p38", 0.38)):
        F = -(9.81 * pay + SELF_L4)
        com = stack_com(pay)
        m_com = (com[0] - L4_HORN[0]) * F
        leg = (106.0 - L4_HORN[0]) * F
        err = (abs(leg) - abs(m_com)) / abs(m_com) * 100
        print("%-8s %-8.2f %-9.0f %-9.0f %-9.3f %+.0f%%"
              % (tag, F, leg, m_com, leg / m_com, err))
    print("    (COM point also carries h ~ -19.5 vs -5 -> axial-force")
    print("     moment arms differ for the direction cases; keel-down")
    print("     shown, matches the -10%% / -7%% under-statement used in R8)")


def check_loft():
    print("\n== 2. L5_LOFT keep-top vs the R6/R7 box notch ==")
    # L5_LOFT rows: (a_centre, 24 keep-top values over |b| stations
    # BS=9.5..16.4 step 0.3); None = keep full plate; -99 = full cut.
    BS = [9.5 + 0.3 * i for i in range(24)]
    full, bot = N.L5_TOP[1], N.L5_TOP[0]
    n_full = n_lip = n_cut = 0
    lips = []
    for a_c, row in N.L5_LOFT:
        assert len(row) == 24, (a_c, len(row))
        for b, v in zip(BS, row):
            if v is None:
                n_full += 1
            elif v == -99.0:
                n_cut += 1
            else:
                n_lip += 1
                lips.append((a_c, b, v))
    tot = n_full + n_lip + n_cut
    print("stations %d over a %.2f..%.2f x |b| %.1f..%.1f:"
          % (tot, N.L5_LOFT[0][0], N.L5_LOFT[-1][0], BS[0], BS[-1]))
    print("  full-depth kept  %d (%.0f%%)" % (n_full, 100 * n_full / tot))
    print("  lip kept (partial) %d (%.0f%%); lips h %.2f..%.2f, "
          "depth above plate bottom %.2f..%.2f"
          % (n_lip, 100 * n_lip / tot,
             min(v for _, _, v in lips), max(v for _, _, v in lips),
             min(v for _, _, v in lips) - bot, max(v for _, _, v in lips) - bot))
    print("  fully relieved   %d (%.0f%%)" % (n_cut, 100 * n_cut / tot))
    # R6/R7 box notch removed ALL material for |b|<10 over a 23.6..41.5
    # regardless of need; the loft keeps full 4 mm plate to |b|~12+ over
    # most of the band plus a >=1 mm bottom lip where the sweep grazes.


if __name__ == "__main__":
    check_moment()
    check_loft()
