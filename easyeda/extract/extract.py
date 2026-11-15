#!/usr/bin/env python3
"""
SOMA Carrier v1.3 — KiCad PCB -> EasyEDA Pro extension data extractor.

Parses order/pcb13_fix/soma-carrier-v13.kicad_pcb (KiCad 10 s-expression
format) and emits:

  easyeda/extension/src/board-data.ts   (embedded data module)
  easyeda/extract/board-data.json       (same data, for inspection/tests)

All output coordinates stay in KiCad board space: millimetres, +X right,
+Y down, rotations counter-clockwise (KiCad convention).  Conversion to
EasyEDA coordinates (mil, +Y up) happens inside the extension so there is
exactly one place where the frame change is applied.

For every component we emit pads/silk twice:
  * absolute board coordinates ("pads[].ax/ay", "silkAbs") — used to
    sanity-check that replicated tracks land on pads;
  * footprint-local coordinates ("fpPads", "fpSilk") — the component's
    KiCad rotation baked in, i.e. local coords rotated by the footprint
    rotation but NOT translated.  The extension draws these in the
    y-flipped EDA frame and places every component at rotation 0, which
    removes any dependence on EDA's rotation-sign convention.
"""

import json
import math
import re
import sys
import time

SRC = "order/pcb13_fix/soma-carrier-v13.kicad_pcb"
OUT_JSON = "easyeda/extract/board-data.json"
OUT_TS = "easyeda/extension/src/board-data.ts"

# ---------------------------------------------------------------- sexp parser

def tokenize(text):
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            tokens.append("(")
            i += 1
        elif c == ")":
            tokens.append(")")
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                elif text[j] == '"':
                    j += 1
                    break
                else:
                    buf.append(text[j])
                    j += 1
            tokens.append(('"', "".join(buf)))
            i = j
        else:
            j = i
            while j < n and text[j] not in "() \t\r\n":
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens

def parse(tokens):
    """Parse token stream into nested lists. Returns list of top-level nodes."""
    stack = [[]]
    for t in tokens:
        if t == "(":
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif t == ")":
            stack.pop()
        else:
            stack[-1].append(t)
    return stack[0]

def atom(node):
    return node[1] if isinstance(node, tuple) else node

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def find(node, key):
    """Direct children of `node` whose head == key."""
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]

def first(node, key, default=None):
    c = find(node, key)
    return c[0] if c else default

def xy(node):
    """(xy x y) or (start x y) / (at x y [rot]) -> (x,y[,rot])"""
    if node is None:
        return (0.0, 0.0, 0.0)
    vals = [num(v) for v in node[1:] if not isinstance(v, list)]
    if len(vals) >= 3:
        return (vals[0], vals[1], vals[2])
    if len(vals) >= 2:
        return (vals[0], vals[1], 0.0)
    return (0.0, 0.0, 0.0)

def rot_point(x, y, deg):
    """KiCad rotation (CCW in y-down frame) — matches gen_pcb.py rot()."""
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (x * c - y * s, x * s + y * c)

def r3(v):
    return round(v, 5)

# ---------------------------------------------------------------- extraction

def extract_footprint(fp):
    name = atom(fp[1]) if len(fp) > 1 else ""
    name = name.split(":")[-1]
    layer = atom(first(fp, "layer", [None, "F.Cu"])[1])
    ax_, ay_, arot = xy(first(fp, "at"))
    ref = val = ""
    for p in find(fp, "property"):
        if len(p) >= 3 and atom(p[1]) == "Reference":
            ref = atom(p[2])
        elif len(p) >= 3 and atom(p[1]) == "Value":
            val = atom(p[2])
    # fp_text reference fallback
    if not ref:
        for t in find(fp, "fp_text"):
            if len(t) >= 3 and t[1] == "reference":
                ref = atom(t[2])

    pads = []
    for p in find(fp, "pad"):
        pnum = atom(p[1])
        ptype = p[2]          # thru_hole | smd | np_thru_hole
        pshape = p[3]         # circle | rect | oval | roundrect | custom
        lx, ly, lrot = xy(first(p, "at"))
        size = first(p, "size")
        w = num(size[1]) if size and len(size) > 1 else 0.0
        h = num(size[2]) if size and len(size) > 2 else w
        drill = first(p, "drill")
        dvals = []
        if drill:
            dvals = [num(v) for v in drill[1:] if not isinstance(v, list)]
        d_oval = bool(drill and len(drill) > 1 and drill[1] == "oval")
        dx = dvals[0] if dvals else 0.0
        dy = dvals[1] if len(dvals) > 1 else dx
        netn = first(p, "net")
        net = atom(netn[1]) if netn and len(netn) > 1 else ""
        layers = [atom(v) for v in first(p, "layers", [None])[1:]] \
            if first(p, "layers") else []
        # absolute (board) coords
        rx, ry = rot_point(lx, ly, arot)
        pads.append({
            "num": pnum, "type": ptype, "shape": pshape,
            "net": net,
            "ax": r3(ax_ + rx), "ay": r3(ay_ + ry),
            "lx": r3(rx), "ly": r3(ry),
            "rot": r3(arot + lrot),
            "w": r3(w), "h": r3(h),
            "drillX": r3(dx), "drillY": r3(dy),
            "drillOval": d_oval,
            "layers": layers,
        })

    def silk_items():
        items = []
        for tag in ("fp_line",):
            for g in find(fp, tag):
                lay = atom(first(g, "layer", [None, ""])[1])
                if "SilkS" not in str(lay):
                    continue
                s = xy(first(g, "start"))
                e = xy(first(g, "end"))
                wdt = num(first(first(g, "stroke"), "width", [0, 0.12])[1])
                s1 = rot_point(s[0], s[1], arot)
                e1 = rot_point(e[0], e[1], arot)
                items.append({"k": "l", "x1": r3(s1[0]), "y1": r3(s1[1]),
                              "x2": r3(e1[0]), "y2": r3(e1[1]), "w": r3(wdt),
                              "ax1": r3(ax_ + s1[0]), "ay1": r3(ay_ + s1[1]),
                              "ax2": r3(ax_ + e1[0]), "ay2": r3(ay_ + e1[1])})
        for g in find(fp, "fp_circle"):
            lay = atom(first(g, "layer", [None, ""])[1])
            if "SilkS" not in str(lay):
                continue
            c = xy(first(g, "center"))
            e = xy(first(g, "end"))
            r = math.hypot(e[0] - c[0], e[1] - c[1])
            wdt = num(first(first(g, "stroke"), "width", [0, 0.12])[1])
            c1 = rot_point(c[0], c[1], arot)
            items.append({"k": "c", "x": r3(c1[0]), "y": r3(c1[1]),
                          "r": r3(r), "w": r3(wdt),
                          "ax": r3(ax_ + c1[0]), "ay": r3(ay_ + c1[1])})
        for g in find(fp, "fp_arc"):
            lay = atom(first(g, "layer", [None, ""])[1])
            if "SilkS" not in str(lay):
                continue
            s = xy(first(g, "start"))
            m = xy(first(g, "mid"))
            e = xy(first(g, "end"))
            wdt = num(first(first(g, "stroke"), "width", [0, 0.12])[1])
            pts = arc_points(s, m, e)
            rpts = [rot_point(px, py, arot) for px, py in pts]
            items.append({"k": "a", "pts": [[r3(p[0]), r3(p[1])] for p in rpts],
                          "w": r3(wdt),
                          "apts": [[r3(ax_ + p[0]), r3(ay_ + p[1])] for p in rpts]})
        for g in find(fp, "fp_poly"):
            lay = atom(first(g, "layer", [None, ""])[1])
            if "SilkS" not in str(lay):
                continue
            wdt = num(first(first(g, "stroke"), "width", [0, 0.12])[1])
            pts = [xy(p)[:2] for p in find(first(g, "pts"), "xy")]
            rpts = [rot_point(px, py, arot) for px, py in pts]
            items.append({"k": "p", "pts": [[r3(p[0]), r3(p[1])] for p in rpts],
                          "w": r3(wdt),
                          "apts": [[r3(ax_ + p[0]), r3(ay_ + p[1])] for p in rpts]})
        return items

    def arc_points(s, m, e):
        """Sample KiCad 3-point arc into polyline pts (KiCad local frame)."""
        # Circle through 3 points
        ax__, ay__ = s[0], s[1]
        bx, by = m[0], m[1]
        cx, cy = e[0], e[1]
        d = 2 * (ax__ * (by - cy) + bx * (cy - ay__) + cx * (ay__ - by))
        if abs(d) < 1e-9:
            return [s[:2], e[:2]]
        ux = ((ax__**2 + ay__**2) * (by - cy) + (bx**2 + by**2) * (cy - ay__)
              + (cx**2 + cy**2) * (ay__ - by)) / d
        uy = ((ax__**2 + ay__**2) * (cx - bx) + (bx**2 + by**2) * (ax__ - cx)
              + (cx**2 + cy**2) * (bx - ax__)) / d
        r = math.hypot(ax__ - ux, ay__ - uy)
        a0 = math.atan2(ay__ - uy, ax__ - ux)
        a1 = math.atan2(by - uy, bx - ux)
        a2 = math.atan2(cy - uy, cx - ux)
        # choose sweep direction that passes through the mid angle
        def norm(a):
            while a < 0:
                a += 2 * math.pi
            while a >= 2 * math.pi:
                a -= 2 * math.pi
            return a
        def between(a, lo, hi):
            if lo <= hi:
                return lo <= a <= hi
            return a >= lo or a <= hi
        la, ha = norm(a0), norm(a2)
        am = norm(a1)
        if not between(am, la, ha):
            la, ha = ha, la
        # still might need wrap direction: test both sweeps
        if not between(am, la, ha):
            la, ha = norm(a0), norm(a2)
            am2 = am
            # go other way (decreasing)
            pts = []
            start, end = la, ha
            if start <= end:
                start += 2 * math.pi
            n = max(4, int(abs(start - end) / (math.pi / 12)) + 1)
            for i in range(n + 1):
                t = start - (start - end) * i / n
                pts.append((ux + r * math.cos(t), uy + r * math.sin(t)))
            return pts
        pts = []
        n = max(4, int((ha - la) / (math.pi / 12)) + 1)
        for i in range(n + 1):
            t = la + (ha - la) * i / n
            pts.append((ux + r * math.cos(t), uy + r * math.sin(t)))
        return pts

    silk = silk_items()
    return {
        "ref": ref, "value": val, "footprint": name,
        "x": r3(ax_), "y": r3(ay_), "rot": r3(arot),
        "side": "B" if layer == "B.Cu" else "F",
        "pads": pads, "silk": silk,
    }

def main():
    t0 = time.time()
    text = open(SRC, encoding="utf-8").read()
    toks = tokenize(text)
    top = parse(toks)
    root = top[0]
    assert root[0] == "kicad_pcb"

    parts, holes = [], []
    for fp in find(root, "footprint"):
        f = extract_footprint(fp)
        if f["footprint"].startswith("MountingHole"):
            for p in f["pads"]:
                holes.append({"x": p["ax"], "y": p["ay"],
                              "drill": p["drillX"], "size": p["w"]})
            continue
        parts.append(f)

    tracks = []
    for s in find(root, "segment"):
        st = xy(first(s, "start"))
        en = xy(first(s, "end"))
        wdt = num(first(s, "width", [0, 0.25])[1])
        lay = atom(first(s, "layer", [None, ""])[1])
        netn = first(s, "net")
        tracks.append({"net": atom(netn[1]) if netn and len(netn) > 1 else "",
                       "layer": lay, "x1": r3(st[0]), "y1": r3(st[1]),
                       "x2": r3(en[0]), "y2": r3(en[1]), "w": r3(wdt)})

    vias = []
    for v in find(root, "via"):
        a = xy(first(v, "at"))
        netn = first(v, "net")
        vias.append({"net": atom(netn[1]) if netn and len(netn) > 1 else "",
                     "x": r3(a[0]), "y": r3(a[1]),
                     "drill": num(first(v, "drill", [0, 0.3])[1]),
                     "size": num(first(v, "size", [0, 0.7])[1])})

    zones = []
    for z in find(root, "zone"):
        netn = first(z, "net")
        lay = atom(first(z, "layer", [None, ""])[1])
        poly = first(z, "polygon")
        pts = [xy(p)[:2] for p in find(first(poly, "pts"), "xy")] if poly else []
        if pts:
            zones.append({"net": atom(netn[1]) if netn and len(netn) > 1 else "",
                          "layer": lay,
                          "pts": [[r3(p[0]), r3(p[1])] for p in pts]})

    outline = []
    for g in find(root, "gr_rect") + find(root, "gr_line") + find(root, "gr_poly"):
        lay = atom(first(g, "layer", [None, ""])[1])
        if lay != "Edge.Cuts":
            continue
        if g[0] == "gr_rect":
            s = xy(first(g, "start"))
            e = xy(first(g, "end"))
            x1, y1 = min(s[0], e[0]), min(s[1], e[1])
            x2, y2 = max(s[0], e[0]), max(s[1], e[1])
            outline = [[r3(x1), r3(y1)], [r3(x2), r3(y1)],
                       [r3(x2), r3(y2)], [r3(x1), r3(y2)]]
        elif g[0] == "gr_line":
            s = xy(first(g, "start"))
            e = xy(first(g, "end"))
            outline.append([r3(s[0]), r3(s[1]), r3(e[0]), r3(e[1])])

    silk_text = []
    for g in find(root, "gr_text"):
        lay = atom(first(g, "layer", [None, ""])[1])
        if "SilkS" not in str(lay):
            continue
        a = xy(first(g, "at"))
        font = first(first(g, "effects"), "font")
        sz = first(font, "size")
        silk_text.append({"text": atom(g[1]), "x": r3(a[0]), "y": r3(a[1]),
                          "rot": r3(a[2]), "layer": lay,
                          "h": num(sz[1]) if sz and len(sz) > 1 else 1.0})

    # nets present on pads/tracks
    nets = sorted({p["net"] for pt in parts for p in pt["pads"] if p["net"]}
                  | {t["net"] for t in tracks if t["net"]}
                  | {v["net"] for v in vias if v["net"]}
                  | {z["net"] for z in zones if z["net"]})

    data = {
        "meta": {
            "source": SRC,
            "kicadVersion": "10.0",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "counts": {"parts": len(parts), "mountingHoles": len(holes),
                       "tracks": len(tracks), "vias": len(vias),
                       "zones": len(zones), "nets": len(nets)},
        },
        "outline": outline,
        "mountingHoles": holes,
        "zones": zones,
        "nets": nets,
        "parts": parts,
        "tracks": tracks,
        "vias": vias,
        "silkText": silk_text,
    }

    with open(OUT_JSON, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    with open(OUT_TS, "w") as f:
        f.write("/* Auto-generated by easyeda/extract/extract.py — do not edit. */\n")
        f.write("import type { BoardData } from './board-data-types';\n\n")
        f.write("export const BOARD_DATA: BoardData = ")
        json.dump(data, f, separators=(",", ":"))
        f.write(";\n")

    # -------- sanity report
    print(f"parts={len(parts)} holes={len(holes)} tracks={len(tracks)} "
          f"vias={len(vias)} zones={len(zones)} nets={len(nets)}")
    refset = sorted(p["ref"] for p in parts)
    print("refs:", " ".join(refset))
    nopads = [p["ref"] for p in parts if not p["pads"]]
    if nopads:
        print("!! parts with no pads:", nopads)
    # pads with no net
    nonet = [(p["ref"], q["num"]) for p in parts for q in p["pads"]
             if not q["net"] and q["type"] != "np_thru_hole"]
    if nonet:
        print("!! unconnected pads:", nonet)
    bside = [p["ref"] for p in parts if p["side"] != "F"]
    if bside:
        print("!! B-side parts:", bside)
    smd = [(p["ref"], q["num"]) for p in parts for q in p["pads"] if q["type"] == "smd"]
    print("smd pads:", smd)
    pad_nets = {p["net"] for pt in parts for p in pt["pads"]}
    track_nets = {t["net"] for t in tracks}
    print("nets only on tracks (not pads):", sorted(track_nets - pad_nets))
    print("nets only on pads (not tracks):", sorted(pad_nets - track_nets - {""}))
    print(f"elapsed {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
