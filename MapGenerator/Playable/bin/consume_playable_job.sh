#!/usr/bin/env bash
# Playable stage consumer
# Processes one payload per invocation; triggered by systemd .path.
set -euo pipefail

PLAYABLE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Playable"

INPUT_DIR="${PLAYABLE_INPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures/outbox}"
OUTPUT_DIR="${PLAYABLE_OUTPUT_DIR:-$PLAYABLE_ROOT/outbox}"
LOG_DIR="${PLAYABLE_LOG_DIR:-$HOME/Code/RTSColonyTerrainGenerator/logs/jobs}"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

PYTHON_BIN="$HOME/Code/RTSColonyTerrainGenerator/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" "$PLAYABLE_ROOT/bin/playable.py" \
  --input "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --log-dir "$LOG_DIR"
