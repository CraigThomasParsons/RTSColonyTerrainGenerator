"""Tests for candidate lifecycle states and explicit operator decisions (#52)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIRECTORY = str(Path(__file__).resolve().parent)
if TESTS_DIRECTORY not in sys.path:
    sys.path.insert(0, TESTS_DIRECTORY)

import candidate_test_support as support  # noqa: E402

candidate_approval = support.candidate_approval
candidate_orchestrator = support.candidate_orchestrator
candidate_plan = support.candidate_plan
candidate_state = support.candidate_state
candidate_validation = support.candidate_validation
pixellab_client = support.pixellab_client
visual_contract = support.visual_contract

MAP_WIDTH = 32
MAP_HEIGHT = 32
FIXED_MOMENT = "2026-08-09T12:34:56+00:00"


class CandidateStateTransitionTests(unittest.TestCase):
    """Automation may reject, but approval is reserved to a named human."""

    def test_automation_may_reject(self) -> None:
        """Failing closed must always be available to automated validation."""
        self.assertEqual(
            candidate_state.STATE_REJECTED,
            candidate_state.require_transition(
                candidate_state.STATE_GENERATED,
                candidate_state.STATE_REJECTED,
                candidate_state.ACTOR_KIND_AUTOMATION,
            ),
        )

    def test_automation_may_never_approve(self) -> None:
        """This is the safety property the whole lane exists to protect."""
        with self.assertRaisesRegex(candidate_state.CandidateStateError, "automation may not set state"):
            candidate_state.require_transition(
                candidate_state.STATE_GENERATED,
                candidate_state.STATE_HUMAN_APPROVED,
                candidate_state.ACTOR_KIND_AUTOMATION,
            )

    def test_an_operator_may_approve_a_generated_candidate(self) -> None:
        """An explicit human decision is the only route to approval."""
        self.assertEqual(
            candidate_state.STATE_HUMAN_APPROVED,
            candidate_state.require_transition(
                candidate_state.STATE_GENERATED,
                candidate_state.STATE_HUMAN_APPROVED,
                candidate_state.ACTOR_KIND_OPERATOR,
            ),
        )

    def test_a_dry_run_candidate_cannot_jump_straight_to_approval(self) -> None:
        """There is nothing to approve until an image exists and validates."""
        with self.assertRaisesRegex(candidate_state.CandidateStateError, "illegal candidate transition"):
            candidate_state.require_transition(
                candidate_state.STATE_DRY_RUN,
                candidate_state.STATE_HUMAN_APPROVED,
                candidate_state.ACTOR_KIND_OPERATOR,
            )

    def test_unknown_states_and_actors_are_refused(self) -> None:
        """A state read from a foreign artifact must not be silently accepted."""
        with self.assertRaisesRegex(candidate_state.CandidateStateError, "unknown candidate state"):
            candidate_state.require_known_state("looks-fine")
        with self.assertRaisesRegex(candidate_state.CandidateStateError, "unknown actor kind"):
            candidate_state.require_known_actor_kind("robot")


class CandidateApprovalTests(unittest.TestCase):
    """Decisions must be attributed, justified, evidenced, and append-only."""

    def setUp(self) -> None:
        """Create a run with one generated candidate ready for a decision."""
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.payload_path = support.write_payload(
            self.root,
            "map.worldpayload",
            support.build_map_payload("approval-test", MAP_WIDTH, MAP_HEIGHT, 1),
        )
        self.fake_submit = support.FakeSubmitBoundary(support.build_png_bytes)
        self.settings = candidate_orchestrator.OrchestrationSettings(
            input_path=self.payload_path,
            output_root=self.root / "run",
            cache_directory=self.root / "cache",
            mode=candidate_plan.MODE_LIVE,
            base_seed=5,
            candidate_count=1,
            candidate_budget=1,
            enable_live_calls=True,
            confirm_credit_spend=True,
            submit_function=self.fake_submit,
        )
        candidate_orchestrator.execute_run(self.settings)
        self.run_plan = candidate_plan.read_run_plan(self.settings.output_root)
        self.candidate_directory = self.settings.candidate_directory(0)

    def tearDown(self) -> None:
        """Delete the temporary workspace."""
        self._temporary.cleanup()

    def decide(self, decision: str, actor: str = "craig", reason: str = "shorelines read correctly") -> dict:
        """Record one decision against candidate zero with a fixed clock."""
        return candidate_approval.record_decision(
            controls_directory=self.settings.controls_directory,
            candidate_directory=self.candidate_directory,
            run_plan=self.run_plan,
            candidate_index=0,
            decision=decision,
            actor=actor,
            reason=reason,
            clock_function=support.fixed_clock(FIXED_MOMENT),
        )

    def test_approval_records_actor_time_reason_and_evidence(self) -> None:
        """An approval must stand on its own as an auditable record."""
        record = self.decide(candidate_approval.DECISION_APPROVE)

        self.assertEqual(candidate_state.STATE_HUMAN_APPROVED, record["currentState"])
        self.assertEqual(1, len(record["decisions"]))
        decision = record["decisions"][0]
        self.assertEqual("craig", decision["actor"])
        self.assertEqual(candidate_state.ACTOR_KIND_OPERATOR, decision["actorKind"])
        self.assertEqual("2026-08-09T12:34:56Z", decision["recordedAt"])
        self.assertEqual("shorelines read correctly", decision["reason"])
        self.assertEqual(candidate_state.STATE_GENERATED, decision["previousState"])

        evidence = decision["evidence"]
        self.assertEqual(self.run_plan["planId"], evidence["planId"])
        self.assertEqual(self.run_plan["controls"]["inputs"], evidence["controlInputs"])
        self.assertEqual(
            visual_contract.sha256_bytes(
                (self.candidate_directory / pixellab_client.CANDIDATE_IMAGE_NAME).read_bytes()
            ),
            evidence["candidateImageSha256"],
        )
        self.assertEqual("deterministic-masks", evidence["protectedLandmarks"]["basis"])

    def test_approval_is_written_atomically_to_the_candidate_directory_only(self) -> None:
        """Source and control artifacts stay byte-identical across a decision."""
        controls_before = support.directory_digest(self.settings.controls_directory)
        payload_before = visual_contract.sha256_bytes(self.payload_path.read_bytes())

        self.decide(candidate_approval.DECISION_APPROVE)

        self.assertEqual(controls_before, support.directory_digest(self.settings.controls_directory))
        self.assertEqual(payload_before, visual_contract.sha256_bytes(self.payload_path.read_bytes()))
        # No partial temporary file may survive an atomic publish.
        leftovers = [path.name for path in self.candidate_directory.iterdir() if path.name.startswith(".")]
        self.assertEqual([], leftovers)

    def test_decision_requires_an_actor_and_a_reason(self) -> None:
        """An unattributed or unexplained decision is not evidence of anything."""
        with self.assertRaisesRegex(candidate_approval.CandidateApprovalError, "non-empty actor"):
            self.decide(candidate_approval.DECISION_APPROVE, actor="   ")
        with self.assertRaisesRegex(candidate_approval.CandidateApprovalError, "non-empty reason"):
            self.decide(candidate_approval.DECISION_APPROVE, reason="")

    def test_unknown_decision_is_refused(self) -> None:
        """Only approve and reject exist; there is no implicit third outcome."""
        with self.assertRaisesRegex(candidate_approval.CandidateApprovalError, "unknown decision"):
            self.decide("maybe")

    def test_rejection_is_recorded_and_blocks_the_candidate(self) -> None:
        """A rejected candidate must never read as approved afterwards."""
        record = self.decide(candidate_approval.DECISION_REJECT, reason="roads drift at the river")

        self.assertEqual(candidate_state.STATE_REJECTED, record["currentState"])
        report = candidate_validation.validate_candidate(
            self.settings.controls_directory, self.candidate_directory, self.run_plan, 0
        )
        self.assertEqual(
            candidate_state.STATE_REJECTED,
            candidate_approval.resolve_current_state(self.candidate_directory, report),
        )

    def test_decisions_are_appended_not_replaced(self) -> None:
        """Superseding a decision must never erase that it was made."""
        self.decide(candidate_approval.DECISION_REJECT, reason="first look was wrong")
        record = self.decide(candidate_approval.DECISION_APPROVE, reason="second look at full size")

        self.assertEqual(candidate_state.STATE_HUMAN_APPROVED, record["currentState"])
        self.assertEqual([1, 2], [decision["sequence"] for decision in record["decisions"]])
        self.assertEqual("first look was wrong", record["decisions"][0]["reason"])
        self.assertEqual(candidate_state.STATE_REJECTED, record["decisions"][1]["previousState"])

    def test_a_candidate_that_fails_validation_cannot_be_approved(self) -> None:
        """Approval re-validates, so a candidate edited since generation is refused."""
        pixellab_client.write_file_atomically(
            self.candidate_directory / pixellab_client.CANDIDATE_IMAGE_NAME,
            support.build_png_bytes(MAP_WIDTH, MAP_HEIGHT, red=250),
        )

        with self.assertRaisesRegex(candidate_approval.CandidateApprovalError, "not eligible"):
            self.decide(candidate_approval.DECISION_APPROVE)

    def test_a_dry_run_candidate_cannot_be_approved(self) -> None:
        """There is no image to judge, so no approval may be recorded."""
        offline_settings = candidate_orchestrator.OrchestrationSettings(
            input_path=self.payload_path,
            output_root=self.root / "offline-run",
            cache_directory=self.root / "offline-cache",
            base_seed=5,
            candidate_count=1,
            candidate_budget=1,
        )
        candidate_orchestrator.execute_run(offline_settings)
        offline_plan = candidate_plan.read_run_plan(offline_settings.output_root)

        with self.assertRaisesRegex(candidate_approval.CandidateApprovalError, "not eligible"):
            candidate_approval.record_decision(
                controls_directory=offline_settings.controls_directory,
                candidate_directory=offline_settings.candidate_directory(0),
                run_plan=offline_plan,
                candidate_index=0,
                decision=candidate_approval.DECISION_APPROVE,
                actor="craig",
                reason="looks fine on paper",
                clock_function=support.fixed_clock(FIXED_MOMENT),
            )

    def test_naive_timestamps_are_refused(self) -> None:
        """An ambiguous local timestamp would weaken the whole audit trail."""
        with self.assertRaisesRegex(candidate_approval.CandidateApprovalError, "timezone-aware"):
            candidate_approval.record_decision(
                controls_directory=self.settings.controls_directory,
                candidate_directory=self.candidate_directory,
                run_plan=self.run_plan,
                candidate_index=0,
                decision=candidate_approval.DECISION_APPROVE,
                actor="craig",
                reason="fine",
                clock_function=support.fixed_clock("2026-08-09T12:34:56"),
            )

    def test_approval_record_matches_its_published_schema_shape(self) -> None:
        """The persisted record must carry every field the schema requires."""
        self.decide(candidate_approval.DECISION_APPROVE)
        record_path = self.candidate_directory / candidate_approval.APPROVAL_RECORD_NAME
        record = json.loads(record_path.read_bytes())
        schema_path = (
            Path(__file__).resolve().parents[1] / "schemas" / "candidate-approval.schema.json"
        )
        schema = json.loads(schema_path.read_bytes())

        for required_property in schema["required"]:
            self.assertIn(required_property, record)
        for required_property in schema["properties"]["decisions"]["items"]["required"]:
            self.assertIn(required_property, record["decisions"][0])
        self.assertEqual(schema["properties"]["approvalVersion"]["const"], record["approvalVersion"])


class ExplorationApprovalTests(unittest.TestCase):
    """A #55 dimension override must never reach an approval decision."""

    def test_exploration_run_produces_controls_and_no_candidate(self) -> None:
        """Local inspection is allowed; approvable candidates are not."""
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            payload = support.build_map_payload("exploration", MAP_WIDTH, MAP_HEIGHT, 1)
            # 17 is neither the tile extent nor half of it: 16x16 would now be
            # accepted outright, tiles spanning exactly cells x 2 being the rule.
            payload["map"] = {"width_in_cells": 17, "height_in_cells": 16}
            payload_path = support.write_payload(root, "map.worldpayload", payload)
            settings = candidate_orchestrator.OrchestrationSettings(
                input_path=payload_path,
                output_root=root / "run",
                cache_directory=root / "cache",
                candidate_count=3,
                candidate_budget=3,
                allow_exploration_dimensions=True,
            )

            result = candidate_orchestrator.execute_run(settings)

            self.assertTrue(result["explorationOnly"])
            self.assertEqual([], result["candidates"])
            self.assertEqual(0, result["networkTransportAttempts"])
            # Controls exist for local inspection, which is the whole point.
            self.assertTrue((settings.controls_directory / "semantic-control.png").is_file())
            self.assertFalse((settings.output_root / "candidates").exists())

    def test_exploration_run_refuses_live_mode(self) -> None:
        """Ambiguous dimensions may never be submitted to PixelLab."""
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            payload = support.build_map_payload("exploration", MAP_WIDTH, MAP_HEIGHT, 1)
            # 17 is neither the tile extent nor half of it: 16x16 would now be
            # accepted outright, tiles spanning exactly cells x 2 being the rule.
            payload["map"] = {"width_in_cells": 17, "height_in_cells": 16}
            payload_path = support.write_payload(root, "map.worldpayload", payload)
            settings = candidate_orchestrator.OrchestrationSettings(
                input_path=payload_path,
                output_root=root / "run",
                cache_directory=root / "cache",
                mode=candidate_plan.MODE_LIVE,
                candidate_count=1,
                candidate_budget=1,
                allow_exploration_dimensions=True,
                enable_live_calls=True,
                confirm_credit_spend=True,
                submit_function=support.FakeSubmitBoundary(support.build_png_bytes),
            )
            run_plan = candidate_orchestrator.plan_run(settings)

            with self.assertRaisesRegex(candidate_orchestrator.LiveModeError, "Gitea #55"):
                candidate_orchestrator.require_live_authorization(settings, run_plan)


if __name__ == "__main__":
    unittest.main()
