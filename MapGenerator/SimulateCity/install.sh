#!/usr/bin/env bash
#
# SimulateCity install script
#
# Responsibilities:
# - Ensure required directories exist
# - Install systemd user units
# - Enable the path unit
#

set -euo pipefail

STAGE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/SimulateCity"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$STAGE_ROOT/bin"
mkdir -p "$STAGE_ROOT/inbox"
mkdir -p "$STAGE_ROOT/outbox"
mkdir -p "$STAGE_ROOT/archive"
mkdir -p "$STAGE_ROOT/failed"
mkdir -p "$STAGE_ROOT/debug"
mkdir -p "$STAGE_ROOT/docs"

ln -sf \
    "$STAGE_ROOT/systemd/simulatecity.service" \
    "$SYSTEMD_USER_DIR/simulatecity.service"

ln -sf \
    "$STAGE_ROOT/systemd/simulatecity.path" \
    "$SYSTEMD_USER_DIR/simulatecity.path"

systemctl --user daemon-reload
systemctl --user enable --now simulatecity.path

echo "[SimulateCity] Installation complete."
