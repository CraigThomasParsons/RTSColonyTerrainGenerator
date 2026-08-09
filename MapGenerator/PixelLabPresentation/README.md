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
| #52–#54 | Candidate orchestration, WorldPreview composition, evaluation (not this package yet) |

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

## Safety boundary

PixelLab outputs are presentation assets. Downstream consumers must render
gameplay and debug overlays from authoritative map data, never infer gameplay
state from an AI-generated image. See
[`docs/adr/0001-pixellab-presentation-only.md`](../../docs/adr/0001-pixellab-presentation-only.md).
