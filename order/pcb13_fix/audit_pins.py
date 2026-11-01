#!/usr/bin/env python3
"""Pin-by-pin netlist audit: dump every footprint pad with net + position.

Reads the emitted soma-carrier-v13.kicad_pcb (self-contained: pad position,
net id, drill/size, footprint rotation) and prints a table per ref.
Also emits a per-net pad count and flags non-GND pads sharing a net
between the three rails (isolation check).
"""
import math
import re
import sys
from collections import defaultdict

PCB = sys.argv[1] if len(sys.argv) > 1 else "soma-carrier-v13.kicad_pcb"
src = open(PCB).read()


def blocks(s, name):
    """Return balanced-paren blocks starting with (name ..."""
    out, i = [], 0
    pat = "(" + name
    while True:
        j = s.find(pat, i)
        if j < 0:
            break
        if j + len(pat) < len(s) and s[j + len(pat)] not in " \t\n":
            i = j + 1
            continue
        depth, k = 0, j
        while k < len(s):
            if s[k] == "(":
                depth += 1
            elif s[k] == ")":
                depth -= 1
                if depth == 0:
                    out.append(s[j:k + 1])
                    break
            k += 1
        i = k + 1
    return out


def f1(b, key, default=None):
    m = re.search(r"\(%s\s+([^()\s]+)" % key, b)
    return m.group(1).strip('"') if m else default


net_names = {}
for nb in blocks(src, "net"):
    m = re.match(r"\(net\s+(\d+)\s+\"([^\"]*)\"", nb)
    if m:
        net_names[int(m.group(1))] = m.group(2)

pads = []          # (ref, padnum, net, x, y, drill, sizex, sizey, layers)
fp_meta = {}       # ref -> (x, y, rot, footprint, value)
for fb in blocks(src, "footprint"):
    if fb.startswith("(footprint \"dummy") or "fp_text" in fb[:60]:
        continue
    lib = f1(fb, "footprint", "")
    at = re.search(r"\n\s*\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?", fb)
    fx, fy = float(at.group(1)), float(at.group(2))
    frot = float(at.group(3) or 0)
    rm = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', fb)
    vm = re.search(r'\(property\s+"Value"\s+"([^"]*)"', fb)
    ref = rm.group(1) if rm else "?"
    val = vm.group(1) if vm else ""
    fp_meta[ref] = (fx, fy, frot, lib.split("/")[-1], val)
    a = math.radians(frot)
    c, s = math.cos(a), math.sin(a)
    for pb in blocks(fb, "pad"):
        num = f1(pb, "pad", "?")
        ptype = re.match(r"\(pad\s+\S+\s+(\S+)", pb).group(1)
        pat = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?", pb)
        lx, ly = float(pat.group(1)), float(pat.group(2))
        pr = float(pat.group(3) or 0)
        # KiCad file frame: y down, footprint rot applied via rot(-a)
        ta = math.radians(frot + pr)
        tc, ts = math.cos(ta), math.sin(ta)
        wx = fx + lx * c + ly * s
        wy = fy - lx * s + ly * c
        nm = re.search(r'\(net\s+(?:(\d+)|"([^"]*)")', pb)
        net = nm.group(1) if nm and nm.group(1) else (
            nm.group(2) if nm else 0)
        size = re.search(r"\(size\s+([-\d.]+)(?:\s+([-\d.]+))?", pb)
        sx = float(size.group(1))
        sy = float(size.group(2)) if size and size.group(2) else sx
        dm = re.search(r"\(drill\s+(?:oval\s+)?([-\d.]+)", pb)
        drill = float(dm.group(1)) if dm else 0.0
        layers = re.search(r"\(layers\s+([^)]+)\)", pb)
        pads.append((ref, num, net_names.get(net, net), wx, wy,
                     drill, sx, sy, ptype,
                     layers.group(1) if layers else ""))

order = {r: i for i, r in enumerate(dict.fromkeys(p[0] for p in pads))}
for ref in sorted(order, key=order.get):
    rows = sorted((p for p in pads if p[0] == ref),
                  key=lambda p: int(p[1]) if p[1].isdigit() else 0)
    x, y, rot, lib, val = fp_meta.get(ref, (0, 0, 0, "?", ""))
    print("### %s  %s  %s @ (%.2f, %.2f) rot=%g" % (ref, val, lib, x, y, rot))
    for r in rows:
        print("  pad %-3s net %-10s (%.2f, %.2f) drill=%.2f size=%.1fx%.1f %s"
              % (r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]))

net_pads = defaultdict(list)
for p in pads:
    net_pads[p[2]].append((p[0], p[1]))
print("\n=== nets ===")
for n in sorted(net_pads, key=str):
    print("%-12s %2d pads: %s" % (n, len(net_pads[n]),
          ", ".join("%s.%s" % t for t in net_pads[n])))

# rail isolation: pads shared between rail nets would show as one net;
# instead report any pad whose ref pads span two rails (part joins them).
print("\n=== rail joins ===")
for ref in order:
    nets = {p[2] for p in pads if p[0] == ref}
    hot = nets & {"+12V_IN", "+12V_SW", "+12V", "+5V", "+5V_MCU", "+3V3"}
    if len(hot) > 1:
        print("%s joins %s" % (ref, sorted(hot)))
