## Stage A2b — 2026-10-28 — PASS
- Gate lines (literal, copy-paste):
```
REACH J2 (np.float64(-20.0), np.float64(143.5)) J3 (np.float64(-20.0), np.float64(270.2)) J4 (np.float64(96.4), np.float64(216.2)) (J4 servo horn) J5 x 134.00 y 0.00 (vertical) J6 y 0.00 z 216.20 (along X) TCP x 228.20
REACH J4->J5 37.60 (want 37.6), J5 axis y 0.00 PASS
REACH J6 axis on the J4 height: dz 0.00 dy 0.00; J5->J6 frame 19.2 on it, J6 horn face at J4 + 63.0 PASS
REACH J4->TCP 131.80 (want 131.8 = 37.6 + 19.2 + 75.0) PASS
REACH J2->TCP 374.9 = 126.7 + 116.4 + 131.8 (want 375 +- 10) PASS
HOLE link4: 4 x d3.4 on the STS3215 horn PCD14 PASS
HOLE link5: 4 x d3.4 on the STS3215 horn PCD14 PASS
HOLE grip_frame: 4 x d3.4 on the STS3215 horn PCD14 PASS
HOLE link4: 4 horn holes measured, pattern centre on the servo horn axis (err 0.000) PASS
HOLE link5: 4 horn holes measured, pattern centre on the servo horn axis (err 0.000) PASS
HOLE grip_frame: 4 horn holes measured, pattern centre on the servo horn axis (err 0.000) PASS
HOLE fore_l2: old reBot d38 DM4310 pilot plugged PASS
HOLE fore_r2: old reBot d38 DM4310 pilot plugged PASS
HOLE fore_r2: 4 x d3.4 J4 cradle bolts clear PASS
HOLE j4_cradle: 4 x d2.5 pilots on the same centres, 8 deep PASS
HOLE STS3215 pockets: 0.15 per side on the 45.2 x 24.7 x 35.7 case PASS
GRIP open 25.0 mm (finger gap 2.0 -> 27.0): racks stay in the 64 mm channels and on the gear, no hits PASS
TORQUE masses: wrist+gripper (J4 horn onward) 0.246 kg, J4 servo+cradle 0.077 kg, payload 0.25 kg at J4 + 131.8
TORQUE J4 0.48 N.m (STS3215 rated 0.98 [U] / 1.4 = 0.70) PASS
TORQUE J5 0.30 N.m with J4 turned 90 (same limit 0.70) PASS
TORQUE J2 2.36 N.m with the real wrist (A2a need <= 2.50, limit 3.50) PASS
TORQUE J3 1.15 N.m with the real wrist (A2a need <= 1.50, limit 2.25) PASS
ROM home pose wrist + gripper clear of every part PASS
ROM J4 free -70..+70 deg (total 140, need >= 140) stops: + [vendor_sts3215_j6 x j4_cradle 1] - [vendor_sts3215_j5 x fore_r2 4] PASS
ROM J5 free -70..+70 deg (total 140, need >= 140) stops: + [grip_frame x fore_r2 2] - [grip_frame x fore_l2 2] PASS
ROM J6 free -180..+180 deg (total 360, need >= 360) stops: + [] - [] PASS
ROM J3 free -180..+30 deg (total 210, need >= 150) stops: + [fore_l2 x link1 147] - [] PASS
ROM J2 free -120..+60 deg (total 180, need >= 150) stops: + [vendor_sts3215_j6 x base_plate 564] - [upper_out x base_reinf 1] PASS
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
finger_d: watertight=True bbox=14.4x4.0x25.2 max=25.2 minwall=3.99 OK
finger_u: watertight=True bbox=14.4x4.0x25.2 max=25.2 minwall=3.99 OK
flange_j2: watertight=True bbox=34.8x9.7x34.8 max=34.8 minwall=2.60 OK
flange_j3: watertight=True bbox=34.8x10.7x34.8 max=34.8 minwall=2.58 OK
fore_l2: watertight=True bbox=171.6x4.0x57.0 max=171.6 minwall=3.99 OK
fore_r2: watertight=True bbox=171.6x4.0x57.0 max=171.6 minwall=3.99 OK
front_spacer_j2: watertight=True bbox=34.8x4.0x34.7 max=34.8 minwall=2.66 OK
front_spacer_j3: watertight=True bbox=34.8x5.0x34.7 max=34.8 minwall=2.38 OK
grip_frame: watertight=True bbox=56.4x64.0x52.4 max=64.0 minwall=1.89 OK
j1_cradle: watertight=True bbox=57.5x57.3x54.5 max=57.5 minwall=4.38 OK
j4_cradle: watertight=True bbox=38.0x52.5x30.0 max=52.5 minwall=2.49 OK
link1: watertight=True bbox=83.7x77.2x84.0 max=84.0 minwall=2.98 OK
link4: watertight=True bbox=66.6x60.6x69.0 max=69.0 minwall=2.11 OK
link5: watertight=True bbox=38.1x30.0x34.6 max=38.1 minwall=1.99 OK
upper_back: watertight=True bbox=61.0x4.0x187.5 max=187.5 minwall=3.80 OK
upper_out: watertight=True bbox=61.0x7.0x187.5 max=187.5 minwall=1.91 OK
vendor_6803_j2: watertight=True bbox=26.0x5.0x25.9 max=26.0 minwall=99.00 OK
vendor_6803_j3: watertight=True bbox=26.0x5.0x25.9 max=26.0 minwall=99.00 OK
vendor_act_j2: watertight=True bbox=57.0x54.4x56.8 max=57.0 minwall=99.00 OK
vendor_act_j3: watertight=True bbox=57.0x54.4x56.8 max=57.0 minwall=99.00 OK
vendor_actout_j2: watertight=True bbox=43.9x2.9x44.0 max=44.0 minwall=99.00 OK
vendor_actout_j3: watertight=True bbox=43.9x2.9x44.0 max=44.0 minwall=99.00 OK
vendor_gear_grip: watertight=True bbox=6.0x17.9x18.0 max=18.0 minwall=99.00 OK
vendor_rack_d: watertight=True bbox=6.0x36.0x12.0 max=36.0 minwall=99.00 OK
vendor_rack_u: watertight=True bbox=6.0x36.0x12.0 max=36.0 minwall=99.00 OK
vendor_sts3215_g: watertight=True bbox=49.3x24.7x45.2 max=49.3 minwall=99.00 OK
vendor_sts3215_j4: watertight=True bbox=45.2x49.3x24.7 max=49.3 minwall=99.00 OK
vendor_sts3215_j5: watertight=True bbox=24.7x45.2x49.3 max=49.3 minwall=99.00 OK
vendor_sts3215_j6: watertight=True bbox=49.3x24.7x45.2 max=49.3 minwall=99.00 OK
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
fore_l2              fo  bbox 171.6 x 4.0 x 57.0  vol 23.9 cm3  wt True
fore_r2              fo  bbox 171.6 x 4.0 x 57.0  vol 23.8 cm3  wt True
j4_cradle            fo  bbox 38.0 x 52.5 x 30.0  vol 28.7 cm3  wt True
vendor_sts3215_j4    fo  bbox 45.2 x 49.3 x 24.7  vol 42.8 cm3  wt True
link4                w4  bbox 66.6 x 60.6 x 69.1  vol 29.8 cm3  wt True
vendor_sts3215_j5    w4  bbox 24.7 x 45.2 x 49.3  vol 42.8 cm3  wt True
link5                w5  bbox 38.0 x 30.0 x 34.6  vol 11.2 cm3  wt True
vendor_sts3215_j6    w5  bbox 49.3 x 24.7 x 45.2  vol 42.8 cm3  wt True
grip_frame           w6  bbox 56.4 x 64.0 x 52.4  vol 20.9 cm3  wt True
vendor_sts3215_g     w6  bbox 49.3 x 24.7 x 45.2  vol 42.8 cm3  wt True
vendor_gear_grip     w6  bbox 6.0 x 18.0 x 18.0  vol 1.5 cm3  wt True
vendor_rack_u        w6  bbox 6.0 x 36.0 x 12.0  vol 2.4 cm3  wt True
vendor_rack_d        w6  bbox 6.0 x 36.0 x 12.0  vol 2.4 cm3  wt True
finger_u             w6  bbox 14.4 x 4.0 x 25.2  vol 1.3 cm3  wt True
finger_d             w6  bbox 14.4 x 4.0 x 25.2  vol 1.3 cm3  wt True
BUILD DONE 38 parts 12 s
```
- Render review (3 iterations rendered, PNGs identical each pass; all 6 files 0.89–1.05 MB, <= 1.5 MB):
  - frontiso: L pose — J1 servo dark in j1_cradle on gray base_link, orange yaw_limit, link1 up to blue J2 drum in orange upper plates, J3 drum at dogleg, orange fore plates to wrist; dark J5 servo sits on top of link4, J6 + gripper servos on the tool axis, gray gear + racks + two flat orange fingers at the tip; no cables/screws visible, nothing floats.
  - backiso: same from behind — lightening holes in upper/fore plates, dark servo bodies in cradle/link4/link5, grip_frame with rack ends and fingers at the tip; exposed flat plates, no covers; nothing floats.
  - side: clean L profile — upper arm vertical, forearm + wrist horizontal at the tip; J5 servo bump on top of the wrist, gear disc + racks + fingers at far end; all parts connected.
  - top: base plate rectangle at one end, arm links in a straight line to the gripper fingers at the other; two flat fingers straddle the centre line, racks on the gear.
  - front: end-on stack — blue J2/J3 drums behind orange plates, wrist + gripper in front with gear meshed between the two racks; nothing floats.
  - cutaway: cradle/pocket interiors visible — J4 servo in j4_cradle, J5 in link4, J6 in link5, gripper servo in grip_frame; rack channels + lips, fingers on rack ends; no gaps or floating parts.
- Files changed: `?? cad/arm2b/` (ap2b.py, p_arm2b.py, build_arm2b.py, arm2b_checks.py, NOTICE.md, BOM.md, rebot_src/ 2x STEP; out/ + __pycache__ excluded from commit), `?? docs/STATUS-arm2b.md`, `?? renders/a2b_*.png` (6)
- BLOCKED: none
- Source: Seeed reBot-DevArm 13bebbf (CERN-OHL-W-2.0), reBot_B601_DM_v1.1_20260425.step; changes in cad/arm2b/NOTICE.md (and cad/arm2/NOTICE.md).
- Assembly: J4 servo into j4_cradle, cradle to fore_r2 with 4x M3x10; link4 on the J4 horn with 4x M3x8; J5 servo into link4 (horn down), link5 on the J5 horn; J6 servo into link5, grip_frame on the J6 horn; gripper servo into grip_frame, gear on its horn (4x M3 countersunk), racks into the channels meshing the gear, fingers glued / M2 to the rack ends. Servo cables daisy-chained J4 -> J5 -> J6 -> gripper.
- Still UNVERIFIED: STS3215 rated torque 0.98 N.m; servo retention in the pockets (no case ears / screws modelled, 0.15 clearance); horn screw thread M3 in the STS3215 horn; gear drilling + countersink, rack-gear mesh and the rack cut (proxies only, mesh not simulated); rack retention by the lips; finger-to-rack joint; J6 horn face at a 63.0 vs the kinematic J6 frame 56.8 (same axis, roll only); fingers 12.1 deep only; J4-J5 37.6 vs rebot-adapt2.md ">= 50"; J4/J5 ROM +-70 (servo cases / bracket hit the forearm at 80); cable route; printed mass factor 0.6.
