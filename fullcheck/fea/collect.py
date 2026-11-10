import glob, re
rows = []
for f in sorted(glob.glob("*.run.log")) + sorted(glob.glob("*.runf.log")):
    p = f.rsplit(".run", 1)[0]
    txt = open(f).read()
    m = re.search(r"(\d+) nodes (\d+) tets \| constrained (\d+) tainted (\d+)", txt)
    peaks = {k: (v, s) for k, v, s in
             re.findall(r"(vm|norm|comp|shear)\s+peak\s+([\d.]+) MPa SF\s+([\d.]+)", txt)}
    bind = re.findall(r"BINDING: (\w+) \(SF\s+([\d.]+)\)", txt)
    rows.append((p, m.groups() if m else None, peaks, bind[-1] if bind else None))
print("%-16s %10s %7s %7s %7s %7s %7s | bind" % ("part","nodes","vm","norm","comp","shear","shear61"))
for p, m, pk, bind in rows:
    s61 = re.search(r"vs 6\.1 SF\s+([\d.]+)", open(p + ".run.log").read() if __import__('os').path.exists(p + ".run.log") else "")
    print("%-16s %10s %7s %7s %7s %7s %7s | %s" % (
        p, m[0] if m else "-",
        pk.get("vm", ("-","-"))[1], pk.get("norm", ("-","-"))[1],
        pk.get("comp", ("-","-"))[1], pk.get("shear", ("-","-"))[1],
        s61.group(1) if s61 else "-",
        ("%s %s" % bind) if bind else "RUNNING"))
