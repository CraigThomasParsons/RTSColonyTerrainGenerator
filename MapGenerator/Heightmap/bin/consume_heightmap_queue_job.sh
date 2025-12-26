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
set -x
set -euo pipefail


process_job() {
    #######################################
    # Configuration
    #######################################
    HEIGHTMAP_MODULE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Heightmap"

    #######################################
    # Load shared environment (if present)
    #######################################

    MAPGEN_ENV_FILE="$HOME/Code/RTSColonyTerrainGenerator/.env"

    if [[ -f "$MAPGEN_ENV_FILE" ]]; then
      # shellcheck disable=SC1090
      source "$MAPGEN_ENV_FILE"
    fi

    #######################################
    # Module paths
    #######################################
    INBOX_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/inbox"
    ARCHIVE_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/archive"
    FAILED_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/failed"
    OUTBOX_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/outbox"

    HEIGHTMAP_ENGINE_BINARY="$HEIGHTMAP_MODULE_ROOT/bin/heightmap-engine/heightmap-engine"


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

    # ignores .processing_*
    # picks the oldest job (FIFO)
    # avoids glob race conditions
    # works reliably under systemd
    JOB_FILE_PATH="$(
    find "$INBOX_DIRECTORY" \
        -maxdepth 1 \
        -type f \
        -name "*.json" \
        ! -name ".processing_*" \
        -printf "%T@ %p\n" \
    | sort -n \
    | head -n 1 \
    | cut -d' ' -f2-
    )"

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

    echo "[heightmap-worker] Generating heightmap: $OUTPUT_FILE_PATH"

    ls -la "$HEIGHTMAP_ENGINE_BINARY"
    "$HEIGHTMAP_ENGINE_BINARY" --version || true

    echo "[heightmap-worker] Running heightmap engine: $HEIGHTMAP_ENGINE_BINARY"


    # ------------------------------------------------------------
    # Debug output handling (human-only)
    # ------------------------------------------------------------

    ENGINE_DEBUG_ARGS=()

    if [[ "${MAPGEN_DEBUG:-0}" == "1" ]]; then
      mkdir -p "$MAPGEN_DEBUG_OUTPUT_DIR"

      if [[ "${MAPGEN_DEBUG_HEIGHTMAP_BMP:-0}" == "1" ]]; then
        ENGINE_DEBUG_ARGS+=(
          "--debug-height-bmp"
          "$MAPGEN_DEBUG_OUTPUT_DIR/${JOB_BASENAME}_height.bmp"
        )
      fi

      if [[ "${MAPGEN_DEBUG_LAYER_BMP:-0}" == "1" ]]; then
        ENGINE_DEBUG_ARGS+=(
          "--debug-layer-bmp"
          "$MAPGEN_DEBUG_OUTPUT_DIR/${JOB_BASENAME}_layers.bmp"
        )
      fi
    fi

    # Default fault iteration count if not set
    HEIGHTMAP_FAULT_ITERATIONS="${HEIGHTMAP_FAULT_ITERATIONS:-50}"



    "$HEIGHTMAP_ENGINE_BINARY" \
      --job-file "$PROCESSING_FILE_PATH" \
      --output-file "$OUTPUT_FILE_PATH" \
      --fault-iterations "$HEIGHTMAP_FAULT_ITERATIONS" \
      "${ENGINE_DEBUG_ARGS[@]}"
    
    echo "[heightmap-worker] Engine finished"

    #######################################
    # Archive the processed job
    #######################################

    mv "$PROCESSING_FILE_PATH" "$ARCHIVE_DIRECTORY/$JOB_FILENAME"

    echo "[heightmap-worker] Job completed successfully: $JOB_FILENAME"
}

if process_job; then
  exit 0
else
  echo "[heightmap-worker] Job failed"
  exit 1
fi

