#!/usr/bin/env bash
#
# tiler-wrapper.sh
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

set -euo pipefail

# Absolute path to the Tiler directory
TILER_DIR="$(cd "$(dirname "$0")" && pwd)"

INBOX="$TILER_DIR/inbox"

# Find exactly one heightmap file
HEIGHTMAP_FILE="$(find "$INBOX" -maxdepth 1 -type f -name '*.heightmap' | head -n 1)"

# Nothing to do
if [[ -z "$HEIGHTMAP_FILE" ]]; then
    exit 0
fi

# Run the tiler from its own working directory
cd "$TILER_DIR"

dotnet run -- "$HEIGHTMAP_FILE"

echo "[Tiler] Success"
echo "  Tile output : $OUTPUT_FILE"
echo "  Handed off  : $DEST_PATH"
