#!/usr/bin/env python3
"""Load the sibling PixelLab presentation scripts as importable modules.

The issue #50 contract builder and the issue #51 adapter are executable scripts
in this directory rather than an installed package, so the orchestration layer
added by issue #52 cannot simply `import` them. This module centralises that
loading in one place so that no orchestration module has to repeat importlib
plumbing, and so that every consumer shares one module instance (and therefore
one set of contract constants) per process.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


BIN_DIRECTORY = Path(__file__).resolve().parent

# Registered names are stable so that a module loaded by the orchestrator and a
# module loaded by a test refer to the same object. Dataclass creation on
# Python 3.14 also looks the owning module up in sys.modules, so the entry must
# exist before the module body executes.
VISUAL_CONTRACT_MODULE_NAME = "visual_contract"
PIXELLAB_CLIENT_MODULE_NAME = "pixellab_client"


def load_sibling_module(module_name: str, file_name: str) -> ModuleType:
    """
    Description:
        Load one script from this directory under a stable sys.modules name.
    Required State:
        The named file must exist beside this module and be valid Python source.
    Usage:
        Prefer the named helpers below; call this directly only for a new script.
    Parameters:
        module_name (str): Name to register in sys.modules.
        file_name (str): File name of the script inside bin/.
    Returns:
        ModuleType: The loaded module object.
    Other I/O:
        - files: reads the named script once per process
    """
    # Returning an already-loaded module keeps contract constants identical
    # across callers and avoids re-executing module-level code.
    existing_module = sys.modules.get(module_name)
    if existing_module is not None:
        return existing_module

    module_path = BIN_DIRECTORY / file_name
    if not module_path.is_file():
        raise FileNotFoundError(f"required PixelLab module not found: {module_path}")

    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"could not build an import spec for {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    # Register before execution so that dataclasses defined in the module can
    # resolve their own __module__ during class creation.
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


def load_visual_contract() -> ModuleType:
    """
    Description:
        Load the issue #50 deterministic control-artifact builder.
    Required State:
        visual_contract.py is present in this directory.
    Usage:
        Call once per module that needs the contract API.
    Parameters:
        none
    Returns:
        ModuleType: The visual_contract module.
    Other I/O:
        - files: reads bin/visual_contract.py on first use
    """
    return load_sibling_module(VISUAL_CONTRACT_MODULE_NAME, "visual_contract.py")


def load_pixellab_client() -> ModuleType:
    """
    Description:
        Load the issue #51 opt-in PixelLab v2 adapter.
    Required State:
        pixellab_client.py is present in this directory.
    Usage:
        Call once per module that needs request, cache, or transport behaviour.
    Parameters:
        none
    Returns:
        ModuleType: The pixellab_client module.
    Other I/O:
        - files: reads bin/pixellab_client.py on first use
    """
    return load_sibling_module(PIXELLAB_CLIENT_MODULE_NAME, "pixellab_client.py")
