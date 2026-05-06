#!/usr/bin/env bash
#
# PathFinder install script
#
# Responsibilities:
# - Ensure required directories exist
# - Install systemd user units
# - Enable the path unit
#

set -euo pipefail

PATHFINDER_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/PathFinder"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$PATHFINDER_ROOT/bin"
mkdir -p "$PATHFINDER_ROOT/inbox"
mkdir -p "$PATHFINDER_ROOT/outbox"
mkdir -p "$PATHFINDER_ROOT/archive"
mkdir -p "$PATHFINDER_ROOT/failed"
mkdir -p "$PATHFINDER_ROOT/systemd"

ln -sf \
    "$PATHFINDER_ROOT/systemd/pathfinder.service" \
    "$SYSTEMD_USER_DIR/pathfinder.service"

ln -sf \
    "$PATHFINDER_ROOT/systemd/pathfinder.path" \
    "$SYSTEMD_USER_DIR/pathfinder.path"

systemctl --user daemon-reload
systemctl --user enable --now pathfinder.path

echo "[PathFinder] Installation complete."
