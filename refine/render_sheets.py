"""render_sheets.py - 3 labelled image sheets for the refinement report.

sheet1: changed parts, stock vs fix isometric (4 pairs)
sheet2: FEA stress fields, stock vs fix (tool_grip + w_grip_frame)
sheet3: weld-repair detail views (w_grip_frame back edge / w_link4 strut)
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
pairs = [("w_grip_frame", "stock_w_grip_frame", "fix_w_grip_frame"),
         ("w_link5", "stock_w_link5", "fix_w_link5"),
         ("w_link4", "stock_w_link4", "fix_w_link4"),
         ("tool_grip", "stock_tool_grip", "fix_tool_grip")]
rows = []
for nm, s_, f_ in pairs:
    for tag, base in (("stock", s_), ("fix", f_)):
        png = os.path.join(REN, "%s_%s.png" % (tag, nm))
        if not os.path.exists(png):
            shot(os.path.join(OUT, base + ".stl"), png)
    rows.append([("%s STOCK" % nm, os.path.join(REN, "stock_%s.png" % nm)),
                 ("%s R-FIXED" % nm, os.path.join(REN, "fix_%s.png" % nm))])
grid(rows, "SOMA D6 wrist refinement - changed parts (stock vs R-fix)", 
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

for tag, vtu, vm in (("l4_r4", FEA + "/l4_scrann_step1.vtu", 20.0),
                     ("l4_r4c", FEA + "/l4_scrann_c0.8_step1.vtu", 20.0),
                     ("l5_r4", FEA + "/l5_scrann_step1.vtu", 20.0),
                     ("l5_r4c", FEA + "/l5_scrann_c0.8_step1.vtu", 20.0)):
    png = FEA + "/%s_iso.png" % tag
    if not os.path.exists(png):
        fea_shot(vtu, png, vmax=vm)

grid([[("w_link4 R4 (collar+rib): scrann filtered 8.1 MPa, |U| 0.36 mm PASS",
        FEA + "/l4_r4_iso.png"),
       ("w_link4 R4 cl0.8 filtered 10.0 MPa (was R3 ~15 tail notch)",
        FEA + "/l4_r4c_iso.png")],
      [("w_link5 R4 (wide plate+longeron): scrann filtered 9.3 MPa PASS",
        FEA + "/l5_r4_iso.png"),
       ("w_link5 R4 cl0.8 ~11.3 MPa (was R3 46.6 still-rising notch)",
        FEA + "/l5_r4c_iso.png")]],
     "CalculiX von Mises - realistic horn-mount BCs (screws+annulus+pilot), 0.5 kg class wrench",
     os.path.join(REN, "sheet2_fea.png"))

# ---- sheet 3: wrist assembly context (world pose) ----
p = pv.Plotter(off_screen=True, window_size=(1100, 700))
import glob
for f in sorted(glob.glob(OUT + "/w_*.stl")) + \
         sorted(glob.glob(os.path.join(HERE, "..", "wrist2", "out", "vendor_sts3215_*.stl"))):
    col = "#c8ccd4" if "vendor" not in f else "#e0a050"
    p.add_mesh(pv.read(f), color=col)
p.camera_position = "iso"; p.set_background("white")
p.screenshot(os.path.join(REN, "assembly_wrist.png")); p.close()
grid([[("wrist assembly (R-fixed parts + vendor servos, world pose)",
        os.path.join(REN, "assembly_wrist.png"))]],
     "Wrist assembly - J4 cradle, link4 fin (J5), link5 keel (J6), grip frame + fingers",
     os.path.join(REN, "sheet3_assembly.png"))
