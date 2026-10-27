import os
from build123d import Box, Pos, export_stl
os.makedirs("out_selftest", exist_ok=True)
export_stl(Pos(0, 0, 0) * Box(20, 20, 20), "out_selftest/a.stl")
export_stl(Pos(15, 0, 0) * Box(20, 20, 20), "out_selftest/b.stl")
export_stl(Pos(0, 0, 0) * (Box(20, 20, 20) - Box(19, 19, 19)), "out_selftest/thin.stl")
print("written")
