"""Tests for deterministic candidate structural validation (Gitea #52)."""

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

candidate_orchestrator = support.candidate_orchestrator
candidate_state = support.candidate_state
candidate_validation = support.candidate_validation
pixellab_client = support.pixellab_client
visual_contract = support.visual_contract

MAP_WIDTH = 32
MAP_HEIGHT = 32


class CandidateValidationTests(unittest.TestCase):
    """Validation must reject broken candidates and never approve any."""

    def setUp(self) -> None:
        """Run one offline batch so there is a real run directory to validate."""
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.payload_path = support.write_payload(
            self.root,
            "map.worldpayload",
            support.build_map_payload("validation-test", MAP_WIDTH, MAP_HEIGHT, 1),
        )
        self.run_root = self.root / "run"
        self.settings = candidate_orchestrator.OrchestrationSettings(
            input_path=self.payload_path,
            output_root=self.run_root,
            cache_directory=self.root / "cache",
            base_seed=5,
            candidate_count=1,
            candidate_budget=1,
        )
        self.run_plan = candidate_orchestrator.plan_run(self.settings)
        self.controls_directory = self.settings.controls_directory
        self.candidate_directory = self.settings.candidate_directory(0)

    def tearDown(self) -> None:
        """Delete the temporary workspace."""
        self._temporary.cleanup()

    def generate_dry_run_candidate(self) -> None:
        """Publish a real offline candidate manifest with no image."""
        adapter_settings = candidate_orchestrator.build_adapter_settings(
            self.settings, 0, 5, candidate_orchestrator.RefusingTransportFactory()
        )
        pixellab_client.run_dry_run_mode(adapter_settings)

    def generate_completed_candidate(self, image_bytes: bytes | None = None) -> bytes:
        """Publish a candidate as a fake completed submission would have."""
        fake_submit = support.FakeSubmitBoundary(
            lambda width, height: image_bytes
            if image_bytes is not None
            else support.build_png_bytes(width, height)
        )
        adapter_settings = pixellab_client.AdapterSettings(
            controls_directory=self.controls_directory,
            output_directory=self.candidate_directory,
            cache_directory=self.settings.cache_directory,
            seed=5,
            candidate_index=0,
        )
        fake_submit(adapter_settings)
        return (self.candidate_directory / pixellab_client.CANDIDATE_IMAGE_NAME).read_bytes()

    def validate(self) -> dict:
        """Validate candidate zero of this run."""
        return candidate_validation.validate_candidate(
            self.controls_directory, self.candidate_directory, self.run_plan, 0
        )

    def test_dry_run_candidate_is_valid_but_not_approvable(self) -> None:
        """An offline candidate is a complete outcome with nothing to approve."""
        self.generate_dry_run_candidate()
        report = self.validate()

        self.assertTrue(report["structurallyValid"])
        self.assertFalse(report["eligibleForApproval"])
        self.assertFalse(report["imagePresent"])
        self.assertEqual(candidate_state.STATE_DRY_RUN, report["resultingState"])
        self.assertEqual(["candidate-image-present"], report["failures"])

    def test_completed_candidate_is_generated_and_approvable(self) -> None:
        """A structurally sound image reaches `generated`, never `human-approved`."""
        image_bytes = self.generate_completed_candidate()
        report = self.validate()

        self.assertTrue(report["structurallyValid"])
        self.assertTrue(report["eligibleForApproval"])
        self.assertEqual(candidate_state.STATE_GENERATED, report["resultingState"])
        self.assertEqual([], report["failures"])
        # Automated validation may mark a candidate ready for a human, never approved.
        self.assertNotEqual(candidate_state.STATE_HUMAN_APPROVED, report["resultingState"])
        self.assertEqual(
            visual_contract.sha256_bytes(image_bytes), report["evidence"]["candidateImage"]["sha256"]
        )

    def test_validation_report_is_byte_stable(self) -> None:
        """Re-validating unchanged artifacts must produce identical evidence."""
        self.generate_completed_candidate()
        first = visual_contract.canonical_json_bytes(self.validate())
        second = visual_contract.canonical_json_bytes(self.validate())
        self.assertEqual(first, second)

    def test_wrong_candidate_image_dimensions_are_rejected(self) -> None:
        """An image that is not one pixel per cell cannot carry landmarks."""
        self.generate_completed_candidate()
        # Replace the image with a correctly hashed but wrongly sized one so the
        # dimension check, not the hash check, is what fails.
        wrong_size_image = support.build_png_bytes(MAP_WIDTH - 4, MAP_HEIGHT)
        pixellab_client.write_file_atomically(
            self.candidate_directory / pixellab_client.CANDIDATE_IMAGE_NAME, wrong_size_image
        )
        manifest_path = self.candidate_directory / pixellab_client.CANDIDATE_MANIFEST_NAME
        manifest = json.loads(manifest_path.read_bytes())
        manifest["output"]["sha256"] = visual_contract.sha256_bytes(wrong_size_image)
        manifest["output"]["width"] = MAP_WIDTH - 4
        pixellab_client.write_file_atomically(
            manifest_path, visual_contract.canonical_json_bytes(manifest)
        )

        report = self.validate()

        self.assertFalse(report["structurallyValid"])
        self.assertFalse(report["eligibleForApproval"])
        self.assertEqual(candidate_state.STATE_REJECTED, report["resultingState"])
        self.assertIn("candidate-image-dimensions-match-request", report["failures"])
        self.assertIn("candidate-image-dimensions-match-masks", report["failures"])

    def test_tampered_candidate_image_fails_the_hash_check(self) -> None:
        """A candidate swapped after generation must lose its provenance."""
        self.generate_completed_candidate()
        pixellab_client.write_file_atomically(
            self.candidate_directory / pixellab_client.CANDIDATE_IMAGE_NAME,
            support.build_png_bytes(MAP_WIDTH, MAP_HEIGHT, red=200, green=1, blue=1),
        )

        report = self.validate()

        self.assertFalse(report["structurallyValid"])
        self.assertIn("candidate-image-hash-matches-manifest", report["failures"])

    def test_edited_control_artifact_is_refused_outright(self) -> None:
        """Issue #50 inputs are immutable; an edited mask stops validation dead."""
        self.generate_completed_candidate()
        protected_mask_path = self.controls_directory / pixellab_client.PROTECTED_MASK_NAME
        protected_mask_path.write_bytes(support.build_png_bytes(MAP_WIDTH, MAP_HEIGHT))

        with self.assertRaisesRegex(pixellab_client.ContractError, "does not match the hash"):
            self.validate()

    def test_seed_mismatch_is_rejected(self) -> None:
        """A manifest generated under a different seed is not this candidate."""
        self.generate_completed_candidate()
        manifest_path = self.candidate_directory / pixellab_client.CANDIDATE_MANIFEST_NAME
        manifest = json.loads(manifest_path.read_bytes())
        manifest["request"]["seed"] = 999
        pixellab_client.write_file_atomically(
            manifest_path, visual_contract.canonical_json_bytes(manifest)
        )

        report = self.validate()

        self.assertFalse(report["structurallyValid"])
        self.assertIn("seed-matches-plan", report["failures"])

    def test_cache_key_must_be_reproducible_from_the_controls(self) -> None:
        """A recorded cache key that the controls cannot reproduce is not trustworthy."""
        self.generate_completed_candidate()
        manifest_path = self.candidate_directory / pixellab_client.CANDIDATE_MANIFEST_NAME
        manifest = json.loads(manifest_path.read_bytes())
        manifest["request"]["requestCacheKey"] = "0" * 64
        pixellab_client.write_file_atomically(
            manifest_path, visual_contract.canonical_json_bytes(manifest)
        )

        report = self.validate()

        self.assertFalse(report["structurallyValid"])
        self.assertIn("request-cache-key-reproducible", report["failures"])

    def test_protected_landmark_evidence_comes_from_the_masks_only(self) -> None:
        """Alignment evidence must cite the deterministic mask, not generated art."""
        self.generate_completed_candidate()
        report = self.validate()
        evidence = report["evidence"]["protectedLandmarks"]

        self.assertEqual("deterministic-masks", evidence["basis"])
        self.assertGreater(evidence["cellCount"], 0)
        self.assertEqual(
            self.run_plan["controls"]["inputs"]["protectedMaskSha256"], evidence["protectedMaskSha256"]
        )
        self.assertIn("never inspected", evidence["note"])

    def test_protected_coordinates_match_the_mask_pixels(self) -> None:
        """The mask decoder must agree with the contract builder's own mask."""
        protected_bytes = (self.controls_directory / pixellab_client.PROTECTED_MASK_NAME).read_bytes()
        coordinates = candidate_validation.collect_protected_coordinates(protected_bytes)
        width, height, pixels = candidate_validation.decode_deterministic_rgb_png(
            protected_bytes, "protected-mask.png"
        )

        self.assertEqual((MAP_WIDTH, MAP_HEIGHT), (width, height))
        expected = [
            (column, row)
            for row in range(height)
            for column in range(width)
            if pixels[row * width + column] == candidate_validation.PROTECTED_MASK_COLOR
        ]
        self.assertEqual(expected, coordinates)

    def test_non_deterministic_png_is_refused_as_a_mask(self) -> None:
        """Only the deterministic encoder's own output may be read as a mask."""
        with self.assertRaisesRegex(candidate_validation.CandidateValidationError, "not a PNG file"):
            candidate_validation.decode_deterministic_rgb_png(b"not a png at all", "fake-mask.png")

    def test_missing_manifest_is_an_explicit_failure(self) -> None:
        """A candidate directory without a manifest cannot be validated at all."""
        self.candidate_directory.mkdir(parents=True, exist_ok=True)
        with self.assertRaisesRegex(candidate_validation.CandidateValidationError, "not found"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
