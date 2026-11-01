import sys, pcbnew
p = sys.argv[1]
b = pcbnew.LoadBoard(p)
zs = list(b.Zones())
for z in zs:
    z.SetIsRuleArea(False)
    z.UnFill()
pcbnew.ZONE_FILLER(b).Fill(zs)
pcbnew.SaveBoard(p, b)
print("filled", len(zs), "zones")
