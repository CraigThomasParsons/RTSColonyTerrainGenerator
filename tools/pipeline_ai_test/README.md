# Pipeline AI Test Tool

A lightweight, AI-style (heuristic) tester that runs the MapGenerator pipeline and streams log health in real time.

## What it does
- Optionally starts a pipeline run via `mapgenctl`.
- Tails `logs/mapgen.log` live.
- Scores health using simple heuristics (errors, warnings, inactivity).
- Detects stage stalls by checking artifact presence and elapsed time.
- Surfaces likely fixes based on known error patterns.
- Shows a live view of stages and recent log lines.

## Usage
From the repo root:

```sh
python tools/pipeline_ai_test/pipeline_ai_test.py --width 64 --height 64 --duration 60
```

Playwright validation for WorldPreview (requires Playwright + system deps):

```sh
python tools/pipeline_ai_test/pipeline_ai_test.py --width 64 --height 64 --duration 60 --playwright-worldpreview
```

WorldSnapshot validation (waits for PNG output):

```sh
python tools/pipeline_ai_test/pipeline_ai_test.py --width 64 --height 64 --duration 60 --worldsnapshot
```

Follow-only mode (no job run):

```sh
python tools/pipeline_ai_test/pipeline_ai_test.py --follow-only --duration 60
```

## Heuristics
- -15 points per ERROR
- -5 points per WARN
- -20 points if no log lines appear for `--stale` seconds
- -3 points per detected issue (pattern or stall)

Why: These signals correlate strongly with pipeline stalls or crashes without needing custom rules per stage.

## Stage timeouts
Defaults (seconds):
- heightmap: 120
- tiler: 120
- weather: 120
- treeplanter: 180

Override with:

```sh
python tools/pipeline_ai_test/pipeline_ai_test.py --stage-timeout tiler=240 --stage-timeout treeplanter=300
```

Why: Some machines or debug builds legitimately take longer.

## Notes
- The tool expects `logs/mapgen.log` to exist.
- Uses the same log normalization already produced by the LogStreamer.
- Intended for local debugging and rapid iteration.
- Playwright install steps:
	- `pip install playwright`
	- `python -m playwright install`
	- Linux deps (if prompted): `sudo playwright install-deps`
