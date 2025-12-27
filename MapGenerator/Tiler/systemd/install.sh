#!/usr/bin/env bash

mkdir -p ~/.config/systemd/user
ln -s ~/Code/RTSColonyTerrainGenerator/MapGenerator/Tiler/systemd/tiler.service ~/.config/systemd/user/
ln -s ~/Code/RTSColonyTerrainGenerator/MapGenerator/Tiler/systemd/tiler.path ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now tiler.path
