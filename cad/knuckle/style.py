from build123d import Axis, fillet
from frames import gbox

def rbox(x0, x1, y0, y1, z0, z1, r, axis=None):
    """gbox with outer edges rounded by r. axis 'X','Y','Z' = only edges parallel to that axis; None = all 12 edges."""
    b = gbox(x0, x1, y0, y1, z0, z1)
    es = b.edges() if axis is None else b.edges().filter_by(getattr(Axis, axis))
    return fillet(es, r)
