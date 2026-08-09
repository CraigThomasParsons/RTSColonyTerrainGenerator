#!/usr/bin/env python3
"""Structural validation of one PixelLab candidate against its controls (#52).

Every check in this module is deterministic, offline, and derived from
authoritative artifacts: the issue #50 control set, the issue #51 candidate
manifest, and the run plan. Two properties are load-bearing.

First, validation never reads the generated image's pixels. It reads the PNG
header for dimensions and hashes the file for provenance, and that is all.
Gameplay truth comes from the deterministic masks, never from pixels a model
invented. Protected-landmark alignment evidence is therefore evidence *about*
the masks and about the candidate's one-to-one addressability, not a claim that
the artwork drew a road in the right place — only a human can judge that.

Second, validation may reject a candidate but can never approve one. A report
produced here marks a candidate eligible for an operator decision; issuing that
decision is `candidate_approval`'s job and requires a named human.
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any

import candidate_plan
import candidate_state
import pixellab_modules


visual_contract = pixellab_modules.load_visual_contract()
pixellab_client = pixellab_modules.load_pixellab_client()

canonical_json_bytes = visual_contract.canonical_json_bytes
sha256_bytes = visual_contract.sha256_bytes

CONTRACT_VERSION = visual_contract.CONTRACT_VERSION
VALIDATION_VERSION = "1"
VALIDATION_REPORT_NAME = "validation.json"

# Colour used by visual_contract.py for a protected cell in protected-mask.png.
PROTECTED_MASK_COLOR = (255, 255, 255)

# The deterministic encoder in visual_contract.py always emits 8-bit truecolour
# with filter type 0 on every scanline. Anything else did not come from that
# encoder and must not be treated as an authoritative mask.
EXPECTED_PNG_BIT_DEPTH = 8
EXPECTED_PNG_COLOR_TYPE = 2
EXPECTED_PNG_FILTER_TYPE = 0


class CandidateValidationError(ValueError):
    """Represent a candidate that cannot be validated at all."""


# --------------------------------------------------------------------------
# Deterministic mask decoding
# --------------------------------------------------------------------------


def decode_deterministic_rgb_png(image_bytes: bytes, description: str) -> tuple[int, int, list[tuple[int, int, int]]]:
    """
    Description:
        Decode a mask produced by visual_contract.py into row-major RGB pixels.
    Required State:
        The image must be 8-bit truecolour with filter type 0 on every row,
        which is the only form visual_contract.py emits.
    Usage:
        Use for the deterministic control masks only, never for generated art.
    Parameters:
        image_bytes (bytes): Complete PNG file content.
        description (str): Artifact name used in failure messages.
    Returns:
        tuple[int, int, list[tuple[int, int, int]]]: Width, height, and pixels.
    Other I/O:
        - none
    """
    # Guard on the container before trusting any offset inside it.
    if not image_bytes.startswith(pixellab_client.PNG_SIGNATURE):
        raise CandidateValidationError(f"{description} is not a PNG file")

    header_fields = struct.unpack(">IIBBBBB", image_bytes[16:29])
    width, height, bit_depth, color_type, compression, filter_method, interlace = header_fields
    if bit_depth != EXPECTED_PNG_BIT_DEPTH or color_type != EXPECTED_PNG_COLOR_TYPE:
        raise CandidateValidationError(
            f"{description} must be 8-bit truecolour to be a deterministic mask; "
            f"found bit depth {bit_depth} and colour type {color_type}"
        )
    if compression != 0 or filter_method != 0 or interlace != 0:
        raise CandidateValidationError(f"{description} uses an unsupported PNG encoding variant")

    # Concatenate every IDAT chunk before inflating; the encoder writes one, but
    # a concatenating reader stays correct if that ever changes.
    compressed_data = bytearray()
    offset = len(pixellab_client.PNG_SIGNATURE)
    while offset + 8 <= len(image_bytes):
        chunk_length = struct.unpack(">I", image_bytes[offset : offset + 4])[0]
        chunk_type = image_bytes[offset + 4 : offset + 8]
        chunk_data = image_bytes[offset + 8 : offset + 8 + chunk_length]
        if chunk_type == b"IDAT":
            compressed_data.extend(chunk_data)
        if chunk_type == b"IEND":
            break
        offset += 12 + chunk_length

    try:
        raw_scanlines = zlib.decompress(bytes(compressed_data))
    except zlib.error as error:
        raise CandidateValidationError(f"{description} pixel data could not be decompressed: {error}") from None

    bytes_per_row = width * 3
    expected_length = height * (bytes_per_row + 1)
    if len(raw_scanlines) != expected_length:
        raise CandidateValidationError(
            f"{description} decoded to {len(raw_scanlines)} bytes; expected {expected_length}"
        )

    pixels: list[tuple[int, int, int]] = []
    for row_index in range(height):
        row_start = row_index * (bytes_per_row + 1)
        # Only the null filter is accepted, so a mask never needs reconstruction
        # arithmetic that could silently mis-decode a landmark.
        if raw_scanlines[row_start] != EXPECTED_PNG_FILTER_TYPE:
            raise CandidateValidationError(
                f"{description} row {row_index} uses PNG filter {raw_scanlines[row_start]}; "
                "only the null filter is accepted for deterministic masks"
            )
        row_bytes = raw_scanlines[row_start + 1 : row_start + 1 + bytes_per_row]
        for column_index in range(width):
            pixel_start = column_index * 3
            pixels.append(
                (
                    row_bytes[pixel_start],
                    row_bytes[pixel_start + 1],
                    row_bytes[pixel_start + 2],
                )
            )
    return width, height, pixels


def collect_protected_coordinates(protected_mask_bytes: bytes) -> list[tuple[int, int]]:
    """
    Description:
        Read the authoritative protected cells straight out of the mask.
    Required State:
        The mask is the deterministic protected-mask.png for this run.
    Usage:
        Use to build alignment evidence without consulting generated pixels.
    Parameters:
        protected_mask_bytes (bytes): Complete protected-mask.png content.
    Returns:
        list[tuple[int, int]]: Protected cell coordinates in row-major order.
    Other I/O:
        - none
    """
    width, height, pixels = decode_deterministic_rgb_png(protected_mask_bytes, "protected-mask.png")
    protected_coordinates: list[tuple[int, int]] = []
    for row_index in range(height):
        for column_index in range(width):
            if pixels[row_index * width + column_index] == PROTECTED_MASK_COLOR:
                protected_coordinates.append((column_index, row_index))
    return protected_coordinates


# --------------------------------------------------------------------------
# Check accumulation
# --------------------------------------------------------------------------


class CheckLedger:
    """Accumulate named pass/fail checks so a report explains itself."""

    def __init__(self) -> None:
        """
        Description:
            Start an empty ordered ledger of validation checks.
        Required State:
            None.
        Usage:
            Create one per candidate validation.
        Parameters:
            none
        Returns:
            None: Constructs the ledger.
        Other I/O:
            - none
        """
        self.checks: list[dict[str, Any]] = []

    def record(self, name: str, passed: bool, detail: str) -> bool:
        """
        Description:
            Record the outcome of one named check in declaration order.
        Required State:
            None.
        Usage:
            Call once per check, including checks that pass.
        Parameters:
            name (str): Stable kebab-case check identifier.
            passed (bool): Whether the check held.
            detail (str): Short explanation, shown whether or not it passed.
        Returns:
            bool: The same passed value, so callers can branch on it.
        Other I/O:
            - none
        """
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        return passed

    def failures(self) -> list[str]:
        """
        Description:
            List the names of every failed check, in declaration order.
        Required State:
            All checks have been recorded.
        Usage:
            Call when assembling the report and when deciding eligibility.
        Parameters:
            none
        Returns:
            list[str]: Names of failing checks.
        Other I/O:
            - none
        """
        return [check["name"] for check in self.checks if not check["passed"]]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def read_candidate_manifest(candidate_directory: Path) -> dict[str, Any]:
    """
    Description:
        Read the issue #51 candidate manifest for one candidate directory.
    Required State:
        The candidate directory was produced by an orchestrated run.
    Usage:
        Call at the start of validation and again at approval time.
    Parameters:
        candidate_directory (Path): Directory owning one candidate.
    Returns:
        dict[str, Any]: Parsed candidate manifest.
    Other I/O:
        - files: reads generation-manifest.json
    """
    manifest_path = candidate_directory / pixellab_client.CANDIDATE_MANIFEST_NAME
    if not manifest_path.is_file():
        raise CandidateValidationError(f"candidate manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_bytes())
    except json.JSONDecodeError as error:
        raise CandidateValidationError(f"candidate manifest is not valid JSON: {error}") from None
    if not isinstance(manifest, dict):
        raise CandidateValidationError(f"candidate manifest must be a JSON object: {manifest_path}")
    return manifest


def validate_candidate(
    controls_directory: Path,
    candidate_directory: Path,
    run_plan: dict[str, Any],
    candidate_index: int,
) -> dict[str, Any]:
    """
    Description:
        Run every deterministic structural check for one candidate.
    Required State:
        The controls directory is the read-only issue #50 artifact set that the
        run plan names, and the candidate directory belongs to that plan.
    Usage:
        Call after generating a candidate and again immediately before approval.
    Parameters:
        controls_directory (Path): Read-only issue #50 artifact directory.
        candidate_directory (Path): Directory owning one candidate.
        run_plan (dict[str, Any]): Plan the candidate belongs to.
        candidate_index (int): Candidate ordinal being validated.
    Returns:
        dict[str, Any]: Deterministic validation report, free of clock readings.
    Other I/O:
        - files: reads the control artifacts, candidate manifest, and image header
    """
    planned_entry = candidate_plan.candidate_entry(run_plan, candidate_index)
    ledger = CheckLedger()
    manifest = read_candidate_manifest(candidate_directory)

    # ---- contract and schema versions -----------------------------------
    ledger.record(
        "contract-version-matches",
        manifest.get("contractVersion") == CONTRACT_VERSION,
        f"candidate manifest contractVersion is {manifest.get('contractVersion')!r}, expected {CONTRACT_VERSION!r}",
    )
    ledger.record(
        "plan-version-matches",
        run_plan.get("planVersion") == candidate_plan.PLAN_VERSION,
        f"run plan planVersion is {run_plan.get('planVersion')!r}, expected {candidate_plan.PLAN_VERSION!r}",
    )

    # ---- immutable control inputs ---------------------------------------
    # load_control_artifacts re-hashes every issue #50 artifact against the
    # template, so an edited control image fails here rather than silently
    # producing a candidate with false provenance.
    control_artifacts = pixellab_client.load_control_artifacts(controls_directory)
    ledger.record(
        "control-artifact-hashes-intact",
        True,
        "every issue #50 control artifact re-hashed to the value recorded in the template",
    )
    template_inputs = control_artifacts.source_manifest.get("inputs", {})
    ledger.record(
        "candidate-inputs-match-controls",
        manifest.get("inputs") == template_inputs,
        "candidate manifest inputs equal the issue #50 template inputs",
    )
    ledger.record(
        "control-inputs-match-plan",
        run_plan.get("controls", {}).get("inputs") == template_inputs,
        "run plan records the same immutable control hashes as the controls directory",
    )
    ledger.record(
        "endpoint-matches-plan",
        manifest.get("endpoint") == run_plan.get("controls", {}).get("endpoint"),
        f"candidate endpoint is {manifest.get('endpoint')!r}",
    )

    # ---- candidate index and seed ---------------------------------------
    recorded_request = manifest.get("request", {})
    ledger.record(
        "candidate-index-matches-plan",
        recorded_request.get("candidateIndex") == planned_entry["candidateIndex"],
        f"manifest candidateIndex {recorded_request.get('candidateIndex')!r} versus plan {planned_entry['candidateIndex']!r}",
    )
    ledger.record(
        "seed-matches-plan",
        recorded_request.get("seed") == planned_entry["seed"],
        f"manifest seed {recorded_request.get('seed')!r} versus plan {planned_entry['seed']!r}",
    )

    # ---- cache key -------------------------------------------------------
    # Rebuilding the request offline from the controls reproduces the cache key
    # and body hash, proving the manifest describes a request that these exact
    # controls and this exact seed would produce.
    rebuild_settings = pixellab_client.AdapterSettings(
        controls_directory=controls_directory,
        output_directory=candidate_directory,
        cache_directory=candidate_directory,
        seed=planned_entry["seed"],
        candidate_index=planned_entry["candidateIndex"],
    )
    _, rebuilt_body, rebuilt_cache_key, _ = pixellab_client.prepare_generation(rebuild_settings)
    ledger.record(
        "request-cache-key-reproducible",
        recorded_request.get("requestCacheKey") == rebuilt_cache_key,
        f"recorded requestCacheKey {recorded_request.get('requestCacheKey')!r} versus rebuilt {rebuilt_cache_key!r}",
    )
    ledger.record(
        "request-body-hash-reproducible",
        recorded_request.get("bodySha256") == sha256_bytes(canonical_json_bytes(rebuilt_body)),
        "recorded request bodySha256 matches the body rebuilt from the controls",
    )

    # ---- brief, mask, and requested dimensions ---------------------------
    brief_dimensions = control_artifacts.visual_brief.get("dimensions", {})
    brief_width = brief_dimensions.get("width")
    brief_height = brief_dimensions.get("height")
    requested_size = rebuilt_body.get("image_size", {})
    ledger.record(
        "requested-size-matches-brief",
        (requested_size.get("width"), requested_size.get("height")) == (brief_width, brief_height),
        f"request image_size {requested_size} versus brief {brief_width}x{brief_height}",
    )

    mask_dimensions: dict[str, tuple[int, int]] = {}
    for mask_name in (
        pixellab_client.SEMANTIC_CONTROL_NAME,
        pixellab_client.PROTECTED_MASK_NAME,
        pixellab_client.DECORATION_MASK_NAME,
    ):
        mask_dimensions[mask_name] = pixellab_client.read_png_dimensions(
            (controls_directory / mask_name).read_bytes()
        )
    ledger.record(
        "mask-dimensions-agree",
        all(size == (brief_width, brief_height) for size in mask_dimensions.values()),
        f"control mask dimensions {mask_dimensions} versus brief {brief_width}x{brief_height}",
    )

    # ---- issue #60 image-size bound --------------------------------------
    # The bound is re-checked here so a candidate directory carried between
    # machines cannot be approved for a map the endpoint could never render.
    within_image_size_bounds = True
    try:
        pixellab_client.require_submittable_image_size(brief_width, brief_height)
    except pixellab_client.ContractError as error:
        within_image_size_bounds = False
        ledger.record("image-size-within-pixellab-bounds", False, str(error))
    if within_image_size_bounds:
        ledger.record(
            "image-size-within-pixellab-bounds",
            True,
            f"{brief_width}x{brief_height} is inside the PixelLab image_size range "
            f"{pixellab_client.MINIMUM_IMAGE_EDGE}-{pixellab_client.MAXIMUM_IMAGE_EDGE} (Gitea #60)",
        )

    # ---- issue #55 exploration override ----------------------------------
    exploration_only = bool(run_plan.get("explorationOnly"))
    ledger.record(
        "no-exploration-dimension-override",
        not exploration_only,
        "run plan carries no EXPLORATION ONLY dimension warning (Gitea #55)"
        if not exploration_only
        else "run plan used the exploration-only dimension override; candidates are ineligible (Gitea #55)",
    )
    manifest_warnings = [
        warning for warning in manifest.get("warnings", []) if warning.startswith("EXPLORATION ONLY")
    ]
    ledger.record(
        "candidate-carries-no-exploration-warning",
        not manifest_warnings,
        f"candidate manifest exploration warnings: {manifest_warnings}",
    )

    # ---- generated image -------------------------------------------------
    candidate_image_path = candidate_directory / pixellab_client.CANDIDATE_IMAGE_NAME
    image_present = candidate_image_path.is_file()
    evidence: dict[str, Any] = {}

    if image_present:
        image_bytes = candidate_image_path.read_bytes()
        # Only the container and the header are read. Pixel content is never
        # inspected, because gameplay truth may not come from generated art.
        is_png = image_bytes.startswith(pixellab_client.PNG_SIGNATURE)
        ledger.record("candidate-image-is-png", is_png, "candidate.png carries a PNG signature")
        recorded_output = manifest.get("output", {})
        ledger.record(
            "candidate-image-mime-recorded",
            recorded_output.get("mimeType") == pixellab_client.EXPECTED_IMAGE_MIME_TYPE,
            f"manifest output mimeType is {recorded_output.get('mimeType')!r}",
        )
        actual_hash = sha256_bytes(image_bytes)
        ledger.record(
            "candidate-image-hash-matches-manifest",
            recorded_output.get("sha256") == actual_hash,
            "candidate.png hash equals the hash recorded in the manifest",
        )
        if is_png:
            actual_width, actual_height = pixellab_client.read_png_dimensions(image_bytes)
            ledger.record(
                "candidate-image-dimensions-match-request",
                (actual_width, actual_height) == (requested_size.get("width"), requested_size.get("height")),
                f"candidate.png is {actual_width}x{actual_height}; {requested_size} was requested",
            )
            ledger.record(
                "candidate-image-dimensions-match-masks",
                (actual_width, actual_height) == (brief_width, brief_height),
                f"candidate.png is {actual_width}x{actual_height}; masks are {brief_width}x{brief_height}",
            )
            evidence["candidateImage"] = {
                "sha256": actual_hash,
                "width": actual_width,
                "height": actual_height,
                "mimeType": pixellab_client.EXPECTED_IMAGE_MIME_TYPE,
            }
    else:
        ledger.record(
            "candidate-image-present",
            False,
            "no candidate.png exists; an offline dry-run candidate has no image to approve",
        )

    # ---- protected-landmark alignment evidence ---------------------------
    protected_coordinates = collect_protected_coordinates(
        (controls_directory / pixellab_client.PROTECTED_MASK_NAME).read_bytes()
    )
    protected_digest = sha256_bytes(
        canonical_json_bytes([[column, row] for column, row in protected_coordinates])
    )
    evidence["protectedLandmarks"] = {
        "basis": "deterministic-masks",
        "cellCount": len(protected_coordinates),
        "coordinatesSha256": protected_digest,
        "protectedMaskSha256": template_inputs.get("protectedMaskSha256"),
        "note": (
            "Alignment evidence is derived from protected-mask.png only. Generated pixels are "
            "never inspected and never establish gameplay truth; visual fidelity remains a "
            "human judgement recorded through candidate_approval."
        ),
    }
    # A protected cell is addressable only when the candidate raster shares the
    # mask's grid exactly. That one-to-one correspondence is the strongest
    # alignment claim that can honestly be made without reading generated art.
    alignment_addressable = (not image_present) or (
        evidence.get("candidateImage", {}).get("width") == brief_width
        and evidence.get("candidateImage", {}).get("height") == brief_height
    )
    ledger.record(
        "protected-landmarks-addressable",
        alignment_addressable and len(protected_coordinates) > 0,
        f"{len(protected_coordinates)} protected cells map one-to-one onto the candidate raster",
    )

    failures = ledger.failures()
    # A dry-run candidate is a legitimate, complete offline outcome, so its
    # missing image must not read as a validation defect.
    non_image_failures = [name for name in failures if name != "candidate-image-present"]
    is_structurally_valid = not non_image_failures
    eligible_for_approval = not failures and image_present

    if not is_structurally_valid:
        resulting_state = candidate_state.STATE_REJECTED
    elif image_present:
        resulting_state = candidate_state.STATE_GENERATED
    else:
        resulting_state = candidate_state.STATE_DRY_RUN

    return {
        "contractVersion": CONTRACT_VERSION,
        "validationVersion": VALIDATION_VERSION,
        "planId": run_plan.get("planId"),
        "candidateIndex": planned_entry["candidateIndex"],
        "seed": planned_entry["seed"],
        "imagePresent": image_present,
        "structurallyValid": is_structurally_valid,
        "eligibleForApproval": eligible_for_approval,
        "resultingState": resulting_state,
        "failures": failures,
        "checks": ledger.checks,
        "evidence": evidence,
    }


def write_validation_report(candidate_directory: Path, report: dict[str, Any]) -> Path:
    """
    Description:
        Publish a validation report atomically beside its candidate.
    Required State:
        The candidate directory exists.
    Usage:
        Call after every validation so the evidence trail is on disk.
    Parameters:
        candidate_directory (Path): Directory owning one candidate.
        report (dict[str, Any]): Report produced by validate_candidate.
    Returns:
        Path: Path of the published report.
    Other I/O:
        - files: writes validation.json through a temporary file and rename
    """
    report_path = candidate_directory / VALIDATION_REPORT_NAME
    pixellab_client.write_file_atomically(report_path, canonical_json_bytes(report))
    return report_path
