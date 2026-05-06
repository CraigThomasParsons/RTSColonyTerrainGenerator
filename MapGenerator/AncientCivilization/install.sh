#!/bin/bash
set -e

# Build the release version of the engine
cd bin/ancientcivilization-engine
cargo build --release
# Copy the compiled binary to the module root
cp target/release/ancientcivilization-engine ../ancientcivilization-engine
# Ensure it is executable
chmod +x ../ancientcivilization-engine
echo "Installed ancientcivilization-engine"
