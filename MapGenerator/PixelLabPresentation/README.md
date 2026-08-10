# PixelLabPresentation

PixelLabPresentation is an optional, non-authoritative presentation lane. It
turns a JSON `.worldpayload` into deterministic control artifacts that a later
stage may submit to PixelLab. Generated pixels never change map geometry,
traversability, starts, resources, or export data.

## Slices

| Issue | Scope |
| --- | --- |
| #50 | Deterministic VisualBrief, semantic/protected/decoration masks, generation-manifest template |
| #51 | Opt-in PixelLab v2 async adapter, content-addressed cache, candidate provenance |
| #52 | Deterministic run plans, bounded candidate batches, structural validation, explicit human approval |
| #53–#54 | WorldPreview composition, evaluation gallery and go/no-go (not this package yet) |

## Issue #50: control artifacts

For an input job `<id>.worldpayload`, `visual_contract.py` writes:

- `visual-brief.json`: versioned visual intent and source summary;
- `semantic-control.png`: one pixel per authoritative map cell;
- `protected-mask.png`: white where visual geometry must be retained;
- `decoration-mask.png`: white where decorative invention is permitted;
- `generation-manifest.template.json`: immutable generation inputs with the
  remote-job fields left unsubmitted.

All JSON is canonical and all PNGs are generated with the Python standard
library. Repeated runs over the same input produce identical bytes.

```bash
python3 MapGenerator/PixelLabPresentation/bin/visual_contract.py \
  --input MapGenerator/Playable/outbox/<id>.worldpayload \
  --output MapGenerator/PixelLabPresentation/outbox/<id>
```

Dimension declarations must agree with the addressed tile grid. The temporary
`--dimensions-from-tiles` option exists only to inspect legacy artifacts while
issue #55 is resolved. Artifacts created with that option carry a warning and
must not be submitted to PixelLab or approved for production use.

## Issue #51: PixelLab v2 adapter

`pixellab_client.py` is the only component allowed to talk to PixelLab. It
defaults to an offline dry run. Live calls require explicit opt-in flags and a
token supplied outside git. **This phase (#51) made zero live PixelLab requests
and spent zero credits.** All automated tests inject a mock transport.

### Environment setup

1. Create a PixelLab account and API token on the PixelLab account page.
2. Export the token only in the shell that will run a live mode:

   ```bash
   export PIXELLAB_API_TOKEN='…'   # never commit, never pass as a CLI flag
   ```

3. Do not put the token in argv, manifests, logs, test fixtures, or process
   listings you intend to share. The adapter redacts `Bearer …` text and the
   configured token value from stderr and error messages, but the safest
   practice is never to echo the variable.

### Modes

| Mode | Network | Spends credits | Flags required |
| --- | --- | --- | --- |
| `dry-run` (default) | none | no | `--controls` `--output` `--cache` |
| `balance` | `GET /balance` only | no | `--enable-live-calls` + token |
| `submit` | one generation POST + polls | maybe one job | `--enable-live-calls` `--confirm-credit-spend` + token |
| `poll` | job status GETs only | no | `--enable-live-calls` + token + prior manifest |

Allowlisted generation endpoint (matches the issue #50 manifest `const`):

- `POST /create-image-pixflux-background`

Read-only companion endpoints:

- `GET /balance`
- `GET /background-jobs/{job_id}`

Base URL: `https://api.pixellab.ai/v2`.

### Dry run (always do this first)

```bash
python3 MapGenerator/PixelLabPresentation/bin/pixellab_client.py \
  --mode dry-run \
  --controls MapGenerator/PixelLabPresentation/outbox/<id> \
  --output MapGenerator/PixelLabPresentation/candidates/<id>/c0 \
  --cache MapGenerator/PixelLabPresentation/cache \
  --seed 1 \
  --candidate-index 0
```

Dry-run writes `generation-manifest.json` into `--output` with the exact request
body summary (init images reduced to hashes), a content-addressed
`requestCacheKey`, and a warning that no PixelLab request was made. It never
reads `PIXELLAB_API_TOKEN` and never opens a socket.

Issue #50 source files stay read-only. The adapter refuses to use the same path
for `--controls` and `--output`.

### Balance / readiness

```bash
export PIXELLAB_API_TOKEN='…'
python3 MapGenerator/PixelLabPresentation/bin/pixellab_client.py \
  --mode balance \
  --enable-live-calls
```

Use this before a live submit to confirm credits and subscription generations
remain available. Balance never creates a generation.

### Live submit (explicit opt-in)

```bash
export PIXELLAB_API_TOKEN='…'
python3 MapGenerator/PixelLabPresentation/bin/pixellab_client.py \
  --mode submit \
  --controls MapGenerator/PixelLabPresentation/outbox/<id> \
  --output MapGenerator/PixelLabPresentation/candidates/<id>/c0 \
  --cache MapGenerator/PixelLabPresentation/cache \
  --seed 1 \
  --candidate-index 0 \
  --enable-live-calls \
  --confirm-credit-spend
```

Behaviour:

1. Rebuild the request from control artifacts and re-verify input hashes.
2. Look up the content-addressed cache. **A cache hit makes no generation
   request** and copies the cached PNG into the candidate directory.
3. On a miss, POST exactly once to the allowlisted endpoint (HTTP 202 +
   `background_job_id`).
4. Poll `GET /background-jobs/{job_id}` within `--max-poll-attempts` and
   `--max-poll-seconds` (default 60 attempts / 900 seconds, 5 s interval).
5. Validate returned image type/format/MIME/dimensions against the request.
6. Atomically write `candidate.png`, update `generation-manifest.json`, and
   store the PNG under `--cache/<requestCacheKey>/`.

Generation is **never** resubmitted automatically. Poll retries are free and
allowed; paying for a second image always requires a new explicit `submit`.

### Resume after timeout or rate limit

```bash
export PIXELLAB_API_TOKEN='…'
python3 MapGenerator/PixelLabPresentation/bin/pixellab_client.py \
  --mode poll \
  --controls MapGenerator/PixelLabPresentation/outbox/<id> \
  --output MapGenerator/PixelLabPresentation/candidates/<id>/c0 \
  --cache MapGenerator/PixelLabPresentation/cache \
  --enable-live-calls
```

Poll reuses `remote.jobId` from the candidate manifest. It never POSTs a new
generation.

### Cache behaviour

- Cache key material: contract version, endpoint, verified control input hashes,
  and the exact request body (including base64 init image when present).
- Lookup happens before any live transport is constructed.
- Cache hits set `remote.cacheHit=true` and leave `remote.jobId` unset.

### Failure recovery

| Condition | Adapter behaviour | Operator action |
| --- | --- | --- |
| Missing token / missing opt-in | exit 3, no network | export token; pass required flags |
| HTTP 401 | actionable error, no retry | refresh `PIXELLAB_API_TOKEN` |
| HTTP 402 | actionable error, no retry | top up credits; re-check with `balance` |
| HTTP 422 | actionable error, no retry | regenerate controls; dry-run again |
| HTTP 423 / 429 / 529 on poll | retry within poll bounds | wait; re-run `poll` if bounds expire |
| Poll timeout | manifest stays `processing` with `jobId` | re-run `poll` (no second charge) |
| Terminal remote `failed` | manifest `failed` | inspect balance; new `submit` only if desired |
| Unexpected MIME / dimensions | reject image, do not promote | treat as remote contract break |
| Map edge outside 16–400 | fail closed offline (Gitea #60) | resize product scope or track #60 |

### Image size limit

PixelLab pixflux `image_size` edges must be integers in **16–400**. This lane
uses one pixel per map cell, so maps outside that range cannot be submitted by
the allowlisted endpoint. Tracking decision work lives in Gitea issue #60.

### Tests for this phase

```bash
python3 -m unittest \
  MapGenerator/PixelLabPresentation/tests/test_visual_contract.py \
  MapGenerator/PixelLabPresentation/tests/test_pixellab_client.py
```

`test_pixellab_client.py` covers dry-run/no-token, missing token for live mode,
token redaction, cache hit/no request, accepted async flow, poll timeout, and
representative HTTP failures. Every test injects a mock transport; none of them
contact `api.pixellab.ai`.

## Issue #52: candidate orchestration

`candidate_orchestrator.py` is the operator entry point. It turns one strict
`.worldpayload` into the issue #50 controls plus a small, explicitly bounded
batch of issue #51 candidates, validates what came back, and lets a human — and
only a human — approve or reject it. **This phase (#52) made zero live PixelLab
requests, zero balance requests, and spent zero credits.** It never reads
`PIXELLAB_API_TOKEN`; only `pixellab_client.py` does, and only during an
explicitly authorized live run.

The orchestration layer adds no contract, token, transport, cache, or polling
logic of its own. It composes the existing modules:

| Module | Responsibility |
| --- | --- |
| `candidate_plan.py` | Deterministic run plan: candidate indices, seeds, directories, budget |
| `candidate_state.py` | The candidate lifecycle and which transitions automation may perform |
| `candidate_validation.py` | Offline structural checks and protected-landmark evidence |
| `candidate_approval.py` | Explicit operator decisions with actor, time, reason, and evidence |
| `candidate_orchestrator.py` | The CLI that composes the above with `visual_contract` and `pixellab_client` |
| `pixellab_modules.py` | Loads the `bin/` scripts as importable modules |

### Run directory layout

```text
<run-root>/
  run-plan.json                     deterministic plan, self-verifying via planId
  controls/                         issue #50 artifacts (read-only after planning)
    visual-brief.json
    semantic-control.png
    protected-mask.png
    decoration-mask.png
    generation-manifest.template.json
  candidates/
    candidate-000/
      generation-manifest.json      issue #51 provenance
      candidate.png                 only after a live run or a cache hit
      validation.json               deterministic structural report
      approval.json                 only after an explicit operator decision
    candidate-001/
      ...
```

### Candidate states

| State | Meaning |
| --- | --- |
| `planned` | In the run plan; nothing written yet |
| `dry-run` | Request built entirely offline; no socket, no credit |
| `processing` | Submitted and accepted remotely, not yet collected |
| `generated` | Image present and passing every automated structural check |
| `rejected` | Automated validation failed, or an operator rejected it |
| `human-approved` | An operator explicitly approved it, on the record |

Automated validation may move a candidate to `rejected`. **It can never produce
`human-approved`** — `candidate_state.require_transition` refuses that
transition for an automation actor, so the restriction is structural rather than
a convention someone has to remember.

### Offline operator workflow (always do this first)

1. **Plan.** Decide the batch before anything is written.

   ```bash
   python3 MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py plan \
     --input MapGenerator/Playable/outbox/<id>.worldpayload \
     --output MapGenerator/PixelLabPresentation/runs/<id> \
     --cache MapGenerator/PixelLabPresentation/cache \
     --seed 11 --candidates 3 --candidate-budget 3
   ```

   This writes `controls/` and `run-plan.json` and prints the plan identifier,
   candidate count, and budget. It makes no network request.

2. **Run offline.** The default mode; identical to `plan` plus one dry-run
   candidate manifest and validation report per candidate.

   ```bash
   python3 MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py run \
     --input MapGenerator/Playable/outbox/<id>.worldpayload \
     --output MapGenerator/PixelLabPresentation/runs/<id> \
     --cache MapGenerator/PixelLabPresentation/cache \
     --seed 11 --candidates 3 --candidate-budget 3
   ```

   The summary reports `"networkTransportAttempts": 0`. That number is the run's
   own evidence: offline mode installs a transport factory that counts and
   refuses every attempt, so a non-zero value would have failed the run.

   Re-running an identical offline plan is byte-stable. Nothing an offline run
   writes contains a clock reading, an absolute path, or environment data.

3. **Review.** Re-validate and read every candidate's current state.

   ```bash
   python3 MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py validate \
     --output MapGenerator/PixelLabPresentation/runs/<id>
   ```

4. **Decide.** Approval and rejection are separate, explicit, attributed acts.

   ```bash
   python3 MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py approve \
     --output MapGenerator/PixelLabPresentation/runs/<id> \
     --candidate 0 --actor "<your name>" --reason "<what you checked>"

   python3 MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py reject \
     --output MapGenerator/PixelLabPresentation/runs/<id> \
     --candidate 1 --actor "<your name>" --reason "<what was wrong>"
   ```

   Both re-run validation first, so a candidate edited since generation cannot
   be approved. Decisions are appended, never replaced: superseding an earlier
   decision keeps it in the record with its own reason and timestamp.

### Live workflow (separately gated, not exercised in this phase)

A live run needs four things at once, and each is deliberately separate:
`--mode live`, `--enable-live-calls`, `--confirm-credit-spend`, and a
`PIXELLAB_API_TOKEN` exported in that shell. Run the issue #51 `balance` mode
first to confirm credits.

```bash
export PIXELLAB_API_TOKEN='…'   # never commit, never pass as a CLI flag
python3 MapGenerator/PixelLabPresentation/bin/pixellab_client.py --mode balance --enable-live-calls

python3 MapGenerator/PixelLabPresentation/bin/candidate_orchestrator.py run \
  --input MapGenerator/Playable/outbox/<id>.worldpayload \
  --output MapGenerator/PixelLabPresentation/runs/<id> \
  --cache MapGenerator/PixelLabPresentation/cache \
  --seed 11 --candidates 3 --candidate-budget 3 \
  --mode live --enable-live-calls --confirm-credit-spend
```

Budget rules, all enforced *before* the first submission:

- The budget is a hard ceiling of at most
  `candidate_plan.MAXIMUM_CANDIDATE_BUDGET` and may never exceed the candidate
  count, because one candidate is at most one submission.
- Cache state for every candidate is computed offline first. If the number of
  cache misses exceeds the budget, the run fails with exit code 7 and submits
  nothing at all — not even the first candidate.
- **Cache hits do not consume the budget.** Replaying a fully cached batch is
  runnable with `--candidate-budget 0`.
- Generation is never resubmitted automatically. A second image always requires
  a new explicit invocation.

### Fail-closed rules

| Condition | Behaviour |
| --- | --- |
| Declared/tile dimension mismatch (Gitea #55) | Run fails; no controls, no candidates |
| `--allow-exploration-dimensions` (Gitea #55) | Controls only. **No candidate is planned**, so none can be submitted or approved |
| Map edge outside 16–400 (Gitea #60) | Run fails before any candidate directory is created |
| Candidate image hash, MIME, or dimensions wrong | Candidate is `rejected`; approval refused |
| Control artifact edited after planning | Validation refuses outright |
| Run plan edited after generation | `planId` re-derivation refuses to load it |

### What validation does and does not claim

Validation checks contract and plan versions, immutable control-input hashes,
the candidate manifest's inputs and endpoint, candidate index and seed against
the plan, cache-key and request-body reproducibility, the PixelLab image-size
bound, mask dimension agreement, and the candidate PNG's signature, recorded
MIME, hash, and header dimensions.

Protected-landmark alignment evidence is derived **from `protected-mask.png`
only** — its cell count, its coordinate digest, and the fact that the candidate
raster shares the mask's grid exactly, so every protected cell is addressable
one-to-one. Validation never reads a single generated pixel. It cannot and does
not claim that the artwork drew a road in the right place; that judgement is a
human's, recorded through `approve`/`reject`.

### Rollback and deletion safety

- The lane is opt-in. Deleting a whole run directory returns the pipeline to its
  existing deterministic output; nothing downstream depends on a candidate.
- Candidates never overwrite authoritative inputs. The orchestrator writes only
  under its run root and the cache root, and the issue #51 adapter refuses to
  use the controls directory as an output directory.
- `controls/` is written once during planning and is read-only afterwards. Any
  later edit is caught by hash re-verification rather than silently accepted.
- Deleting `cache/` is safe: it only forces a future live run to pay again.
  Deleting a candidate directory is safe once its manifest, validation report,
  and approval record have been retained per the eventual #54 runbook.
- A rejected candidate can never become the active preview. Issue #53 must
  consume `approval.json` with `currentState` equal to `human-approved`, and
  nothing else.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 2 | Contract, plan, validation, or approval refusal |
| 3 | Live mode not fully authorized |
| 6 | `validate` found at least one structurally invalid candidate |
| 7 | Run would exceed the explicit candidate budget |

### Tests for this phase

```bash
python3 -m unittest \
  MapGenerator/PixelLabPresentation/tests/test_visual_contract.py \
  MapGenerator/PixelLabPresentation/tests/test_pixellab_client.py \
  MapGenerator/PixelLabPresentation/tests/test_candidate_plan.py \
  MapGenerator/PixelLabPresentation/tests/test_candidate_validation.py \
  MapGenerator/PixelLabPresentation/tests/test_candidate_approval.py \
  MapGenerator/PixelLabPresentation/tests/test_candidate_orchestrator.py
```

The issue #52 tests cover deterministic and byte-stable plans, zero-network
offline runs across three representative maps, bounded candidate counts and
budgets, cache reuse with a zero budget, validation rejection, the #55 and #60
fail-closed paths, and explicit human approval and rejection transitions. Every
client boundary is injected: offline runs use a refusing transport factory and
live-mode tests use a fake submission boundary, so no test can reach
`api.pixellab.ai`.

## Safety boundary

PixelLab outputs are presentation assets. Downstream consumers must render
gameplay and debug overlays from authoritative map data, never infer gameplay
state from an AI-generated image. See
[`docs/adr/0001-pixellab-presentation-only.md`](../../docs/adr/0001-pixellab-presentation-only.md).
