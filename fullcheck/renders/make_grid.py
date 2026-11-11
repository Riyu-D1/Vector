"""make_grid.py - ALL_PARTS.png overview grid from the per-part renders.

Crops each render's isometric panel and tiles them with a caption bar
(part key + binding SF).  Run after render_one.py has produced all PNGs.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts import PARTS  # noqa: E402

COLS = 5
CELL_W = 380
CAP = 34


def cell(key, caption):
    png = os.path.join(HERE, key + ".png")
    im = Image.open(png)
    w, h = im.size
    iso = im.crop((0, int(0.055 * h), int(0.47 * w), int(0.92 * h)))
    r = CELL_W / iso.width
    iso = iso.resize((CELL_W, int(iso.height * r)))
    out = Image.new("RGB", (CELL_W, iso.height + CAP), "#f4f4f4")
    out.paste(iso, (0, 0))
    d = ImageDraw.Draw(out)
    try:
        fnt = ImageFont.truetype("Menlo.ttc", 16)
    except Exception:
        fnt = ImageFont.load_default()
    d.rectangle([0, iso.height, CELL_W, iso.height + CAP], fill="#222831")
    d.text((8, iso.height + 8), caption, fill="white", font=fnt)
    return out


def main():
    cells = [cell(p["key"], "%s  SF %s" % (p["key"],
                                          p.get("sf_disp", "%g" % p["sf"])))
             for p in PARTS]
    cw, ch = cells[0].size
    rows = (len(cells) + COLS - 1) // COLS
    grid = Image.new("RGB", (COLS * cw, rows * ch), "#f4f4f4")
    for i, c in enumerate(cells):
        grid.paste(c, ((i % COLS) * cw, (i // COLS) * ch))
    out = os.path.join(HERE, "ALL_PARTS.png")
    grid.save(out)
    print(out, grid.size)


if __name__ == "__main__":
    main()
