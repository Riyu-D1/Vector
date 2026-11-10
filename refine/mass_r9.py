"""refine/mass_r9.py - R9 wrist mass model (same contract as mass_r5).

R9 changes vs R8 (p_wrist9/ap9):
  - w_link4 gains the +b yoke plate + journal boss (two-sided J4 support).
  - w_j4_cradle gains the pin bracket boss/web (stator side of the second
    J4 bearing) minus the CR_RELIEVE pocket cut.
  - wrist_pin: solid d3 steel dowel spanning the cradle boss and the link4
    journal; fixed to the cradle -> "fore" body (it does not turn with J4).
  - w_link5, w_grip_frame unchanged (R9 re-uses the p_wrist7 code path).

Volumes/centroids measured on the p_wrist9 solids (build123d .volume/
.center, W frame) then shifted to the AB pose via AB = W + (223.1,0,89.5):
  cradle 15.55 cc -> 12.22 g @ W(-14.31, 8.40, -0.08) [fore]  (R8 16.27/12.79)
  pin     0.12 cc ->  0.95 g @ W(  0.00,22.95, 0.00)  [fore]  (steel d3, 7.85)
  l4     17.71 cc -> 13.92 g @ W( 28.77,-9.25, 11.66) [wrist4](R8 17.22/13.53)
  l5     14.26 cc -> 11.21 g @ W( 38.06,-0.08,-34.44) [wrist5](R8 14.26/11.21)
  gf     20.33 cc -> 15.98 g @ W( 94.77,-0.02,-25.68) [grip]  (unchanged)
(*R8 l4 mass model value was 13.18 g at 16.77 cc pre-R8-trim; the R8-as-run
volume was 17.22 cc -> 13.53 g.  The delta quoted in the log uses the
as-run number.)
"""

# (body, mass kg, AB-pose centroid mm) - measured R9 geometry
PLASTIC = [
    ("fore",   0.01222, (208.79,   8.40,  89.42)),   # cradle 15.55 cc
    ("fore",   0.00095, (223.10,  22.95,  89.50)),   # wrist_pin d3 steel dowel
    ("wrist4", 0.01392, (251.87,  -9.25, 101.16)),   # l4 17.71 cc (yoke+boss, solid arm)
    ("wrist5", 0.01121, (261.16,  -0.08,  55.06)),   # l5 14.26 cc
    ("grip",   0.01598, (317.87,  -0.02,  63.82)),   # gf 20.33 cc (unchanged)
]
RHO6 = 1.31e-3 * 0.6          # g/mm3 effective (60 % infill convention)

VENDOR = [
    ("wrist4", 0.05500, (266.29,   0.00, 108.57)),   # j5 servo
    ("wrist5", 0.05500, (264.63,   0.00,  59.91)),   # j6 servo
    ("grip",   0.05500, (318.63,   0.00,  59.91)),   # g servo
    ("grip",   0.00800, (342.80,   0.00,  72.50)),   # gear
    ("grip",   0.01200, (343.00, -12.99,  86.22)),   # rack_u
    ("grip",   0.01200, (343.00,  12.99,  58.78)),   # rack_d
    ("grip",   0.00097, (354.18,   3.00,  72.88)),   # finger_u
    ("grip",   0.00097, (354.18,  -3.00,  72.12)),   # finger_d
]

ORIGINS = {"wrist5": (253.7, 0.0, 97.1), "grip": (276.1, 0.0, 72.5)}

# stale up1 wrist entries to drop (matched by (body, mass)) - same list as
# mass_r5: the product model still carries the same stale entries.
DROP = [
    ("wrist4", 0.02810000), ("wrist4", 0.05500000),
    ("wrist5", 0.00660000), ("wrist5", 0.05500000),
    ("grip",   0.01340000), ("grip",   0.05500000), ("grip", 0.00800000),
    ("grip",   0.01200000), ("grip",   0.01200000),
    ("grip",   0.00096585), ("grip",   0.00096585),
]

# also drop the R5-era plastic rows if a caller applies this after mass_r5
DROP5 = [
    ("fore",   0.01279), ("wrist4", 0.01318), ("wrist5", 0.01113),
    ("grip",   0.01598),
    ("wrist4", 0.05500), ("wrist5", 0.05500), ("grip", 0.05500),
    ("grip",   0.00800), ("grip",   0.01200), ("grip", 0.01200),
    ("grip",   0.00097), ("grip",   0.00097),
]


def apply(G1):
    """Patch gravity_up1 in place: corrected origins + measured
    wrist/fore entries (R9 PLASTIC incl. the steel pin + VENDOR)."""
    drop = set(DROP) | set(DROP5)
    G1.PARTS = [p for p in G1.PARTS
                if not any(p[0] == b and abs(p[1] - m) < 2e-5
                           for b, m in drop)]
    G1.PARTS += PLASTIC + VENDOR
    G1._ORIGIN_AB_MM.update(ORIGINS)
    G1._LOCAL = G1._local_parts()
    return G1
