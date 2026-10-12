#!/usr/bin/env python3
"""Build deterministic PixelLab control artifacts from a world payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


CONTRACT_VERSION = "1.0"
PROMPT_VERSION = "1"
PIXELLAB_ENDPOINT = "/create-image-pixflux-background"
TERRAIN_COLORS: dict[str, tuple[int, int, int]] = {
    "grass": (78, 137, 73),
    "mountain": (105, 100, 95),
    "rock": (132, 119, 101),
    "water": (47, 91, 142),
    "sand": (194, 169, 111),
    "snow": (222, 229, 232),
    "road": (123, 94, 65),
}
PROTECTED_FEATURE_TYPES = {"bridge", "cavern", "lumber", "path", "ramp", "road", "tunnel"}
# A cell occupies exactly one 2x2 tile region. That is the pipeline's oldest verified rule
# (specs/tiling/CellToTile.dfy, slice 01, promoted in both ledgers), which is why a payload
# declaring cells while its tiles span tile space is correct rather than inconsistent.
TILES_PER_CELL_AXIS = 2


class ContractError(ValueError):
    """Represent a world payload that cannot safely produce visual controls."""


def canonical_json_bytes(value: Any) -> bytes:
    """
    Description:
        Serialize JSON deterministically for hashing and repeatable artifacts.
    Required State:
        The value must contain only JSON-compatible data.
    Usage:
        Use for every contract JSON output and cache-key component.
    Parameters:
        value (Any): JSON-compatible value to serialize.
    Returns:
        bytes: UTF-8 canonical JSON ending in one newline.
    Other I/O:
        - none
    """
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    """
    Description:
        Compute a stable SHA-256 identifier for contract content.
    Required State:
        Content is the exact byte sequence that will be persisted or submitted.
    Usage:
        Use when recording provenance and building cache keys.
    Parameters:
        content (bytes): Content to hash.
    Returns:
        str: Lowercase hexadecimal SHA-256 digest.
    Other I/O:
        - none
    """
    return hashlib.sha256(content).hexdigest()


def read_payload(input_path: Path) -> tuple[dict[str, Any], bytes]:
    """
    Description:
        Read and validate the top-level shape of a JSON world payload.
    Required State:
        The input path must name a readable JSON file.
    Usage:
        Call once before deriving dimensions or visual intent.
    Parameters:
        input_path (Path): World payload file.
    Returns:
        tuple[dict[str, Any], bytes]: Parsed payload and original bytes.
    Other I/O:
        - files: reads input_path
    """
    source_bytes = input_path.read_bytes()
    try:
        payload = json.loads(source_bytes)
    except json.JSONDecodeError as error:
        raise ContractError(f"invalid JSON: {error}") from error

    if not isinstance(payload, dict):
        raise ContractError("world payload must be a JSON object")
    if not isinstance(payload.get("tiles"), list) or not payload["tiles"]:
        raise ContractError("world payload must contain a non-empty tiles array")
    return payload, source_bytes


def validate_tiles(tiles: list[Any]) -> tuple[dict[tuple[int, int], dict[str, Any]], int, int]:
    """
    Description:
        Validate tile coordinates, uniqueness, terrain vocabulary, and extents.
    Required State:
        Tiles came from a parsed world payload.
    Usage:
        Call before trusting dimensions or rendering masks.
    Parameters:
        tiles (list[Any]): Raw tile records.
    Returns:
        tuple[dict, int, int]: Coordinate lookup, inferred width, inferred height.
    Other I/O:
        - none
    """
    tile_lookup: dict[tuple[int, int], dict[str, Any]] = {}
    maximum_x = -1
    maximum_y = -1

    for index, raw_tile in enumerate(tiles):
        if not isinstance(raw_tile, dict):
            raise ContractError(f"tile {index} must be an object")
        coordinate_x = raw_tile.get("x")
        coordinate_y = raw_tile.get("y")
        terrain = raw_tile.get("terrain")
        if type(coordinate_x) is not int or type(coordinate_y) is not int:
            raise ContractError(f"tile {index} requires integer x and y")
        if coordinate_x < 0 or coordinate_y < 0:
            raise ContractError(f"tile {index} has a negative coordinate")
        if terrain not in TERRAIN_COLORS:
            raise ContractError(f"tile {index} has unsupported terrain: {terrain!r}")

        coordinate = (coordinate_x, coordinate_y)
        if coordinate in tile_lookup:
            raise ContractError(f"duplicate tile coordinate: {coordinate}")
        tile_lookup[coordinate] = raw_tile
        maximum_x = max(maximum_x, coordinate_x)
        maximum_y = max(maximum_y, coordinate_y)

    return tile_lookup, maximum_x + 1, maximum_y + 1


def resolve_dimensions(
    payload: dict[str, Any], inferred_width: int, inferred_height: int, allow_inferred: bool
) -> tuple[int, int, list[str]]:
    """
    Description:
        Reconcile declared map dimensions with validated tile-grid extents.
    Required State:
        Inferred dimensions came from unique non-negative tile coordinates.
    Usage:
        Use before checking grid completeness or writing image artifacts.
    Parameters:
        payload (dict[str, Any]): Parsed world payload.
        inferred_width (int): Width implied by maximum tile x.
        inferred_height (int): Height implied by maximum tile y.
        allow_inferred (bool): Permit an exploration-only legacy override.
    Returns:
        tuple[int, int, list[str]]: Selected dimensions and warnings.
    Other I/O:
        - none
    """
    map_record = payload.get("map")
    if not isinstance(map_record, dict):
        raise ContractError("world payload requires a map object")
    declared_width = map_record.get("width_in_cells")
    declared_height = map_record.get("height_in_cells")
    if type(declared_width) is not int or type(declared_height) is not int:
        raise ContractError("map dimensions must be integers")
    if declared_width <= 0 or declared_height <= 0:
        raise ContractError("map dimensions must be positive")

    if (declared_width, declared_height) == (inferred_width, inferred_height):
        return declared_width, declared_height, []

    # `width_in_cells` and the tiles array are different units, so equality is the wrong
    # test. A payload whose tiles span exactly cells x TILES_PER_CELL_AXIS is obeying the
    # verified cell-to-tile rule, not contradicting itself. Tile extents are returned
    # because everything downstream — grid completeness, the per-cell raster — indexes
    # tile coordinates.
    expanded = (declared_width * TILES_PER_CELL_AXIS, declared_height * TILES_PER_CELL_AXIS)
    if (inferred_width, inferred_height) == expanded:
        return inferred_width, inferred_height, []

    mismatch = (
        f"declared dimensions {declared_width}x{declared_height} do not match "
        f"tile extents {inferred_width}x{inferred_height} (Gitea #55)"
    )
    if not allow_inferred:
        raise ContractError(mismatch)
    return inferred_width, inferred_height, [f"EXPLORATION ONLY: {mismatch}"]


def require_complete_grid(tile_lookup: dict[tuple[int, int], dict[str, Any]], width: int, height: int) -> None:
    """
    Description:
        Require exactly one tile for every cell in a rectangular map.
    Required State:
        Tile coordinates are unique and dimensions are resolved.
    Usage:
        Call before producing per-cell PNG data.
    Parameters:
        tile_lookup (dict): Validated coordinate-to-tile mapping.
        width (int): Expected grid width.
        height (int): Expected grid height.
    Returns:
        None: Completes when the grid is rectangular and complete.
    Other I/O:
        - none
    """
    expected_count = width * height
    if len(tile_lookup) != expected_count:
        raise ContractError(f"tile grid has {len(tile_lookup)} cells; expected {expected_count}")
    for coordinate_y in range(height):
        for coordinate_x in range(width):
            if (coordinate_x, coordinate_y) not in tile_lookup:
                raise ContractError(f"tile grid is missing coordinate {(coordinate_x, coordinate_y)}")


def collect_explicit_protected_coordinates(payload: dict[str, Any], width: int, height: int) -> set[tuple[int, int]]:
    """
    Description:
        Collect gameplay landmarks whose visual positions must not drift.
    Required State:
        Payload dimensions and tile grid are already valid.
    Usage:
        Combine with terrain boundaries to build the protected mask.
    Parameters:
        payload (dict[str, Any]): Parsed world payload.
        width (int): Valid map width.
        height (int): Valid map height.
    Returns:
        set[tuple[int, int]]: In-bounds protected coordinates.
    Other I/O:
        - none
    """
    protected: set[tuple[int, int]] = set()
    feature_records: list[Any] = payload.get("features") if isinstance(payload.get("features"), list) else []
    playable = payload.get("playable") if isinstance(payload.get("playable"), dict) else {}
    playable_records: list[Any] = []
    for key in ("start_zones", "resource_clusters", "settlement_labels"):
        if isinstance(playable.get(key), list):
            playable_records.extend(playable[key])

    for record in feature_records:
        if not isinstance(record, dict):
            continue
        if record.get("type") not in PROTECTED_FEATURE_TYPES:
            continue
        coordinate_x = record.get("x")
        coordinate_y = record.get("y")
        if type(coordinate_x) is int and type(coordinate_y) is int:
            if 0 <= coordinate_x < width and 0 <= coordinate_y < height:
                protected.add((coordinate_x, coordinate_y))

    # Playable labels are protected regardless of their type because their
    # coordinate is the authoritative contract consumed by game exporters.
    for record in playable_records:
        if not isinstance(record, dict):
            continue
        coordinate_x = record.get("x")
        coordinate_y = record.get("y")
        if type(coordinate_x) is int and type(coordinate_y) is int:
            if 0 <= coordinate_x < width and 0 <= coordinate_y < height:
                protected.add((coordinate_x, coordinate_y))
    return protected


def build_masks(
    tile_lookup: dict[tuple[int, int], dict[str, Any]],
    explicit_protected: set[tuple[int, int]],
    width: int,
    height: int,
) -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]], list[tuple[int, int, int]]]:
    """
    Description:
        Build semantic, protected, and decoration pixel buffers.
    Required State:
        The tile grid is complete and explicit coordinates are in bounds.
    Usage:
        Use once per validated payload before PNG encoding.
    Parameters:
        tile_lookup (dict): Coordinate-to-tile mapping.
        explicit_protected (set): Starts, resources, labels, and features.
        width (int): Grid width.
        height (int): Grid height.
    Returns:
        tuple[list, list, list]: Semantic RGB, protected mask, decoration mask.
    Other I/O:
        - none
    """
    semantic_pixels: list[tuple[int, int, int]] = []
    protected_pixels: list[tuple[int, int, int]] = []
    decoration_pixels: list[tuple[int, int, int]] = []
    neighbor_offsets = ((-1, 0), (1, 0), (0, -1), (0, 1))

    for coordinate_y in range(height):
        for coordinate_x in range(width):
            coordinate = (coordinate_x, coordinate_y)
            terrain = tile_lookup[coordinate]["terrain"]
            is_boundary = False
            for offset_x, offset_y in neighbor_offsets:
                neighbor = (coordinate_x + offset_x, coordinate_y + offset_y)
                if neighbor in tile_lookup and tile_lookup[neighbor]["terrain"] != terrain:
                    is_boundary = True
                    break
            is_protected = terrain in {"water", "road"} or is_boundary or coordinate in explicit_protected
            is_decoratable = not is_protected and terrain not in {"mountain", "water"}

            semantic_pixels.append(TERRAIN_COLORS[terrain])
            protected_pixels.append((255, 255, 255) if is_protected else (0, 0, 0))
            decoration_pixels.append((255, 255, 255) if is_decoratable else (0, 0, 0))
    return semantic_pixels, protected_pixels, decoration_pixels


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """
    Description:
        Encode one PNG chunk with length and CRC.
    Required State:
        Chunk type is a four-byte PNG chunk identifier.
    Usage:
        Use only through encode_rgb_png.
    Parameters:
        chunk_type (bytes): Four-byte chunk type.
        data (bytes): Chunk payload.
    Returns:
        bytes: Complete encoded PNG chunk.
    Other I/O:
        - none
    """
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def encode_rgb_png(width: int, height: int, pixels: Iterable[tuple[int, int, int]]) -> bytes:
    """
    Description:
        Encode a deterministic 8-bit RGB PNG without third-party dependencies.
    Required State:
        Pixel iteration contains exactly width multiplied by height RGB triples.
    Usage:
        Use for semantic and binary mask images.
    Parameters:
        width (int): Image width in pixels.
        height (int): Image height in pixels.
        pixels (Iterable[tuple[int, int, int]]): Row-major RGB values.
    Returns:
        bytes: Complete PNG file content.
    Other I/O:
        - none
    """
    pixel_values = list(pixels)
    if len(pixel_values) != width * height:
        raise ContractError("PNG pixel count does not match dimensions")
    scanlines = bytearray()
    for coordinate_y in range(height):
        scanlines.append(0)
        row_start = coordinate_y * width
        for red, green, blue in pixel_values[row_start : row_start + width]:
            scanlines.extend((red, green, blue))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    signature = b"\x89PNG\r\n\x1a\n"
    compressed_pixels = zlib.compress(bytes(scanlines), 9)
    return (
        signature
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", compressed_pixels)
        + png_chunk(b"IEND", b"")
    )


def build_visual_brief(
    payload: dict[str, Any], source_hash: str, width: int, height: int, warnings: list[str]
) -> dict[str, Any]:
    """
    Description:
        Build deterministic visual intent without invoking a generative model.
    Required State:
        Payload, dimensions, tiles, and terrain vocabulary are validated.
    Usage:
        Persist as visual-brief.json and include in the generation cache key.
    Parameters:
        payload (dict[str, Any]): Validated world payload.
        source_hash (str): Hash of original payload bytes.
        width (int): Valid grid width.
        height (int): Valid grid height.
        warnings (list[str]): Compatibility warnings.
    Returns:
        dict[str, Any]: Versioned visual brief.
    Other I/O:
        - none
    """
    terrain_histogram = Counter(tile["terrain"] for tile in payload["tiles"])
    present_terrains = sorted(terrain_histogram)
    description = (
        "high top-down RTS terrain, readable cell-aligned geography, "
        + ", ".join(present_terrains)
        + ", preserve shorelines roads starts resources and traversability cues"
    )
    return {
        "contractVersion": CONTRACT_VERSION,
        "jobId": str(payload.get("job_id", "unknown")),
        "source": {"sha256": source_hash, "type": "worldpayload-json"},
        "dimensions": {"width": width, "height": height, "pixelsPerCell": 1},
        "terrainHistogram": dict(sorted(terrain_histogram.items())),
        "palette": {name: list(TERRAIN_COLORS[name]) for name in present_terrains},
        "prompt": {
            "version": PROMPT_VERSION,
            "description": description,
            "camera": "high top-down",
            "outline": "selective outline",
            "shading": "detailed shading",
            "detail": "highly detailed",
        },
        "authority": {
            "presentationOnly": True,
            "immutable": ["terrain", "traversability", "shorelines", "roads", "starts", "resources"],
        },
        "warnings": warnings,
    }


def write_contract(input_path: Path, output_directory: Path, allow_inferred: bool) -> dict[str, Any]:
    """
    Description:
        Validate a world payload and atomically publish all deterministic controls.
    Required State:
        Output directory may be created; no remote generation is performed.
    Usage:
        Main application entry point and test seam.
    Parameters:
        input_path (Path): JSON world payload.
        output_directory (Path): Destination artifact directory.
        allow_inferred (bool): Exploration-only dimension override.
    Returns:
        dict[str, Any]: Generation manifest template that was written.
    Other I/O:
        - files: reads input, writes five output artifacts
    """
    payload, source_bytes = read_payload(input_path)
    tile_lookup, inferred_width, inferred_height = validate_tiles(payload["tiles"])
    width, height, warnings = resolve_dimensions(payload, inferred_width, inferred_height, allow_inferred)
    require_complete_grid(tile_lookup, width, height)
    explicit_protected = collect_explicit_protected_coordinates(payload, width, height)
    semantic_pixels, protected_pixels, decoration_pixels = build_masks(
        tile_lookup, explicit_protected, width, height
    )

    source_hash = sha256_bytes(source_bytes)
    visual_brief = build_visual_brief(payload, source_hash, width, height, warnings)
    visual_brief_bytes = canonical_json_bytes(visual_brief)
    semantic_png = encode_rgb_png(width, height, semantic_pixels)
    protected_png = encode_rgb_png(width, height, protected_pixels)
    decoration_png = encode_rgb_png(width, height, decoration_pixels)

    immutable_inputs = {
        "visualBriefSha256": sha256_bytes(visual_brief_bytes),
        "semanticControlSha256": sha256_bytes(semantic_png),
        "protectedMaskSha256": sha256_bytes(protected_png),
        "decorationMaskSha256": sha256_bytes(decoration_png),
    }
    cache_key = sha256_bytes(canonical_json_bytes({"contractVersion": CONTRACT_VERSION, **immutable_inputs}))
    manifest = {
        "contractVersion": CONTRACT_VERSION,
        "state": "unsubmitted",
        "endpoint": PIXELLAB_ENDPOINT,
        "cacheKey": cache_key,
        "inputs": immutable_inputs,
        "request": {"seed": None, "candidateIndex": None},
        "remote": {"jobId": None, "usage": None},
        "output": {"sha256": None, "mimeType": None, "width": None, "height": None},
        "acceptance": {"state": "pending", "validator": None, "reason": None},
        "warnings": warnings,
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "visual-brief.json": visual_brief_bytes,
        "semantic-control.png": semantic_png,
        "protected-mask.png": protected_png,
        "decoration-mask.png": decoration_png,
        "generation-manifest.template.json": canonical_json_bytes(manifest),
    }
    for file_name, content in artifacts.items():
        temporary_path = output_directory / f".{file_name}.tmp"
        temporary_path.write_bytes(content)
        temporary_path.replace(output_directory / file_name)
    return manifest


def main() -> int:
    """
    Description:
        Parse CLI arguments and build one deterministic visual contract.
    Required State:
        Python 3.10+ and a readable JSON world payload are available.
    Usage:
        Run from the repository or through a future stage wrapper.
    Parameters:
        none
    Returns:
        int: Zero on success, two for invalid contracts.
    Other I/O:
        - stderr: actionable validation failures
        - files: delegates to write_contract
    """
    parser = argparse.ArgumentParser(description="Build deterministic PixelLab visual control artifacts")
    parser.add_argument("--input", required=True, type=Path, help="JSON worldpayload file")
    parser.add_argument("--output", required=True, type=Path, help="Output artifact directory")
    parser.add_argument(
        "--dimensions-from-tiles",
        action="store_true",
        help="Exploration only: override inconsistent declared dimensions (Gitea #55)",
    )
    arguments = parser.parse_args()
    try:
        manifest = write_contract(arguments.input, arguments.output, arguments.dimensions_from_tiles)
    except (ContractError, OSError) as error:
        print(f"visual contract rejected: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"state": manifest["state"], "cacheKey": manifest["cacheKey"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
