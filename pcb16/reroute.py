#!/usr/bin/env python3
"""reroute.py — hand-reroute engine for soma-carrier-v16.

Reads ROUTES from routes_v16.py:
    ROUTES = {
      "NET": [ (layer, width, [(x,y), ...]), ... ],   # legs; layer change => via
      "GND_VIAS": [(x,y), ...],                       # stitching via grid
      "EXTRA_VIAS": {"NET": [(x,y), ...]},            # parallel via farms
    }

- Chamfers every 90-degree interior vertex into two 45-degree bends.
- Validates: pad clearance, same-layer foreign-track clearance, via
  clearance, board-edge clearance, pad exit angle, 0/45/90-only angles.
- Writes a new .kicad_pcb: footprints/zones/graphics preserved, all old
  segments/vias and baked zone fills removed, new copper appended.

Usage:
  python3 reroute.py [in.kicad_pcb] [out.kicad_pcb] [--check]
  --check : validate only, do not write
"""
import math, re, sys, uuid
from routes_v16 import ROUTES, GND_VIAS, EXTRA_VIAS

IN  = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") \
      else "soma-carrier-v16.kicad_pcb"
OUT = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") \
      else IN
CHECK = "--check" in sys.argv

CLR = 0.22          # net-to-net copper clearance (mm, edge to edge)
EDGE_CLR = 1.0      # copper edge to board edge
VIA_SIZE, VIA_DRILL = 0.7, 0.3
CHAMFER = 1.4       # nominal chamfer leg length for 90-deg corners
PADEXIT = 0.6       # straight axis-aligned run required out of a pad

txt = open(IN).read()

def sexpr_blocks(s, head):
    for m in re.finditer(re.escape(head), s):
        i2, depth, instr, j = m.start(), 0, False, m.start()
        while j < len(s):
            ch = s[j]
            if ch == '"':
                instr = not instr
            elif not instr:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        break
            j += 1
        yield (m.start(), j + 1, s[i2:j + 1])

def net_of(b):
    m = re.search(r'\(net\s+\d+\s+"([^"]*)"\)', b)     # (net N "name")
    if m:
        return m.group(1)
    m = re.search(r'\(net\s+(?:(\d+)|"([^"]*)")\)', b)
    return (m.group(2) if m.group(2) is not None else int(m.group(1))) if m else 0

# ---------------------------------------------------------------- pads
pads = []   # dict(net, ref, num, x, y, x0,y0,x1,y1)
for a, b, fb in sexpr_blocks(txt, '(footprint'):
    rm = re.search(r'\(property "Reference" "([^"]+)"', fb)
    ref = rm.group(1) if rm else "?"
    at = re.search(r'\n\s*\(at\s+([\d.\-]+)\s+([\d.\-]+)(?:\s+([\d.\-]+))?', fb)
    fx, fy = float(at.group(1)), float(at.group(2))
    fr = math.radians(float(at.group(3) or 0))
    c, s = math.cos(fr), math.sin(fr)
    for pa, pb_, pb in sexpr_blocks(fb, '(pad'):
        pm = re.search(r'\(pad\s+"?([^"\s]+)"?', pb)
        num = pm.group(1) if pm else "?"
        pat = re.search(r'\(at\s+([\d.\-]+)\s+([\d.\-]+)(?:\s+([\d.\-]+))?', pb)
        lx, ly = float(pat.group(1)), float(pat.group(2))
        pr = float(pat.group(3) or 0)
        sm = re.search(r'\(size\s+([\d.]+)(?:\s+([\d.]+))?', pb)
        sx, sy = float(sm.group(1)), float(sm.group(2) or sm.group(1))
        arot = math.radians((float(at.group(3) or 0) + pr) % 180)
        hx = abs(sx / 2 * math.cos(arot)) + abs(sy / 2 * math.sin(arot))
        hy = abs(sx / 2 * math.sin(arot)) + abs(sy / 2 * math.cos(arot))
        wx, wy = fx + lx * c + ly * s, fy - lx * s + ly * c
        lm = re.search(r'\(pad\s+"?[^"\s]+"?\s+(\S+)', pb)
        ptype = lm.group(1) if lm else "thru_hole"
        laym = re.search(r'\(layers\s+([^)]*)\)', pb)
        lays = set()
        if ptype == "thru_hole" or (laym and "*.Cu" in laym.group(1)):
            lays = {"F.Cu", "B.Cu"}
        elif laym:
            lays = {l.strip('"') for l in laym.group(1).split()
                    if l.strip('"').endswith(".Cu")}
        pads.append(dict(net=net_of(pb), ref=ref, num=num, x=wx, y=wy,
                         x0=wx - hx, y0=wy - hy, x1=wx + hx, y1=wy + hy,
                         layers=lays or {"F.Cu", "B.Cu"}))

PADPOS = {("%s.%s" % (p['ref'], p['num'])): (p['x'], p['y']) for p in pads}

# ---------------------------------------------------------------- geometry
def seg_dist(p, a, b):
    """distance point p to segment a-b"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0,
        ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    qx, qy = a[0] + t * dx, a[1] + t * dy
    return math.hypot(p[0] - qx, p[1] - qy)

def seg_seg_dist(a, b, c, d):
    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2 = ccw(c, d, a), ccw(c, d, b)
    d3, d4 = ccw(a, b, c), ccw(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(seg_dist(a, c, d), seg_dist(b, c, d),
               seg_dist(c, a, b), seg_dist(d, a, b))

def rect_seg_dist(a, b, r):
    """distance from segment a-b to rect (x0,y0,x1,y1); 0 if inside"""
    x0, y0, x1, y1 = r
    # if either endpoint inside rect -> 0
    for p in (a, b):
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
            return 0.0
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
             ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return min(seg_seg_dist(a, b, e0, e1) for e0, e1 in edges)

def chamfer_pts(pts, cham=CHAMFER, protected=()):
    """Replace each 90-degree interior vertex with two 45-deg bends.
    Legs must already use only 0/45/90-degree steps.  A vertex listed
    in `protected` (a T-junction point) keeps its square corner."""
    if len(pts) <= 2:
        return list(pts)
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, v, p1 = pts[i - 1], pts[i], pts[i + 1]
        if any(abs(v[0] - q[0]) < 1e-6 and abs(v[1] - q[1]) < 1e-6
               for q in protected):
            out.append(v)
            continue
        d0 = (v[0] - p0[0], v[1] - p0[1])
        d1 = (p1[0] - v[0], p1[1] - v[1])
        l0, l1 = math.hypot(*d0), math.hypot(*d1)
        if l0 < 1e-9 or l1 < 1e-9:
            out.append(v)
            continue
        dot = (d0[0] * d1[0] + d0[1] * d1[1]) / (l0 * l1)
        ang = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
        if abs(ang - 90.0) < 0.01:
            c = min(cham, 0.45 * l0, 0.45 * l1)
            u0 = (d0[0] / l0, d0[1] / l0)
            u1 = (d1[0] / l1, d1[1] / l1)
            out.append((v[0] - u0[0] * c, v[1] - u0[1] * c))
            out.append((v[0] + u1[0] * c, v[1] + u1[1] * c))
        else:
            out.append(v)
    out.append(pts[-1])
    return out

# ---------------------------------------------------------------- build
legs_out = []   # (net, layer, w, [pts])   after chamfer
vias_out = []   # (net, x, y)
warn = []

def pad_dual_at(p, tol=0.05):
    """True if point p sits inside a pad present on BOTH copper layers
    (a THT pad gives a free F<->B junction, no via needed)."""
    for pp in pads:
        if ({"F.Cu", "B.Cu"} <= pp['layers'] and
                pp['x0'] - tol <= p[0] <= pp['x1'] + tol and
                pp['y0'] - tol <= p[1] <= pp['y1'] + tol):
            return pp
    return None

def on_pad(net, p, tol=0.12):
    return any(pp['net'] == net and
               pp['x0'] - tol <= p[0] <= pp['x1'] + tol and
               pp['y0'] - tol <= p[1] <= pp['y1'] + tol
               for pp in pads)

for net, legs in ROUTES.items():
    prev_layer = None
    prev_end = None
    prior_segs = []     # (a, b, layer) of earlier legs of this net
    # vertices that other legs of this net T onto -> keep square
    protected = set()
    for li, leg in enumerate(legs):
        if li == 0:
            continue
        p0 = leg[2][0]
        if any(seg_dist(p0, pp0, pp1) < 0.05
               for l2, w2, pts2 in legs[:li]
               for pp0, pp1 in zip(pts2, pts2[1:])):
            protected.add(p0)
    for li, leg in enumerate(legs):
        layer, w, pts = leg
        layer = "F.Cu" if layer in ("F", "F.Cu") else "B.Cu"
        if prev_layer is not None:
            touch = None   # layer of earlier copper this leg starts on
            if prev_end == pts[0]:
                touch = prev_layer
            else:
                for a, b, tl in prior_segs:
                    if seg_dist(pts[0], a, b) < 0.3:
                        touch = tl
                        break
            if touch is None and not on_pad(net, pts[0]):
                warn.append("%s leg %d: floating start %s (prev end %s)"
                            % (net, li, pts[0], prev_end))
            elif touch is not None and touch != layer \
                    and not pad_dual_at(pts[0]):
                if not any(n == net and abs(x - pts[0][0]) < 0.01
                           and abs(y - pts[0][1]) < 0.01
                           for n, x, y in vias_out):
                    vias_out.append((net, pts[0][0], pts[0][1]))
        cpts = chamfer_pts(pts, protected=protected)
        legs_out.append((net, layer, w, cpts))
        prior_segs += [(cpts[i], cpts[i + 1], layer)
                       for i in range(len(cpts) - 1)]
        prev_layer, prev_end = layer, cpts[-1]
for net, coords in EXTRA_VIAS.items():
    for x, y in coords:
        vias_out.append((net, x, y))
for x, y in GND_VIAS:
    vias_out.append(("GND", x, y))

# ---- per-segment records for checks
segs = []       # (net, layer, w, a, b)
for net, layer, w, pts in legs_out:
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if math.hypot(b[0]-a[0], b[1]-a[1]) < 0.01:
            continue
        ang = abs(math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))) % 180
        ok = min(ang, abs(ang-45), abs(ang-90), abs(ang-135))
        if ok > 0.6:
            warn.append("%s %s seg %s->%s angle %.1f not in {0,45,90}"
                        % (net, layer, a, b, ang))
        segs.append((net, layer, w, a, b))

def is_pad_touch(net, p, tol=0.12):
    return any(pp['net'] == net and
               pp['x0'] - tol <= p[0] <= pp['x1'] + tol and
               pp['y0'] - tol <= p[1] <= pp['y1'] + tol
               for pp in pads)

# ---- check: pads
for net, layer, w, a, b in segs:
    for p in pads:
        if p['net'] == net or layer not in p['layers']:
            continue
        d = rect_seg_dist(a, b, (p['x0'], p['y0'], p['x1'], p['y1']))
        need = w / 2 + CLR
        if d < need - 1e-6:
            warn.append("%s %s %s->%s w%.2f: pad %s.%s(%s) gap %.2f < %.2f"
                        % (net, layer, a, b, w, p['ref'], p['num'],
                           p['net'], d + w / 2 - w / 2, need))

# ---- check: foreign tracks same layer
for i in range(len(segs)):
    n1, l1, w1, a1, b1 = segs[i]
    for j in range(i + 1, len(segs)):
        n2, l2, w2, a2, b2 = segs[j]
        if n1 == n2 or l1 != l2:
            continue
        d = seg_seg_dist(a1, b1, a2, b2)
        need = w1 / 2 + w2 / 2 + CLR
        if d < need - 1e-6:
            warn.append("%s %s %s-%s crosses %s seg %s-%s gap %.2f < %.2f"
                        % (n1, l1, a1, b1, n2, a2, b2, d, need))

# ---- check: vias
for net, x, y in vias_out:
    for p in pads:
        d = math.hypot(x - p['x'], y - p['y'])
        if p['net'] != net and d < VIA_SIZE / 2 + CLR + max(
                p['x1'] - p['x'], p['y1'] - p['y']):
            warn.append("via %s@(%.2f,%.2f) inside/near pad %s.%s d=%.2f"
                        % (net, x, y, p['ref'], p['num'], d))
        elif d < 1.0 and d > 1e-6:
            warn.append("via %s@(%.2f,%.2f) %.2fmm from pad %s.%s (<1.0)"
                        % (net, x, y, d, p['ref'], p['num']))
    for n2, l2, w2, a2, b2 in segs:
        if n2 == net:
            continue
        d = seg_dist((x, y), a2, b2)
        need = VIA_SIZE / 2 + w2 / 2 + CLR
        if d < need - 1e-6:
            warn.append("via %s@(%.2f,%.2f) hits %s %s seg %s-%s gap %.2f"
                        % (net, x, y, n2, l2, a2, b2, d))
for i in range(len(vias_out)):
    for j in range(i + 1, len(vias_out)):
        n1, x1, y1 = vias_out[i]
        n2, x2, y2 = vias_out[j]
        d = math.hypot(x1 - x2, y1 - y2)
        if n1 != n2 and d < VIA_SIZE + CLR:
            warn.append("via %s@(%.2f,%.2f) too close to via %s@(%.2f,%.2f)"
                        % (n1, x1, y1, n2, x2, y2))

# ---- check: board edge
for net, layer, w, a, b in segs:
    for p in (a, b):
        for e, d in (("x=0", p[0]), ("x=135", 135 - p[0]),
                     ("y=0", p[1]), ("y=115", 115 - p[1])):
            if d - w / 2 < EDGE_CLR - 1e-6:
                warn.append("%s %s pt %s edge %s gap %.2f"
                            % (net, layer, p, e, d - w / 2))

# ---- check: pad exits axis-aligned for PADEXIT mm
for net, layer, w, pts in legs_out:
    for end_i, p, seg in ((0, pts[0], (pts[0], pts[1])),
                          (-1, pts[-1], (pts[-1], pts[-2]))):
        pp = next((pp for pp in pads if pp['net'] == net and
                   math.hypot(pp['x'] - p[0], pp['y'] - p[1]) < 0.45), None)
        if not pp:
            continue
        dx = abs(seg[1][0] - seg[0][0])
        dy = abs(seg[1][1] - seg[0][1])
        L = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
        if min(dx, dy) > 0.02:
            warn.append("%s %s pad %s.%s exit not axis-aligned %s"
                        % (net, layer, pp['ref'], pp['num'], seg))
        elif L < PADEXIT - 0.05:
            warn.append("%s %s pad %s.%s exit stub %.2fmm < %.1f"
                        % (net, layer, pp['ref'], pp['num'], L, PADEXIT))

# ---- check: no dangling leg endpoints (not on pad / not on same-net
# copper / not a via junction)
via_pts_set = [(x, y) for _, x, y in vias_out]
net_segs = {}
for net, layer, w, a, b in segs:
    net_segs.setdefault(net, []).append((a, b))
for net, layer, w, pts in legs_out:
    for p in (pts[0], pts[-1]):
        if is_pad_touch(net, p):
            continue
        if any(math.hypot(p[0] - vx, p[1] - vy) < 0.05
               for vx, vy in via_pts_set):
            continue
        hits = sum(1 for a, b in net_segs.get(net, [])
                   if seg_dist(p, a, b) < 0.25)
        # the endpoint sits on its own first/last seg (1) plus must touch
        # at least one other same-net segment
        if hits < 2:
            warn.append("%s %s dangling endpoint %s" % (net, layer, p))
missed = []
for p in pads:
    net = p['net']
    if net in (0, "0", "GND") or net not in ROUTES:
        continue
    hit = any(rect_seg_dist(a, b, (p['x0'], p['y0'], p['x1'], p['y1']))
              < w / 2 for nn, ll, w, a, b in segs if nn == net)
    if not hit:
        missed.append("%s.%s(%s)@(%.2f,%.2f)" %
                      (p['ref'], p['num'], net, p['x'], p['y']))
for m in missed:
    warn.append("PAD NOT ROUTED: " + m)
extra_nets = [n for n in ROUTES if not any(p['net'] == n for p in pads)]
for n in extra_nets:
    warn.append("route for unknown net " + str(n))

# ---------------------------------------------------------------- report
nv = sum(1 for _ in vias_out)
ns = sum(1 for _ in segs)
tl = sum(math.hypot(b[0]-a[0], b[1]-a[1]) for _,_,_,a,b in segs)
print("legs %d, segments %d, vias %d, total track %.1f mm"
      % (len(legs_out), ns, nv, tl))
if missed:
    print("unrouted pads: %d" % len(missed))
print("warnings: %d" % len(warn))
for w_ in warn[:80]:
    print("  " + w_)

# ---------------------------------------------------------------- emit
def fmt_seg(net, w, layer, a, b):
    return ('\t(segment\n\t\t(start %.4g %.4g)\n\t\t(end %.4g %.4g)\n'
            '\t\t(width %.4g)\n\t\t(layer "%s")\n\t\t(net "%s")\n'
            '\t\t(uuid "%s")\n\t)\n'
            % (a[0], a[1], b[0], b[1], w, layer, net, uuid.uuid4()))

def fmt_via(net, x, y):
    return ('\t(via\n\t\t(at %.4g %.4g)\n\t\t(size %.4g)\n\t\t(drill %.4g)\n'
            '\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "%s")\n\t\t(uuid "%s")\n\t)\n'
            % (x, y, VIA_SIZE, VIA_DRILL, net, uuid.uuid4()))

def strip_blocks(s, head):
    """Remove all balanced blocks starting with `head`."""
    spans = [(a, e) for a, e, _ in sexpr_blocks(s, head)]
    if not spans:
        return s
    out, i = [], 0
    for a, b in sorted(spans):
        out.append(s[i:a])
        i = b
    out.append(s[i:])
    return "".join(out)

if not CHECK and not missed and not warn:
    new = strip_blocks(txt, '(segment')
    new = strip_blocks(new, '(via')
    new = strip_blocks(new, '(filled_polygon')
    copper = "".join(fmt_seg(n, w, l, a, b) for n, l, w, a, b in segs)
    copper += "".join(fmt_via(n, x, y) for n, x, y in vias_out)
    # insert before the first (zone block so zones stay last
    zi = new.find('\n\t(zone')
    if zi < 0:
        zi = new.rfind(')')
    new = new[:zi + 1] + copper + new[zi + 1:]
    open(OUT, "w").write(new)
    print("wrote", OUT)
elif CHECK:
    print("(check only)")
else:
    print("NOT WRITING — fix warnings first")
