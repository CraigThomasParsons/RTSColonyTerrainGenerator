use std::io::Write;
use std::env;
use std::fs;
use std::path::Path;

use serde::Deserialize;
use rand::Rng;
use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;

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
// Write an 8-bit grayscale BMP image for visual debugging.
//
// PURPOSE:
// This function generates a grayscale BMP image representing
// the heightmap produced by the engine.
//
// Each pixel corresponds to one terrain cell:
// - Pixel intensity (0–255) directly represents height
// - Darker values = lower terrain
// - Lighter values = higher terrain
//
// This output is intended for:
// - Visual sanity checking
// - Algorithm validation
// - Developer debugging
//
// It is NOT part of the production pipeline and is optional.
//
// INPUTS:
// - output_path:
//     Filesystem path where the BMP file will be written.
//
// - width:
//     Width of the image in pixels.
//     Must match the width of the heightmap grid.
//
// - height:
//     Height of the image in pixels.
//     Must match the height of the heightmap grid.
//
// - pixel_bytes:
//     A slice of bytes containing normalized height values.
//     Each value must be in the range 0–255.
//     Length must be exactly width// height.
//
// OUTPUTS:
// - Writes a BMP file to disk at output_path.
//
// RETURNS:
// - None.
//
// SIDE EFFECTS:
// - Creates or overwrites the file at output_path.
//
// IMPORTANT NOTES:
// - BMP format stores pixel rows bottom-up, so rows are written in reverse.
// - This function writes a fixed grayscale palette (256 entries).
// - No compression is used.
// - No error recovery is attempted; failures cause a panic.
//
fn write_grayscale_bmp(
    output_path: &Path,
    width: u32,
    height: u32,
    pixel_bytes: &[u8],
) {
    use std::io::Write;

    //
    // Calculate total file size.
    //
    // Components:
    // - BMP file header (14 bytes)
    // - DIB header (40 bytes)
    // - Grayscale palette (256// 4 bytes)
    // - Pixel data (width// height bytes)
    //
    let file_size: u32 =
        14 + 40 + 256 * 4 + (width * height);

    let mut file =
        fs::File::create(output_path)
            .expect("Failed to create BMP file");



    // BMP file header
    file.write_all(b"BM").unwrap();
    file.write_all(&file_size.to_le_bytes()).unwrap();
    file.write_all(&[0u8; 4]).unwrap();
    
    let pixel_data_offset: u32 = 14 + 40 + 256 * 4;
    file.write_all(&pixel_data_offset.to_le_bytes())
        .expect("Failed to write BMP pixel data offset");

    // DIB header (BITMAPINFOHEADER)
    file.write_all(&40u32.to_le_bytes()).unwrap();
    file.write_all(&width.to_le_bytes()).unwrap();
    file.write_all(&height.to_le_bytes()).unwrap();
    file.write_all(&1u16.to_le_bytes()).unwrap();   // planes
    file.write_all(&8u16.to_le_bytes()).unwrap();   // bpp
    file.write_all(&0u32.to_le_bytes()).unwrap();   // compression
    file.write_all(&(width * height).to_le_bytes()).unwrap();
    file.write_all(&[0u8; 16]).unwrap();

    // Grayscale palette
    for i in 0..256u32 {
        let value: u8 = i as u8;
        file.write_all(&[value, value, value, 0]).unwrap();
    }

    // Pixel data (BMP is bottom-up)
    for row in (0..height).rev() {
        let start = (row * width) as usize;
        let end = start + width as usize;
        file.write_all(&pixel_bytes[start..end]).unwrap();
    }
}

//
// Write a 24-bit RGB BMP image representing terrain layers.
//
// PURPOSE:
// This function generates a color-coded BMP image where each
// pixel represents the semantic terrain layer of a cell.
//
// This visualization allows developers to:
// - Verify terrain classification thresholds
// - Confirm correct water / land / mountain separation
// - Quickly spot classification errors
//
// INPUTS:
// - output_path:
//     Filesystem path where the BMP file will be written.
//
// - width:
//     Width of the image in pixels.
//
// - height:
//     Height of the image in pixels.
//
// - layer_bytes:
//     A slice of bytes representing terrain layers.
//     Each byte corresponds to a TerrainLayer enum value.
//     Length must be exactly width// height.
//
// COLOR MAPPING (DEBUG ONLY):
// - Water        → Blue
// - Land         → Green
// - PineMountain → Dark Green
// - RockMountain → Gray
//
// OUTPUTS:
// - Writes a BMP file to disk at output_path.
//
// RETURNS:
// - None.
//
// SIDE EFFECTS:
// - Creates or overwrites the file at output_path.
//
// IMPORTANT NOTES:
// - Uses 24-bit uncompressed BMP format.
// - BMP rows are written bottom-up.
// - This output is for debugging only and is not part of the engine contract.
//
fn write_layer_bmp(
    output_path: &Path,
    width: u32,
    height: u32,
    layer_bytes: &[u8],
) {
    use std::io::Write;

    let bytes_per_pixel: u32 = 3;
    let image_size: u32 = width * height * bytes_per_pixel;
    let file_size: u32 = 14 + 40 + image_size;

    let mut file =
        fs::File::create(output_path)
            .expect("Failed to create BMP file");

    // BMP FILE HEADER
    file.write_all(b"BM").unwrap();
    file.write_all(&file_size.to_le_bytes()).unwrap();
    file.write_all(&[0u8; 4]).unwrap();

    let pixel_data_offset: u32 = 14 + 40;

    file.write_all(&pixel_data_offset.to_le_bytes())
        .expect("Failed to write BMP pixel data offset");


    // DIB HEADER
    file.write_all(&40u32.to_le_bytes()).unwrap();
    file.write_all(&width.to_le_bytes()).unwrap();
    file.write_all(&height.to_le_bytes()).unwrap();
    file.write_all(&1u16.to_le_bytes()).unwrap();   // color planes
    file.write_all(&24u16.to_le_bytes()).unwrap();  // bits per pixel
    file.write_all(&0u32.to_le_bytes()).unwrap();   // no compression
    file.write_all(&image_size.to_le_bytes()).unwrap();
    file.write_all(&[0u8; 16]).unwrap();

    // PIXEL DATA (BOTTOM-UP)
    for row in (0..height).rev() {
        for col in 0..width {
            let index = (row * width + col) as usize;

            // Map terrain layer to a debug color.
            //
            // BMP uses BGR ordering.
            //
            let color = match layer_bytes[index] {
                0 => [255, 0, 0],     // Water → Blue
                1 => [0, 255, 0],     // Land → Green
                2 => [0, 128, 0],     // PineMountain → Dark green
                _ => [128, 128, 128], // RockMountain → Gray
            };

            file.write_all(&color).unwrap();
        }
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
    random_seed: u64,

    #[allow(dead_code)]
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

    if arguments.len() < 5 {
        eprintln!(
            "Usage: heightmap-engine --job-file <path> --output-file <path>"
        );
        std::process::exit(1);
    }

    let job_file_path = &arguments[2];
    let output_file_path = &arguments[4];

    let job_file_contents = fs::read_to_string(job_file_path)
        .expect("Failed to read job file");

    let job: HeightmapJob = serde_json::from_str(&job_file_contents)
        .expect("Failed to parse job JSON");

    let mut debug_height_bmp_path: Option<String> = None;
    let mut debug_layer_bmp_path: Option<String> = None;

    let mut argument_index: usize = 1;

    while argument_index < arguments.len() {
        match arguments[argument_index].as_str() {
            "--debug-height-bmp" => {
                debug_height_bmp_path =
                    arguments.get(argument_index + 1).cloned();
                argument_index += 2;
            }
            "--debug-layer-bmp" => {
                debug_layer_bmp_path =
                    arguments.get(argument_index + 1).cloned();
                argument_index += 2;
            }
            _ => {
                argument_index += 1;
            }
        }
    }

    println!(
        "[heightmap-engine] Generating {}x{} heightmap for job {}",
        job.map_width_in_cells,
        job.map_height_in_cells,
        job.job_id
    );

    let total_cell_count =
        job.map_width_in_cells * job.map_height_in_cells;

    //
   // Output buffer for normalized height values.
   // One byte per cell.
   //
    let mut heightmap_bytes: Vec<u8> =
        Vec::with_capacity(total_cell_count as usize);

    //
   // Output buffer for terrain layer classification.
   //
   // This buffer is parallel to heightmap_bytes:
   // index N refers to the same cell in both buffers.
   //
    let mut terrain_layer_bytes: Vec<u8> =
        Vec::with_capacity(total_cell_count as usize);


    //
    // Determine how many fault iterations we should run.
    //
    // If the job JSON does not contain the field yet,
    // we choose a conservative default that still produces visible ridges.
    //
    let fault_line_iteration_count: u32 =
        job.fault_line_iteration_count.unwrap_or(50);

    //
    // We will accumulate heights using signed integers.
    //
    // This is important because fault iterations add and subtract values.
    // We normalize to 0..255 later.
    //
    let mut height_accumulator_values: Vec<i32> =
        vec![0; total_cell_count as usize];

    //
    // Create a deterministic random number generator.
    //
    // As long as width, height, and seed stay the same,
    // you will get the exact same map again.
    //
    let mut deterministic_rng: ChaCha8Rng =
        ChaCha8Rng::seed_from_u64(job.random_seed);

    //
    // The displacement amount controls ridge strength.
    //
    // A larger number creates taller mountains faster.
    // We will start simple and tune later.
    //
    let displacement_amount_per_iteration: i32 = 2;

    //
    // Run the fault-line algorithm.
    //
    for fault_iteration_index in 0..fault_line_iteration_count {
        //
        // Pick two random points to define a line.
        //
        // We pick points in floating point space because
        // it makes the signed-side test simple and stable.
        //
        let line_point_one_x: f32 =
            deterministic_rng.gen_range(0.0..job.map_width_in_cells as f32);
        let line_point_one_y: f32 =
            deterministic_rng.gen_range(0.0..job.map_height_in_cells as f32);

        let line_point_two_x: f32 =
            deterministic_rng.gen_range(0.0..job.map_width_in_cells as f32);
        let line_point_two_y: f32 =
            deterministic_rng.gen_range(0.0..job.map_height_in_cells as f32);

        //
        // Compute the line direction vector.
        //
        let line_direction_x: f32 = line_point_two_x - line_point_one_x;
        let line_direction_y: f32 = line_point_two_y - line_point_one_y;

        //
        // If both points are almost identical, skip this iteration.
        // This avoids divide-by-zero-like edge cases in our geometry.
        //
        let line_length_squared: f32 =
            (line_direction_x * line_direction_x) + (line_direction_y * line_direction_y);

        if line_length_squared < 0.0001 {
            println!(
                "[heightmap-engine] Skipping degenerate fault line at iteration {}",
                fault_iteration_index
            );
            continue;
        }

        //
        // For every cell, determine which side of the line it is on.
        //
        // We use the 2D cross product (signed area) to determine side:
        // cross = (point - line_point_one) x (line_direction)
        //
        // - cross > 0 means one side
        // - cross < 0 means the other side
        //
        for row_index in 0..job.map_height_in_cells {
            for column_index in 0..job.map_width_in_cells {
                let cell_center_x: f32 = column_index as f32 + 0.5;
                let cell_center_y: f32 = row_index as f32 + 0.5;

                let vector_from_line_to_cell_x: f32 = cell_center_x - line_point_one_x;
                let vector_from_line_to_cell_y: f32 = cell_center_y - line_point_one_y;

                let signed_cross_product_value: f32 =
                    (vector_from_line_to_cell_x * line_direction_y)
                        - (vector_from_line_to_cell_y * line_direction_x);

                let accumulator_index: usize =
                    (row_index * job.map_width_in_cells + column_index) as usize;

                //
                // Apply displacement based on which side we are on.
                //
                // This creates a "step" along the fault line.
                // Repeating many times creates ridges.
                //
                if signed_cross_product_value >= 0.0 {
                    height_accumulator_values[accumulator_index] +=
                        displacement_amount_per_iteration;
                } else {
                    height_accumulator_values[accumulator_index] -=
                        displacement_amount_per_iteration;
                }
            }
        }
    }

    // Normalization section, also known as min-max normalization.

    //
    // Normalize accumulator values into 0..255 bytes.
    //
    // This is required for compatibility with the tiler and image formats.
    //
    let mut minimum_height_value: i32 = i32::MAX;
    let mut maximum_height_value: i32 = i32::MIN;

    //
    // The min/max discovery loop
    //  This prepares for normalization.
    //  Answers the question: "What is the smallest height value and 
    // the largest height value in the entire map?""
    //
    for &height_value in height_accumulator_values.iter() {
        if height_value < minimum_height_value {
            minimum_height_value = height_value;
        }

        if height_value > maximum_height_value {
            maximum_height_value = height_value;
        }
    }

    //
    // Compute the range of accumulated height values.
    //
    // Avoid division by zero if the map is perfectly flat.
    //
    // This can happen with a very small iteration count,
    // or if displacement_amount_per_iteration is zero.
    //
    // This tells us how much vertical variation exists in the map.
    // We need this value to normalize heights into the range 0..255.
    //
    let height_value_range: i32 = maximum_height_value - minimum_height_value;

    //
   // Special case: the map is perfectly flat.
   //
   // This can happen if:
   // - The fault iteration count is very small
   // - The displacement amount is zero
   //
   // If the range is zero, normalization would cause division by zero.
   //
    if height_value_range == 0 {
        println!(
            "[heightmap-engine] Height range is zero; output will be flat."
        );

        //
        // Fill the entire heightmap with a neutral mid-gray value.
        //
        // 128 is chosen because it sits in the middle of 0..255
        // and represents a "flat" terrain.
        //
        for _ in 0..total_cell_count {
            heightmap_bytes.push(128);
        }
    } else {

        //
        // Normal case: the map has height variation.
        //
        // We convert each accumulated height value into a byte.
        //
        for &height_value in height_accumulator_values.iter() {

            //
            // Normalize the signed height value into the range 0.0..1.0.
            //
            // Subtracting the minimum shifts the range to start at zero.
            // Dividing by the total range scales it to a unit interval.
            //
            let normalized_value_zero_to_one: f32 =
                (height_value - minimum_height_value) as f32
                    / height_value_range as f32;

            //
            // Convert the normalized floating-point value into a byte.
            //
            // - Multiply by 255 to scale into byte range
            // - Round to avoid truncation bias
            //
            let normalized_value_zero_to_255: u8 =
                (normalized_value_zero_to_one * 255.0).round() as u8;

            //
            // Adding
            // The height of each cell (0–255)
            // to the growable array.
            // This is the primary heightmap output.
            // And it is storing the normalized value:
            //
            heightmap_bytes.push(normalized_value_zero_to_255);

            //
            // Terrain layer bytes is:  The terrain type of each cell.
            //                           (water / land / etc.)
            //
            // Classify the terrain layer based on height.
            //
            // This converts a numeric height into a semantic meaning
            // such as water, land, pine forest, or rock.
            //
            let terrain_layer: TerrainLayer =
                classify_terrain_layer(normalized_value_zero_to_255);

            //
            // Store the terrain layer as a byte.
            //
            // This buffer is parallel to heightmap_bytes:
            // index N refers to the same cell in both arrays.
            //
            terrain_layer_bytes.push(terrain_layer as u8);
        }
    }

    // Sanity check.
    assert_eq!(heightmap_bytes.len(), terrain_layer_bytes.len());

    let output_path = Path::new(output_file_path);

    //
    // Create the output file.
    //
    // This file will contain:
    // - A fixed-size header
    // - The heightmap byte buffer
    // - The terrain layer byte buffer
    //
    let mut output_file =
        fs::File::create(output_path)
            .expect("Failed to create output heightmap file");

    //
    // Write header fields in little-endian format.
    //
    // The header allows the tiler to understand the file
    // without relying on external metadata.
    //
    output_file
        .write_all(&job.map_width_in_cells.to_le_bytes())
        .expect("Failed to write map width");

    output_file
        .write_all(&job.map_height_in_cells.to_le_bytes())
        .expect("Failed to write map height");

    output_file
        .write_all(&job.random_seed.to_le_bytes())
        .expect("Failed to write random seed");

    //
    // Write heightmap data.
    //
    // One byte per cell, row-major order.
    //
    output_file
        .write_all(&heightmap_bytes)
        .expect("Failed to write heightmap data");

    //
    // Write terrain layer data.
    //
    // One byte per cell, parallel to heightmap data.
    //
    output_file
        .write_all(&terrain_layer_bytes)
        .expect("Failed to write terrain layer data");

    if let Some(path) = debug_height_bmp_path {
        write_grayscale_bmp(
            Path::new(&path),
            job.map_width_in_cells,
            job.map_height_in_cells,
            &heightmap_bytes,
        );
    }

    if let Some(path) = debug_layer_bmp_path {
        write_layer_bmp(
            Path::new(&path),
            job.map_width_in_cells,
            job.map_height_in_cells,
            &terrain_layer_bytes,
        );
    }

    println!(
        "[heightmap-engine] Output written to {}",
        output_file_path
    );
}
