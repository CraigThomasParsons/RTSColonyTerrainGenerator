#!/usr/bin/env bash
set -euo pipefail

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
MODULE_ROOT_ABS="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$SYSTEMD_USER_DIR"

ln -sf "$MODULE_ROOT_ABS/systemd/worldsnapshot.service" "$SYSTEMD_USER_DIR/worldsnapshot.service"
ln -sf "$MODULE_ROOT_ABS/systemd/worldsnapshot.path" "$SYSTEMD_USER_DIR/worldsnapshot.path"

systemctl --user daemon-reload
systemctl --user enable --now worldsnapshot.path

echo "Installed WorldSnapshot systemd units."
