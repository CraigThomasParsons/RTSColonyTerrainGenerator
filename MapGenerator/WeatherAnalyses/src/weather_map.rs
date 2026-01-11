use anyhow::{Context, Result};
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

pub const MAGIC: u32 = 0x57414E41; // "WANA" (Weather ANAlyses) - Made up for now, spec didn't specify value constant
pub const VERSION: u16 = 1;

#[derive(Debug)]
pub struct WeatherMap {
    pub width: u32,
    pub height: u32,
    pub slope: Vec<i16>,     // Layer 1
    pub flow: Vec<u8>,       // Layer 2
    pub basin: Vec<u32>,     // Layer 3
}

impl WeatherMap {
    pub fn new(width: u32, height: u32) -> Self {
        let size = (width * height) as usize;
        Self {
            width,
            height,
            slope: vec![0; size],
            flow: vec![0; size],
            basin: vec![0; size],
        }
    }

    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let path = path.as_ref();
        let file = File::create(path).with_context(|| format!("Failed to create output file: {:?}", path))?;
        let mut writer = BufWriter::new(file);

        // Header
        // magic: u32
        // version: u16
        // width: u32
        // height: u32
        // layer_count: u16
        
        writer.write_all(&MAGIC.to_le_bytes())?;
        writer.write_all(&VERSION.to_le_bytes())?;
        writer.write_all(&self.width.to_le_bytes())?;
        writer.write_all(&self.height.to_le_bytes())?;
        
        let layer_count: u16 = 3;
        writer.write_all(&layer_count.to_le_bytes())?;

        // Layer 1: Slope (i16)
        for &val in &self.slope {
            writer.write_all(&val.to_le_bytes())?;
        }

        // Layer 2: Flow (u8)
        writer.write_all(&self.flow)?;

        // Layer 3: Basin (u32)
        for &val in &self.basin {
            writer.write_all(&val.to_le_bytes())?;
        }

        writer.flush()?;
        Ok(())
    }
}
