#!/usr/bin/env bash
#
# TransportTycoonDeluxe stage runner (v1)
#
# Consumes one <job_id>.heightmap.png per invocation and produces
# <job_id>.transporttycoon.json on success.
#

set -euo pipefail

STAGE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TransportTycoonDeluxe"

INPUT_DIR="${TRANSPORT_TYCOON_DELUXE_INPUT_DIR:-$STAGE_ROOT/inbox}"
OUTPUT_DIR="${TRANSPORT_TYCOON_DELUXE_OUTPUT_DIR:-$STAGE_ROOT/outbox}"
ARCHIVE_DIR="${TRANSPORT_TYCOON_DELUXE_ARCHIVE_DIR:-$STAGE_ROOT/archive}"
FAILED_DIR="${TRANSPORT_TYCOON_DELUXE_FAILED_DIR:-$STAGE_ROOT/failed}"
DEBUG_DIR="${TRANSPORT_TYCOON_DELUXE_DEBUG_DIR:-$STAGE_ROOT/debug}"
TEMP_DIR_BASE="${TRANSPORT_TYCOON_DELUXE_TEMP_DIR:-$STAGE_ROOT/debug}"

MAP_SIZE="${TRANSPORT_TYCOON_DELUXE_MAP_SIZE:-1024x1024}"
MAP_X_EXP="${TRANSPORT_TYCOON_DELUXE_MAP_X_EXP:-10}"
MAP_Y_EXP="${TRANSPORT_TYCOON_DELUXE_MAP_Y_EXP:-10}"
WATER_LEVEL="${TRANSPORT_TYCOON_DELUXE_WATER_LEVEL:-2}"
RUN_SECONDS="${TRANSPORT_TYCOON_DELUXE_RUN_SECONDS:-5}"

CONFIG_TEMPLATE="$STAGE_ROOT/openttd.cfg.template"

mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$ARCHIVE_DIR" "$FAILED_DIR" "$DEBUG_DIR" "$TEMP_DIR_BASE"

LATEST_JOB=$(find "$INPUT_DIR" -maxdepth 1 -type f -name '*.heightmap.png' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | awk '{print $2}')
if [ -z "${LATEST_JOB:-}" ]; then
  echo "[TransportTycoonDeluxe] No heightmap jobs in $INPUT_DIR"
  exit 0
fi

JOB_FILE=$(basename "$LATEST_JOB")
JOB_ID="${JOB_FILE%.heightmap.png}"
TIMESTAMP_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

DEBUG_LOG="$DEBUG_DIR/$JOB_ID.transporttycoon.log"

fail_job() {
  echo "[TransportTycoonDeluxe] FAILURE: $1" | tee -a "$DEBUG_LOG"
  if [ -f "$LATEST_JOB" ]; then
    mv "$LATEST_JOB" "$FAILED_DIR/" || true
  fi
  exit 1
}

if [ ! -f "$CONFIG_TEMPLATE" ]; then
  fail_job "Missing config template: $CONFIG_TEMPLATE"
fi

if ! command -v openttd >/dev/null 2>&1; then
  fail_job "OpenTTD not found in PATH"
fi

if ! command -v timeout >/dev/null 2>&1; then
  fail_job "timeout command not found; required for headless run"
fi

WORK_DIR="$(mktemp -d "$TEMP_DIR_BASE/$JOB_ID.XXXXXX")"
HEIGHTMAP_PATH="$WORK_DIR/$JOB_FILE"
CONFIG_PATH="$WORK_DIR/openttd.cfg"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

cp "$LATEST_JOB" "$HEIGHTMAP_PATH"

sed \
  -e "s/{{MAP_X}}/$MAP_X_EXP/g" \
  -e "s/{{MAP_Y}}/$MAP_Y_EXP/g" \
  -e "s/{{WATER_LEVEL}}/$WATER_LEVEL/g" \
  "$CONFIG_TEMPLATE" > "$CONFIG_PATH"

{
  echo "[TransportTycoonDeluxe] Starting OpenTTD headless run"
  echo "[TransportTycoonDeluxe] Job: $JOB_ID"
  echo "[TransportTycoonDeluxe] Heightmap: $HEIGHTMAP_PATH"
  echo "[TransportTycoonDeluxe] Seed: ${TRANSPORT_TYCOON_DELUXE_SEED:-auto}"
  echo "[TransportTycoonDeluxe] Map size: $MAP_SIZE"
  echo "[TransportTycoonDeluxe] Water level: $WATER_LEVEL"
} >> "$DEBUG_LOG"

if [ -n "${TRANSPORT_TYCOON_DELUXE_SEED:-}" ]; then
  SEED="$TRANSPORT_TYCOON_DELUXE_SEED"
else
  SEED="$(printf '%s' "$JOB_ID" | cksum | awk '{print $1}')"
fi

set +e
timeout "$RUN_SECONDS" \
  openttd \
  -v null \
  -s null \
  -m null \
  -g "$HEIGHTMAP_PATH" \
  -G "$SEED" \
  -c "$CONFIG_PATH" \
  -x \
  >> "$DEBUG_LOG" 2>&1
OPENTTD_STATUS=$?
set -e

if [ "$OPENTTD_STATUS" -ne 0 ] && [ "$OPENTTD_STATUS" -ne 124 ]; then
  fail_job "OpenTTD exited with status $OPENTTD_STATUS"
fi

OUTPUT_FILE="$OUTPUT_DIR/$JOB_ID.transporttycoon.json"

{
  echo "{"
  echo "  \"job_id\": \"$JOB_ID\","
  echo "  \"status\": \"world_generated\","
  echo "  \"engine\": \"OpenTTD\","
  echo "  \"map_size\": \"$MAP_SIZE\","
  echo "  \"seed\": $SEED,"
  echo "  \"timestamp\": \"$TIMESTAMP_UTC\","
  echo "  \"notes\": \"Infrastructure extraction not implemented yet\""
  echo "}"
} > "$OUTPUT_FILE"

echo "[TransportTycoonDeluxe] Wrote output: $OUTPUT_FILE" | tee -a "$DEBUG_LOG"

mv "$LATEST_JOB" "$ARCHIVE_DIR/"
