#!/usr/bin/env python3
"""Cross-check emitted pads vs the generator's internal pad map.

The router targets generator-side coordinates; KiCad renders file-side
coordinates. Any sign/convention slip means routes land on empty space.

Usage:
    PLACE_ONLY=1 PAD_DUMP=1 python3 gen_pcb.py > /tmp/paddump.txt
    python3 check_pads.py /tmp/paddump.txt

Must print ONLY the header line ("OK") before routing may proceed.
"""
import math
import re
import sys

PCB = "soma-carrier.placeonly.kicad_pcb"


def _sexpr_blocks(txt, head):
    """Yield balanced s-expr blocks starting with `head` (e.g. '(footprint')."""
    for m in re.finditer(re.escape(head), txt):
        i, depth = m.start(), 0
        instr = False
        j = i
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
        yield txt[i:j + 1]


def emitted_pads(path):
    """ref.num -> (x, y) parsed from the emitted board, KiCad convention."""
    txt = open(path).read()
    out = {}
    for body in _sexpr_blocks(txt, '(footprint'):
        ref = re.search(r'\(property "Reference" "([^"]+)"', body)
        if not ref:
            continue
        ref = ref.group(1)
        at = re.search(r'\(at ([\d.\-]+) ([\d.\-]+)(?: (\-?[\d.]+))?\)', body)
        fx, fy = float(at.group(1)), float(at.group(2))
        rot = float(at.group(3) or 0)
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for pm in re.finditer(
                r'\(pad "([^"]+)" [^\n]*\n'
                r'\s*\(at ([\d.\-]+) ([\d.\-]+)', body):
            num, lx, ly = pm.group(1), float(pm.group(2)), float(pm.group(3))
            # KiCad: +y down, +angle CCW on screen => world = rot(-a) @ local
            out[f"{ref}.{num}"] = (fx + lx * c + ly * s,
                                   fy - lx * s + ly * c)
    return out


def internal_pads(path):
    out = {}
    for line in open(path):
        m = re.match(r'\s+(\S+)\.(\S+) = \(([\d.\-]+),([\d.\-]+)\)', line)
        if m:
            out[f"{m.group(1)}.{m.group(2)}"] = (float(m.group(3)),
                                                 float(m.group(4)))
    return out


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else "/tmp/paddump.txt"
    pcb = sys.argv[2] if len(sys.argv) > 2 else PCB
    em, iv = emitted_pads(pcb), internal_pads(dump)
    bad = 0
    for k in sorted(set(em) | set(iv)):
        if k not in em:
            print(f"  MISSING-IN-FILE {k} internal={iv[k]}")
            bad += 1
        elif k not in iv:
            print(f"  MISSING-IN-GEN  {k} file={em[k]}")
            bad += 1
        else:
            d = math.hypot(em[k][0] - iv[k][0], em[k][1] - iv[k][1])
            if d > 0.01:
                print(f"  DIFF {k}: file={em[k]} internal={iv[k]} d={d:.3f}")
                bad += 1
    # also flag any pad outside the board outline
    for k, (x, y) in em.items():
        if x < 0 or x > 135 or y < 0 or y > 115:
            print(f"  OFF-BOARD {k} at ({x:.2f},{y:.2f})")
            bad += 1
    if bad:
        print(f"{bad} pad mismatches")
        sys.exit(1)
    print(f"OK — {len(em)} file pads all match internal map, all on-board")


if __name__ == "__main__":
    main()
