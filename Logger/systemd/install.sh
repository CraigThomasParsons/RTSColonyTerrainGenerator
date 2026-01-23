#!/usr/bin/env bash
# Install script for the LogStreamer systemd user unit.
# Mirrors other modules: symlink into ~/.config/systemd/user and enable the unit.

set -euo pipefail

LOGGER_ROOT="$HOME/Code/RTSColonyTerrainGenerator/Logger"
SYSTEMD_TARGET_DIRECTORY="$HOME/.config/systemd/user"
UNIT_NAME="logstreamer.service"

mkdir -p "$SYSTEMD_TARGET_DIRECTORY"

ln -sfn \
  "$LOGGER_ROOT/systemd/$UNIT_NAME" \
  "$SYSTEMD_TARGET_DIRECTORY/$UNIT_NAME"

echo "[install] Symlinked $UNIT_NAME"

systemctl --user daemon-reload
echo "[install] systemd user daemon reloaded"

systemctl --user enable --now "$UNIT_NAME"
echo "[install] Enabled and started $UNIT_NAME"

echo "[install] LogStreamer installation complete"
