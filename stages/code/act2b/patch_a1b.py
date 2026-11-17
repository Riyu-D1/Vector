"""Stage A1b patch (tested by the designer 28 Oct 2026). Run from cad/act2:
   $PY ~/Vector/stages/code/act2b/patch_a1b.py minwall   -> 3 minwall fixes (ap.py + p_act.py)
   $PY ~/Vector/stages/code/act2b/patch_a1b.py motor     -> Tarot base screws from the BOPP STEP (ap.py)
Each mode prints one 'PATCHED ...' line per edit and 'PATCH <mode> OK'. It refuses (AssertionError)
if a line is not found exactly once, so running it twice fails on purpose: do not run a mode twice."""
import sys
mode = sys.argv[1]
AP = [
 ("minwall",
  "BORE_PIN = 47.0                 # [D] = 2*R: ring pins half buried; Z_MID[0] .. Z_RINGPIN[1]\n",
  "BORE_PIN = 47.4                 # [D] A1b: was 47.0 (=2R); +0.2 radius trims the thin pin-web tips (minwall)\n"),
 ("minwall",
  "CSK_Z = 31.5; CSK_ANG = (30.0, 150.0, 270.0)           # [D] 3x radial M3 countersunk into mid_plate\n",
  "CSK_Z = 31.5; CSK_ANG = ()                           # [D] A1b: radial screws removed (minwall); mid_plate keyed by KEY_PINS\n"),
 ("minwall",
  "GRUB_Z = 35.8; GRUB_PILOT = 2.5 # M3x5 ISO 4026 set screw, radial, at angle 90\n",
  "GRUB_Z = 37.95; GRUB_PILOT = 2.5 # A1b: was 35.8; = Z_CAM_SPLIT (minwall). M3x5 ISO 4026 set screw, radial, at angle 90\n"),
 ("minwall",
  "MID_GROOVE = (4.0, 1.5)         # [D] wire groove on back face at WIRE_ANG: width, depth\n",
  "MID_GROOVE = (4.0, 1.5)         # [D] wire groove on back face at WIRE_ANG: width, depth\n"
  "KEY_PINS = (0, 14, 27)          # [D] A1b: ring-pin slots k (angle 360k/NP) that also key the mid_plate\n"
  "KEY_CLR = 0.1                   # [D] A1b: lug d = 2*RP - KEY_CLR (groove is 2*RP + 0.05)\n"),
 ("motor",
  "MOT_PCD = 25.0; MOT_SCREW_ANG = (45.0, 135.0, 225.0, 315.0)  # [U] stator base 4x M3 (Q3)\n",
  "MOT_PCD = 32.0; MOT_SCREW_ANG = (30.0, 150.0, 270.0)  # [S BOPP Tarot 4008 STEP] stator base 3x M3 on PCD 32 (= 27.7 triangle); was [U] 4x PCD25\n"),
]
PA = [
 ("minwall",
  "        h -= zcyl(x, y, 2 * RP + 0.05, ap.Z_RINGPIN[0], ap.Z_RINGPIN[1])\n",
  "        h -= zcyl(x, y, 2 * RP + 0.05, ap.Z_RINGPIN[0], ap.Z_RINGPIN[1])\n"
  "    for k in ap.KEY_PINS:     # A1b: 3 pin grooves continue down through the mid_plate zone = keyways for its lugs\n"
  "        x, y = pol(R, 360.0 * k / NP)\n"
  "        h -= zcyl(x, y, 2 * RP + 0.05, ap.Z_MID[0], ap.Z_RINGPIN[0] + 0.01)\n"),
 ("minwall",
  "    m = zcyl(0, 0, ap.MID_D, *ap.Z_MID)\n",
  "    m = zcyl(0, 0, ap.MID_D, *ap.Z_MID)\n"
  "    N, NP, R, RP, E = cyc.gear()\n"
  "    for k in ap.KEY_PINS:     # A1b: 3 round anti-rotation lugs that slide in the KEY_PINS grooves\n"
  "        x, y = pol(R, 360.0 * k / NP)\n"
  "        m += zcyl(x, y, 2 * RP - ap.KEY_CLR, *ap.Z_MID)\n"),
]
for fn, edits in (("ap.py", AP), ("p_act.py", PA)):
    s = open(fn).read()
    for m, old, new in edits:
        if m != mode:
            continue
        assert s.count(old) == 1, f"{fn}: line not found exactly once: {old.strip()[:60]}"
        s = s.replace(old, new)
        print(f"PATCHED {fn}: {new.splitlines()[0].strip()[:70]}")
    open(fn, "w").write(s)
print(f"PATCH {mode} OK")
