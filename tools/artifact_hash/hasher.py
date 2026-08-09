"""Logical-content hashing primitives.

The public surface is small on purpose:
  logical_hash(path, *, ignore_identity=False) -> "sha256:<hex>"
  build_manifest(job_id, repo_root) -> dict

Dispatch is by artifact kind:
  - JSON-family (.json, .playable.json, and world.json inside a .worldpayload dir):
    parsed, volatile keys stripped recursively, re-serialized canonically, then hashed.
    This makes the hash insensitive to key order and to timestamps.
  - Binary (.heightmap, .weather, .maptiles, .png, .chk, .scm): raw bytes hashed.
    These formats are already deterministic byte-for-byte for a given input.
  - .worldpayload directory: hashed via its logical world.json only; the sibling
    index.html / main.js / style.css are a fixed viewer shell, not stage output.

`ignore_identity=True` additionally strips per-run identity keys (job_id), so two runs
of the same map under different job ids produce the same logical hash — needed when a
replacement stage is exercised on a fresh job rather than the golden job id.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Keys whose values are non-contractual metadata: never part of logical equality.
VOLATILE_KEYS = frozenset({
    "requested_at_utc",
    "generated_at",
    "generatedat",
    "created_at",
    "updated_at",
    "timestamp",
    "produced_at",
    "duration_ms",
    "elapsed_ms",
    "wall_ms",
    "source_path",
    "output_path",
})

# Keys that identify a particular run rather than its logical content.
IDENTITY_KEYS = frozenset({"job_id", "jobid"})

# Extensions whose bytes are already a deterministic function of the input.
_BINARY_EXTS = frozenset({".heightmap", ".weather", ".maptiles", ".png", ".chk", ".scm"})


def _strip(value, drop: frozenset):
    """Recursively drop `drop` keys from dicts, preserving everything else."""
    if isinstance(value, dict):
        return {k: _strip(v, drop) for k, v in value.items() if k.lower() not in drop}
    if isinstance(value, list):
        return [_strip(v, drop) for v in value]
    return value


def _canonical_json_bytes(obj, *, ignore_identity: bool) -> bytes:
    drop = VOLATILE_KEYS | (IDENTITY_KEYS if ignore_identity else frozenset())
    normalized = _strip(obj, drop)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def logical_hash(path: str | Path, *, ignore_identity: bool = False) -> str:
    """Return "sha256:<hex>" of the artifact's logical content."""
    path = Path(path)

    if path.is_dir():
        # A .worldpayload bundle: its logical content is world.json.
        world = path / "world.json"
        if not world.exists():
            raise ValueError(f"{path} is a directory but has no world.json to hash")
        obj = json.loads(world.read_text(encoding="utf-8"))
        return _digest(_canonical_json_bytes(obj, ignore_identity=ignore_identity))

    suffix = path.suffix.lower()
    name = path.name.lower()

    if suffix in _BINARY_EXTS:
        return _digest(path.read_bytes())

    if suffix == ".json" or name.endswith(".playable.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        return _digest(_canonical_json_bytes(obj, ignore_identity=ignore_identity))

    # Unknown text/other: fall back to raw bytes so nothing is silently unhashed.
    return _digest(path.read_bytes())


# Where each stage leaves the artifact(s) for a completed job, relative to repo root.
# (outbox = authoritative output; archive = consumed input, kept for lineage.)
_MANIFEST_SOURCES = [
    ("Heightmap/archive", ".json"),            # the job spec (pipeline input)
    ("WeatherAnalyses/archive", ".heightmap"),  # Heightmap output, consumed here
    ("WeatherAnalyses/outbox", ".weather"),
    ("Tiler/outbox", ".maptiles"),
    ("TreePlanter/outbox", ".worldpayload"),
    ("WorldFeatures/outbox", ".worldpayload"),
    ("PathFinder/outbox", ".json"),
    ("Playable/outbox", ".playable.json"),
    ("Playable/outbox", ".worldpayload"),
    ("WorldSnapshot/outbox", ".png"),
    ("StargusExport/outbox", ".chk"),
    ("StargusExport/outbox", ".scm"),
]


def build_manifest(job_id: str, repo_root: str | Path) -> dict:
    """Walk a completed job's artifacts and record a logical-hash manifest.

    Returns {"job_id", "artifacts": {relpath: {"kind", "bytes", "logical_sha256"}}}.
    Missing artifacts are skipped (recorded under "missing") rather than failing, so a
    partially-complete job still yields a usable baseline.
    """
    repo_root = Path(repo_root)
    stages_root = repo_root / "MapGenerator"
    artifacts: dict[str, dict] = {}
    missing: list[str] = []

    for subdir, ext in _MANIFEST_SOURCES:
        artifact = stages_root / subdir / f"{job_id}{ext}"
        rel = f"MapGenerator/{subdir}/{job_id}{ext}"
        if not artifact.exists():
            missing.append(rel)
            continue
        size = sum(f.stat().st_size for f in artifact.rglob("*") if f.is_file()) if artifact.is_dir() else artifact.stat().st_size
        artifacts[rel] = {
            "kind": "dir" if artifact.is_dir() else ext.lstrip("."),
            "bytes": size,
            "logical_sha256": logical_hash(artifact),
        }

    return {"job_id": job_id, "artifacts": artifacts, "missing": missing}
