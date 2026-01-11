use anyhow::{ensure, Context, Result};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Heightmap {
    pub width: u32,
    pub height: u32,
    pub data: Vec<i16>, // Using i16 based on "signed height values" history, though u16 also possible.
}

impl Heightmap {
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref();
        let bytes = fs::read(path).with_context(|| format!("Failed to read heightmap: {:?}", path))?;

        ensure!(bytes.len() >= 16, "File too small to contain header");

        // Parse header
        let width = u32::from_le_bytes(bytes[0..4].try_into()?);
        let height = u32::from_le_bytes(bytes[4..8].try_into()?);
        
        // Next 8 bytes: 8..16 (Metadata/Seed - ignored)
        
        let header_size = 16;
        let expected_data_size = (width as usize) * (height as usize) * 2; // 2 bytes per pixel
        let total_expected_size = header_size + expected_data_size;

        ensure!(
            bytes.len() == total_expected_size,
            "File size mismatch. Header claims {}x{} ({} bytes data), but file is {} bytes. Expected {}",
            width, height, expected_data_size, bytes.len(), total_expected_size
        );

        // Parse data
        let mut data = Vec::with_capacity((width * height) as usize);
        let data_slice = &bytes[header_size..];

        for chunk in data_slice.chunks_exact(2) {
            let val = i16::from_le_bytes(chunk.try_into()?);
            data.push(val);
        }

        Ok(Self {
            width,
            height,
            data,
        })
    }

    pub fn get(&self, x: u32, y: u32) -> Option<i16> {
        if x >= self.width || y >= self.height {
            None
        } else {
            let index = (y * self.width + x) as usize;
            Some(self.data[index])
        }
    }
}
