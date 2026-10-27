import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SHARED_C_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "firmware", "shared"))
