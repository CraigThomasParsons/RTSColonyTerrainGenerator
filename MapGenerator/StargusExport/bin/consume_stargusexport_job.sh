#!/bin/bash
set -euo pipefail

MODULE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/StargusExport"
INPUT_SOURCE="${PLAYABLE_OUTPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Playable/outbox}"
OUTPUT_DIR="$MODULE_ROOT/outbox"

LATEST_JOB=$(ls -t "$INPUT_SOURCE"/*.worldpayload 2>/dev/null | head -n1)

if [ -z "$LATEST_JOB" ]; then
    FALLBACK_SOURCE="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TreePlanter/outbox"
    LATEST_JOB=$(ls -t "$FALLBACK_SOURCE"/*.worldpayload 2>/dev/null | head -n1)
fi

if [ -z "$LATEST_JOB" ]; then
    echo "No worldpayload found in $INPUT_SOURCE"
    exit 0
fi

JOB_ID=$(basename "$LATEST_JOB" .worldpayload)

echo "Processing $LATEST_JOB..."
"$MODULE_ROOT/stargus-exporter" \
    --job-file "$LATEST_JOB" \
    --output-dir "$OUTPUT_DIR"

echo "Done: $OUTPUT_DIR/${JOB_ID}.chk"
