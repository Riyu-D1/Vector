"""render_sheets.py - 3 labelled image sheets for the R7 refinement report.

sheet1: changed parts, stock vs fix isometric (5 pairs, R7 volumes noted)
sheet2: R7 FEA stress fields (l5 r6-notch corner, floor-only bound on the
        deepened aft block, gf v3 notch + lateral bound, cl0.8 convergence)
sheet3: wrist assembly context + w_link5 print orientation (up=h)
Run: fea/.venv/bin/python render_sheets.py
"""
import os
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FEA = os.path.join(HERE, "fea")
REN = os.path.join(HERE, "renders")
os.makedirs(REN, exist_ok=True)
pv.OFF_SCREEN = True

def shot(stl, png, cam=(1.35, -1.1, 0.9)):
    p = pv.Plotter(off_screen=True, window_size=(720, 560))
    p.add_mesh(pv.read(stl), color="#c8ccd4", smooth_shading=False,
               specular=0.2)
    p.camera_position = "iso"
    p.camera.azimuth = 25; p.camera.elevation = -18
    p.set_background("white")
    p.screenshot(png)
    p.close()

def grid(cells, title, dest, cw=720, ch=560, pad=8, hdr=54, sub=28):
    cols = max(len(r) for r in cells)
    W = cols * cw + (cols + 1) * pad
    H = hdr + sum(ch + sub + pad for r in cells) + pad
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
        f2 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 21)
    except Exception:
        f = f2 = ImageFont.load_default()
    dr.text((pad + 4, 12), title, fill="black", font=f)
    y = hdr
    for r in cells:
        x = pad
        for label, png in r:
            dr.text((x + 4, y), label, fill="black", font=f2)
            if png and os.path.exists(png):
                img.paste(Image.open(png).resize((cw, ch)), (x, y + sub))
            x += cw + pad
        y += ch + sub + pad
    img.save(dest)
    print("wrote", dest)

# ---- sheet 1: parts stock vs fix ----
# parts whose geometry changed in R7 -> force re-render (stale R6 pngs)
R7_CHANGED = {"w_grip_frame", "w_link5"}
pairs = [("w_grip_frame", "stock_w_grip_frame", "fix_w_grip_frame", "20.3 cc"),
         ("w_link5", "stock_w_link5", "fix_w_link5", "14.2 cc"),
         ("w_link4", "stock_w_link4", "fix_w_link4", "16.8 cc"),
         ("w_j4_cradle", "stock_w_j4_cradle", "fix_w_j4_cradle", "16.3 cc"),
         ("tool_grip", "stock_tool_grip", "fix_tool_grip", "24.7 cc")]
rows = []
for nm, s_, f_, vol in pairs:
    for tag, base in (("stock", s_), ("fix", f_)):
        png = os.path.join(REN, "%s_%s.png" % (tag, nm))
        if not os.path.exists(png) or (tag == "fix" and nm in R7_CHANGED):
            shot(os.path.join(OUT, base + ".stl"), png)
    rows.append([("%s STOCK" % nm, os.path.join(REN, "stock_%s.png" % nm)),
                 ("%s R7-FIXED (%s)" % (nm, vol),
                  os.path.join(REN, "fix_%s.png" % nm))])
grid(rows, "SOMA wrist refinement R7 - changed parts (stock vs R-fix)",
     os.path.join(REN, "sheet1_parts.png"))

# ---- sheet 2: FEA (R3 horn-mount models) ----
def fea_shot(vtu, png, warp=25.0, vmax=None):
    g = pv.read(vtu)
    p = pv.Plotter(off_screen=True, window_size=(720, 560))
    kw = {} if vmax is None else {"clim": (0, vmax)}
    p.add_mesh(g.warp_by_vector("DISP", factor=warp), scalars="VM",
               cmap="jet", smooth_shading=False, **kw)
    p.camera_position = "iso"; p.set_background("white")
    p.screenshot(png); p.close()

for tag, vtu, vm in (("l5_r7", FEA + "/l5_scrann_step1.vtu", 20.0),
                     ("l5_r7latf", FEA + "/l5_scrann_latf_step1.vtu", 20.0),
                     ("l5_r7flop", FEA + "/l5_scrann_flop_step1.vtu", 20.0),
                     ("gf_r7", FEA + "/gf_scrann_step1.vtu", 20.0),
                     ("gf_r7lat", FEA + "/gf_scrann_lat_step1.vtu", 20.0),
                     ("l5_r7c", FEA + "/l5_scrann_c0.8_step1.vtu", 20.0)):
    png = FEA + "/%s_iso.png" % tag
    if not os.path.exists(png) and os.path.exists(vtu):
        fea_shot(vtu, png, vmax=vm)

grid([[("l5 R7 scrann (-h): notch corner tau 5.3, VM 9.1",
        FEA + "/l5_r7_iso.png"),
       ("l5 R7 _latf floor-only bound: aft block -7.5 (was -8.4)",
        FEA + "/l5_r7latf_iso.png")],
      [("l5 R7 _flop worst combined: tau 6.1 at corner",
        FEA + "/l5_r7flop_iso.png"),
       ("gf R7 scrann: notch -6.7 (was -12 R3 / -10.6 R7v1)",
        FEA + "/gf_r7_iso.png")],
      [("gf R7 _lat bound: aft-cage VM 14.8 conservative",
        FEA + "/gf_r7lat_iso.png"),
       ("l5 R7 cl0.8 convergence: corner tau 5.7",
        FEA + "/l5_r7c_iso.png")]],
     "CalculiX von Mises - realistic horn-mount BCs (screws+annulus+pilot), 0.5 kg class wrench",
     os.path.join(REN, "sheet2_fea.png"))

# ---- sheet 3: wrist assembly context (W frame) + l5 orientation ----
# all printed wrist parts share the W design frame -> the fix_* STLs
# assemble as-is (the committed w_*.stl posed files are a stale R1-era
# arm pose and are NOT used).
p = pv.Plotter(off_screen=True, window_size=(1100, 700))
for f in (OUT + "/fix_w_j4_cradle.stl", OUT + "/fix_w_link4.stl",
          OUT + "/fix_w_link5.stl", OUT + "/fix_w_grip_frame.stl",
          OUT + "/fix_tool_grip.stl"):
    p.add_mesh(pv.read(f), color="#c8ccd4", smooth_shading=False)
p.camera_position = "iso"; p.set_background("white")
p.screenshot(os.path.join(REN, "assembly_wrist.png")); p.close()

# w_link5 in its R5/R6 print orientation (up=h: rests on the cage-back
# faces, layers in the a-b plane -> the J5-plate bending stresses are
# in-layer; orientation changes the allowable mapping, not the stress)
m = pv.read(OUT + "/fix_w_link5.stl")          # W-frame STL: +z IS the part's +h
p2 = pv.Plotter(off_screen=True, window_size=(720, 560))
p2.add_mesh(m, color="#c8ccd4", smooth_shading=False)
p2.camera_position = "iso"; p2.camera.elevation = -10
p2.set_background("white")
p2.screenshot(os.path.join(REN, "l5_print_up_h.png")); p2.close()

grid([[("wrist assembly (R7 parts, W design frame)",
        os.path.join(REN, "assembly_wrist.png")),
       ("w_link5 print orientation: up=h (layers in a-b plane)",
        os.path.join(REN, "l5_print_up_h.png"))]],
     "Wrist assembly - J4 cradle, link4 fin (J5), link5 keel (J6), grip frame + fingers",
     os.path.join(REN, "sheet3_assembly.png"))
