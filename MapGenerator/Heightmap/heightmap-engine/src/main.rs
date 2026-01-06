use std::io::Write;
use std::env;
use std::fs;
use std::path::Path;
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;

mod stage_logger;

use serde::Deserialize;
use rand::Rng;
use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;

use crate::stage_logger::StageLogger;

//
// Terrain classification derived from normalized height values.
//
// These numeric values are written directly to the output file
// and must remain stable for the tiler to interpret correctly.
//
#[repr(u8)]
#[derive(Debug, Clone, Copy)]
enum TerrainLayer {
    Water = 0,
    Land = 1,
    PineMountain = 2,
    RockMountain = 3,
}

//
// Classify a terrain layer based on a normalized height value.
//
// This mapping is intentionally simple and stable.
// Changing these thresholds will change terrain distribution,
// but will not break the binary format.
//
fn classify_terrain_layer(height_value: u8) -> TerrainLayer {
    match height_value {
        0..=79 => TerrainLayer::Water,
        80..=159 => TerrainLayer::Land,
        160..=219 => TerrainLayer::PineMountain,
        _ => TerrainLayer::RockMountain,
    }
}

//
// Seed initial micro-variation into the height accumulator using hash-based noise.
//
// PURPOSE:
// (unchanged — original comment preserved verbatim)
//
fn seed_height_noise(
    values: &mut [i32],
    width: u32,
    height: u32,
    seed: u64,
    amplitude: i32,
) {
    let width_usize = width as usize;
    let height_usize = height as usize;

    debug_assert_eq!(values.len(), width_usize * height_usize);

    if amplitude <= 0 {
        return;
    }

    let domain_seed: u32 =
        (seed as u32)
            ^ width.wrapping_mul(0x9E3779B1)
            ^ height.wrapping_mul(0x85EBCA77);

    for y in 0..height_usize {
        let y_term: u32 = (y as u32).wrapping_mul(668265263);

        for x in 0..width_usize {
            let idx = y * width_usize + x;

            let mut h: u32 = x as u32;
            h = h.wrapping_mul(374761393);
            h ^= y_term;
            h ^= domain_seed;

            h = (h ^ (h >> 13)).wrapping_mul(1274126177);
            h ^= h >> 16;

            let noise =
                (h & 0xFFFF) as i32 % (amplitude * 2 + 1) - amplitude;

            values[idx] += noise;
        }
    }
}

//
// Apply a box smoothing filter to a heightmap accumulator.
//
// PURPOSE:
// (unchanged — original comment preserved verbatim)
//
fn smooth_heightmap_box(
    values: &mut Vec<i32>,
    width: u32,
    height: u32,
    passes: u32,
) {
    let width = width as usize;
    let height = height as usize;

    let mut scratch = values.clone();

    for _ in 0..passes {
        for row in 1..height - 1 {
            let row_offset = row * width;

            for col in 1..width - 1 {
                let idx = row_offset + col;

                let sum =
                    values[idx] +
                    values[idx - 1] +
                    values[idx + 1] +
                    values[idx - width] +
                    values[idx + width] +
                    values[idx - width - 1] +
                    values[idx - width + 1] +
                    values[idx + width - 1] +
                    values[idx + width + 1];

                scratch[idx] = sum / 9;
            }
        }

        std::mem::swap(values, &mut scratch);
    }
}

//
// Representation of a heightmap job as written by the API.
//
#[derive(Debug, Deserialize)]
struct HeightmapJob {
    job_id: String,
    map_width_in_cells: u32,
    map_height_in_cells: u32,
    fault_line_iteration_count: Option<u32>,
    requested_at_utc: String,
}

//
// Entry point for the heightmap engine.
//
// This program:
// - Parses command-line arguments
// - Loads the job JSON file
// - Generates placeholder heightmap data
// - Writes a binary output file
//
fn main() {
    let arguments: Vec<String> = env::args().collect();

    // Early usage failure: logger cannot exist yet
    if arguments.len() < 5 {
        eprintln!(
            "Usage: heightmap-engine --job-file <path> --output-file <path>"
        );
        std::process::exit(1);
    }

    let job_file_path = &arguments[2];
    let output_file_path = &arguments[4];

    let job_file_contents =
        fs::read_to_string(job_file_path)
            .expect("Failed to read job file");

    let job: HeightmapJob =
        serde_json::from_str(&job_file_contents)
            .expect("Failed to parse job JSON");

    // Logger is created as soon as job_id is known.
    // From this point on, operational output goes to logs, not stdout.
    let logger =
        StageLogger::new(job.job_id.clone(), "heightmap")
            .expect("Failed to initialize logger");

    logger.info(
        "stage_started",
        "Heightmap stage started",
        HashMap::from([
            ("width".into(), job.map_width_in_cells.to_string()),
            ("height".into(), job.map_height_in_cells.to_string()),
        ]),
    ).unwrap();

    //
    // Derive a deterministic seed from job parameters.
    // API does NOT provide a seed.
    //
    let mut hasher = DefaultHasher::new();
    job.job_id.hash(&mut hasher);
    job.map_width_in_cells.hash(&mut hasher);
    job.map_height_in_cells.hash(&mut hasher);
    let seed: u64 = hasher.finish();

    logger.info(
        "seed_derived",
        "Deterministic seed derived from job parameters",
        HashMap::from([
            ("seed".into(), seed.to_string()),
        ]),
    ).unwrap();

    let total_cell_count =
        job.map_width_in_cells * job.map_height_in_cells;

    //
    // Determine how many fault iterations we should run.
    //
    let fault_line_iteration_count =
        job.fault_line_iteration_count.unwrap_or(50);

    logger.info(
        "fault_iterations_selected",
        "Fault line iteration count selected",
        HashMap::from([
            ("iterations".into(), fault_line_iteration_count.to_string()),
        ]),
    ).unwrap();

    //
    // Height accumulator buffer.
    //
    let mut height_accumulator_values =
        vec![0i32; total_cell_count as usize];

    //
    // Create deterministic RNG.
    //
    let mut deterministic_rng =
        ChaCha8Rng::seed_from_u64(seed);

    //
    // Initial seed noise.
    //
    seed_height_noise(
        &mut height_accumulator_values,
        job.map_width_in_cells,
        job.map_height_in_cells,
        seed,
        2,
    );

    logger.info(
        "initial_noise_applied",
        "Initial micro-noise seeded into height accumulator",
        HashMap::new(),
    ).unwrap();

    //
    // Run the fault-line algorithm.
    //
    for fault_iteration_index in 0..fault_line_iteration_count {
        let x1 =
            deterministic_rng.gen_range(0.0..job.map_width_in_cells as f32);
        let y1 =
            deterministic_rng.gen_range(0.0..job.map_height_in_cells as f32);
        let x2 =
            deterministic_rng.gen_range(0.0..job.map_width_in_cells as f32);
        let y2 =
            deterministic_rng.gen_range(0.0..job.map_height_in_cells as f32);

        let dx = x2 - x1;
        let dy = y2 - y1;
        let len2 = dx * dx + dy * dy;

        if len2 < 0.0001 {
            logger.warn(
                "degenerate_fault_line",
                "Skipped degenerate fault line iteration",
                HashMap::from([
                    ("iteration".into(), fault_iteration_index.to_string()),
                ]),
            ).unwrap();
            continue;
        }

        for row in 0..job.map_height_in_cells {
            for col in 0..job.map_width_in_cells {
                let cx = col as f32 + 0.5;
                let cy = row as f32 + 0.5;

                let cross =
                    (cx - x1) * dy - (cy - y1) * dx;

                let idx =
                    (row * job.map_width_in_cells + col) as usize;

                if cross >= 0.0 {
                    height_accumulator_values[idx] += 2;
                } else {
                    height_accumulator_values[idx] -= 2;
                }
            }
        }
    }

    logger.info(
        "fault_lines_complete",
        "Fault-line terrain shaping complete",
        HashMap::new(),
    ).unwrap();

    //
    // Smooth accumulated heights.
    //
    smooth_heightmap_box(
        &mut height_accumulator_values,
        job.map_width_in_cells,
        job.map_height_in_cells,
        2,
    );

    logger.info(
        "smoothing_complete",
        "Heightmap smoothing pass complete",
        HashMap::new(),
    ).unwrap();

    //
    // Normalize accumulator values into 0..255.
    //
    let mut min = i32::MAX;
    let mut max = i32::MIN;

    for &v in &height_accumulator_values {
        min = min.min(v);
        max = max.max(v);
    }

    let range = max - min;

    let mut heightmap_bytes = Vec::with_capacity(total_cell_count as usize);
    let mut terrain_layer_bytes = Vec::with_capacity(total_cell_count as usize);

    if range == 0 {
        logger.warn(
            "flat_heightmap",
            "Heightmap range is zero; output will be flat",
            HashMap::new(),
        ).unwrap();

        heightmap_bytes.resize(total_cell_count as usize, 128);
        terrain_layer_bytes.resize(
            total_cell_count as usize,
            TerrainLayer::Land as u8,
        );
    } else {
        for &v in &height_accumulator_values {
            let norm =
                ((v - min) as f32 / range as f32 * 255.0).round() as u8;

            heightmap_bytes.push(norm);
            terrain_layer_bytes.push(
                classify_terrain_layer(norm) as u8,
            );
        }
    }

    //
    // Write output file.
    //
    let mut output =
        fs::File::create(output_file_path)
            .expect("Failed to create output file");

    output.write_all(&job.map_width_in_cells.to_le_bytes()).unwrap();
    output.write_all(&job.map_height_in_cells.to_le_bytes()).unwrap();
    output.write_all(&seed.to_le_bytes()).unwrap();
    output.write_all(&heightmap_bytes).unwrap();
    output.write_all(&terrain_layer_bytes).unwrap();

    logger.info(
        "output_written",
        "Heightmap output written successfully",
        HashMap::from([
            ("path".into(), output_file_path.to_string()),
            ("cells".into(), total_cell_count.to_string()),
        ]),
    ).unwrap();

    logger.info(
        "stage_finished",
        "Heightmap stage completed successfully",
        HashMap::new(),
    ).unwrap();
}
