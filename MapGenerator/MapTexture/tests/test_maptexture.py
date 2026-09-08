import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "bin" / "maptexture.py"
SPEC = importlib.util.spec_from_file_location("maptexture", MODULE_PATH)
maptexture = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = maptexture
SPEC.loader.exec_module(maptexture)


class MapTextureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.job = "fixture-job"
        width = height = 64
        cells = width * height
        heights = bytes(index % 256 for index in range(cells))
        terrain = bytes(index % 4 for index in range(cells))
        (self.inputs / "map.heightmap").write_bytes(
            struct.pack("<IIQ", width, height, 7) + heights + terrain)
        (self.inputs / "map.png").write_bytes(
            maptexture.png_bytes(64, 64, [(index % 256,) * 3 for index in range(cells)]))
        tiles = []
        names = ["deep_water", "water", "dirt", "grass", "rock", "mountain"]
        for y in range(128):
            for x in range(128):
                terrain_name = names[min(5, x // 22)]
                tiles.append({"x": x, "y": y, "terrain": terrain_name,
                              "decorations": [], "features": []})
        (self.inputs / "map.worldpayload").write_text(json.dumps({
            "version": 1, "job_id": self.job,
            "map": {"width_in_cells": 64, "height_in_cells": 64}, "tiles": tiles}))
        (self.inputs / "map.playable.json").write_text(json.dumps({
            "version": 1, "job_id": self.job,
            "start_zones": [{"id": "start", "x": 70, "y": 70}],
            "resource_clusters": [{"id": "wood", "x": 72, "y": 70}],
            "settlement_labels": []}))

    def tearDown(self):
        self.temporary.cleanup()

    def arguments(self, output="run", **changes):
        values = {
            "heightmap": str(self.inputs / "map.heightmap"),
            "heightmap_png": str(self.inputs / "map.png"),
            "worldpayload": str(self.inputs / "map.worldpayload"),
            "playable": str(self.inputs / "map.playable.json"),
            "output": str(self.root / output), "seed": 11, "candidates": 2,
        }
        values.update(changes)
        return Namespace(**values)

    def test_repeated_runs_are_byte_identical_and_offline(self):
        first = maptexture.run_stage(self.arguments("first"))
        second = maptexture.run_stage(self.arguments("second"))
        self.assertEqual(first["planId"], second["planId"])
        for relative in (
            "controls/semantic-control.png", "controls/protected-mask.png",
            "controls/topology-control.png", "controls/decoration-mask.png",
            "run-plan.json", "candidates/candidate-000/candidate.png",
            "candidates/candidate-000/generation-manifest.json",
            "candidates/candidate-000/validation.json",
        ):
            self.assertEqual((self.root / "first" / relative).read_bytes(),
                             (self.root / "second" / relative).read_bytes())
        manifest = json.loads((self.root / "first/candidates/candidate-000/generation-manifest.json").read_bytes())
        self.assertFalse(manifest["networkUsed"])
        self.assertEqual(0, manifest["paidSubmissions"])

    def test_controls_are_128_and_candidate_maps_each_tile_to_four_pixels(self):
        maptexture.run_stage(self.arguments())
        control = maptexture.decode_png((self.root / "run/controls/semantic-control.png").read_bytes())
        candidate = maptexture.decode_png((self.root / "run/candidates/candidate-000/candidate.png").read_bytes())
        self.assertEqual((128, 128), control[:2])
        self.assertEqual((512, 512), candidate[:2])
        for tile_x, tile_y in ((0, 0), (64, 64), (127, 127)):
            expected = control[2][tile_y * 128 + tile_x]
            for offset_y in range(4):
                for offset_x in range(4):
                    actual = candidate[2][(tile_y * 4 + offset_y) * 512 + tile_x * 4 + offset_x]
                    if tile_x in (0, 127):
                        self.assertEqual(expected, actual)

    def test_missing_input_and_dimension_mismatch_fail_closed(self):
        (self.inputs / "map.png").unlink()
        with self.assertRaisesRegex(maptexture.ContractError, "required input"):
            maptexture.run_stage(self.arguments())
        (self.inputs / "map.png").write_bytes(
            maptexture.png_bytes(64, 64, [(0, 0, 0)] * (64 * 64)))
        world = json.loads((self.inputs / "map.worldpayload").read_text())
        world["map"]["width_in_cells"] = 63
        (self.inputs / "map.worldpayload").write_text(json.dumps(world))
        with self.assertRaisesRegex(maptexture.ContractError, "dimensions disagree"):
            maptexture.run_stage(self.arguments())

    def test_changed_control_and_wrong_candidate_dimensions_are_rejected(self):
        plan = maptexture.run_stage(self.arguments())
        controls = self.root / "run/controls"
        candidate = self.root / "run/candidates/candidate-000/candidate.png"
        (controls / "decoration-mask.png").write_bytes(b"changed")
        report = maptexture.validate_candidate(controls, candidate, plan["controlHashes"])
        self.assertFalse(report["eligibleForApproval"])
        self.assertIn("control hash mismatch: decoration-mask.png", report["failures"])
        maptexture.run_stage(self.arguments("wrong"))
        wrong = self.root / "wrong/candidates/candidate-000/candidate.png"
        wrong.write_bytes(maptexture.png_bytes(128, 128, [(0, 0, 0)] * (128 * 128)))
        report = maptexture.validate_candidate(self.root / "wrong/controls", wrong,
                                               json.loads((self.root / "wrong/run-plan.json").read_bytes())["controlHashes"])
        self.assertFalse(report["eligibleForApproval"])
        self.assertIn("expected 512x512", report["failures"][0])

    def test_protected_obstruction_and_topology_displacement_reject(self):
        plan = maptexture.run_stage(self.arguments())
        candidate = self.root / "run/candidates/candidate-000/candidate.png"
        width, height, pixels = maptexture.decode_png(candidate.read_bytes())
        pixels[2 * width + 2] = (255, 0, 255)
        candidate.write_bytes(maptexture.png_bytes(width, height, pixels))
        report = maptexture.validate_candidate(self.root / "run/controls", candidate,
                                               plan["controlHashes"])
        self.assertFalse(report["eligibleForApproval"])
        self.assertRegex(report["failures"][0], "protected obstruction|topology displacement")

    def test_only_explicit_human_decision_approves_one_background(self):
        maptexture.run_stage(self.arguments())
        common = {"output": str(self.root / "run"), "actor": "Craig", "reason": "Compared visually"}
        first = maptexture.decide(Namespace(candidate=0, **common), True)
        self.assertEqual("approved", first["decision"])
        self.assertTrue((self.root / "run/background.png").is_file())
        maptexture.decide(Namespace(candidate=1, **common), True)
        prior = json.loads((self.root / "run/candidates/candidate-000/approval.json").read_bytes())
        current = json.loads((self.root / "run/candidates/candidate-001/approval.json").read_bytes())
        self.assertEqual("rejected", prior["decision"])
        self.assertEqual("approved", current["decision"])
        with self.assertRaisesRegex(maptexture.ContractError, "actor and reason"):
            maptexture.decide(Namespace(output=str(self.root / "run"), candidate=0,
                                        actor="", reason=""), True)

    def test_run_bundle_is_immutable_and_rejecting_approved_removes_background(self):
        maptexture.run_stage(self.arguments())
        with self.assertRaisesRegex(maptexture.ContractError, "must be empty"):
            maptexture.run_stage(self.arguments())
        decision = Namespace(output=str(self.root / "run"), candidate=0,
                             actor="Craig", reason="Visual review")
        maptexture.decide(decision, True)
        self.assertTrue((self.root / "run/background.png").is_file())
        maptexture.decide(decision, False)
        self.assertFalse((self.root / "run/background.png").exists())

    def test_heightmap_png_must_be_a_matching_png(self):
        (self.inputs / "map.png").write_bytes(maptexture.png_bytes(32, 32, [(0, 0, 0)] * (32 * 32)))
        with self.assertRaisesRegex(maptexture.ContractError, "PNG dimensions disagree"):
            maptexture.run_stage(self.arguments())


if __name__ == "__main__":
    unittest.main()
