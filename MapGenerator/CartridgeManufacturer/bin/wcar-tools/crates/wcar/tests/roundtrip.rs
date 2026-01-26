use wcar::format::{HeadChunk, ProvChunk, ProvEntry, TileChunk, TileTypeDef};
use wcar::WcarFile;

#[test]
fn wcar_roundtrip_head_and_tile() {
    let head = HeadChunk {
        magic: *b"WCAR",
        major_version: 0,
        minor_version: 2,
        world_uuid: 1,
        created_unix_ts: 1,
        width_tiles: 2,
        height_tiles: 2,
        tile_world_size: 1.0,
        vertical_scale: 1.0,
        declared_chunk_mask: 0,
    };

    let prov = ProvChunk {
        entries: vec![ProvEntry {
            stage_name: "Test".to_string(),
            stage_version: "0.0".to_string(),
            start_ts: 0,
            end_ts: 0,
            input_hash: 0,
            output_hash: 0,
        }],
    };

    let tile = TileChunk {
        tile_defs: vec![TileTypeDef {
            tile_id: 0,
            tile_name: "grass".to_string(),
        }],
        tile_map: vec![0, 0, 0, 0],
    };

    let wcar = WcarFile {
        head,
        prov,
        seed: None,
        hmap: None,
        tile: Some(tile),
        biom: None,
        feat: None,
        path: None,
        navi: None,
        chk: None,
        unknown_chunks: Vec::new(),
    };

    let bytes = wcar.to_bytes().expect("serialize");
    let parsed = wcar::read_wcar_bytes(&bytes).expect("parse");

    assert_eq!(parsed.head.width_tiles, 2);
    assert_eq!(parsed.head.height_tiles, 2);
    assert_eq!(parsed.prov.entries.len(), 1);
    assert!(parsed.tile.is_some());
}
