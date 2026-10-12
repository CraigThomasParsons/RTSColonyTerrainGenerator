"""Shared fixtures and fake boundaries for the issue #52 candidate tests.

Every test in this package runs entirely offline. The only PixelLab "client"
any test ever sees is a fake transport or a fake submit function defined here,
so no test can contact api.pixellab.ai even by accident.
"""

from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Callable


BIN_DIRECTORY = Path(__file__).resolve().parents[1] / "bin"

# The orchestration modules are siblings in bin/ and import each other by name.
# Tests are the only consumer that does not already have that directory on
# sys.path, so the tests add it explicitly rather than the library doing it.
if str(BIN_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BIN_DIRECTORY))

import candidate_approval  # noqa: E402
import candidate_orchestrator  # noqa: E402
import candidate_plan  # noqa: E402
import candidate_state  # noqa: E402
import candidate_validation  # noqa: E402
import pixellab_modules  # noqa: E402


visual_contract = pixellab_modules.load_visual_contract()
pixellab_client = pixellab_modules.load_pixellab_client()

# A deliberately fake token. No test ever reads a real operator token, and the
# adapter is only ever handed a fake transport.
FAKE_TOKEN = "issue52-test-token-never-live-FAKESECRET"

TERRAIN_VOCABULARY = ("grass", "water", "rock", "sand", "snow", "mountain", "road")


def build_map_payload(job_id: str, width: int, height: int, terrain_seed: int) -> dict[str, Any]:
    """
    Description:
        Build one complete, strict synthetic world payload for a test map.
    Required State:
        Dimensions must be large enough to satisfy callers' expectations.
    Usage:
        Use to create representative maps without touching real game data.
    Parameters:
        job_id (str): Identifier recorded in the payload and the visual brief.
        width (int): Map width in cells.
        height (int): Map height in cells.
        terrain_seed (int): Multiplier that varies the terrain pattern per map.
    Returns:
        dict[str, Any]: JSON-compatible world payload with a complete tile grid.
    Other I/O:
        - none
    """
    tiles: list[dict[str, Any]] = []
    for coordinate_y in range(height):
        for coordinate_x in range(width):
            terrain_index = (coordinate_x * terrain_seed + coordinate_y * 3) % len(TERRAIN_VOCABULARY)
            tiles.append(
                {"x": coordinate_x, "y": coordinate_y, "terrain": TERRAIN_VOCABULARY[terrain_index]}
            )
    return {
        "version": 1,
        "job_id": job_id,
        "map": {"width_in_cells": width, "height_in_cells": height},
        "tiles": tiles,
        "features": [{"type": "road", "x": 2, "y": 2}, {"type": "bridge", "x": 5, "y": 5}],
        "playable": {
            "start_zones": [{"id": "start-1", "x": 3, "y": 3}],
            "resource_clusters": [{"id": "ore-1", "x": 6, "y": 7}],
            "settlement_labels": [{"id": "town-1", "x": 8, "y": 9}],
        },
    }


def write_payload(directory: Path, file_name: str, payload: dict[str, Any]) -> Path:
    """
    Description:
        Persist one synthetic world payload as canonical JSON.
    Required State:
        The directory exists or can be created.
    Usage:
        Call from setUp before planning or running.
    Parameters:
        directory (Path): Destination directory.
        file_name (str): Payload file name.
        payload (dict[str, Any]): Payload content.
    Returns:
        Path: Path of the written payload.
    Other I/O:
        - files: writes one .worldpayload file
    """
    directory.mkdir(parents=True, exist_ok=True)
    payload_path = directory / file_name
    payload_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return payload_path


def build_png_bytes(width: int, height: int, red: int = 10, green: int = 20, blue: int = 30) -> bytes:
    """
    Description:
        Build a minimal valid 8-bit RGB PNG for dimension and hash checks.
    Required State:
        Width and height are positive integers.
    Usage:
        Use as the image a fake PixelLab response would have returned.
    Parameters:
        width (int): Image width in pixels.
        height (int): Image height in pixels.
        red (int): Red channel value for every pixel.
        green (int): Green channel value for every pixel.
        blue (int): Blue channel value for every pixel.
    Returns:
        bytes: Complete PNG file content.
    Other I/O:
        - none
    """
    raw_rows = bytearray()
    for _row_index in range(height):
        raw_rows.append(0)
        for _column_index in range(width):
            raw_rows.extend((red, green, blue))

    def chunk(tag: bytes, data: bytes) -> bytes:
        """Pack one PNG chunk with length, type, payload, and CRC."""
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw_rows), 9))
        + chunk(b"IEND", b"")
    )


class FakeSubmitBoundary:
    """Stand in for a live submit, counting calls and writing a real candidate.

    The fake reuses the adapter's own offline preparation, cache lookup, and
    manifest publishing, so what lands on disk is exactly what a live run would
    have produced. Only the network is replaced.
    """

    def __init__(self, image_factory: Callable[[int, int], bytes]):
        """
        Description:
            Create a fake submission boundary with a scripted image source.
        Required State:
            The image factory returns a PNG matching the requested size.
        Usage:
            Inject as OrchestrationSettings.submit_function in live-mode tests.
        Parameters:
            image_factory (Callable[[int, int], bytes]): Builds the returned PNG.
        Returns:
            None: Constructs the fake.
        Other I/O:
            - none
        """
        self.image_factory = image_factory
        self.call_count = 0
        self.submission_count = 0
        self.cache_hit_count = 0

    def __call__(self, adapter_settings: Any) -> dict[str, Any]:
        """
        Description:
            Produce one candidate exactly as a live submission would have.
        Required State:
            The adapter settings name intact controls and a candidate directory.
        Usage:
            Invoked by the orchestrator once per candidate in live mode.
        Parameters:
            adapter_settings (Any): AdapterSettings for one candidate.
        Returns:
            dict[str, Any]: The candidate manifest that was published.
        Other I/O:
            - files: writes candidate.png, generation-manifest.json, cache entry
        """
        self.call_count += 1
        _, request_body, request_cache_key, manifest = pixellab_client.prepare_generation(
            adapter_settings
        )
        adapter_settings.output_directory.mkdir(parents=True, exist_ok=True)

        # A cache hit must cost nothing, exactly as the real adapter guarantees.
        cached_image = pixellab_client.lookup_cached_image(
            adapter_settings.cache_directory, request_cache_key
        )
        if cached_image is not None:
            self.cache_hit_count += 1
            manifest["remote"]["cacheHit"] = True
            image_bytes = cached_image
        else:
            self.submission_count += 1
            manifest["remote"]["jobId"] = f"fake-job-{request_cache_key[:8]}"
            manifest["remote"]["status"] = "completed"
            manifest["remote"]["usage"] = {"type": "usd", "usd": 0.02}
            image_bytes = self.image_factory(
                request_body["image_size"]["width"], request_body["image_size"]["height"]
            )
            pixellab_client.store_cached_image(
                adapter_settings.cache_directory, request_cache_key, image_bytes
            )

        pixellab_client.record_output_in_manifest(manifest, image_bytes)
        pixellab_client.write_file_atomically(
            adapter_settings.output_directory / pixellab_client.CANDIDATE_IMAGE_NAME, image_bytes
        )
        pixellab_client.publish_candidate_manifest(adapter_settings.output_directory, manifest)
        return manifest


def fixed_clock(timestamp_text: str) -> Callable[[], Any]:
    """
    Description:
        Build a clock that always reports one fixed UTC moment.
    Required State:
        The text must be an ISO 8601 instant with an explicit UTC offset.
    Usage:
        Inject into candidate_approval.record_decision for reproducible records.
    Parameters:
        timestamp_text (str): ISO 8601 moment, for example "2026-08-09T12:00:00+00:00".
    Returns:
        Callable[[], datetime]: Clock returning that moment every time.
    Other I/O:
        - none
    """
    from datetime import datetime

    moment = datetime.fromisoformat(timestamp_text)

    def clock() -> Any:
        """Return the single fixed moment this clock was built with."""
        return moment

    return clock


def directory_digest(root: Path) -> dict[str, str]:
    """
    Description:
        Hash every file under a directory to compare two runs byte for byte.
    Required State:
        The directory exists.
    Usage:
        Use to assert that repeating an identical offline plan is byte-stable.
    Parameters:
        root (Path): Directory to digest.
    Returns:
        dict[str, str]: Relative file path mapped to its SHA-256 digest.
    Other I/O:
        - files: reads every file below root
    """
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digests[str(path.relative_to(root))] = visual_contract.sha256_bytes(path.read_bytes())
    return digests
