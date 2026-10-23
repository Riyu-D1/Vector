#!/usr/bin/env python3
"""SOMA base-carrier board generator.

Emit a KiCad .kicad_pcb directly — no schematic needed for a passive
carrier board; pads get nets assigned here so DRC is meaningful.

Board: 90 x 70 mm, 2-layer, 100% through-hole, zero ICs.
Contents: ESP32-S3-DevKitC-1 socket rows, 12 V in -> fuse -> servo bus
ports (KK-254), optional Mini-360 buck footprint + 5 V screw terminal,
Schottky on ESP32 5 V feed, 2x I2C ports (SEA encoders), UART port to
wrist node, estop pins, power + status LEDs, GND zone on B.Cu.

Run:  python3 pcb/gen_pcb.py
Out:  pcb/soma-carrier.kicad_pcb  +  pcb/soma-carrier.kicad_pro
"""

import math
import re
import uuid
from pathlib import Path

KICAD_LIB = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
OUT = Path(__file__).resolve().parent
BOARD_W, BOARD_H = 90.0, 70.0

NETS = [
    "GND", "+12V_IN", "+12V", "+5V", "+5V_MCU", "+3V3",
    "BUSA_DATA", "BUSB_DATA", "RXA", "RXB",
    "SDA1", "SCL1", "SDA2", "SCL2",
    "WTX", "WRX", "ESTOP", "LEDGPIO", "LED1_A", "LED2_A",
]
NET_ID = {n: i + 1 for i, n in enumerate(NETS)}


def rot(p, deg):
    a = math.radians(deg)
    return (p[0] * math.cos(a) - p[1] * math.sin(a),
            p[0] * math.sin(a) + p[1] * math.cos(a))


def load_footprint(libdir, name):
    return (KICAD_LIB / libdir / name).read_text()


def pad_info(fp_text):
    """Return {pad_num: (x, y, half_size, layers)} in local footprint coords."""
    out = {}
    pat = re.compile(
        r'\(pad "([^"]+)" (\S+) (\S+)\s*\(\s*at\s+([-\d.]+)\s+([-\d.]+)'
        r'[^)]*\)\s*\(\s*size\s+([\d.]+)\s+([\d.]+)\)')
    for m in pat.finditer(fp_text):
        num, typ, shape, x, y, sx, sy = m.groups()
        layers = ("F.Cu", "B.Cu") if typ == "thru_hole" else ("F.Cu",)
        hx, hy = float(sx) / 2, float(sy) / 2
        # rect/oval pads reach the corner; circles reach the radius
        prr = math.hypot(hx, hy) if shape != "circle" else max(hx, hy)
        out[num] = (float(x), float(y), hx, hy, prr, layers)
    return out


def inject(fp_text, pad_nets):
    """Add net/pintype/uuid to every pad (net 0 "" when unassigned)."""
    result, lines = [], fp_text.split("\n")
    depth, buf, padnum = 0, [], None
    for line in lines:
        if buf:
            buf.append(line)
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                block = "\n".join(buf).rstrip()
                n = pad_nets.get(padnum)
                nid, nname = (NET_ID[n], n) if n else (0, "")
                block = block[:-1] + f' (net {nid} "{nname}")'
                block += ' (pinfunction "") (pintype "passive")'
                block += f' (uuid "{uuid.uuid4()}"))'
                result.append(block)
                buf, padnum = [], None
        else:
            m = re.search(r'\(pad "([^"]+)"', line)
            if m:
                buf, padnum = [line], m.group(1)
                depth = line.count("(") - line.count(")")
                if depth <= 0:
                    block = buf[0].rstrip()
                    n = pad_nets.get(padnum)
                    nid, nname = (NET_ID[n], n) if n else (0, "")
                    block = block[:-1] + f' (net {nid} "{nname}")'
                    block += ' (pinfunction "") (pintype "passive")'
                    block += f' (uuid "{uuid.uuid4()}"))'
                    result.append(block)
                    buf, padnum = [], None
            else:
                result.append(line)
    return "\n".join(result)


class Placed:
    def __init__(self, ref, value, libdir, fname, x, y, rot_deg=0.0, pad_nets=None):
        self.ref, self.x, self.y, self.r = ref, x, y, rot_deg
        src = load_footprint(libdir, fname)
        lib_name = fname[:-len(".kicad_mod")]
        lib = libdir[:-len(".pretty")]
        src = re.sub(r'\(footprint "[^"]*"',
                     f'(footprint "{lib}:{lib_name}"', src, count=1)
        # drop library-file-only attrs
        src = re.sub(r'\n\t\(version [^)]*\)', '', src)
        src = re.sub(r'\n\t\(generator [^)]*\)', '', src)
        # placement + identity after (layer "F.Cu")
        src = src.replace(
            '(layer "F.Cu")',
            f'(layer "F.Cu")\n\t\t(uuid "{uuid.uuid4()}")'
            f'\n\t\t(at {x:.3f} {y:.3f} {rot_deg:g})', 1)
        src = re.sub(r'\(property "Reference" "[^"]*"',
                     f'(property "Reference" "{ref}"', src, count=1)
        src = re.sub(r'\(property "Value" "[^"]*"',
                     f'(property "Value" "{value}"', src, count=1)
        if pad_nets:
            src = inject(src, pad_nets)
        self.src = src
        # KiCad y-axis points down: file rotation a == math rotation -a
        self.pads, self.padinfo = {}, {}
        for n, (px, py, hx, hy, prr, layers) in pad_info(
                load_footprint(libdir, fname)).items():
            rx, ry = rot((px, py), -rot_deg)
            self.pads[n] = (x + rx, y + ry)
            self.padinfo[n] = (x + rx, y + ry, hx, hy, prr, layers)

    def pad(self, num):
        return self.pads[num]


C = {}


def place(ref, value, libdir, fname, x, y, rot_deg=0, pad_nets=None):
    C[ref] = Placed(ref, value, libdir, fname, x, y, rot_deg, pad_nets or {})


# ---------------------------------------------------------------------------
# Component placement  (x, y in mm; board 90x70)
# ---------------------------------------------------------------------------

# Power in — left edge, bottom half
place("J1", "12V_IN", "TerminalBlock_Phoenix.pretty",
      "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod",
      8.0, 48.0, rot_deg=90, pad_nets={"1": "+12V_IN", "2": "GND"})
place("J2", "5V_IN", "TerminalBlock_Phoenix.pretty",
      "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod",
      8.0, 34.0, rot_deg=90, pad_nets={"1": "+5V", "2": "GND"})
place("F1", "6A", "Fuse.pretty", "Fuse_Blade_Mini_directSolder.kicad_mod",
      17.0, 50.0, rot_deg=90, pad_nets={"1": "+12V_IN", "2": "+12V"})
place("C1", "1000uF", "Capacitor_THT.pretty", "CP_Radial_D10.0mm_P5.00mm.kicad_mod",
      40.0, 19.0, pad_nets={"1": "+12V", "2": "GND"})

# Optional Mini-360 buck module — 4 edge pads, top-left
place("J3", "MINI360", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x04_P2.54mm_Vertical.kicad_mod", 10.0, 12.0,
      pad_nets={"1": "+12V", "2": "GND", "3": "+5V", "4": "GND"})

# Servo bus ports along top edge (pin1=GND pin2=+12V pin3=DATA)
place("J4", "BUS_A1", "Connector_Molex.pretty",
      "Molex_KK-254_AE-6410-03A_1x03_P2.54mm_Vertical.kicad_mod",
      30.0, 9.0, pad_nets={"1": "GND", "2": "+12V", "3": "BUSA_DATA"})
place("J5", "BUS_A2", "Connector_Molex.pretty",
      "Molex_KK-254_AE-6410-03A_1x03_P2.54mm_Vertical.kicad_mod",
      45.0, 9.0, pad_nets={"1": "GND", "2": "+12V", "3": "BUSA_DATA"})
place("J6", "BUS_B", "Connector_Molex.pretty",
      "Molex_KK-254_AE-6410-03A_1x03_P2.54mm_Vertical.kicad_mod",
      70.0, 9.0, pad_nets={"1": "GND", "2": "+12V", "3": "BUSB_DATA"})

# DevKitC-1 socket: two 1x19 rows, 22.86 mm apart, USB ports -> left edge
# ROW_BOT (y=51.16) = J1  |  ROW_TOP (y=28.44) = J2   (verify on assembly!)
j1_nets = {}
j1_map = {1: "+3V3", 3: "ESTOP", 7: "U2TX", 8: "U2RX", 9: "U1TX", 10: "U1RX",
          11: "SDA1", 14: "SCL1", 15: "SCL2", 16: "SDA2"}
net_name = {"U2TX": "BUSB_DATA", "U2RX": "RXB", "U1TX": "BUSA_DATA",
            "U1RX": "RXA"}
for pin, sig in j1_map.items():
    j1_nets[str(pin)] = net_name.get(sig, sig)
place("U1A", "DevKitC-J1", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x19_P2.54mm_Vertical.kicad_mod",
      22.14, 51.16, rot_deg=90, pad_nets=j1_nets)
j2_map = {1: "+5V_MCU", 2: "GND", 3: "WTX", 4: "WRX", 18: "LEDGPIO"}
place("U1B", "DevKitC-J2", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x19_P2.54mm_Vertical.kicad_mod",
      22.14, 28.30, rot_deg=90, pad_nets={str(k): v for k, v in j2_map.items()})

# Bus coupling resistors: RX <- DATA through 1k
place("R1", "1k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      44.0, 44.0, pad_nets={"1": "BUSA_DATA", "2": "RXA"})
place("R2", "1k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      32.0, 44.0, pad_nets={"1": "BUSB_DATA", "2": "RXB"})

# Schottky on the ESP32 5V feed
place("D1", "1N5820", "Diode_THT.pretty",
      "D_DO-201_P12.70mm_Horizontal.kicad_mod",
      16.0, 35.0, rot_deg=90, pad_nets={"1": "+5V_MCU", "2": "+5V"})

# 5V bulk + decoupling
place("C3", "220uF", "Capacitor_THT.pretty", "CP_Radial_D8.0mm_P3.50mm.kicad_mod",
      78.0, 22.0, pad_nets={"1": "+5V", "2": "GND"})
place("C2", "100nF", "Capacitor_THT.pretty", "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod",
      56.0, 14.0, pad_nets={"1": "+12V", "2": "GND"})
place("C4", "100nF", "Capacitor_THT.pretty", "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod",
      82.0, 30.0, pad_nets={"1": "+5V", "2": "GND"})

# I/O ports along bottom edge — horizontal pin rows, y-staggered so the
# pad walls never line up into one long barrier (no sealed pockets).
# Pin headers extend -y from origin, so rot=+90 puts pin1 leftmost.
place("J7", "ENC_J2", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x04_P2.54mm_Vertical.kicad_mod", 18.0, 60.0, rot_deg=90,
      pad_nets={"1": "+3V3", "2": "GND", "3": "SDA1", "4": "SCL1"})
place("J8", "ENC_J3", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x04_P2.54mm_Vertical.kicad_mod", 30.0, 64.0, rot_deg=90,
      pad_nets={"1": "+3V3", "2": "GND", "3": "SDA2", "4": "SCL2"})
place("J9", "ESTOP", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x02_P2.54mm_Vertical.kicad_mod", 44.0, 60.0, rot_deg=90,
      pad_nets={"1": "ESTOP", "2": "GND"})
place("J10", "WRIST", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x04_P2.54mm_Vertical.kicad_mod", 58.0, 64.0, rot_deg=90,
      pad_nets={"1": "+5V", "2": "GND", "3": "WTX", "4": "WRX"})

# LEDs
place("D2", "PWR", "LED_THT.pretty", "LED_D3.0mm.kicad_mod",
      76.0, 62.0, pad_nets={"1": "GND", "2": "LED1_A"})
place("R3", "330", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      62.0, 57.0, pad_nets={"1": "+5V", "2": "LED1_A"})
place("D3", "STAT", "LED_THT.pretty", "LED_D3.0mm.kicad_mod",
      76.0, 56.0, pad_nets={"1": "GND", "2": "LED2_A"})
place("R4", "330", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      60.0, 46.0, pad_nets={"1": "LEDGPIO", "2": "LED2_A"})

# Test pads + mounting holes
place("TP1", "GND", "TestPoint.pretty", "TestPoint_THTPad_D1.5mm_Drill0.7mm.kicad_mod",
      74.0, 44.0, pad_nets={"1": "GND"})
place("TP2", "+12V", "TestPoint.pretty", "TestPoint_THTPad_D1.5mm_Drill0.7mm.kicad_mod",
      74.0, 40.0, pad_nets={"1": "+12V"})
for i, (hx, hy) in enumerate([(4, 4), (86, 4), (4, 66), (86, 66)]):
    place(f"H{i+1}", "M3", "MountingHole.pretty",
          "MountingHole_3.2mm_M3_DIN965.kicad_mod", hx, hy)


# ---------------------------------------------------------------------------
# Routing table — net: (width, [waypoints]) — segments on F.Cu.
# (x,y) may be absolute or a (ref, pad) reference resolved below.
# ---------------------------------------------------------------------------

def P(ref, pad):
    return ("PAD", ref, pad)


SEG = []  # (net, width, layer, [pts])
VIA = []  # (x, y, net)


def path(net, width, pts, layer="F.Cu"):
    pts = [C[p[1]].pad(p[2])
           if isinstance(p, tuple) and len(p) == 3 and p[0] == "PAD"
           else p for p in pts]
    SEG.append((net, width, layer, pts))


def via(x, y, net):
    VIA.append((x, y, net))


# ---------------------------------------------------------------------------
# Tiny A* grid router — through-hole pads conduct both layers, so each net
# is routed entirely on one layer and never needs vias.
# ---------------------------------------------------------------------------
import heapq

GRID = 0.127           # 5 mil routing grid
EDGE_KEEP = 1.0        # keep copper this far inside the outline
CLR = 0.2              # copper-to-copper clearance target, mm
PAD_R = 0.85           # THT pad half-size (1.7mm square pads)
obstacles = {"F.Cu": {}, "B.Cu": {}}  # cell -> net that owns the track there
PADS = []              # all pads + mounting holes: (x, y)


def cell(p):
    return (round(p[0] / GRID), round(p[1] / GRID))


def disc_cells(x, y, r):
    out = set()
    for gx in range(int((x - r) / GRID) - 1, int((x + r) / GRID) + 2):
        for gy in range(int((y - r) / GRID) - 1, int((y + r) / GRID) + 2):
            cx, cy = gx * GRID, gy * GRID
            if (cx - x) ** 2 + (cy - y) ** 2 <= r * r:
                out.add((gx, gy))
    return out


def block_disc(layer, x, y, r, net):
    obstacles[layer].update({c: net for c in disc_cells(x, y, r)})


def collect_pads():
    """Gather every pad + mounting hole: (x, y, keepout_radius, layers)."""
    for ref, c in C.items():
        for num, (px, py, hx, hy, prr, layers) in c.padinfo.items():
            PADS.append((px, py, prr, layers))
    for ref in ("H1", "H2", "H3", "H4"):
        # M3 hole: 3.2 drill + margin; obstacle on both layers
        PADS.append((C[ref].x, C[ref].y, 1.9, ("F.Cu", "B.Cu")))


def mark_track(net, width, layer, pts):
    # keep future track centers clear of this track's edge;
    # 0.75 = half-width of the widest track in ROUTES (+12V @1.5mm)
    r = width / 2 + CLR + 0.85
    for a, b in zip(pts, pts[1:]):
        steps = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / GRID) + 1)
        for t in range(steps + 1):
            x, y = a[0] + (b[0] - a[0]) * t / steps, a[1] + (b[1] - a[1]) * t / steps
            block_disc(layer, x, y, r, net)


LNAME = ("F.Cu", "B.Cu")
VIA_COST = 8.0        # mm-equivalent cost; discourages gratuitous vias
VIA_R = 1.1           # via keep-out radius vs pads/marks


def astar(net, starts, goals, w=0.5, slack=18):
    """3D A* over (grid cell, layer); returns [(x, y, layer_idx), ...].
    starts/goals: terminal dicts {x, y, r, layers} — r is the pad's own
    half-size so the search can end anywhere on its copper."""
    # per-layer pad obstacles with ownership: cell -> {pad idx}
    padown = [dict(), dict()]
    for idx, (px, py, prr, layers) in enumerate(PADS):
        for li, ln in enumerate(LNAME):
            if ln in layers:
                # +0.12 headroom: grid quantization + KiCad's exact geometry.
                # Kept small — on 2.54mm pitch, keepouts >~1.27+w/2 merge
                # across a neighbour's pad and seal its copper entirely.
                for c in disc_cells(px, py, prr + CLR + w / 2 + 0.12):
                    padown[li].setdefault(c, set()).add(idx)
    obs_l = (obstacles["F.Cu"], obstacles["B.Cu"])

    # identify which pads are this route's terminals
    tidx = set()
    for t in starts + goals:
        for idx, (px, py, prr, layers) in enumerate(PADS):
            if (px - t["x"]) ** 2 + (py - t["y"]) ** 2 < 0.16:
                tidx.add(idx)

    def terminal_cells(t):
        out = []
        for c in disc_cells(t["x"], t["y"], max(t["r"], GRID)):
            for li, ln in enumerate(LNAME):
                if ln in t["layers"]:
                    out.append((c, li))
        return out

    # cells on a terminal's own copper: always enterable — a track may land
    # on its pad even where a neighbour's keepout overlaps that copper.
    # (On 2.54mm pitch, a wide route's keepout for pad N swallows N±1's pads.)
    termcu = set()
    for t in starts + goals:
        if t["r"] > 0:   # real pads only; waypoints don't bypass keepouts
            for c in disc_cells(t["x"], t["y"], t["r"]):
                for li in range(len(LNAME)):
                    termcu.add((c, li))

    def blocked(c, li):
        if (c, li) in termcu:
            return False
        owners = padown[li].get(c)
        return owners is not None and bool(owners - tidx)

    # precomputed no-via region: pad keepouts on both layers (one set —
    # vias span both). Built once per route, not per search state.
    viabad = set()
    for px, py, prr, _ in PADS:
        viabad |= disc_cells(px, py, prr + 1.25)

    def via_ok(cc):
        if cc in viabad:
            return False
        for o in obs_l:            # ~0.38mm radius vs other-net mark cells
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx * dx + dy * dy > 9:
                        continue
                    owner = o.get((cc[0] + dx, cc[1] + dy))
                    if owner is not None and owner != net:
                        return False
        return True

    start_cells = [s for t in starts for s in terminal_cells(t)]
    goal = {g for t in goals for g in terminal_cells(t)}
    W, H = int(BOARD_W / GRID) - 1, int(BOARD_H / GRID) - 1
    # search window: terminal bbox + slack (keeps local routes cheap)
    bx0 = int((min(t["x"] for t in starts + goals) - slack) / GRID)
    bx1 = int((max(t["x"] for t in starts + goals) + slack) / GRID)
    by0 = int((min(t["y"] for t in starts + goals) - slack) / GRID)
    by1 = int((max(t["y"] for t in starts + goals) + slack) / GRID)
    inside = lambda c: (max(10, bx0) <= c[0] <= min(W - 10, bx1)
                        and max(10, by0) <= c[1] <= min(H - 10, by1))
    start_cells = [s for s in start_cells if inside(s[0])]
    openq = [(0, s) for s in start_cells]
    heapq.heapify(openq)
    came, cost = {}, {s: 0 for s in start_cells}
    dirs = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
            (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    found = None
    while openq:
        f, cur = heapq.heappop(openq)
        if cur in goal:
            found = cur
            break
        c2, li = cur
        for dx, dy, d in dirs:
            n2 = (c2[0] + dx, c2[1] + dy)
            if not inside(n2) or blocked(n2, li) \
                    or obs_l[li].get(n2, net) != net:
                continue
            if dx and dy:                      # no corner-cutting
                if blocked((c2[0] + dx, c2[1]), li) \
                        or blocked((c2[0], c2[1] + dy), li):
                    continue
                m1 = obs_l[li].get((c2[0] + dx, c2[1]))
                m2 = obs_l[li].get((c2[0], c2[1] + dy))
                if (m1 is not None and m1 != net) \
                        or (m2 is not None and m2 != net):
                    continue
            nxt = (n2, li)
            nc = cost[cur] + d
            if nxt not in cost or nc < cost[nxt]:
                cost[nxt] = nc
                h = min(abs(n2[0] - g[0][0]) + abs(n2[1] - g[0][1])
                        for g in goal)
                heapq.heappush(openq, (nc + h * 1.4, nxt))
                came[nxt] = cur
        nxt = (c2, 1 - li)                      # layer hop = via
        if not blocked(c2, 1 - li) and via_ok(c2):
            nc = cost[cur] + VIA_COST
            if nxt not in cost or nc < cost[nxt]:
                cost[nxt] = nc
                h = min(abs(c2[0] - g[0][0]) + abs(c2[1] - g[0][1])
                        for g in goal)
                heapq.heappush(openq, (nc + h * 1.4, nxt))
                came[nxt] = cur
    if found is None:
        gx = [c[0] for c, _ in cost]; gy = [c[1] for c, _ in cost]
        print(f"  [{net}] explored {len(cost)} states, "
              f"x {min(gx)*GRID:.1f}..{max(gx)*GRID:.1f} "
              f"y {min(gy)*GRID:.1f}..{max(gy)*GRID:.1f} | "
              f"starts {[(t['x'], t['y']) for t in starts]} "
              f"goals {[(t['x'], t['y']) for t in goals]}")
        raise RuntimeError(f"no route for {net}")
    path = [found]
    while path[-1] in came:
        path.append(came[path[-1]])
    path.reverse()
    pts = [(gx * GRID, gy * GRID, li) for (gx, gy), li in path]
    # simplify collinear runs within a single layer
    simp = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, cpt = simp[-1], pts[i], pts[i + 1]
        if a[2] != b[2] or b[2] != cpt[2]:
            simp.append(b)
            continue
        cross = ((b[0] - a[0]) * (cpt[1] - b[1])
                 - (b[1] - a[1]) * (cpt[0] - b[0]))
        if abs(cross) > 0.05:
            simp.append(b)
    simp.append(pts[-1])
    return simp


def term(s):
    """Route endpoint -> terminal dict for astar."""
    if isinstance(s[0], str):
        x, y, hx, hy, prr, layers = C[s[0]].padinfo[s[1]]
        # goal disc = pad's inscribed circle: every cell in it is on copper
        return {"x": x, "y": y, "r": min(hx, hy), "layers": layers}
    return {"x": s[0], "y": s[1], "r": 0.0, "layers": ("F.Cu", "B.Cu")}


def route(net, stops, layer="F.Cu", w=0.5):
    """stops: (ref, pad) tuples or (x, y) waypoints, connected serially.
    The router picks layers itself; `layer` is ignored (kept for the table)."""
    done = [term(stops[0])]
    for s in stops[1:]:
        t = term(s)
        print(f"    {net}: -> ({t['x']:.1f},{t['y']:.1f})")
        try:
            pts3 = astar(net, done, [t], w)
        except RuntimeError:
            pts3 = astar(net, done, [t], w, slack=99)   # full board retry
        # split into contiguous per-layer runs; emit a via at each hop
        run = [pts3[0][:2]]
        li = pts3[0][2]
        for p in pts3[1:]:
            if p[2] != li:
                if len(run) > 1:
                    SEG.append((net, w, LNAME[li], run))
                    mark_track(net, w, LNAME[li], run)
                vx, vy = p[0], p[1]
                VIA.append((vx, vy, net))
                for l in LNAME:
                    block_disc(l, vx, vy, 0.75 + CLR + 0.85, net)
                run, li = [p[:2]], p[2]
            else:
                run.append(p[:2])
        if len(run) > 1:
            SEG.append((net, w, LNAME[li], run))
            mark_track(net, w, LNAME[li], run)
        done.append(t)


# ---------------------------------------------------------------------------
# Route every net through the grid router.
# F.Cu: power rails + servo-bus nets.  B.Cu: the small signal wires
# (through-hole pads conduct both sides, so no vias are needed).
# ---------------------------------------------------------------------------
collect_pads()

ROUTES = [
    # net, stops, layer, width — bottom-port signals dive under the row and
    # rise into their pads; retry pass handles whatever still pockets.
    ("SDA2", [("U1A", "16"), ("J8", "3")], "B.Cu", 0.4),
    ("SCL2", [("U1A", "15"), ("J8", "4")], "B.Cu", 0.4),
    ("ESTOP", [("U1A", "3"), ("J9", "1")], "B.Cu", 0.4),
    ("LED1_A", [("R3", "2"), ("D2", "2")], "B.Cu", 0.4),
    ("LED2_A", [("R4", "2"), ("D3", "2")], "B.Cu", 0.4),
    ("LEDGPIO", [("U1B", "18"), ("R4", "1")], "B.Cu", 0.4),
    ("SDA1", [("U1A", "11"), ("J7", "3")], "F.Cu", 0.4),
    ("SCL1", [("U1A", "14"), ("J7", "4")], "F.Cu", 0.4),
    ("+3V3", [("U1A", "1"), ("J7", "1"), ("J8", "1")], "F.Cu", 0.5),
    ("WTX", [("U1B", "3"), ("J10", "3")], "F.Cu", 0.4),
    ("WRX", [("U1B", "4"), ("J10", "4")], "F.Cu", 0.4),
    ("BUSA_DATA", [("J4", "3"), ("J5", "3"), ("U1A", "9"), ("R1", "1")],
     "F.Cu", 0.6),
    ("RXA", [("R1", "2"), ("U1A", "10")], "F.Cu", 0.5),
    ("BUSB_DATA", [("J6", "3"), ("U1A", "7"), ("R2", "1")], "F.Cu", 0.6),
    ("RXB", [("R2", "2"), ("U1A", "8")], "F.Cu", 0.5),
    ("+12V_IN", [("J1", "1"), ("F1", "1")], "F.Cu", 1.2),
    ("+12V", [("F1", "2"), ("J3", "1"), ("J4", "2"), ("J5", "2"),
              ("C1", "1"), ("C2", "1"), ("J6", "2"), ("TP2", "1")],
     "F.Cu", 1.5),
    ("+5V", [("J2", "1"), ("J3", "3"), ("D1", "2"), ("C3", "1"),
             ("C4", "1"), (72, 56), ("R3", "1"), ("J10", "1")],
     "F.Cu", 1.2),
    ("+5V_MCU", [("D1", "1"), ("U1B", "1")], "F.Cu", 0.8),
    # GND backbone tree — the pour alone leaves islands where connector
    # rows fence off copper; the tree guarantees connectivity.
    ("GND", [("J3", "2"), ("J3", "4"), ("U1B", "2"), ("J4", "1"),
             ("J5", "1"), ("C1", "2"), ("C2", "2"), ("J6", "1"),
             ("C3", "2"), ("C4", "2"), ("TP1", "1"), ("D3", "1"),
             ("D2", "1"), ("J10", "2"), ("J9", "2"), ("J8", "2"),
             ("J7", "2"), ("J1", "2"), ("J2", "2")], "B.Cu", 0.9),
]

def route_span(stops):
    pts_of = lambda s: C[s[0]].pad(s[1]) if isinstance(s[0], str) else s
    pts = [pts_of(s) for s in stops]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return max(xs) - min(xs) + max(ys) - min(ys)


# GND backbone first (its walls are bridgeable by vias); then shortest-span
# nets first: short hops can't dodge walls, long rails can
failed = []
# Fat power nets first: they can't squeeze gaps, so they run while the
# board is empty. GND is the backbone tree; then the 12V/5V rails.
PWR = {"+12V": 0, "+12V_IN": 1, "+5V": 2, "+5V_MCU": 3, "GND": 4}
order = sorted(ROUTES, key=lambda r: (PWR.get(r[0], 10),
                                      route_span(r[1])))
for net, stops, layer, w in order:
    try:
        route(net, stops, layer, w)
    except RuntimeError:
        failed.append(net)
        print(f"  deferred {net}")
for net, stops, layer, w in order:          # second pass, later walls exist
    if net not in failed:
        continue
    try:
        route(net, stops, layer, w)
        failed.remove(net)
        print(f"  routed {net} on retry")
    except RuntimeError:
        pass
if failed:
    raise RuntimeError(f"unrouted nets: {failed}")


# ---------------------------------------------------------------------------
# Emit the .kicad_pcb
# ---------------------------------------------------------------------------

TEMPLATE = (KICAD_LIB.parent / "template" / "RaspberryPi-HAT"
            / "RaspberryPi-HAT.kicad_pcb")


def template_header():
    """Everything from a real board file up to its net list."""
    txt = TEMPLATE.read_text()
    end = txt.index("\t(net ")
    return txt[:end]


def seg_sexp(net, width, layer, pts):
    out = []
    for a, b in zip(pts, pts[1:]):
        out.append(
            f'\t(segment\n\t\t(start {a[0]:.3f} {a[1]:.3f})'
            f'\n\t\t(end {b[0]:.3f} {b[1]:.3f})\n\t\t(width {width})'
            f'\n\t\t(layer "{layer}")\n\t\t(net {NET_ID[net]})'
            f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    return out


def label(text, x, y, size=1.3, layer="F.SilkS", rot_deg=0):
    justify = "\n\t\t\t\t(justify mirror)" if layer.startswith("B.") else ""
    return (f'\t(gr_text "{text}"\n\t\t(at {x} {y} {rot_deg})'
            f'\n\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")'
            f'\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})'
            f'\n\t\t\t\t(thickness {size*0.18:.3f})\n\t\t\t){justify}'
            '\n\t\t)\n\t)')


def build_pcb():
    parts = [template_header()]
    parts += [f'\t(net {i} "{n}")\n' for i, n in enumerate([""] + NETS)]

    for c in C.values():
        parts.append(c.src.rstrip() + "\n")

    # edge cuts — one rect on Edge.Cuts
    parts.append(
        f'\t(gr_rect\n\t\t(start 0 0)\n\t\t(end {BOARD_W} {BOARD_H})'
        '\n\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type solid)\n\t\t)'
        '\n\t\t(fill no)\n\t\t(layer "Edge.Cuts")'
        f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

    for l in [
        label("SOMA BASE CARRIER v1", 45, 4, 1.8),
        label("12V IN", 8, 48.5), label("5V IN", 8, 66.5),
        label("BUS-A x2 (STS3215)", 37.5, 5.5, 1.1),
        label("BUS-B (HTD45H)", 70, 5.5, 1.1),
        label("G", 27.46, 12, 0.9), label("V", 30, 12, 0.9),
        label("D", 32.54, 12, 0.9),
        label("ENC-J2 SDA1/SCL1", 18, 67.5, 1.0),
        label("ENC-J3 SDA2/SCL2", 30, 67.5, 1.0),
        label("ESTOP", 44, 67.5, 1.0),
        label("WRIST 5V G TX RX", 58, 67.5, 1.0),
        label("MINI-360 (opt)", 14, 8.0, 1.0),
        label("ESP32-S3-DevKitC-1  USB->LEFT", 45, 39.5, 1.3),
        label("ROW-BOT=J1  ROW-TOP=J2", 45, 40.8, 1.0),
        label("PWR", 76, 59, 1.0), label("STAT", 76, 53, 1.0),
        label("F1 6A", 19, 48, 1.0),
        label("github.com/Riyu-D1/Vector", 45, 69, 0.8, "B.SilkS"),
    ]:
        parts.append(l + "\n")

    for net, w, layer, pts in SEG:
        parts.extend(s + "\n" for s in seg_sexp(net, w, layer, pts))
    for x, y, net in VIA:
        parts.append(
            f'\t(via\n\t\t(at {x:.3f} {y:.3f})\n\t\t(size 1.5)\n\t\t(drill 0.8)'
            f'\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net {NET_ID[net]})'
            f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

    # GND zone on B.Cu — structure copied from KiCad template
    parts.append(
        f'\t(zone\n\t\t(net {NET_ID["GND"]})\n\t\t(net_name "GND")'
        '\n\t\t(layer "B.Cu")'
        f'\n\t\t(uuid "{uuid.uuid4()}")\n\t\t(name "GND")'
        '\n\t\t(hatch full 0.508)\n\t\t(connect_pads\n\t\t\t(clearance 0.3)\n\t\t)'
        '\n\t\t(min_thickness 0.254)\n\t\t(filled_areas_thickness no)'
        '\n\t\t(keepout\n\t\t\t(tracks allowed)\n\t\t\t(vias allowed)'
        '\n\t\t\t(pads allowed)\n\t\t\t(copperpour allowed)'
        '\n\t\t\t(footprints allowed)\n\t\t)'
        '\n\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)'
        '\n\t\t(fill\n\t\t\t(thermal_gap 0.4)\n\t\t\t(thermal_bridge_width 0.4)'
        '\n\t\t\t(smoothing chamfer)\n\t\t\t(radius 0.25)'
        '\n\t\t\t(island_removal_mode 1)\n\t\t\t(island_area_min 10.0)\n\t\t)'
        f'\n\t\t(polygon\n\t\t\t(pts\n\t\t\t\t(xy 0.5 0.5)'
        f'\n\t\t\t\t(xy {BOARD_W-0.5} 0.5)\n\t\t\t\t(xy {BOARD_W-0.5} {BOARD_H-0.5})'
        f'\n\t\t\t\t(xy 0.5 {BOARD_H-0.5})\n\t\t\t)\n\t\t)\n\t)\n')

    parts.append('\t(embedded_fonts no)\n)\n')
    return "".join(parts)


def build_pro():
    return """{
  "board": {"design_settings": {}, "ipc2581": {}, "layers": []},
  "boards": [],
  "cvpcb": {"equivalence_files": []},
  "libraries": {"loaded_footprint_libraries": [], "loaded_symbol_libraries": []},
  "meta": {"filename": "soma-carrier.kicad_pro", "version": 1},
  "net_settings": {"classes": [], "class_patterns": [], "meta": {"version": 3}},
  "project": {"files": []},
  "schematic": {"annotate_start_num": 0, "drawing": {}, "legacy_lib_dir": "",
                "legacy_lib_list": [], "meta": {"version": 1},
                "net_format_name": "", "page_layout_descr_file": "",
                "plot_directory": "", "spice_adjust_passive_values": false,
                "spice_command_net": "spice", "spice_external_command": "",
                "spice_model_current_sheet_as_root": false,
                "spice_save_all_currents": false,
                "spice_save_all_voltages": false, "subpart_first_id": 65,
                "subpart_id_separator": 0},
  "sheets": [],
  "text_variables": {}
}
"""


if __name__ == "__main__":
    (OUT / "soma-carrier.kicad_pcb").write_text(build_pcb())
    (OUT / "soma-carrier.kicad_pro").write_text(build_pro())
    print(f"wrote {OUT/'soma-carrier.kicad_pcb'}")
    for ref, c in C.items():
        print(f"  {ref}: {len(c.pads)} pads at {c.x},{c.y}")
