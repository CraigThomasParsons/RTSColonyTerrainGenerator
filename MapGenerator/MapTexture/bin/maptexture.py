#!/usr/bin/env python3
"""Offline, non-authoritative MapTexture presentation stage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import struct
import tempfile
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

CONTRACT_VERSION = "maptexture.v1"
CONTROL_SIZE = 128
OUTPUT_SIZE = 512
PIXELS_PER_TILE = OUTPUT_SIZE // CONTROL_SIZE
TERRAINS = {
    "deep_water": (24, 62, 104),
    "water": (38, 102, 146),
    "dirt": (126, 94, 58),
    "grass": (64, 119, 55),
    "rock": (123, 120, 111),
    "mountain": (92, 88, 84),
}
PROTECTED_TERRAINS = {"deep_water", "water", "rock", "mountain"}


class ContractError(ValueError):
    """An authoritative input or generated artifact violated the stage contract."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def png_bytes(width: int, height: int, pixels: list[tuple[int, int, int]]) -> bytes:
    if len(pixels) != width * height:
        raise ContractError("PNG pixel count does not match its dimensions")
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for red, green, blue in pixels[y * width:(y + 1) * width]:
            raw.extend((red, green, blue))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(
        b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def decode_png(data: bytes) -> tuple[int, int, list[tuple[int, int, int]]]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ContractError("candidate is not a PNG")
    offset = 8
    compressed = bytearray()
    width = height = 0
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload)
            if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ContractError("candidate PNG must be non-interlaced 8-bit RGB")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(compressed)
    stride = width * 3
    if len(raw) != height * (stride + 1):
        raise ContractError("candidate PNG body length is invalid")
    pixels: list[tuple[int, int, int]] = []
    previous = bytearray(stride)
    for row in range(height):
        start = row * (stride + 1)
        filter_kind = raw[start]
        encoded = raw[start + 1:start + 1 + stride]
        decoded = bytearray(stride)
        for index, value in enumerate(encoded):
            left = decoded[index - 3] if index >= 3 else 0
            up = previous[index]
            upper_left = previous[index - 3] if index >= 3 else 0
            if filter_kind == 0:
                decoded[index] = value
            elif filter_kind == 1:
                decoded[index] = (value + left) & 255
            elif filter_kind == 2:
                decoded[index] = (value + up) & 255
            elif filter_kind == 3:
                decoded[index] = (value + ((left + up) // 2)) & 255
            elif filter_kind == 4:
                p = left + up - upper_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upper_left)
                predictor = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
                decoded[index] = (value + predictor) & 255
            else:
                raise ContractError("candidate PNG uses an unsupported row filter")
        pixels.extend(tuple(decoded[i:i + 3]) for i in range(0, stride, 3))
        previous = decoded
    return width, height, pixels


@dataclass(frozen=True)
class Inputs:
    job_id: str
    width: int
    height: int
    heights: bytes
    terrain_layer: bytes
    tiles: list[dict]
    features: list[dict]
    playable: dict
    source_hashes: dict[str, str]


def load_inputs(heightmap: Path, heightmap_png: Path, worldpayload: Path, playable: Path) -> Inputs:
    paths = (heightmap, heightmap_png, worldpayload, playable)
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ContractError(f"required input not found: {', '.join(missing)}")
    heightmap_data = heightmap.read_bytes()
    if len(heightmap_data) < 16:
        raise ContractError("heightmap header is truncated")
    width, height, _seed = struct.unpack("<IIQ", heightmap_data[:16])
    cells = width * height
    if len(heightmap_data) != 16 + (2 * cells):
        raise ContractError("heightmap body length does not match declared dimensions")
    png_data = heightmap_png.read_bytes()
    if not png_data.startswith(b"\x89PNG\r\n\x1a\n") or len(png_data) < 24:
        raise ContractError("heightmap PNG is malformed")
    png_width, png_height = struct.unpack(">II", png_data[16:24])
    if (png_width, png_height) != (width, height):
        raise ContractError("heightmap PNG dimensions disagree with heightmap data")
    world_data = worldpayload.read_bytes()
    playable_data = playable.read_bytes()
    try:
        world = json.loads(world_data)
        playable_document = json.loads(playable_data)
    except json.JSONDecodeError as error:
        raise ContractError(f"JSON input is malformed: {error}") from None
    declared = world.get("map", {})
    if (declared.get("width_in_cells"), declared.get("height_in_cells")) != (width, height):
        raise ContractError("heightmap and worldpayload dimensions disagree")
    tile_width, tile_height = width * 2, height * 2
    if (tile_width, tile_height) != (CONTROL_SIZE, CONTROL_SIZE):
        raise ContractError(f"MapTexture v1 requires a {CONTROL_SIZE}x{CONTROL_SIZE} tile grid")
    tiles = world.get("tiles")
    if not isinstance(tiles, list) or len(tiles) != tile_width * tile_height:
        raise ContractError("worldpayload must contain one tile for every control coordinate")
    coordinates = {(tile.get("x"), tile.get("y")) for tile in tiles if isinstance(tile, dict)}
    expected = {(x, y) for y in range(tile_height) for x in range(tile_width)}
    if coordinates != expected:
        raise ContractError("worldpayload tile coordinates are incomplete or duplicated")
    job_id = str(world.get("job_id", ""))
    if not job_id or str(playable_document.get("job_id", "")) != job_id:
        raise ContractError("worldpayload and playable job identifiers disagree")
    hashes = {
        "heightmap": sha256(heightmap_data),
        "heightmapPng": sha256(png_data),
        "worldpayload": sha256(world_data),
        "playable": sha256(playable_data),
    }
    features = world.get("features", [])
    if not isinstance(features, list):
        raise ContractError("worldpayload features must be an array")
    return Inputs(job_id, width, height, heightmap_data[16:16 + cells],
                  heightmap_data[16 + cells:], tiles, features, playable_document, hashes)


def build_controls(inputs: Inputs, controls: Path) -> dict:
    by_coordinate = {(tile["x"], tile["y"]): tile for tile in inputs.tiles}
    semantic: list[tuple[int, int, int]] = []
    protected: list[tuple[int, int, int]] = []
    topology: list[tuple[int, int, int]] = []
    decoration: list[tuple[int, int, int]] = []
    gameplay = set()
    for collection in ("start_zones", "resource_clusters", "settlement_labels"):
        for item in inputs.playable.get(collection, []):
            gameplay.add((item.get("x"), item.get("y")))
    for feature in inputs.features:
        if isinstance(feature, dict):
            gameplay.add((feature.get("x"), feature.get("y")))
    for y in range(CONTROL_SIZE):
        for x in range(CONTROL_SIZE):
            tile = by_coordinate[(x, y)]
            terrain = tile.get("terrain")
            if terrain not in TERRAINS:
                raise ContractError(f"unsupported terrain {terrain!r} at ({x},{y})")
            color = TERRAINS[terrain]
            semantic.append(color)
            neighbors = [by_coordinate[(nx, ny)].get("terrain") for nx, ny in
                         ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                         if 0 <= nx < CONTROL_SIZE and 0 <= ny < CONTROL_SIZE]
            edge = any(neighbor != terrain for neighbor in neighbors)
            feature = bool(tile.get("features"))
            is_protected = terrain in PROTECTED_TERRAINS or edge or feature or (x, y) in gameplay
            protected.append((255, 255, 255) if is_protected else (0, 0, 0))
            topology.append((255, 255, 255) if edge else (0, 0, 0))
            free = not is_protected and terrain in {"grass", "dirt"}
            decoration.append((255, 255, 255) if free else (0, 0, 0))
    artifacts = {
        "semantic-control.png": png_bytes(CONTROL_SIZE, CONTROL_SIZE, semantic),
        "protected-mask.png": png_bytes(CONTROL_SIZE, CONTROL_SIZE, protected),
        "topology-control.png": png_bytes(CONTROL_SIZE, CONTROL_SIZE, topology),
        "decoration-mask.png": png_bytes(CONTROL_SIZE, CONTROL_SIZE, decoration),
    }
    for name, data in artifacts.items():
        atomic_write(controls / name, data)
    brief = {
        "contractVersion": CONTRACT_VERSION,
        "jobId": inputs.job_id,
        "controlDimensions": {"width": CONTROL_SIZE, "height": CONTROL_SIZE},
        "outputDimensions": {"width": OUTPUT_SIZE, "height": OUTPUT_SIZE},
        "pixelsPerTile": PIXELS_PER_TILE,
        "purpose": "non-authoritative terrain texture background",
        "prohibitedFeatures": ["text", "units", "buildings", "new roads", "new coastlines"],
    }
    atomic_write(controls / "visual-brief.json", canonical_bytes(brief))
    return {name: sha256(data) for name, data in artifacts.items()} | {
        "visual-brief.json": sha256(canonical_bytes(brief))}


class TextureProvider(Protocol):
    name: str

    def generate(self, controls: Path, seed: int, candidate_index: int) -> bytes: ...


class OfflineTextureProvider:
    """Deterministic fixture provider. It has no credential or network seam."""

    name = "offline-deterministic"

    def generate(self, controls: Path, seed: int, candidate_index: int) -> bytes:
        _, _, semantics = decode_png((controls / "semantic-control.png").read_bytes())
        _, _, protected = decode_png((controls / "protected-mask.png").read_bytes())
        rng = random.Random((seed << 16) ^ candidate_index)
        output: list[tuple[int, int, int]] = []
        for y in range(OUTPUT_SIZE):
            tile_y = y // PIXELS_PER_TILE
            for x in range(OUTPUT_SIZE):
                tile_x = x // PIXELS_PER_TILE
                index = tile_y * CONTROL_SIZE + tile_x
                base = semantics[index]
                protected_tile = protected[index] == (255, 255, 255)
                variation = 0 if protected_tile else rng.randint(-9, 9)
                grain = ((x * 17 + y * 31 + seed + candidate_index * 13) % 7) - 3
                delta = variation + (0 if protected_tile else grain)
                output.append(tuple(max(0, min(255, channel + delta)) for channel in base))
        return png_bytes(OUTPUT_SIZE, OUTPUT_SIZE, output)


def validate_candidate(controls: Path, candidate: Path, expected_hashes: dict[str, str]) -> dict:
    failures: list[str] = []
    for name, expected in expected_hashes.items():
        path = controls / name
        if not path.is_file() or sha256(path.read_bytes()) != expected:
            failures.append(f"control hash mismatch: {name}")
    width, height, pixels = decode_png(candidate.read_bytes())
    if (width, height) != (OUTPUT_SIZE, OUTPUT_SIZE):
        failures.append(f"candidate dimensions are {width}x{height}, expected {OUTPUT_SIZE}x{OUTPUT_SIZE}")
    _, _, semantics = decode_png((controls / "semantic-control.png").read_bytes())
    _, _, protected = decode_png((controls / "protected-mask.png").read_bytes())
    _, _, topology = decode_png((controls / "topology-control.png").read_bytes())
    if not failures:
        for tile_y in range(CONTROL_SIZE):
            for tile_x in range(CONTROL_SIZE):
                index = tile_y * CONTROL_SIZE + tile_x
                center_x = tile_x * PIXELS_PER_TILE + PIXELS_PER_TILE // 2
                center_y = tile_y * PIXELS_PER_TILE + PIXELS_PER_TILE // 2
                actual = pixels[center_y * OUTPUT_SIZE + center_x]
                expected = semantics[index]
                distance = max(abs(actual[channel] - expected[channel]) for channel in range(3))
                if protected[index] == (255, 255, 255) and distance > 4:
                    failures.append(f"protected obstruction at tile ({tile_x},{tile_y})")
                if topology[index] == (255, 255, 255) and distance > 4:
                    failures.append(f"topology displacement at tile ({tile_x},{tile_y})")
                if failures:
                    break
            if failures:
                break
    return {
        "contractVersion": CONTRACT_VERSION,
        "structurallyValid": len(failures) == 0,
        "eligibleForApproval": len(failures) == 0,
        "failures": failures,
        "candidateSha256": sha256(candidate.read_bytes()),
        "dimensions": {"width": width, "height": height},
    }


def run_stage(args: argparse.Namespace, provider: TextureProvider | None = None) -> dict:
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ContractError("output directory must be empty; MapTexture run bundles are immutable")
    controls = output / "controls"
    inputs = load_inputs(Path(args.heightmap), Path(args.heightmap_png),
                         Path(args.worldpayload), Path(args.playable))
    control_hashes = build_controls(inputs, controls)
    seeds = [args.seed + index for index in range(args.candidates)]
    plan = {
        "contractVersion": CONTRACT_VERSION,
        "jobId": inputs.job_id,
        "provider": "offline-deterministic",
        "networkAllowed": False,
        "paidSubmissions": 0,
        "sourceHashes": inputs.source_hashes,
        "controlHashes": control_hashes,
        "candidates": [{"candidateIndex": index, "seed": seed}
                       for index, seed in enumerate(seeds)],
    }
    plan["planId"] = sha256(canonical_bytes(plan))
    atomic_write(output / "run-plan.json", canonical_bytes(plan))
    selected_provider = provider or OfflineTextureProvider()
    if selected_provider.name != "offline-deterministic":
        raise ContractError("MapTexture v1 permits only the offline deterministic provider")
    for index, seed in enumerate(seeds):
        directory = output / "candidates" / f"candidate-{index:03d}"
        candidate_data = selected_provider.generate(controls, seed, index)
        atomic_write(directory / "candidate.png", candidate_data)
        manifest = {
            "contractVersion": CONTRACT_VERSION,
            "provider": selected_provider.name,
            "seed": seed,
            "candidateIndex": index,
            "networkUsed": False,
            "paidSubmissions": 0,
            "controlHashes": control_hashes,
            "request": {
                "visualBriefSha256": control_hashes["visual-brief.json"],
                "outputDimensions": {"width": OUTPUT_SIZE, "height": OUTPUT_SIZE},
                "seed": seed,
                "candidateIndex": index,
            },
            "candidateSha256": sha256(candidate_data),
        }
        atomic_write(directory / "generation-manifest.json", canonical_bytes(manifest))
        validation = validate_candidate(controls, directory / "candidate.png", control_hashes)
        atomic_write(directory / "validation.json", canonical_bytes(validation))
    return plan


def decide(args: argparse.Namespace, approved: bool) -> dict:
    output = Path(args.output)
    if not args.actor.strip() or not args.reason.strip():
        raise ContractError("actor and reason are required for a human decision")
    directory = output / "candidates" / f"candidate-{args.candidate:03d}"
    candidate = directory / "candidate.png"
    validation_path = directory / "validation.json"
    if not candidate.is_file() or not validation_path.is_file():
        raise ContractError("candidate evidence is incomplete")
    validation = json.loads(validation_path.read_bytes())
    if approved and not validation.get("eligibleForApproval"):
        raise ContractError("candidate is not eligible for approval")
    for prior in (output / "candidates").glob("candidate-*/approval.json"):
        document = json.loads(prior.read_bytes())
        if approved and document.get("decision") == "approved" and prior.parent != directory:
            document["decision"] = "rejected"
            document["reason"] = "Superseded by a later explicit approval."
            atomic_write(prior, canonical_bytes(document))
    record = {
        "contractVersion": CONTRACT_VERSION,
        "decision": "approved" if approved else "rejected",
        "actor": args.actor.strip(),
        "reason": args.reason.strip(),
        "decidedAtUtc": datetime.now(timezone.utc).isoformat(),
        "candidateSha256": sha256(candidate.read_bytes()),
        "validationSha256": sha256(validation_path.read_bytes()),
    }
    atomic_write(directory / "approval.json", canonical_bytes(record))
    if approved:
        temporary = output / ".background.png.tmp"
        shutil.copyfile(candidate, temporary)
        os.replace(temporary, output / "background.png")
    else:
        background = output / "background.png"
        if background.is_file() and sha256(background.read_bytes()) == sha256(candidate.read_bytes()):
            background.unlink()
    return record


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    for name in ("heightmap", "heightmap-png", "worldpayload", "playable", "output"):
        run.add_argument(f"--{name}", required=True)
    run.add_argument("--seed", type=int, default=1)
    run.add_argument("--candidates", type=int, choices=range(1, 5), default=3)
    for command in ("approve", "reject"):
        decision = commands.add_parser(command)
        decision.add_argument("--output", required=True)
        decision.add_argument("--candidate", required=True, type=int)
        decision.add_argument("--actor", required=True)
        decision.add_argument("--reason", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        result = run_stage(args) if args.command == "run" else decide(args, args.command == "approve")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ContractError, OSError) as error:
        print(f"MapTexture failed: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
