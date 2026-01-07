#!/usr/bin/env bash
set -e

# Define paths
STAGE_DIR=~/Code/RTSColonyTerrainGenerator/MapGenerator/WeatherAnalyses
SYSTEMD_DIR=~/.config/systemd/user

# Create systemd user directory if it doesn't exist
mkdir -p "$SYSTEMD_DIR"

# Link systemd units
echo "Linking systemd units..."
ln -sf "$STAGE_DIR/systemd/weather.service" "$SYSTEMD_DIR/"
ln -sf "$STAGE_DIR/systemd/weather.path" "$SYSTEMD_DIR/"

# Reload and enable
echo "Reloading systemd..."
systemctl --user daemon-reload
echo "Enabling weather.path..."
systemctl --user enable --now weather.path

echo "WeatherAnalyses stage installed successfully."
