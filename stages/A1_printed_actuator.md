# Stage A1 — ONE printed 40:1 cycloidal actuator module (shoulder J2 + elbow J3)
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply, with these THREE overrides for this stage only:
> (a) branch is `arm-actuator2` (NOT arm-knuckle), worktree `~/Vector-wt/act2`; never commit, push or tag on `arm-knuckle`;
> (b) every number lives in `cad/act2/ap.py` (not kp.py); rule 0.6 applies to ap.py;
> (c) status file is `docs/STATUS-act2.md` (not STATUS-knuckle.md).
> Work dir: `~/Vector-wt/act2`. Type first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = output must match (numbers ±0.05 unless stated). If not: re-run once, then do the "If not" line.

**Goal:** parametric build123d code in `cad/act2/` for ONE printed cycloidal actuator (same module at J2 and J3), STEP + STL per part, gates passing, 6 renders, BOM, committed and pushed.
**Branch:** `arm-actuator2` (made from `arm-knuckle`). **Tag to create:** `act-1-done`. **Inputs:** `cad/knuckle/gate.py`, `cad/knuckle/frames.py`, `cad/knuckle/render_blend.py` (tested, use as-is, do not edit); tested maths `~/Vector/stages/code/act2/ap.py` + `cyc.py` (copy verbatim); studies `~/Vector/stages/ref/printed-actuator-study.md`, `~/Vector/stages/ref/rebot-adapt2.md` (read only).
**Why:** Riyansh wants a slim reBot-style arm. Bought GIM motors are too expensive, so we print a cycloid reducer around a cheap Tarot 4008 outrunner, Ø57 to fit reBot joint ends (R28.5, 6×M3 PCD50 back, M3 PCD27 + Ø4 PCD24 output).

## 0. Design summary (all values are in ap.py; [S] sourced, [D] design, [U] unverified)
- Envelope Ø57.0 × 55.0 long [D]. Module frame: origin = BACK face centre, +Z to output, output face Z 55.0.
- Motor: Tarot TL2955 4008 330KV, Ø44.5 × 22, 85 g, 4 mm shaft [S study]; Kt = 8.27/330 = 0.0251 N·m/A [S study].
  Mounted **stator base forward** on `mid_plate`, bell toward the back wall; magnet glued on the bell top centre; AS5600 in the back wall.
- Torque at output: T = Kt × I × ratio × η = 0.0251 × I × 40 × 0.75 = **0.75 N·m per A** [S study]. 5 A (J2) → 3.76 N·m vs 2.3 needed; 3 A (J3) → 2.26 vs 1.8.
  Speed at 12 V: 330 × 12 / 40 = 99 rpm ideal [S study].
- **ESC decision:** B-G431B-ESC1 (30×41, diagonal 50.8 mm) does NOT fit: the motor bore is Ø45.4 and there is no length left (55.0 used).
  It mounts OUTSIDE on the link plate (later stage). This stage only makes the wire channel and the side notch.

### 0.1 Gear maths (cycloid, ring fixed, input = eccentric hub, output = pins in the disc holes)
- Lobes N = 40, ring pins NP = N + 1 = 41. Ratio = N / (NP − N) = 40 / 1 = **40.0**; output turns opposite to input.
- Pin circle radius R = 23.5, pin radius RP = 1.5 (Ø3 × 10 steel dowels, ISO 8734), eccentricity E = 0.42.
- Disc outline = equidistant of the epitrochoid (t = 0..2π, r = RP + CLR_TOOTH = 1.65):
  `ψ(t) = atan2( sin(N t), R/(E·NP) − cos(N t) )`
  `x(t) = R cos t − E cos(NP t) − r cos(t − ψ)`
  `y(t) = R sin t − E sin(NP t) − r sin(t − ψ)`
- Checks (all computed by `cyc.py`, already run by the designer):
  - shortening coefficient K1 = E·NP/R = 0.42×41/23.5 = **0.733** (< 0.95, no cusps; textbook 0.65–0.9);
  - E ≤ 0.5·RP = 0.75 ✓;
  - pin pitch 2R·sin(π/41) = **3.598** → steel gap 3.598 − 3.0 = 0.598 (≥ 0.3);
  - undercut: min convex radius of curvature of the pin-centre curve ρmin = **1.931** > r = 1.65 ✓.
    The designer first tried Dongil's E = 0.5 [S study]: ρmin 1.387 < 1.65 = undercut, so E was cut to 0.42;
  - disc root r_min 21.58, tip r_max 22.42; output-pin holes d = 3 + 2E + 2·0.15 = **4.14** at PCD 33;
  - web from hole edge to root = 21.58 − (16.5 + 2.07) = **3.01** (≥ 1.6);
  - mesh simulation, 360 crank positions, both discs: min clearance **0.144** (≥ 0.10) and worst-step ≤ 0.25.
- Two discs, 180° apart (balance): disc 2 sits on the −E cam and its OUTLINE is turned +180/N = 4.5° (half a lobe); its holes are not turned.
  The designer's control run without the turn gave −0.69 mm (collision), so the turn is required.
- **50:1 fallback = one switch:** `RATIO = 50` in ap.py → N = 50, NP = 51, ratio 50/(51−50) = 50.0.
  RP = 1.25 (Ø2.5 × 10 pins), E = 0.30, K1 0.651, ρmin 1.748 > 1.40, gap 0.393, holes 3.90, clearance 0.146.
  Only discs, ring-pin holes and BOM pins change. (Note: N = 49 lobes would need NP = 50 → 49:1, so it is NOT used.)

### 0.2 Z stack (module frame, mm) — parts in assembly order
| Z | Item | Part file name |
|---|---|---|
| 0.0–3.6 | housing back wall; AS5600 pocket 23.4² × 2.0 deep open to back; Ø10 chip window | `housing` |
| 5.0–7.5 | magnet 6×2.5 diametric (glued on bell top) | `vendor_magnet` |
| 7.5–29.5 | motor (bell Ø44.5) in bore Ø45.4 | `vendor_motor` |
| 29.5–33.5 | stator mount plate Ø46.8, 3 radial M3 countersunk screws at Z 31.5 | `mid_plate` |
| 33.5–43.5 | 41 ring pins Ø3×10 at R 23.5, half buried in bore Ø47.0 | `vendor_ringpins` |
| 33.8–37.8 / 38.1–42.1 | disc 1 / disc 2 (4.0 thick) on 6702 bearings | `disc1`, `disc2`, `vendor_6702a/b` |
| 33.8–47.2 | hub: cam1 Ø15 @+E, cam2 Ø15 @−E, stub Ø4.99 | `hub` |
| 34.0–46.0 | 6 output pins Ø3×12 at PCD 33, angles 30+60k | `vendor_outpins` |
| 42.4–45.4 | carrier rear plate Ø43 (685 seat, pin holes) | `carrier` |
| 43.5–45.4 | pin_ring Ø51.9/45.0 (pins → 6808 outer race) | `pin_ring` |
| 45.4–52.4 | 6808 in seat Ø52.1; carrier spigot Ø39.95 | `vendor_6808`, `carrier` |
| 52.4–54.4 | front_ring Ø52.0/46.0; housing ends Z 54.4 | `front_ring` |
| 52.4–55.0 | out_flange Ø44 (3×M3 PCD27 Ø3.4, 3×Ø4.1 PCD24) | `out_flange` |

## 1. Part recipes (use ONLY these helpers + `frames.zcyl`; every number by its ap.py name)
Put this at the top of `cad/act2/p_act.py`:
```python
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "knuckle"))
from build123d import Box, Cone, Cylinder, Location, Polygon, Pos, Rot, extrude
from frames import zcyl
import ap, cyc

def pol(r, a):            # polar -> (x, y)
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))

def ring(d_out, d_in, z0, z1):
    return zcyl(0, 0, d_out, z0, z1) - zcyl(0, 0, d_in, z0 - 0.01, z1 + 0.01)

def radial_hole(d, r0, r1, ang, z):   # cylinder along the radius from r0 to r1 at angle ang, height z
    c = Rot(0, 90, 0) * Cylinder(d / 2, r1 - r0)          # axis now along X
    return Pos(0, 0, z) * Rot(0, 0, ang) * Pos((r0 + r1) / 2, 0, 0) * c

def radial_csk(ang, z):   # 90-deg countersink at the OD for ISO 10642 M3, apex inward
    c = Rot(0, -90, 0) * Cone(ap.CSK_D / 2, ap.CSK_HOLE / 2, (ap.CSK_D - ap.CSK_HOLE) / 2, align=None)
    return Pos(0, 0, z) * Rot(0, 0, ang) * Pos(ap.OD / 2 - (ap.CSK_D - ap.CSK_HOLE) / 2, 0, 0) * c
```
If `radial_csk` gives a wrong-way cone (check in the cutaway render), change `Rot(0, -90, 0)` to `Rot(0, 90, 0)`, once. If still wrong: drop the countersink, use a plain Ø3.4 hole + M3×8 ISO 7380 button head, and write `csk skipped` in STATUS.

Each function returns ONE solid. `PARTS = {name: fn}` at the bottom (same style as `cad/knuckle/p_*.py`).
1. **housing()**
   - Base: `zcyl(0,0,OD,0,Z_FRONT_RING[1])`.
   - Bores, minus:
     - `zcyl(0,0,BORE_MOTOR,Z_BACK[1],Z_MID[0])`
     - `zcyl(0,0,BORE_PIN,Z_MID[0],Z_RINGPIN[1])`
     - `zcyl(0,0,SEAT_6808,Z_PIN_RING[0],Z_FRONT_RING[1]+0.01)`
   - Ring-pin holes: NP × `zcyl(*pol(R, 360*k/NP), 2*RP+0.05, Z_RINGPIN[0], Z_RINGPIN[1])`, NP/R/RP from `cyc.gear()`.
   - Back face: encoder pocket `Box(ENC_W,ENC_W,2.0)` placed at Z 0–2.0; window `zcyl(0,0,ENC_WINDOW_D,1.9,Z_BACK[1]+0.01)`.
   - Link pilots: 6 × `zcyl(*pol(LINK_PCD/2, 60k), LINK_PILOT_D, -0.01, LINK_PILOT_L)`.
   - Wire channel at WIRE_ANG: box, radial WIRE_R, tangential WIRE_W, Z_BACK[1]-0.01 .. Z_MID[0]+0.01.
   - Side notch at WIRE_ANG: radial 22.0..OD/2+1, width NOTCH_W, Z NOTCH_Z.
   - Back-face groove: pocket edge → notch at WIRE_ANG, width ENC_GROOVE_W, depth ENC_GROOVE_D.
   - Make every box with `Rot(0,0,ang) * Pos(r_mid,0,z_mid) * Box(dr, w, dz)`.
   - 3 radial screws at CSK_ANG: `radial_hole(CSK_HOLE, OD/2-4, OD/2+0.1, a, CSK_Z)` + `radial_csk(a, CSK_Z)`.
2. **mid_plate()**
   - Base: `zcyl(0,0,MID_D,*Z_MID)` − `zcyl(0,0,STATOR_HOLE_D,...)`.
   - 4 × M3 Ø3.4 at MOT_PCD/2, MOT_SCREW_ANG, with CB `MID_CB_D` × `MID_CB_H` from the FRONT face (Z 33.5 down).
   - 3 × `radial_hole(CSK_PILOT, MID_D/2-CSK_PILOT_L, MID_D/2+0.1, a, CSK_Z)`.
   - Back-face wire groove at WIRE_ANG from r 6 to OD, `MID_GROOVE`.
3. **hub()**
   - `zcyl(E,0,CAM_D,Z_HUB[0],Z_CAM_SPLIT)` + `zcyl(-E,0,CAM_D,Z_CAM_SPLIT,Z_STUB0)` + `zcyl(0,0,STUB_D,Z_STUB0,Z_HUB[1])`.
   - Minus the bore `zcyl(0,0,HUB_BORE,Z_HUB[0]-0.01,Z_HUB[0]+HUB_BORE_L)`.
   - Minus the grub pilot `radial_hole(GRUB_PILOT,1.5,CAM_D/2+1,90,GRUB_Z)`.
4. **disc(second)**
   - Outline: `pts = cyc.disc_outline(second=second, m=ap.DISC_M)`, then `extrude(Polygon(*[tuple(map(float,p)) for p in pts], align=None), amount=4.0)`.
   - Minus `Cylinder(DISC_BORE/2, 20)`.
   - Minus 6 holes Ø(OUT_PIN_D+2E+2·CLR_TOOTH) at OUT_PIN_PCD/2, angles 30+60k (NOT turned for disc 2).
   - Then move by `Pos(±E, 0, Z_DISC1[0] or Z_DISC2[0])`: disc1 at +E, disc2 at −E.
   - The designer tested this: valid, watertight, vol 4253 mm³ for disc1 before the move. It takes about 25 s.
5. **carrier()**
   - Base: `zcyl(0,0,PLATE_D,*Z_CARRIER_PLATE)` + `zcyl(0,0,SPIGOT_D,*Z_SPIGOT)`.
   - Minus the 685 seat `zcyl(0,0,SEAT_685,Z_685[0]-0.01,Z_685[1])`.
   - Minus 6 output-pin holes Ø OUT_PIN_PRESS at PCD 33, angles 30+60k, Z 42.39..46.0.
   - Minus 3 inserts Ø INS_M3_D at OUT_M3 (Z 46.4..52.41) and 3 dowel holes Ø OUT_DOWEL_HOLE at OUT_DOWEL (Z 49.3..52.41).
6. **out_flange()**
   - Base: `zcyl(0,0,FLANGE_D,*Z_FLANGE)`.
   - Minus 3 × Ø3.4 at OUT_M3 and 3 × Ø OUT_DOWEL_FLANGE_HOLE at OUT_DOWEL, through.
7. **pin_ring()** = `ring(*PIN_RING, *Z_PIN_RING)`; **front_ring()** = `ring(*FRONT_RING, *Z_FRONT_RING)`.
8. **Vendor proxies** (names start with `vendor_` so gate.py treats them as bought parts):
   - `vendor_motor` = `zcyl(0,0,MOT_D,*Z_MOTOR)` + shaft `zcyl(0,0,SHAFT_D,Z_MOTOR[1],Z_MOTOR[1]+SHAFT_OUT)`;
   - `vendor_magnet` Ø6 at Z_MAG;
   - `vendor_ringpins` (all NP pins Ø2RP at Z_RINGPIN);
   - `vendor_outpins` (6 × Ø3 at Z_OUTPIN);
   - `vendor_dowels` (3 × Ø4, Z 49.3..57.3);
   - `vendor_6808` = ring(52,40,*Z_6808);
   - `vendor_6702a` = `Pos(E,0,0)*ring(21,15,*Z_DISC1)`, `vendor_6702b` = `Pos(-E,0,0)*ring(21,15,*Z_DISC2)`;
   - `vendor_685` = ring(11,5,*Z_685).
Files: `cad/act2/{ap.py, cyc.py, p_act.py, build_act.py, act_checks.py, BOM.md, NOTICE.md}`. Printed parts: housing, mid_plate, hub, disc1, disc2, carrier, out_flange, pin_ring, front_ring (9).

## Steps
1. Command: `cd ~/Vector-wt/act2 && /usr/bin/git branch --show-current && /usr/bin/git log --oneline -1`
   Expected: `arm-actuator2` then a line starting `9a55485` (or later arm-knuckle commit). If not: STOP, `BLOCKED: worktree`.
2. Command: `mkdir -p cad/act2 && cp ~/Vector/stages/code/act2/ap.py ~/Vector/stages/code/act2/cyc.py cad/act2/ && cd cad/act2 && $PY cyc.py 40 | tail -4 && $PY cyc.py 50 | tail -2`
   Expected (about 40 s):
   ```
   disc2 mesh clearance worst-step <= 0.25: 0.144 OK
   disc r_min 21.580 r_max 22.420  out-pin hole d 4.14  pin pitch 3.598
   CYC PASS
   disc r_min 21.950 r_max 22.550  out-pin hole d 3.90  pin pitch 2.893
   CYC PASS
   ```
   Also `$PY cyc.py | head -1` → `RATIO 40.0` (**GATE G1 ratio**). If not: STOP, `BLOCKED: cyc` (do not edit cyc.py).
3. Write `cad/act2/p_act.py` exactly from section 1 (helpers verbatim, then one function per part, `PARTS` dict).
4. Write `cad/act2/build_act.py`. Copy `cad/knuckle/build.py` with 3 changes:
   - `sys.path.insert(0, "../knuckle")` before `import frames`;
   - MODULES = `["p_act"]` and no VENDOR dict (vendors are in PARTS);
   - after `export_stl` also call `export_step(s, os.path.join(OUT, n + ".step"))`, imported from build123d.
   Output dir `cad/act2/out/`.
5. Command: `cd ~/Vector-wt/act2/cad/act2 && $PY build_act.py 2>&1 | grep -v Warning`
   Expected: 19 lines `name: bbox=(...) vol=...` (9 printed + 10 vendor), no Traceback. Check these bboxes by eye (±0.05):
   - `housing` (−28.5, 28.5, −28.5, 28.5, 0.0, 54.4)
   - `out_flange` z 52.4..55.0
   - `disc1` x max ≈ 22.84
   - `mid_plate` z 29.5..33.5
   - `hub` z 33.8..47.2
   Then `ls out/*.step | wc -l` → `19`.
   If a part fails: fix only that function (3 tries, rule 0.5), else `BLOCKED: <part>` and continue.
6. Write `cad/act2/act_checks.py` (gates G2/G3), exactly:
   ```python
   import glob, sys, trimesh
   P = ["housing","mid_plate","hub","disc1","disc2","carrier","out_flange","pin_ring","front_ring"]
   ok = True; zmin, zmax, rmax = 1e9, -1e9, 0.0
   for n in P:
       m = trimesh.load_mesh(f"out/{n}.stl", force="mesh"); m.merge_vertices()
       b = m.bounds; zmin = min(zmin, b[0][2]); zmax = max(zmax, b[1][2])
       r = float(((m.vertices[:, :2] ** 2).sum(1) ** 0.5).max()); rmax = max(rmax, r)
       wt = bool(m.is_watertight); ok &= wt
       print(f"{n}: watertight={wt} rmax={r:.2f}")
   L = zmax - zmin
   print(f"LENGTH {L:.2f} {'OK' if L <= 55.0 + 0.01 else 'BAD'}"); ok &= L <= 55.01
   print(f"OD {2*rmax:.2f} {'OK' if 2*rmax <= 57.0 + 0.02 else 'BAD'}"); ok &= 2 * rmax <= 57.02
   print("ACT PASS" if ok else "ACT FAIL"); sys.exit(0 if ok else 1)
   ```
7. **GATE G2/G3** (watertight, length ≤ 55, OD ≤ 57): `$PY act_checks.py; echo rc=$?` → 9 lines `watertight=True`, `LENGTH 55.00 OK`, `OD 57.00 OK`, `ACT PASS`, `rc=0`.
   If watertight=False: rebuild that part once with `DISC_M=720` (disc only) or check for 0-thickness faces (extend cutters by 0.01). Else `BLOCKED: watertight <part>`.
8. **GATE G4/G5** (min wall 1.6 per part + assembly interference, existing gate). Command (slow, ≤ 10 min):
   `$PY ../knuckle/gate.py out/housing.stl out/mid_plate.stl out/hub.stl out/disc1.stl out/disc2.stl out/carrier.stl out/out_flange.stl out/pin_ring.stl out/front_ring.stl out/vendor_*.stl; echo rc=$?`
   Expected: every printed line `OK` (minwall ≥ 1.60), no `INTERF ... BAD`, `GATE PASS`, `rc=0`.
   Allowed fallbacks, one each, recorded in STATUS:
   - `INTERF vendor_outpins x carrier` or `vendor_6808 x carrier`/`housing`, or `vendor_6702* x disc*`/`hub` (press/coincident faces) → re-run with `--allow=<a>:<b>`;
   - `minwall` BAD for `housing` only because of the 2.0 encoder-pocket floor → change `Z_ENC_POCKET` to `(0.0, 1.8)` AND the window start to 1.7, once.
   - Any other BAD → STOP that line, `BLOCKED: gate <line>`.
9. **GATE G6 (tooth interference in 3D)**, the designer's sweep on the real STL:
   `$PY -c "import cyc; print(cyc.mesh_clearance(40), cyc.mesh_clearance(40, second=True))"` → `(0.144..., 0.144...) (0.144..., 0.144...)`.
10. **Printability check** (record, do not fix):
    - Overhang rule: print housing back-face down, mid_plate front-face down, carrier plate down, discs/rings/flange flat, hub cam1 down.
    - Write in STATUS which faces bridge: the housing pocket ceiling bridges 23.4 mm (OK on A1); radial holes Ø3.4/Ø2.5 print as horizontal holes (OK).
    - Every part must fit 256×256 (largest is 57).
11. **Render** (same tool as S4). Write `/tmp/act_list.txt`, one line each `<abs path stl> r g b`:
    - housing 0.85 0.85 0.88; mid_plate, pin_ring, front_ring 0.25 0.25 0.28;
    - disc1 0.20 0.45 0.85; disc2 0.15 0.65 0.45; hub, carrier, out_flange 0.95 0.55 0.10;
    - all vendor_* 0.6 0.6 0.6.
    Command: `mkdir -p ~/Vector-wt/act2/renders && /usr/local/bin/blender -b -P ../knuckle/render_blend.py -- ~/Vector-wt/act2/renders/a1 /tmp/act_list.txt 2>&1 | grep WROTE`
    Expected: 6 `WROTE` lines (`a1_frontiso … a1_cutaway`). Look at each PNG and write 1 line per view in STATUS. Pass criteria:
    (a) cutaway shows motor → mid plate → two discs → carrier → 6808 → flange in that order;
    (b) ring pins visible half buried;
    (c) no part floats;
    (d) countersinks open outward;
    (e) outline is a plain Ø57 cylinder with no bumps.
    PNGs must be ≤ 1.5 MB each (rule 0.4). If one is bigger, do not edit render_blend.py: leave that PNG out of the commit and note it in STATUS.
12. **50:1 dry run** (do not commit its STLs): `sed -i '' 's/^RATIO = 40 /RATIO = 50 /' ap.py && $PY build_act.py disc1 disc2 housing 2>&1 | grep -v Warning && sed -i '' 's/^RATIO = 50 /RATIO = 40 /' ap.py && $PY build_act.py disc1 disc2 housing 2>&1 | grep -v Warning`.
    Expected: 6 bbox lines, no Traceback. Then `grep '^RATIO' ap.py` → `RATIO = 40 ...`. Record the 50:1 disc bboxes in STATUS.
13. Write `cad/act2/BOM.md`: the table in section 2 below, copied, plus the print settings. Write `cad/act2/NOTICE.md`:
    "Interface dims from Seeed reBot-DevArm (CERN-OHL-W-2.0), https://github.com/Seeed-Projects/reBot-DevArm; cycloid concept after Dongil Choi, hackaday.io/project/167688. Changes: new printed actuator."

## 2. BOM (one module; USD, prices from the study read 28 Oct 2026; [U] = not verified)
| Qty | Item | Size | USD |
|---|---|---|---|
| 1 | Tarot TL2955 4008 330KV | Ø44.5×22, 85 g, 4 mm shaft | 45.99 Foxtech [S study]; AliExpress 25–29 [U] |
| 1 | ST B-G431B-ESC1 (outside module) | 30×41, CAN | 39.26 ST eStore [S study] |
| 1 | AS5600 board + 6×2.5 diametric magnet | board 23×23 [U] | 3–5 [U] |
| 1 | 6808-2RS | 40×52×7 | ~4 [U] |
| 2 | 6702-2RS | 15×21×4 | ~2 total [U] |
| 1 | 685-2RS | 5×11×5 | ~0.5 [U] |
| 41 | dowel ISO 8734 Ø3×10 (50:1: 51 × Ø2.5×10) | hardened steel | ~3 [U] |
| 6 | dowel Ø3×12 (output pins) | | ~1 [U] |
| 3 | dowel Ø4×8 (output locating) | | ~1 [U] |
| 6 | M3×8 thread-forming or ISO 7380 (link → back face; length = link plate + 3) | | |
| 4 | M3×6 ISO 7380 (stator → mid_plate) [U length, Q3] | | |
| 3 | M3×6 ISO 10642 countersunk (radial, housing → mid_plate) | | |
| 3 | M3 heat-set insert 4.6×5.7 + M3×8 ISO 7380 (flange → carrier) | | |
| 1 | M3×5 ISO 4026 set screw (hub on shaft) + Loctite 243 | | |
| | Filament ~90 g | | ~2 [U] |
| | **Module total** (ESC included) | | **≈ $105 [U]**; 2 modules ≈ $210 (study: $196.50 + pins/screws) |

**Print (Bambu A1, 0.4 nozzle):**
- Housing, mid_plate, rings: PETG, 0.2 layer, 6 walls, 40 % gyroid.
- Discs, hub, carrier, out_flange: PA-CF (dry 8 h at 80 °C) or PETG, 0.12 layer, 6 walls, 100 % infill.
- No supports. Clearance rule: 0.15 per side on slip fits; fit-test the 6808 seat and the Ø3 pin holes first (print only the housing front 12 mm).
- Grease the ring pins and discs with PTFE or lithium grease.

## Gate before commit
- Steps 2 (G1 `RATIO 40.0`, `CYC PASS`), 7 (`ACT PASS`), 8 (`GATE PASS` or allowed fallback recorded) and 9 all pass.
- 6 `WROTE`.
- `git status` shows only `cad/act2/{ap.py,cyc.py,p_act.py,build_act.py,act_checks.py,BOM.md,NOTICE.md}`, `renders/a1_*.png` (only if each ≤ 1.5 MB) and `docs/STATUS-act2.md`.

## Status + commit (always the last steps)
S.1 Create `docs/STATUS-act2.md` (first line `# STATUS — printed actuator (branch arm-actuator2)`) with a section:
```
## Stage A1 — <today's date> — PASS or FAIL
- Gate lines: <every line ending PASS/FAIL/BAD/OK from steps 2, 7, 8, 9>
- Part bboxes + volumes: <step 5 output>   50:1 dry run: <step 12 bboxes>
- Render review: <one line per view>   Printability: <step 10 notes>
- Files added: <git status --short>   Fallbacks used: <none | list>
- UNVERIFIED values touched: SHAFT_OUT, MOT_PCD, STATOR_HOLE_D, ENC_W, 6808 lands, Tarot dims (list any others)
- Questions for Riyansh: Q1 measure the Tarot 4008 (OD, height incl. base, base face to bell top); Q2 shaft length beyond the stator base (need ≥ 12); Q3 stator base hole PCD and thread, centre boss Ø; Q4 AS5600 board size and chip height; Q5 PETG or PA-CF for the discs?
```
S.2 Command: `cd ~/Vector-wt/act2 && /usr/bin/git status --short` → only the files above. NO `out/`, NO `.stl`, NO `.step`, NO `__pycache__`. If not: do not add them.
S.3 Command: `/usr/bin/git add <those paths> && /usr/bin/git commit -m "A1: printed 40:1 cycloid actuator module"` → `[arm-actuator2 <hash>] A1: printed 40:1 cycloid actuator module`
S.4 Command: `/usr/bin/git tag act-1-done && /usr/bin/git push -u origin arm-actuator2 --tags` → ends with `* [new tag] act-1-done -> act-1-done`. If rejected: `/usr/bin/git pull --ff-only origin arm-actuator2` once, push again; else `BLOCKED: push`.
S.5 STOP. Do not start another stage. Do not touch `arm-knuckle`.
