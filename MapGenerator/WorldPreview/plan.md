# WorldPreview Implementation Plan

## Goal

Implement the `WorldPreview` stage to generate a static, human-inspectable HTML preview of the generated world.

## methodology: TYS (Implement -> Verify -> Loop)

## Phase 1: Scaffolding & Setup

1. **Scaffold**: Use `tools/create_module.sh WorldPreview` to create the Rust project structure.
2. **Dependencies**: Add `image` (0.24) and `hex` to `Cargo.toml` for image generation.
3. **Install Script**: Verify `install.sh` builds the binary.

## Phase 2: Tileset Generation (Rust)

1. **Image Logic**: In `main.rs`, implement `generate_tileset()`.
    * Create a 32x32 (or similar) grid of tiles.
    * Draw symbolic representations:
        * **Grass/Dirt**: Solid colors.
        * **Water**: Blue with wave pattern.
        * **Tree**: Green circle/triangle.
        * **Ridge**: Grey chevron.
        * **Road**: Brown line.
        * **Structure**: Simple house icon.
    * Save to `outbox/<job_id>/assets/tileset.png`.

## Phase 3: Previewer Logic (HTML/JS)

1. **Static Files**: Embed HTML/CSS/JS strings in `main.rs` (or read from `src/static`).
    * `index.html`: Canvas-based viewer.
    * `main.js`:
        * Fetch `world.json` and `assets/tileset.png`.
        * Render loop (drawImage from tileset based on world data).
        * Zoom/Pan logic (wheel/drag listeners).
        * Hover logic (translate mouse -> grid -> lookup info).
    * `style.css`: Basic layout, absolute positioning for overlay.
2. **Data Copy**: Read input `pathfinder` payload and write it as `world.json` in the output folder.

## Phase 4: Verification

1. **Trigger**: Manually invoke `bin/worldpreview-engine --job-file <path> --output-file <outbox>`.
2. **Check**:
    * `index.html` opens in a browser (simulated check: verification script checks file presence and valid syntax).
    * `tileset.png` is a valid image.
    * `world.json` contains tile data.

## Technical Details

* **Language**: Rust (Generator), Vanilla JS (Viewer).
* **Libraries**: `image`, `serde_json`, `serde`.
* **No Server**: Must work via `file://` protocol.

## Next Steps

Execute scaffolding.
