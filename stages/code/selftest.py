import frames as f
for j in ("J1", "J2", "J3"):
    print(j, f.bb(f.gim_solid(j)))
for j in ("J4", "J5", "J6"):
    print(j, f.bb(f.servo_solid(j)))
print("J2 pin62", tuple(round(v, 2) for v in f.mod_pt("J2", 12, 62)))
print("J3 out29", tuple(round(v, 2) for v in f.mod_pt("J3", 13.5, 29)))
print("J1 out29", tuple(round(v, 2) for v in f.mod_pt("J1", 13.5, 29)))
print("ycyl", f.bb(f.ycyl(280, 150, 34, 19, 30)), "xcyl", f.bb(f.xcyl(2.8, 150, 54, 150, 298.6)), "zcyl", f.bb(f.zcyl(0, 5.5, 58, 80, 150)))
print("sbox", f.bb(f.sbox("J5", -22, -11, -40.2, -28, -9, 9)))
print("yprism", f.bb(f.yprism([(0, 188), (150, 183), (150, 117), (0, 112)], -74.8, -25)))
print("arc", [tuple(round(v, 2) for v in p) for p in f.arc_pts((0, 150), 32, -27, 180, 0, 90)])
