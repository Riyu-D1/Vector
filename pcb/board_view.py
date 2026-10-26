#!/usr/bin/env python3
"""board_view.py — ASCII eyes for the generated .kicad_pcb.

Usage: python3 board_view.py [soma-carrier.kicad_pcb] [-l F.Cu|B.Cu|both] [-c] [-u]

- text map at 1 mm/char: '#' pad, '=' track, 'o' via, '.' free, 'X' board edge
- -c: table of different-net pad pairs whose copper edges are < 0.5 mm apart
- -u: per unrouted net, the copper islands and the straight gap between them
"""
import math, re, sys
from pathlib import Path

F = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") \
    else str(Path(__file__).parent / "soma-carrier.kicad_pcb")
ARGS = set(a for a in sys.argv[1:] if a.startswith("-"))
txt = open(F).read()

# ---- parse ---------------------------------------------------------------
sex = re.findall(r'\(footprint\s+"([^"]+)"\n(.*?)\n\)\n', txt, re.S)
pads = []          # ref, num, wx, wy, halfx, halfy, net, layers
for libfp, body in sex:
    refm = re.search(r'\(property "Reference" "([^"]+)"', body)
    ref = refm.group(1) if refm else "?"
    at = re.search(r'\n\t+\(at ([\d.\-]+) ([\d.\-]+)(?: (\-?[\d.]+))?\)'
                   r'\n\t\(descr', body)
    if at is None:
        at = re.search(r'\n\t+\(at ([\d.\-]+) ([\d.\-]+)'
                       r'(?: (\-?[\d.]+))?\)\n', body)
    fx, fy, rot = float(at.group(1)), float(at.group(2)), \
        float(at.group(3) or 0)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for pm in re.finditer(
            r'\(pad "([^"]+)" (\S+) \S+\s*\n'
            r'\s*\(at ([\d.\-]+) ([\d.\-]+)(?: (\-?[\d.]+))?\)'
            r'.*?\(size ([\d.]+) ([\d.]+)\)'
            r'.*?\(net (\d+)(?: "([^"]*)")?\)', body, re.S):
        num, kind, lx, ly, prot, sx, sy, nid, nname = pm.groups()
        lx, ly = float(lx), float(ly)
        pr = float(prot or 0)
        # pad center in world — KiCad file convention: +y down, positive
        # angle is CCW on screen => world = rot(-rot) * local
        wx = fx + lx * c + ly * s
        wy = fy - lx * s + ly * c
        # pad orientation = fp rot + pad rot; keep half extents
        a = math.radians((rot + pr) % 180)
        hx = abs(float(sx) / 2 * math.cos(a)) \
            + abs(float(sy) / 2 * math.sin(a))
        hy = abs(float(sx) / 2 * math.sin(a)) \
            + abs(float(sy) / 2 * math.cos(a))
        layers = ("F.Cu",) if kind == "smd" else ("F.Cu", "B.Cu")
        pads.append(dict(ref=ref, num=num, x=wx, y=wy, hx=hx, hy=hy,
                         net=int(nid or 0), netname=nname or "",
                         layers=layers, kind=kind))

segs = []          # x1,y1,x2,y2,w,layer,net
for sm in re.finditer(
        r'\(segment \(start ([\d.\-]+) ([\d.\-]+)\) \(end ([\d.\-]+) ([\d.\-]+)\)'
        r'\s*\(width ([\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net (\d+)\)', txt):
    segs.append(tuple(float(v) if i < 5 else (v if i == 5 else int(v))
                      for i, v in enumerate(sm.groups())))

vias = []          # x, y, net
for vm in re.finditer(
        r'\(via \(at ([\d.\-]+) ([\d.\-]+)\) \(size [\d.]+\)\s*\(drill [\d.]+\)'
        r'\s*\(layers[^)]*\)\s*\(net (\d+)\)', txt):
    vias.append((float(vm.group(1)), float(vm.group(2)), int(vm.group(3))))

em = re.search(r'\(gr_rect\s*\(start ([\d.\-]+) ([\d.\-]+)\)\s*\(end ([\d.\-]+) '
               r'([\d.\-]+)\)', txt)
BW, BH = (float(em.group(3)), float(em.group(4))) if em else (115.0, 95.0)

NETNAME = {p["net"]: p["netname"] for p in pads}
netname = lambda n: NETNAME.get(n) or f"net{n}"

# ---- text map -------------------------------------------------------------
def render(layer):
    W, H = int(BW), int(BH)
    g = [["." for _ in range(W)] for _ in range(H)]
    for p in pads:
        if layer not in p["layers"]:
            continue
        for yy in range(max(0, int(p["y"] - p["hy"])),
                        min(H, int(p["y"] + p["hy"]) + 1)):
            for xx in range(max(0, int(p["x"] - p["hx"])),
                            min(W, int(p["x"] + p["hx"]) + 1)):
                g[yy][xx] = "#"
    for x1, y1, x2, y2, w, lay, n in segs:
        if lay != layer:
            continue
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) * 2))
        for t in range(steps + 1):
            x, y = x1 + (x2 - x1) * t / steps, y1 + (y2 - y1) * t / steps
            for dy in range(-int(w / 2), int(w / 2) + 1):
                for dx in range(-int(w / 2), int(w / 2) + 1):
                    xx, yy = int(x + dx), int(y + dy)
                    if 0 <= xx < W and 0 <= yy < H and g[yy][xx] == ".":
                        g[yy][xx] = "="
    for x, y, n in vias:
        xx, yy = int(x), int(y)
        if 0 <= xx < W and 0 <= yy < H:
            g[yy][xx] = "o"
    print(f"--- {layer}  (0..{W} x 0..{H})  '#'=pad '='=track 'o'=via ---")
    print("    " + "".join(str((x // 10) % 10) if x % 10 == 0 else
                             str(x % 10) for x in range(W)))
    for yy in range(H):
        if yy % 5 == 0:
            print(f"{yy:3d} " + "".join(g[yy]))
        else:
            print("    " + "".join(g[yy]))


# ---- collision table -------------------------------------------------------
def collisions(lim=0.5):
    print(f"--- pad pairs on different nets with edge gap < {lim} mm ---")
    out = []
    for i in range(len(pads)):
        for j in range(i + 1, len(pads)):
            a, b = pads[i], pads[j]
            if a["net"] == b["net"] and a["net"]:
                continue
            if a["ref"] == b["ref"]:
                continue
            dx = max(0, abs(a["x"] - b["x"]) - a["hx"] - b["hx"])
            dy = max(0, abs(a["y"] - b["y"]) - a["hy"] - b["hy"])
            d = math.hypot(dx, dy)
            if d < lim:
                out.append((d, a, b))
    for d, a, b in sorted(out, key=lambda t: t[0]):
        print(f"  {d:4.2f}mm  {a['ref']}.{a['num']}({netname(a['net'])})"
              f"({a['x']:.1f},{a['y']:.1f})  <->  {b['ref']}.{b['num']}"
              f"({netname(b['net'])})({b['x']:.1f},{b['y']:.1f})")
    if not out:
        print("  none")
    return out


# ---- unrouted islands ------------------------------------------------------
def islands():
    """For each net: connected copper blobs (pads touching tracks/vias) —
    two blobs = unconnected. Report each gap's endpoints + distance."""
    # collect per-net copper cells: pad rects + seg endpoints + vias
    per = {}
    for p in pads:
        if not p["net"]:
            continue
        per.setdefault(p["net"], []).append(
            (p["x"] - p["hx"], p["y"] - p["hy"],
             p["x"] + p["hx"], p["y"] + p["hy"]))
    for x1, y1, x2, y2, w, lay, n in segs:
        if not n:
            continue
        per.setdefault(n, []).append(
            (min(x1, x2) - w / 2, min(y1, y2) - w / 2,
             max(x1, x2) + w / 2, max(y1, y2) + w / 2))
    for x, y, n in vias:
        per.setdefault(n, []).append((x - .5, y - .5, x + .5, y + .5))
    print("--- nets with >1 copper island (unconnected stubs) ---")
    for n, rects in sorted(per.items()):
        blobs = []
        for r in rects:
            hit = None
            for bi, blob in enumerate(blobs):
                for bx0, by0, bx1, by1 in blob:
                    if not (r[2] < bx0 or r[0] > bx1 or
                            r[3] < by0 or r[1] > by1):
                        hit = bi
                        break
                if hit is not None:
                    break
            if hit is None:
                blobs.append([r])
            else:
                blobs[hit].append(r)
        # merge transitive
        merged = True
        while merged:
            merged = False
            for i in range(len(blobs)):
                for j in range(i + 1, len(blobs)):
                    if any(not (a[2] < b[0] or a[0] > b[2] or
                                a[3] < b[1] or a[1] > b[3])
                           for a in blobs[i] for b in blobs[j]):
                        blobs[i] += blobs[j]
                        del blobs[j]
                        merged = True
                        break
                if merged:
                    break
        if len(blobs) > 1:
            # nearest pair of blobs + their bbox centres
            pair, best = None, 1e9
            for i in range(len(blobs)):
                for j in range(i + 1, len(blobs)):
                    ax0 = min(r[0] for r in blobs[i]); ax1 = max(r[2] for r in blobs[i])
                    ay0 = min(r[1] for r in blobs[i]); ay1 = max(r[3] for r in blobs[i])
                    bx0 = min(r[0] for r in blobs[j]); bx1 = max(r[2] for r in blobs[j])
                    by0 = min(r[1] for r in blobs[j]); by1 = max(r[3] for r in blobs[j])
                    d = math.hypot(max(0, max(ax0 - bx1, bx0 - ax1)),
                                   max(0, max(ay0 - by1, by0 - ay1)))
                    if d < best:
                        best, pair = d, (i, j,
                            ((ax0 + ax1) / 2, (ay0 + ay1) / 2),
                            ((bx0 + bx1) / 2, (by0 + by1) / 2))
            i, j, ca, cb = pair
            print(f"  {netname(n)}: {len(blobs)} islands, nearest gap "
                  f"{best:.1f}mm  ({ca[0]:.0f},{ca[1]:.0f})->({cb[0]:.0f},{cb[1]:.0f})")


lay = "both"
for i, a in enumerate(sys.argv):
    if a == "-l" and i + 1 < len(sys.argv):
        lay = sys.argv[i + 1]

if "-c" in ARGS:
    collisions()
elif "-u" in ARGS:
    islands()
else:
    if lay in ("F.Cu", "both"):
        render("F.Cu")
    if lay in ("B.Cu", "both"):
        render("B.Cu")
    collisions()
    islands()
