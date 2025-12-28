#!/usr/bin/env python3
"""
Compatibility shim: old `MapGenTest/mapgenctl/mapgenctl.py` location.

This file delegates execution to the moved copy under `tools/mapgenctl/`.
"""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "tools" / "mapgenctl" / "mapgenctl.py"

if not DEST.exists():
    print(f"Moved mapgenctl not found at: {DEST}")
    sys.exit(1)

# Execute the moved script as __main__
runpy.run_path(str(DEST), run_name="__main__")
