"""Integration tests for bounded PixelLab candidate orchestration (Gitea #52).

No test here constructs a real transport. Offline runs install a transport
factory that counts and refuses every attempt, and live-mode runs inject a fake
submission boundary, so the suite provably makes zero network requests.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIRECTORY = str(Path(__file__).resolve().parent)
if TESTS_DIRECTORY not in sys.path:
    sys.path.insert(0, TESTS_DIRECTORY)

import candidate_test_support as support  # noqa: E402

candidate_approval = support.candidate_approval
candidate_orchestrator = support.candidate_orchestrator
candidate_plan = support.candidate_plan
candidate_state = support.candidate_state
pixellab_client = support.pixellab_client
visual_contract = support.visual_contract

# Three representative maps of different shapes, as issue #52 requires.
REPRESENTATIVE_MAPS = (
    ("alpha", 32, 32, 1),
    ("beta", 24, 40, 2),
    ("gamma", 48, 48, 5),
)


class OrchestrationWorkspace(unittest.TestCase):
    """Shared temporary workspace for orchestration tests."""

    def setUp(self) -> None:
        """Create a workspace holding the three representative maps."""
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.maps_directory = self.root / "maps"
        self.payload_paths: dict[str, Path] = {}
        for name, width, height, terrain_seed in REPRESENTATIVE_MAPS:
            self.payload_paths[name] = support.write_payload(
                self.maps_directory,
                f"{name}.worldpayload",
                support.build_map_payload(name, width, height, terrain_seed),
            )
        # No test may inherit a real operator token from the surrounding shell.
        self._environment = mock.patch.dict(os.environ, {}, clear=False)
        self._environment.start()
        os.environ.pop(pixellab_client.TOKEN_ENVIRONMENT_VARIABLE, None)

    def tearDown(self) -> None:
        """Restore the environment and delete the workspace."""
        self._environment.stop()
        self._temporary.cleanup()

    def offline_settings(self, map_name: str, run_name: str, **overrides) -> object:
        """Build offline orchestration settings for one representative map."""
        arguments = {
            "input_path": self.payload_paths[map_name],
            "output_root": self.root / "runs" / run_name,
            "cache_directory": self.root / "cache",
            "base_seed": 11,
            "candidate_count": 3,
            "candidate_budget": 3,
        }
        arguments.update(overrides)
        return candidate_orchestrator.OrchestrationSettings(**arguments)


class OfflineRunTests(OrchestrationWorkspace):
    """Offline runs must be deterministic, bounded, and provably network-free."""

    def test_three_representative_maps_run_offline_without_network(self) -> None:
        """Issue #52 requires at least three maps in dry-run mode."""
        for map_name, _width, _height, _seed in REPRESENTATIVE_MAPS:
            result = candidate_orchestrator.execute_run(
                self.offline_settings(map_name, f"offline-{map_name}")
            )

            self.assertEqual(candidate_plan.MODE_OFFLINE, result["mode"])
            self.assertEqual(3, len(result["candidates"]))
            self.assertEqual(0, result["submissions"])
            self.assertEqual(0, result["networkTransportAttempts"])
            for candidate in result["candidates"]:
                self.assertEqual(candidate_state.STATE_DRY_RUN, candidate["state"])
                self.assertTrue(candidate["structurallyValid"])
                self.assertFalse(candidate["eligibleForApproval"])

    def test_offline_run_never_constructs_a_transport(self) -> None:
        """The refusing factory is the run's own zero-network evidence."""
        settings = self.offline_settings("alpha", "no-transport")
        # If any offline path reached for a transport, this factory would raise
        # and the run would fail rather than quietly opening a socket.
        result = candidate_orchestrator.execute_run(settings)
        self.assertEqual(0, result["networkTransportAttempts"])

        refusing_factory = candidate_orchestrator.RefusingTransportFactory()
        with self.assertRaisesRegex(candidate_orchestrator.LiveModeError, "no PixelLab request"):
            refusing_factory()
        self.assertEqual(1, refusing_factory.attempts)

    def test_repeating_an_identical_offline_plan_is_byte_stable(self) -> None:
        """Two independent runs of the same plan must agree byte for byte."""
        first = self.offline_settings("alpha", "stable-first")
        second = self.offline_settings("alpha", "stable-second")
        candidate_orchestrator.execute_run(first)
        candidate_orchestrator.execute_run(second)

        self.assertEqual(
            support.directory_digest(first.output_root), support.directory_digest(second.output_root)
        )

    def test_rerunning_in_place_is_byte_stable(self) -> None:
        """Re-running over an existing run directory must change nothing."""
        settings = self.offline_settings("beta", "rerun")
        candidate_orchestrator.execute_run(settings)
        before = support.directory_digest(settings.output_root)
        candidate_orchestrator.execute_run(settings)

        self.assertEqual(before, support.directory_digest(settings.output_root))

    def test_candidate_directories_and_seeds_follow_the_plan(self) -> None:
        """Directory names and seeds must be predictable from the plan alone."""
        settings = self.offline_settings("alpha", "layout", base_seed=40)
        candidate_orchestrator.execute_run(settings)

        for candidate_index, expected_seed in enumerate((40, 41, 42)):
            candidate_directory = settings.output_root / "candidates" / f"candidate-{candidate_index:03d}"
            manifest = json.loads(
                (candidate_directory / pixellab_client.CANDIDATE_MANIFEST_NAME).read_bytes()
            )
            self.assertEqual(expected_seed, manifest["request"]["seed"])
            self.assertEqual(candidate_index, manifest["request"]["candidateIndex"])

    def test_each_candidate_has_a_distinct_cache_key(self) -> None:
        """Fixed seeds must produce genuinely different generation contracts."""
        result = candidate_orchestrator.execute_run(self.offline_settings("gamma", "distinct"))
        cache_keys = [candidate["requestCacheKey"] for candidate in result["candidates"]]
        self.assertEqual(len(cache_keys), len(set(cache_keys)))

    def test_run_plan_matches_its_published_schema_shape(self) -> None:
        """The persisted plan must carry every field the schema requires."""
        settings = self.offline_settings("alpha", "schema")
        candidate_orchestrator.execute_run(settings)
        run_plan = json.loads((settings.output_root / candidate_plan.RUN_PLAN_NAME).read_bytes())
        schema = json.loads(
            (Path(__file__).resolve().parents[1] / "schemas" / "run-plan.schema.json").read_bytes()
        )

        for required_property in schema["required"]:
            self.assertIn(required_property, run_plan)
        self.assertEqual(schema["properties"]["planVersion"]["const"], run_plan["planVersion"])
        self.assertEqual(
            schema["properties"]["controls"]["properties"]["endpoint"]["const"],
            run_plan["controls"]["endpoint"],
        )
        for entry in run_plan["candidates"]:
            for required_property in schema["properties"]["candidates"]["items"]["required"]:
                self.assertIn(required_property, entry)


class FailClosedTests(OrchestrationWorkspace):
    """Known-unsafe inputs must fail before any candidate directory exists."""

    def test_dimension_mismatch_fails_closed_by_default(self) -> None:
        """Gitea #55 ambiguity must stop the run unless explicitly overridden."""
        payload = support.build_map_payload("mismatch", 32, 32, 1)
        payload["map"] = {"width_in_cells": 16, "height_in_cells": 16}
        payload_path = support.write_payload(self.maps_directory, "mismatch.worldpayload", payload)
        settings = self.offline_settings("alpha", "mismatch", input_path=payload_path)

        with self.assertRaisesRegex(visual_contract.ContractError, "Gitea #55"):
            candidate_orchestrator.execute_run(settings)
        self.assertFalse((settings.output_root / "candidates").exists())

    def test_oversized_map_fails_closed_before_any_candidate(self) -> None:
        """Gitea #60 bounds must be checked before candidate directories exist."""
        payload = support.build_map_payload("oversized", 401, 20, 1)
        payload_path = support.write_payload(self.maps_directory, "oversized.worldpayload", payload)
        settings = self.offline_settings("alpha", "oversized", input_path=payload_path)

        with self.assertRaisesRegex(pixellab_client.ContractError, "Gitea #60"):
            candidate_orchestrator.execute_run(settings)
        self.assertFalse((settings.output_root / "candidates").exists())

    def test_undersized_map_fails_closed(self) -> None:
        """The lower PixelLab edge is enforced exactly like the upper one."""
        payload = support.build_map_payload("tiny", 12, 12, 1)
        payload_path = support.write_payload(self.maps_directory, "tiny.worldpayload", payload)
        settings = self.offline_settings("alpha", "tiny", input_path=payload_path)

        with self.assertRaisesRegex(pixellab_client.ContractError, "Gitea #60"):
            candidate_orchestrator.execute_run(settings)

    def test_missing_input_is_reported_clearly(self) -> None:
        """A mistyped payload path must not create a half-built run directory."""
        settings = self.offline_settings(
            "alpha", "missing", input_path=self.maps_directory / "nope.worldpayload"
        )
        with self.assertRaisesRegex(candidate_orchestrator.OrchestrationError, "not found"):
            candidate_orchestrator.execute_run(settings)


class BudgetTests(OrchestrationWorkspace):
    """Spending must be bounded before the first submission, not after."""

    def test_budget_is_enforced_before_any_submission(self) -> None:
        """A run that would overspend must not submit even the first candidate."""
        fake_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        settings = self.offline_settings(
            "alpha",
            "over-budget",
            mode=candidate_plan.MODE_LIVE,
            candidate_count=3,
            candidate_budget=1,
            enable_live_calls=True,
            confirm_credit_spend=True,
            submit_function=fake_submit,
        )

        with self.assertRaisesRegex(candidate_orchestrator.BudgetError, "budget"):
            candidate_orchestrator.execute_run(settings)
        self.assertEqual(0, fake_submit.call_count)

    def test_each_candidate_costs_at_most_one_submission(self) -> None:
        """Three cache misses must cost exactly three submissions, never more."""
        fake_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        settings = self.offline_settings(
            "alpha",
            "live-batch",
            mode=candidate_plan.MODE_LIVE,
            candidate_count=3,
            candidate_budget=3,
            enable_live_calls=True,
            confirm_credit_spend=True,
            submit_function=fake_submit,
        )

        result = candidate_orchestrator.execute_run(settings)

        self.assertEqual(3, fake_submit.submission_count)
        self.assertEqual(3, result["submissions"])
        self.assertEqual(0, fake_submit.cache_hit_count)
        for candidate in result["candidates"]:
            self.assertEqual(candidate_state.STATE_GENERATED, candidate["state"])
            self.assertTrue(candidate["eligibleForApproval"])

    def test_cached_candidates_do_not_consume_the_budget(self) -> None:
        """A fully cached replay must be runnable with a budget of zero."""
        warm_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        warm_settings = self.offline_settings(
            "beta",
            "warm-cache",
            mode=candidate_plan.MODE_LIVE,
            candidate_count=2,
            candidate_budget=2,
            enable_live_calls=True,
            confirm_credit_spend=True,
            submit_function=warm_submit,
        )
        candidate_orchestrator.execute_run(warm_settings)
        self.assertEqual(2, warm_submit.submission_count)

        # The same plan, the same cache, and a budget that forbids all spending.
        replay_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        replay_settings = self.offline_settings(
            "beta",
            "cache-replay",
            mode=candidate_plan.MODE_LIVE,
            candidate_count=2,
            candidate_budget=0,
            enable_live_calls=True,
            confirm_credit_spend=True,
            submit_function=replay_submit,
        )
        result = candidate_orchestrator.execute_run(replay_settings)

        self.assertEqual(0, replay_submit.submission_count)
        self.assertEqual(2, replay_submit.cache_hit_count)
        self.assertEqual(0, result["submissions"])
        for candidate in result["candidates"]:
            self.assertTrue(candidate["cacheHit"])
            self.assertEqual(candidate_state.STATE_GENERATED, candidate["state"])

    def test_live_mode_requires_both_explicit_opt_ins(self) -> None:
        """Neither opt-in alone may authorize spending."""
        fake_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        for enable_live, confirm_spend, expected_fragment in (
            (False, True, "--enable-live-calls"),
            (True, False, "--confirm-credit-spend"),
        ):
            settings = self.offline_settings(
                "alpha",
                f"opt-in-{enable_live}-{confirm_spend}",
                mode=candidate_plan.MODE_LIVE,
                candidate_count=1,
                candidate_budget=1,
                enable_live_calls=enable_live,
                confirm_credit_spend=confirm_spend,
                submit_function=fake_submit,
            )
            with self.assertRaisesRegex(candidate_orchestrator.LiveModeError, expected_fragment):
                candidate_orchestrator.execute_run(settings)
        self.assertEqual(0, fake_submit.call_count)


class OperatorWorkflowTests(OrchestrationWorkspace):
    """The full offline-to-decision workflow an operator actually performs."""

    def build_generated_run(self, run_name: str = "workflow"):
        """Produce a run with two validated, approvable candidates."""
        fake_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        settings = self.offline_settings(
            "alpha",
            run_name,
            mode=candidate_plan.MODE_LIVE,
            candidate_count=2,
            candidate_budget=2,
            enable_live_calls=True,
            confirm_credit_spend=True,
            submit_function=fake_submit,
        )
        candidate_orchestrator.execute_run(settings)
        return settings

    def test_status_reports_states_and_decision_counts(self) -> None:
        """An operator must be able to review a run before deciding anything."""
        settings = self.build_generated_run("status")
        status = candidate_orchestrator.report_status(settings)

        self.assertEqual(2, len(status["candidates"]))
        for candidate in status["candidates"]:
            self.assertEqual(candidate_state.STATE_GENERATED, candidate["state"])
            self.assertEqual(0, candidate["decisionCount"])

    def test_explicit_approval_and_rejection_change_reported_state(self) -> None:
        """Only recorded human decisions may move a candidate off `generated`."""
        settings = self.build_generated_run("decisions")
        candidate_orchestrator.decide_candidate(
            settings, 0, candidate_approval.DECISION_APPROVE, "craig", "reads well at full size"
        )
        candidate_orchestrator.decide_candidate(
            settings, 1, candidate_approval.DECISION_REJECT, "craig", "shoreline drifted two cells"
        )

        status = candidate_orchestrator.report_status(settings)
        by_index = {candidate["candidateIndex"]: candidate for candidate in status["candidates"]}

        self.assertEqual(candidate_state.STATE_HUMAN_APPROVED, by_index[0]["state"])
        self.assertEqual(candidate_state.STATE_REJECTED, by_index[1]["state"])
        self.assertEqual(1, by_index[0]["decisionCount"])

    def test_running_a_batch_never_approves_anything(self) -> None:
        """No automated path may leave a candidate in the approved state."""
        settings = self.build_generated_run("never-approve")
        status = candidate_orchestrator.report_status(settings)

        approved = [
            candidate
            for candidate in status["candidates"]
            if candidate["state"] == candidate_state.STATE_HUMAN_APPROVED
        ]
        self.assertEqual([], approved)
        for candidate_index in range(2):
            self.assertIsNone(
                candidate_approval.read_approval_record(settings.candidate_directory(candidate_index))
            )


class CommandLineTests(OrchestrationWorkspace):
    """The operator-facing CLI must default to safe behaviour and say so."""

    def run_cli(self, argv: list[str]) -> tuple[int, dict]:
        """Run the orchestrator CLI and return its exit code and JSON summary."""
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            exit_code = candidate_orchestrator.main(argv)
        output = stdout.getvalue().strip()
        summary = json.loads(output) if output else {}
        return exit_code, summary

    def test_cli_run_defaults_to_offline_with_zero_network(self) -> None:
        """The short command must be the safe command."""
        exit_code, summary = self.run_cli(
            [
                "run",
                "--input",
                str(self.payload_paths["alpha"]),
                "--output",
                str(self.root / "runs" / "cli"),
                "--cache",
                str(self.root / "cache"),
                "--seed",
                "11",
                "--candidates",
                "3",
                "--candidate-budget",
                "3",
            ]
        )

        self.assertEqual(candidate_orchestrator.EXIT_SUCCESS, exit_code)
        self.assertEqual(candidate_plan.MODE_OFFLINE, summary["mode"])
        self.assertEqual(0, summary["submissions"])
        self.assertEqual(0, summary["networkTransportAttempts"])
        self.assertEqual(3, len(summary["candidates"]))

    def test_cli_plan_reports_the_budget_and_makes_no_request(self) -> None:
        """Planning alone must be a free, side-effect-light operation."""
        exit_code, summary = self.run_cli(
            [
                "plan",
                "--input",
                str(self.payload_paths["beta"]),
                "--output",
                str(self.root / "runs" / "cli-plan"),
                "--cache",
                str(self.root / "cache"),
                "--candidates",
                "2",
                "--candidate-budget",
                "2",
            ]
        )

        self.assertEqual(candidate_orchestrator.EXIT_SUCCESS, exit_code)
        self.assertEqual(2, summary["candidateCount"])
        self.assertEqual(2, summary["candidateBudget"])
        self.assertEqual(0, summary["networkRequests"])
        self.assertFalse((self.root / "runs" / "cli-plan" / "candidates").exists())

    def test_cli_over_budget_returns_the_budget_exit_code(self) -> None:
        """A wrapper must be able to branch on overspending without parsing text."""
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            exit_code, _ = self.run_cli(
                [
                    "run",
                    "--input",
                    str(self.payload_paths["alpha"]),
                    "--output",
                    str(self.root / "runs" / "cli-budget"),
                    "--cache",
                    str(self.root / "cache"),
                    "--candidates",
                    "3",
                    "--candidate-budget",
                    "1",
                    "--mode",
                    "live",
                    "--enable-live-calls",
                    "--confirm-credit-spend",
                ]
            )

        self.assertEqual(candidate_orchestrator.EXIT_BUDGET_EXCEEDED, exit_code)
        self.assertIn("budget", stderr.getvalue())

    def test_cli_live_without_opt_in_returns_a_configuration_error(self) -> None:
        """Asking for live mode is not the same as authorizing it."""
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            exit_code, _ = self.run_cli(
                [
                    "run",
                    "--input",
                    str(self.payload_paths["alpha"]),
                    "--output",
                    str(self.root / "runs" / "cli-live"),
                    "--cache",
                    str(self.root / "cache"),
                    "--candidates",
                    "1",
                    "--candidate-budget",
                    "1",
                    "--mode",
                    "live",
                ]
            )

        self.assertEqual(candidate_orchestrator.EXIT_CONFIGURATION_ERROR, exit_code)
        self.assertIn("--enable-live-calls", stderr.getvalue())

    def test_cli_validate_reports_rejection_through_its_exit_code(self) -> None:
        """A wrapper must detect a broken candidate without parsing the report."""
        run_root = self.root / "runs" / "cli-validate"
        settings = self.offline_settings("alpha", "cli-validate", output_root=run_root)
        candidate_orchestrator.execute_run(settings)

        exit_code, summary = self.run_cli(["validate", "--output", str(run_root)])
        self.assertEqual(candidate_orchestrator.EXIT_SUCCESS, exit_code)
        self.assertEqual(3, len(summary["candidates"]))

        # Corrupt one candidate's manifest so its recorded seed no longer matches.
        manifest_path = (
            run_root / "candidates" / "candidate-001" / pixellab_client.CANDIDATE_MANIFEST_NAME
        )
        manifest = json.loads(manifest_path.read_bytes())
        manifest["request"]["seed"] = 999
        pixellab_client.write_file_atomically(
            manifest_path, visual_contract.canonical_json_bytes(manifest)
        )

        exit_code, summary = self.run_cli(["validate", "--output", str(run_root)])
        self.assertEqual(candidate_orchestrator.EXIT_VALIDATION_REJECTED, exit_code)
        rejected = [
            candidate
            for candidate in summary["candidates"]
            if candidate["state"] == candidate_state.STATE_REJECTED
        ]
        self.assertEqual(1, len(rejected))

    def test_cli_approve_requires_actor_and_reason(self) -> None:
        """argparse must refuse an approval that names nobody and explains nothing."""
        with self.assertRaises(SystemExit):
            candidate_orchestrator.main(
                ["approve", "--output", str(self.root / "runs" / "cli"), "--candidate", "0"]
            )

    def test_cli_help_documents_offline_default_and_token_boundary(self) -> None:
        """Help must state where the token lives and that offline is the default."""
        buffer = io.StringIO()
        candidate_orchestrator.build_argument_parser().print_help(buffer)
        help_text = buffer.getvalue()

        self.assertIn("offline", help_text)
        self.assertIn(pixellab_client.TOKEN_ENVIRONMENT_VARIABLE, help_text)
        self.assertNotIn("--token", help_text)

    def test_cli_never_reads_the_pixellab_token(self) -> None:
        """An offline run must complete with no token configured at all."""
        self.assertNotIn(pixellab_client.TOKEN_ENVIRONMENT_VARIABLE, os.environ)
        exit_code, summary = self.run_cli(
            [
                "run",
                "--input",
                str(self.payload_paths["gamma"]),
                "--output",
                str(self.root / "runs" / "cli-no-token"),
                "--cache",
                str(self.root / "cache"),
                "--candidates",
                "1",
                "--candidate-budget",
                "1",
            ]
        )

        self.assertEqual(candidate_orchestrator.EXIT_SUCCESS, exit_code)
        self.assertEqual(0, summary["networkTransportAttempts"])


if __name__ == "__main__":
    unittest.main()
