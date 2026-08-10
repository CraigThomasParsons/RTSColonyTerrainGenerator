"""Focused tests for deterministic PixelLab visual contract generation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "bin" / "visual_contract.py"
MODULE_SPEC = importlib.util.spec_from_file_location("visual_contract", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
visual_contract = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(visual_contract)


def valid_payload() -> dict:
    """Return a complete synthetic map with landmarks and terrain boundaries."""
    return {
        "version": 1,
        "job_id": "contract-test",
        "map": {"width_in_cells": 3, "height_in_cells": 2},
        "tiles": [
            {"x": 0, "y": 0, "terrain": "water"},
            {"x": 1, "y": 0, "terrain": "grass"},
            {"x": 2, "y": 0, "terrain": "grass"},
            {"x": 0, "y": 1, "terrain": "water"},
            {"x": 1, "y": 1, "terrain": "grass"},
            {"x": 2, "y": 1, "terrain": "rock"},
        ],
        "features": [{"type": "ramp", "x": 1, "y": 1}],
        "playable": {
            "start_zones": [{"id": "start-1", "x": 2, "y": 0}],
            "resource_clusters": [],
            "settlement_labels": [],
        },
    }


class VisualContractTests(unittest.TestCase):
    """Verify strict validation, determinism, and artifact provenance."""

    def write_payload(self, directory: Path, payload: dict) -> Path:
        """Write one canonical synthetic payload for a focused test."""
        input_path = directory / "input.worldpayload"
        input_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return input_path

    def test_writes_deterministic_contract_artifacts(self) -> None:
        """Repeated generation must produce identical JSON, PNG, and cache keys."""
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary_directory = Path(temporary_name)
            input_path = self.write_payload(temporary_directory, valid_payload())
            first_output = temporary_directory / "first"
            second_output = temporary_directory / "second"

            first_manifest = visual_contract.write_contract(input_path, first_output, False)
            second_manifest = visual_contract.write_contract(input_path, second_output, False)

            expected_files = {
                "visual-brief.json",
                "semantic-control.png",
                "protected-mask.png",
                "decoration-mask.png",
                "generation-manifest.template.json",
            }
            self.assertEqual(expected_files, {path.name for path in first_output.iterdir()})
            self.assertEqual(first_manifest["cacheKey"], second_manifest["cacheKey"])
            for file_name in expected_files:
                self.assertEqual((first_output / file_name).read_bytes(), (second_output / file_name).read_bytes())
            self.assertTrue((first_output / "semantic-control.png").read_bytes().startswith(b"\x89PNG"))

    def test_rejects_declared_dimension_mismatch_by_default(self) -> None:
        """Ambiguous dimensions must fail closed until Gitea issue #55 is resolved."""
        payload = valid_payload()
        payload["map"] = {"width_in_cells": 2, "height_in_cells": 2}
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary_directory = Path(temporary_name)
            input_path = self.write_payload(temporary_directory, payload)
            with self.assertRaisesRegex(visual_contract.ContractError, "Gitea #55"):
                visual_contract.write_contract(input_path, temporary_directory / "output", False)

    def test_marks_dimension_override_as_exploration_only(self) -> None:
        """Legacy inspection is explicit and produces a warning that blocks approval."""
        payload = valid_payload()
        payload["map"] = {"width_in_cells": 2, "height_in_cells": 2}
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary_directory = Path(temporary_name)
            input_path = self.write_payload(temporary_directory, payload)
            manifest = visual_contract.write_contract(input_path, temporary_directory / "output", True)
            self.assertIn("EXPLORATION ONLY", manifest["warnings"][0])

    def test_rejects_duplicate_coordinates(self) -> None:
        """Two tile records may never claim the same authoritative cell."""
        payload = valid_payload()
        payload["tiles"][1]["x"] = 0
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary_directory = Path(temporary_name)
            input_path = self.write_payload(temporary_directory, payload)
            with self.assertRaisesRegex(visual_contract.ContractError, "duplicate tile coordinate"):
                visual_contract.write_contract(input_path, temporary_directory / "output", False)

    def test_rejects_unknown_terrain(self) -> None:
        """Unknown terrain must not silently acquire an arbitrary presentation color."""
        payload = valid_payload()
        payload["tiles"][0]["terrain"] = "mystery"
        with tempfile.TemporaryDirectory() as temporary_name:
            temporary_directory = Path(temporary_name)
            input_path = self.write_payload(temporary_directory, payload)
            with self.assertRaisesRegex(visual_contract.ContractError, "unsupported terrain"):
                visual_contract.write_contract(input_path, temporary_directory / "output", False)


if __name__ == "__main__":
    unittest.main()
