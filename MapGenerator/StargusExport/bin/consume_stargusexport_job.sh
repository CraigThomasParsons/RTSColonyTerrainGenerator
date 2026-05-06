#!/bin/bash
set -euo pipefail
shopt -s nullglob

MODULE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/StargusExport"
INPUT_SOURCE="${PLAYABLE_OUTPUT_DIR:-$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Playable/outbox}"
OUTPUT_DIR="$MODULE_ROOT/outbox"
EXPORTS_DIR="$MODULE_ROOT/exports"
STARGUS_MAPS_DIR="${STARGUS_MAPS_DIR:-}"
STARGUS_MAPS_SUBDIR="${STARGUS_MAPS_SUBDIR:-MapGeneratorOutput}"
STARGUS_STARTOOL="${STARGUS_STARTOOL:-$HOME/Code/stargus/build/startool}"
STARGUS_TEMPLATE_SCM="${STARGUS_TEMPLATE_SCM:-}"
MIN_SCM_BYTES="${MIN_SCM_BYTES:-10240}"

mkdir -p "$OUTPUT_DIR" "$EXPORTS_DIR"

LOG_FILE=""

log_line() {
    if [ -n "$LOG_FILE" ]; then
        echo "$1" | tee -a "$LOG_FILE"
    else
        echo "$1"
    fi
}

resolve_stargus_maps_dir() {
    if [ -n "$STARGUS_MAPS_DIR" ]; then
        local target="$STARGUS_MAPS_DIR/$STARGUS_MAPS_SUBDIR"
        mkdir -p "$target"
        echo "$target"
        return
    fi

    local base_dirs=(
        "$HOME/.local/share/stratagus/data.Stargus"
        "$HOME/.stratagus/sc"
        "$HOME/.stratagus/stargus"
        "$HOME/.local/share/stratagus/sc"
        "$HOME/.local/share/stratagus/stargus"
    )

    for base in "${base_dirs[@]}"; do
        if [ -d "$base" ]; then
            local target="$base/maps/$STARGUS_MAPS_SUBDIR"
            mkdir -p "$target"
            echo "$target"
            return
        fi
    done

    echo ""
}

latest_from_dir() {
    local source_dir="$1"
    local files=("$source_dir"/*.worldpayload)
    if [ ${#files[@]} -eq 0 ]; then
        echo ""
        return
    fi
    ls -t "${files[@]}" | head -n1
}

LATEST_JOB=$(latest_from_dir "$INPUT_SOURCE")

if [ -z "$LATEST_JOB" ]; then
    FALLBACK_SOURCE="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TreePlanter/outbox"
    LATEST_JOB=$(latest_from_dir "$FALLBACK_SOURCE")
fi

if [ -z "$LATEST_JOB" ]; then
    echo "No worldpayload found in $INPUT_SOURCE"
    exit 0
fi

JOB_ID=$(basename "$LATEST_JOB" .worldpayload)
LOG_FILE="$OUTPUT_DIR/${JOB_ID}.stargus-export.log"

log_line "Processing $LATEST_JOB..."
EXPORT_ARGS=(--job-file "$LATEST_JOB" --output-dir "$OUTPUT_DIR")
if [ -n "$STARGUS_TEMPLATE_SCM" ]; then
    EXPORT_ARGS+=(--template-scm "$STARGUS_TEMPLATE_SCM")
fi
"$MODULE_ROOT/stargus-exporter" "${EXPORT_ARGS[@]}"

log_line "Done: $OUTPUT_DIR/${JOB_ID}.chk"

SCM_PATH="$OUTPUT_DIR/${JOB_ID}.scm"
if [ ! -f "$SCM_PATH" ]; then
    log_line "[StargusExport] Missing SCM output: $SCM_PATH"
    exit 1
fi

SCM_SIZE=$(stat -c '%s' "$SCM_PATH" 2>/dev/null || echo 0)
if [ "$SCM_SIZE" -lt "$MIN_SCM_BYTES" ]; then
    log_line "[StargusExport] SCM too small ($SCM_SIZE bytes). Expected at least $MIN_SCM_BYTES bytes."
    exit 1
fi

SCM_SIG=$(dd if="$SCM_PATH" bs=4 count=1 2>/dev/null | od -An -t x1 | tr -d ' \n')
if [ "$SCM_SIG" != "4d50511a" ]; then
    log_line "[StargusExport] SCM header is not MPQ\\x1a (got $SCM_SIG)."
    exit 1
fi

LAST_MAP_NAME="last_map_${JOB_ID}.scm"
cp -f "$SCM_PATH" "$EXPORTS_DIR/${JOB_ID}.scm"
cp -f "$SCM_PATH" "$EXPORTS_DIR/$LAST_MAP_NAME"
log_line "Exported: $SCM_PATH ($SCM_SIZE bytes, MPQ header OK)"
log_line "Staged: $EXPORTS_DIR/${JOB_ID}.scm"
log_line "Staged: $EXPORTS_DIR/$LAST_MAP_NAME"

MAPS_DIR=$(resolve_stargus_maps_dir)
if [ -n "$MAPS_DIR" ] && [ -f "$SCM_PATH" ]; then
    if [ -x "$STARGUS_STARTOOL" ]; then
        CHK_PATH="$OUTPUT_DIR/${JOB_ID}.chk"
        (cd "$HOME/Code/stargus" && STARGUS_CONVERT_CHK="$CHK_PATH" STARGUS_CONVERT_OUT="$MAPS_DIR" "$STARGUS_STARTOOL")
        if [ -f "$MAPS_DIR/${JOB_ID}.smp" ]; then
            log_line "Converted: $SCM_PATH -> $MAPS_DIR/${JOB_ID}.smp/.sms"
        else
            log_line "Conversion did not produce $MAPS_DIR/${JOB_ID}.smp"
        fi
    else
        log_line "startool not found at $STARGUS_STARTOOL; skipping SCM->SMP conversion."
    fi
else
    log_line "Skipping Stargus map copy. Set STARGUS_MAPS_DIR or create ~/.stratagus/sc to enable."
fi
