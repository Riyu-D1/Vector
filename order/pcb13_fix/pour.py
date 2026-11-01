"""GND pour fill computation for the soma carrier board.

Computes filled_polygon point lists per copper layer using build123d
(OCP) booleans: pour = board rect minus keepouts around foreign pads,
tracks, and vias.  GND copper solid-connects.  Each island is emitted
as one KiCad filled_polygon whose holes are merged into the outline
with degenerate bridge edges (the same encoding KiCad writes).

Used by fill_zones.py (post-processor) and gen_pcb.py (emit).
"""

import math

CLE = 0.5          # zone clearance, matches the zone emit
MARGIN = 0.15      # polygon discretization + fp slack on top of CLE
MIN_ISLAND = 10.0  # mm^2, matches island_area_min
VIA_R = 0.35       # emitted route-via pad radius (0.7 mm dia)
STITCH_R = 0.3     # emitted stitch-via pad radius (0.6 mm dia)


def _stadium(x, y, hx, hy, r):
    """Box (hx*hy) inflated by disc radius r, centred at (x,y)."""
    from build123d import Pos, Rectangle, fillet
    s = Pos(x, y) * Rectangle(2 * (hx + r), 2 * (hy + r))
    return fillet(s.vertices(), r)


def _capsule(a, b, r):
    """Segment a->b inflated by disc radius r."""
    from build123d import Axis, Pos, Rectangle, Circle
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    body = Rectangle(L, 2 * r) \
        + Pos(L / 2, 0) * Circle(r) + Pos(-L / 2, 0) * Circle(r)
    return Pos(mx, my) * body.rotate(Axis.Z, ang)


def wire_pts(w, step=0.1):
    """Discretize a build123d wire: line edges contribute only their
    endpoints; arcs/curves are sampled at `step` spacing."""
    from build123d import GeomType, PositionMode
    pts = []
    for e in w.edges():
        is_line = e.geom_type == GeomType.LINE
        n = 2 if is_line else max(3, int(e.length / step) + 1)
        for i in range(n):
            v = e.position_at(i / (n - 1),
                              position_mode=PositionMode.PARAMETER)
            pts.append((v.X, v.Y))
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) \
            + abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def merge_holes(outer, holes):
    """Merge hole rings into the outer contour via degenerate bridges.

    Each hole's rightmost vertex is ray-cast horizontally onto the
    outline; the hit edge is split at the intersection point and the
    hole ring inserted between the two appearances of that point —
    producing a single closed contour with a zero-width slit.
    """
    P = list(outer)
    for H in holes:
        hi = max(range(len(H)), key=lambda i: H[i][0])
        hx, hy = H[hi]
        best = None
        for j in range(len(P)):
            a, b = P[j], P[(j + 1) % len(P)]
            if a[1] == b[1] or (a[1] > hy) == (b[1] > hy):
                continue
            t = (hy - a[1]) / (b[1] - a[1])
            ix = a[0] + t * (b[0] - a[0])
            if ix <= hx:
                continue
            if best is None or ix - hx < best[0]:
                best = (ix - hx, j, ix)
        if best is None:
            continue
        _, j, ix = best
        I = (ix, hy)
        Hr = H[hi:] + H[:hi]
        P = P[:j + 1] + [I] + Hr + [Hr[0]] + [I] + P[j + 1:]
    return P


def fill_polys(layer, board_w, board_h, pads, tracks, vias):
    """Filled contours for the GND pour on `layer` ("F.Cu"/"B.Cu").

    pads:   (x, y, hx, hy, prr, kind, layers, net)
    tracks: (net, width, layer, a, b)
    vias:   (x, y, net, radius)
    Returns a list of point lists, one per kept island.
    """
    from build123d import Pos, Rectangle, Circle, Compound, Vector

    def has_layer(lay, layer):
        return "*.Cu" in lay or layer in lay

    keep = []
    for (px, py, hx, hy, prr, kind, layers, net) in pads:
        if net == "GND" or not has_layer(layers, layer):
            continue
        if kind == "circle":
            keep.append(Pos(px, py) * Circle(prr + CLE + MARGIN))
        else:
            keep.append(_stadium(px, py, hx, hy, CLE + MARGIN))
    for (net, w, l, a, b) in tracks:
        if net == "GND" or l != layer:
            continue
        keep.append(_capsule(a, b, w / 2 + CLE + MARGIN))
    for (vx, vy, net, vr) in vias:
        if net != "GND":
            keep.append(Pos(vx, vy) * Circle(vr + CLE + MARGIN))
    pour = Pos(board_w / 2, board_h / 2) \
        * Rectangle(board_w - 1.0, board_h - 1.0)
    if keep:
        pour = pour - Compound(children=keep)
    # islands that reach no GND copper are dead slivers — drop them so
    # the fill matches what island_removal_mode expects
    gnd_anchors = [(px, py) for (px, py, hx, hy, prr, kind, layers, net)
                   in pads if net == "GND" and has_layer(layers, layer)]
    gnd_anchors += [(vx, vy) for (vx, vy, net, vr) in vias
                    if net == "GND"]
    res = []
    for f in pour.faces():
        if f.area < MIN_ISLAND:
            continue
        if not any(f.intersect(Pos(x, y) * Circle(0.01))
                   for (x, y) in gnd_anchors):
            continue
        outer = wire_pts(f.outer_wire())
        holes = [wire_pts(w) for w in f.inner_wires()]
        res.append(merge_holes(outer, holes))
    return res


def fill_sexp(layer, pts):
    """One filled_polygon element (island), holes already merged."""
    pts_fmt = " ".join(f"(xy {x:.6f} {y:.6f})" for x, y in pts)
    return (f'\t\t(filled_polygon\n\t\t\t(layer "{layer}")\n\t\t\t(pts'
            f'\n\t\t\t\t{pts_fmt}\n\t\t\t)\n\t\t)\n')
