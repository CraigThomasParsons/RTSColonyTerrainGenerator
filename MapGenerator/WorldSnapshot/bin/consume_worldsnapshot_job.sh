#!/usr/bin/env bash
# WorldSnapshot queue consumer
# Processes one WorldPreview output per invocation; triggered by systemd .path.
set -euo pipefail

REPO_ROOT="$HOME/Code/RTSColonyTerrainGenerator"
MODULE_ROOT="$REPO_ROOT/MapGenerator/WorldSnapshot"

INPUT_DIR="${WORLD_SNAPSHOT_INPUT_DIR:-$REPO_ROOT/MapGenerator/WorldPreview/outbox}"
OUTPUT_DIR="${WORLD_SNAPSHOT_OUTPUT_DIR:-$MODULE_ROOT/outbox}"
LOG_DIR="${WORLD_SNAPSHOT_LOG_DIR:-$REPO_ROOT/logs/jobs}"
TIMEOUT_SECONDS="${WORLD_SNAPSHOT_TIMEOUT_SECONDS:-20}"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" "$MODULE_ROOT/bin/worldsnapshot.py" \
  --input "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --log-dir "$LOG_DIR" \
  --timeout "$TIMEOUT_SECONDS"
