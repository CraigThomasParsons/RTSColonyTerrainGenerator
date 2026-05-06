#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Installs user-level systemd timer for LeftOff autosave snapshots.
# -----------------------------------------------------------------------------

REPO_ROOT="${REPO_ROOT:-$HOME/Code/RTSColonyTerrainGenerator}"
MAPGEN_ROOT="${MAPGEN_ROOT:-$REPO_ROOT/MapGenerator}"
SYSTEMD_USER_DIR="${SYSTEMD_USER_DIR:-$HOME/.config/systemd/user}"

mkdir -p "$SYSTEMD_USER_DIR"

ln -sf "$MAPGEN_ROOT/systemd/leftoff-autosave.service" "$SYSTEMD_USER_DIR/leftoff-autosave.service"
ln -sf "$MAPGEN_ROOT/systemd/leftoff-autosave.timer" "$SYSTEMD_USER_DIR/leftoff-autosave.timer"

systemctl --user daemon-reload
systemctl --user enable --now leftoff-autosave.timer

echo "[leftoff] Installed and started leftoff-autosave.timer"
systemctl --user status --no-pager --lines=5 leftoff-autosave.timer || true
