# Golden Jobs

Three fully-completed runs of the **legacy** pipeline, captured as the baseline that
migration slices prove parity against. Documented in [docs/baseline/](../../../docs/baseline/).

```
<job-id>/
├── input.job.json          the pipeline input (Heightmap job spec)
├── <job-id>.heightmap      Heightmap output  (binary)
├── <job-id>.weather        WeatherAnalyses output (binary)
├── <job-id>.maptiles       Tiler output (binary)
├── <job-id>.playable.json  Playable output (text)
├── <job-id>.worldpayload   TreePlanter output (text, ~5 MB) — re-captured, see below
└── manifest.json           logical hashes for EVERY artifact this job produced
```

The small canonical artifacts are stored in full (~70 KB/job). The `.png` and `.chk`/`.scm`
outputs are **hashed but not stored** — their logical hashes live in `manifest.json` under
the `MapGenerator/<stage>/<lane>/…` keys.

## The re-captured `.worldpayload`

The original capture hashed TreePlanter's artifact without storing it, which left the
replayed preview and map document with no canopy at all. Each `.worldpayload` here was
therefore produced by re-running the legacy TreePlanter stage over the fixtures already in
this directory — it needs only `.heightmap`, `.maptiles` and `.weather`, all of which are
stored:

```bash
php scripts/tools/capture_treeplanter_worldpayload.php
```

The capture is deterministic (TreePlanter seeds its placement at a fixed 12345), so re-running
it reproduces these bytes exactly. It does **not** reproduce the `manifest.json` hash of the
original run: the artifacts are downstream of the `.weather` planar-decode fix (issue #39),
so the weather values these tiles carry — and the tree placements derived from them — differ
from the run the manifest recorded. The manifest entry stays as the record of that original
run; it is not a claim about this file.

## Using them

Recompute a stored artifact's logical hash and compare to the manifest:

```bash
python -m tools.artifact_hash hash tests/fixtures/golden/<job>/<job>.maptiles
```

The C# compatibility harness (`tests/MapGen.CompatibilityTests`) loads these fixtures, parses
`manifest.json`, and asserts that C# binary hashing agrees with the recorded Python hashes —
the parity substrate Epic 1's Tiler comparison builds on.

## Regenerating a manifest

```bash
python -m tools.artifact_hash manifest <job-id> --out tests/fixtures/golden/<job-id>/manifest.json
```

Manifests are only valid while the corresponding artifacts still sit in the stage outboxes;
the stored copies in each fixture directory are the durable record.
