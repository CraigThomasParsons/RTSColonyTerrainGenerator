use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Deserialize;

use wcar::format::{HeadChunk, ProvChunk, ProvEntry, TileChunk, TileTypeDef};
use wcar::{WcarError, WcarFile};

//
// World payload input shape (subset).
//
#[derive(Debug, Deserialize)]
struct WorldPayload {
    job_id: String,
    map: WorldMap,
    tiles: Vec<WorldTile>,
}

#[derive(Debug, Deserialize)]
struct WorldMap {
    width_in_cells: u32,
    height_in_cells: u32,
}

#[derive(Debug, Deserialize)]
struct WorldTile {
    x: u32,
    y: u32,
    terrain: String,
}

//
// Entry point for the WCAR packer.
//
// This program:
// - Parses command-line arguments
// - Loads a world payload JSON file
// - Builds HEAD + PROV + TILE chunks
// - Writes a deterministic WCAR file
//
fn main() -> Result<(), WcarError> {
    let args = parse_args();
    let payload = load_payload(&args.input)?;

    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();

    let head = HeadChunk {
        magic: *b"WCAR",
        major_version: 0,
        minor_version: 2,
        world_uuid: parse_uuid(&payload.job_id).unwrap_or(0),
        created_unix_ts: now,
        width_tiles: payload.map.width_in_cells,
        height_tiles: payload.map.height_in_cells,
        tile_world_size: 1.0,
        vertical_scale: 1.0,
        declared_chunk_mask: 0,
    };

    let prov = ProvChunk {
        entries: vec![ProvEntry {
            stage_name: "CartridgeManufacturer".to_string(),
            stage_version: "0.1.0".to_string(),
            start_ts: now,
            end_ts: now,
            input_hash: 0,
            output_hash: 0,
        }],
    };

    let tile_chunk = build_tile_chunk(payload.map.width_in_cells, payload.map.height_in_cells, &payload.tiles);

    let wcar = WcarFile {
        head,
        prov,
        seed: None,
        hmap: None,
        tile: Some(tile_chunk),
        biom: None,
        feat: None,
        path: None,
        navi: None,
        chk: None,
        unknown_chunks: Vec::new(),
    };

    let output_path = args.output.join(format!("{}.wcar", payload.job_id));
    wcar.write_to_path(&output_path)?;

    Ok(())
}

//
// CLI arguments.
//
struct Args {
    input: PathBuf,
    output: PathBuf,
}

fn parse_args() -> Args {
    let mut input = None;
    let mut output = None;

    let mut iter = std::env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--input" => input = iter.next().map(PathBuf::from),
            "--output" => output = iter.next().map(PathBuf::from),
            _ => {}
        }
    }

    let input = input.expect("--input is required");
    let output = output.expect("--output is required");

    Args { input, output }
}

//
// Load world payload JSON.
//
fn load_payload(path: &PathBuf) -> Result<WorldPayload, WcarError> {
    let raw = fs::read_to_string(path).map_err(WcarError::Io)?;
    let payload: WorldPayload = serde_json::from_str(&raw)
        .map_err(|err| WcarError::InvalidFormat(format!("Invalid world payload: {}", err)))?;
    Ok(payload)
}

//
// Build TILE chunk from world payload tiles.
//
fn build_tile_chunk(width: u32, height: u32, tiles: &[WorldTile]) -> TileChunk {
    let mut terrain_names: Vec<String> = tiles.iter().map(|t| t.terrain.clone()).collect();
    terrain_names.sort();
    terrain_names.dedup();

    let mut tile_defs = Vec::new();
    for (index, name) in terrain_names.iter().enumerate() {
        tile_defs.push(TileTypeDef {
            tile_id: index as u16,
            tile_name: name.clone(),
        });
    }

    let mut tile_map = vec![0u16; (width * height) as usize];
    for tile in tiles {
        let index = (tile.y * width + tile.x) as usize;
        if let Some((id, _)) = tile_defs
            .iter()
            .find(|def| def.tile_name == tile.terrain)
            .map(|def| (def.tile_id, def.tile_name.clone()))
        {
            if index < tile_map.len() {
                tile_map[index] = id;
            }
        }
    }

    TileChunk { tile_defs, tile_map }
}

//
// Parse a UUID string into a u128.
//
// Assumes standard 8-4-4-4-12 formatting.
//
fn parse_uuid(value: &str) -> Option<u128> {
    let hex: String = value.chars().filter(|c| *c != '-').collect();
    if hex.len() != 32 {
        return None;
    }

    let mut bytes = [0u8; 16];
    for i in 0..16 {
        let slice = &hex[i * 2..i * 2 + 2];
        let byte = u8::from_str_radix(slice, 16).ok()?;
        bytes[i] = byte;
    }

    Some(u128::from_be_bytes(bytes))
}
