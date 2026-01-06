"""
Entry point for running mapgenctl as a Python module.

This module enables the package to be executed directly via:
    python -m mapgenctl <command>

Purpose:
    Python packages need a __main__.py file to be runnable as modules.
    This file simply imports and invokes the main CLI function, keeping
    the entry point logic minimal and the actual implementation in cli.py.

Why This Pattern:
    - Separates "how to run" from "what to run"
    - Allows the CLI to be imported and tested independently
    - Follows Python packaging conventions
"""

from .cli import main

# Guard ensures this only runs when executed as a script, not when imported
if __name__ == "__main__":
    main()
