use std::fs;
use std::path::PathBuf;

use serde::Deserialize;

use wcar::format::TileChunk;
use wcar::{read_wcar, WcarError};

//
// Tileset metadata for StarCraft I.
//
const TILESET_IDS: [(&str, u16); 8] = [
    ("badlands", 0),
    ("space_platform", 1),
    ("installation", 2),
    ("ashworld", 3),
    ("jungle", 4),
    ("desert", 5),
    ("ice", 6),
    ("twilight", 7),
];

//
// Mapping file schema.
//
#[derive(Debug, Deserialize)]
struct TileMapConfig {
    tileset: String,
    default_tile: u16,
    terrain_to_tile: std::collections::HashMap<String, u16>,
}

//
// Entry point for CHK export.
//
// This program:
// - Loads a WCAR file
// - Projects WCAR TILE data to MTXM
// - Writes CHK or SCX/SCM output
//
fn main() -> Result<(), WcarError> {
    let args = parse_args();
    let wcar_file = read_wcar(&args.input)?;

    let chk_bytes = if let Some(chk) = wcar_file.chk.as_ref() {
        chk.chk_data.clone()
    } else {
        let tile_chunk = wcar_file
            .tile
            .as_ref()
            .ok_or_else(|| WcarError::InvalidFormat("Missing TILE chunk".to_string()))?;
        build_chk(&wcar_file, tile_chunk, &args.tileset_map)?
    };

    if args.output.extension().and_then(|s| s.to_str()).unwrap_or("") == "chk" {
        fs::write(&args.output, &chk_bytes).map_err(WcarError::Io)?;
    } else {
        let mpq_bytes = build_mpq_archive(&chk_bytes);
        fs::write(&args.output, &mpq_bytes).map_err(WcarError::Io)?;
    }

    Ok(())
}

//
// CLI arguments.
//
struct Args {
    input: PathBuf,
    output: PathBuf,
    tileset_map: PathBuf,
}

fn parse_args() -> Args {
    let mut input = None;
    let mut output = None;
    let mut tileset_map = None;

    let mut iter = std::env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--input" => input = iter.next().map(PathBuf::from),
            "--output" => output = iter.next().map(PathBuf::from),
            "--tileset-map" => tileset_map = iter.next().map(PathBuf::from),
            _ => {}
        }
    }

    let input = input.expect("--input is required");
    let output = output.expect("--output is required");
    let tileset_map = tileset_map.unwrap_or_else(|| PathBuf::from("tileset_mappings/default_badlands.json"));

    Args {
        input,
        output,
        tileset_map,
    }
}

//
// Build a CHK binary from WCAR TILE data.
//
fn build_chk(wcar_file: &wcar::WcarFile, tile_chunk: &TileChunk, map_path: &PathBuf) -> Result<Vec<u8>, WcarError> {
    let config = load_tile_map(map_path)?;
    let tileset_id = TILESET_IDS
        .iter()
        .find(|(name, _)| *name == config.tileset)
        .map(|(_, id)| *id)
        .unwrap_or(0);

    let width = wcar_file.head.width_tiles;
    let height = wcar_file.head.height_tiles;
    let expected_tiles = (width * height) as usize;
    if tile_chunk.tile_map.len() != expected_tiles {
        return Err(WcarError::InvalidFormat(format!(
            "Tile map size mismatch: expected {}, got {}",
            expected_tiles,
            tile_chunk.tile_map.len()
        )));
    }

    let mut tile_grid = vec![config.default_tile; expected_tiles];

    for (index, tile_id) in tile_chunk.tile_map.iter().enumerate() {
        let terrain_name = tile_chunk
            .tile_defs
            .iter()
            .find(|def| def.tile_id == *tile_id)
            .map(|def| def.tile_name.clone());

        let mapped = terrain_name
            .as_ref()
            .and_then(|name| config.terrain_to_tile.get(name))
            .copied()
            .unwrap_or(config.default_tile);

        if index < tile_grid.len() {
            tile_grid[index] = mapped;
        }
    }

    Ok(build_chk_binary(width as u16, height as u16, tileset_id, &tile_grid))
}

fn load_tile_map(path: &PathBuf) -> Result<TileMapConfig, WcarError> {
    let raw = fs::read_to_string(path).map_err(WcarError::Io)?;
    let config: TileMapConfig = serde_json::from_str(&raw)
        .map_err(|err| WcarError::InvalidFormat(format!("Invalid tileset mapping: {}", err)))?;
    Ok(config)
}

//
// Build a minimal CHK binary with core sections.
//
fn build_chk_binary(width: u16, height: u16, tileset_id: u16, tiles: &[u16]) -> Vec<u8> {
    let mut sections = Vec::new();

    sections.extend(pack_section("TYPE", &map_type_section()));
    sections.extend(pack_section("VER ", &version_section()));
    sections.extend(pack_section("IVER", &0u16.to_le_bytes()));
    sections.extend(pack_section("IVE2", &0u16.to_le_bytes()));
    sections.extend(pack_section("ERA ", &tileset_id.to_le_bytes()));
    sections.extend(pack_section("DIM ", &dim_section(width, height)));
    sections.extend(pack_section("MTXM", &mtxm_section(tiles)));

    sections
}

fn map_type_section() -> [u8; 2] {
    2u16.to_le_bytes()
}

fn version_section() -> [u8; 2] {
    33u16.to_le_bytes()
}

fn dim_section(width: u16, height: u16) -> Vec<u8> {
    let mut data = Vec::new();
    data.extend_from_slice(&width.to_le_bytes());
    data.extend_from_slice(&height.to_le_bytes());
    data
}

fn mtxm_section(tiles: &[u16]) -> Vec<u8> {
    let mut data = Vec::with_capacity(tiles.len() * 2);
    for tile in tiles {
        data.extend_from_slice(&tile.to_le_bytes());
    }
    data
}

fn pack_section(name: &str, data: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(name.as_bytes());
    out.extend_from_slice(&(data.len() as u32).to_le_bytes());
    out.extend_from_slice(data);
    out
}

//
// Minimal MPQ builder for .scm/.scx.
//
fn build_mpq_archive(chk_data: &[u8]) -> Vec<u8> {
    let header_size = 32u32;
    let sector_shift = 3u16; // 512 << 3 = 4096
    let hash_entries = 1u32;
    let block_entries = 1u32;

    let data_offset = header_size as usize;
    let data_size = chk_data.len();
    let hash_table_offset = data_offset + data_size;
    let block_table_offset = hash_table_offset + 16;
    let archive_size = block_table_offset + 16;

    let mut bytes = Vec::new();
    bytes.extend_from_slice(b"MPQ\x1a");
    bytes.extend_from_slice(&header_size.to_le_bytes());
    bytes.extend_from_slice(&(archive_size as u32).to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    bytes.extend_from_slice(&sector_shift.to_le_bytes());
    bytes.extend_from_slice(&(hash_table_offset as u32).to_le_bytes());
    bytes.extend_from_slice(&(block_table_offset as u32).to_le_bytes());
    bytes.extend_from_slice(&hash_entries.to_le_bytes());
    bytes.extend_from_slice(&block_entries.to_le_bytes());

    bytes.extend_from_slice(chk_data);

    let file_name = "staredit\\scenario.chk";
    let hash_a = hash_string(file_name, 1);
    let hash_b = hash_string(file_name, 2);

    bytes.extend_from_slice(&hash_a.to_le_bytes());
    bytes.extend_from_slice(&hash_b.to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    bytes.extend_from_slice(&0u32.to_le_bytes());

    let block_flags = 0x80000000u32 | 0x01000000u32;
    bytes.extend_from_slice(&(data_offset as u32).to_le_bytes());
    bytes.extend_from_slice(&(data_size as u32).to_le_bytes());
    bytes.extend_from_slice(&(data_size as u32).to_le_bytes());
    bytes.extend_from_slice(&block_flags.to_le_bytes());

    bytes
}

fn hash_string(name: &str, hash_type: u32) -> u32 {
    let crypt_table = build_crypt_table();
    let mut seed1 = 0x7FED7FEDu32;
    let mut seed2 = 0xEEEEEEEEu32;

    for ch in name.bytes() {
        let value = ch.to_ascii_uppercase() as usize;
        let index = (hash_type << 8) as usize + value;
        seed1 = crypt_table[index] ^ (seed1.wrapping_add(seed2));
        seed2 = (value as u32)
            .wrapping_add(seed1)
            .wrapping_add(seed2)
            .wrapping_add(seed2 << 5)
            .wrapping_add(3);
    }

    seed1
}

fn build_crypt_table() -> [u32; 0x500] {
    let mut table = [0u32; 0x500];
    let mut seed = 0x00100001u32;

    for index in 0..0x100u32 {
        for i in 0..5u32 {
            seed = seed.wrapping_mul(125).wrapping_add(3) % 0x2AAAAB;
            let temp1 = (seed & 0xFFFF) << 16;
            seed = seed.wrapping_mul(125).wrapping_add(3) % 0x2AAAAB;
            let temp2 = seed & 0xFFFF;
            table[(i * 0x100 + index) as usize] = temp1 | temp2;
        }
    }

    table
}
