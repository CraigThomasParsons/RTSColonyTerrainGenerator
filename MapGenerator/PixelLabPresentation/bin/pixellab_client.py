#!/usr/bin/env python3
"""Opt-in PixelLab v2 adapter for the presentation-only visual lane (Gitea #51).

This module turns the deterministic control artifacts produced by issue #50
into a PixelLab v2 request, optionally submits that request as a background
job, polls it within explicit bounds, and records complete provenance in a
copied generation manifest.

Boundaries enforced here:

- The bearer token is read from the environment only at live-call time and is
  never accepted as an argument, persisted, printed, or attached to an error.
- Only a fixed endpoint allowlist may be contacted.
- A content-addressed cache hit performs no generation request at all.
- The issue #50 source artifacts are read-only; every write lands in a
  separate candidate directory through an atomic replace.
- Generation is never resubmitted automatically. Polling may retry; paying for
  a second image always requires a new explicit invocation.

Generated pixels remain presentation-only. See
docs/adr/0001-pixellab-presentation-only.md.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol


# --------------------------------------------------------------------------
# Contract constants
#
# These mirror the authoritative PixelLab v2 references (llms.txt and
# openapi.json) and the issue #50 manifest contract. They are deliberately
# hard-coded so that a typo in an operator argument can never redirect a paid
# request to an unintended endpoint.
# --------------------------------------------------------------------------

CONTRACT_VERSION = "1.0"
PIXELLAB_BASE_URL = "https://api.pixellab.ai/v2"
TOKEN_ENVIRONMENT_VARIABLE = "PIXELLAB_API_TOKEN"
REDACTION_PLACEHOLDER = "***REDACTED***"

# The generation allowlist is intentionally a one-element set. Issue #50's
# manifest contract pins this endpoint with a JSON `const`, so anything else
# would produce an artifact that cannot validate.
ALLOWED_GENERATION_ENDPOINTS = frozenset({"/create-image-pixflux-background"})

# Read-only endpoints never create a billable generation. They are listed
# separately so that the generation allowlist stays exactly one entry wide.
BALANCE_ENDPOINT = "/balance"
BACKGROUND_JOB_ENDPOINT_TEMPLATE = "/background-jobs/{job_id}"

# PixelLab rejects any image_size outside this inclusive range, so a map that
# cannot be expressed at one pixel per cell must fail before it is submitted.
MINIMUM_IMAGE_EDGE = 16
MAXIMUM_IMAGE_EDGE = 400

# Style vocabularies copied from the v2 OpenAPI enums. Issue #50 already emits
# values from these sets; validating locally converts a would-be paid HTTP 422
# into a free failure.
ALLOWED_CAMERA_VIEWS = frozenset({"side", "low top-down", "high top-down"})
ALLOWED_OUTLINES = frozenset(
    {"single color black outline", "single color outline", "selective outline", "lineless"}
)
ALLOWED_SHADINGS = frozenset(
    {"flat shading", "basic shading", "medium shading", "detailed shading", "highly detailed shading"}
)
ALLOWED_DETAILS = frozenset({"low detail", "medium detail", "highly detailed"})

# PixelLab returns pixel art as base64 PNG. Anything else is a contract break.
EXPECTED_IMAGE_FORMAT = "png"
EXPECTED_IMAGE_MIME_TYPE = "image/png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Terminal job states reported by GET /background-jobs/{job_id}.
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_PROCESSING = "processing"

# Artifact file names. The template belongs to issue #50 and is never written.
SOURCE_MANIFEST_NAME = "generation-manifest.template.json"
CANDIDATE_MANIFEST_NAME = "generation-manifest.json"
CANDIDATE_IMAGE_NAME = "candidate.png"
VISUAL_BRIEF_NAME = "visual-brief.json"
SEMANTIC_CONTROL_NAME = "semantic-control.png"
PROTECTED_MASK_NAME = "protected-mask.png"
DECORATION_MASK_NAME = "decoration-mask.png"

# Maps each control artifact to the manifest `inputs` key that records its hash.
CONTROL_ARTIFACT_HASH_KEYS = {
    VISUAL_BRIEF_NAME: "visualBriefSha256",
    SEMANTIC_CONTROL_NAME: "semanticControlSha256",
    PROTECTED_MASK_NAME: "protectedMaskSha256",
    DECORATION_MASK_NAME: "decorationMaskSha256",
}

# Default request tuning. `text_guidance_scale` and `init_image_strength` are
# pinned rather than defaulted server-side so that the recorded request body
# fully determines the cache key.
DEFAULT_TEXT_GUIDANCE_SCALE = 8
DEFAULT_INIT_IMAGE_STRENGTH = 300
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_MAXIMUM_POLL_ATTEMPTS = 60
DEFAULT_MAXIMUM_POLL_SECONDS = 900.0

# Poll responses that mean "not finished yet" rather than "broken". PixelLab
# uses 423 with a Retry-After header on several of its job-status endpoints, so
# the adapter treats it as retryable wherever it appears.
RETRYABLE_POLL_STATUS_CODES = frozenset({423, 429, 529})

# Exit codes chosen so that an operator or wrapper can branch without parsing
# text. docs/python.md requires explicit failure codes over silent failure.
EXIT_SUCCESS = 0
EXIT_CONTRACT_ERROR = 2
EXIT_CONFIGURATION_ERROR = 3
EXIT_REMOTE_ERROR = 4
EXIT_TIMEOUT = 5


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class PixelLabError(Exception):
    """Base class for every failure this adapter reports to an operator."""

    exit_code = EXIT_REMOTE_ERROR


class ContractError(PixelLabError):
    """Represent control artifacts that cannot safely produce a request."""

    exit_code = EXIT_CONTRACT_ERROR


class ConfigurationError(PixelLabError):
    """Represent a missing token, missing opt-in, or disallowed endpoint."""

    exit_code = EXIT_CONFIGURATION_ERROR


class TransportError(PixelLabError):
    """Represent a network failure or timeout before a response was read."""

    exit_code = EXIT_TIMEOUT


class RemoteError(PixelLabError):
    """Represent an actionable HTTP failure reported by PixelLab."""

    exit_code = EXIT_REMOTE_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """
        Description:
            Record an HTTP failure together with the status code that caused it.
        Required State:
            The message must already be redacted of any token material.
        Usage:
            Raised by response classification; caught by the CLI entry point.
        Parameters:
            message (str): Actionable operator-facing description.
            status_code (int | None): HTTP status code, when one was received.
        Returns:
            None: Constructs the exception.
        Other I/O:
            - none
        """
        super().__init__(message)
        self.status_code = status_code


class ProtocolError(PixelLabError):
    """Represent a syntactically or structurally invalid PixelLab response."""

    exit_code = EXIT_REMOTE_ERROR


class OutputError(PixelLabError):
    """Represent returned image bytes that violate the expected contract."""

    exit_code = EXIT_REMOTE_ERROR


class PollTimeoutError(PixelLabError):
    """Represent a job that did not finish inside the configured bounds."""

    exit_code = EXIT_TIMEOUT


# --------------------------------------------------------------------------
# Secret hygiene
# --------------------------------------------------------------------------

# Matches an Authorization header value in any text destined for a log, an
# error message, or a persisted manifest.
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bBearer\s+\S+")


def redact_secrets(text: str) -> str:
    """
    Description:
        Remove token material from any text that may reach a log, error, or file.
    Required State:
        None. Safe to call whether or not a token is configured.
    Usage:
        Wrap every operator-visible string and every persisted diagnostic.
    Parameters:
        text (str): Text that may contain a bearer token.
    Returns:
        str: Text with token material replaced by a fixed placeholder.
    Other I/O:
        - reads the PIXELLAB_API_TOKEN environment variable to redact its value
    """
    # Redact the configured token first so that a token appearing without the
    # "Bearer" prefix (for example echoed inside a JSON error body) is caught.
    configured_token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE)
    if configured_token:
        text = text.replace(configured_token, REDACTION_PLACEHOLDER)
    return BEARER_TOKEN_PATTERN.sub(f"Bearer {REDACTION_PLACEHOLDER}", text)


def emit_log(message: str) -> None:
    """
    Description:
        Write one redacted progress line to stderr.
    Required State:
        None.
    Usage:
        Use for every operator-facing progress or diagnostic message.
    Parameters:
        message (str): Human-readable message, possibly containing secrets.
    Returns:
        None: Writes to stderr.
    Other I/O:
        - stderr: one redacted line
    """
    print(redact_secrets(message), file=sys.stderr)


def resolve_api_token() -> str:
    """
    Description:
        Read the bearer token from the environment at the moment of a live call.
    Required State:
        Only call this on a code path that is about to contact PixelLab.
    Usage:
        Call immediately before building request headers; never store the result.
    Parameters:
        none
    Returns:
        str: The configured bearer token.
    Other I/O:
        - reads the PIXELLAB_API_TOKEN environment variable
    """
    # Guard early so that a missing token fails before any socket is opened.
    token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "").strip()
    if not token:
        raise ConfigurationError(
            f"{TOKEN_ENVIRONMENT_VARIABLE} is not set; export it in the shell that runs a "
            "live mode. It is never accepted as a command-line argument."
        )
    return token


# --------------------------------------------------------------------------
# Injectable HTTP transport
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class HttpResponse:
    """Carry a completed HTTP response independently of the transport used."""

    status_code: int
    headers: dict[str, str]
    body: bytes


class HttpTransport(Protocol):
    """Describe the single send operation the adapter needs from a transport."""

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        """Send one request and return its response without raising on 4xx/5xx."""


class UrllibHttpTransport:
    """Send requests with the standard library, with an explicit timeout."""

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        """
        Description:
            Perform one HTTP request using urllib with a mandatory timeout.
        Required State:
            The URL must already have been checked against the endpoint allowlist.
        Usage:
            Default transport for live modes; tests inject a fake instead.
        Parameters:
            method (str): HTTP method.
            url (str): Absolute request URL.
            headers (dict[str, str]): Request headers including authorization.
            body (bytes | None): Request body, or None for GET requests.
            timeout_seconds (float): Hard socket timeout.
        Returns:
            HttpResponse: Status, lower-cased headers, and raw body bytes.
        Other I/O:
            - network: one outbound HTTPS request
        """
        request = urllib.request.Request(url=url, data=body, method=method)
        for header_name, header_value in headers.items():
            request.add_header(header_name, header_value)

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return HttpResponse(
                    status_code=response.status,
                    headers={key.lower(): value for key, value in response.headers.items()},
                    body=response.read(),
                )
        except urllib.error.HTTPError as error:
            # A 4xx/5xx is a normal, classifiable outcome rather than a crash,
            # so it is returned like any other response.
            return HttpResponse(
                status_code=error.code,
                headers={key.lower(): value for key, value in error.headers.items()}
                if error.headers
                else {},
                body=error.read(),
            )
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            # The failure text can contain a request URL but never the token,
            # and it is redacted anyway as defence in depth.
            raise TransportError(
                redact_secrets(f"network failure contacting PixelLab: {error}")
            ) from None


# --------------------------------------------------------------------------
# Deterministic helpers shared with the issue #50 contract builder
# --------------------------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    """
    Description:
        Serialize JSON deterministically for hashing and repeatable artifacts.
    Required State:
        The value must contain only JSON-compatible data.
    Usage:
        Use for the cache key, the request body, and every persisted manifest.
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
        Content is the exact byte sequence persisted, submitted, or received.
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


def write_file_atomically(destination_path: Path, content: bytes) -> None:
    """
    Description:
        Publish a file so that readers never observe a partial write.
    Required State:
        The parent directory must exist and be writable.
    Usage:
        Use for every candidate image and manifest this adapter produces.
    Parameters:
        destination_path (Path): Final path to publish.
        content (bytes): Complete file content.
    Returns:
        None: Completes once the destination names the new content.
    Other I/O:
        - files: writes a sibling temporary file and renames it into place
    """
    temporary_path = destination_path.parent / f".{destination_path.name}.tmp"
    temporary_path.write_bytes(content)
    temporary_path.replace(destination_path)


def read_json_file(path: Path, description: str) -> dict[str, Any]:
    """
    Description:
        Read and parse a JSON object, rejecting anything that is not an object.
    Required State:
        The path is expected to exist; a missing file is an actionable error.
    Usage:
        Use for the visual brief and both manifests.
    Parameters:
        path (Path): File to read.
        description (str): Human-readable name used in error messages.
    Returns:
        dict[str, Any]: Parsed JSON object.
    Other I/O:
        - files: reads path
    """
    # Guard clauses keep the failure attributable to a specific artifact.
    if not path.is_file():
        raise ContractError(f"{description} not found: {path}")
    try:
        parsed = json.loads(path.read_bytes())
    except json.JSONDecodeError as error:
        raise ContractError(f"{description} is not valid JSON: {error}") from None
    if not isinstance(parsed, dict):
        raise ContractError(f"{description} must be a JSON object: {path}")
    return parsed


def read_png_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """
    Description:
        Extract width and height from a PNG header without a third-party decoder.
    Required State:
        The bytes must begin with a PNG signature followed by an IHDR chunk.
    Usage:
        Use to verify that returned pixels match the requested image size.
    Parameters:
        image_bytes (bytes): Complete PNG file content.
    Returns:
        tuple[int, int]: Width and height in pixels.
    Other I/O:
        - none
    """
    # A PNG always places IHDR width/height at bytes 16..24, so a shorter file
    # cannot be a PNG at all.
    if not image_bytes.startswith(PNG_SIGNATURE) or len(image_bytes) < 24:
        raise OutputError("returned image is not a PNG file")
    if image_bytes[12:16] != b"IHDR":
        raise OutputError("returned PNG does not begin with an IHDR chunk")
    width, height = struct.unpack(">II", image_bytes[16:24])
    return width, height


# --------------------------------------------------------------------------
# Control-artifact loading
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ControlArtifacts:
    """Hold the validated issue #50 inputs that determine one generation."""

    controls_directory: Path
    visual_brief: dict[str, Any]
    source_manifest: dict[str, Any]
    semantic_control_png: bytes


def load_control_artifacts(controls_directory: Path) -> ControlArtifacts:
    """
    Description:
        Load issue #50 control artifacts and prove they match their recorded hashes.
    Required State:
        The directory must contain the five artifacts written by visual_contract.py.
    Usage:
        Call at the start of every mode, including dry runs.
    Parameters:
        controls_directory (Path): Directory produced by visual_contract.py.
    Returns:
        ControlArtifacts: Validated brief, template manifest, and control image.
    Other I/O:
        - files: reads the five issue #50 artifacts (read-only)
    """
    source_manifest = read_json_file(
        controls_directory / SOURCE_MANIFEST_NAME, "generation manifest template"
    )
    visual_brief = read_json_file(controls_directory / VISUAL_BRIEF_NAME, "visual brief")

    if source_manifest.get("contractVersion") != CONTRACT_VERSION:
        raise ContractError(
            f"manifest template contractVersion must be {CONTRACT_VERSION}; "
            f"found {source_manifest.get('contractVersion')!r}"
        )
    if visual_brief.get("contractVersion") != CONTRACT_VERSION:
        raise ContractError(
            f"visual brief contractVersion must be {CONTRACT_VERSION}; "
            f"found {visual_brief.get('contractVersion')!r}"
        )

    recorded_inputs = source_manifest.get("inputs")
    if not isinstance(recorded_inputs, dict):
        raise ContractError("manifest template is missing its inputs hash map")

    # Re-hash every control artifact so that an edited or truncated input can
    # never be submitted under the provenance of the original contract.
    for file_name, hash_key in CONTROL_ARTIFACT_HASH_KEYS.items():
        artifact_path = controls_directory / file_name
        if not artifact_path.is_file():
            raise ContractError(f"control artifact not found: {artifact_path}")
        actual_hash = sha256_bytes(artifact_path.read_bytes())
        if recorded_inputs.get(hash_key) != actual_hash:
            raise ContractError(
                f"{file_name} does not match the hash recorded in {hash_key}; "
                "regenerate the controls with visual_contract.py"
            )

    return ControlArtifacts(
        controls_directory=controls_directory,
        visual_brief=visual_brief,
        source_manifest=source_manifest,
        semantic_control_png=(controls_directory / SEMANTIC_CONTROL_NAME).read_bytes(),
    )


def require_allowed_generation_endpoint(endpoint: str) -> str:
    """
    Description:
        Refuse to contact any generation endpoint outside the fixed allowlist.
    Required State:
        The endpoint comes from the manifest template, not from operator input.
    Usage:
        Call before constructing a request body and again before submitting.
    Parameters:
        endpoint (str): Endpoint path recorded in the manifest.
    Returns:
        str: The validated endpoint path.
    Other I/O:
        - none
    """
    if endpoint not in ALLOWED_GENERATION_ENDPOINTS:
        raise ConfigurationError(
            f"endpoint {endpoint!r} is not in the generation allowlist "
            f"{sorted(ALLOWED_GENERATION_ENDPOINTS)}"
        )
    return endpoint


# --------------------------------------------------------------------------
# Request construction
# --------------------------------------------------------------------------


def require_enum_value(value: Any, allowed: frozenset[str], field_name: str) -> str:
    """
    Description:
        Validate one style value against the PixelLab v2 enum for that field.
    Required State:
        The value came from the visual brief's prompt object.
    Usage:
        Use so an unknown style fails locally instead of as a remote HTTP 422.
    Parameters:
        value (Any): Candidate value from the visual brief.
        allowed (frozenset[str]): Legal values from the v2 OpenAPI enum.
        field_name (str): Request field name used in the error message.
    Returns:
        str: The validated value.
    Other I/O:
        - none
    """
    if not isinstance(value, str) or value not in allowed:
        raise ContractError(
            f"visual brief prompt.{field_name} must be one of {sorted(allowed)}; found {value!r}"
        )
    return value


def require_submittable_image_size(width: Any, height: Any) -> tuple[int, int]:
    """
    Description:
        Enforce the PixelLab image_size bounds before anything can be charged.
    Required State:
        Dimensions come from the visual brief, which uses one pixel per map cell.
    Usage:
        Call while building the request body for every mode.
    Parameters:
        width (Any): Declared brief width in cells.
        height (Any): Declared brief height in cells.
    Returns:
        tuple[int, int]: Validated width and height in pixels.
    Other I/O:
        - none
    """
    if type(width) is not int or type(height) is not int:
        raise ContractError("visual brief dimensions must be integers")
    # PixelLab rejects an out-of-range image_size, so a map larger than the
    # supported edge cannot be rendered at one pixel per cell by this endpoint.
    for edge_name, edge_value in (("width", width), ("height", height)):
        if edge_value < MINIMUM_IMAGE_EDGE or edge_value > MAXIMUM_IMAGE_EDGE:
            raise ContractError(
                f"visual brief {edge_name} {edge_value} is outside the PixelLab "
                f"image_size range {MINIMUM_IMAGE_EDGE}-{MAXIMUM_IMAGE_EDGE}; this map "
                "cannot be generated at one pixel per cell (Gitea #60)"
            )
    return width, height


def build_request_body(
    control_artifacts: ControlArtifacts,
    seed: int | None,
    use_semantic_control_init_image: bool,
    init_image_strength: int,
) -> dict[str, Any]:
    """
    Description:
        Build the exact CreateImagePixfluxRequest body implied by the controls.
    Required State:
        Control artifacts are loaded and their hashes verified.
    Usage:
        Used identically by dry-run and submit so a dry run is a true preview.
    Parameters:
        control_artifacts (ControlArtifacts): Validated issue #50 inputs.
        seed (int | None): Fixed seed recorded for reproducibility.
        use_semantic_control_init_image (bool): Send the control image as init_image.
        init_image_strength (int): Influence of the control image, 1 to 999.
    Returns:
        dict[str, Any]: Request body matching the v2 schema exactly.
    Other I/O:
        - none
    """
    prompt = control_artifacts.visual_brief.get("prompt")
    dimensions = control_artifacts.visual_brief.get("dimensions")
    if not isinstance(prompt, dict) or not isinstance(dimensions, dict):
        raise ContractError("visual brief requires prompt and dimensions objects")

    description = prompt.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ContractError("visual brief prompt.description must be a non-empty string")

    width, height = require_submittable_image_size(dimensions.get("width"), dimensions.get("height"))

    # The v2 schema sets additionalProperties=false, so only documented fields
    # may appear. Every value is pinned rather than left to a server default so
    # that the recorded body alone determines the cache key.
    request_body: dict[str, Any] = {
        "description": description,
        "image_size": {"width": width, "height": height},
        "text_guidance_scale": DEFAULT_TEXT_GUIDANCE_SCALE,
        "view": require_enum_value(prompt.get("camera"), ALLOWED_CAMERA_VIEWS, "camera"),
        "outline": require_enum_value(prompt.get("outline"), ALLOWED_OUTLINES, "outline"),
        "shading": require_enum_value(prompt.get("shading"), ALLOWED_SHADINGS, "shading"),
        "detail": require_enum_value(prompt.get("detail"), ALLOWED_DETAILS, "detail"),
        "isometric": False,
        "no_background": False,
    }

    # A seed is optional to the API but required for the fixed-seed candidate
    # comparison that issue #54 will run, so it is recorded whenever supplied.
    if seed is not None:
        request_body["seed"] = seed

    # The semantic control image is the only issue #50 artifact that pixflux
    # can consume. The masks have no corresponding request field; they stay
    # hashed into the cache key and are consumed by downstream validation.
    if use_semantic_control_init_image:
        if init_image_strength < 1 or init_image_strength > 999:
            raise ContractError("init image strength must be between 1 and 999")
        request_body["init_image"] = {
            "type": "base64",
            "base64": base64.b64encode(control_artifacts.semantic_control_png).decode("ascii"),
            "format": EXPECTED_IMAGE_FORMAT,
        }
        request_body["init_image_strength"] = init_image_strength

    return request_body


def summarize_request_body(request_body: dict[str, Any]) -> dict[str, Any]:
    """
    Description:
        Replace embedded image payloads with their hashes for manifest storage.
    Required State:
        The body was produced by build_request_body.
    Usage:
        Use whenever the request is written to a manifest or printed to a human.
    Parameters:
        request_body (dict[str, Any]): Full request body.
    Returns:
        dict[str, Any]: Body with base64 image fields reduced to hash summaries.
    Other I/O:
        - none
    """
    summary = dict(request_body)
    # Storing megabytes of base64 in a manifest would make it unreadable and
    # would not add provenance the hash does not already carry.
    for image_field in ("init_image", "color_image"):
        image_value = summary.get(image_field)
        if isinstance(image_value, dict) and isinstance(image_value.get("base64"), str):
            summary[image_field] = {
                "type": "base64",
                "format": image_value.get("format"),
                "sha256": sha256_bytes(base64.b64decode(image_value["base64"])),
            }
    return summary


def compute_request_cache_key(
    endpoint: str, recorded_inputs: dict[str, Any], request_body: dict[str, Any]
) -> str:
    """
    Description:
        Derive the content address of one generation before any network call.
    Required State:
        Inputs come from the verified manifest template; the body is final.
    Usage:
        Use to look up the cache and to name the cache entry after a success.
    Parameters:
        endpoint (str): Allowlisted generation endpoint.
        recorded_inputs (dict[str, Any]): Immutable control-artifact hashes.
        request_body (dict[str, Any]): Exact body that would be submitted.
    Returns:
        str: Lowercase hexadecimal SHA-256 cache key.
    Other I/O:
        - none
    """
    # Hashing the full body, including the base64 init image, guarantees that
    # any change to what would be sent produces a different cache entry.
    cache_material = {
        "contractVersion": CONTRACT_VERSION,
        "endpoint": endpoint,
        "inputs": recorded_inputs,
        "request": request_body,
    }
    return sha256_bytes(canonical_json_bytes(cache_material))


# --------------------------------------------------------------------------
# Manifest construction
# --------------------------------------------------------------------------


def build_candidate_manifest(
    control_artifacts: ControlArtifacts,
    request_body: dict[str, Any],
    request_cache_key: str,
    seed: int | None,
    candidate_index: int | None,
) -> dict[str, Any]:
    """
    Description:
        Copy the issue #50 template into a candidate manifest ready for updates.
    Required State:
        The template was validated and its endpoint is allowlisted.
    Usage:
        Call once per invocation; later stages mutate only the copy.
    Parameters:
        control_artifacts (ControlArtifacts): Validated issue #50 inputs.
        request_body (dict[str, Any]): Exact body that would be submitted.
        request_cache_key (str): Content address of this request.
        seed (int | None): Fixed seed recorded for reproducibility.
        candidate_index (int | None): Candidate ordinal within a batch.
    Returns:
        dict[str, Any]: Manifest conforming to the issue #50 schema.
    Other I/O:
        - none
    """
    template = control_artifacts.source_manifest
    # The schema forbids extra top-level properties, so every field this phase
    # adds lives inside the free-form request, remote, and output objects.
    return {
        "contractVersion": CONTRACT_VERSION,
        "state": "unsubmitted",
        "endpoint": template["endpoint"],
        "cacheKey": template["cacheKey"],
        "inputs": dict(template["inputs"]),
        "request": {
            "seed": seed,
            "candidateIndex": candidate_index,
            "requestCacheKey": request_cache_key,
            "bodySha256": sha256_bytes(canonical_json_bytes(request_body)),
            "body": summarize_request_body(request_body),
        },
        "remote": {
            "jobId": None,
            "usage": None,
            "status": None,
            "pollAttempts": 0,
            "cacheHit": False,
        },
        "output": {"sha256": None, "mimeType": None, "width": None, "height": None},
        "acceptance": {"state": "pending", "validator": None, "reason": None},
        "warnings": list(template.get("warnings", [])),
    }


def publish_candidate_manifest(output_directory: Path, manifest: dict[str, Any]) -> None:
    """
    Description:
        Atomically write the candidate manifest without touching issue #50 files.
    Required State:
        The output directory is distinct from the controls directory.
    Usage:
        Call after every state transition so a crash leaves a readable manifest.
    Parameters:
        output_directory (Path): Candidate directory.
        manifest (dict[str, Any]): Manifest to persist.
    Returns:
        None: Completes once the manifest names the new content.
    Other I/O:
        - files: writes generation-manifest.json atomically
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    write_file_atomically(output_directory / CANDIDATE_MANIFEST_NAME, canonical_json_bytes(manifest))


def require_separate_output_directory(controls_directory: Path, output_directory: Path) -> None:
    """
    Description:
        Refuse to write candidates into the authoritative issue #50 directory.
    Required State:
        Both paths are operator-supplied and may not yet exist.
    Usage:
        Call before creating the output directory in any writing mode.
    Parameters:
        controls_directory (Path): Read-only issue #50 artifact directory.
        output_directory (Path): Candidate destination directory.
    Returns:
        None: Completes when the destination is safely separate.
    Other I/O:
        - none
    """
    # resolve() makes the comparison robust against ".." and symlinked paths.
    if controls_directory.resolve() == output_directory.resolve():
        raise ConfigurationError(
            "output directory must differ from the controls directory; issue #50 "
            "artifacts are read-only inputs"
        )


# --------------------------------------------------------------------------
# Response classification
# --------------------------------------------------------------------------


def parse_json_response(response: HttpResponse, description: str) -> dict[str, Any]:
    """
    Description:
        Parse a PixelLab JSON response, failing loudly on malformed payloads.
    Required State:
        The response status was already classified as a success.
    Usage:
        Use for submission, polling, and balance responses.
    Parameters:
        response (HttpResponse): Response whose body should be a JSON object.
        description (str): Human-readable name used in error messages.
    Returns:
        dict[str, Any]: Parsed JSON object.
    Other I/O:
        - none
    """
    try:
        parsed = json.loads(response.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ProtocolError(
            redact_secrets(f"{description} was not valid JSON: {error}")
        ) from None
    if not isinstance(parsed, dict):
        raise ProtocolError(f"{description} must be a JSON object")
    return parsed


def describe_remote_error_body(response: HttpResponse) -> str:
    """
    Description:
        Extract a short, redacted explanation from an error response body.
    Required State:
        The response represents a non-success status code.
    Usage:
        Use to make an HTTP failure actionable without leaking secrets.
    Parameters:
        response (HttpResponse): Failing response.
    Returns:
        str: Short redacted detail, or an empty string when none is available.
    Other I/O:
        - none
    """
    # The body may be JSON, HTML, or empty; none of those should ever be
    # trusted verbatim, so the text is truncated and redacted.
    body_text = response.body.decode("utf-8", errors="replace").strip()
    if not body_text:
        return ""
    return redact_secrets(body_text[:400])


def classify_failure(response: HttpResponse, operation: str) -> RemoteError:
    """
    Description:
        Turn a PixelLab HTTP failure into one actionable operator message.
    Required State:
        The status code is outside the success range for the operation.
    Usage:
        Call from every request helper before raising.
    Parameters:
        response (HttpResponse): Failing response.
        operation (str): Short description of what was attempted.
    Returns:
        RemoteError: Exception carrying a redacted, actionable message.
    Other I/O:
        - none
    """
    detail = describe_remote_error_body(response)
    status_code = response.status_code
    # Each branch names the operator action, because a bare status code does
    # not tell anyone whether to top up credits, wait, or fix the request.
    guidance = {
        401: (
            f"PixelLab rejected the token (401). Check that {TOKEN_ENVIRONMENT_VARIABLE} "
            "holds a current token from your PixelLab account page."
        ),
        402: (
            "PixelLab reports insufficient credits (402). Run the balance mode and top up "
            "before retrying; no image was generated and nothing was charged."
        ),
        404: (
            "PixelLab could not find the background job (404). It may have expired or "
            "belong to a different account; submit a new generation explicitly."
        ),
        422: (
            "PixelLab rejected the request as invalid (422). The control artifacts produced "
            "a body the API will not accept; regenerate them and re-run a dry run."
        ),
        423: (
            "PixelLab reports the job is still processing (423). Re-run the poll mode; do "
            "not resubmit, because the original job is still running."
        ),
        429: (
            "PixelLab reports too many concurrent jobs (429). Wait and re-run the poll mode, "
            "or submit again later as a new explicit invocation."
        ),
        529: (
            "PixelLab reports its rate limit was exceeded (529). Wait and re-run; this "
            "adapter never resubmits a generation automatically."
        ),
    }.get(
        status_code,
        f"PixelLab returned an unexpected HTTP {status_code} while {operation}.",
    )
    message = f"{operation} failed: {guidance}"
    if detail:
        message = f"{message} Response detail: {detail}"
    return RemoteError(message, status_code=status_code)


# --------------------------------------------------------------------------
# Live operations
# --------------------------------------------------------------------------


def build_authorized_headers(include_json_body: bool) -> dict[str, str]:
    """
    Description:
        Build request headers, reading the token only at this moment.
    Required State:
        Only call on a code path that is about to contact PixelLab.
    Usage:
        Call once per request; never cache or log the returned mapping.
    Parameters:
        include_json_body (bool): Add a JSON content type for requests with bodies.
    Returns:
        dict[str, str]: Headers including the bearer authorization header.
    Other I/O:
        - reads the PIXELLAB_API_TOKEN environment variable
    """
    headers = {
        "Authorization": f"Bearer {resolve_api_token()}",
        "Accept": "application/json",
    }
    if include_json_body:
        headers["Content-Type"] = "application/json"
    return headers


def fetch_balance(transport: HttpTransport, timeout_seconds: float) -> dict[str, Any]:
    """
    Description:
        Read the account balance to confirm readiness before spending anything.
    Required State:
        A token is configured and the operator opted into live calls.
    Usage:
        Backs the balance mode; it never creates a generation.
    Parameters:
        transport (HttpTransport): Injected HTTP transport.
        timeout_seconds (float): Hard request timeout.
    Returns:
        dict[str, Any]: Parsed BalanceResponse object.
    Other I/O:
        - network: one GET to the read-only balance endpoint
    """
    response = transport.send(
        method="GET",
        url=f"{PIXELLAB_BASE_URL}{BALANCE_ENDPOINT}",
        headers=build_authorized_headers(include_json_body=False),
        body=None,
        timeout_seconds=timeout_seconds,
    )
    if response.status_code != 200:
        raise classify_failure(response, "reading the PixelLab balance")
    return parse_json_response(response, "balance response")


def submit_generation(
    transport: HttpTransport,
    endpoint: str,
    request_body: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """
    Description:
        Submit exactly one background generation job and return its identifier.
    Required State:
        The cache was already checked and reported a miss.
    Usage:
        Called once per invocation. It never retries, because a retry could
        create a second paid job for the same request.
    Parameters:
        transport (HttpTransport): Injected HTTP transport.
        endpoint (str): Allowlisted generation endpoint.
        request_body (dict[str, Any]): Exact body to submit.
        timeout_seconds (float): Hard request timeout.
    Returns:
        dict[str, Any]: Parsed CreateImagePixfluxBackgroundResponse object.
    Other I/O:
        - network: exactly one POST that may consume credits
    """
    require_allowed_generation_endpoint(endpoint)
    response = transport.send(
        method="POST",
        url=f"{PIXELLAB_BASE_URL}{endpoint}",
        headers=build_authorized_headers(include_json_body=True),
        body=canonical_json_bytes(request_body),
        timeout_seconds=timeout_seconds,
    )
    # The documented success status for the background endpoint is 202. Any
    # other status is surfaced without a retry so a paid job is never doubled.
    if response.status_code != 202:
        raise classify_failure(response, "submitting the generation job")

    accepted = parse_json_response(response, "submission response")
    job_identifier = accepted.get("background_job_id")
    if not isinstance(job_identifier, str) or not job_identifier:
        raise ProtocolError("submission response did not include a background_job_id")
    return accepted


@dataclass
class PollSettings:
    """Bound how long and how often a background job may be polled."""

    interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS
    maximum_attempts: int = DEFAULT_MAXIMUM_POLL_ATTEMPTS
    maximum_seconds: float = DEFAULT_MAXIMUM_POLL_SECONDS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


@dataclass
class PollResult:
    """Carry the terminal outcome of a bounded polling run."""

    job_response: dict[str, Any]
    attempts: int
    warnings: list[str] = field(default_factory=list)


def resolve_retry_delay(response: HttpResponse, fallback_seconds: float) -> float:
    """
    Description:
        Honour a Retry-After header when PixelLab supplies one.
    Required State:
        The response status was classified as retryable.
    Usage:
        Use between poll attempts so the adapter backs off as instructed.
    Parameters:
        response (HttpResponse): Retryable response.
        fallback_seconds (float): Delay to use when no usable header exists.
    Returns:
        float: Delay in seconds before the next attempt.
    Other I/O:
        - none
    """
    retry_after = response.headers.get("retry-after")
    if retry_after is None:
        return fallback_seconds
    try:
        # Only the delta-seconds form is honoured; an HTTP-date would need a
        # clock comparison that adds no value against a bounded poll loop.
        parsed_delay = float(retry_after.strip())
    except ValueError:
        return fallback_seconds
    return max(0.0, parsed_delay)


def poll_background_job(
    transport: HttpTransport,
    job_identifier: str,
    settings: PollSettings,
    sleep_function: Callable[[float], None],
    monotonic_function: Callable[[], float],
) -> PollResult:
    """
    Description:
        Poll one background job until it finishes or the configured bounds end.
    Required State:
        The job was already submitted; this function never creates a job.
    Usage:
        Called by submit after acceptance, and directly by the poll mode.
    Parameters:
        transport (HttpTransport): Injected HTTP transport.
        job_identifier (str): PixelLab background job identifier.
        settings (PollSettings): Attempt, wall-clock, and timeout bounds.
        sleep_function (Callable[[float], None]): Injected delay function.
        monotonic_function (Callable[[], float]): Injected monotonic clock.
    Returns:
        PollResult: Terminal job response plus the attempt count.
    Other I/O:
        - network: repeated GETs against the read-only job-status endpoint
        - stderr: one redacted progress line per attempt
    """
    job_url = f"{PIXELLAB_BASE_URL}{BACKGROUND_JOB_ENDPOINT_TEMPLATE.format(job_id=job_identifier)}"
    started_at = monotonic_function()
    warnings: list[str] = []

    for attempt_number in range(1, settings.maximum_attempts + 1):
        # The wall-clock bound is checked before each request so that a slow
        # transport cannot extend the run past the operator's limit.
        elapsed_seconds = monotonic_function() - started_at
        if elapsed_seconds > settings.maximum_seconds:
            raise PollTimeoutError(
                f"job {job_identifier} did not finish within {settings.maximum_seconds} seconds "
                f"after {attempt_number - 1} attempts; re-run the poll mode to resume without "
                "paying for a second generation"
            )

        response = transport.send(
            method="GET",
            url=job_url,
            headers=build_authorized_headers(include_json_body=False),
            body=None,
            timeout_seconds=settings.timeout_seconds,
        )

        # Retryable statuses mean "not ready", so they consume an attempt but
        # do not fail the run. Polling is free; only submission costs credits.
        if response.status_code in RETRYABLE_POLL_STATUS_CODES:
            delay_seconds = resolve_retry_delay(response, settings.interval_seconds)
            warnings.append(
                f"poll attempt {attempt_number} received HTTP {response.status_code}; "
                f"retrying after {delay_seconds} seconds"
            )
            emit_log(warnings[-1])
            sleep_function(delay_seconds)
            continue

        if response.status_code != 200:
            raise classify_failure(response, f"polling job {job_identifier}")

        job_response = parse_json_response(response, "job status response")
        status = job_response.get("status")
        if not isinstance(status, str):
            raise ProtocolError("job status response did not include a string status")

        if status == JOB_STATUS_COMPLETED:
            emit_log(f"job {job_identifier} completed after {attempt_number} attempts")
            return PollResult(job_response=job_response, attempts=attempt_number, warnings=warnings)

        if status == JOB_STATUS_FAILED:
            # A terminal remote failure is reported with whatever detail the
            # job carried, so an operator can decide whether to resubmit.
            detail = json.dumps(job_response.get("last_response"), sort_keys=True)
            raise RemoteError(
                redact_secrets(
                    f"PixelLab reported that job {job_identifier} failed terminally. "
                    "Credits may already have been consumed; inspect the balance before "
                    f"resubmitting. Job detail: {detail[:400]}"
                )
            )

        emit_log(f"job {job_identifier} status {status!r}; attempt {attempt_number}")
        sleep_function(settings.interval_seconds)

    raise PollTimeoutError(
        f"job {job_identifier} was still unfinished after {settings.maximum_attempts} attempts; "
        "re-run the poll mode to resume without paying for a second generation"
    )


# --------------------------------------------------------------------------
# Output extraction and validation
# --------------------------------------------------------------------------


def extract_completed_image(job_response: dict[str, Any], expected_size: dict[str, int]) -> bytes:
    """
    Description:
        Validate and decode the PNG carried by a completed background job.
    Required State:
        The job reported the completed status.
    Usage:
        Call before writing any candidate image or cache entry.
    Parameters:
        job_response (dict[str, Any]): Parsed BackgroundJobResponse object.
        expected_size (dict[str, int]): Requested width and height.
    Returns:
        bytes: Verified PNG file content.
    Other I/O:
        - none
    """
    last_response = job_response.get("last_response")
    if not isinstance(last_response, dict):
        raise ProtocolError("completed job did not include a last_response object")

    image_record = last_response.get("image")
    if not isinstance(image_record, dict):
        raise ProtocolError("completed job did not include an image object")

    # The v2 Base64Image contract defaults type to "base64" and format to "png".
    # Accept an omitted type as the documented default; reject any other value.
    image_type = image_record.get("type", "base64")
    if image_type != "base64":
        raise OutputError(f"unexpected image encoding type: {image_type!r}")
    image_format = image_record.get("format", EXPECTED_IMAGE_FORMAT)
    if image_format != EXPECTED_IMAGE_FORMAT:
        raise OutputError(
            f"unexpected image format {image_format!r}; only {EXPECTED_IMAGE_FORMAT} is accepted"
        )

    encoded_image = image_record.get("base64")
    if not isinstance(encoded_image, str) or not encoded_image:
        raise OutputError("completed job image did not include base64 data")
    try:
        image_bytes = base64.b64decode(encoded_image, validate=True)
    except (binascii.Error, ValueError) as error:
        raise OutputError(f"completed job image base64 could not be decoded: {error}") from None

    actual_width, actual_height = read_png_dimensions(image_bytes)
    if (actual_width, actual_height) != (expected_size["width"], expected_size["height"]):
        raise OutputError(
            f"returned image is {actual_width}x{actual_height} but "
            f"{expected_size['width']}x{expected_size['height']} was requested"
        )
    return image_bytes


# --------------------------------------------------------------------------
# Content-addressed cache
# --------------------------------------------------------------------------


def cache_entry_directory(cache_directory: Path, request_cache_key: str) -> Path:
    """
    Description:
        Resolve the directory that holds one cached generation.
    Required State:
        The cache key was derived from the final request body.
    Usage:
        Use for both lookup and storage so the two can never diverge.
    Parameters:
        cache_directory (Path): Cache root.
        request_cache_key (str): Content address of the request.
    Returns:
        Path: Directory for this cache entry.
    Other I/O:
        - none
    """
    return cache_directory / request_cache_key


def lookup_cached_image(cache_directory: Path, request_cache_key: str) -> bytes | None:
    """
    Description:
        Return a previously generated image for an identical request, if present.
    Required State:
        The cache directory may not exist; that is a normal cache miss.
    Usage:
        Call before submission. A hit must prevent any generation request.
    Parameters:
        cache_directory (Path): Cache root.
        request_cache_key (str): Content address of the request.
    Returns:
        bytes | None: Cached PNG bytes, or None on a miss.
    Other I/O:
        - files: reads the cached candidate image when present
    """
    cached_image_path = cache_entry_directory(cache_directory, request_cache_key) / CANDIDATE_IMAGE_NAME
    if not cached_image_path.is_file():
        return None

    cached_bytes = cached_image_path.read_bytes()
    # A truncated or replaced cache file must not be served as a valid result,
    # so the signature is re-checked rather than trusted from the file name.
    if not cached_bytes.startswith(PNG_SIGNATURE):
        raise ContractError(f"cache entry is not a PNG file: {cached_image_path}")
    return cached_bytes


def store_cached_image(cache_directory: Path, request_cache_key: str, image_bytes: bytes) -> None:
    """
    Description:
        Store a generated image under its content address for reuse.
    Required State:
        The image already passed MIME, type, and dimension validation.
    Usage:
        Call once after a successful generation.
    Parameters:
        cache_directory (Path): Cache root.
        request_cache_key (str): Content address of the request.
        image_bytes (bytes): Verified PNG content.
    Returns:
        None: Completes once the entry is readable.
    Other I/O:
        - files: writes the cache entry atomically
    """
    entry_directory = cache_entry_directory(cache_directory, request_cache_key)
    entry_directory.mkdir(parents=True, exist_ok=True)
    write_file_atomically(entry_directory / CANDIDATE_IMAGE_NAME, image_bytes)


def record_output_in_manifest(manifest: dict[str, Any], image_bytes: bytes) -> None:
    """
    Description:
        Record verified output provenance on the candidate manifest.
    Required State:
        The image passed every structural check.
    Usage:
        Call for both a cache hit and a freshly generated image.
    Parameters:
        manifest (dict[str, Any]): Candidate manifest to update in place.
        image_bytes (bytes): Verified PNG content.
    Returns:
        None: Mutates the manifest.
    Other I/O:
        - none
    """
    width, height = read_png_dimensions(image_bytes)
    manifest["output"] = {
        "sha256": sha256_bytes(image_bytes),
        "mimeType": EXPECTED_IMAGE_MIME_TYPE,
        "width": width,
        "height": height,
    }
    manifest["state"] = "completed"


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------


@dataclass
class AdapterSettings:
    """Group everything one invocation needs, with injectable seams for tests."""

    controls_directory: Path
    output_directory: Path
    cache_directory: Path
    seed: int | None = None
    candidate_index: int | None = None
    use_semantic_control_init_image: bool = True
    init_image_strength: int = DEFAULT_INIT_IMAGE_STRENGTH
    poll_settings: PollSettings = field(default_factory=PollSettings)
    transport_factory: Callable[[], HttpTransport] = UrllibHttpTransport
    sleep_function: Callable[[float], None] = time.sleep
    monotonic_function: Callable[[], float] = time.monotonic


def prepare_generation(settings: AdapterSettings) -> tuple[ControlArtifacts, dict[str, Any], str, dict[str, Any]]:
    """
    Description:
        Perform every offline step shared by the dry-run and submit modes.
    Required State:
        The controls directory holds validated issue #50 artifacts.
    Usage:
        Call first in any mode that needs a request body or a cache key.
    Parameters:
        settings (AdapterSettings): Resolved invocation settings.
    Returns:
        tuple: Control artifacts, request body, cache key, candidate manifest.
    Other I/O:
        - files: reads the issue #50 artifacts only
    """
    control_artifacts = load_control_artifacts(settings.controls_directory)
    endpoint = require_allowed_generation_endpoint(control_artifacts.source_manifest["endpoint"])
    request_body = build_request_body(
        control_artifacts,
        settings.seed,
        settings.use_semantic_control_init_image,
        settings.init_image_strength,
    )
    request_cache_key = compute_request_cache_key(
        endpoint, control_artifacts.source_manifest["inputs"], request_body
    )
    manifest = build_candidate_manifest(
        control_artifacts, request_body, request_cache_key, settings.seed, settings.candidate_index
    )
    return control_artifacts, request_body, request_cache_key, manifest


def run_dry_run_mode(settings: AdapterSettings) -> dict[str, Any]:
    """
    Description:
        Build and publish the exact request that a live run would submit.
    Required State:
        No token is required and no network access is attempted.
    Usage:
        Default mode; run it before every live opt-in.
    Parameters:
        settings (AdapterSettings): Resolved invocation settings.
    Returns:
        dict[str, Any]: The candidate manifest that was written.
    Other I/O:
        - files: writes generation-manifest.json into the output directory
    """
    require_separate_output_directory(settings.controls_directory, settings.output_directory)
    _, _, request_cache_key, manifest = prepare_generation(settings)

    # A dry run reports whether a live run would be free, without contacting
    # PixelLab to find out.
    cached_image = lookup_cached_image(settings.cache_directory, request_cache_key)
    manifest["remote"]["cacheHit"] = cached_image is not None
    manifest["warnings"].append("DRY RUN: no PixelLab request was made and no credits were spent")

    publish_candidate_manifest(settings.output_directory, manifest)
    emit_log(
        f"dry run complete; requestCacheKey={request_cache_key} "
        f"cacheHit={cached_image is not None}"
    )
    return manifest


def run_balance_mode(settings: AdapterSettings) -> dict[str, Any]:
    """
    Description:
        Report account readiness without creating any generation.
    Required State:
        A token is configured and the operator opted into live calls.
    Usage:
        Run before a live submission to confirm credits are available.
    Parameters:
        settings (AdapterSettings): Resolved invocation settings.
    Returns:
        dict[str, Any]: Parsed balance response.
    Other I/O:
        - network: one GET to the read-only balance endpoint
    """
    transport = settings.transport_factory()
    balance = fetch_balance(transport, settings.poll_settings.timeout_seconds)
    emit_log("balance retrieved; no generation was requested")
    return balance


def run_submit_mode(settings: AdapterSettings) -> dict[str, Any]:
    """
    Description:
        Generate one candidate, reusing the cache instead of paying when possible.
    Required State:
        The operator supplied both the live-call and credit-spend opt-ins.
    Usage:
        Run exactly once per candidate. Resubmission needs a new invocation.
    Parameters:
        settings (AdapterSettings): Resolved invocation settings.
    Returns:
        dict[str, Any]: The candidate manifest that was written.
    Other I/O:
        - files: writes the candidate image, manifest, and cache entry
        - network: at most one POST plus bounded read-only polling
    """
    require_separate_output_directory(settings.controls_directory, settings.output_directory)
    _, request_body, request_cache_key, manifest = prepare_generation(settings)
    settings.output_directory.mkdir(parents=True, exist_ok=True)

    # The cache is consulted before the transport is even constructed, so a hit
    # provably cannot reach the network.
    cached_image = lookup_cached_image(settings.cache_directory, request_cache_key)
    if cached_image is not None:
        manifest["remote"]["cacheHit"] = True
        record_output_in_manifest(manifest, cached_image)
        write_file_atomically(settings.output_directory / CANDIDATE_IMAGE_NAME, cached_image)
        publish_candidate_manifest(settings.output_directory, manifest)
        emit_log(f"cache hit for {request_cache_key}; no PixelLab request was made")
        return manifest

    transport = settings.transport_factory()
    endpoint = manifest["endpoint"]

    # The manifest is published as "submitted" before the POST is even read so
    # that a crash still leaves evidence that credits may have been consumed.
    manifest["state"] = "submitted"
    publish_candidate_manifest(settings.output_directory, manifest)

    accepted = submit_generation(
        transport, endpoint, request_body, settings.poll_settings.timeout_seconds
    )
    job_identifier = accepted["background_job_id"]
    manifest["remote"]["jobId"] = job_identifier
    manifest["remote"]["status"] = accepted.get("status", JOB_STATUS_PROCESSING)
    manifest["remote"]["usage"] = accepted.get("usage")
    manifest["state"] = "processing"
    publish_candidate_manifest(settings.output_directory, manifest)
    emit_log(f"generation accepted as job {job_identifier}; polling within configured bounds")

    return complete_job(settings, transport, manifest, request_body, request_cache_key)


def run_poll_mode(settings: AdapterSettings) -> dict[str, Any]:
    """
    Description:
        Resume an already-submitted job without paying for a second generation.
    Required State:
        The output directory holds a manifest with a recorded remote job id.
    Usage:
        Run after a polling timeout, or after a transient 429 or 529.
    Parameters:
        settings (AdapterSettings): Resolved invocation settings.
    Returns:
        dict[str, Any]: The updated candidate manifest.
    Other I/O:
        - files: reads and rewrites the candidate manifest
        - network: bounded read-only polling only
    """
    manifest = read_json_file(
        settings.output_directory / CANDIDATE_MANIFEST_NAME, "candidate manifest"
    )
    remote = manifest.get("remote")
    if not isinstance(remote, dict) or not isinstance(remote.get("jobId"), str):
        raise ContractError(
            "candidate manifest has no recorded remote.jobId; there is nothing to poll. "
            "Submitting a new generation requires an explicit submit invocation."
        )

    # The request body is rebuilt from the same controls so that the returned
    # image can still be checked against the size that was actually requested.
    _, request_body, request_cache_key, _ = prepare_generation(settings)
    transport = settings.transport_factory()
    return complete_job(settings, transport, manifest, request_body, request_cache_key)


def complete_job(
    settings: AdapterSettings,
    transport: HttpTransport,
    manifest: dict[str, Any],
    request_body: dict[str, Any],
    request_cache_key: str,
) -> dict[str, Any]:
    """
    Description:
        Poll a submitted job to completion and publish its verified output.
    Required State:
        The manifest records a remote job id from a previous submission.
    Usage:
        Shared tail of the submit and poll modes; it never submits anything.
    Parameters:
        settings (AdapterSettings): Resolved invocation settings.
        transport (HttpTransport): Injected HTTP transport.
        manifest (dict[str, Any]): Candidate manifest to update.
        request_body (dict[str, Any]): Body whose image_size must be honoured.
        request_cache_key (str): Content address used for the cache entry.
    Returns:
        dict[str, Any]: The updated candidate manifest.
    Other I/O:
        - files: writes the candidate image, manifest, and cache entry
        - network: bounded read-only polling only
    """
    job_identifier = manifest["remote"]["jobId"]
    try:
        poll_result = poll_background_job(
            transport,
            job_identifier,
            settings.poll_settings,
            settings.sleep_function,
            settings.monotonic_function,
        )
    except (PollTimeoutError, RemoteError, ProtocolError) as error:
        # Persist the failure state so the next invocation can resume polling
        # rather than paying to submit the same request again.
        manifest["state"] = "failed" if isinstance(error, RemoteError) else "processing"
        manifest["warnings"].append(redact_secrets(str(error)))
        publish_candidate_manifest(settings.output_directory, manifest)
        raise

    manifest["remote"]["status"] = poll_result.job_response.get("status")
    manifest["remote"]["pollAttempts"] = poll_result.attempts
    # The job's own usage is authoritative over the submission estimate.
    if poll_result.job_response.get("usage") is not None:
        manifest["remote"]["usage"] = poll_result.job_response["usage"]
    manifest["warnings"].extend(poll_result.warnings)

    image_bytes = extract_completed_image(poll_result.job_response, request_body["image_size"])
    record_output_in_manifest(manifest, image_bytes)

    # The cache is written before the manifest so that a crash between the two
    # leaves a reusable entry rather than an orphaned charge.
    store_cached_image(settings.cache_directory, request_cache_key, image_bytes)
    write_file_atomically(settings.output_directory / CANDIDATE_IMAGE_NAME, image_bytes)
    publish_candidate_manifest(settings.output_directory, manifest)
    emit_log(f"candidate published for job {job_identifier}")
    return manifest


# --------------------------------------------------------------------------
# Command-line interface
# --------------------------------------------------------------------------


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Description:
        Define the operator interface, including the explicit live-call opt-ins.
    Required State:
        None.
    Usage:
        Called by main and by tests that assert on help output.
    Parameters:
        none
    Returns:
        argparse.ArgumentParser: Configured parser.
    Other I/O:
        - none
    """
    parser = argparse.ArgumentParser(
        prog="pixellab_client.py",
        description=(
            "Opt-in PixelLab v2 adapter for presentation-only map backgrounds. "
            "Defaults to a dry run that makes no network request and spends no credits."
        ),
        epilog=(
            f"The bearer token is read only from the {TOKEN_ENVIRONMENT_VARIABLE} environment "
            "variable at live-call time. It is never accepted as an argument, written to a "
            "manifest, or included in a log line or error message."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("dry-run", "balance", "submit", "poll"),
        default="dry-run",
        help="dry-run builds the request offline; balance and poll are read-only live "
        "calls; submit may spend credits (default: dry-run)",
    )
    parser.add_argument(
        "--controls",
        type=Path,
        help="read-only directory of issue #50 control artifacts (required except balance)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="candidate directory for the copied manifest and generated image (required except balance)",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        help="content-addressed cache root; a hit makes no generation request (required except balance)",
    )
    parser.add_argument("--seed", type=int, default=None, help="fixed seed recorded for reproducibility")
    parser.add_argument(
        "--candidate-index", type=int, default=None, help="candidate ordinal recorded in the manifest"
    )
    parser.add_argument(
        "--no-init-image",
        action="store_true",
        help="omit semantic-control.png as the pixflux init_image",
    )
    parser.add_argument(
        "--init-image-strength",
        type=int,
        default=DEFAULT_INIT_IMAGE_STRENGTH,
        help=f"init image influence, 1 to 999 (default: {DEFAULT_INIT_IMAGE_STRENGTH})",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"per-request timeout (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help=f"delay between poll attempts (default: {DEFAULT_POLL_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--max-poll-attempts",
        type=int,
        default=DEFAULT_MAXIMUM_POLL_ATTEMPTS,
        help=f"maximum poll attempts (default: {DEFAULT_MAXIMUM_POLL_ATTEMPTS})",
    )
    parser.add_argument(
        "--max-poll-seconds",
        type=float,
        default=DEFAULT_MAXIMUM_POLL_SECONDS,
        help=f"maximum polling wall-clock time (default: {DEFAULT_MAXIMUM_POLL_SECONDS})",
    )
    parser.add_argument(
        "--enable-live-calls",
        action="store_true",
        help="required for balance, submit, and poll; without it no socket is opened",
    )
    parser.add_argument(
        "--confirm-credit-spend",
        action="store_true",
        help="required in addition to --enable-live-calls for submit; acknowledges that one "
        "generation may be charged",
    )
    return parser


def require_live_call_opt_in(mode: str, arguments: argparse.Namespace) -> None:
    """
    Description:
        Refuse to open a socket unless the operator asked for it explicitly.
    Required State:
        Arguments were parsed successfully.
    Usage:
        Call before constructing a transport in any live mode.
    Parameters:
        mode (str): Selected mode.
        arguments (argparse.Namespace): Parsed arguments.
    Returns:
        None: Completes when the mode is permitted to run.
    Other I/O:
        - none
    """
    if not arguments.enable_live_calls:
        raise ConfigurationError(
            f"mode {mode!r} performs a live PixelLab call; pass --enable-live-calls to "
            "authorize it, or use the default dry-run mode"
        )
    # The second opt-in exists only for the one mode that can be charged, so
    # that a read-only balance check never trains an operator to pass it.
    if mode == "submit" and not arguments.confirm_credit_spend:
        raise ConfigurationError(
            "submit may consume PixelLab credits; pass --confirm-credit-spend to acknowledge "
            "that exactly one generation will be requested"
        )
    # Resolving the token here converts a missing token into a clear failure
    # before any request is built.
    resolve_api_token()


def require_mode_paths(mode: str, arguments: argparse.Namespace) -> None:
    """
    Description:
        Ensure modes that touch controls or candidates received their paths.
    Required State:
        Arguments were parsed successfully.
    Usage:
        Call before constructing AdapterSettings for any mode except balance.
    Parameters:
        mode (str): Selected mode.
        arguments (argparse.Namespace): Parsed arguments.
    Returns:
        None: Completes when every required path is present.
    Other I/O:
        - none
    """
    # Balance only needs a live token; every other mode needs the control and
    # candidate paths so the adapter cannot invent destinations.
    if mode == "balance":
        return
    missing = [
        flag
        for flag, value in (
            ("--controls", arguments.controls),
            ("--output", arguments.output),
            ("--cache", arguments.cache),
        )
        if value is None
    ]
    if missing:
        raise ConfigurationError(
            f"mode {mode!r} requires {', '.join(missing)}; balance is the only path-free mode"
        )


def build_settings(arguments: argparse.Namespace) -> AdapterSettings:
    """
    Description:
        Translate parsed arguments into the adapter's settings object.
    Required State:
        Arguments were parsed and any live opt-in was already validated.
    Usage:
        Called by main; tests construct AdapterSettings directly instead.
    Parameters:
        arguments (argparse.Namespace): Parsed arguments.
    Returns:
        AdapterSettings: Settings with the default live transport and clock.
    Other I/O:
        - none
    """
    # Balance may omit paths; supply placeholders so the dataclass still builds.
    placeholder = Path(".")
    return AdapterSettings(
        controls_directory=arguments.controls or placeholder,
        output_directory=arguments.output or placeholder,
        cache_directory=arguments.cache or placeholder,
        seed=arguments.seed,
        candidate_index=arguments.candidate_index,
        use_semantic_control_init_image=not arguments.no_init_image,
        init_image_strength=arguments.init_image_strength,
        poll_settings=PollSettings(
            interval_seconds=arguments.poll_interval_seconds,
            maximum_attempts=arguments.max_poll_attempts,
            maximum_seconds=arguments.max_poll_seconds,
            timeout_seconds=arguments.timeout_seconds,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """
    Description:
        Parse arguments, run one mode, and report a redacted summary.
    Required State:
        Python 3.10 or newer and a readable issue #50 controls directory.
    Usage:
        Run from the repository root or through a future stage wrapper.
    Parameters:
        argv (list[str] | None): Argument vector, or None to use sys.argv.
    Returns:
        int: Zero on success, or a mode-specific non-zero failure code.
    Other I/O:
        - stdout: one canonical JSON summary line
        - stderr: redacted progress and failure messages
    """
    arguments = build_argument_parser().parse_args(argv)

    try:
        require_mode_paths(arguments.mode, arguments)
        if arguments.mode != "dry-run":
            require_live_call_opt_in(arguments.mode, arguments)
        settings = build_settings(arguments)

        if arguments.mode == "dry-run":
            manifest = run_dry_run_mode(settings)
            summary = {
                "mode": arguments.mode,
                "state": manifest["state"],
                "requestCacheKey": manifest["request"]["requestCacheKey"],
                "cacheHit": manifest["remote"]["cacheHit"],
                "networkRequests": 0,
            }
        elif arguments.mode == "balance":
            balance = run_balance_mode(settings)
            summary = {"mode": arguments.mode, "balance": balance}
        else:
            runner = run_submit_mode if arguments.mode == "submit" else run_poll_mode
            manifest = runner(settings)
            summary = {
                "mode": arguments.mode,
                "state": manifest["state"],
                "requestCacheKey": manifest["request"]["requestCacheKey"],
                "cacheHit": manifest["remote"]["cacheHit"],
                "jobId": manifest["remote"]["jobId"],
            }
    except PixelLabError as error:
        # Redaction is applied once more at the boundary so that no failure
        # path can print token material, regardless of where it was raised.
        emit_log(f"pixellab adapter failed: {error}")
        return error.exit_code

    print(redact_secrets(json.dumps(summary, sort_keys=True)))
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
