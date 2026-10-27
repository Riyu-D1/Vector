"""Measure every SO-ARM-102 follower STEP: bbox, volume, COM.

Run: ~/soma/.venv/bin/python inventory.py
"""
import glob, os
from build123d import import_step

REF = "/tmp/so102/models/step"

parts = sorted(
    glob.glob(f"{REF}/common/*.STEP") + glob.glob(f"{REF}/follower/*.STEP")
)
for p in parts:
    name = os.path.basename(p)
    try:
        part = import_step(p)
        bb = part.bounding_box()
        print(f"{name:55s} bbox=({bb.min.X:8.2f},{bb.min.Y:8.2f},{bb.min.Z:8.2f})"
              f" -> ({bb.max.X:8.2f},{bb.max.Y:8.2f},{bb.max.Z:8.2f})"
              f"  size=({bb.size.X:6.1f},{bb.size.Y:6.1f},{bb.size.Z:6.1f})"
              f"  vol={part.volume/1000:7.1f}cm3")
    except Exception as e:
        print(f"{name:55s} FAILED: {e}")
