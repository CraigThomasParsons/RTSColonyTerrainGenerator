#!/usr/bin/env bash
#
# tiler-test-runner.sh
#
# Systemd-safe single-file worker for the Tiler stage.
#
# Responsibilities:
# - Accept exactly ONE .heightmap file
# - Run the Tiler on that file
# - Emit exactly ONE .maptiles file
# - Move the input file to WeatherAnalyses/inbox on success
#
# This script contains NO terrain logic.
#
# I kept this version because it has much more comments and checks.
# but I usually follow what the A.I. tells me if everything is still stable.
#

set -euo pipefail

# ---- Resolve directories ----

TILER_DIR="$(cd "$(dirname "$0")" && pwd)"

INBOX_DIR="$TILER_DIR/inbox"
OUTBOX_DIR="$TILER_DIR/outbox"

# WeatherAnalyses handoff
WEATHER_INBOX_DIR="$TILER_DIR/../WeatherAnalyses/inbox"

DOTNET_BIN="dotnet"
TILER_DLL="$TILER_DIR/bin/Debug/net10.0/Tiler.dll"

# ---- Input validation ----

if [[ $# -ne 1 ]]; then
    echo "Usage: tiler-wrapper.sh <path-to-heightmap>" >&2
    exit 1
fi

INPUT_FILE="$1"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Input file does not exist: $INPUT_FILE" >&2
    exit 2
fi

if [[ "${INPUT_FILE##*.}" != "heightmap" ]]; then
    echo "Input file is not a .heightmap: $INPUT_FILE" >&2
    exit 3
fi

# ---- Ensure directories exist ----

mkdir -p "$OUTBOX_DIR"
mkdir -p "$WEATHER_INBOX_DIR"

# ---- Run Tiler ----

echo "[Tiler] Processing heightmap:"
echo "  $INPUT_FILE"

"$DOTNET_BIN" "$TILER_DLL" "$INPUT_FILE" --outbox "$OUTBOX_DIR"

# ---- Verify output ----

BASENAME="$(basename "$INPUT_FILE" .heightmap)"
OUTPUT_FILE="$OUTBOX_DIR/$BASENAME.maptiles"

if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "[Tiler] Expected output not found:" >&2
    echo "  $OUTPUT_FILE" >&2
    exit 4
fi

# ---- Handoff to WeatherAnalyses ----

DEST_PATH="$WEATHER_INBOX_DIR/$(basename "$INPUT_FILE")"

mv "$INPUT_FILE" "$DEST_PATH"

echo "[Tiler] Success"
echo "  Tile output : $OUTPUT_FILE"
echo "  Handed off  : $DEST_PATH"

exit 0
