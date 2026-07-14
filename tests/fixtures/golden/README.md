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
└── manifest.json           logical hashes for EVERY artifact this job produced
```

Only the small canonical artifacts are stored in full (~70 KB/job). The multi-MB
`.worldpayload`, `.png`, and `.chk`/`.scm` outputs are **hashed but not stored** — their
logical hashes live in `manifest.json` under the `MapGenerator/<stage>/<lane>/…` keys.

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
