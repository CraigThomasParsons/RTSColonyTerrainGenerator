#!/usr/bin/env bash
#
# WorldFeatures install script
#
# Responsibilities:
# - Ensure required directories exist
# - Install systemd user units
# - Enable the path unit
#

set -euo pipefail

WORLD_FEATURES_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$WORLD_FEATURES_ROOT/bin"
mkdir -p "$WORLD_FEATURES_ROOT/inbox"
mkdir -p "$WORLD_FEATURES_ROOT/outbox"
mkdir -p "$WORLD_FEATURES_ROOT/archive"
mkdir -p "$WORLD_FEATURES_ROOT/failed"

ln -sf \
    "$WORLD_FEATURES_ROOT/systemd/worldfeatures.service" \
    "$SYSTEMD_USER_DIR/worldfeatures.service"

ln -sf \
    "$WORLD_FEATURES_ROOT/systemd/worldfeatures.path" \
    "$SYSTEMD_USER_DIR/worldfeatures.path"

systemctl --user daemon-reload
systemctl --user enable --now worldfeatures.path

echo "[WorldFeatures] Installation complete."
