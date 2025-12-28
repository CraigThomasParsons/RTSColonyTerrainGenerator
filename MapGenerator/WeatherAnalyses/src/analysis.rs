use crate::heightmap::Heightmap;
use crate::weather_map::WeatherMap;

// Flow Direction Constants
// 0 = no flow / local minimum
// 1 = north
// 2 = north-east
// 3 = east
// 4 = south-east
// 5 = south
// 6 = south-west
// 7 = west
// 8 = north-west

const DX: [i32; 9] = [0, 0, 1, 1, 1, 0, -1, -1, -1];
const DY: [i32; 9] = [0, -1, -1, 0, 1, 1, 1, 0, -1];
// Distance factors for slope calc (approximate 1.0 vs 1.414 scaled by 1000 or similar? Or just raw height diff?)
// Spec says "Normalized to engine scale".
// We will use raw Max Drop for slope and standard D8 for flow.

pub fn generate_weather_map(heightmap: &Heightmap) -> WeatherMap {
    let mut map = WeatherMap::new(heightmap.width, heightmap.height);

    // Pass 1: Slope and Flow Direction
    for y in 0..heightmap.height {
        for x in 0..heightmap.width {
            let (slope, flow) = calc_slope_and_flow(heightmap, x, y);
            let idx = (y * heightmap.width + x) as usize;
            map.slope[idx] = slope;
            map.flow[idx] = flow;
        }
    }

    // Pass 2: Basin IDs
    // Identify sinks and trace basins
    identify_basins(&mut map, heightmap.width, heightmap.height);

    map
}

fn calc_slope_and_flow(hm: &Heightmap, x: u32, y: u32) -> (i16, u8) {
    let center_h = match hm.get(x, y) {
        Some(h) => h,
        None => return (0, 0),
    };

    let mut best_flow = 0;
    let mut max_drop_val = 0.0;
    let mut max_diff_abs = 0; // For slope magnitude

    // Iterate 1..=8 neighbors
    for dir in 1..=8 {
        let nx = (x as i32 + DX[dir]);
        let ny = (y as i32 + DY[dir]);

        // Bounds check
        if nx < 0 || ny < 0 || nx >= hm.width as i32 || ny >= hm.height as i32 {
            continue;
        }

        if let Some(nh) = hm.get(nx as u32, ny as u32) {
            let diff = center_h as f32 - nh as f32;
            let abs_diff = (center_h - nh).abs();
            
            if abs_diff > max_diff_abs {
                max_diff_abs = abs_diff;
            }

            // Flow calculation (Steepest Descent)
            // Distance: 1.0 for cardinal (odd dir), sqrt(2) for diagonal (even dir)
            // wait: 1=N (0,-1) len 1.
            // 2=NE (1,-1) len 1.414.
            
            let dist = if dir % 2 != 0 { 1.0 } else { 1.41421356 };
            let drop_rate = diff / dist;

            if drop_rate > max_drop_val {
                max_drop_val = drop_rate;
                best_flow = dir as u8;
            }
        }
    }

    // Slope: spec says "Derived from height differences". 
    // We'll use max absolute difference as a robust integer metric for now.
    // Or should it be max_drop_val * some_scalar?
    // Let's use max_diff_abs directly as i16.
    (max_diff_abs, best_flow)
}

fn identify_basins(map: &mut WeatherMap, width: u32, height: u32) {
    let mut next_basin_id = 1;
    let size = (width * height) as usize;
    
    // We use an iterative approach with path splitting or similar to avoid recursion depth issues
    // But since it's a DAG (mostly), we can trace.
    // Ideally, iterate all cells. If not basin assigned, trace flow.
    // If sink reached, assign basin ID.
    // If trace hits already assigned path, copy basin ID.
    
    // Need a way to resolve stack.
    
    for i in 0..size {
        if map.basin[i] != 0 {
            continue; // Already assigned
        }

        let mut path = Vec::new();
        let mut curr = i;
        
        loop {
            if map.basin[curr] != 0 {
                // Found an existing basin, propagate it back
                let found_id = map.basin[curr];
                for &node in &path {
                    map.basin[node] = found_id;
                }
                break;
            }

            path.push(curr);

            let flow_dir = map.flow[curr];
            if flow_dir == 0 {
                // Found a sink (and it wasn't assigned yet, otherwise map.basin[curr] != 0)
                // Assign new basin ID
                let new_id = next_basin_id;
                next_basin_id += 1;
                map.basin[curr] = new_id;
                
                // Propagate
                for &node in &path {
                    map.basin[node] = new_id;
                }
                break;
            }

            // Move to neighbor
            let cx = (curr as u32) % width;
            let cy = (curr as u32) / width;
            let dir = flow_dir as usize;
            
            let nx = cx as i32 + DX[dir];
            let ny = cy as i32 + DY[dir];

            // Safety check (should be safe by flow generation logic, but strictly...)
            if nx < 0 || ny < 0 || nx >= width as i32 || ny >= height as i32 {
                 // Boundary error? Treat as sink.
                 let new_id = next_basin_id;
                 next_basin_id += 1;
                 map.basin[curr] = new_id;
                 for &node in &path {
                    map.basin[node] = new_id;
                }
                break;
            }

            let next_idx = (ny * width as i32 + nx) as usize;
            
            // Cycle detection (simple: if next_idx is in path)
            // Since D8 with strictly positive drop avoids cycles, loop is impossible unless flat area handling produced cycles.
            // Our calc_slope_and_flow only flows if drop > 0 (strictly positive). 
            // So no cycles possible. Flat areas return flow 0 (sink).
            
            curr = next_idx;
        }
    }
}
