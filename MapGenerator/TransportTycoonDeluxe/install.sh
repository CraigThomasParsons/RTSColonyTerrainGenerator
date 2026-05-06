#!/usr/bin/env bash
#
# TransportTycoonDeluxe install script
#
# Responsibilities:
# - Ensure required directories exist
# - Install systemd user units
# - Enable the path unit
#

set -euo pipefail

STAGE_ROOT="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/TransportTycoonDeluxe"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_USER_DIR"
mkdir -p "$STAGE_ROOT/bin"
mkdir -p "$STAGE_ROOT/inbox"
mkdir -p "$STAGE_ROOT/outbox"
mkdir -p "$STAGE_ROOT/archive"
mkdir -p "$STAGE_ROOT/failed"
mkdir -p "$STAGE_ROOT/debug"
mkdir -p "$STAGE_ROOT/docs"

chmod +x "$STAGE_ROOT/bin/run_transport_tycoon.sh" || true

ln -sf \
    "$STAGE_ROOT/systemd/transporttycoondeluxe.service" \
    "$SYSTEMD_USER_DIR/transporttycoondeluxe.service"

ln -sf \
    "$STAGE_ROOT/systemd/transporttycoondeluxe.path" \
    "$SYSTEMD_USER_DIR/transporttycoondeluxe.path"

systemctl --user daemon-reload
systemctl --user enable --now transporttycoondeluxe.path

echo "[TransportTycoonDeluxe] Installation complete."
