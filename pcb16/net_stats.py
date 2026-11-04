#!/usr/bin/env python3
"""net_stats.py — per-net routing review for a .kicad_pcb.

Reports per net: track length, via count, layers used, min width,
straight-line span of its pads vs routed length (detour ratio), and
counts of 45/90/other-angle segments plus stub-like dead ends.

Handles both generator output (net ids) and pcbnew-saved files
(net names as strings, multi-line sexprs).

Usage: python3 net_stats.py soma-carrier-v16.kicad_pcb
"""
import math, re, sys
from collections import defaultdict

F = sys.argv[1] if len(sys.argv) > 1 else "soma-carrier-v16.kicad_pcb"
txt = open(F).read()

def sexpr_blocks(s, head):
    """Yield balanced blocks starting with `head` e.g. '(segment'."""
    for m in re.finditer(re.escape(head), s):
        i, depth, instr, j = m.start(), 0, False, m.start()
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
        yield s[i:j + 1]

def net_of(b):
    m = re.search(r'\(net\s+(?:(\d+)|"([^"]*)")\)', b)
    if not m:
        return 0
    return m.group(2) if m.group(2) is not None else int(m.group(1))

# --- pads (world coords)
pads = []
for fb in sexpr_blocks(txt, '(footprint'):
    rm = re.search(r'\(property "Reference" "([^"]+)"', fb)
    ref = rm.group(1) if rm else "?"
    at = re.search(r'\n\s*\(at\s+([\d.\-]+)\s+([\d.\-]+)(?:\s+([\d.\-]+))?', fb)
    fx, fy = float(at.group(1)), float(at.group(2))
    frot = math.radians(float(at.group(3) or 0))
    c, s = math.cos(frot), math.sin(frot)
    for pb in sexpr_blocks(fb, '(pad'):
        pm = re.search(r'\(pad\s+"?([^"\s]+)"?', pb)
        num = pm.group(1) if pm else "?"
        pat = re.search(r'\(at\s+([\d.\-]+)\s+([\d.\-]+)', pb)
        lx, ly = float(pat.group(1)), float(pat.group(2))
        nid = net_of(pb)
        pads.append((nid, fx + lx * c + ly * s,
                     fy - lx * s + ly * c, ref, num))

# --- segments & vias
segs = []
for sb in sexpr_blocks(txt, '(segment'):
    m1 = re.search(r'\(start ([\d.\-]+) ([\d.\-]+)\)', sb)
    m2 = re.search(r'\(end ([\d.\-]+) ([\d.\-]+)\)', sb)
    mw = re.search(r'\(width ([\d.]+)\)', sb)
    ml = re.search(r'\(layer "([^"]+)"\)', sb)
    segs.append((float(m1.group(1)), float(m1.group(2)),
                 float(m2.group(1)), float(m2.group(2)),
                 float(mw.group(1)), ml.group(1), net_of(sb)))

vias = []
for vb in sexpr_blocks(txt, '(via'):
    ma = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)\)', vb)
    vias.append((float(ma.group(1)), float(ma.group(2)), net_of(vb)))

stat = defaultdict(lambda: dict(len=0.0, vias=0, layers=set(), minw=1e9,
                                n90=0, n45=0, nother=0, nseg=0))
for x1, y1, x2, y2, w, lay, nid in segs:
    st = stat[nid]
    st['len'] += math.hypot(x2 - x1, y2 - y1)
    st['layers'].add(lay)
    st['minw'] = min(st['minw'], w)
    st['nseg'] += 1
    ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1))) % 180
    if ang < 1 or abs(ang - 90) < 1:
        st['n90'] += 1
    elif abs(ang - 45) < 1 or abs(ang - 135) < 1:
        st['n45'] += 1
    else:
        st['nother'] += 1
for x, y, nid in vias:
    stat[nid]['vias'] += 1

ep_count = defaultdict(int)
for x1, y1, x2, y2, w, lay, nid in segs:
    ep_count[(nid, lay, round(x1, 2), round(y1, 2))] += 1
    ep_count[(nid, lay, round(x2, 2), round(y2, 2))] += 1
pad_pts = defaultdict(list)
for nid, x, y, r, n in pads:
    pad_pts[nid].append((x, y))
via_pts = defaultdict(list)
for x, y, nid in vias:
    via_pts[nid].append((x, y))

def near(p, pts, tol=0.9):
    return any(math.hypot(p[0]-q[0], p[1]-q[1]) <= tol for q in pts)

dead = defaultdict(int)
for (nid, lay, x, y), c in ep_count.items():
    if c != 1:
        continue
    if near((x, y), pad_pts.get(nid, [])) or \
       near((x, y), via_pts.get(nid, []), 0.45):
        continue
    dead[nid] += 1

net_pads = defaultdict(list)
for nid, x, y, r, n in pads:
    net_pads[nid].append((x, y))

print("%-9s %7s %4s %-11s %5s %4s %4s %4s %4s %5s  %s" %
      ("net", "len", "via", "layers", "minw", "seg", "hv", "d45",
       "oth", "stub", "detour"))
order = sorted(stat, key=lambda n: (n != 0 and str(n)))
tot_len = tot_via = 0
for nid in order:
    st = stat[nid]
    if nid == 0:
        nm = "0(NC)"
    else:
        nm = str(nid)
    pts = net_pads.get(nid, [])
    span = 0.0
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            span = max(span, math.hypot(pts[i][0]-pts[j][0],
                                        pts[i][1]-pts[j][1]))
    det = st['len'] / span if span > 0.5 else 0.0
    flag = " <<<" if det > 2.5 else ""
    print("%-9s %7.1f %4d %-11s %5.2f %4d %4d %4d %4d %5d  %5.2f%s" %
          (nm, st['len'], st['vias'], "/".join(sorted(st['layers'])),
           st['minw'], st['nseg'], st['n90'], st['n45'], st['nother'],
           dead.get(nid, 0), det, flag))
    tot_len += st['len']
    tot_via += st['vias']

print("\nTOTAL track %.1f mm, vias %d (incl. any GND stitching)" %
      (tot_len, tot_via))
