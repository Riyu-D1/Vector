# WIRING — knuckle arm (branch arm-knuckle)

Buses: J1–J3 are GIM CAN (CAN H/L + 24 V) daisy-chained on the existing J15
wiring; J4–J6 are STS3215 (12 V + TTL bus) daisy-chained. Route letters are
the cable.py waypoint polylines (A–E); all routes verified CLEAR (CABLE PASS).

| Joint | Device | CAN id / servo id | Cable route | Connector |
|---|---|---|---|---|
| J1 base yaw | Steadywin GIM4305-10 | CAN id 1 | A (base notch → drum → J1 bulkhead slot → service loop) | GIM plug behind cap (CAN H/L + 24 V daisy chain) |
| J2 shoulder | Steadywin GIM4310-36 | CAN id 2 | A (drum → spigot slot → column → riser → knuckle cavity → tunnel → J2 groove) | GIM plug (CAN H/L + 24 V daisy chain) |
| J3 elbow | Steadywin GIM4310-10-GDS | CAN id 3 | B (J2 groove over the top → upper arm → J3 notch) | GIM plug (CAN H/L + 24 V daisy chain) |
| J4 wrist pitch | Feetech STS3215 | servo id 4 | C (J3 notch → forearm groove → forearm tube → pass → J4 plug zone) | STS3215 TTL plug (12 V + TTL bus daisy chain) |
| J5 wrist roll | Feetech STS3215 | servo id 5 | D (J4 plug zone → channel → cup groove → P1/P2 → pod channel → J5 plug) | STS3215 TTL plug (12 V + TTL bus daisy chain) |
| J6 gripper | Feetech STS3215 | servo id 6 | E (pod channel → pod_front hole → gripper groove → slot → J6 plug) | STS3215 TTL plug (12 V + TTL bus daisy chain) |
