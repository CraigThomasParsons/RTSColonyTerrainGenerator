use std::convert::TryFrom;
use std::fmt;

use super::WcarError;

//
// WCAR chunk tags.
//
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChunkTag {
    HEAD,
    SEED,
    PROV,
    HMAP,
    TILE,
    BIOM,
    FEAT,
    PATH,
    NAVI,
    CHK0,
    EXTX,
    UNKNOWN,
}

impl ChunkTag {
    pub fn from_bytes(bytes: [u8; 4]) -> Self {
        match &bytes {
            b"HEAD" => ChunkTag::HEAD,
            b"SEED" => ChunkTag::SEED,
            b"PROV" => ChunkTag::PROV,
            b"HMAP" => ChunkTag::HMAP,
            b"TILE" => ChunkTag::TILE,
            b"BIOM" => ChunkTag::BIOM,
            b"FEAT" => ChunkTag::FEAT,
            b"PATH" => ChunkTag::PATH,
            b"NAVI" => ChunkTag::NAVI,
            b"CHK0" => ChunkTag::CHK0,
            [b'X', _, _, _] => ChunkTag::EXTX,
            _ => ChunkTag::UNKNOWN,
        }
    }

    pub fn to_bytes(self) -> [u8; 4] {
        match self {
            ChunkTag::HEAD => *b"HEAD",
            ChunkTag::SEED => *b"SEED",
            ChunkTag::PROV => *b"PROV",
            ChunkTag::HMAP => *b"HMAP",
            ChunkTag::TILE => *b"TILE",
            ChunkTag::BIOM => *b"BIOM",
            ChunkTag::FEAT => *b"FEAT",
            ChunkTag::PATH => *b"PATH",
            ChunkTag::NAVI => *b"NAVI",
            ChunkTag::CHK0 => *b"CHK0",
            ChunkTag::EXTX => *b"EXTX",
            ChunkTag::UNKNOWN => *b"UNKN",
        }
    }
}

//
// A raw chunk as stored in WCAR.
//
#[derive(Debug, Clone)]
pub struct Chunk {
    pub tag: ChunkTag,
    pub raw_tag: [u8; 4],
    pub data: Vec<u8>,
}

impl Chunk {
    pub fn read_from(buffer: &[u8], offset: usize) -> Result<(Self, usize), WcarError> {
        if buffer.len() < offset + 8 {
            return Err(WcarError::InvalidFormat("Chunk header truncated".to_string()));
        }
        let raw_tag = <[u8; 4]>::try_from(&buffer[offset..offset + 4])
            .map_err(|_| WcarError::InvalidFormat("Invalid chunk tag".to_string()))?;
        let length = u32::from_le_bytes(
            buffer[offset + 4..offset + 8]
                .try_into()
                .map_err(|_| WcarError::InvalidFormat("Invalid chunk length".to_string()))?,
        ) as usize;

        let start = offset + 8;
        let end = start + length;
        if buffer.len() < end {
            return Err(WcarError::InvalidFormat("Chunk data truncated".to_string()));
        }

        let data = buffer[start..end].to_vec();
        let tag = ChunkTag::from_bytes(raw_tag);

        Ok((Chunk { tag, raw_tag, data }, end))
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(8 + self.data.len());
        let tag_bytes = self.raw_tag;
        out.extend_from_slice(&tag_bytes);
        out.extend_from_slice(&(self.data.len() as u32).to_le_bytes());
        out.extend_from_slice(&self.data);
        out
    }
}

//
// HEAD chunk.
//
#[derive(Debug, Clone)]
pub struct HeadChunk {
    pub magic: [u8; 4],
    pub major_version: u16,
    pub minor_version: u16,
    pub world_uuid: u128,
    pub created_unix_ts: u64,
    pub width_tiles: u32,
    pub height_tiles: u32,
    pub tile_world_size: f32,
    pub vertical_scale: f32,
    pub declared_chunk_mask: u32,
}

impl HeadChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        if chunk.data.len() < 4 + 2 + 2 + 16 + 8 + 4 + 4 + 4 + 4 + 4 {
            return Err(WcarError::InvalidFormat("HEAD chunk too small".to_string()));
        }
        let mut offset = 0usize;
        let magic = <[u8; 4]>::try_from(&chunk.data[offset..offset + 4])
            .map_err(|_| WcarError::InvalidFormat("Invalid HEAD magic".to_string()))?;
        offset += 4;
        let major_version = read_u16(&chunk.data, &mut offset)?;
        let minor_version = read_u16(&chunk.data, &mut offset)?;
        let world_uuid = read_u128(&chunk.data, &mut offset)?;
        let created_unix_ts = read_u64(&chunk.data, &mut offset)?;
        let width_tiles = read_u32(&chunk.data, &mut offset)?;
        let height_tiles = read_u32(&chunk.data, &mut offset)?;
        let tile_world_size = read_f32(&chunk.data, &mut offset)?;
        let vertical_scale = read_f32(&chunk.data, &mut offset)?;
        let declared_chunk_mask = read_u32(&chunk.data, &mut offset)?;

        Ok(HeadChunk {
            magic,
            major_version,
            minor_version,
            world_uuid,
            created_unix_ts,
            width_tiles,
            height_tiles,
            tile_world_size,
            vertical_scale,
            declared_chunk_mask,
        })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&self.magic);
        data.extend_from_slice(&self.major_version.to_le_bytes());
        data.extend_from_slice(&self.minor_version.to_le_bytes());
        data.extend_from_slice(&self.world_uuid.to_le_bytes());
        data.extend_from_slice(&self.created_unix_ts.to_le_bytes());
        data.extend_from_slice(&self.width_tiles.to_le_bytes());
        data.extend_from_slice(&self.height_tiles.to_le_bytes());
        data.extend_from_slice(&self.tile_world_size.to_le_bytes());
        data.extend_from_slice(&self.vertical_scale.to_le_bytes());
        data.extend_from_slice(&self.declared_chunk_mask.to_le_bytes());

        Chunk {
            tag: ChunkTag::HEAD,
            raw_tag: *b"HEAD",
            data,
        }
    }
}

//
// PROV chunk.
//
#[derive(Debug, Clone)]
pub struct ProvEntry {
    pub stage_name: String,
    pub stage_version: String,
    pub start_ts: u64,
    pub end_ts: u64,
    pub input_hash: u64,
    pub output_hash: u64,
}

#[derive(Debug, Clone)]
pub struct ProvChunk {
    pub entries: Vec<ProvEntry>,
}

impl ProvChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let count = read_u32(&chunk.data, &mut offset)? as usize;
        let mut entries = Vec::with_capacity(count);

        for _ in 0..count {
            let stage_name = read_fixed_string(&chunk.data, &mut offset, 32)?;
            let stage_version = read_fixed_string(&chunk.data, &mut offset, 32)?;
            let start_ts = read_u64(&chunk.data, &mut offset)?;
            let end_ts = read_u64(&chunk.data, &mut offset)?;
            let input_hash = read_u64(&chunk.data, &mut offset)?;
            let output_hash = read_u64(&chunk.data, &mut offset)?;

            entries.push(ProvEntry {
                stage_name,
                stage_version,
                start_ts,
                end_ts,
                input_hash,
                output_hash,
            });
        }

        Ok(ProvChunk { entries })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.entries.len() as u32).to_le_bytes());

        for entry in &self.entries {
            write_fixed_string(&mut data, &entry.stage_name, 32);
            write_fixed_string(&mut data, &entry.stage_version, 32);
            data.extend_from_slice(&entry.start_ts.to_le_bytes());
            data.extend_from_slice(&entry.end_ts.to_le_bytes());
            data.extend_from_slice(&entry.input_hash.to_le_bytes());
            data.extend_from_slice(&entry.output_hash.to_le_bytes());
        }

        Chunk {
            tag: ChunkTag::PROV,
            raw_tag: *b"PROV",
            data,
        }
    }
}

//
// SEED chunk.
//
#[derive(Debug, Clone)]
pub struct SeedEntry {
    pub name: String,
    pub seed_value: u64,
}

#[derive(Debug, Clone)]
pub struct SeedChunk {
    pub entries: Vec<SeedEntry>,
}

impl SeedChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let count = read_u32(&chunk.data, &mut offset)? as usize;
        let mut entries = Vec::with_capacity(count);

        for _ in 0..count {
            let name = read_fixed_string(&chunk.data, &mut offset, 32)?;
            let seed_value = read_u64(&chunk.data, &mut offset)?;
            entries.push(SeedEntry { name, seed_value });
        }

        Ok(SeedChunk { entries })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.entries.len() as u32).to_le_bytes());
        for entry in &self.entries {
            write_fixed_string(&mut data, &entry.name, 32);
            data.extend_from_slice(&entry.seed_value.to_le_bytes());
        }

        Chunk {
            tag: ChunkTag::SEED,
            raw_tag: *b"SEED",
            data,
        }
    }
}

//
// HMAP chunk.
//
#[derive(Debug, Clone)]
pub struct HmapChunk {
    pub width: u32,
    pub height: u32,
    pub min_height: f32,
    pub max_height: f32,
    pub height_values: Vec<f32>,
}

impl HmapChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let width = read_u32(&chunk.data, &mut offset)?;
        let height = read_u32(&chunk.data, &mut offset)?;
        let min_height = read_f32(&chunk.data, &mut offset)?;
        let max_height = read_f32(&chunk.data, &mut offset)?;
        let expected = (width as usize) * (height as usize);

        let mut height_values = Vec::with_capacity(expected);
        for _ in 0..expected {
            height_values.push(read_f32(&chunk.data, &mut offset)?);
        }

        Ok(HmapChunk {
            width,
            height,
            min_height,
            max_height,
            height_values,
        })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&self.width.to_le_bytes());
        data.extend_from_slice(&self.height.to_le_bytes());
        data.extend_from_slice(&self.min_height.to_le_bytes());
        data.extend_from_slice(&self.max_height.to_le_bytes());
        for value in &self.height_values {
            data.extend_from_slice(&value.to_le_bytes());
        }

        Chunk {
            tag: ChunkTag::HMAP,
            raw_tag: *b"HMAP",
            data,
        }
    }
}

//
// TILE chunk.
//
#[derive(Debug, Clone)]
pub struct TileTypeDef {
    pub tile_id: u16,
    pub tile_name: String,
}

#[derive(Debug, Clone)]
pub struct TileChunk {
    pub tile_defs: Vec<TileTypeDef>,
    pub tile_map: Vec<u16>,
}

impl TileChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let tile_type_count = read_u16(&chunk.data, &mut offset)? as usize;
        let mut tile_defs = Vec::with_capacity(tile_type_count);

        for _ in 0..tile_type_count {
            let tile_id = read_u16(&chunk.data, &mut offset)?;
            let tile_name = read_fixed_string(&chunk.data, &mut offset, 32)?;
            tile_defs.push(TileTypeDef { tile_id, tile_name });
        }

        let mut tile_map = Vec::new();
        while offset < chunk.data.len() {
            tile_map.push(read_u16(&chunk.data, &mut offset)?);
        }

        Ok(TileChunk { tile_defs, tile_map })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.tile_defs.len() as u16).to_le_bytes());
        for def in &self.tile_defs {
            data.extend_from_slice(&def.tile_id.to_le_bytes());
            write_fixed_string(&mut data, &def.tile_name, 32);
        }
        for tile_id in &self.tile_map {
            data.extend_from_slice(&tile_id.to_le_bytes());
        }

        Chunk {
            tag: ChunkTag::TILE,
            raw_tag: *b"TILE",
            data,
        }
    }
}

//
// BIOM chunk.
//
#[derive(Debug, Clone)]
pub struct BiomeDef {
    pub biome_id: u16,
    pub biome_name: String,
    pub biome_flags: u32,
}

#[derive(Debug, Clone)]
pub struct BiomChunk {
    pub biome_defs: Vec<BiomeDef>,
    pub biome_map: Vec<u16>,
}

impl BiomChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let biome_count = read_u16(&chunk.data, &mut offset)? as usize;
        let mut biome_defs = Vec::with_capacity(biome_count);

        for _ in 0..biome_count {
            let biome_id = read_u16(&chunk.data, &mut offset)?;
            let biome_name = read_fixed_string(&chunk.data, &mut offset, 32)?;
            let biome_flags = read_u32(&chunk.data, &mut offset)?;
            biome_defs.push(BiomeDef {
                biome_id,
                biome_name,
                biome_flags,
            });
        }

        let mut biome_map = Vec::new();
        while offset < chunk.data.len() {
            biome_map.push(read_u16(&chunk.data, &mut offset)?);
        }

        Ok(BiomChunk { biome_defs, biome_map })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.biome_defs.len() as u16).to_le_bytes());
        for def in &self.biome_defs {
            data.extend_from_slice(&def.biome_id.to_le_bytes());
            write_fixed_string(&mut data, &def.biome_name, 32);
            data.extend_from_slice(&def.biome_flags.to_le_bytes());
        }
        for biome_id in &self.biome_map {
            data.extend_from_slice(&biome_id.to_le_bytes());
        }

        Chunk {
            tag: ChunkTag::BIOM,
            raw_tag: *b"BIOM",
            data,
        }
    }
}

//
// FEAT chunk.
//
#[derive(Debug, Clone)]
pub struct FeatureEntry {
    pub feature_id: u32,
    pub feature_type: u16,
    pub x: u32,
    pub y: u32,
    pub elevation: f32,
    pub metadata: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct FeatChunk {
    pub features: Vec<FeatureEntry>,
}

impl FeatChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let count = read_u32(&chunk.data, &mut offset)? as usize;
        let mut features = Vec::with_capacity(count);

        for _ in 0..count {
            let feature_id = read_u32(&chunk.data, &mut offset)?;
            let feature_type = read_u16(&chunk.data, &mut offset)?;
            let x = read_u32(&chunk.data, &mut offset)?;
            let y = read_u32(&chunk.data, &mut offset)?;
            let elevation = read_f32(&chunk.data, &mut offset)?;
            let metadata_len = read_u32(&chunk.data, &mut offset)? as usize;

            if offset + metadata_len > chunk.data.len() {
                return Err(WcarError::InvalidFormat("FEAT metadata truncated".to_string()));
            }
            let metadata = chunk.data[offset..offset + metadata_len].to_vec();
            offset += metadata_len;

            features.push(FeatureEntry {
                feature_id,
                feature_type,
                x,
                y,
                elevation,
                metadata,
            });
        }

        Ok(FeatChunk { features })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.features.len() as u32).to_le_bytes());
        for feature in &self.features {
            data.extend_from_slice(&feature.feature_id.to_le_bytes());
            data.extend_from_slice(&feature.feature_type.to_le_bytes());
            data.extend_from_slice(&feature.x.to_le_bytes());
            data.extend_from_slice(&feature.y.to_le_bytes());
            data.extend_from_slice(&feature.elevation.to_le_bytes());
            data.extend_from_slice(&(feature.metadata.len() as u32).to_le_bytes());
            data.extend_from_slice(&feature.metadata);
        }

        Chunk {
            tag: ChunkTag::FEAT,
            raw_tag: *b"FEAT",
            data,
        }
    }
}

//
// PATH chunk.
//
#[derive(Debug, Clone)]
pub struct PathNode {
    pub x: u32,
    pub y: u32,
}

#[derive(Debug, Clone)]
pub struct PathEntry {
    pub path_id: u32,
    pub path_type: u8,
    pub nodes: Vec<PathNode>,
}

#[derive(Debug, Clone)]
pub struct PathChunk {
    pub paths: Vec<PathEntry>,
}

impl PathChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let count = read_u32(&chunk.data, &mut offset)? as usize;
        let mut paths = Vec::with_capacity(count);

        for _ in 0..count {
            let path_id = read_u32(&chunk.data, &mut offset)?;
            let path_type = read_u8(&chunk.data, &mut offset)?;
            let node_count = read_u32(&chunk.data, &mut offset)? as usize;
            let mut nodes = Vec::with_capacity(node_count);

            for _ in 0..node_count {
                let x = read_u32(&chunk.data, &mut offset)?;
                let y = read_u32(&chunk.data, &mut offset)?;
                nodes.push(PathNode { x, y });
            }

            paths.push(PathEntry {
                path_id,
                path_type,
                nodes,
            });
        }

        Ok(PathChunk { paths })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.paths.len() as u32).to_le_bytes());
        for path in &self.paths {
            data.extend_from_slice(&path.path_id.to_le_bytes());
            data.push(path.path_type);
            data.extend_from_slice(&(path.nodes.len() as u32).to_le_bytes());
            for node in &path.nodes {
                data.extend_from_slice(&node.x.to_le_bytes());
                data.extend_from_slice(&node.y.to_le_bytes());
            }
        }

        Chunk {
            tag: ChunkTag::PATH,
            raw_tag: *b"PATH",
            data,
        }
    }
}

//
// NAVI chunk.
//
#[derive(Debug, Clone)]
pub struct NaviEntry {
    pub region_id: u32,
    pub region_flags: u32,
}

#[derive(Debug, Clone)]
pub struct NaviChunk {
    pub regions: Vec<NaviEntry>,
}

impl NaviChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let count = read_u32(&chunk.data, &mut offset)? as usize;
        let mut regions = Vec::with_capacity(count);

        for _ in 0..count {
            let region_id = read_u32(&chunk.data, &mut offset)?;
            let region_flags = read_u32(&chunk.data, &mut offset)?;
            regions.push(NaviEntry { region_id, region_flags });
        }

        Ok(NaviChunk { regions })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&(self.regions.len() as u32).to_le_bytes());
        for region in &self.regions {
            data.extend_from_slice(&region.region_id.to_le_bytes());
            data.extend_from_slice(&region.region_flags.to_le_bytes());
        }

        Chunk {
            tag: ChunkTag::NAVI,
            raw_tag: *b"NAVI",
            data,
        }
    }
}

//
// CHK0 chunk.
//
#[derive(Debug, Clone)]
pub struct ChkChunk {
    pub format_version: u32,
    pub chk_data: Vec<u8>,
}

impl ChkChunk {
    pub fn from_chunk(chunk: &Chunk) -> Result<Self, WcarError> {
        let mut offset = 0usize;
        let format_version = read_u32(&chunk.data, &mut offset)?;
        let chk_length = read_u32(&chunk.data, &mut offset)? as usize;
        if offset + chk_length > chunk.data.len() {
            return Err(WcarError::InvalidFormat("CHK0 data truncated".to_string()));
        }
        let chk_data = chunk.data[offset..offset + chk_length].to_vec();
        Ok(ChkChunk {
            format_version,
            chk_data,
        })
    }

    pub fn to_chunk(&self) -> Chunk {
        let mut data = Vec::new();
        data.extend_from_slice(&self.format_version.to_le_bytes());
        data.extend_from_slice(&(self.chk_data.len() as u32).to_le_bytes());
        data.extend_from_slice(&self.chk_data);

        Chunk {
            tag: ChunkTag::CHK0,
            raw_tag: *b"CHK0",
            data,
        }
    }
}

//
// Binary helpers.
//
fn read_u8(buffer: &[u8], offset: &mut usize) -> Result<u8, WcarError> {
    if *offset + 1 > buffer.len() {
        return Err(WcarError::InvalidFormat("u8 read overflow".to_string()));
    }
    let value = buffer[*offset];
    *offset += 1;
    Ok(value)
}

fn read_u16(buffer: &[u8], offset: &mut usize) -> Result<u16, WcarError> {
    if *offset + 2 > buffer.len() {
        return Err(WcarError::InvalidFormat("u16 read overflow".to_string()));
    }
    let value = u16::from_le_bytes(buffer[*offset..*offset + 2].try_into().unwrap());
    *offset += 2;
    Ok(value)
}

fn read_u32(buffer: &[u8], offset: &mut usize) -> Result<u32, WcarError> {
    if *offset + 4 > buffer.len() {
        return Err(WcarError::InvalidFormat("u32 read overflow".to_string()));
    }
    let value = u32::from_le_bytes(buffer[*offset..*offset + 4].try_into().unwrap());
    *offset += 4;
    Ok(value)
}

fn read_u64(buffer: &[u8], offset: &mut usize) -> Result<u64, WcarError> {
    if *offset + 8 > buffer.len() {
        return Err(WcarError::InvalidFormat("u64 read overflow".to_string()));
    }
    let value = u64::from_le_bytes(buffer[*offset..*offset + 8].try_into().unwrap());
    *offset += 8;
    Ok(value)
}

fn read_u128(buffer: &[u8], offset: &mut usize) -> Result<u128, WcarError> {
    if *offset + 16 > buffer.len() {
        return Err(WcarError::InvalidFormat("u128 read overflow".to_string()));
    }
    let value = u128::from_le_bytes(buffer[*offset..*offset + 16].try_into().unwrap());
    *offset += 16;
    Ok(value)
}

fn read_f32(buffer: &[u8], offset: &mut usize) -> Result<f32, WcarError> {
    if *offset + 4 > buffer.len() {
        return Err(WcarError::InvalidFormat("f32 read overflow".to_string()));
    }
    let value = f32::from_le_bytes(buffer[*offset..*offset + 4].try_into().unwrap());
    *offset += 4;
    Ok(value)
}

fn read_fixed_string(buffer: &[u8], offset: &mut usize, length: usize) -> Result<String, WcarError> {
    if *offset + length > buffer.len() {
        return Err(WcarError::InvalidFormat("fixed string read overflow".to_string()));
    }
    let bytes = &buffer[*offset..*offset + length];
    *offset += length;
    let end = bytes.iter().position(|b| *b == 0).unwrap_or(length);
    let text = String::from_utf8_lossy(&bytes[..end]).to_string();
    Ok(text)
}

fn write_fixed_string(buffer: &mut Vec<u8>, value: &str, length: usize) {
    let mut bytes = vec![0u8; length];
    let value_bytes = value.as_bytes();
    let copy_len = value_bytes.len().min(length);
    bytes[..copy_len].copy_from_slice(&value_bytes[..copy_len]);
    buffer.extend_from_slice(&bytes);
}

impl fmt::Display for WcarError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WcarError::Io(err) => write!(f, "IO error: {}", err),
            WcarError::InvalidFormat(msg) => write!(f, "Invalid format: {}", msg),
        }
    }
}
