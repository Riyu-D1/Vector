## Stage A2a — 2026-10-28 — PASS
- Gate lines (literal, copy-paste):
  ```
  REACH J2 (np.float64(-20.0), np.float64(143.5)) J3 (np.float64(-20.0), np.float64(270.2)) J4 (np.float64(96.4), np.float64(216.2))
  REACH upper J2->J3 126.70 (want 126.7) PASS
  REACH forearm J3->J4 axial 116.40 (want 116.4), offset 54.00 (want 54.0) PASS
  REACH J2->TCP 375.0 = 126.7 + 116.4 + A2b 131.9 (want 375 +- 10) PASS
  HOLE back_spacer_j2: 6 x d2.5 on actuator back pilots PCD50 PASS
  HOLE back_spacer_j3: 6 x d2.5 on actuator back pilots PCD50 PASS
  HOLE upper_back: 12 x d2.5 on actuator back pilots PCD50 PASS
  HOLE front_spacer_j2: 3 x d3.0 on actuator M3 PCD27 PASS
  HOLE front_spacer_j2: 3 x d4.0 on actuator dowels PCD24 PASS
  HOLE front_spacer_j2: old reBot dowel holes plugged PASS
  HOLE front_spacer_j3: 3 x d3.0 on actuator M3 PCD27 PASS
  HOLE front_spacer_j3: 3 x d4.0 on actuator dowels PCD24 PASS
  HOLE front_spacer_j3: old reBot dowel holes plugged PASS
  HOLE link1: 3 x d3.0 J2 cheek on actuator M3 PASS
  HOLE dogleg_l: 3 x d3.0 J3 end on actuator M3 PASS
  HOLE upper_out ring d57.15 on housing OD 57.00 (clearance 0.15) PASS
  HOLE upper_out: housing OD free and ring wall present at both ends PASS
  HOLE fore_l: 4 dogleg top-end holes clear PASS
  HOLE yaw_limit: 4 horn holes PCD14 clear, old d14 plugged, horn recess open PASS
  TORQUE masses: upper printed 0.050 kg, forearm printed 0.066 kg, J3 actuator 0.300 [U], wrist+grip 0.315, payload 0.25; J4->TCP 131.8
  TORQUE J2 2.34 N.m (rebot_torque 0.48: 2.23, limit 3.50, margin 1.50x, need <= 2.50) PASS
  TORQUE J3 1.15 N.m (rebot_torque 0.48: 1.15, limit 2.25, margin 1.96x, need <= 1.50) PASS
  ROM home pose J2 joint clear PASS
  ROM J3 free -180..+30 deg (total 210, need >= 150) stops: + [fore_l x link1 147] - [] PASS
  ROM J2 free -120..+70 deg (total 190, need >= 150) stops: + [fore_l x base_plate 142] - [upper_out x base_reinf 1] PASS
  CHECKS PASS
  rc=0
  ```
  ```
  back_spacer_j2: watertight=True bbox=57.0x4.7x56.8 max=57.0 minwall=1.89 OK
  back_spacer_j3: watertight=True bbox=57.0x4.7x56.8 max=57.0 minwall=1.89 OK
  base_link: watertight=True bbox=92.0x92.0x63.7 max=92.0 minwall=3.02 OK
  base_plate: watertight=True bbox=140.0x200.0x14.0 max=200.0 minwall=13.99 OK
  base_reinf: watertight=True bbox=92.0x92.0x6.9 max=92.0 minwall=1.84 OK
  dogleg_l: watertight=True bbox=76.1x5.0x99.0 max=99.0 minwall=3.62 OK
  dogleg_r: watertight=True bbox=76.1x5.0x99.0 max=99.0 minwall=3.68 OK
  flange_j2: watertight=True bbox=34.8x9.7x34.8 max=34.8 minwall=2.60 OK
  flange_j3: watertight=True bbox=34.8x10.7x34.8 max=34.8 minwall=2.58 OK
  fore_l: watertight=True bbox=171.6x4.0x57.0 max=171.6 minwall=3.99 OK
  fore_r: watertight=True bbox=171.6x4.0x57.0 max=171.6 minwall=3.99 OK
  front_spacer_j2: watertight=True bbox=34.8x4.0x34.7 max=34.8 minwall=2.66 OK
  front_spacer_j3: watertight=True bbox=34.8x5.0x34.7 max=34.8 minwall=2.38 OK
  j1_cradle: watertight=True bbox=57.5x57.3x54.5 max=57.5 minwall=4.38 OK
  link1: watertight=True bbox=83.7x77.2x84.0 max=84.0 minwall=2.98 OK
  upper_back: watertight=True bbox=61.0x4.0x187.5 max=187.5 minwall=3.80 OK
  upper_out: watertight=True bbox=61.0x7.0x187.5 max=187.5 minwall=1.91 OK
  vendor_6803_j2: watertight=True bbox=26.0x5.0x25.9 max=26.0 minwall=99.00 OK
  vendor_6803_j3: watertight=True bbox=26.0x5.0x25.9 max=26.0 minwall=99.00 OK
  vendor_act_j2: watertight=True bbox=57.0x54.4x56.8 max=57.0 minwall=99.00 OK
  vendor_act_j3: watertight=True bbox=57.0x54.4x56.8 max=57.0 minwall=99.00 OK
  vendor_actout_j2: watertight=True bbox=43.9x2.9x44.0 max=44.0 minwall=99.00 OK
  vendor_actout_j3: watertight=True bbox=43.9x2.9x44.0 max=44.0 minwall=99.00 OK
  vendor_sts3250_j1: watertight=True bbox=45.2x24.7x49.8 max=49.8 minwall=99.00 OK
  yaw_limit: watertight=True bbox=77.0x77.0x7.1 max=77.0 minwall=1.89 OK
  GATE PASS
  rc=0
  ```
- Part list (bbox + volume):
  ```
  base_plate           fix bbox 140.0 x 200.0 x 14.0  vol 385.5 cm3  wt True
  base_link            fix bbox 92.0 x 92.0 x 63.7  vol 243.5 cm3  wt True
  j1_cradle            fix bbox 57.5 x 57.5 x 54.5  vol 104.2 cm3  wt True
  vendor_sts3250_j1    fix bbox 45.2 x 24.7 x 49.8  vol 42.9 cm3  wt True
  base_reinf           fix bbox 92.0 x 92.0 x 7.0  vol 27.3 cm3  wt True
  yaw_limit            fix bbox 77.0 x 77.0 x 7.1  vol 13.2 cm3  wt True
  link1                fix bbox 83.8 x 77.3 x 84.1  vol 42.6 cm3  wt True
  front_spacer_j2      fix bbox 34.8 x 4.0 x 34.8  vol 2.8 cm3  wt True
  flange_j2            fix bbox 34.8 x 9.8 x 34.8  vol 5.2 cm3  wt True
  vendor_actout_j2     fix bbox 44.0 x 2.9 x 44.0  vol 1.0 cm3  wt True
  vendor_act_j2        up  bbox 57.0 x 54.4 x 57.0  vol 138.8 cm3  wt True
  back_spacer_j2       up  bbox 57.0 x 4.7 x 57.0  vol 9.5 cm3  wt True
  vendor_6803_j2       up  bbox 26.0 x 5.0 x 26.0  vol 1.5 cm3  wt True
  upper_out            up  bbox 61.0 x 7.0 x 187.7  vol 18.9 cm3  wt True
  upper_back           up  bbox 61.0 x 4.0 x 187.7  vol 27.6 cm3  wt True
  vendor_act_j3        up  bbox 57.0 x 54.4 x 57.0  vol 138.8 cm3  wt True
  back_spacer_j3       up  bbox 57.0 x 4.7 x 57.0  vol 9.5 cm3  wt True
  vendor_6803_j3       up  bbox 26.0 x 5.0 x 26.0  vol 1.5 cm3  wt True
  front_spacer_j3      fo  bbox 34.8 x 5.0 x 34.8  vol 3.6 cm3  wt True
  flange_j3            fo  bbox 34.8 x 10.8 x 34.8  vol 6.0 cm3  wt True
  vendor_actout_j3     fo  bbox 44.0 x 2.9 x 44.0  vol 1.0 cm3  wt True
  dogleg_l             fo  bbox 76.2 x 5.0 x 99.0  vol 19.4 cm3  wt True
  dogleg_r             fo  bbox 76.2 x 5.0 x 99.0  vol 19.4 cm3  wt True
  fore_l               fo  bbox 171.6 x 4.0 x 57.0  vol 19.4 cm3  wt True
  fore_r               fo  bbox 171.6 x 4.0 x 57.0  vol 19.4 cm3  wt True
  BUILD DONE 25 parts 12 s
  ```
  Render review:
  - frontiso: L pose clear — base at lower right, upper plates vertical, blue J2 actuator between them, dogleg + fore plates reaching right at the top with J3 actuator; exposed flat plates, nothing floats.
  - backiso: from behind — seeed-studio base plate, link1, both blue actuators (J2 between upper plates, J3 at the dogleg end), orange fore plates ring ends; no covers.
  - side: clean L — vertical upper arm off the base, forearm horizontal, sitting below the J3 axis (dogleg offset); lightening slots visible in upper plates.
  - top: base plate + base_link disc, J2/J3 blue actuators side by side between the two orange plate lines; forearm plates edge-on pointing forward.
  - front: looking down the forearm — J3 and J2 blue barrels in line, link1 and orange plates stacked, base at the far end; nothing detached.
  - cutaway: J2 and J3 actuator bores visible in the orange rings; dark STS3250 servo inside the j1_cradle pocket in the base, horn face up under yaw_limit; no visible screws/cables, nothing floats.
- Files changed: `?? cad/arm2/`, `?? docs/STATUS-arm2.md`, `?? renders/a2_*.png` (6 files). BLOCKED: none.
- Source: Seeed reBot-DevArm 13bebbf (CERN-OHL-W-2.0), reBot_B601_DM_v1.1_20260425.step; changes in cad/arm2/NOTICE.md.
- Assembly: J1 servo + horn into j1_cradle in base_link, yaw_limit on the horn with 4x M3x8 from the top, then reBot J1 stack (AXK5578, 6707, reinforcement) and Link1. J2/J3: actuator housing into the upper_out ring (slip + CA), back_spacer + upper_back with 6x M3x10 countersunk into the back pilots; front spacer + Link1 cheek (J2) / dogleg_l (J3) with 3x M3x14 / M3x16 into the carrier inserts; 6803 in the back spacer on the reBot FLANGE.
- Still UNVERIFIED: STS3250 case = STS3215 case (45.2 x 24.7 x 35, horn PCD14, horn thread); upper_out ring grip (0.15 clearance + CA); M3x10 countersunk grip in the 3.2 pilots (1.3 mm); J3 actuator mass 0.300 kg; printed mass factor 0.6; servo cable route (cradle d10 hole -> base floor d16); Link1 printed at reBot 3 mm sheet thickness; forearm band 32 mm (reBot neck).
