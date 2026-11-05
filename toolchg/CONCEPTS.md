# D10 toolchanger - Task 1+2: interface requirements and concepts

All dimensions mm, angles deg.  Verified numbers cite their source;
everything else is tagged `[U]`.

## 1. What must pass through the coupling

Mechanical, between the J6 horn face (a = 62.7 in W) and the tool:

| Load | Value | Source |
| --- | --- | --- |
| Tool weight | ~0.09 kg hanging on the coupling | `tc_analysis.py` tool-swap J6-out |
| Payload moment | 0.5 kg at TCP a = 149.4 (~86.7 mm from horn face) -> up to ~0.42 N·m pitch at the plate | [S final2 payload, W geometry] |
| Wrist torque loads | J6 static ~0.2 N·m; grip-drive gear force ~30 N peak `[U]` | gravity model, STS3215 stall 1.9 N·m at 17 mm gear `[U]` |
| Pull-out | must resist the full payload moment as lug->catch bearing | [D] |
| Repeatable alignment | spigot pilot in bore: radial runout <= ~0.2 mm, angular < ~1 deg | [D] target - print tolerance ~0.15 `[U]` |
| Backlash target | < ~0.5 mm at TCP (~0.3 deg) under finger force | [D] |

Electrical (tool-swap needs it through the coupling):

- `GND`, `+12 V`, `DATA` - the STS3215 half-duplex TTL bus that already
  drives the gripper servo [S soma_arm wiring]
- `SP1`, `SP2` - two spare signal lines for sensors on future tools
- Implemented as 5 pogo pins on the socket floor + arc pads on the
  master spigot tip face (GND arc longest = make-first/break-last) [D]

## 2. Finger-swap vs tool-swap

Two architectures were costed with the tested gravity model
(`soma_arm.gravity`); J6-out masses re-point-massed from the CAD volumes.

| | stock grip | tool-swap | finger-swap |
| --- | --- | --- | --- |
| J6-out mass while gripping | 0.1018 kg | 0.0945 kg | 0.1075 kg |
| J2 torque @ AB pose, 0.5 kg | 3.249 N·m | 3.283 (+0.034) | 3.325 (+0.076) |
| J3 | 1.756 | 1.799 (+0.043) | 1.825 (+0.069) |
| J4 | 0.828 | 0.879 (+0.051) | 0.891 (+0.063) |
| electrical pass-through | - | needs 3+2 pogo | none |
| drive-line through coupling | - | none (servo rides on tool) | must re-mesh gear/rack or flex drive `[U]` |
| works for non-gripper tools | - | yes (pen, camera, suction...) | only finger-type tools |
| extra cost per tool | - | 1x STS3215 (~GBP 6-7 `[U]`) + pogo | none |

Notes:

- Tool-swap J6-out is *lighter* than stock (94.5 vs 101.8 g) because the
  socket+body print is slimmer than w_grip_frame's horn plate/cage and
  the modelled rack/finger stock masses were conservative.  The payload
  bound at the reach pose *improves* ~0.007 kg (d_tau_J2 -0.025 N·m).
- Finger-swap is *heavier* during gripping (the whole mechanism stays
  plus the master plate) and - more importantly - needs a rotary
  drive-through (re-meshing the gear/rack blind at every dock is
  error-prone and sets finger backlash directly).
- Tool-swap's only real cost is the powered-contact reliability [U
  bench test] and one extra servo per powered tool.

**Decision: TOOL-SWAP.**  Each tool carries its own servo where powered;
the coupling only passes mechanics + 5 pogo lines.  Passive tools (pen,
hook, camera) skip the servo entirely and still dock.

## 3. Concepts

### Concept A - 3-lug bayonet twist-lock on the J6 axis (BUILT)

```
        tool socket (ring + 3 catches + floor)        master (on J6 horn)
        ___________________________                       _______
       /   ring r23  catch r13.2   \                     | plate |
      |   _______________________   |        _______     | r15   |
      |  |  bore r18.2  pocket    | |  <==   | spigot|===|_______|
      |  | floor + pogos a76-78.4 | |   +a   | r13   | lugs r17.3
       \_|_______________________|_/         |_______| arc 32 @ 3x
         groove r20 72.25-77.25 (rack slot lands here)
    dock: slide +a, twist J6 +60 deg -> lugs under catches,
    spring-ball detent clicks into lug dimple at lock.
```

J6 roll does everything: insert -> twist -> detent click.  No extra
actuator, no release pin - unlock = twist -60 and pull out.  Rack fork
in the OD groove keeps the tool steady; key notch sets the roll phase
so the lugs meet the gaps blind.

### Concept B - kinematic 3-groove/3-ball seat + spring latch

```
      tool cone/ball seats on 3 V-grooves (exact constraint)
      cam latch hooks the plate edge; release = push-pin cam on the rack
      ____________________________________________
      |  V   V   V   (3 grooves r20, 120 deg)      |
      |  o   o   o   (3 balls/dowels on master)    |
      |_____latch hook over edge -> cam push______|
```

Repeatability is the best of the three (closed-form kinematic seat,
~few um with lapped hardware), but the seat can't carry the 0.42 N·m
payload moment on a 40 mm plate without a large preload spring, and
the rack needs a *moving* release cam that the arm must find and press
blind - a 4th degree of the dock problem.

### Concept C - magnetic kinematic mount + pogo pins

```
      3x N35 disc magnets (master) <-> steel pole plates (tool)
      ball-in-V seats locate; pogo block bridges power/data
      dock: magnets pull in; release: J6 peels the plate off an edge
```

Magnet check: 3x N35 Ø10x4 pull ~6-9 kgf axial combined `[U]`, plenty
for the 4.9 N payload weight - BUT the payload moment loads the mount
in *peel*: 0.42 N·m on a ~0.023 m lever is ~18 N peeling force at the
plate edge, and magnet pull degrades ~quadratically once a gap opens.
SF >= 2 on peel still wants a mechanical back-up latch, which puts us
back at concept A's latch plus magnet cost.  Also: magnets near the
TTL bus and servo magnetics is a reliability question `[U]`, and the
pacemaker/electronics warning lands in STATUS.

### Trade table

| | A - bayonet twist | B - kinematic+latch | C - magnetic |
| --- | --- | --- | --- |
| added mass (master side) | 5.6 g | ~6 g `[U]` | ~10 g `[U]` |
| added length (TCP shift) | +12 mm | ~+10 mm `[U]` | ~+8 mm `[U]` |
| printed parts (coupling) | 2 plates | 2 plates + latch | 2 plates + mag pockets |
| non-printed parts | spring-ball plunger, 5 pogo, 4 M2 screws | 3 dowels/balls, spring, latch pin, cam, 5 pogo | 3 magnets, steel plates, 5 pogo |
| repeatability | ~0.2 mm pilot fit | ~0.05 mm `[U]` | ~0.05 mm `[U]` |
| parts cost | ~GBP 3-5 `[U]` | ~GBP 6-10 `[U]` | ~GBP 8-12 `[U]` |
| printability | face-down both, no supports | good | good |
| failure modes | lug/catch wear, detent gumming | latch bounce, cam alignment | peel-off under moment, magnet corrosion, EMI |
| actuator-free dock | yes - J6 twist | needs rack-side release cam | yes - magnetic self-seat |
| unlock motion | J6 roll -60 | push-pin against rack cam | J6 peel + pull |

**Pick: Concept A** - the only one that locks positively with arm motion
alone (no rack-side moving parts), carries the payload moment in bearing
not friction, keeps every tool compatible (passive or powered), and is
the lightest.  Its known weakness - repeatability set by the spigot fit
rather than a kinematic seat - is acceptable at the ~0.2 mm target and
can be improved later by shrinking TC_SPIGOT/TC_RING fits or adding
conical seat faces.

## 4. Selected design in one breath

- `tc_master` on the J6 horn: Ø30 horn plate (same 4-screw pattern as
  w_grip_frame) + r13 spigot + three 32-deg lugs.
- `tc_plate` on every tool: ring with three 60-deg catches (chamfered
  lead faces, support-free print), floor holding 5 pogo pins,
  circumferential dock groove + key notch.
- `tc_rack`: 4-slot fork rack; tools drop in keel-down, groove on the
  slot, key in the notch -> repeatable roll phase for the blind dock.
- Dock sequence: master at ENTRY_REL -12 -> slide +a to seat -> J6 +60
  -> ball detent clicks -> payload.  Release: J6 -60 -> pull -a -> lift
  tool out of the slot by +z...  (pickup is the mirror.)
- Verified by `tc_checks.py`: entry sweep 0.00 mm3, twist sweep 0.00
  mm3, pull-out capture 1368 mm3 interference (captured), rack seat
  8.4 mm3 (key tolerance), drop-in 0.00 mm3.
