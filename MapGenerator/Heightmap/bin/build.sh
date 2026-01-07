#!/usr/bin/env bash
set -euo pipefail

# Resolve paths explicitly to avoid ambiguity
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR/../heightmap-engine"
BIN_DIR="$SCRIPT_DIR"

echo "[build] Building heightmap-engine (release)"

cd "$ENGINE_DIR"
cargo build --release

echo "[build] Installing binary to bin/"

cp \
  "$ENGINE_DIR/target/release/heightmap-engine" \
  "$BIN_DIR/heightmap-engine"

chmod +x "$BIN_DIR/heightmap-engine"

echo "[build] Done:"
echo "        $BIN_DIR/heightmap-engine"
