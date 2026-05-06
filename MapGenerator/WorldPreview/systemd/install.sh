#!/usr/bin/env bash

mkdir -p ~/.config/systemd/user
ln -sf ~/Code/RTSColonyTerrainGenerator/MapGenerator/WorldPreview/systemd/worldpreview.service ~/.config/systemd/user/
ln -sf ~/Code/RTSColonyTerrainGenerator/MapGenerator/WorldPreview/systemd/worldpreview.path ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now worldpreview.path
