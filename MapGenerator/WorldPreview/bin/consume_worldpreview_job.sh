#!/bin/bash
set -euo pipefail

# Wrapper to find the latest job and invoke the engine
# This follows the pattern of other modules

MODULE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WorldPreview"
INPUT_SOURCE="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/PathFinder/outbox"
OUTPUT_DIR="$MODULE_ROOT/outbox"

# Find latest JSON in PathFinder outbox
LATEST_JOB=$(ls -t "$INPUT_SOURCE"/*.json 2>/dev/null | head -n1)

if [ -z "$LATEST_JOB" ]; then
    echo "No job found in $INPUT_SOURCE"
    exit 0
fi

JOB_ID=$(basename "$LATEST_JOB" .json)
OUTPUT_TARGET="$OUTPUT_DIR/$JOB_ID"

# Check if already exists to avoid re-processing (optional, but good for idempotency)
# Actually, we might want to overwrite if updated.
# Let's run it.

echo "Processing $LATEST_JOB..."
"$MODULE_ROOT/worldpreview-engine" --job-file "$LATEST_JOB" --output-file "$OUTPUT_DIR"
