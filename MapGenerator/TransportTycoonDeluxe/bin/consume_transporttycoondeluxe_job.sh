#!/usr/bin/env bash
#
# TransportTycoonDeluxe queue consumer (scaffold)
#
# This script processes ONE payload per invocation.
# It is designed to be triggered by a systemd .path unit.
#

set -euo pipefail

STAGE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TransportTycoonDeluxe"

INPUT_DIR="${TRANSPORT_TYCOON_DELUXE_INPUT_DIR:-$STAGE_ROOT/inbox}"
OUTPUT_DIR="${TRANSPORT_TYCOON_DELUXE_OUTPUT_DIR:-$STAGE_ROOT/outbox}"
ARCHIVE_DIR="${TRANSPORT_TYCOON_DELUXE_ARCHIVE_DIR:-$STAGE_ROOT/archive}"
FAILED_DIR="${TRANSPORT_TYCOON_DELUXE_FAILED_DIR:-$STAGE_ROOT/failed}"
LOG_DIR="${TRANSPORT_TYCOON_DELUXE_LOG_DIR:-$HOME/Code/RTSColonyTerrainGenerator/logs/jobs}"

mkdir -p "$OUTPUT_DIR" "$ARCHIVE_DIR" "$FAILED_DIR" "$LOG_DIR"

CURRENT_JOB=""

on_error() {
  if [[ -n "$CURRENT_JOB" && -f "$CURRENT_JOB" ]]; then
    mv "$CURRENT_JOB" "$FAILED_DIR/" || true
  fi
}

trap on_error ERR

LATEST_JOB=$(ls -t "$INPUT_DIR"/* 2>/dev/null | head -n1 || true)
if [[ -z "$LATEST_JOB" ]]; then
  echo "[TransportTycoonDeluxe] No jobs in $INPUT_DIR"
  exit 0
fi

CURRENT_JOB="$LATEST_JOB"
JOB_FILE=$(basename "$LATEST_JOB")
JOB_ID="${JOB_FILE%.*}"

OUTPUT_FILE="$OUTPUT_DIR/$JOB_ID.transporttycoondeluxe"
LOG_FILE="$LOG_DIR/$JOB_ID.transporttycoondeluxe.log"

{
  echo "{"
  echo "  \"job_id\": \"$JOB_ID\","
  echo "  \"stage\": \"TransportTycoonDeluxe\","
  echo "  \"status\": \"scaffold\","
  echo "  \"input\": \"$JOB_FILE\","
  echo "  \"generated_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\""
  echo "}"
} > "$OUTPUT_FILE"

echo "[TransportTycoonDeluxe] Wrote placeholder output: $OUTPUT_FILE" | tee -a "$LOG_FILE"

mv "$LATEST_JOB" "$ARCHIVE_DIR/"
