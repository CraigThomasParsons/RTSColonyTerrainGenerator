#!/usr/bin/env bash
#
# PathFinder queue consumer
#
# This script processes ONE payload per invocation.
# It is designed to be triggered by a systemd .path unit.
#

set -euo pipefail

PATHFINDER_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/PathFinder"

INPUT_DIR="${PATHFINDER_INPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures/outbox}"
OUTPUT_DIR="${PATHFINDER_OUTPUT_DIR:-$PATHFINDER_ROOT/outbox}"
LOG_DIR="${PATHFINDER_LOG_DIR:-$HOME/Code/RTSColonyTerrainGenerator/logs/jobs}"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

GRADLE_COMMAND="$PATHFINDER_ROOT/gradlew"
if [[ -x "$GRADLE_COMMAND" ]]; then
    GRADLE_RUN="$GRADLE_COMMAND"
else
    GRADLE_RUN="gradle"
fi

cd "$PATHFINDER_ROOT"

"$GRADLE_RUN" -q run --args="--input $INPUT_DIR --output $OUTPUT_DIR --log-dir $LOG_DIR"
