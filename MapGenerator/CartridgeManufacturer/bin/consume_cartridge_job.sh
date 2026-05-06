#!/usr/bin/env bash
set -euo pipefail

STAGE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/CartridgeManufacturer"
INPUT_DIR="${PLAYABLE_OUTPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Playable/outbox}"
OUTPUT_DIR="$STAGE_ROOT/outbox"
ARCHIVE_DIR="$STAGE_ROOT/archive"
FAILED_DIR="$STAGE_ROOT/failed"
LOG_DIR="$HOME/Code/RTSColonyTerrainGenerator/logs/jobs"

mkdir -p "$OUTPUT_DIR" "$ARCHIVE_DIR" "$FAILED_DIR" "$LOG_DIR"

LATEST_JOB=$(ls -t "$INPUT_DIR"/*.worldpayload 2>/dev/null | head -n1)

if [ -z "$LATEST_JOB" ]; then
    FALLBACK_DIR="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TreePlanter/outbox"
    LATEST_JOB=$(ls -t "$FALLBACK_DIR"/*.worldpayload 2>/dev/null | head -n1)
fi

if [ -z "$LATEST_JOB" ]; then
    echo "No worldpayload found in $INPUT_DIR"
    exit 0
fi

JOB_ID=$(basename "$LATEST_JOB" .worldpayload)
JOB_LOG_DIR="$LOG_DIR/$JOB_ID"
mkdir -p "$JOB_LOG_DIR"
LOG_FILE="$JOB_LOG_DIR/cartridge.log.jsonl"

log_json() {
    local level="$1"
    local message="$2"
    printf '{"ts":"%s","job":"%s","stage":"cartridge","level":"%s","msg":"%s"}\n' \
        "$(date -u +%FT%TZ)" "$JOB_ID" "$level" "$message" >> "$LOG_FILE"
}

if [[ ! -x "$STAGE_ROOT/wcar_pack" ]]; then
    log_json "info" "wcar_pack missing, running install.sh"
    "$STAGE_ROOT/install.sh"
fi

log_json "info" "packing WCAR"
if "$STAGE_ROOT/wcar_pack" --input "$LATEST_JOB" --output "$OUTPUT_DIR"; then
    log_json "info" "wcar_pack complete"
else
    log_json "error" "wcar_pack failed"
    mv "$LATEST_JOB" "$FAILED_DIR/"
    exit 1
fi

log_json "info" "exporting CHK/SCM"
WCAR_PATH="$OUTPUT_DIR/$JOB_ID.wcar"
CHK_PATH="$OUTPUT_DIR/$JOB_ID.chk"
SCM_PATH="$OUTPUT_DIR/$JOB_ID.scm"

if "$STAGE_ROOT/wcar_export_chk" --input "$WCAR_PATH" --output "$SCM_PATH" --tileset-map "$STAGE_ROOT/tileset_mappings/default_badlands.json"; then
    log_json "info" "wcar_export_chk complete"
    # Also emit raw CHK
    "$STAGE_ROOT/wcar_export_chk" --input "$WCAR_PATH" --output "$CHK_PATH" --tileset-map "$STAGE_ROOT/tileset_mappings/default_badlands.json"
else
    log_json "error" "wcar_export_chk failed"
    mv "$LATEST_JOB" "$FAILED_DIR/"
    exit 1
fi

log_json "info" "running stratagus harness"
HARNESS_OUT="$JOB_LOG_DIR/stratagus"
mkdir -p "$HARNESS_OUT"

if "$STAGE_ROOT/wcar_run_stratagus" --map "$SCM_PATH" --ticks 5000 --seed 0 --out-dir "$HARNESS_OUT" --harness-script "$STAGE_ROOT/docs/harness.lua"; then
    log_json "info" "stratagus harness pass"
else
    log_json "error" "stratagus harness failed"
fi

mv "$LATEST_JOB" "$ARCHIVE_DIR/"
log_json "info" "job archived"
