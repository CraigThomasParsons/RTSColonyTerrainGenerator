#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/Code/RTSColonyTerrainGenerator}"
EXPORT_SCRIPT="$REPO_ROOT/MapGenerator/StargusExport/bin/consume_stargusexport_job.sh"

# Default to the local Stargus maps directory unless explicitly overridden.
STARGUS_MAPS_DIR="${STARGUS_MAPS_DIR:-$HOME/.stratagus/sc/maps}"

export STARGUS_MAPS_DIR
exec "$EXPORT_SCRIPT"
