#!/usr/bin/env python3
"""Verify each new v1.3 net's pads form a single copper island.

Prints, per net: the pad list and whether all pads are mutually
connected (one copper island) using KiCad's own connectivity model.
Run with KiCad's bundled python:
  "$KICAD_PY" pcb16/verify_nets.py pcb15/soma-carrier-v16.kicad_pcb
"""
import sys
import pcbnew

NEW_NETS = ["+12V_RP", "RP_GATE", "+12V_MOT", "RLY_LOW", "RLY_SW",
            "Q3_B", "MOTOR_EN"]

def pad_pos(p):
    xy = p.GetPosition()
    return round(xy[0] / 1e6, 2), round(xy[1] / 1e6, 2)

def main(path):
    b = pcbnew.LoadBoard(path)
    conn = b.GetConnectivity()

    pads_by_net = {n: [] for n in NEW_NETS}
    for f in b.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n in pads_by_net:
                pads_by_net[n].append((f.GetReference(), p))

    ok = True
    for net in NEW_NETS:
        pads = pads_by_net[net]
        names = ["%s.%s@%s" % (r, p.GetNumber(), pad_pos(p)) for r, p in pads]
        print("%-9s pads: %s" % (net, ", ".join(names)))
        if len(pads) < 2:
            print("   SINGLE-PAD net (island trivially one)")
            continue
        ref = pads[0][1]
        try:
            island = conn.GetConnectedItems(ref)
        except TypeError:
            island = conn.GetConnectedItems(ref, True)
        island_ids = {str(i.m_Uuid.AsString()) for i in island} if island else set()
        reach = []
        for r, p in pads[1:]:
            hit = str(p.m_Uuid.AsString()) in island_ids
            reach.append("%s.%s:%s" % (r, p.GetNumber(), "connected" if hit else "ISOLATED"))
            ok &= hit
        print("   island check:", ", ".join(reach))
        if all(":" in x and x.endswith("connected") for x in reach):
            print("   -> one copper island")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "soma-carrier-v16.kicad_pcb"))
