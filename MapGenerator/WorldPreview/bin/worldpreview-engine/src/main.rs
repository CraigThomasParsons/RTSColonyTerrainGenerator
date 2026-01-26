use std::env;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};
use image::{ImageBuffer, Rgb};

#[derive(Debug, Deserialize, Serialize)]
struct Job {
    job_id: String,
}

// RTS-style tileset atlas: 16 columns, 8 rows = 128 tiles (32x32 each)
// Layout: Row 0-1: Base terrain | Row 2-5: Ridge variations | Row 6-7: Decorations
const ATLAS_WIDTH: u32 = 512;
const ATLAS_HEIGHT: u32 = 256;

// Embedded Static Files - HTML template with placeholder for inline data
fn get_html_template(world_json: &str) -> String {
    // NOTE: In Rust format!, use {{}} to escape literal braces.
    // The {} in "window.WORLD_DATA = {}" needs proper handling.
    format!(r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>World Preview</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="ui-layer">
        <div id="info-panel">
            <h1>World Preview</h1>
            <div id="status">Loading...</div>
            <div id="hover-info">Hover over a tile</div>
            <div id="controls">
                <label><input type="checkbox" id="toggle-height" checked> Heightmap</label>
                <label><input type="checkbox" id="toggle-terrain" checked> Terrain</label>
                <label><input type="checkbox" id="toggle-features" checked> Features</label>
                <label><input type="checkbox" id="toggle-paths" checked> Paths</label>
            </div>
        </div>
    </div>
    <canvas id="world-canvas"></canvas>
    <!-- INLINE WORLD DATA: Embedded to avoid fetch() CORS issues on file:// -->
    <script>
        window.WORLD_DATA = {world_data};
    </script>
    <script src="main.js"></script>
</body>
</html>"#, world_data = world_json)
}

const CSS_TEMPLATE: &str = r#"body { margin: 0; overflow: hidden; background: #222; color: #eee; font-family: monospace; }
#ui-layer { position: absolute; top: 10px; left: 10px; pointer-events: none; z-index: 100; }
#info-panel { background: rgba(0, 0, 0, 0.8); padding: 15px; border-radius: 8px; pointer-events: auto; max-width: 300px; }
canvas { display: block; image-rendering: pixelated; }
#controls label { display: block; margin-top: 5px; cursor: pointer; }
#hover-info { margin-top: 10px; font-size: 12px; line-height: 1.4; }"#;

// Updated JS: Uses window.WORLD_DATA instead of fetch()
const JS_TEMPLATE: &str = r#"const TILE_SIZE = 32;
let world = window.WORLD_DATA; // Embedded inline, no fetch needed!
let tileset = new Image();
let canvas = document.getElementById('world-canvas');
let ctx = canvas.getContext('2d');
let camera = { x: 0, y: 0, zoom: 0.5 };
let isDragging = false;
let lastMouse = { x: 0, y: 0 };

// Tile Mappings (Sync with Rust generation)
// Row 0: Base terrain
const TILES = {
    GRASS: { x: 0, y: 0 },
    DIRT:  { x: 32, y: 0 },
    WATER: { x: 64, y: 0 },
    DEEP_WATER: { x: 96, y: 0 },
    ROCK:  { x: 128, y: 0 },
    SAND:  { x: 160, y: 0 },
    
    // Row 1: Terrain variations
    GRASS_DARK: { x: 0, y: 32 },
    DIRT_LIGHT: { x: 32, y: 32 },
    
    // Row 2: Ridge tiles - North facing (cliff on south side)
    RIDGE_N: { x: 0, y: 64 },
    RIDGE_S: { x: 32, y: 64 },
    RIDGE_E: { x: 64, y: 64 },
    RIDGE_W: { x: 96, y: 64 },
    
    // Row 3: Ridge corners - outer
    RIDGE_NE: { x: 0, y: 96 },
    RIDGE_NW: { x: 32, y: 96 },
    RIDGE_SE: { x: 64, y: 96 },
    RIDGE_SW: { x: 96, y: 96 },
    
    // Row 4: Ridge corners - inner
    RIDGE_INNER_NE: { x: 0, y: 128 },
    RIDGE_INNER_NW: { x: 32, y: 128 },
    RIDGE_INNER_SE: { x: 64, y: 128 },
    RIDGE_INNER_SW: { x: 96, y: 128 },
    
    // Row 6: Decorations
    TREE:  { x: 0, y: 192 },
    TREE_PINE: { x: 32, y: 192 },
    ROCK_SMALL: { x: 64, y: 192 },
    BUSH: { x: 96, y: 192 },
    
    // Row 7: Infrastructure
    ROAD:  { x: 0, y: 224 },
    PATH:  { x: 32, y: 224 },
    BRIDGE:{ x: 64, y: 224 }
};

function init() {
    if (!world || !world.tiles) {
        document.getElementById('status').textContent = 'Error: No world data embedded';
        console.error('window.WORLD_DATA is missing or invalid');
        return;
    }
    
    tileset.src = 'assets/tileset.png';
    tileset.onload = () => {
        document.getElementById('status').textContent = `Loaded: ${world.job_id} (${world.tiles.length} tiles)`;
        resize();
        draw();
    };
    tileset.onerror = () => {
        document.getElementById('status').textContent = 'Error loading tileset.png';
    };
}

function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    draw();
}

function draw() {
    if (!world || !world.tiles || !tileset.complete) return;
    
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.save();
    ctx.translate(canvas.width/2 + camera.x, canvas.height/2 + camera.y);
    ctx.scale(camera.zoom, camera.zoom);
    
    // Helper: Get tile at position
    const getTile = (x, y) => world.tiles.find(t => t.x === x && t.y === y);
    
    // Helper: Get height (default to 0 if no weather data)
    const getHeight = (tile) => {
        if (!tile) return 0;
        if (tile.height !== undefined) return tile.height;
        if (tile.weather && tile.weather.height !== undefined) return tile.weather.height;
        return 0;
    };
    
    // PASS 1: Draw base terrain
    world.tiles.forEach(tile => {
        let src = TILES.GRASS;
        if (tile.terrain === 'dirt') src = TILES.DIRT;
        if (tile.terrain === 'rock' || tile.terrain === 'mountain') src = TILES.ROCK;
        if (tile.terrain === 'water') src = TILES.WATER;
        if (tile.terrain === 'deep_water') src = TILES.DEEP_WATER;
        
        if (document.getElementById('toggle-terrain').checked) {
            ctx.drawImage(tileset, src.x, src.y, 32, 32, tile.x * 32, tile.y * 32, 32, 32);
        }
    });
    
    // PASS 2: Draw ridges (cliff edges) - RTS style!
    // Ridge threshold: show cliff if height difference >= 0.15
    const RIDGE_THRESHOLD = 0.15;
    
    world.tiles.forEach(tile => {
        const h = getHeight(tile);
        const x = tile.x;
        const y = tile.y;
        
        // Check all 4 cardinal neighbors
        const north = getTile(x, y - 1);
        const south = getTile(x, y + 1);
        const east = getTile(x + 1, y);
        const west = getTile(x - 1, y);
        
        const hN = getHeight(north);
        const hS = getHeight(south);
        const hE = getHeight(east);
        const hW = getHeight(west);
        
        // Draw ridge if this tile is higher than neighbor
        // Ridge faces the LOWER terrain (cliff edge)
        if (h - hS >= RIDGE_THRESHOLD) {
            // South neighbor is lower - draw south-facing ridge
            ctx.drawImage(tileset, TILES.RIDGE_S.x, TILES.RIDGE_S.y, 32, 32, x * 32, y * 32, 32, 32);
        }
        if (h - hN >= RIDGE_THRESHOLD) {
            // North neighbor is lower - draw north-facing ridge
            ctx.drawImage(tileset, TILES.RIDGE_N.x, TILES.RIDGE_N.y, 32, 32, x * 32, y * 32, 32, 32);
        }
        if (h - hE >= RIDGE_THRESHOLD) {
            // East neighbor is lower - draw east-facing ridge
            ctx.drawImage(tileset, TILES.RIDGE_E.x, TILES.RIDGE_E.y, 32, 32, x * 32, y * 32, 32, 32);
        }
        if (h - hW >= RIDGE_THRESHOLD) {
            // West neighbor is lower - draw west-facing ridge
            ctx.drawImage(tileset, TILES.RIDGE_W.x, TILES.RIDGE_W.y, 32, 32, x * 32, y * 32, 32, 32);
        }
    });
    
    // PASS 3: Draw features (decorations)
    if (document.getElementById('toggle-features').checked) {
        world.tiles.forEach(tile => {
            if (tile.decorations) {
                tile.decorations.forEach(dec => {
                    // Fix: Check for 'type' or 'vegetation' (legacy)
                    if (dec.type === 'tree' || dec.vegetation) {
                        ctx.drawImage(tileset, TILES.TREE.x, TILES.TREE.y, 32, 32, tile.x * 32, tile.y * 32, 32, 32);
                    }
                });
            }
        });
    }
    
    // Draw Routes/Paths (from PathFinder output if present)
    if (document.getElementById('toggle-paths').checked && world.routes) {
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 2 / camera.zoom;
        world.routes.forEach(route => {
            if (route.success && route.path && route.path.length > 1) {
                ctx.beginPath();
                const start = route.path[0].split(',');
                ctx.moveTo(parseInt(start[0]) * 32 + 16, parseInt(start[1]) * 32 + 16);
                for (let i = 1; i < route.path.length; i++) {
                    const pt = route.path[i].split(',');
                    ctx.lineTo(parseInt(pt[0]) * 32 + 16, parseInt(pt[1]) * 32 + 16);
                }
                ctx.stroke();
            }
        });
    }
    
    ctx.restore();
}

// Input Handling
window.addEventListener('resize', resize);
canvas.addEventListener('mousedown', e => { isDragging = true; lastMouse = { x: e.clientX, y: e.clientY }; });
window.addEventListener('mouseup', () => isDragging = false);
canvas.addEventListener('mousemove', e => {
    if (isDragging) {
        camera.x += e.clientX - lastMouse.x;
        camera.y += e.clientY - lastMouse.y;
        lastMouse = { x: e.clientX, y: e.clientY };
        draw();
    }
    // Hover logic
    if (!world || !world.tiles) return;
    const worldX = Math.floor(((e.clientX - canvas.width/2 - camera.x) / camera.zoom) / 32);
    const worldY = Math.floor(((e.clientY - canvas.height/2 - camera.y) / camera.zoom) / 32);
    const tile = world.tiles.find(t => t.x === worldX && t.y === worldY);
    
    const info = document.getElementById('hover-info');
    if (tile) {
        info.innerHTML = `<b>Job:</b> ${world.job_id}<br>
        <b>X:</b> ${tile.x} <b>Y:</b> ${tile.y}<br>
        <b>Terrain:</b> ${tile.terrain}<br>
        <b>Slope:</b> ${tile.weather ? tile.weather.slope : 'N/A'}`;
    } else {
        info.textContent = `X: ${worldX} Y: ${worldY} (Empty)`;
    }
});
canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const zoomSpeed = 0.1;
    camera.zoom += e.deltaY < 0 ? zoomSpeed : -zoomSpeed;
    camera.zoom = Math.max(0.1, Math.min(camera.zoom, 5));
    draw();
});

document.querySelectorAll('input').forEach(i => i.addEventListener('change', draw));

init();
"#;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 5 {
        eprintln!("Usage: worldpreview-engine --job-file <path> --output-file <path>");
        std::process::exit(1);
    }

    let input_path = &args[2];
    let output_root = &args[4];
    
    println!("Processing job from {}", input_path);

    // 1. Read Payload
    let content = fs::read_to_string(input_path).expect("Failed to read input file");
    let job: Job = serde_json::from_str(&content).expect("Failed to parse JSON job header");
    let job_id = job.job_id.clone();

    println!("Job ID: {}", job_id);

    // 2. Prepare Output Directory: output_root/job_id/
    let base_path = Path::new(output_root);
    let job_dir = base_path.join(&job_id);
    let assets_dir = job_dir.join("assets");

    fs::create_dir_all(&assets_dir).expect("Failed to create output/assets dirs");

    // 3. Write Static Files
    // KEY FIX: Embed the world JSON directly into the HTML to avoid fetch() CORS issues
    let html_content = get_html_template(&content);
    fs::write(job_dir.join("index.html"), html_content).expect("Failed to write index.html");
    fs::write(job_dir.join("style.css"), CSS_TEMPLATE).expect("Failed to write style.css");
    fs::write(job_dir.join("main.js"), JS_TEMPLATE).expect("Failed to write main.js");
    
    // 4. Also write world.json for reference (not used by viewer, but useful for debugging)
    fs::write(job_dir.join("world.json"), &content).expect("Failed to write world.json");

    // 5. Generate Tileset
    generate_tileset(&assets_dir.join("tileset.png"));

    println!("Preview generated at: {}", job_dir.display());
}

fn generate_tileset(path: &Path) {
    let mut img = ImageBuffer::new(ATLAS_WIDTH, ATLAS_HEIGHT);

    // Helper to fill rect
    let mut draw_rect = |x: u32, y: u32, w: u32, h: u32, color: Rgb<u8>| {
        for iy in y..y+h {
            for ix in x..x+w {
                if ix < ATLAS_WIDTH && iy < ATLAS_HEIGHT {
                    img.put_pixel(ix, iy, color);
                }
            }
        }
    };

    // Color palette - RTS style
    let grass = Rgb([100, 180, 80]);
    let grass_dark = Rgb([80, 150, 60]);
    let dirt = Rgb([140, 100, 60]);
    let dirt_light = Rgb([160, 120, 80]);
    let water = Rgb([60, 120, 200]);
    let deep_water = Rgb([40, 80, 160]);
    let rock = Rgb([120, 120, 120]);
    let sand = Rgb([200, 180, 140]);
    
    // Cliff colors - brown/tan like Warcraft 2 and Avalon
    let cliff_brown = Rgb([120, 80, 50]);
    let cliff_tan = Rgb([140, 100, 70]);
    let cliff_dark = Rgb([90, 60, 40]);

    // --- ROW 0: Base Terrain (y=0) ---
    // Grass (0,0)
    draw_rect(0, 0, 32, 32, grass);
    for i in 0..8 {
        draw_rect(i*4, i*4, 2, 2, grass_dark);
    }
    
    // Dirt (32,0)
    draw_rect(32, 0, 32, 32, dirt);
    for i in 0..6 {
        draw_rect(32 + i*5, i*5, 3, 3, dirt_light);
    }
    
    // Water (64,0)
    draw_rect(64, 0, 32, 32, water);
    for i in 0..4 {
        draw_rect(64, i*8, 32, 2, Rgb([80, 140, 220]));
    }
    
    // Deep Water (96,0)
    draw_rect(96, 0, 32, 32, deep_water);
    
    // Rock (128,0)
    draw_rect(128, 0, 32, 32, rock);
    for i in 0..5 {
        draw_rect(128 + i*6, i*6, 4, 4, Rgb([100, 100, 100]));
    }
    
    // Sand (160,0)
    draw_rect(160, 0, 32, 32, sand);

    // --- ROW 1: Terrain Variations (y=32) ---
    draw_rect(0, 32, 32, 32, grass_dark);
    draw_rect(32, 32, 32, 32, dirt_light);

    // --- ROW 2: Ridge Tiles - Cardinal Directions (y=64) ---
    // RIDGE_N (0, 64) - Cliff on NORTH edge (top)
    draw_rect(0, 64, 32, 32, grass);
    draw_rect(0, 64, 32, 10, cliff_brown);
    draw_rect(0, 66, 32, 2, cliff_dark);
    draw_rect(0, 70, 32, 2, cliff_tan);
    
    // RIDGE_S (32, 64) - Cliff on SOUTH edge (bottom)
    draw_rect(32, 64, 32, 32, grass);
    draw_rect(32, 86, 32, 10, cliff_brown);
    draw_rect(32, 88, 32, 2, cliff_dark);
    draw_rect(32, 92, 32, 2, cliff_tan);
    
    // RIDGE_E (64, 64) - Cliff on EAST edge (right)
    draw_rect(64, 64, 32, 32, grass);
    draw_rect(86, 64, 10, 32, cliff_brown);
    draw_rect(88, 64, 2, 32, cliff_dark);
    draw_rect(92, 64, 2, 32, cliff_tan);
    
    // RIDGE_W (96, 64) - Cliff on WEST edge (left)
    draw_rect(96, 64, 32, 32, grass);
    draw_rect(96, 64, 10, 32, cliff_brown);
    draw_rect(98, 64, 2, 32, cliff_dark);
    draw_rect(102, 64, 2, 32, cliff_tan);

    // --- ROW 3: Ridge Corners - Outer (y=96) ---
    draw_rect(0, 96, 32, 32, grass);
    draw_rect(0, 96, 32, 10, cliff_brown);
    draw_rect(86, 96, 10, 32, cliff_brown);
    
    draw_rect(32, 96, 32, 32, grass);
    draw_rect(32, 96, 32, 10, cliff_brown);
    draw_rect(32, 96, 10, 32, cliff_brown);
    
    draw_rect(64, 96, 32, 32, grass);
    draw_rect(64, 86, 32, 10, cliff_brown);
    draw_rect(86, 96, 10, 32, cliff_brown);
    
    draw_rect(96, 96, 32, 32, grass);
    draw_rect(96, 86, 32, 10, cliff_brown);
    draw_rect(96, 96, 10, 32, cliff_brown);

    // --- ROW 4: Inner corners (y=128) ---
    draw_rect(0, 128, 32, 32, grass);
    draw_rect(32, 128, 32, 32, grass);
    draw_rect(64, 128, 32, 32, grass);
    draw_rect(96, 128, 32, 32, grass);

    // --- ROW 6: Decorations (y=192) ---
    // Tree
    draw_rect(0, 192, 32, 32, grass);
    draw_rect(14, 206, 4, 12, Rgb([60, 40, 20]));
    draw_rect(10, 196, 12, 12, Rgb([40, 120, 40]));
    
    // Pine Tree
    draw_rect(32, 192, 32, 32, grass);
    draw_rect(46, 206, 4, 12, Rgb([60, 40, 20]));
    draw_rect(44, 200, 8, 6, Rgb([30, 100, 30]));
    draw_rect(42, 206, 12, 6, Rgb([30, 100, 30]));
    
    // Rock Small
    draw_rect(64, 192, 32, 32, grass);
    draw_rect(74, 202, 12, 10, rock);
    draw_rect(76, 204, 8, 6, Rgb([140, 140, 140]));
    
    // Bush
    draw_rect(96, 192, 32, 32, grass);
    draw_rect(104, 204, 16, 10, Rgb([50, 130, 50]));

    // --- ROW 7: Infrastructure (y=224) ---
    // Road
    draw_rect(0, 224, 32, 32, grass);
    draw_rect(12, 224, 8, 32, Rgb([180, 160, 120]));
    
    // Path
    draw_rect(32, 224, 32, 32, grass);
    draw_rect(38, 224, 4, 32, Rgb([200, 180, 140]));
    
    // Bridge
    draw_rect(64, 224, 32, 32, water);
    draw_rect(74, 224, 12, 32, Rgb([140, 100, 60]));

    img.save(path).expect("Failed to save tileset.png");
}
