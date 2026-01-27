use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

pub mod format;

use format::{
    Chunk, ChunkTag, HeadChunk, ProvChunk, SeedChunk, HmapChunk, TileChunk, BiomChunk, FeatChunk,
    PathChunk, NaviChunk, ChkChunk,
};

//
// Error type for WCAR parsing and writing.
//
// This keeps failure modes explicit and traceable.
//
#[derive(Debug)]
pub enum WcarError {
    Io(std::io::Error),
    InvalidFormat(String),
}

impl From<std::io::Error> for WcarError {
    fn from(err: std::io::Error) -> Self {
        WcarError::Io(err)
    }
}

//
// A parsed WCAR file with typed access to known chunks.
//
// Unknown chunks are preserved in `unknown_chunks` for forward compatibility.
//
pub struct WcarFile {
    pub head: HeadChunk,
    pub prov: ProvChunk,
    pub seed: Option<SeedChunk>,
    pub hmap: Option<HmapChunk>,
    pub tile: Option<TileChunk>,
    pub biom: Option<BiomChunk>,
    pub feat: Option<FeatChunk>,
    pub path: Option<PathChunk>,
    pub navi: Option<NaviChunk>,
    pub chk: Option<ChkChunk>,
    pub unknown_chunks: Vec<Chunk>,
}

impl WcarFile {
    //
    // Serialize the WCAR file to a byte vector.
    //
    pub fn to_bytes(&self) -> Result<Vec<u8>, WcarError> {
        let mut bytes = Vec::new();

        bytes.extend_from_slice(&self.head.to_chunk().to_bytes());
        bytes.extend_from_slice(&self.prov.to_chunk().to_bytes());

        if let Some(seed) = &self.seed {
            bytes.extend_from_slice(&seed.to_chunk().to_bytes());
        }
        if let Some(hmap) = &self.hmap {
            bytes.extend_from_slice(&hmap.to_chunk().to_bytes());
        }
        if let Some(tile) = &self.tile {
            bytes.extend_from_slice(&tile.to_chunk().to_bytes());
        }
        if let Some(biom) = &self.biom {
            bytes.extend_from_slice(&biom.to_chunk().to_bytes());
        }
        if let Some(feat) = &self.feat {
            bytes.extend_from_slice(&feat.to_chunk().to_bytes());
        }
        if let Some(path) = &self.path {
            bytes.extend_from_slice(&path.to_chunk().to_bytes());
        }
        if let Some(navi) = &self.navi {
            bytes.extend_from_slice(&navi.to_chunk().to_bytes());
        }
        if let Some(chk) = &self.chk {
            bytes.extend_from_slice(&chk.to_chunk().to_bytes());
        }

        for chunk in &self.unknown_chunks {
            bytes.extend_from_slice(&chunk.to_bytes());
        }

        Ok(bytes)
    }

    //
    // Write the WCAR file to disk.
    //
    pub fn write_to_path(&self, path: &Path) -> Result<(), WcarError> {
        let bytes = self.to_bytes()?;
        let mut file = File::create(path)?;
        file.write_all(&bytes)?;
        Ok(())
    }
}

//
// Parse a WCAR file from disk.
//
pub fn read_wcar(path: &Path) -> Result<WcarFile, WcarError> {
    let mut file = File::open(path)?;
    let mut buffer = Vec::new();
    file.read_to_end(&mut buffer)?;
    read_wcar_bytes(&buffer)
}

//
// Parse a WCAR file from bytes.
//
pub fn read_wcar_bytes(buffer: &[u8]) -> Result<WcarFile, WcarError> {
    let mut offset = 0usize;
    let mut head: Option<HeadChunk> = None;
    let mut prov: Option<ProvChunk> = None;
    let mut seed: Option<SeedChunk> = None;
    let mut hmap: Option<HmapChunk> = None;
    let mut tile: Option<TileChunk> = None;
    let mut biom: Option<BiomChunk> = None;
    let mut feat: Option<FeatChunk> = None;
    let mut path_chunk: Option<PathChunk> = None;
    let mut navi: Option<NaviChunk> = None;
    let mut chk: Option<ChkChunk> = None;
    let mut unknown = Vec::new();

    let mut saw_first_chunk = false;

    while offset < buffer.len() {
        let (chunk, next) = Chunk::read_from(buffer, offset)?;
        offset = next;

        if !saw_first_chunk {
            saw_first_chunk = true;
            if chunk.tag != ChunkTag::HEAD {
                return Err(WcarError::InvalidFormat("HEAD chunk must be first".to_string()));
            }
        }

        match chunk.tag {
            ChunkTag::HEAD => head = Some(HeadChunk::from_chunk(&chunk)?),
            ChunkTag::PROV => prov = Some(ProvChunk::from_chunk(&chunk)?),
            ChunkTag::SEED => seed = Some(SeedChunk::from_chunk(&chunk)?),
            ChunkTag::HMAP => hmap = Some(HmapChunk::from_chunk(&chunk)?),
            ChunkTag::TILE => tile = Some(TileChunk::from_chunk(&chunk)?),
            ChunkTag::BIOM => biom = Some(BiomChunk::from_chunk(&chunk)?),
            ChunkTag::FEAT => feat = Some(FeatChunk::from_chunk(&chunk)?),
            ChunkTag::PATH => path_chunk = Some(PathChunk::from_chunk(&chunk)?),
            ChunkTag::NAVI => navi = Some(NaviChunk::from_chunk(&chunk)?),
            ChunkTag::CHK0 => chk = Some(ChkChunk::from_chunk(&chunk)?),
            ChunkTag::EXTX => unknown.push(chunk),
            ChunkTag::UNKNOWN => unknown.push(chunk),
        }
    }

    let head = head.ok_or_else(|| WcarError::InvalidFormat("Missing HEAD chunk".to_string()))?;
    if &head.magic != b"WCAR" {
        return Err(WcarError::InvalidFormat("Invalid HEAD magic".to_string()));
    }
    if head.major_version != 0 || head.minor_version != 2 {
        return Err(WcarError::InvalidFormat("Unsupported WCAR version".to_string()));
    }
    let prov = prov.ok_or_else(|| WcarError::InvalidFormat("Missing PROV chunk".to_string()))?;

    if let Some(hmap) = &hmap {
        if hmap.width != head.width_tiles || hmap.height != head.height_tiles {
            return Err(WcarError::InvalidFormat("HMAP dimensions do not match HEAD".to_string()));
        }
    }

    if let Some(tile) = &tile {
        let expected = (head.width_tiles as usize) * (head.height_tiles as usize);
        if tile.tile_map.len() != expected {
            return Err(WcarError::InvalidFormat("TILE map length does not match HEAD".to_string()));
        }
    }

    if let Some(biom) = &biom {
        let expected = (head.width_tiles as usize) * (head.height_tiles as usize);
        if biom.biome_map.len() != expected {
            return Err(WcarError::InvalidFormat("BIOM map length does not match HEAD".to_string()));
        }
    }

    Ok(WcarFile {
        head,
        prov,
        seed,
        hmap,
        tile,
        biom,
        feat,
        path: path_chunk,
        navi,
        chk,
        unknown_chunks: unknown,
    })
}
