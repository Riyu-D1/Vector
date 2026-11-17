"""Stage A1c patch (tested by the designer 28 Oct 2026 on a copy of 87508f4). Run ONCE from cad/act2:
   $PY ~/Vector/stages/code/act2c/patch_a1c.py
Motor turned round (bell top -> gearbox, stator base -> housing back plate); hub = one-piece rotor
flange + cams bolted to the bell top with 2x M3 on the 34 mm prop-hole circle; magnet on a printed
mag_puck on the shaft-end M3; mid_plate, shaft grip, grub screw and radial CSK screws removed.
Prints one 'PATCHED ...' line per edit, then 'PATCH a1c OK'. AssertionError = a line was not found
exactly once (running it twice fails on purpose)."""
import re

def rep_line(s, prefix, new):            # replace the ONE line starting with prefix (new='' deletes it)
    lines = s.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, f"line not found exactly once: {prefix}"
    lines[idx[0]:idx[0] + 1] = new.split("\n") if new else []
    print(f"PATCHED ap.py: {(new.splitlines() or ['(deleted) ' + prefix])[0][:70]}")
    return "\n".join(lines)

def rep_func(s, name, new):              # replace a whole top-level def (up to the next top-level line)
    m = re.search(rf"^def {name}\(.*?(?=^\S)", s, flags=re.S | re.M)
    assert m and s.count(f"\ndef {name}(") == 1, f"def {name} not found exactly once"
    s = s[:m.start()] + new + s[m.end():]
    print(f"PATCHED p_act.py: def {name}" + (" (deleted)" if not new else ""))
    return s

# ---------------- ap.py ----------------
a = open("ap.py").read()
a = rep_line(a, "MOT_D = 44.5; MOT_H = 22.0;",
 "MOT_D = 44.5; MOT_H = 19.0; MOT_MASS_G = 85     # [U] A1c: stator base face -> bell top (community STEP 19.0; Tarot spec 22.0 maybe incl. prop seat)\n"
 "DZ = MOT_H - 19.0               # A1c: shifts every part in front of the motor. MOT_H 22.0 -> DZ 3.0 -> length 58.0 (gate limit 55)")
a = rep_line(a, "SHAFT_OUT = ",
 "ROTOR_PCD = 34.0; ROTOR_ANG = (90.0, 270.0)      # [S Tarot prop mount 34 mm, Dongil adapter +-17] [U positions on the real bell]\n"
 "ROTOR_HOLE = 3.4; ROTOR_CB_D = 6.2; ROTOR_CB_H = 1.9   # [D] A1c: 2x M3x5 ISO 7380 hub -> bell top [U thread depth in the bell]")
a = rep_line(a, "STATOR_HOLE_D = ",
 "MOT_PLATE = 3.0; MOT_CB_D = 6.2  # [D] A1c: back plate under the stator screw heads; 3x M3x6 ISO 7380 from the back [U thread depth]")
a = rep_line(a, "Z_MAG = ",
 "Z_MAG = (4.7, 7.2)              # [D] A1c: 6x2.5 magnet in mag_puck, faces the AS5600 (gap 0.95 [U chip height])\n"
 "Z_STATOR = 10.2                 # [D] A1c: stator base face on the housing back plate\n"
 "Z_PUCK = (4.7, Z_STATOR + 0.5)  # [D] A1c: mag_puck; its d8 nose enters the stator washer recess by 0.5 [U]\n"
 "PUCK_D = 12.0; PUCK_NOSE = (8.0, 0.8); PUCK_HOLE = 3.2; PUCK_POCKET = (6.05, 4.15)  # [S Dongil puck 12x6, pocket 6.05, hole 3.2] pocket depth = magnet 2.5 + M3 button head 1.65\n"
 "PUCK_CAV_D = 13.0               # [D] A1c: housing cavity around the spinning puck\n"
 "MOT_RECESS = (9.1, 0.6)         # [S BOPP STEP: retaining washer d9.07, 0.5 inside the base] vendor_motor proxy only")
a = rep_line(a, "Z_MOTOR = ", "Z_MOTOR = (Z_STATOR, Z_STATOR + MOT_H)   # [D] A1c: stator base -> bell top (bell top faces the gearbox)\n"
 "Z_ADAPT = (Z_MOTOR[1], Z_MOTOR[1] + 4.0)  # [D] A1c: hub rotor flange, 4.0 thick, clamped on the bell top\n"
 "ADAPT_L = 44.0; ADAPT_W = 20.0; ADAPT_CTR = (3.0, 4.0)  # [S Dongil adapter 44x20 bar] ends trimmed to d44; centre clearance d, depth [U bell centre]")
a = rep_line(a, "Z_MID = ", "")
for k, v in [("Z_DISC1", "(33.8 + DZ, 37.8 + DZ)"), ("Z_DISC2", "(38.1 + DZ, 42.1 + DZ)"),
             ("Z_RINGPIN", "(33.5 + DZ, 43.5 + DZ)"), ("Z_HUB", "(Z_ADAPT[0], 47.2 + DZ)"),
             ("Z_CARRIER_PLATE", "(42.4 + DZ, 45.4 + DZ)"), ("Z_PIN_RING", "(43.5 + DZ, 45.4 + DZ)"),
             ("Z_6808", "(45.4 + DZ, 52.4 + DZ)"), ("Z_SPIGOT", "(45.4 + DZ, 52.4 + DZ)"),
             ("Z_FRONT_RING", "(52.4 + DZ, 54.4 + DZ)"), ("Z_FLANGE", "(52.4 + DZ, 55.0 + DZ)"),
             ("Z_OUTPIN", "(34.0 + DZ, 46.0 + DZ)"), ("Z_685", "(42.4 + DZ, 47.4 + DZ)")]:
    old = [l for l in a.split("\n") if l.startswith(k + " = ")]
    assert len(old) == 1, k
    cmt = old[0].split("#", 1)[1] if "#" in old[0] else " [D]"
    cmt = {"Z_RINGPIN": " [D] A1c: ring pins (10 long) stand on the blind housing groove floors",
           "Z_HUB": " [D] A1c: rotor flange Z_ADAPT, cam1 to Z_CAM_SPLIT, cam2 to Z_STUB0, stub to 47.2"}.get(k, cmt)
    a = rep_line(a, k + " = ", f"{k} = {v}  #{cmt}")
a = rep_line(a, "Z_CAM_SPLIT = ", "Z_CAM_SPLIT = 37.95 + DZ; Z_STUB0 = 42.25 + DZ")
a = rep_line(a, "BORE_MOTOR = ", "BORE_MOTOR = 45.4               # [D] A1c: Z_STATOR .. Z_RINGPIN[0]")
a = rep_line(a, "CSK_Z = ", "")
a = rep_line(a, "CSK_D = ", "")
a = rep_line(a, "# ---------- mid_plate", "")
a = rep_line(a, "MID_D = ", "")
a = rep_line(a, "MID_CB_D = ", "")
a = rep_line(a, "MID_GROOVE = ", "WIRE_GROOVE = (4.0, 1.5)        # [D] A1c: phase-wire groove in the back-plate front face at WIRE_ANG: width, depth [U wire exit]")
a = rep_line(a, "KEY_PINS = ", "")
a = rep_line(a, "KEY_CLR = ", "")
a = rep_line(a, "HUB_BORE = ", "")
a = rep_line(a, "HUB_BORE_L = ", "")
a = rep_line(a, "GRUB_Z = ", "")
a = rep_line(a, "# chip face at z", "# chip face at z ~3.75 [U SOIC-8 1.75 tall] -> magnet gap 0.95 (AS5600 wants 0.5-3) [U]")
open("ap.py", "w").write(a)

# ---------------- p_act.py ----------------
p = open("p_act.py").read()
p = rep_func(p, "radial_hole", "")
p = rep_func(p, "radial_csk", "")
p = rep_func(p, "housing", '''def housing():
    N, NP, R, RP, E = cyc.gear()
    h = zcyl(0, 0, ap.OD, 0, ap.Z_FRONT_RING[1])
    h -= zcyl(0, 0, ap.BORE_MOTOR, ap.Z_STATOR, ap.Z_RINGPIN[0])          # A1c: motor bore down to the back plate
    h -= zcyl(0, 0, ap.BORE_PIN, ap.Z_RINGPIN[0], ap.Z_RINGPIN[1])
    h -= zcyl(0, 0, ap.SEAT_6808, ap.Z_PIN_RING[0], ap.Z_FRONT_RING[1] + 0.01)
    h -= zcyl(0, 0, ap.PUCK_CAV_D, ap.Z_BACK[1] - 0.01, ap.Z_STATOR + 0.01)   # A1c: mag_puck cavity
    for k in range(NP):       # blind grooves: the ring pins stand on their floors at Z_RINGPIN[0]
        x, y = pol(R, 360.0 * k / NP)
        h -= zcyl(x, y, 2 * RP + 0.05, ap.Z_RINGPIN[0], ap.Z_RINGPIN[1])
    h -= Pos(0, 0, ap.Z_ENC_POCKET[1] / 2 - 0.005) * \\
        Box(ap.ENC_W, ap.ENC_W, ap.Z_ENC_POCKET[1] + 0.01)        # AS5600 pocket, open to back
    h -= zcyl(0, 0, ap.ENC_WINDOW_D, 1.7, ap.Z_BACK[1] + 0.01)   # chip window
    for k in range(ap.LINK_N):
        x, y = pol(ap.LINK_PCD / 2, ap.LINK_ANG0 + 60 * k)
        h -= zcyl(x, y, ap.LINK_PILOT_D, -0.01, ap.LINK_PILOT_L)
    for a in ap.MOT_SCREW_ANG:  # A1c: stator base screws from the back face, heads in counterbores
        x, y = pol(ap.MOT_PCD / 2, a)
        h -= zcyl(x, y, 3.4, -0.01, ap.Z_STATOR + 0.01)
        h -= zcyl(x, y, ap.MOT_CB_D, -0.01, ap.Z_STATOR - ap.MOT_PLATE)
    z0, z1 = ap.Z_BACK[1] - 0.01, ap.Z_STATOR + 0.01              # axial wire channel -> motor bore
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((ap.WIRE_R[0] + ap.WIRE_R[1]) / 2, 0, (z0 + z1) / 2) * \\
        Box(ap.WIRE_R[1] - ap.WIRE_R[0], ap.WIRE_W, z1 - z0)
    r0, r1 = ap.PUCK_CAV_D / 2 - 0.01, ap.BORE_MOTOR / 2 + 0.1   # A1c: wire groove in the back-plate front face
    z0, z1 = ap.Z_STATOR - ap.WIRE_GROOVE[1], ap.Z_STATOR + 0.01
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((r0 + r1) / 2, 0, (z0 + z1) / 2) * Box(r1 - r0, ap.WIRE_GROOVE[0], z1 - z0)
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((22.0 + ap.OD / 2 + 1) / 2, 0, (ap.NOTCH_Z[0] + ap.NOTCH_Z[1]) / 2) * \\
        Box(ap.OD / 2 + 1 - 22.0, ap.NOTCH_W, ap.NOTCH_Z[1] - ap.NOTCH_Z[0])   # side notch
    r0, r1 = ap.ENC_W / 2 - 0.5, 22.5                            # back-face groove pocket -> notch
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((r0 + r1) / 2, 0, (ap.ENC_GROOVE_D - 0.01) / 2) * \\
        Box(r1 - r0, ap.ENC_GROOVE_W, ap.ENC_GROOVE_D + 0.01)
    return h


''')
p = rep_func(p, "mid_plate", '''def mag_puck():   # A1c: magnet holder on the shaft-end M3 at the stator base (Dongil motor_and_magnet_holder)
    p = zcyl(0, 0, ap.PUCK_D, ap.Z_PUCK[0], ap.Z_PUCK[1] - ap.PUCK_NOSE[1])
    p += zcyl(0, 0, ap.PUCK_NOSE[0], ap.Z_PUCK[1] - ap.PUCK_NOSE[1], ap.Z_PUCK[1])
    p -= zcyl(0, 0, ap.PUCK_POCKET[0], ap.Z_PUCK[0] - 0.01, ap.Z_PUCK[0] + ap.PUCK_POCKET[1])
    p -= zcyl(0, 0, ap.PUCK_HOLE, ap.Z_PUCK[0], ap.Z_PUCK[1] + 0.01)
    return p


''')
p = rep_func(p, "hub", '''def hub():   # A1c: one piece = rotor flange (2x M3 into the bell top) + cam1 + cam2 + front stub
    N, NP, R, RP, E = cyc.gear()
    z0, z1 = ap.Z_ADAPT
    h = zcyl(0, 0, ap.ADAPT_L, z0, z1) & (Pos(0, 0, (z0 + z1) / 2) * Box(ap.ADAPT_W, ap.ADAPT_L + 1, z1 - z0))
    h += zcyl(E, 0, ap.CAM_D, z0, ap.Z_CAM_SPLIT)
    h += zcyl(-E, 0, ap.CAM_D, ap.Z_CAM_SPLIT, ap.Z_STUB0)
    h += zcyl(0, 0, ap.STUB_D, ap.Z_STUB0, ap.Z_HUB[1])
    for a in ap.ROTOR_ANG:
        x, y = pol(ap.ROTOR_PCD / 2, a)
        h -= zcyl(x, y, ap.ROTOR_HOLE, z0 - 0.01, z1 + 0.01)
        h -= zcyl(x, y, ap.ROTOR_CB_D, z1 - ap.ROTOR_CB_H, z1 + 0.01)
    h -= zcyl(0, 0, ap.ADAPT_CTR[0], z0 - 0.01, z0 + ap.ADAPT_CTR[1])
    return h


''')
p = rep_func(p, "vendor_motor", '''def vendor_motor():   # A1c: stator base on the back plate, bell top toward the gearbox
    return zcyl(0, 0, ap.MOT_D, *ap.Z_MOTOR) - \\
        zcyl(0, 0, ap.MOT_RECESS[0], ap.Z_STATOR - 0.01, ap.Z_STATOR + ap.MOT_RECESS[1])


''')
assert p.count('"mid_plate": mid_plate') == 1
p = p.replace('"mid_plate": mid_plate', '"mag_puck": mag_puck'); print("PATCHED p_act.py: PARTS mid_plate -> mag_puck")
open("p_act.py", "w").write(p)

# ---------------- act_checks.py ----------------
c = open("act_checks.py").read()
assert c.count('"mid_plate"') == 1
open("act_checks.py", "w").write(c.replace('"mid_plate"', '"mag_puck"')); print("PATCHED act_checks.py: P mid_plate -> mag_puck")
print("PATCH a1c OK")
