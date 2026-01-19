#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_DIR"

ln -sf "$SCRIPT_DIR/systemd/web-dashboard.service" "$SYSTEMD_DIR/web-dashboard.service"
ln -sf "$SCRIPT_DIR/systemd/web-dashboard-reload.service" "$SYSTEMD_DIR/web-dashboard-reload.service"
ln -sf "$SCRIPT_DIR/systemd/web-dashboard.path" "$SYSTEMD_DIR/web-dashboard.path"

systemctl --user daemon-reload
systemctl --user enable --now web-dashboard.service
systemctl --user enable --now web-dashboard.path

echo "Pipeline dashboard is enabled on http://localhost:5001"
