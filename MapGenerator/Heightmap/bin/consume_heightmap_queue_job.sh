#!/usr/bin/env bash
#
# Heightmap queue consumer
#
# This script processes ONE heightmap job per invocation.
# It is designed to be triggered by a systemd .path unit.
#
# Responsibilities:
# - Find the oldest job JSON in the inbox
# - Atomically claim it
# - Invoke the heightmap engine (placeholder for now)
# - Move job to archive or failed
#

set -euo pipefail

#######################################
# Configuration
#######################################

HEIGHTMAP_MODULE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap"


INBOX_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/inbox"
ARCHIVE_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/archive"
FAILED_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/failed"
OUTBOX_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/outbox"

HEIGHTMAP_ENGINE_BINARY="$HEIGHTMAP_MODULE_ROOT/bin/heightmap-engine"


echo "[heightmap-worker] Invoked at $(date -Is)"

#######################################
# Ensure required directories exist
#######################################

mkdir -p "$INBOX_DIRECTORY"
mkdir -p "$ARCHIVE_DIRECTORY"
mkdir -p "$FAILED_DIRECTORY"
mkdir -p "$OUTBOX_DIRECTORY"

#######################################
# Find the oldest job in the inbox
#######################################

JOB_FILE_PATH="$(ls -1t "$INBOX_DIRECTORY"/*.json 2>/dev/null | tail -n 1 || true)"

if [[ -z "$JOB_FILE_PATH" ]]; then
    echo "[heightmap-worker] No jobs found in inbox. Exiting."
    exit 0
fi

#######################################
# Atomically claim the job
#######################################

JOB_FILENAME="$(basename "$JOB_FILE_PATH")"
PROCESSING_FILE_PATH="$INBOX_DIRECTORY/.processing_$JOB_FILENAME"

mv "$JOB_FILE_PATH" "$PROCESSING_FILE_PATH"

echo "[heightmap-worker] Claimed job: $JOB_FILENAME"

#######################################
# Placeholder engine invocation
# (We will replace this with Rust shortly)
#######################################

JOB_BASENAME="${JOB_FILENAME%.json}"
OUTPUT_FILE_PATH="$OUTBOX_DIRECTORY/${JOB_BASENAME}.heightmap"

echo "[heightmap-worker] Generating placeholder output: $OUTPUT_FILE_PATH"

# Placeholder output so we can test the pipeline end-to-end
echo "PLACEHOLDER HEIGHTMAP OUTPUT for $JOB_FILENAME" > "$OUTPUT_FILE_PATH"

#######################################
# Archive the processed job
#######################################

mv "$PROCESSING_FILE_PATH" "$ARCHIVE_DIRECTORY/$JOB_FILENAME"

echo "[heightmap-worker] Job completed successfully: $JOB_FILENAME"
