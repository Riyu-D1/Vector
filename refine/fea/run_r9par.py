"""refine/fea/run_r9par.py - parallel R9 driver.

Same case tables + deck/solve/analyze pipeline as run_r9fea.py but the
solve stage runs ccx with a worker pool (deck gen still sequential -
it re-parses the .msh each call and is I/O bound).

Usage: python3 run_r9par.py [deck|solve|analyze|all] [l4,cr,l5,gf] [NWORKERS]
"""
import os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_r9fea as R


def deck_one(part_case):
    part, case = part_case.split("_", 1)
    R.deck(part, case)
    return case


def solve_one(part_case):
    part, case, cl = part_case
    R.solve(part, case, cl)
    return case


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else \
        ("l4", "cr", "l5", "gf")
    nw = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    allc = []
    for part in only:
        allc += [part + "_" + c for c in R.cases(part) if "_" in c or True]
    # cases() yields "l4_face" style already? no - it yields part_"bc"
    # -> rebuild: cases() yields full "part_bc" names already.
    allc = [c for p in only for c in R.cases(p)]
    allc += [c for p in only for c in R.EXTRA[p]]
    conv = [(p, p + ("_scrann" if p != "cr" else "_boltface"), cl)
            for p in only for cl in R.CONVERGE_CL]
    if which in ("deck", "all"):
        dtodo = [(c.split("_", 1)[0], c, R.CL)
                 for c in allc
                 if not os.path.exists(os.path.join(HERE, c + ".inp"))]
        dtodo += [(p, c, cl) for p, c, cl in conv
                  if not os.path.exists(os.path.join(
                      HERE, c + "_c%g.inp" % cl))]
        with ThreadPoolExecutor(max_workers=nw) as ex:
            list(ex.map(lambda t: R.deck(t[0], t[1], t[2]), dtodo))
    if which in ("solve", "all"):
        todo = [(c.split("_", 1)[0], c, R.CL) for c in allc]
        todo += conv
        with ThreadPoolExecutor(max_workers=nw) as ex:
            list(ex.map(solve_one, todo))
    if which == "analyze":
        for c in allc:
            R.analyze(c.split("_", 1)[0], c.split("_", 1)[1])
        for part, case, cl in conv:
            R.analyze(part, case, cl)
    print("done")


if __name__ == "__main__":
    main()
