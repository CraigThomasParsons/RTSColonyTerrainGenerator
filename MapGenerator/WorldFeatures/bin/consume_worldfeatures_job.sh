#!/usr/bin/env bash
#
# WorldFeatures queue consumer
#
# This script processes ONE payload per invocation.
# It is designed to be triggered by a systemd .path unit.
#

set -euo pipefail

WORLD_FEATURES_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures"

INPUT_DIR="${WORLD_FEATURES_INPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TreePlanter/outbox}"
OUTPUT_DIR="${WORLD_FEATURES_OUTPUT_DIR:-$WORLD_FEATURES_ROOT/outbox}"
LOG_DIR="${WORLD_FEATURES_LOG_DIR:-$HOME/Code/RTSColonyTerrainGenerator/logs/jobs}"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

GRADLE_COMMAND="$WORLD_FEATURES_ROOT/gradlew"
if [[ -x "$GRADLE_COMMAND" ]]; then
    GRADLE_RUN="$GRADLE_COMMAND"
else
    GRADLE_RUN="gradle"
fi

cd "$WORLD_FEATURES_ROOT"

"$GRADLE_RUN" -q run --args="--input $INPUT_DIR --output $OUTPUT_DIR --log-dir $LOG_DIR"
