"""render_sheets_r8.py - 3 labelled image sheets for the R8 final pass.

sheet1: the two changed parts, stock vs R8 isometric (l5 loft relief,
        l4 outboard-thickened horn plate + J4-hardware clearance cuts)
sheet2: R8 FEA fields - l5 lip-edge hotspot, l5 flop tensile bound,
        l4 strut-edge keel-down, l4 lateral fin-bearing bound
sheet3: wrist assembly context + print orientations
Run: fea/fea/.venv/bin/python render_sheets_r8.py
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

def shot(stl, png):
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

# ---- sheet 1: parts stock vs R8 ----
pairs = [("w_link5", "stock_w_link5", "fix_w_link5",
          "14.3 cc - swept-envelope loft relief"),
         ("w_link4", "stock_w_link4", "fix_w_link4",
          "17.2 cc - +1.45 mm horn plate, J4 clearance cuts")]
rows = []
for nm, s_, f_, vol in pairs:
    for tag, base in (("stock", s_), ("fix", f_)):
        png = os.path.join(REN, "%s_%s.png" % (tag, nm))
        if not os.path.exists(png) or tag == "fix":
            shot(os.path.join(OUT, base + ".stl"), png)
    rows.append([("%s STOCK" % nm, os.path.join(REN, "stock_%s.png" % nm)),
                 ("%s R8 (%s)" % (nm, vol),
                  os.path.join(REN, "fix_%s.png" % nm))])
grid(rows, "SOMA wrist refinement R8 - changed parts (stock vs R8)",
     os.path.join(REN, "r8_sheet1_parts.png"))

# ---- sheet 2: FEA ----
def fea_shot(vtu, png, warp=25.0, vmax=None):
    g = pv.read(vtu)
    p = pv.Plotter(off_screen=True, window_size=(720, 560))
    kw = {} if vmax is None else {"clim": (0, vmax)}
    p.add_mesh(g.warp_by_vector("DISP", factor=warp), scalars="VM",
               cmap="jet", smooth_shading=False, **kw)
    p.camera_position = "iso"; p.set_background("white")
    p.screenshot(png); p.close()

for tag, vtu in (("l5_r8", "l5_scrann_step1.vtu"),
                 ("l5_r8flop", "l5_scrann_flop_step1.vtu"),
                 ("l4_r8", "l4_scrann_step1.vtu"),
                 ("l4_r8lat", "l4_scrann_lat_step1.vtu"),
                 ("gf_r8", "gf_scrann_step1.vtu")):
    png = FEA + "/%s_iso.png" % tag
    src = os.path.join(FEA, vtu)
    if not os.path.exists(png) and os.path.exists(src):
        fea_shot(src, png, vmax=20.0)

grid([[("l5 R8 scrann p50: lip-edge tau 5.3-6.7 (was funnel 5.3)",
        FEA + "/l5_r8_iso.png"),
       ("l5 R8 _flop p50: lip tensile +16.5 layer-normal",
        FEA + "/l5_r8flop_iso.png")],
      [("l4 R8 scrann p50: strut-edge tau 7.5-9.8 NON-CONVERGED",
        FEA + "/l4_r8_iso.png"),
       ("l4 R8 _lat p50: fin bearing edge tau 21-33 NON-CONVERGED",
        FEA + "/l4_r8lat_iso.png")],
      [("gf R8 scrann p50: tau 3.2 PASS (unchanged)",
        FEA + "/gf_r8_iso.png"), ("", None)]],
     "CalculiX von Mises - R8 decks (true-COM wrenches + self-weight), 0.5 kg class",
     os.path.join(REN, "r8_sheet2_fea.png"))

# ---- sheet 3: assembly + print orientations ----
p = pv.Plotter(off_screen=True, window_size=(1100, 700))
for f in (OUT + "/fix_w_j4_cradle.stl", OUT + "/fix_w_link4.stl",
          OUT + "/fix_w_link5.stl", OUT + "/fix_w_grip_frame.stl",
          OUT + "/fix_tool_grip.stl"):
    p.add_mesh(pv.read(f), color="#c8ccd4", smooth_shading=False)
p.camera_position = "iso"; p.set_background("white")
p.screenshot(os.path.join(REN, "r8_assembly_wrist.png")); p.close()

for nm, el in (("w_link4", -10), ("w_link5", -10)):
    m = pv.read(OUT + "/fix_%s.stl" % nm)
    p2 = pv.Plotter(off_screen=True, window_size=(720, 560))
    p2.add_mesh(m, color="#c8ccd4", smooth_shading=False)
    p2.camera_position = "iso"; p2.camera.elevation = el
    p2.set_background("white")
    p2.screenshot(os.path.join(REN, "r8_%s_print.png" % nm)); p2.close()

grid([[("wrist assembly (R8 parts, W design frame)",
        os.path.join(REN, "r8_assembly_wrist.png"))],
      [("w_link4 print orientation: up=b (layers in a-h plane)",
        os.path.join(REN, "r8_w_link4_print.png")),
       ("w_link5 print orientation: up=h (layers in a-b plane)",
        os.path.join(REN, "r8_w_link5_print.png"))]],
     "Wrist assembly + R8 print orientations",
     os.path.join(REN, "r8_sheet3_assembly.png"))
