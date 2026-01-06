"""
Utility modules for mapgenctl.

This subpackage contains shared utilities used across mapgenctl:

Modules:
    - paths: Filesystem path resolution for pipeline directories
    - joblog: Job logging utilities for pipeline observability

Purpose:
    These utilities are separated from the main CLI to:
    - Avoid circular imports
    - Enable reuse across different CLI commands and TUI components
    - Keep path and logging logic centralized and testable
"""
