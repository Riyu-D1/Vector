# Stream B status — arm structure (branch arm-rebuild)

Updated: 2026-10-27 ~18:50 local

## Done
- Re-read all spec versions; current plan = ARM_HYBRID_V3.md (this file
  supersedes v2: NO springs/belts; J1-J3 = Stream A cycloidal actuators;
  J4-J6 = STS3215; ~260 mm reach; wrist cluster <=180 g target).
- SO-ARM-102 cloned (real STEPs + URDF). Extracted:
  - True joint axes of follower (world coords): J1 wheel (0,29.05,0) axis Y;
    J2 (·,100,40) axis X; J3 (·,100,-73) X; J4 (·,133.06,62.92) X;
    J5 (-0.05,133.05,119.97) Z.
  - STS3215 servo solid -> cad/arm/reference/sts3215_servo.step
    (45.2 x 24.7 case, 42.5 over wheels, Ø19.2 bosses).
  - Servo mounting: M2 holes on 24.45x20.5 (primary face) and 20.7x20.5
    (back face) — verified against Waveshare ST3215-2D.zip DXF.
- cad/arm/arm_params.py written: placeholder actuator spec (Ø60x70,
  marked ASSUMED), verified servo spec, links 120/100/~55, case
  interface from cad/lib/case.py, joint limits from SO-102.
- cad/arm/NOTICE.md attribution.

## In progress
- Base housing on 6808 turntable + turret + links + wrist + gripper.

## Blocked / waiting
- cad/actuator/INTERFACE.md on arm-actuator branch not published yet;
  using Ø60x70 placeholder per spec. Will adapt when it lands.

## Open items / notes
- Wrist cluster: 3x STS3215 = 165 g alone; the 180 g cluster target is
  unreachable with this servo set — will report real mass (~240 g est).
- l_tool: V3 asks 40 mm J4->tip; a servo-driven jaw needs ~50-55 mm —
  reporting real value (~270 mm total reach).
