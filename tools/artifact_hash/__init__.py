"""Logical-content hashing for MapGenerator pipeline artifacts.

A stage is deterministic (docs/Stage_Contract.md), so the same logical input must
produce the same logical output. This tool computes a hash of an artifact's *logical*
content — ignoring non-contractual metadata such as timestamps — so that:

  - a golden job can be recorded as a manifest of logical hashes (the baseline);
  - a replacement stage (e.g. the verified C# Tiler) can be checked for parity by
    re-hashing its output and comparing to the recorded golden hash.

This is the Phase 0 (M1) artifact-hash tool and the substrate for Gate 7 compatibility
tests. See tools/artifact_hash/README.md.
"""

from .hasher import (
    VOLATILE_KEYS,
    logical_hash,
    build_manifest,
)

__all__ = ["VOLATILE_KEYS", "logical_hash", "build_manifest"]
