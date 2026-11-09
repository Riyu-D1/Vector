"""refine/p_wrist7.py - D6 wrist v2 geometry with the R1 mirrored-cheek fix.

Copy of cradlefix/p_wrist6.py (D7 state) with one repair:

  BUG (F9 root cause): for the -b cheek the code placed the a-h profile on
  the INNER pocket plane (b = -CHEEK_B[0] = -12.51) and extruded +2.4 mm
  along +b, i.e. INWARD into the servo pocket volume.  The subsequent
  `s - pocket(key)` cut then removed the entire -b cheek.  Every keel-cage
  part (w_link4 fin, w_link5 cage, w_grip_frame cage) shipped with only
  its +b cheek; the -b cable cleats floated as slivers.

  FIX (matches the D5 p_wrist5.py pattern): the profile face is placed on
  the LOWER b-bound and extruded up by (hi-lo), so each cheek occupies
  exactly CHEEK_B[0]..CHEEK_B[1] on its own side of the pocket.

Nothing else changes: profiles, windows, webs, pockets, horn holes,
cleats, rack-train interface dims all identical -> every interface dim
is preserved.
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
from build123d import (Plane, Pos, Polygon, RectangleRounded, extrude, Location,
                       fillet, Axis)
import ap2 as P2
import p_arm2 as PA
import ap2b as B
import p_arm2b as PB
import ap7 as N          # refine params (R-fixes); was ap6

box = PA.box
cyl = PB.cyl
rest = PB.rest
horn_holes = PB.horn_holes

# ---------- local pose helpers (identical to p_arm2b but reading ap6.SERVOS) ----------
def servo_loc(key):
    o, ly, lx = N.SERVOS[key]
    lz = (lx[1] * ly[2] - lx[2] * ly[1], lx[2] * ly[0] - lx[0] * ly[2], lx[0] * ly[1] - lx[1] * ly[0])
    return Location(Plane(origin=o, x_dir=lx, z_dir=lz))

def servo_w(key, clr=0.0, plug_clr=None, horn=True):
    return servo_loc(key) * PB.servo_kp(clr, plug_clr, horn)

def pocket(key):
    return servo_w(key, B.SV_CLR, 0.3)

def vendor_servo(key):
    return lambda: rest(servo_w(key))

# ---------- profile helpers (same convention as p_wrist5) ----------
def _ah(b):
    return Plane(origin=(0, b, 0), x_dir=(1, 0, 0), y_dir=(0, 0, 1))

def _bh(a):
    return Plane(origin=(a, 0, 0), x_dir=(0, 1, 0), y_dir=(0, 0, 1))

def _ab(h):
    return Plane(origin=(0, 0, h), x_dir=(1, 0, 0), y_dir=(0, 1, 0))

def ah(b, a0, a1, h0, h1, r):
    return _ah(b) * Pos((a0 + a1) / 2, (h0 + h1) / 2, 0) * RectangleRounded(a1 - a0, h1 - h0, r)

def bh(a, b0, b1, h0, h1, r):
    return _bh(a) * Pos((b0 + b1) / 2, (h0 + h1) / 2, 0) * RectangleRounded(b1 - b0, h1 - h0, r)

def ab(h, a0, a1, b0, b1, r):
    return _ab(h) * Pos((a0 + a1) / 2, (b0 + b1) / 2, 0) * RectangleRounded(a1 - a0, b1 - b0, r)

def poly_ah(b, pts):
    return _ah(b) * Polygon(*pts, align=None)

def poly_bh(a, pts):
    return _bh(a) * Polygon(*pts, align=None)

def poly_ab(h, pts):
    return _ab(h) * Polygon(*pts, align=None)

def xb(face, b0, b1):
    return extrude(face, amount=b1 - b0, dir=(0, 1, 0))

def xa(face, a0, a1):
    return extrude(face, amount=a1 - a0, dir=(1, 0, 0))

def cleat_a(b, h, a_face):
    return cyl((b, h), 2.6, "a", a_face - 3.0, a_face + 0.5) + cyl((b, h), 4.4, "a", a_face - 4.0, a_face - 3.0)

def cleat_b(a, h, b_face):
    return cyl((a, h), 2.6, "b", b_face - 3.0, b_face + 0.5) + cyl((a, h), 4.4, "b", b_face - 4.0, b_face - 3.0)

# ---------- w_j4_cradle: same sleeve interface as D5 ----------
def w_j4_cradle():
    s = xb(ah(N.CR_B[0], *N.CR_OUT), *N.CR_B)
    s = s + xb(ah(N.CR_PLATE_B[0], *N.CR_PLATE), *N.CR_PLATE_B)
    for a_, h_ in B.J4_BOLTS:
        s = s + cyl((a_, h_), N.CR_BOSS_D, "b", N.CR_BOSS_B[0], N.CR_BOSS_B[1])
    s = s - pocket("j4")
    a0, a1, b0, b1, h0, h1 = N.CR_SLOT
    s = s - box(a0, a1, b0, b1, h0, h1)
    for a_, h_ in B.J4_BOLTS:
        s = s - cyl((a_, h_), B.M3_PILOT, "b", 24.55, 33.55)
    a0, a1, b0, b1, h0, h1 = N.CR_GROOVE
    s = s - box(a0, a1, b0, b1, h0, h1)
    return s

# ---------- w_link4: J4 horn plate + strut rib + dorsal fin ----------
def w_link4():
    b0, b1 = N.L4_B
    s = xb(ah(b0, *N.L4_PLATE), b0, b1)                       # horn plate
    s = s + xb(poly_ah(N.L4_STRUT_B[0], N.L4_STRUT), *N.L4_STRUT_B)   # R3: widened strut rib
    for sg in (1, -1):                                       # dorsal fin cheeks
        b_lo, b_hi = sorted((sg * N.L4_CHEEK_B[0], sg * N.L4_CHEEK_B[1]))
        s = s + xb(poly_ah(b_lo, N.L4_FIN), b_lo, b_hi)      # R1: face on lower bound, grows outward
    s = s + box(20.0, 61.05, -N.L4_CHEEK_B[1], N.L4_CHEEK_B[1], -1.4, -0.05)   # fin bottom web
    for sg in (1, -1):                                       # R4: tail collar sides
        c_lo, c_hi = sorted((sg * N.L4_COLB[0], sg * N.L4_COLB[1]))
        s = s + xb(poly_ah(c_lo, N.L4_COLSIDE), c_lo, c_hi)  # lap the cheek outer faces
    ta0, ta1, tb0, tb1, th0, th1 = N.L4_COLBACK
    s = s + box(ta0, ta1, tb0, tb1, th0, th1)                # collar back plate (closes tail)
    for ra0, ra1, rh0, rh1 in N.L4_RIBS:                                       # ribs strut -> fin -b cheek
        s = s + box(ra0, ra1, b0, -12.7, rh0, rh1)
    s = s + xb(poly_ah(N.L4_STRUT_B[0], N.L4_RIBMID),     # R4v3: tapered mid rib;
               N.L4_STRUT_B[0], -20.5)                    # R8: end 0.5 short of the
                                                        # cradle -b wall (was -12.7,
                                                        # intruded the wall corner)
    # R8: clear the J4 hardware out of the strut/rib band - the kp model:
    # horn disc b -26.1..-21.6 r9.6; case front face -24.5 spanning
    # a -35..10.1, h +-12.36.  Bore d20 through the horn band + a case-front
    # box.  The R3 strut had always overlapped the vendor horn; stale STLs
    # masked it in the ROM check.
    s = s - cyl((0, 0), 20.0, "b", -26.55, -24.8)
    # case-front clearance must be the SWEPT footprint: the case box
    # (a -35.12..10.11, h +-12.36) contains the J4 axis, so the union over
    # the +-80 deg sweep is a big fan, not the rest-pose box.  Cutting only
    # the static box left ~10 mm3 grazes at +-5 deg.
    sw = None
    for q in range(-80, 81, 8):
        c = box(-35.4, 10.4, -24.85, -19.0, -12.8, 12.8)
        c = c.rotate(Axis((0, -22.0, 0), (0, 1, 0)), q)
        sw = c if sw is None else sw + c
    s = s - sw
    # R5: honest mass trims for the J2 margin - windows in the R4-added
    # bulkheads, placed in the rib-only b span so the plate face, strut
    # (b<=-22.65) and the -b cheek band (b>=-14.91) are all untouched;
    # the remaining a-h frame strips keep the plate->cheek tie.  All
    # corners rounded r1.5 (b-parallel edges) so the window corners are
    # not stress-riser notches in the printed part.
    def wcut(a0, a1, b0, b1, h0, h1, r=1.5):
        r = min(r, 0.45 * (a1 - a0), 0.45 * (h1 - h0))
        c = box(a0, a1, b0, b1, h0, h1)
        return fillet(c.edges().filter_by(Axis.Y), r)
    s = s - wcut(13.5, 27.5, -22.4, -15.0, 10.0, 14.5)      # mid-rib window
    s = s - wcut(28.0, 40.0, -22.4, -15.0, 33.5, 36.5)      # shoulder-rib window
    # (collar back-plate window REVERTED: the thin frame rim reached
    #  sigma_n(y) +9.6 MPa tensile at (66.4,+-11.4,22) - SF ~1.3 for
    #  ~0.4 g saved, not worth a new hotspot in the R4 collar)
    s = s - wcut(42.0, 52.0, -15.91, 15.91, 22.0, 30.0)     # fin cheek window
    s = s - wcut(42.0, 52.0, -15.91, 15.91, 6.0, 14.0)      # fin cheek window (lower)
    s = s - wcut(52.0, 58.0, -15.91, 15.91, 14.0, 22.0)     # fin cheek window (aft)
    s = s - wcut(44.0, 58.0, -15.91, -12.51, 4.0, 12.0)     # -b cheek window (rib-free zone)
    s = s - wcut(24.0, 40.0, 12.51, 15.91, 6.0, 28.0)       # +b cheek window (no ribs on +b)
    s = s - wcut(42.0, 52.0, 12.51, 15.91, 14.0, 22.0)      # +b cheek band between windows
    s = s - wcut(40.0, 58.0, 12.51, 15.91, 30.0, 34.0)      # +b cheek upper window
    s = s - pocket("j5")                                     # case + plug + horn (open top slot)
    s = s - horn_holes((0, 0), "b", b0, b1, b0 - 1, b0 + B.HORN_CB[1],
                       b1 - B.HORN_RECESS[1], b1 + 1)
    return s

# ---------- w_link5: J5 horn plate + ventral keel cage for J6 ----------
def w_link5():
    h0, h1 = N.L5_TOP
    s = extrude(ab(h0, *N.L5_PLATE), amount=h1 - h0, dir=(0, 0, 1))            # horn plate
    for sg in (1, -1):                                                       # D7: front b-corner reliefs (cradle sweep clearance)
        # R7v3: variant-driven relief.  Measured envelope from
        # clearance_map.py / relief_depth.py (intrusion reaches the full
        # plate thickness at |b|>~14.5, so the relief must stay full
        # height; ~+0.4 mm sample pessimism).
        if N.L5_RELIEF == "r6":                        # R6 verbatim: box notch
            lo, hi2 = sorted((sg * 10.0, sg * 17.0))
            s = s - box(N.L5_PLATE[0] - 1.0, 28.2, lo, hi2, h0 - 1.0, h1 + 1.0)
        elif N.L5_RELIEF == "r6f":                     # R6 step + in-plane corner round
            lo, hi2 = sorted((sg * 10.0, sg * 17.0))
            cut = box(N.L5_PLATE[0] - 1.0, 28.2, lo, hi2, h0 - 1.0, h1 + 1.0)
            ce = [e for e in cut.edges()                             # vertical cut edge at
                  if abs(e.center().X - 28.2) < 0.2                  # the neck->full-width
                  and abs(e.center().Y - sg * 10.0) < 0.2]           # re-entrant corner
            if ce:
                cut = cut.fillet(2.5, ce)
            s = s - cut
        elif N.L5_RELIEF == "r6w":                     # wider neck, same step
            lo, hi2 = sorted((sg * 10.75, sg * 17.0))
            s = s - box(N.L5_PLATE[0] - 1.0, 28.2, lo, hi2, h0 - 1.0, h1 + 1.0)
        elif N.L5_RELIEF == "2step":                   # two smaller steps
            lo, hi2 = sorted((sg * 10.0, sg * 17.0))
            s = s - box(N.L5_PLATE[0] - 1.0, 28.2, lo, hi2, h0 - 1.0, h1 + 1.0)
            lo, hi2 = sorted((sg * 12.5, sg * 17.0))
            s = s - box(28.2, 31.0, lo, hi2, h0 - 1.0, h1 + 1.0)
        elif N.L5_RELIEF == "lip":                     # bottom-flanged neck: |b|<10
            lo, hi2 = sorted((sg * 10.0, sg * 17.0))   #  full height + a 1.75 mm
            s = s - box(N.L5_PLATE[0] - 1.0, 28.2, lo, hi2, -4.4, h1 + 1.0)
            lo, hi2 = sorted((sg * 12.4, sg * 17.0))   #  bottom lip out to |b|=12.4
            s = s - box(N.L5_PLATE[0] - 1.0, 28.2, lo, hi2, h0 - 1.0, -4.4)
        elif N.L5_RELIEF == "flush":                   # mouth edge flush with cheek inner face
            eg = ((23.0, 12.51), (25.0, 12.55), (27.0, 12.55),
                  (29.0, 12.9), (30.5, 13.6), (32.0, 14.6),
                  (33.5, 15.4), (35.5, 16.1), (37.5, 16.45))
            tp = tuple((a_, sg * b_) for a_, b_ in eg) + \
                ((38.5, sg * 17.0), (23.0, sg * 17.0))
            s = s - extrude(_ab(h0 - 1.0) * Polygon(*tp, align=None),
                            amount=(h1 - h0) + 2.0, dir=(0, 0, 1))
        elif N.L5_RELIEF == "loft":                    # R8: swept-envelope lip loft
            # keep-top table baked from the J4xJ5 swept phantom
            # (checks/bake_loft.py).  None = keep full plate; -99 = full cut.
            BS = [9.5 + 0.3 * i for i in range(24)]
            for a_c, row in N.L5_LOFT:
                j = 0
                while j < len(row):
                    k = j
                    while k + 1 < len(row) and row[k + 1] == row[j]:
                        k += 1
                    if row[j] is not None:
                        b_lo = sg * (BS[j] - 0.16)
                        b_hi = sg * (BS[k] + 0.16)
                        lo, hi2 = sorted((b_lo, b_hi))
                        z0 = row[j] if row[j] != -99.0 else h0 - 0.1
                        s = s - box(a_c - 0.21, a_c + 0.21, lo, hi2,
                                    z0 - 0.02, h1 + 1.0)
                    j = k + 1
            # beyond the table (|b|>16.5): full cut, same as r6 outer band
            lo, hi2 = sorted((sg * 16.4, sg * 17.0))
            s = s - box(N.L5_PLATE[0] - 1.0, 28.7, lo, hi2, h0 - 1.0, h1 + 1.0)
    for sg in (1, -1):
        b_lo, b_hi = sorted((sg * N.L5_CHEEK_B[0], sg * N.L5_CHEEK_B[1]))
        s = s + xb(poly_ah(b_lo, N.L5_CAGE), b_lo, b_hi)     # R1: face on lower bound, grows outward
    for sg in (1, -1):                                       # R4: under-plate gusset ribs
        g_lo, g_hi = sorted((sg * N.L5_GUS_B[0], sg * N.L5_GUS_B[1]))
        s = s + xb(poly_ah(g_lo, N.L5_GUSSET), g_lo, g_hi)
    s = s + box(N.L5_CAGE[1][0], 64.7, -N.L5_CHEEK_B[1], N.L5_CHEEK_B[1], N.L5_BOTTOM - 2.0, N.L5_BOTTOM)  # keel web
    for sg in (1, -1):                                   # R6: bottom longeron - outer-face
        b_lo, b_hi = sorted((sg * N.L5_CHEEK_B[1],       #  T-flange on each cheek bottom; the
                             sg * 17.3))                 #  pocket-face cheek/keel corner can't be
        s = s + box(N.L5_CAGE[1][0], 64.7, b_lo, b_hi,   #  filleted (case clearance), so deepen
                    N.L5_BOTTOM - 2.0, -48.0)            #  the section at the outer face instead
        s = s + box(50.0, 64.7, b_lo, b_hi, -48.0, -38.0)  #  + aft-end rib: relieves the (61.05,-41.4)
                                                         #  step corner under floor-entry bound.
                                                         #  R7: 55->50 a-reach and -45->-48 depth so
                                                         #  the outer-face block runs continuous
                                                         #  h -52.4..-38 over a 50..64.7 - the (58.7,
                                                         #  +-12.5,-51.8) pocket-floor inner corner
                                                         #  sits inside a ~14.5 mm deep T-section now
                                                         #  (floor-only lateral bound).
    a0, a1, bh0, bh1 = N.L5_BACK
    s = s + box(a0, a1, -N.L5_CHEEK_B[1], N.L5_CHEEK_B[1], bh0, bh1)            # back-bottom wall
    s = s - pocket("j6")
    for ac, ahw, hc, hhw in N.L5_WIN:                                        # cheek windows
        for sg in (1, -1):                    # R6: recess each window from the INNER face
            b_lo, b_hi = sorted((sg * (N.L5_CHEEK_B[0] - 1.0),               #  up to L5_SKIN short of
                                 sg * (N.L5_CHEEK_B[1] - N.L5_SKIN)))        #  the outer face -> closed skin
            w = box(ac - ahw, ac + ahw, b_lo, b_hi, hc - hhw, hc + hhw)
            yed = [e for e in w.edges()                                       #  rounded recess
                   if abs(e.tangent_at(0.5).normalized().Y) > 0.99]           #  boundary: fillet the
            w = w.fillet(N.L5_SKIN_R, yed)                                    #  4 b-running corner edges
            s = s - w
    sed = [e for e in s.edges()                                               # R6: fillet the aft-tab
           if abs(e.center().X - 61.05) < 0.6                                 #  step corner (61.05,-41.4)
           and abs(e.center().Z + 41.4) < 0.6                                 #  - re-entrant notch at the
           and abs(e.tangent_at(0.5).normalized().Y) > 0.9]                   #  pocket face; only the
    if sed:                                                                   #  cheek-band segments
        s = s.fillet(2.0, sed)                                                #  (|b|>12.51) remain
    s = s - horn_holes((N.A_J5, 0), "h", h0, h1, h0 - 1, h0 + B.HORN_CB[1],
                       h1 - B.HORN_RECESS[1], h1 + 1)
    for p in N.L5_CLEATS:
        s = s + cleat_b(p[0], p[1], -N.L5_CHEEK_B[1])
    return s

# ---------- w_grip_frame: J6 horn plate + grip keel + rack cage ----------
def w_grip_frame():
    a0, a1 = N.GF_PLATE_A
    s = xa(poly_bh(a0, N.GF_PLATE), a0, a1)                  # horn plate (r16.2 roll clip)
    ped = [e for e in s.edges()                              # R7: round the plate's bottom
           if abs(e.center().Z + 26.5) < 0.5                 #  edges (+-11.61,-26.5) - softens the
           and abs(e.tangent_at(0.5).normalized().X) > 0.9]  #  cheek-side of the a=67 weld corner
    if ped:
        s = s.fillet(2.5, ped)                               #  (R7v2: 1.5->2.5 - notch still -10.6)
    for sg in (1, -1):
        b_lo, b_hi = sorted((sg * N.GF_CHEEK_B[0], sg * N.GF_CHEEK_B[1]))
        s = s + xb(poly_ah(b_lo, N.GF_CAGE), b_lo, b_hi)     # R1: face on lower bound, grows outward
        s = s + box(66.0, 69.0, *sorted((sg * 13.5, sg * N.GF_CHEEK_B[1])),
                    -26.5, -8.5)                             # R2f: side boss wrapping the plate's outer b edge
                                                             # (a>=66 stays clear of the j5 case roll sweep)
        ra0, ra1, rb0, rb1, rh0, rh1 = N.GF_RIB               # R7: outer-face brace rib
        s = s + box(ra0, ra1, *sorted((sg * rb0, sg * rb1)), rh0, rh1)
    s = s + box(71.5, 114.7, -N.GF_CHEEK_B[1], N.GF_CHEEK_B[1], N.GF_BOTTOM - 2.0, N.GF_BOTTOM)  # keel web
    a0w, a1w, bh0, bh1 = N.GF_BACKWALL
    s = s + box(a0w, a1w, -N.GF_CHEEK_B[1], N.GF_CHEEK_B[1], bh0, bh1)         # back-bottom wall
    s = s - pocket("g")
    hs, sh = N.H_SH, N.A_SH
    for sg in (1, -1):                                       # rack rails + lips (B block, h+a shifted)
        s = s + box(B.BR_A[0] + sh, B.CH_A1 + sh, -B.BR_B, B.BR_B, *sorted((sg * B.CH_H[0] + hs, sg * B.CH_H[1] + hs)))
        s = s + box(B.LIP[0] + sh, B.CH_A1 + sh, -B.BR_B, B.BR_B, *sorted((sg * B.LIP[1] + hs, sg * B.CH_H[0] + hs)))
    s = s + xa(bh(B.BR_A[0] + sh, -B.BR_B, B.BR_B, -B.CH_H[1] + hs, B.CH_H[1] + hs, N.GF_BRACKET_R),
               B.BR_A[0] + sh, B.BR_A[1] + sh)
    s = s - cyl((0, hs), B.BR_HOLE, "a", B.BR_A[0] + sh - 1, B.BR_A[1] + sh + 1)
    for sg in (1, -1):                                       # 45 deg chamfers under the lips
        tri = poly_ah(-B.BR_B - 1, ((B.LIP[0] + sh, sg * B.LIP[1] + hs), (B.LIP[0] + sh, sg * B.CH_H[0] + hs),
                                    (B.LIP[0] + sh - N.GF_LIP_CH, sg * B.LIP[1] + hs)))
        s = s - xb(tri, -B.BR_B - 1, B.BR_B + 1)
    s = s - horn_holes((0, hs), "a", a0, a1, N.GF_CB_A, a1 + 1, a0 - 1, a0 + B.HORN_RECESS[1])
    for ac, ahw, hc, hhw in N.GF_WIN:                        # cheek windows
        s = s - box(ac - ahw, ac + ahw, -N.GF_CHEEK_B[1] - 1, N.GF_CHEEK_B[1] + 1, hc - hhw, hc + hhw)
    s = s + cleat_b(N.GF_CLEAT[0], N.GF_CLEAT[2], -N.GF_CHEEK_B[1])
    return s

# ---------- shifted vendor parts (racks/fingers/gear roll about h = -17) ----------
def rack_sh(which, open_mm=0.0):
    sg = 1 if which == "U" else -1
    return Pos(N.A_SH, 0, N.H_SH) * PB.rack(which, open_mm)

def finger_sh(which, open_mm=0.0):
    sg = 1 if which == "U" else -1
    return Pos(0, sg * open_mm, 0) * Pos(N.A_SH, 0, N.H_SH) * PB.finger(which)

def vendor_gear():
    return rest(cyl((0, N.H_SH), B.GEAR[0], "a", B.GEAR[1] + N.A_SH, B.GEAR[2] + N.A_SH))

# ---------- part table ----------
def parts():
    return [
        ("w_j4_cradle", "fo", lambda: rest(w_j4_cradle())),
        ("vendor_sts3215_j4", "fo", vendor_servo("j4")),
        ("w_link4", "w4", lambda: rest(w_link4())),
        ("vendor_sts3215_j5", "w4", vendor_servo("j5")),
        ("w_link5", "w5", lambda: rest(w_link5())),
        ("vendor_sts3215_j6", "w5", vendor_servo("j6")),
        ("w_grip_frame", "w6", lambda: rest(w_grip_frame())),
        ("vendor_sts3215_g", "w6", vendor_servo("g")),
        ("vendor_gear_grip", "w6", vendor_gear),
        ("vendor_rack_u", "w6", lambda: rest(rack_sh("U"))),
        ("vendor_rack_d", "w6", lambda: rest(rack_sh("D"))),
        ("finger_u", "w6", lambda: rest(finger_sh("U"))),
        ("finger_d", "w6", lambda: rest(finger_sh("D"))),
    ]

def pose(shape, group, **kw):
    return PB.pose(shape, "fo" if group.startswith("w") else group, **kw)
