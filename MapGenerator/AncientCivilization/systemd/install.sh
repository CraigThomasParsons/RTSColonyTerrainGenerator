#!/usr/bin/env bash

mkdir -p ~/.config/systemd/user
ln -sf ~/Code/RTSColonyTerrainGenerator/MapGenerator/AncientCivilization/systemd/ancientcivilization.service ~/.config/systemd/user/
ln -sf ~/Code/RTSColonyTerrainGenerator/MapGenerator/AncientCivilization/systemd/ancientcivilization.path ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now ancientcivilization.path
