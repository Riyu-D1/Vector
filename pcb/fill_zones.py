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
    if not (r.returncode == 0 and "ok" in r.stdout):
        return False
    # drop dead-copper polygons marked (island yes) — they never reach a
    # GND pad, so removing them is strictly cosmetic cleanup
    dropped = _strip_islands(path)
    print(f"stripped {dropped} isolated island polygon(s)")
    _fixup_gnd(kpy, path)
    return True


def _strip_islands(path):
    """Remove (island yes) filled_polygons from the file in place."""
    txt = open(path).read()
    out, last, dropped = [], 0, 0
    for i, j, body in _sexpr_blocks(txt, '(filled_polygon'):
        out.append(txt[last:i])          # keep ALL non-polygon text —
        # dropping the gap with the block eats the board head when the
        # first polygon is an island
        if '(island yes)' in body:
            dropped += 1
        else:
            out.append(body)
        last = j
    out.append(txt[last:])
    open(path, "w").write("".join(out))
    return dropped


def _inside(px, py, pts):
    c, j = False, len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > py) != (yj > py)) and \
                (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            c = not c
        j = i
    return c


def _pour_polys(txt):
    """-> {layer: [polygon point lists]} from filled GND zone data."""
    polys = {"F.Cu": [], "B.Cu": []}
    for _, _, zb in _sexpr_blocks(txt, '(zone'):
        if '"GND"' not in zb:
            continue
        lay = re.search(r'\(layer "([FB]\.Cu)"', zb)
        lay = lay.group(1) if lay else None
        for _, _, pb in _sexpr_blocks(zb, '(filled_polygon'):
            pts = [(float(a), float(b)) for a, b in
                   re.findall(r'\(xy ([\d.\-]+) ([\d.\-]+)\)', pb)]
            if pts and lay in polys:
                polys[lay].append(pts)
    return polys


def _seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(
        1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    dx = p[0] - (a[0] + vx * t)
    dy = p[1] - (a[1] + vy * t)
    return (dx * dx + dy * dy) ** 0.5


def _fixup_gnd(kpy, path):
    """Two post-fill repairs, verified against the just-written pour:

    1. Stitch-grid vias that landed outside BOTH pours are dead holes
       (KiCad: via_dangling). Delete them — vias inside a pour are real
       stitches and stay.
    2. GND pads the pour can't reach (sealed pockets) get a stub track
       to a via dropped inside a verified pour polygon, then a refill.
    """
    import math
    import subprocess
    import uuid as _uuid
    txt = open(path).read()
    polys = _pour_polys(txt)
    gnd_pads = [p for p in parse_pads(txt) if p[7] == "GND"]
    tracks = parse_tracks(txt)
    vias = parse_vias(txt)

    def in_pour(x, y):
        return {ln for ln, pl in polys.items()
                if any(_inside(x, y, p) for p in pl)}

    # --- 1. prune stitch vias outside both pours -----------------------
    # a route via always has a track endpoint on it; stitch vias don't
    def _has_track(vx, vy):
        return any(_seg_dist((vx, vy), a, b) < 0.4
                   for _, _, _, a, b in tracks)
    dead = {(x, y) for x, y, n, _r in vias
            if n == "GND" and not _has_track(x, y) and not in_pour(x, y)}
    if dead:
        out, last = [], 0
        for i, j, body in _sexpr_blocks(txt, '(via'):
            out.append(txt[last:i])
            m = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)\)', body)
            if not (m and (float(m.group(1)), float(m.group(2))) in dead):
                out.append(body)
            last = j
        out.append(txt[last:])
        txt = "".join(out)
        print(f"pruned {len(dead)} dead stitch via(s)")

    # --- 2. stitch orphan GND pads ------------------------------------
    all_pads = parse_pads(txt)
    vias = [v for v in vias if (v[0], v[1]) not in dead]
    # authoritative orphan list: KiCad's own DRC on the filled board
    import json as _json
    import os as _os
    import tempfile
    kcli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    orphans = {}   # (x,y) -> set of layers needing relief; '*' = any
    if _os.path.exists(kcli):
        with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False) as tf:
            rep = tf.name
        subprocess.run([kcli, "pcb", "drc", "--format", "json",
                        "-o", rep, path], capture_output=True)
        try:
            repj = _json.load(open(rep))
            for u in repj.get("unconnected_items", []):
                for it in u.get("items", []):
                    if "pad" in it.get("description", ""):
                        p = it["pos"]
                        orphans.setdefault(
                            (round(p["x"], 2), round(p["y"], 2)),
                            set()).add("*")
            # starved_thermal pads have a marginal spoke link — stitch
            # them too so the joint is solid copper, not a whisker. The
            # stub runs on the FLAGGED layer's pour — stitching to the
            # other layer doesn't help a starving relief spoke.
            for v in repj.get("violations", []):
                if v.get("type") != "starved_thermal":
                    continue
                ln = ("F.Cu" if "F.Cu" in v.get("description", "")
                      else "B.Cu")
                for it in v.get("items", []):
                    if "pad" in it.get("description", ""):
                        p = it["pos"]
                        orphans.setdefault(
                            (round(p["x"], 2), round(p["y"], 2)),
                            set()).add(ln)
        except Exception as e:
            print("  WARNING: fixup DRC parse failed:", e)
        finally:
            _os.unlink(rep)

    def _deep_pour(x, y):
        # inside a pour with ~0.6mm depth — survives the refill
        lns = in_pour(x, y)
        if not lns:
            return set()
        return {ln for ln in lns if all(
            in_pour(x + dx, y + dy) and ln in in_pour(x + dx, y + dy)
            for dx, dy in ((0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6)))}

    def _stub_ok(x0, y0, x1, y1, ln):
        # stub pad->via on layer ln: no foreign pads, foreign vias, or
        # foreign tracks touched. The via at (x1,y1) is a through-hole —
        # its annulus must clear foreign copper on BOTH layers and sit
        # inside `ln`'s pour.
        for px, py, hx, hy, _r, _k, _plays, pn in all_pads:
            if abs(px - x0) < 0.01 and abs(py - y0) < 0.01:
                continue
            if ln not in _plays and "*.Cu" not in _plays:
                continue
            for t in (0.15, 0.4, 0.65, 0.9, 1.0):
                qx, qy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                if abs(qx - px) < hx + 0.4 and abs(qy - py) < hy + 0.4:
                    return False
            # via annulus vs the pad itself on either layer
            if abs(x1 - px) < hx + 0.55 and abs(y1 - py) < hy + 0.55:
                return False
        for nid, w, l, a, b in tracks:
            if nid == "GND":
                continue
            for t in (0.15, 0.4, 0.65, 0.9, 1.0):
                qx, qy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                if l == ln and _seg_dist((qx, qy), a, b) < w / 2 + 0.45:
                    return False
            # via annulus vs foreign track on EITHER layer — a B.Cu
            # track under the via shorts it just like an F.Cu one does
            if _seg_dist((x1, y1), a, b) < w / 2 + 0.55:
                return False
        for vx, vy, n, r in vias:
            if n != "GND" and (x1 - vx) ** 2 + (y1 - vy) ** 2 \
                    < (r + 0.65) ** 2:
                return False
        return True

    stubs, nvias = [], 0
    for (x, y, hx, hy, _r, _kind, plays, _n) in gnd_pads:
        if (round(x, 2), round(y, 2)) not in orphans:
            continue
        placed = False
        for r in (1.9, 2.5, 3.2, 4.2, 5.5):
            if placed:
                break
            for k in range(16):
                a = math.radians(k * 22.5)
                qx, qy = x + r * math.cos(a), y + r * math.sin(a)
                lns = _deep_pour(qx, qy)
                if not lns:
                    continue
                need = orphans[(round(x, 2), round(y, 2))]
                pref = [l for l in ("F.Cu", "B.Cu")
                        if l in need and l in lns]
                ln = (pref[0] if pref else
                      "B.Cu" if "B.Cu" in lns else "F.Cu")
                if _stub_ok(x, y, qx, qy, ln):
                    stubs.append((x, y, qx, qy, ln))
                    placed = True
                    break
        if not placed:
            print(f"  WARNING: GND pad at ({x:.1f},{y:.1f}) unstitchable")
    if stubs:
        add = []
        for x0, y0, x1, y1, ln in stubs:
            add.append(
                f'\t(segment\n\t\t(start {x0:.3f} {y0:.3f})'
                f'\n\t\t(end {x1:.3f} {y1:.3f})\n\t\t(width 0.5)'
                f'\n\t\t(layer "{ln}")\n\t\t(net "GND")'
                f'\n\t\t(uuid "{_uuid.uuid4()}")\n\t)\n')
            add.append(
                f'\t(via\n\t\t(at {x1:.3f} {y1:.3f})\n\t\t(size 0.7)'
                f'\n\t\t(drill 0.3)\n\t\t(layers "F.Cu" "B.Cu")'
                f'\n\t\t(net "GND")\n\t\t(uuid "{_uuid.uuid4()}")\n\t)\n')
            nvias += 1
        # embedded_fonts appears inside EVERY footprint too — replace()
        # would inject board vias/segments into all of them. The root
        # (board-level) occurrence is the last one in file order.
        idx = txt.rfind("\t(embedded_fonts no)")
        txt = txt[:idx] + "".join(add) + txt[idx:]
        open(path, "w").write(txt)
        print(f"stitched {nvias} orphan GND pad(s); refilling")
        code = ("import pcbnew,sys;"
                "b=pcbnew.LoadBoard(sys.argv[1]);"
                "zs=list(b.Zones());"
                "[z.SetIsRuleArea(False) for z in zs];"
                "[z.UnFill() for z in zs];"
                "pcbnew.ZONE_FILLER(b).Fill(zs);"
                "b.Save(sys.argv[1]);"
                "print('ok')")
        r = subprocess.run([kpy, "-c", code, path],
                           capture_output=True, text=True)
        if "ok" not in r.stdout:
            print("  WARNING: refill after stitching failed:", r.stderr[-200:])
    elif dead:
        open(path, "w").write(txt)


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
            net = re.search(r'\(net (?:\d+ )?"([^"]*)"\)', pblk)
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


def _net_names(txt):
    return {int(m.group(1)): m.group(2)
            for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', txt)}


def _norm_net(tok, names):
    """Net token may be a quoted name or a numeric id -> net name."""
    tok = tok.strip('"')
    return names.get(int(tok), tok) if tok.isdigit() else tok


def parse_tracks(txt, names=None):
    """-> [(net_name, w, layer, a, b)]"""
    if names is None:
        names = _net_names(txt)
    segs = []
    for m in re.finditer(
            r'\(segment\s*\n?\s*\(start ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*'
            r'\(end ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*\(width ([\d.]+)\)\s*'
            r'\n?\s*\(layer "([FB]\.Cu)"\)\s*\n?\s*\(net ("[^"]*"|\d+)\)',
            txt):
        x1, y1 = float(m.group(1)), float(m.group(2))
        x2, y2 = float(m.group(3)), float(m.group(4))
        w, l = float(m.group(5)), m.group(6)
        segs.append((_norm_net(m.group(7), names), w, l,
                     (x1, y1), (x2, y2)))
    return segs


def parse_vias(txt, names=None):
    """-> [(x, y, net_name, radius)]. pcbnew Save() injects
    (capping)/(covering) fields between (layers) and (net) — parse the
    whole block, then pull fields in any order."""
    if names is None:
        names = _net_names(txt)
    out = []
    for _, _, body in _sexpr_blocks(txt, '(via'):
        at = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)\)', body)
        sz = re.search(r'\(size ([\d.]+)\)', body)
        nt = re.search(r'\(net ("[^"]*"|\d+)\)', body)
        if at and sz and nt:
            out.append((float(at.group(1)), float(at.group(2)),
                        _norm_net(nt.group(1), names),
                        float(sz.group(1)) / 2))
    return out


def fill_with_geometry(path):
    """Fallback: compute filled_polygon data with build123d."""
    import pour
    txt = open(path).read()
    pads = parse_pads(txt)
    tracks = parse_tracks(txt)
    vias = parse_vias(txt)
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


_SEG_RE = (r'\(segment\s*\n?\s*\(start ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*'
           r'\(end ([\d.\-]+) ([\d.\-]+)\)\s*\n?\s*\(width ([\d.]+)\)\s*'
           r'\n?\s*\(layer "([FB]\.Cu)"\)\s*\n?\s*\(net ("[^"]*"|\d+)\)')
# pcbnew Save() injects (capping)/(covering) fields between (layers)
# and (net) — field order is not stable, so match loosely to (net).
_VIA_RE = (r'\(via\s*\n?\s*\(at ([\d.\-]+) ([\d.\-]+)\)'
           r'(?:(?!\(via)[\s\S])*?\(size ([\d.]+)\)'
           r'(?:(?!\(via)[\s\S])*?\(net ("[^"]*"|\d+)\)')

def _blk_end(txt, i):
    """balanced-sexpr end for the block starting at i"""
    depth, instr = 0, False
    for j in range(i, len(txt)):
        ch = txt[j]
        if ch == '"':
            instr = not instr
        elif not instr:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return j + 1
    return len(txt)


def prune_dead_copper(path, kcli=None):
    """DRC-driven dead-end prune: KiCad's own connectivity decides what
    is dangling — we only ever remove atoms it has already flagged
    (via_dangling / track_dangling), so real copper is never touched.
    Removing a leaf can expose the atom behind it, so loop DRC->remove
    until clean (bounded)."""
    import json as _json
    import os as _os
    import subprocess
    import tempfile
    if kcli is None:
        kcli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if not _os.path.exists(kcli):
        return
    total = 0
    for _pass in range(10):
        with tempfile.NamedTemporaryFile(suffix=".json",
                                         delete=False) as tf:
            rep = tf.name
        subprocess.run([kcli, "pcb", "drc", "--format", "json",
                        "-o", rep, path], capture_output=True)
        try:
            repj = _json.load(open(rep))
        except Exception:
            break
        finally:
            _os.unlink(rep)
        via_pts, seg_pts = [], []
        for v in repj.get("violations", []):
            t = v.get("type")
            if t not in ("via_dangling", "track_dangling"):
                continue
            for it in v.get("items", []):
                p = it.get("pos", {})
                (via_pts if "Via" in it.get("description", "")
                 else seg_pts).append((p.get("x"), p.get("y")))
        if not via_pts and not seg_pts:
            break
        txt = open(path).read()
        kill = set()
        for m in re.finditer(_VIA_RE, txt):
            x, y = float(m.group(1)), float(m.group(2))
            if any(abs(x - px) < 0.4 and abs(y - py) < 0.4
                   for px, py in via_pts):
                kill.add(m.start())
        # a flagged "track" is one segment atom; pos is near its dangling
        # end — remove the containing segment closest to the report point
        for px, py in seg_pts:
            best, bd = None, 1.5
            for m in re.finditer(_SEG_RE, txt):
                a = (float(m.group(1)), float(m.group(2)))
                b = (float(m.group(3)), float(m.group(4)))
                d = min(_seg_dist((px, py), a, b), 9)
                if d < bd:
                    bd, best = d, m.start()
            if best is not None:
                kill.add(best)
        if not kill:
            break
        out, last = [], 0
        for m in re.finditer('|'.join((_SEG_RE, _VIA_RE)), txt):
            out.append(txt[last:m.start()])
            if m.start() in kill:
                total += 1
                last = _blk_end(txt, m.start())
            else:
                out.append(m.group(0))
                last = m.end()
        out.append(txt[last:])
        open(path, "w").write("".join(out))
    if total:
        print(f"pruned {total} DRC-flagged dead atom(s)")


def nudge_pad_grazes(path, margin=0.15, kcli=None):
    """DRC-driven pad-graze repair: for every clearance violation KiCad
    flags between a track and a foreign pad, split the segment at the
    closest point and push the new vertex radially away until the gap
    is met (endpoint grazes translate the shared vertex — all same-net
    atoms at that coordinate move together). Loop DRC->fix until clean;
    only flagged pairs are touched, so nothing else is disturbed."""
    import json as _json
    import math
    import os as _os
    import subprocess
    import tempfile
    import pcbnew
    NM = 1e6
    if kcli is None:
        kcli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if not _os.path.exists(kcli):
        return 0
    total = 0
    for _pass in range(15):
        with tempfile.NamedTemporaryFile(suffix=".json",
                                         delete=False) as tf:
            rep = tf.name
        subprocess.run([kcli, "pcb", "drc", "--format", "json",
                        "-o", rep, path], capture_output=True)
        try:
            repj = _json.load(open(rep))
        except Exception:
            break
        finally:
            _os.unlink(rep)
        pairs = []
        for v in repj.get("violations", []):
            if v.get("type") != "clearance":
                continue
            its = v.get("items", [])
            trk = [i for i in its
                   if i.get("description", "").startswith("Track [")]
            pad = [i for i in its if "pad" in i.get("description", "")]
            if trk and pad:
                pairs.append((trk[0]["pos"], pad[0]["pos"]))
        if not pairs:
            break
        board = pcbnew.LoadBoard(path)
        if board is None:
            break
        pads = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                v = p.GetPosition()
                r = max(p.GetSizeX(), p.GetSizeY()) / (2.0 * NM)
                pads.append((v.x / NM, v.y / NM, r, p.GetNetname()))
        fixed = 0
        for tp, pp in pairs:
            px, py, pr, pn = None, None, None, None
            for cx2, cy2, r2, n2 in pads:
                if abs(cx2 - pp["x"]) < 0.3 and abs(cy2 - pp["y"]) < 0.3:
                    px, py, pr, pn = cx2, cy2, r2, n2
            if px is None:
                continue
            best, bd = None, 1.2
            for t in board.GetTracks():
                if not isinstance(t, pcbnew.PCB_TRACK):
                    continue
                sa, sb = t.GetStart(), t.GetEnd()
                a = (sa.x / NM, sa.y / NM)
                b = (sb.x / NM, sb.y / NM)
                vx, vy = b[0] - a[0], b[1] - a[1]
                L2 = vx * vx + vy * vy
                if L2 == 0:
                    continue            # vias: start==end, not a track
                tt = max(0.0, min(1.0,
                      ((tp["x"] - a[0]) * vx
                       + (tp["y"] - a[1]) * vy) / L2))
                cx, cy = a[0] + vx * tt, a[1] + vy * tt
                d = math.hypot(tp["x"] - cx, tp["y"] - cy)
                if d < bd:
                    bd, best = d, (t, a, b)
            if best is None:
                continue
            t, a, b = best
            w = t.GetWidth() / NM
            net = t.GetNetname()
            need = pr + w / 2 + 0.2 + margin
            # translate the whole offending vertex run: every same-net
            # endpoint within `need` of the pad is pushed radially to
            # need+0.1 — a single-point push just migrates the graze
            # along the arc. Vertices sitting inside an own-net pad
            # (approach ends) are pinned or the link detaches.
            move = {}
            for t2 in board.GetTracks():
                if t2.GetNetname() != net:
                    continue
                for st in (True, False):
                    pt = t2.GetStart() if st else t2.GetEnd()
                    vx2, vy2 = pt.x / NM, pt.y / NM
                    dd = math.hypot(vx2 - px, vy2 - py)
                    if dd >= need or dd < 1e-9:
                        continue
                    pinned = any(
                        n3 == net and math.hypot(vx2 - qx, vy2 - qy)
                        < r3 + 0.2
                        for qx, qy, r3, n3 in pads)
                    if pinned:
                        continue
                    # target must clear ALL foreign pads nearby (a
                    # track threading two pads would otherwise
                    # oscillate) — project outward until satisfied
                    tx, ty = vx2, vy2
                    for _it in range(10):
                        worst = None
                        for qx, qy, r3, n3 in pads:
                            if n3 == net:
                                continue
                            d3 = math.hypot(tx - qx, ty - qy)
                            nd = r3 + w / 2 + 0.2 + margin
                            if d3 < nd and (worst is None
                                            or d3 - nd < worst[0]):
                                worst = (d3 - nd, qx, qy, nd, d3)
                        if worst is None:
                            break
                        _s, qx, qy, nd, d3 = worst
                        if d3 < 1e-9:
                            break
                        tx += (tx - qx) / d3 * (nd - d3 + 0.1)
                        ty += (ty - qy) / d3 * (nd - d3 + 0.1)
                    move[(round(vx2, 3), round(vy2, 3))] = (tx, ty)
            if not move:
                # no vertex inside the keepout: split the segment at
                # its closest point and push that new vertex out
                vx, vy = b[0] - a[0], b[1] - a[1]
                L2 = vx * vx + vy * vy
                tt = (0.0 if L2 == 0 else max(0.0, min(1.0,
                      ((px - a[0]) * vx + (py - a[1]) * vy) / L2)))
                cx, cy = a[0] + vx * tt, a[1] + vy * tt
                d = math.hypot(px - cx, py - cy)
                if d < 1e-9:
                    continue
                ux, uy = (cx - px) / d, (cy - py) / d
                nx, ny = px + ux * (need + 0.1), py + uy * (need + 0.1)
                t.SetEnd(pcbnew.VECTOR2I(int(nx * NM), int(ny * NM)))
                s2 = pcbnew.PCB_TRACK(board)
                s2.SetStart(pcbnew.VECTOR2I(int(nx * NM), int(ny * NM)))
                s2.SetEnd(pcbnew.VECTOR2I(int(b[0] * NM),
                                          int(b[1] * NM)))
                s2.SetWidth(t.GetWidth())
                s2.SetLayer(t.GetLayer())
                s2.SetNetCode(t.GetNetCode())
                board.Add(s2)
                fixed += 1
                continue
            for t2 in board.GetTracks():
                if t2.GetNetname() != net:
                    continue
                for st in (True, False):
                    pt = t2.GetStart() if st else t2.GetEnd()
                    k = (round(pt.x / NM, 3), round(pt.y / NM, 3))
                    if k in move:
                        nx, ny = move[k]
                        (t2.SetStart if st else t2.SetEnd)(
                            pcbnew.VECTOR2I(int(nx * NM), int(ny * NM)))
            fixed += len(move)
        if fixed:
            pcbnew.SaveBoard(path, board)
            total += fixed
        else:
            break
    if total:
        print(f"nudged {total} DRC-flagged pad graze(s)")
    return total


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "soma-carrier.kicad_pcb"
    try:
        nudge_pad_grazes(path)
    except ImportError:
        pass                     # no pcbnew — nothing to nudge
    if fill_with_pcbnew(path):
        prune_dead_copper(path)
        # the fixup refill can pinch off fresh islands — strip again
        d = _strip_islands(path)
        if d:
            print(f"stripped {d} post-fixup island(s)")
        return
    print("pcbnew unavailable — using geometry fallback")
    fill_with_geometry(path)


if __name__ == "__main__":
    main()
