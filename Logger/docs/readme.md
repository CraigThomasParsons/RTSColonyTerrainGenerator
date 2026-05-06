# MapGenerator LogStreamer

## What this does
- Watches stage log directories (Heightmap, Tiler, Weather, TreePlanter, World, and logs/jobs/*).
- Streams new lines via `tail -n0 -F`, normalizes them as JSON objects, and appends to a single canonical log: logs/mapgen.log.
- Uses a FIFO and single writer to prevent interleaved writes; minimal state (offset only), restart-safe, append-only.
- If an input line is JSON, it is normalized; otherwise it is wrapped as a `raw_log` event with safe defaults.

## Input → Output normalization (JSONL)
- Input expectation: one JSON object per line (JSONL). Example input fields include `ts`, `stage`, `job_id`, `level`, `event`, `msg`, `kv`.
- Output (one JSON object per line) written to logs/mapgen.log:
  - `ts`: ISO-8601 UTC. Numeric millis are converted; strings are passed through; missing → now.
  - `stage`: from JSON `stage`, else inferred from path, else `unknown`.
  - `job`: from JSON `job` or `job_id`, else inferred from path, else `unknown`.
  - `level`: uppercased string; default `INFO`.
  - `event`: from JSON `event`, default `unknown`.
  - `msg`: from JSON `msg`, default empty.
  - `kv`: from JSON `kv`, default `{}`.
- Invalid JSON lines are wrapped:
  ```json
  {"ts": "<now>", "stage": "<inferred>", "job": "<inferred>", "level": "INFO", "event": "raw_log", "msg": "<original line>", "kv": {}}
  ```

## Architecture highlights
- Polling discovery over explicit globs; no config files, no inotify.
- Per-file watchers: `tail -n0 -F --retry` to avoid duplication on restart and survive rotations.
- Single writer: a FIFO feeds one `cat >> logs/mapgen.log` to avoid interleaving across watchers.
- Path-only inference for stage/job; no content-based stage detection.

## Files
- Script: [Logger/logstreamer.sh](Logger/logstreamer.sh)
- Systemd unit: [Logger/systemd/logstreamer.service](Logger/systemd/logstreamer.service)
- Installer: [Logger/systemd/install.sh](Logger/systemd/install.sh)

## Requirements
- bash (with `pipefail`), coreutils (tail, mkfifo), systemd user session, `jq` available in PATH.
- Writable logs directory at logs/ under the repo root.

## Setup (user session)
1) Make scripts executable (one-time):
```sh
chmod +x Logger/logstreamer.sh Logger/systemd/install.sh
```
2) Install + start via systemd user:
```sh
Logger/systemd/install.sh
```
3) Verify:
```sh
systemctl --user status logstreamer.service
journalctl --user -u logstreamer.service -n 50
```

## Runtime
- Output file: logs/mapgen.log (append-only, single writer).
- Restart-safe: tail resumes from end; no backfill duplication.
- To restart manually:
```sh
systemctl --user restart logstreamer.service
```

## Removal
```sh
systemctl --user disable --now logstreamer.service
rm -f ~/.config/systemd/user/logstreamer.service
systemctl --user daemon-reload
```
