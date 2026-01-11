#!/usr/bin/env python3
"""
mapgenctl for WeatherAnalyses

Developer control tool for the WeatherAnalyses pipeline stage.
"""

import os
import sys
import argparse
import struct
import shutil
import time
import subprocess
from pathlib import Path

# Paths (relative to this script in WeatherAnalyses root)
ROOT_DIR = Path(__file__).parent.resolve()
INBOX = ROOT_DIR / "inbox"
OUTBOX = ROOT_DIR / "outbox"
ARCHIVE = ROOT_DIR / "archive"
FAILED = ROOT_DIR / "failed"
BIN_DIR = ROOT_DIR / "bin"
TARGET_DIR = ROOT_DIR / "target"
SRC_DIR = ROOT_DIR / "src"

def clean(args):
    """Remove files from runtime directories."""
    dirs = {"inbox": INBOX, "outbox": OUTBOX, "archive": ARCHIVE, "failed": FAILED}
    print("[mapgenctl] Cleaning runtime directories...")
    
    for name, path in dirs.items():
        if not path.exists():
            continue
            
        count = 0
        for item in path.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                item.unlink()
                count += 1
        print(f"  {name}: removed {count} files")

def watch(args):
    """Watch runtime directories for activity."""
    dirs = {"inbox": INBOX, "outbox": OUTBOX, "archive": ARCHIVE, "failed": FAILED}
    print("[mapgenctl] Watching directories. Press Ctrl+C to stop.")
    
    for name, path in dirs.items():
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            
    print(f"  Root: {ROOT_DIR}")

    state = {name: set(p.name for p in path.iterdir()) for name, path in dirs.items()}

    try:
        while True:
            time.sleep(1)
            for name, path in dirs.items():
                current = set(p.name for p in path.iterdir())
                added = current - state[name]
                removed = state[name] - current
                
                for item in sorted(added):
                    print(f"[{name}] + {item}")
                for item in sorted(removed):
                    print(f"[{name}] - {item}")
                    
                state[name] = current
    except KeyboardInterrupt:
        print("\n[mapgenctl] Stopped.")

def build(args):
    """Build Rust binary and deploy to bin/."""
    print("[mapgenctl] Building weather-engine (release)...")
    
    cmd = ["cargo", "build", "--release"]
    if subprocess.call(cmd, cwd=ROOT_DIR) != 0:
        print("Build failed!")
        sys.exit(1)
        
    src_bin = TARGET_DIR / "release" / "weather-engine"
    dst_bin = BIN_DIR / "weather-engine"
    
    BIN_DIR.mkdir(exist_ok=True)
    shutil.copy2(src_bin, dst_bin)
    print(f"[mapgenctl] Deployed to {dst_bin}")

def inspect(args):
    """Inspect a .weather binary file."""
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
        
    size = path.stat().st_size
    if size < 16:
        print("File too small to match .weather format")
        sys.exit(1)
        
    with open(path, "rb") as f:
        # Header: magic(4), version(2), width(4), height(4), layers(2)
        header = f.read(16)
        magic, ver, w, h, layers = struct.unpack("<I H I I H", header[:16])
        # Note: struct format check
        # magic: u32 (I)
        # ver: u16 (H) -> Wait, struct alignment might need padding
        # Let's verify rust: write_all u32, u16, u32, u32, u16.
        # This is packed tightly. Python struct 'I I I I H' expects 4 byte alignment usually?
        # Use standard size '<' (Little endian, standard)
        # I=4, H=2.
        # <I H I I H
        # 4 + 2 + 4 + 4 + 2 = 16 bytes.
        magic, ver, w, h, layers = struct.unpack("<I H I I H", header)
        
    magic_str = magic.to_bytes(4, 'little').decode('ascii', errors='ignore')
    
    print(f"[mapgenctl] Inspecting {path.name}")
    print(f"  Size:    {size} bytes")
    print(f"  Magic:   0x{magic:08X} ({magic_str})")
    print(f"  Version: {ver}")
    print(f"  Dim:     {w} x {h}")
    print(f"  Layers:  {layers}")
    
    # Validation
    expected_data = (w * h) * 7 # 2(slope) + 1(flow) + 4(basin)
    expected_total = 16 + expected_data
    
    print(f"  Cells:   {w*h}")
    print(f"  Exp Size:{expected_total}")
    
    if size == expected_total:
        print("  Status:  VALID structure")
    else:
        print(f"  Status:  INVALID size (diff {size - expected_total})")

def main():
    parser = argparse.ArgumentParser(prog="mapgenctl", description="WeatherAnalyses Control")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("clean", help="Clean runtime dirs")
    subparsers.add_parser("watch", help="Watch runtime dirs")
    subparsers.add_parser("build", help="Build and deploy binary")
    
    insp = subparsers.add_parser("inspect", help="Inspect .weather file")
    insp.add_argument("path", help="Path to .weather file")
    
    args = parser.parse_args()
    
    if args.command == "clean": clean(args)
    elif args.command == "watch": watch(args)
    elif args.command == "build": build(args)
    elif args.command == "inspect": inspect(args)

if __name__ == "__main__":
    main()
