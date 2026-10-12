"""Tests for the deterministic candidate run plan (Gitea #52)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# The shared support module lives beside this file. Adding its directory keeps
# the tests runnable by path, which is how the repository documents them.
TESTS_DIRECTORY = str(Path(__file__).resolve().parent)
if TESTS_DIRECTORY not in sys.path:
    sys.path.insert(0, TESTS_DIRECTORY)

import candidate_test_support as support  # noqa: E402

candidate_plan = support.candidate_plan
visual_contract = support.visual_contract


def controls_manifest_for(payload_path: Path, controls_directory: Path, allow_inferred: bool = False) -> dict:
    """
    Description:
        Build issue #50 controls and return the manifest template they produced.
    Required State:
        The payload path names a readable synthetic world payload.
    Usage:
        Use to give plan tests a real, hash-consistent controls manifest.
    Parameters:
        payload_path (Path): World payload file.
        controls_directory (Path): Destination for the control artifacts.
        allow_inferred (bool): Use the exploration-only dimension override.
    Returns:
        dict: The generation-manifest template that was written.
    Other I/O:
        - files: writes the five issue #50 control artifacts
    """
    return visual_contract.write_contract(payload_path, controls_directory, allow_inferred)


class CandidateSeedDerivationTests(unittest.TestCase):
    """Fixed seeds must be predictable, distinct, and explicitly bounded."""

    def test_derived_seeds_are_sequential_from_the_base_seed(self) -> None:
        """A reader must be able to predict any candidate's seed by hand."""
        self.assertEqual([7, 8, 9], candidate_plan.derive_candidate_seeds(7, 3, None))

    def test_explicit_seeds_override_derivation(self) -> None:
        """Reproducing one historic candidate must not require its whole batch."""
        self.assertEqual([4, 19, 55], candidate_plan.derive_candidate_seeds(1, 3, [4, 19, 55]))

    def test_explicit_seeds_must_match_the_candidate_count(self) -> None:
        """A miscounted seed list is an operator error, not a silent truncation."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "explicit seeds"):
            candidate_plan.derive_candidate_seeds(1, 3, [4, 19])

    def test_explicit_seeds_must_be_distinct(self) -> None:
        """Two candidates sharing a seed would not be comparable in #54."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "distinct"):
            candidate_plan.derive_candidate_seeds(1, 2, [4, 4])

    def test_candidate_count_is_hard_bounded(self) -> None:
        """A typo must never plan an unbounded batch of paid generations."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "hard maximum"):
            candidate_plan.derive_candidate_seeds(1, candidate_plan.MAXIMUM_CANDIDATE_COUNT + 1, None)

    def test_candidate_count_must_be_positive(self) -> None:
        """A zero-candidate run is a planning mistake worth reporting."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "at least 1"):
            candidate_plan.derive_candidate_seeds(1, 0, None)


class CandidateBudgetTests(unittest.TestCase):
    """The submission budget must stay small, explicit, and self-consistent."""

    def test_budget_may_not_exceed_the_candidate_count(self) -> None:
        """One candidate is at most one submission, so a larger budget is nonsense."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "planned candidates"):
            candidate_plan.require_candidate_budget(4, 2)

    def test_budget_is_hard_bounded(self) -> None:
        """A large budget must be impossible, not merely discouraged."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "hard maximum"):
            candidate_plan.require_candidate_budget(candidate_plan.MAXIMUM_CANDIDATE_BUDGET + 1, 100)

    def test_zero_budget_is_allowed_for_a_cache_only_run(self) -> None:
        """Replaying a fully cached batch must be expressible as zero spending."""
        self.assertEqual(0, candidate_plan.require_candidate_budget(0, 3))


class RunPlanTests(unittest.TestCase):
    """A plan must be deterministic, self-verifying, and honest about #55."""

    def setUp(self) -> None:
        """Create a temporary workspace with one representative map."""
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.payload_path = support.write_payload(
            self.root, "map.worldpayload", support.build_map_payload("plan-test", 32, 32, 1)
        )
        self.controls_manifest = controls_manifest_for(self.payload_path, self.root / "controls")

    def tearDown(self) -> None:
        """Delete the temporary workspace."""
        self._temporary.cleanup()

    def build_plan(self, **overrides) -> dict:
        """Build a plan from this fixture, with per-test overrides."""
        arguments = {
            "source_sha256": visual_contract.sha256_bytes(self.payload_path.read_bytes()),
            "source_file_name": self.payload_path.name,
            "controls_manifest": self.controls_manifest,
            "mode": candidate_plan.MODE_OFFLINE,
            "base_seed": 11,
            "candidate_count": 3,
            "explicit_seeds": None,
            "candidate_budget": 3,
        }
        arguments.update(overrides)
        return candidate_plan.build_run_plan(**arguments)

    def test_identical_inputs_produce_an_identical_plan(self) -> None:
        """Deriving the plan twice must yield the same identifier and bytes."""
        first = self.build_plan()
        second = self.build_plan()
        self.assertEqual(first, second)
        self.assertEqual(
            visual_contract.canonical_json_bytes(first),
            visual_contract.canonical_json_bytes(second),
        )

    def test_plan_fixes_candidate_indices_seeds_and_directories(self) -> None:
        """Indices, seeds, and directories are decided before anything is written."""
        plan = self.build_plan()
        self.assertEqual(
            [(entry["candidateIndex"], entry["seed"], entry["directory"]) for entry in plan["candidates"]],
            [
                (0, 11, "candidates/candidate-000"),
                (1, 12, "candidates/candidate-001"),
                (2, 13, "candidates/candidate-002"),
            ],
        )
        self.assertEqual(plan["budget"]["submissionsPerCandidate"], 1)

    def test_changing_the_seed_changes_the_plan_identifier(self) -> None:
        """Two different runs must never share a plan identifier."""
        self.assertNotEqual(self.build_plan()["planId"], self.build_plan(base_seed=99)["planId"])

    def test_plan_round_trips_through_disk(self) -> None:
        """A published plan must read back identical to what was built."""
        plan = self.build_plan()
        candidate_plan.write_run_plan(self.root / "run", plan)
        self.assertEqual(plan, candidate_plan.read_run_plan(self.root / "run"))

    def test_edited_plan_is_rejected_on_read(self) -> None:
        """Hand-editing a plan between generation and approval must be detected."""
        plan = self.build_plan()
        plan_path = candidate_plan.write_run_plan(self.root / "run", plan)
        tampered = plan_path.read_text(encoding="utf-8").replace('"seed":11', '"seed":12')
        plan_path.write_text(tampered, encoding="utf-8")
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "modified after generation"):
            candidate_plan.read_run_plan(self.root / "run")

    def test_unknown_mode_is_refused(self) -> None:
        """Only the declared offline and live modes may be planned."""
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "unknown mode"):
            self.build_plan(mode="whatever")

    def test_exploration_override_plans_no_candidates(self) -> None:
        """A #55 dimension override may produce controls and nothing else."""
        payload = support.build_map_payload("exploration", 32, 32, 1)
        # 17 is neither the tile extent nor half of it: 16x16 would now be accepted
        # outright, because tiles spanning exactly cells x 2 is the verified rule.
        payload["map"] = {"width_in_cells": 17, "height_in_cells": 16}
        payload_path = support.write_payload(self.root, "exploration.worldpayload", payload)
        exploration_manifest = controls_manifest_for(
            payload_path, self.root / "exploration-controls", allow_inferred=True
        )

        plan = self.build_plan(controls_manifest=exploration_manifest)

        self.assertTrue(plan["explorationOnly"])
        self.assertEqual([], plan["candidates"])
        self.assertEqual(0, plan["budget"]["candidateBudget"])
        self.assertTrue(any(warning.startswith("EXPLORATION ONLY") for warning in plan["warnings"]))

    def test_unknown_candidate_index_is_refused(self) -> None:
        """Validation and approval may only address candidates the plan created."""
        plan = self.build_plan()
        with self.assertRaisesRegex(candidate_plan.CandidatePlanError, "not part of this run plan"):
            candidate_plan.candidate_entry(plan, 9)


if __name__ == "__main__":
    unittest.main()
