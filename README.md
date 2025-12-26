# RTSColonyTerrainGenerator
The Map Generator for the rts colony sim.


### Building the heightmap engine
cd MapGenerator/Heightmap/bin/heightmap-engine
cargo clean
cargo build --release
cp target/release/heightmap-engine ./heightmap-engine
chmod +x heightmap-engine
systemctl --user restart heightmap-queue.service