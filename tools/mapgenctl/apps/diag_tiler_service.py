#!/usr/bin/env python3
"""
Diagnostic tool: Tiler Service Configuration Checker

This app diagnoses why the tiler service is not processing jobs by comparing:
1. The installed systemd unit vs the repo source
2. Whether scripts referenced in ExecStart actually exist
3. Whether symlinks are properly established

Usage:
    python3 -m tools.mapgenctl.apps.diag_tiler_service
"""

import os
import subprocess
import sys
from pathlib import Path

# Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    """Print a success message."""
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    """Print a failure message."""
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    """Print a warning message."""
    print(f"  {YELLOW}⚠{RESET} {msg}")


def info(msg: str) -> None:
    """Print an info message."""
    print(f"  {BLUE}ℹ{RESET} {msg}")


def header(title: str) -> None:
    """Print a section header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def main() -> int:
    """Run all diagnostic checks for the tiler service."""
    home = Path.home()
    repo_root = home / "Code" / "RTSColonyTerrainGenerator"
    tiler_dir = repo_root / "MapGenerator" / "Tiler"
    
    installed_service = home / ".config" / "systemd" / "user" / "tiler.service"
    installed_path_unit = home / ".config" / "systemd" / "user" / "tiler.path"
    
    repo_service = tiler_dir / "systemd" / "tiler.service"
    repo_path_unit = tiler_dir / "systemd" / "tiler.path"
    
    issues_found = 0
    
    # ========================================
    header("1. Checking Installed Service Unit")
    # ========================================
    
    if not installed_service.exists():
        fail("tiler.service not found in ~/.config/systemd/user/")
        issues_found += 1
    else:
        ok(f"Installed service exists: {installed_service}")
        
        # Check if it's a symlink or a copy
        if installed_service.is_symlink():
            target = installed_service.resolve()
            ok(f"Is a symlink → {target}")
            if target == repo_service.resolve():
                ok("Symlink points to correct repo file")
            else:
                fail(f"Symlink points to wrong target! Expected: {repo_service}")
                issues_found += 1
        else:
            fail("NOT a symlink — this is a COPY, updates to repo won't apply!")
            issues_found += 1
            
            # Show diff
            print(f"\n  Diff between installed and repo:")
            result = subprocess.run(
                ["diff", "-u", str(installed_service), str(repo_service)],
                capture_output=True, text=True
            )
            if result.stdout:
                for line in result.stdout.splitlines()[:20]:
                    if line.startswith("-"):
                        print(f"    {RED}{line}{RESET}")
                    elif line.startswith("+"):
                        print(f"    {GREEN}{line}{RESET}")
                    else:
                        print(f"    {line}")
    
    # ========================================
    header("2. Checking ExecStart Target")
    # ========================================
    
    if installed_service.exists():
        content = installed_service.read_text()
        for line in content.splitlines():
            if line.startswith("ExecStart="):
                exec_start = line.split("=", 1)[1].strip()
                # Expand %h
                exec_start_expanded = exec_start.replace("%h", str(home))
                info(f"ExecStart: {exec_start}")
                info(f"Expanded:  {exec_start_expanded}")
                
                exec_path = Path(exec_start_expanded)
                if exec_path.exists():
                    ok(f"ExecStart target EXISTS")
                    if os.access(exec_path, os.X_OK):
                        ok(f"ExecStart target is EXECUTABLE")
                    else:
                        fail(f"ExecStart target is NOT executable!")
                        issues_found += 1
                else:
                    fail(f"ExecStart target DOES NOT EXIST: {exec_path}")
                    issues_found += 1
                break
    
    # ========================================
    header("3. Checking Published Binary")
    # ========================================
    
    published_binary = tiler_dir / "bin" / "published" / "Tiler"
    if published_binary.exists():
        ok(f"Published binary exists: {published_binary}")
        size_kb = published_binary.stat().st_size // 1024
        info(f"Size: {size_kb} KB")
    else:
        fail(f"Published binary MISSING: {published_binary}")
        warn("Run: cd MapGenerator/Tiler && ./build.sh")
        issues_found += 1
    
    # ========================================
    header("4. Checking Wrapper Script Chain")
    # ========================================
    
    wrapper = tiler_dir / "bin" / "consume_tiler_queue_job.sh"
    tiler_sh = tiler_dir / "bin" / "tiler.sh"
    
    for script, name in [(wrapper, "consume_tiler_queue_job.sh"), (tiler_sh, "tiler.sh")]:
        if script.exists():
            ok(f"{name} exists")
            if os.access(script, os.X_OK):
                ok(f"{name} is executable")
            else:
                fail(f"{name} is NOT executable")
                issues_found += 1
        else:
            fail(f"{name} MISSING")
            issues_found += 1
    
    # ========================================
    header("5. Checking Inbox for Jobs")
    # ========================================
    
    inbox = tiler_dir / "inbox"
    if inbox.exists():
        heightmaps = list(inbox.glob("*.heightmap"))
        if heightmaps:
            ok(f"Found {len(heightmaps)} job(s) waiting in inbox")
            for hm in heightmaps[:3]:
                info(f"  - {hm.name}")
        else:
            info("No jobs in inbox (this is normal if none are pending)")
    else:
        warn("Inbox directory does not exist")
    
    # ========================================
    header("6. Systemd Service Status")
    # ========================================
    
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "tiler.service"],
        capture_output=True, text=True
    )
    status = result.stdout.strip()
    if status == "active":
        ok(f"tiler.service is active")
    elif status == "inactive":
        info(f"tiler.service is inactive (normal for oneshot)")
    else:
        warn(f"tiler.service status: {status}")
    
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "tiler.path"],
        capture_output=True, text=True
    )
    status = result.stdout.strip()
    if status == "active":
        ok(f"tiler.path is active (watching inbox)")
    else:
        fail(f"tiler.path is NOT active: {status}")
        issues_found += 1
    
    # ========================================
    header("DIAGNOSIS SUMMARY")
    # ========================================
    
    if issues_found == 0:
        print(f"{GREEN}No issues found!{RESET}")
    else:
        print(f"{RED}Found {issues_found} issue(s){RESET}\n")
        
        print(f"{YELLOW}Recommended Fix:{RESET}")
        print("""
  1. Remove the stale copy:
     rm ~/.config/systemd/user/tiler.service
     rm ~/.config/systemd/user/tiler.path
  
  2. Reinstall as symlinks:
     cd ~/Code/RTSColonyTerrainGenerator/MapGenerator/Tiler/systemd
     ./install.sh
  
  3. Verify with:
     systemctl --user daemon-reload
     systemctl --user status tiler.path
""")
    
    return 1 if issues_found else 0


if __name__ == "__main__":
    sys.exit(main())
