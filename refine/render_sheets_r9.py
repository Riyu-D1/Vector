"""render_sheets_r9.py - 3 labelled image sheets for the R9 final pass.

sheet1: the changed parts, stock vs R9 isometric (l4 +b yoke arm +
        J4-axis journal boss, cradle pin seat, w_link5, w_grip_frame)
sheet2: R9 FEA fields - l4 journal-supported roll/lat, cradle boltface,
        plus the R8 horn-only bound for contrast
sheet3: wrist assembly context + the yoke/pin detail + print
        orientations
Run: fea/fea/.venv/bin/python render_sheets_r9.py
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

def shot(stl, png, az=25, el=-18):
    p = pv.Plotter(off_screen=True, window_size=(720, 560))
    p.add_mesh(pv.read(stl), color="#c8ccd4", smooth_shading=False,
               specular=0.2)
    p.camera_position = "iso"
    p.camera.azimuth = az; p.camera.elevation = el
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

# ---- sheet 1: parts stock vs R9 ----
pairs = [("w_link4", "stock_w_link4", "fix_w_link4",
          "17.4 cc - +b yoke arm + J4-axis journal boss"),
         ("w_j4_cradle", "stock_w_j4_cradle", "fix_w_j4_cradle",
          "15.6 cc - d3 pin seat in pad+flange"),
         ("w_link5", "stock_w_link5", "fix_w_link5",
          "14.3 cc - loft relief (R8)"),
         ("w_grip_frame", "stock_w_grip_frame", "fix_w_grip_frame",
          "20.3 cc - unchanged interface")]
rows = []
for nm, s_, f_, vol in pairs:
    for tag, base in (("stock", s_), ("fix", f_)):
        png = os.path.join(REN, "r9_%s_%s.png" % (tag, nm))
        if not os.path.exists(png) or tag == "fix":
            shot(os.path.join(OUT, base + ".stl"), png)
    rows.append([("%s STOCK" % nm, os.path.join(REN, "r9_stock_%s.png" % nm)),
                 ("%s R9 (%s)" % (nm, vol),
                  os.path.join(REN, "r9_fix_%s.png" % nm))])
# the pin, two views
shot(OUT + "/fix_wrist_pin.stl", os.path.join(REN, "r9_pin.png"))
rows.append([("wrist_pin R9 (d3 x 17.1 steel dowel)",
              os.path.join(REN, "r9_pin.png")), ("", None)])
grid(rows, "SOMA wrist refinement R9 - parts (stock vs R9 yoke redesign)",
     os.path.join(REN, "r9_sheet1_parts.png"))

# ---- sheet 2: FEA ----
def fea_shot(vtu, png, warp=25.0, vmax=None):
    g = pv.read(vtu)
    p = pv.Plotter(off_screen=True, window_size=(720, 560))
    kw = {} if vmax is None else {"clim": (0, vmax)}
    p.add_mesh(g.warp_by_vector("DISP", factor=warp), scalars="VM",
               cmap="jet", smooth_shading=False, **kw)
    p.camera_position = "iso"; p.set_background("white")
    p.screenshot(png); p.close()

for tag, vtu in (("l4_r9_roll", "l4_scrann_roll_step1.vtu"),
                 ("l4_r9_rollj", "l4_scrjh_roll_step1.vtu"),
                 ("l4_r9_lat", "l4_scrann_lat_step1.vtu"),
                 ("l4_r9_latj", "l4_scrjh_lat_step1.vtu"),
                 ("l4_r9_keel", "l4_scrj_step1.vtu"),
                 ("cr_r9", "cr_boltface_step1.vtu"),
                 ("l5_r9", "l5_scrann_step1.vtu"),
                 ("gf_r9", "gf_scrann_step1.vtu")):
    png = FEA + "/%s_iso.png" % tag
    src = os.path.join(FEA, vtu)
    if not os.path.exists(png) and os.path.exists(src):
        fea_shot(src, png, vmax=20.0)

grid([[("l4 R9 scrann roll p50: horn-only bound (R8 baseline)",
        FEA + "/l4_r9_roll_iso.png"),
       ("l4 R9 scrjh roll p50: +journal half-circle support",
        FEA + "/l4_r9_rollj_iso.png")],
      [("l4 R9 scrann lat p50: horn-only bound",
        FEA + "/l4_r9_lat_iso.png"),
       ("l4 R9 scrjh lat p50: +journal half-circle support",
        FEA + "/l4_r9_latj_iso.png")],
      [("l4 R9 scrj p50 keel: journal full-circle",
        FEA + "/l4_r9_keel_iso.png"),
       ("cr R9 boltface p50: pin-seat load path",
        FEA + "/cr_r9_iso.png")],
      [("l5 R9 scrann p50", FEA + "/l5_r9_iso.png"),
       ("gf R9 scrann p50", FEA + "/gf_r9_iso.png")]],
     "CalculiX von Mises - R9 decks (true-COM wrenches + self-weight), 0.5 kg class",
     os.path.join(REN, "r9_sheet2_fea.png"))

# ---- sheet 3: assembly + yoke detail + print orientations ----
p = pv.Plotter(off_screen=True, window_size=(1100, 700))
for f in (OUT + "/w_j4_cradle.stl", OUT + "/w_link4.stl",
          OUT + "/w_link5.stl", OUT + "/w_grip_frame.stl",
          OUT + "/wrist_pin.stl"):
    if os.path.exists(f):
        p.add_mesh(pv.read(f), color="#c8ccd4", smooth_shading=False)
p.camera_position = "iso"; p.set_background("white")
p.screenshot(os.path.join(REN, "r9_assembly_wrist.png")); p.close()

# yoke close-up: cradle + l4 + pin, posed
p = pv.Plotter(off_screen=True, window_size=(720, 560))
for f, c in ((OUT + "/w_j4_cradle.stl", "#c8ccd4"),
             (OUT + "/w_link4.stl", "#9fc6e8"),
             (OUT + "/wrist_pin.stl", "#e8a15c")):
    if os.path.exists(f):
        p.add_mesh(pv.read(f), color=c, smooth_shading=False)
p.camera_position = "iso"; p.camera.elevation = -12
p.set_background("white")
p.screenshot(os.path.join(REN, "r9_yoke_detail.png")); p.close()

for nm, el in (("w_link4", -10), ("w_j4_cradle", -10)):
    m = pv.read(OUT + "/fix_%s.stl" % nm)
    p2 = pv.Plotter(off_screen=True, window_size=(720, 560))
    p2.add_mesh(m, color="#c8ccd4", smooth_shading=False)
    p2.camera_position = "iso"; p2.camera.elevation = el
    p2.set_background("white")
    p2.screenshot(os.path.join(REN, "r9_%s_print.png" % nm)); p2.close()

grid([[("wrist assembly R9 (posed W frame)",
        os.path.join(REN, "r9_assembly_wrist.png")),
       ("yoke detail: cradle pad + l4 journal boss + d3 pin",
        os.path.join(REN, "r9_yoke_detail.png"))],
      [("w_link4 print orientation: up=b (layers in a-h plane)",
        os.path.join(REN, "r9_w_link4_print.png")),
       ("w_j4_cradle print orientation: up=b",
        os.path.join(REN, "r9_w_j4_cradle_print.png"))]],
     "Wrist assembly + R9 yoke + print orientations",
     os.path.join(REN, "r9_sheet3_assembly.png"))
