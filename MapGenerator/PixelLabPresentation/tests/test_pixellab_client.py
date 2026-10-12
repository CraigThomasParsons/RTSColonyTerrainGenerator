"""Standard-library mock-transport tests for the PixelLab v2 adapter (#51)."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any, Callable
from unittest import mock


def load_module(module_name: str, module_path: Path):
    """
    Description:
        Load a bin/ script as a module under a stable sys.modules name.
    Required State:
        module_path must exist and be importable as source.
    Usage:
        Use for scripts that are not installed as a package.
    Parameters:
        module_name (str): Name registered in sys.modules (required for dataclasses).
        module_path (Path): Path to the Python source file.
    Returns:
        module: Loaded module object.
    Other I/O:
        - none
    """
    # Python 3.14 dataclasses look up cls.__module__ in sys.modules during class
    # creation, so the module must be registered before exec_module runs.
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


client = load_module(
    "pixellab_client", Path(__file__).parents[1] / "bin" / "pixellab_client.py"
)
visual_contract = load_module(
    "visual_contract_for_client_tests",
    Path(__file__).parents[1] / "bin" / "visual_contract.py",
)

FAKE_TOKEN = "test-token-value-never-live-FAKESECRET_e4f5g6h7i8j9k0l1m2n3"
MAP_WIDTH = 16
MAP_HEIGHT = 16


def build_png_bytes(width: int, height: int, red: int = 10, green: int = 20, blue: int = 30) -> bytes:
    """
    Description:
        Build a minimal valid RGB PNG for dimension and MIME checks.
    Required State:
        Width and height are positive integers within PixelLab bounds.
    Usage:
        Use for mock completed-job images and cache fixtures.
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
    for _row in range(height):
        raw_rows.append(0)
        for _column in range(width):
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


def large_enough_payload() -> dict[str, Any]:
    """
    Description:
        Build a synthetic world payload inside the PixelLab image_size range.
    Required State:
        None.
    Usage:
        Feed visual_contract to produce real control artifacts for adapter tests.
    Parameters:
        none
    Returns:
        dict[str, Any]: JSON-compatible world payload.
    Other I/O:
        - none
    """
    tiles: list[dict[str, Any]] = []
    terrains = ("grass", "water", "rock", "sand")
    for coordinate_y in range(MAP_HEIGHT):
        for coordinate_x in range(MAP_WIDTH):
            tiles.append(
                {
                    "x": coordinate_x,
                    "y": coordinate_y,
                    "terrain": terrains[(coordinate_x + coordinate_y) % len(terrains)],
                }
            )
    return {
        "version": 1,
        "job_id": "client-test-map",
        "map": {"width_in_cells": MAP_WIDTH, "height_in_cells": MAP_HEIGHT},
        "tiles": tiles,
        "features": [{"type": "road", "x": 1, "y": 1}],
        "playable": {
            "start_zones": [{"id": "start-1", "x": 2, "y": 2}],
            "resource_clusters": [],
            "settlement_labels": [],
        },
    }


class RecordingTransport:
    """Record every request and serve scripted responses without a network."""

    def __init__(self, handlers: list[Callable[[str, str, dict[str, str], bytes | None], client.HttpResponse]]):
        """
        Description:
            Store ordered response handlers for deterministic mock HTTP flows.
        Required State:
            Each handler returns an HttpResponse for one request.
        Usage:
            Inject via AdapterSettings.transport_factory in tests.
        Parameters:
            handlers (list): Ordered callables invoked once per send().
        Returns:
            None: Constructs the transport.
        Other I/O:
            - none
        """
        self._handlers = list(handlers)
        self.requests: list[dict[str, Any]] = []

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> client.HttpResponse:
        """
        Description:
            Record one request and return the next scripted response.
        Required State:
            At least one unused handler remains for each expected call.
        Usage:
            Called by the adapter under test; never opens a socket.
        Parameters:
            method (str): HTTP method.
            url (str): Absolute URL.
            headers (dict[str, str]): Request headers.
            body (bytes | None): Request body.
            timeout_seconds (float): Request timeout (unused).
        Returns:
            HttpResponse: Scripted response for this call.
        Other I/O:
            - none
        """
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout_seconds": timeout_seconds,
            }
        )
        if not self._handlers:
            raise AssertionError(f"unexpected HTTP call: {method} {url}")
        handler = self._handlers.pop(0)
        return handler(method, url, headers, body)


class PixelLabClientTests(unittest.TestCase):
    """Prove dry-run safety, cache behaviour, async flow, and secret hygiene."""

    def setUp(self) -> None:
        """
        Description:
            Create a temporary workspace and real issue #50 control artifacts.
        Required State:
            visual_contract.py is available beside the adapter under test.
        Usage:
            unittest calls this before every test method.
        Parameters:
            none
        Returns:
            None
        Other I/O:
            - files: creates a temporary directory of control artifacts
        """
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.controls = self.root / "controls"
        self.output = self.root / "output"
        self.cache = self.root / "cache"
        payload_path = self.root / "map.worldpayload"
        payload_path.write_text(json.dumps(large_enough_payload(), sort_keys=True), encoding="utf-8")
        visual_contract.write_contract(payload_path, self.controls, False)
        # Tests must never inherit a real operator token from the surrounding shell.
        self._token_env = mock.patch.dict(os.environ, {}, clear=False)
        self._token_env.start()
        os.environ.pop(client.TOKEN_ENVIRONMENT_VARIABLE, None)

    def tearDown(self) -> None:
        """
        Description:
            Restore environment state and delete temporary artifacts.
        Required State:
            setUp completed for this test.
        Usage:
            unittest calls this after every test method.
        Parameters:
            none
        Returns:
            None
        Other I/O:
            - files: deletes the temporary directory
        """
        self._token_env.stop()
        self._temporary.cleanup()

    def settings(
        self,
        transport: RecordingTransport | None = None,
        sleep_calls: list[float] | None = None,
        clock_values: list[float] | None = None,
        maximum_attempts: int = 5,
        maximum_seconds: float = 30.0,
        interval_seconds: float = 0.0,
    ) -> client.AdapterSettings:
        """
        Description:
            Build adapter settings wired to the temporary directories and mocks.
        Required State:
            setUp has produced control artifacts.
        Usage:
            Call from each test that invokes a mode.
        Parameters:
            transport (RecordingTransport | None): Mock transport, when live.
            sleep_calls (list[float] | None): Collector for injected sleeps.
            clock_values (list[float] | None): Monotonic clock sequence.
            maximum_attempts (int): Poll attempt bound.
            maximum_seconds (float): Poll wall-clock bound.
            interval_seconds (float): Delay between successful processing polls.
        Returns:
            AdapterSettings: Ready-to-run settings object.
        Other I/O:
            - none
        """
        recorded_sleeps = sleep_calls if sleep_calls is not None else []
        clock = list(clock_values) if clock_values is not None else [0.0]

        def sleep_function(seconds: float) -> None:
            recorded_sleeps.append(seconds)

        def monotonic_function() -> float:
            if len(clock) == 1:
                return clock[0]
            return clock.pop(0)

        settings = client.AdapterSettings(
            controls_directory=self.controls,
            output_directory=self.output,
            cache_directory=self.cache,
            seed=7,
            candidate_index=0,
            poll_settings=client.PollSettings(
                interval_seconds=interval_seconds,
                maximum_attempts=maximum_attempts,
                maximum_seconds=maximum_seconds,
                timeout_seconds=5.0,
            ),
            sleep_function=sleep_function,
            monotonic_function=monotonic_function,
        )
        if transport is not None:
            settings.transport_factory = lambda: transport
        return settings

    def json_response(self, status_code: int, payload: dict[str, Any], headers: dict[str, str] | None = None) -> client.HttpResponse:
        """Build one JSON HttpResponse for a scripted handler."""
        return client.HttpResponse(
            status_code=status_code,
            headers={key.lower(): value for key, value in (headers or {}).items()},
            body=json.dumps(payload).encode("utf-8"),
        )

    def completed_job_payload(self, job_id: str = "job-123") -> dict[str, Any]:
        """Return a completed BackgroundJobResponse carrying a valid PNG."""
        image_bytes = build_png_bytes(MAP_WIDTH, MAP_HEIGHT)
        return {
            "id": job_id,
            "status": "completed",
            "created_at": "2026-08-08T00:00:00Z",
            "usage": {"type": "usd", "usd": 0.02},
            "last_response": {
                "image": {
                    "type": "base64",
                    "base64": base64.b64encode(image_bytes).decode("ascii"),
                    "format": "png",
                }
            },
        }

    def test_dry_run_builds_request_without_token_or_network(self) -> None:
        """Dry-run must never require a token and never open a socket."""
        transport = RecordingTransport(handlers=[])
        settings = self.settings(transport=transport)
        # A factory that would raise if the dry-run path constructed a transport.
        settings.transport_factory = lambda: (_ for _ in ()).throw(AssertionError("transport used"))

        manifest = client.run_dry_run_mode(settings)

        self.assertEqual(manifest["state"], "unsubmitted")
        self.assertFalse(manifest["remote"]["cacheHit"])
        self.assertEqual(manifest["endpoint"], "/create-image-pixflux-background")
        self.assertIn("DRY RUN", manifest["warnings"][0])
        self.assertEqual(manifest["request"]["seed"], 7)
        self.assertEqual(manifest["request"]["body"]["image_size"], {"width": MAP_WIDTH, "height": MAP_HEIGHT})
        # Manifest storage keeps type/format metadata but replaces the payload with a hash.
        init_image_summary = manifest["request"]["body"]["init_image"]
        self.assertEqual(init_image_summary["type"], "base64")
        self.assertIn("sha256", init_image_summary)
        self.assertNotIn("base64", init_image_summary)
        published = json.loads((self.output / "generation-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(published["request"]["requestCacheKey"], manifest["request"]["requestCacheKey"])
        self.assertEqual(transport.requests, [])

    def test_cli_dry_run_reports_zero_network_requests(self) -> None:
        """CLI dry-run exits zero and states that no network request occurred."""
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            exit_code = client.main(
                [
                    "--mode",
                    "dry-run",
                    "--controls",
                    str(self.controls),
                    "--output",
                    str(self.output),
                    "--cache",
                    str(self.cache),
                    "--seed",
                    "7",
                ]
            )
        self.assertEqual(exit_code, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["networkRequests"], 0)
        self.assertEqual(summary["mode"], "dry-run")

    def test_live_mode_requires_token(self) -> None:
        """Submit without PIXELLAB_API_TOKEN must fail before any request."""
        transport = RecordingTransport(handlers=[])
        settings = self.settings(transport=transport)
        with self.assertRaises(client.ConfigurationError) as raised:
            # main-path check is require_live_call_opt_in; also cover resolve_api_token.
            client.resolve_api_token()
        self.assertIn(client.TOKEN_ENVIRONMENT_VARIABLE, str(raised.exception))

        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            exit_code = client.main(
                [
                    "--mode",
                    "submit",
                    "--controls",
                    str(self.controls),
                    "--output",
                    str(self.output),
                    "--cache",
                    str(self.cache),
                    "--enable-live-calls",
                    "--confirm-credit-spend",
                ]
            )
        self.assertEqual(exit_code, client.EXIT_CONFIGURATION_ERROR)
        self.assertEqual(transport.requests, [])
        self.assertNotIn(FAKE_TOKEN, stderr.getvalue())

    def test_token_never_appears_in_logs_manifests_or_errors(self) -> None:
        """Bearer material must be redacted from operator-visible surfaces."""
        os.environ[client.TOKEN_ENVIRONMENT_VARIABLE] = FAKE_TOKEN

        def unauthorized(_method: str, _url: str, headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            # Include the raw token in the body so redaction is forced to scrub it.
            return client.HttpResponse(
                status_code=401,
                headers={},
                body=f"invalid token {FAKE_TOKEN} Bearer {FAKE_TOKEN}".encode("utf-8"),
            )

        transport = RecordingTransport(handlers=[unauthorized])
        settings = self.settings(transport=transport)
        with self.assertRaises(client.RemoteError) as raised:
            client.run_submit_mode(settings)

        message = str(raised.exception)
        self.assertNotIn(FAKE_TOKEN, message)
        self.assertIn(client.REDACTION_PLACEHOLDER, message)

        # Redaction also applies to free-form text that embeds the secret.
        self.assertNotIn(FAKE_TOKEN, client.redact_secrets(f"Authorization: Bearer {FAKE_TOKEN}"))
        self.assertNotIn(FAKE_TOKEN, client.redact_secrets(f"leaked {FAKE_TOKEN}"))

        if (self.output / "generation-manifest.json").is_file():
            manifest_text = (self.output / "generation-manifest.json").read_text(encoding="utf-8")
            self.assertNotIn(FAKE_TOKEN, manifest_text)
            self.assertNotIn("Bearer ", manifest_text)

    def test_cache_hit_makes_no_generation_request(self) -> None:
        """An identical prior generation must be reused without contacting PixelLab."""
        _, request_body, request_cache_key, _ = client.prepare_generation(self.settings())
        image_bytes = build_png_bytes(MAP_WIDTH, MAP_HEIGHT, red=40, green=50, blue=60)
        client.store_cached_image(self.cache, request_cache_key, image_bytes)

        transport = RecordingTransport(handlers=[])
        settings = self.settings(transport=transport)
        settings.transport_factory = lambda: (_ for _ in ()).throw(AssertionError("transport used on cache hit"))

        os.environ[client.TOKEN_ENVIRONMENT_VARIABLE] = FAKE_TOKEN
        manifest = client.run_submit_mode(settings)

        self.assertTrue(manifest["remote"]["cacheHit"])
        self.assertEqual(manifest["state"], "completed")
        self.assertEqual(manifest["output"]["mimeType"], "image/png")
        self.assertEqual(manifest["output"]["width"], MAP_WIDTH)
        self.assertEqual((self.output / "candidate.png").read_bytes(), image_bytes)
        self.assertEqual(transport.requests, [])
        # The request body that would have been paid for stays fully determined.
        self.assertEqual(request_body["image_size"]["width"], MAP_WIDTH)

    def test_accepted_async_flow_submits_once_and_records_usage(self) -> None:
        """One paid POST plus bounded polling produces a verified candidate."""
        os.environ[client.TOKEN_ENVIRONMENT_VARIABLE] = FAKE_TOKEN
        job_id = "bg-job-async-1"
        image_bytes = build_png_bytes(MAP_WIDTH, MAP_HEIGHT)

        def accept(method: str, url: str, headers: dict[str, str], body: bytes | None) -> client.HttpResponse:
            self.assertEqual(method, "POST")
            self.assertTrue(url.endswith("/create-image-pixflux-background"))
            self.assertEqual(headers["Authorization"], f"Bearer {FAKE_TOKEN}")
            payload = json.loads(body or b"{}")
            self.assertEqual(payload["image_size"], {"width": MAP_WIDTH, "height": MAP_HEIGHT})
            self.assertIn("init_image", payload)
            return self.json_response(
                202,
                {"background_job_id": job_id, "status": "processing", "usage": {"type": "usd", "usd": 0.0}},
            )

        def processing(_method: str, url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            self.assertIn(f"/background-jobs/{job_id}", url)
            return self.json_response(
                200,
                {
                    "id": job_id,
                    "status": "processing",
                    "created_at": "2026-08-08T00:00:00Z",
                    "last_response": None,
                    "usage": None,
                },
            )

        def completed(_method: str, url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            self.assertIn(f"/background-jobs/{job_id}", url)
            return self.json_response(200, self.completed_job_payload(job_id))

        transport = RecordingTransport(handlers=[accept, processing, completed])
        settings = self.settings(transport=transport, interval_seconds=0.0)
        manifest = client.run_submit_mode(settings)

        self.assertEqual(manifest["state"], "completed")
        self.assertEqual(manifest["remote"]["jobId"], job_id)
        self.assertEqual(manifest["remote"]["usage"], {"type": "usd", "usd": 0.02})
        self.assertFalse(manifest["remote"]["cacheHit"])
        self.assertEqual(manifest["output"]["sha256"], client.sha256_bytes(image_bytes))
        self.assertEqual((self.output / "candidate.png").read_bytes(), image_bytes)
        # Exactly one generation POST; the rest are free poll GETs.
        post_calls = [item for item in transport.requests if item["method"] == "POST"]
        get_calls = [item for item in transport.requests if item["method"] == "GET"]
        self.assertEqual(len(post_calls), 1)
        self.assertEqual(len(get_calls), 2)
        # Cache must now serve the same image without another POST.
        second_transport = RecordingTransport(handlers=[])
        second_settings = self.settings(transport=second_transport)
        second_settings.output_directory = self.root / "output-2"
        second_manifest = client.run_submit_mode(second_settings)
        self.assertTrue(second_manifest["remote"]["cacheHit"])
        self.assertEqual(second_transport.requests, [])

    def test_poll_timeout_does_not_resubmit(self) -> None:
        """Exhausted poll bounds leave the job recoverable without a new POST."""
        os.environ[client.TOKEN_ENVIRONMENT_VARIABLE] = FAKE_TOKEN
        job_id = "job-timeout"

        def accept(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            return self.json_response(202, {"background_job_id": job_id, "status": "processing"})

        def still_processing(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            return self.json_response(
                200,
                {
                    "id": job_id,
                    "status": "processing",
                    "created_at": "2026-08-08T00:00:00Z",
                    "last_response": None,
                },
            )

        transport = RecordingTransport(handlers=[accept, still_processing, still_processing])
        settings = self.settings(
            transport=transport,
            maximum_attempts=2,
            maximum_seconds=100.0,
            interval_seconds=0.0,
        )
        with self.assertRaises(client.PollTimeoutError):
            client.run_submit_mode(settings)

        manifest = json.loads((self.output / "generation-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["remote"]["jobId"], job_id)
        self.assertEqual(manifest["state"], "processing")
        self.assertEqual(sum(1 for item in transport.requests if item["method"] == "POST"), 1)

    def test_http_401_and_402_are_actionable(self) -> None:
        """Representative auth and credit failures must not retry submission."""
        os.environ[client.TOKEN_ENVIRONMENT_VARIABLE] = FAKE_TOKEN

        for status_code, fragment in ((401, "token"), (402, "credits")):

            def fail(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None, code=status_code) -> client.HttpResponse:
                return client.HttpResponse(status_code=code, headers={}, body=b"{}")

            transport = RecordingTransport(handlers=[fail])
            settings = self.settings(transport=transport)
            settings.output_directory = self.root / f"out-{status_code}"
            with self.assertRaises(client.RemoteError) as raised:
                client.run_submit_mode(settings)
            self.assertEqual(raised.exception.status_code, status_code)
            self.assertIn(fragment, str(raised.exception).lower())
            self.assertEqual(len(transport.requests), 1)
            self.assertNotIn(FAKE_TOKEN, str(raised.exception))

    def test_http_429_and_529_during_poll_are_retryable_without_resubmit(self) -> None:
        """Rate-limit responses on poll may retry; generation is not repeated."""
        os.environ[client.TOKEN_ENVIRONMENT_VARIABLE] = FAKE_TOKEN
        job_id = "job-rate-limit"

        def accept(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            return self.json_response(202, {"background_job_id": job_id, "status": "processing"})

        def rate_limited(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            return client.HttpResponse(status_code=429, headers={"retry-after": "0"}, body=b"slow down")

        def overloaded(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            return client.HttpResponse(status_code=529, headers={}, body=b"overloaded")

        def completed(_method: str, _url: str, _headers: dict[str, str], _body: bytes | None) -> client.HttpResponse:
            return self.json_response(200, self.completed_job_payload(job_id))

        transport = RecordingTransport(handlers=[accept, rate_limited, overloaded, completed])
        sleep_calls: list[float] = []
        settings = self.settings(transport=transport, sleep_calls=sleep_calls, maximum_attempts=10)
        manifest = client.run_submit_mode(settings)

        self.assertEqual(manifest["state"], "completed")
        self.assertEqual(sum(1 for item in transport.requests if item["method"] == "POST"), 1)
        self.assertGreaterEqual(len(sleep_calls), 2)

    def test_rejects_map_outside_pixflux_image_size(self) -> None:
        """Maps larger than PixelLab's documented image_size fail closed offline."""
        oversized = large_enough_payload()
        oversized["map"] = {"width_in_cells": 401, "height_in_cells": 16}
        oversized["tiles"] = [
            {"x": x, "y": 0, "terrain": "grass"} for x in range(401)
        ] + [
            {"x": x, "y": y, "terrain": "grass"}
            for y in range(1, 16)
            for x in range(401)
        ]
        payload_path = self.root / "oversized.worldpayload"
        payload_path.write_text(json.dumps(oversized, sort_keys=True), encoding="utf-8")
        controls = self.root / "oversized-controls"
        # visual_contract allows any positive integer dimension; the adapter enforces PixelLab bounds.
        visual_contract.write_contract(payload_path, controls, False)
        settings = self.settings()
        settings.controls_directory = controls
        with self.assertRaisesRegex(client.ContractError, "Gitea #60"):
            client.run_dry_run_mode(settings)

    def test_help_documents_token_environment_variable(self) -> None:
        """Operator help must mention env-only token handling and never a token flag."""
        buffer = io.StringIO()
        parser = client.build_argument_parser()
        parser.print_help(buffer)
        help_text = buffer.getvalue()
        self.assertIn(client.TOKEN_ENVIRONMENT_VARIABLE, help_text)
        self.assertNotIn("--token", help_text)
        self.assertIn("dry-run", help_text)


if __name__ == "__main__":
    unittest.main()
