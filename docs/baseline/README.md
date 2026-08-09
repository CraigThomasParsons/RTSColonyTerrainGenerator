# Pipeline Baseline (Phase 0 / M1)

This directory characterizes the **existing** MapGenerator pipeline so that later
migration slices have a fixed reference to prove parity against. It documents what the
pipeline *does today* — including where the current behaviour is imperfect — not what it
should become.

Authoritative sources are the on-disk code and `docs/Stage_Contract.md`. Where
`MapGenerator/stages.md` disagrees with the code, the code wins and the discrepancy is
recorded in [artifact-formats.md](artifact-formats.md#baseline-hazards) and
[pipeline-graph.md](pipeline-graph.md).

## Contents

- [stage-inventory.md](stage-inventory.md) — every stage: language, invocation, inputs, outputs.
- [artifact-formats.md](artifact-formats.md) — the on-disk format of each artifact type, plus baseline hazards.
- [pipeline-graph.md](pipeline-graph.md) — the real data-flow DAG and the per-stage lane lifecycle.

## Golden jobs

Three fully-completed pipeline runs are captured as fixtures under
[tests/fixtures/golden/](../../tests/fixtures/golden/):

| Job id | Map | Reached |
|---|---|---|
| `43860dcf-6469-42a7-9843-4e33abeacfac` | 64×64 cells | all 11 wired stages |
| `3c96b74c-6f86-4d27-a0ca-c567f385ae8e` | 64×64 cells | all 11 wired stages |
| `0860a05a-a410-4cc2-987d-a48a4cd120c7` | 64×64 cells | all 11 wired stages |

Each fixture stores the small canonical artifacts in full (`input.job.json`, `.heightmap`,
`.weather`, `.maptiles`, `.playable.json`) plus a `manifest.json` of **logical hashes** for
every artifact the job produced — including the multi-MB `.worldpayload`, `.png`, and
`.chk`/`.scm` outputs that are hashed but not stored. See
[tests/fixtures/golden/README.md](../../tests/fixtures/golden/README.md).

## Artifact hash tool

`tools/artifact_hash` computes an artifact's **logical** hash — insensitive to key order and
to non-contractual metadata (timestamps) — so a replacement stage can be checked for parity:

```bash
python -m tools.artifact_hash hash MapGenerator/Tiler/outbox/<job>.maptiles
python -m tools.artifact_hash manifest <job> --out tests/fixtures/golden/<job>/manifest.json
```

For binary artifacts the logical hash is `sha256:` + hex of the raw bytes, which the C#
compatibility harness (`tests/MapGen.CompatibilityTests`) reproduces exactly — that shared
definition is what makes cross-language parity checks trustworthy.

## Exit criteria (met)

- One command runs a known job through the current pipeline (`python -m tools.mapgenctl run`).
- Output artifacts can be inspected and hashed (`tools.artifact_hash`, `mapgenctl inspect-heightmap`).
- Failures are logged by job and stage (`logs/jobs/<id>/<stage>.log`).
- Current behaviour is characterized, imperfections included (see baseline hazards).
