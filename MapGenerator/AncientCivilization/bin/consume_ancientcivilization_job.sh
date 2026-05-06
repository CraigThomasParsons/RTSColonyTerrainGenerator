#!/usr/bin/env bash
# AncientCivilization queue consumer
# Processes ONE payload per invocation.
# Triggered by systemd .path unit.
set -euo pipefail

ANCIENT_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/AncientCivilization"

INPUT_DIR="${ANCIENT_INPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures/outbox}"
OUTPUT_DIR="${ANCIENT_OUTPUT_DIR:-$ANCIENT_ROOT/outbox}"
LOG_DIR="${ANCIENT_LOG_DIR:-$HOME/Code/RTSColonyTerrainGenerator/logs/jobs}"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

cd "$ANCIENT_ROOT"

# Ensure engine is present (built via install.sh)
ENGINE="$ANCIENT_ROOT/ancientcivilization-engine"
if [[ ! -x "$ENGINE" ]]; then
  echo "ancientcivilization-engine not found; building via install.sh..."
  ./install.sh
fi

"$ENGINE" --input "$INPUT_DIR" --output "$OUTPUT_DIR" --log-dir "$LOG_DIR"
