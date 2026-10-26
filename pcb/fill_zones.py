#!/usr/bin/env python3
"""Bake GND pour fills into a .kicad_pcb.

Primary path: KiCad's bundled pcbnew ZONE_FILLER (the real engine —
clearances and thermal handling are exact).  The zones must be proper
copper zones first: SetIsRuleArea(False) unsticks the flag the
generator's K9-style zone sexpr trips.

Fallback path: pour.py computes the pour geometry with build123d and
emits filled_polygon data directly (used only if pcbnew is absent).

Usage: python3 fill_zones.py [board.kicad_pcb]
"""

import os
import re
import sys

KPYTHON_CANDIDATES = [
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework"
    "/Versions/3.9/bin/python3",
    "/usr/bin/python3",
]


def fill_with_pcbnew(path):
    """Fill via KiCad's bundled pcbnew. Returns True on success."""
    kpy = next((p for p in KPYTHON_CANDIDATES
                if os.path.exists(p)), None)
    if not kpy:
        return False
    import subprocess
    code = (
        "import pcbnew,sys;"
        "b=pcbnew.LoadBoard(sys.argv[1]);"
        "zs=list(b.Zones());"
        "[z.SetIsRuleArea(False) for z in zs];"
        "[z.UnFill() for z in zs];"
        "pcbnew.ZONE_FILLER(b).Fill(zs);"
        "b.Save(sys.argv[1]);"
        "print('pcbnew fill: ok')"
    )
    r = subprocess.run([kpy, "-c", code, path],
                       capture_output=True, text=True)
    return r.returncode == 0 and "ok" in r.stdout


def _sexpr_blocks(txt, head):
    """Yield (start, end, body) for balanced s-expr blocks at `head`."""
    for m in re.finditer(re.escape(head), txt):
        i, depth, instr, j = m.start(), 0, False, m.start()
        while j < len(txt):
            ch = txt[j]
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
        yield i, j + 1, txt[i:j + 1]


def parse_pads(txt):
    """-> [(x, y, hx, hy, prr, kind, layers, net)] global coords."""
    import math
    pads = []
    for _, _, body in _sexpr_blocks(txt, '(footprint'):
        at = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)(?: (\-?[\d.]+))?\)',
                       body)
        if not at:
            continue
        fx, fy = float(at.group(1)), float(at.group(2))
        rot = float(at.group(3) or 0)
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for _, _, pblk in _sexpr_blocks(body, '(pad '):
            at2 = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)'
                            r'(?: (\-?[\d.]+))?\)', pblk)
            sz = re.search(r'\(size ([\d.]+) ([\d.]+)\)', pblk)
            if not (at2 and sz):
                continue
            sm = re.search(r'\(pad "[^"]+" \S+ (\w+)', pblk)
            shape = sm.group(1) if sm else "rect"
            net = re.search(r'\(net \d+ "([^"]*)"\)', pblk)
            lay = re.search(r'\(layers ([^)]*)\)', pblk)
            lx, ly = float(at2.group(1)), float(at2.group(2))
            prot = float(at2.group(3) or 0)
            sw, sh = float(sz.group(1)), float(sz.group(2))
            net = net.group(1) if net else ""
            layers = lay.group(1).replace('"', '') if lay else "*.Cu"
            wx = fx + lx * c + ly * s
            wy = fy - lx * s + ly * c
            a = (rot + prot) % 360
            hx, hy = sw / 2, sh / 2
            if abs(a % 180 - 90) < 1:
                hx, hy = hy, hx
            elif a % 90 > 1:
                shape = "circle"         # arbitrary angle: be conservative
                hx = hy = math.hypot(sw, sh) / 2
            pads.append((wx, wy, hx, hy, math.hypot(hx, hy),
                         shape, layers, net))
    return pads


def parse_tracks(txt):
    """-> [(net_id, w, layer, a, b)]"""
    segs = []
    for m in re.finditer(
            r'\(segment\s*\n?\s*\(start ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*'
            r'\(end ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*\(width ([\d.]+)\)\s*'
            r'\n?\s*\(layer "([FB]\.Cu)"\)\s*\n?\s*\(net (\d+)\)', txt):
        x1, y1 = float(m.group(1)), float(m.group(2))
        x2, y2 = float(m.group(3)), float(m.group(4))
        w, l, nid = float(m.group(5)), m.group(6), int(m.group(7))
        segs.append((nid, w, l, (x1, y1), (x2, y2)))
    return segs


def parse_vias(txt):
    """-> [(x, y, net_id, radius)]"""
    out = []
    for m in re.finditer(
            r'\(via\s*\n?\s*\(at ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*'
            r'\(size ([\d.]+)\)\s*\n?\s*\(drill [\d.]+\)\s*\n?\s*'
            r'\(layers[^)]*\)\s*\n?\s*\(net (\d+)\)', txt):
        out.append((float(m.group(1)), float(m.group(2)),
                    int(m.group(4)), float(m.group(3)) / 2))
    return out


def fill_with_geometry(path):
    """Fallback: compute filled_polygon data with build123d."""
    import pour
    txt = open(path).read()
    names = {int(m.group(1)): m.group(2)
             for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', txt)}
    pads = parse_pads(txt)
    tracks = [(names.get(n, ""), w, l, a, b)
              for (n, w, l, a, b) in parse_tracks(txt)]
    vias = [(x, y, names.get(n, ""), r)
            for (x, y, n, r) in parse_vias(txt)]
    m = re.search(r'\(gr_rect\s*\n?\s*\(start 0 0\)\s*\n?\s*'
                  r'\(end ([\d.]+) ([\d.]+)\)', txt)
    if not m:
        sys.exit("no board outline found")
    bw, bh = float(m.group(1)), float(m.group(2))
    out_txt, last, nfill = [], 0, 0
    for i, j, body in _sexpr_blocks(txt, '(zone'):
        out_txt.append(txt[last:i])
        if '(net_name "GND")' not in body:
            out_txt.append(body)
            last = j
            continue
        layer = re.search(r'\(layer "([FB]\.Cu)"\)', body).group(1)
        body = body.replace("(connect_pads\n\t\t\t(clearance",
                            "(connect_pads yes\n\t\t\t(clearance")
        body = re.sub(r'\n\t\t\(filled_polygon\n(?:[^\n]*\n)*?\t\t\)',
                      '', body)
        polys = pour.fill_polys(layer, bw, bh, pads, tracks, vias)
        fills = "".join(pour.fill_sexp(layer, p) for p in polys)
        body = body.rstrip()[:-1].rstrip() + "\n" + fills + "\t)\n"
        out_txt.append(body)
        nfill += len(polys)
        print(f"{layer}: {len(polys)} island(s) kept")
        last = j
    out_txt.append(txt[last:])
    open(path, "w").write("".join(out_txt))
    print(f"geometry fill: wrote {nfill} polygons to {path}")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "soma-carrier.kicad_pcb"
    if fill_with_pcbnew(path):
        return
    print("pcbnew unavailable — using geometry fallback")
    fill_with_geometry(path)


if __name__ == "__main__":
    main()
