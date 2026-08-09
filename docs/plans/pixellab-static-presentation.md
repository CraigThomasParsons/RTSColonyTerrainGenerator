# PixelLab-assisted static map presentation

## Outcome

Gitea outcome #49 adds an optional visual-production lane that enriches
procedurally generated maps while leaving gameplay data authoritative. The
target is a one-to-two-week vertical slice, not immediate production adoption.

## Architecture

```text
.worldpayload
     |
     +-- authoritative gameplay geometry
     |
     v
VisualBrief + semantic-control.png
            + protected-mask.png
            + decoration-mask.png
     |
     v
PixelLab v2 async adapter (opt-in, #51)
     |
     +-- content-addressed cache
     +-- provenance manifest
     v
candidate background (#52)
     |
     +-- structural validator
     +-- human acceptance
     v
approved optional underlay (#53)
     |
     +-- authoritative overlays rendered above it
     v
evaluation and go/no-go ADR (#54)
```

## Dependency order

1. #50 defines deterministic contracts and controls.
2. #51 implements the PixelLab client, polling, cache and manifests.
3. #52 creates bounded fixed-seed candidates from WorldSnapshot/control inputs.
4. #53 integrates only accepted candidates beneath authoritative overlays.
5. #54 measures fidelity, readability, latency and credits, then chooses whole
   maps, Wang tiles plus map objects, or no production adoption.

Issue #55 reconciles a discovered mismatch between declared dimensions and tile
extents. It blocks strict use of affected live artifacts, but synthetic contract
tests and documentation can proceed.

## Artifact contract

Each cell in `semantic-control.png` maps one-to-one to an authoritative tile.
Colors are contract values, not presentation colors. `protected-mask.png`
protects water, terrain boundaries, roads, features, starts, resources and
settlement labels. `decoration-mask.png` permits invention only on stable,
non-protected cells.

The generation manifest records all immutable input hashes, prompt version,
endpoint, seed, candidate index, PixelLab job ID, returned usage, output
dimensions/MIME/hash and acceptance evidence. Its cache key is derived before a
network call and prevents duplicate spending for identical requests.

## PixelLab integration rules

- Base URL: `https://api.pixellab.ai/v2`.
- Authentication: bearer token supplied outside git.
- Initial endpoint: `/create-image-pixflux-background`.
- Generation is asynchronous and polled through `/background-jobs/{job_id}`.
- Live calls require an explicit enable flag, configured token, balance check
  and candidate budget.
- HTTP 401, 402, 429 and 529 fail with actionable messages and do not trigger
  unbounded resubmission.
- A cache hit makes no generation request.
- Tokens are never included in logs, manifests, prompts or test fixtures.

## Validation and acceptance

Automated validation checks contract/schema versions, hashes, PNG dimensions,
MIME type, mask dimensions and protected-landmark alignment. Image semantics
still require human review during the experiment.

The evaluation gallery uses at least three maps and fixed seeds. Reviewers score
shorelines, roads, traversability cues, starts/resources, visual cohesion and
readability. Credit usage, latency, cache hit rate and failure rate accompany
the visual comparison.

## Rollback

PixelLab remains opt-in. Disabling it returns WorldSnapshot and WorldPreview to
their existing deterministic outputs. Generated candidates never overwrite
inputs and are safe to delete after their manifests and evaluation evidence are
retained according to the eventual #54 runbook.
