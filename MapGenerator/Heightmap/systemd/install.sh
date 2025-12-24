#!/usr/bin/env bash
#
# Install script for Heightmap module systemd units
#
# This script:
# - Symlinks systemd user units into ~/.config/systemd/user
# - Reloads the systemd user daemon
# - Enables and starts the heightmap queue watcher
#

set -euo pipefail

#######################################
# Explicit paths (no magic)
#######################################

HEIGHTMAP_MODULE_ROOT="$HOME/MapGenerator/Heightmap"

SYSTEMD_SOURCE_DIRECTORY="$HEIGHTMAP_MODULE_ROOT/systemd/heightmap-queue"
SYSTEMD_TARGET_DIRECTORY="$HOME/.config/systemd/user"

PATH_UNIT_NAME="heightmap-queue.path"
SERVICE_UNIT_NAME="heightmap-queue.service"

#######################################
# Ensure systemd user directory exists
#######################################

mkdir -p "$SYSTEMD_TARGET_DIRECTORY"

#######################################
# Create or update symlinks
#######################################

ln -sfn \
    "$SYSTEMD_SOURCE_DIRECTORY/$PATH_UNIT_NAME" \
    "$SYSTEMD_TARGET_DIRECTORY/$PATH_UNIT_NAME"

ln -sfn \
    "$SYSTEMD_SOURCE_DIRECTORY/$SERVICE_UNIT_NAME" \
    "$SYSTEMD_TARGET_DIRECTORY/$SERVICE_UNIT_NAME"

echo "[install] Symlinked systemd user units"

#######################################
# Reload systemd user daemon
#######################################

systemctl --user daemon-reload
echo "[install] systemd user daemon reloaded"

#######################################
# Enable and start the path unit
#######################################

systemctl --user enable --now "$PATH_UNIT_NAME"
echo "[install] Enabled and started $PATH_UNIT_NAME"

echo "[install] Heightmap module installation complete"
