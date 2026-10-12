"""Behavior tests for the deterministic Terrain stage-manifest evaluator."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIRECTORY))

from stage_manifest import evaluate_stage, manifest_digest  # noqa: E402


class StageManifestEvaluationTest(unittest.TestCase):
    """Exercise completeness through the evaluator's public file interface."""

    def test_complete_full_stack_stage_is_ready(self) -> None:
        """A receipt for every required side makes the exact manifest ready."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            digest = manifest_digest(manifest)
            receipt_paths = []
            for component in manifest["components"]:
                receipt_path = root / f"{component['id']}.receipt.json"
                receipt_path.write_text(
                    json.dumps(self._passing_receipt(manifest, component, digest)),
                    encoding="utf-8",
                )
                receipt_paths.append(receipt_path)

            result = evaluate_stage(manifest_path, receipt_paths)

        self.assertEqual("ready", result["state"])
        self.assertEqual([], result["reasons"])
        self.assertEqual(digest, result["manifestDigest"])

    def test_missing_delivery_side_is_contradictory_without_approval(self) -> None:
        """A stage cannot silently call itself complete without client coverage."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest["components"] = [
                component
                for component in manifest["components"]
                if component["side"] != "client"
            ]
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = evaluate_stage(manifest_path, [])

        self.assertEqual("contradictory", result["state"])
        self.assertIn(
            {"code": "missing-coverage", "side": "client"},
            result["reasons"],
        )

    def test_receipt_for_an_older_manifest_is_stale(self) -> None:
        """Evidence from a changed manifest cannot authorize the current stage."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            component = manifest["components"][0]
            receipt = self._passing_receipt(manifest, component, "sha256:" + "0" * 64)
            receipt_path = root / "contract.receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            result = evaluate_stage(manifest_path, [receipt_path])

        self.assertEqual("stale", result["state"])
        self.assertIn(
            {"code": "stale-receipt", "componentId": "contract"},
            result["reasons"],
        )

    def test_different_receipts_for_one_component_are_contradictory(self) -> None:
        """Two claimed result commits cannot both authorize one component."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            digest = manifest_digest(manifest)

            component = manifest["components"][0]
            first_receipt = self._passing_receipt(manifest, component, digest)
            second_receipt = self._passing_receipt(manifest, component, digest)
            second_receipt["resultCommit"] = "4" * 40
            first_path = root / "contract-first.receipt.json"
            second_path = root / "contract-second.receipt.json"
            first_path.write_text(json.dumps(first_receipt), encoding="utf-8")
            second_path.write_text(json.dumps(second_receipt), encoding="utf-8")

            result = evaluate_stage(manifest_path, [first_path, second_path])

        self.assertEqual("contradictory", result["state"])
        self.assertIn(
            {"code": "contradictory-receipts", "componentId": "contract"},
            result["reasons"],
        )

    def test_unknown_dependency_makes_manifest_contradictory(self) -> None:
        """A misspelled dependency cannot be treated as satisfied ordering."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest["components"][1]["dependsOn"] = ["missing-contract"]
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = evaluate_stage(manifest_path, [])

        self.assertEqual("contradictory", result["state"])
        self.assertIn(
            {"code": "unknown-dependency", "componentId": "server"},
            result["reasons"],
        )

    def test_receipt_without_exact_commit_is_contradictory(self) -> None:
        """A branch name or abbreviated SHA cannot stand in for immutable evidence."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            digest = manifest_digest(manifest)

            component = manifest["components"][0]
            receipt = self._passing_receipt(manifest, component, digest)
            receipt["resultCommit"] = "main"
            receipt_path = root / "contract.receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

            result = evaluate_stage(manifest_path, [receipt_path])

        self.assertEqual("contradictory", result["state"])
        self.assertIn(
            {"code": "invalid-receipt", "componentId": "contract"},
            result["reasons"],
        )

    def test_dependency_cycle_makes_manifest_contradictory(self) -> None:
        """Cyclic slices cannot provide a deterministic execution order."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest["components"][0]["dependsOn"] = ["server"]
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = evaluate_stage(manifest_path, [])

        self.assertEqual("contradictory", result["state"])
        self.assertIn({"code": "dependency-cycle"}, result["reasons"])

    def test_next_components_follow_satisfied_dependency_order(self) -> None:
        """Only components whose dependencies passed are exposed as executable."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            digest = manifest_digest(manifest)

            contract = manifest["components"][0]
            receipt_path = root / "contract.receipt.json"
            receipt_path.write_text(
                json.dumps(self._passing_receipt(manifest, contract, digest)),
                encoding="utf-8",
            )

            result = evaluate_stage(manifest_path, [receipt_path])

        self.assertEqual(["client", "server"], result["nextEligibleComponents"])

    def test_human_approved_coverage_exception_is_part_of_the_contract(self) -> None:
        """An explicit digest-bound decision may mark one delivery side inapplicable."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = self._full_stack_manifest()
            manifest["components"] = [
                component
                for component in manifest["components"]
                if component["side"] != "client"
            ]
            manifest["coverageExceptions"] = [
                {
                    "side": "client",
                    "reason": "This stage changes a server-only transport contract.",
                    "approvedBy": "Craig",
                    "approvedAt": "2026-08-13T15:00:00Z",
                }
            ]
            verification = next(
                component
                for component in manifest["components"]
                if component["id"] == "verification"
            )
            verification["dependsOn"] = ["server"]
            manifest_path = root / "stage.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = evaluate_stage(manifest_path, [])

        self.assertEqual("incomplete", result["state"])
        self.assertNotIn(
            {"code": "missing-coverage", "side": "client"},
            result["reasons"],
        )

    @staticmethod
    def _full_stack_manifest() -> dict:
        """Return the smallest manifest covering every required delivery side."""
        return {
            "protocol": "terrain.stage-manifest/v1",
            "stageId": "golden-job-preview",
            "goal": "Render one verified Golden Job in the developer workbench.",
            "baseCommit": "1" * 40,
            "integrationBranch": "stage/golden-job-preview",
            "authoritativeBranch": "main",
            "components": [
                {"id": "contract", "side": "contract", "issue": 90, "dependsOn": []},
                {"id": "server", "side": "server", "issue": 91, "dependsOn": ["contract"]},
                {"id": "client", "side": "client", "issue": 92, "dependsOn": ["contract"]},
                {
                    "id": "verification",
                    "side": "verification",
                    "issue": 93,
                    "dependsOn": ["server", "client"],
                },
            ],
            "coverageExceptions": [],
        }

    @staticmethod
    def _passing_receipt(manifest: dict, component: dict, digest: str) -> dict:
        """Bind successful evidence to one component and the exact manifest digest."""
        return {
            "protocol": "terrain.stage-receipt/v1",
            "stageId": manifest["stageId"],
            "manifestDigest": digest,
            "componentId": component["id"],
            "issue": component["issue"],
            "result": "passed",
            "resultCommit": "2" * 40,
            "evidence": [
                {
                    "command": "just quality",
                    "exitCode": 0,
                    "logDigest": "sha256:" + "3" * 64,
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
