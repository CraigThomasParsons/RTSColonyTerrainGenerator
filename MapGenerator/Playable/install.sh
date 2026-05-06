#!/usr/bin/env bash
# Playable stage install script
# - Ensures required directories
# - Installs systemd user units
# - Enables path watcher

set -euo pipefail

PLAYABLE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/Playable"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$PLAYABLE_ROOT/bin" "$PLAYABLE_ROOT/inbox" "$PLAYABLE_ROOT/outbox" \
  "$PLAYABLE_ROOT/archive" "$PLAYABLE_ROOT/failed" "$PLAYABLE_ROOT/debug" "$PLAYABLE_ROOT/docs"

ln -sf "$PLAYABLE_ROOT/systemd/playable.service" "$SYSTEMD_USER_DIR/playable.service"
ln -sf "$PLAYABLE_ROOT/systemd/playable.path" "$SYSTEMD_USER_DIR/playable.path"

systemctl --user daemon-reload
systemctl --user enable --now playable.path

echo "[Playable] Installation complete."
