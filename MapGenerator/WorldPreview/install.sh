#!/bin/bash
set -e

# Build the release version of the engine
cd bin/worldpreview-engine
cargo build --release
# Copy the compiled binary to the module root
cp target/release/worldpreview-engine ../worldpreview-engine
# Ensure it is executable
chmod +x ../worldpreview-engine
echo "Installed worldpreview-engine"

# Systemd Installation
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

# Correct path: we are in bin/worldpreview-engine, so we go up 2 levels
MODULE_ROOT="$(dirname "$(pwd)")/.."
# Or simpler:
MODULE_ROOT_ABS="$(cd ../.. && pwd)"

ln -sf "$MODULE_ROOT_ABS/systemd/worldpreview.service" "$SYSTEMD_USER_DIR/worldpreview.service"
ln -sf "$MODULE_ROOT_ABS/systemd/worldpreview.path" "$SYSTEMD_USER_DIR/worldpreview.path"

systemctl --user daemon-reload
systemctl --user enable --now worldpreview.path

echo "Installed systemd units."
