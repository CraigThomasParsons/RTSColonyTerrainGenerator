#!/bin/bash
set -e

cd bin/pathfinder-engine
cargo build --release
cp target/release/pathfinder-engine ../pathfinder-engine
chmod +x ../pathfinder-engine
echo "Installed pathfinder-engine"
