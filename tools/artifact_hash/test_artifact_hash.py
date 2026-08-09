"""Tests for the logical-hash tool. Run: python -m pytest tools/artifact_hash/"""

import json
from pathlib import Path

from tools.artifact_hash.hasher import logical_hash


def _write(tmp_path: Path, name: str, obj) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def test_key_order_does_not_change_hash(tmp_path):
    a = _write(tmp_path, "a.json", {"x": 1, "y": 2})
    b = _write(tmp_path, "b.json", {"y": 2, "x": 1})
    assert logical_hash(a) == logical_hash(b)


def test_volatile_timestamp_is_ignored(tmp_path):
    a = _write(tmp_path, "a.json", {"job_id": "j", "requested_at_utc": "2026-01-01T00:00:00Z", "w": 64})
    b = _write(tmp_path, "b.json", {"job_id": "j", "requested_at_utc": "2099-12-31T23:59:59Z", "w": 64})
    assert logical_hash(a) == logical_hash(b)


def test_content_change_changes_hash(tmp_path):
    a = _write(tmp_path, "a.json", {"w": 64})
    b = _write(tmp_path, "b.json", {"w": 128})
    assert logical_hash(a) != logical_hash(b)


def test_ignore_identity_strips_job_id(tmp_path):
    a = _write(tmp_path, "a.json", {"job_id": "job-A", "w": 64})
    b = _write(tmp_path, "b.json", {"job_id": "job-B", "w": 64})
    assert logical_hash(a) != logical_hash(b)                       # identity kept by default
    assert logical_hash(a, ignore_identity=True) == logical_hash(b, ignore_identity=True)


def test_binary_hashes_raw_bytes(tmp_path):
    p = tmp_path / "x.maptiles"
    p.write_bytes(b"MTIL\x01\x00\x00\x00payload")
    assert logical_hash(p).startswith("sha256:")


def test_hash_is_stable_across_calls(tmp_path):
    a = _write(tmp_path, "a.json", {"a": [3, 2, 1], "b": {"c": 1}})
    assert logical_hash(a) == logical_hash(a)
