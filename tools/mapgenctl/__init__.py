"""
mapgenctl - Developer Control Tool for the MapGenerator Pipeline.

This package provides a command-line interface and TUI (Text User Interface)
for interacting with the RTSColonyTerrainGenerator MapGenerator pipeline.

Purpose:
    mapgenctl exists to give developers fine-grained control over the
    terrain generation pipeline during development and testing. It allows
    submitting jobs, monitoring progress, inspecting outputs, and cleaning
    up pipeline state without needing to interact with the raw filesystem.

Package Structure:
    - cli.py: Main command-line interface and entry point
    - tui/: Text User Interface components for live monitoring
    - utils/: Shared utilities for paths and logging

Usage:
    Run as a module: python -m mapgenctl <command>
    
Example:
    python -m mapgenctl run --width 256 --height 256 --tui
"""
