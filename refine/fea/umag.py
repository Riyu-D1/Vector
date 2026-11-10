"""umag.py - deflection metrics from a .frd.

Reports: (a) rigid TCP/ref-node |U| (the payload-point deflection),
(b) max |U| over stressed nodes (VM > 2 MPa) - the real body deflection,
ignoring detached-sliver free DOFs.
Run: python3 umag.py <file.frd>"""
import math, sys
from frd2vtu import read_frd, vonmises
nodes, elems, steps = read_frd(sys.argv[1])
ref = max(nodes)
disp = next(s["data"] for s in steps if s["name"] == "DISP")
stress = next(s["data"] for s in steps if s["name"] == "STRESS")
vm = {n: vonmises(s[:6]) for n, s in stress.items()}
ru = disp.get(ref, [0,0,0])[:3]
print("%s:" % sys.argv[1])
print("  ref-node |U| (TCP rigid-body) = %.3f mm  u=(%.2f,%.2f,%.2f)"
      % (math.sqrt(sum(v*v for v in ru)), *ru))
best, bn = 0.0, None
for n, u in disp.items():
    if n == ref or vm.get(n, 0.0) < 2.0: continue
    m = math.sqrt(sum(v*v for v in u[:3]))
    if m > best: best, bn = m, n
print("  max|U| over VM>2MPa nodes = %.3f mm at %s" % (best, nodes.get(bn)))
