#!/usr/bin/env python3
"""pmap.py — fast ASCII map of the board for hand routing.

Usage:
  python3 pmap.py [file.kicad_pcb] [-x0 X0] [-x1 X1] [-y0 Y0] [-y1 Y1]
                  [-s SCALE] [--tracks] [--layer F.Cu|B.Cu] [--net NAME]

Defaults: whole board, pads only, ~0.8 char/mm.
  '#' pad, '=' track (if --tracks), 'o' via, '.' free, '+' every 5mm grid.
Coordinates labelled in mm. y grows DOWN (KiCad convention).
"""
import math, re, sys
from collections import defaultdict

args = sys.argv[1:]
F = "soma-carrier-v16.kicad_pcb"
X0, Y0, X1, Y1 = 0.0, 0.0, 135.0, 115.0
SCALE = 0.8          # chars per mm
SHOW_TR = False
LAYER = None
ONLY_NET = None
i = 0
while i < len(args):
    a = args[i]
    if not a.startswith("-"):
        F = a
    elif a == "-x0": i += 1; X0 = float(args[i])
    elif a == "-x1": i += 1; X1 = float(args[i])
    elif a == "-y0": i += 1; Y0 = float(args[i])
    elif a == "-y1": i += 1; Y1 = float(args[i])
    elif a == "-s": i += 1; SCALE = float(args[i])
    elif a == "--tracks": SHOW_TR = True
    elif a == "--layer": i += 1; LAYER = args[i]
    elif a == "--net": i += 1; ONLY_NET = args[i]
    i += 1

txt = open(F).read()

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
        yield s[i2:j + 1]

def net_of(b):
    m = re.search(r'\(net\s+(?:(\d+)|"([^"]*)")\)', b)
    return (m.group(2) if m.group(2) is not None else int(m.group(1))) if m else 0

CW = max(2, int((X1 - X0) * SCALE))   # grid width chars
CH = max(2, int((Y1 - Y0) * SCALE))
grid = [["." for _ in range(CW)] for _ in range(CH)]

def put(x, y, ch):
    cx = int((x - X0) * SCALE)
    cy = int((y - Y0) * SCALE)
    if 0 <= cx < CW and 0 <= cy < CH:
        grid[cy][cx] = ch

def line(x1, y1, x2, y2, ch):
    n = max(1, int(math.hypot(x2 - x1, y2 - y1) * SCALE * 3))
    for t in range(n + 1):
        put(x1 + (x2 - x1) * t / n, y1 + (y2 - y1) * t / n, ch)

# pads
npads = 0
for fb in sexpr_blocks(txt, '(footprint'):
    rm = re.search(r'\(property "Reference" "([^"]+)"', fb)
    ref = rm.group(1) if rm else "?"
    at = re.search(r'\n\s*\(at\s+([\d.\-]+)\s+([\d.\-]+)(?:\s+([\d.\-]+))?', fb)
    fx, fy = float(at.group(1)), float(at.group(2))
    fr = math.radians(float(at.group(3) or 0))
    c, s = math.cos(fr), math.sin(fr)
    for pb in sexpr_blocks(fb, '(pad'):
        pm = re.search(r'\(pad\s+"?([^"\s]+)"?', pb)
        num = pm.group(1) if pm else "?"
        pat = re.search(r'\(at\s+([\d.\-]+)\s+([\d.\-]+)', pb)
        lx, ly = float(pat.group(1)), float(pat.group(2))
        pr = float((re.search(r'\(at\s+[\d.\-]+\s+[\d.\-]+\s+([\d.\-]+)', pb) or [0, 0])[1] or 0)
        sm = re.search(r'\(size\s+([\d.]+)(?:\s+([\d.]+))?', pb)
        sx, sy = float(sm.group(1)), float(sm.group(2) or sm.group(1))
        a = math.radians((float(at.group(3) or 0) + pr) % 180)
        hx = abs(sx / 2 * math.cos(a)) + abs(sy / 2 * math.sin(a))
        hy = abs(sx / 2 * math.sin(a)) + abs(sy / 2 * math.cos(a))
        wx, wy = fx + lx * c + ly * s, fy - lx * s + ly * c
        nid = net_of(pb)
        if ONLY_NET and nid != ONLY_NET and nid != 0:
            continue
        npads += 1
        ch = '#' if nid != 0 else 'n'
        for yy in range(int((wy - hy - Y0) * SCALE), int((wy + hy - Y0) * SCALE) + 1):
            for xx in range(int((wx - hx - X0) * SCALE), int((wx + hx - X0) * SCALE) + 1):
                if 0 <= xx < CW and 0 <= yy < CH:
                    grid[yy][xx] = ch
        put(wx, wy, ch if nid == 0 else ('@' if nid != 0 else ch))

if SHOW_TR:
    for sb in sexpr_blocks(txt, '(segment'):
        m1 = re.search(r'\(start ([\d.\-]+) ([\d.\-]+)\)', sb)
        m2 = re.search(r'\(end ([\d.\-]+) ([\d.\-]+)\)', sb)
        ml = re.search(r'\(layer "([^"]+)"\)', sb)
        mw = re.search(r'\(width ([\d.]+)\)', sb)
        if LAYER and ml.group(1) != LAYER:
            continue
        if ONLY_NET and net_of(sb) != ONLY_NET:
            continue
        line(float(m1.group(1)), float(m1.group(2)),
             float(m2.group(1)), float(m2.group(2)), '=')
    for vb in sexpr_blocks(txt, '(via'):
        ma = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)\)', vb)
        if ONLY_NET and net_of(vb) != ONLY_NET:
            continue
        put(float(ma.group(1)), float(ma.group(2)), 'o')

# 5mm reference dots on otherwise-free cells
for gy in range(int(Y0) // 5 * 5, int(Y1) + 1, 5):
    for gx in range(int(X0) // 5 * 5, int(X1) + 1, 5):
        cx = int((gx - X0) * SCALE); cy = int((gy - Y0) * SCALE)
        if 0 <= cx < CW and 0 <= cy < CH and grid[cy][cx] == ".":
            grid[cy][cx] = ":"

# ruler
print("x: %g..%g  y: %g..%g  scale %.2f ch/mm  '#'=pad '@'=padctr 'n'=NCpad" %
      (X0, X1, Y0, Y1, SCALE))
hdr = "      "
for cx in range(CW):
    xmm = X0 + cx / SCALE
    hdr += str(int(xmm) // 10 % 10) if abs(xmm % 10) < 0.5 / SCALE else " "
print(hdr)
hdr2 = "      "
for cx in range(CW):
    xmm = X0 + cx / SCALE
    hdr2 += str(int(xmm) % 10) if abs(xmm % 10) < 0.5 / SCALE else " "
print(hdr2)
for cy in range(CH):
    ymm = Y0 + cy / SCALE
    lab = "%5.1f " % ymm if abs(ymm % 5) < 0.5 / SCALE else "      "
    print(lab + "".join(grid[cy]))
