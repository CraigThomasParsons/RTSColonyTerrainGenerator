## Todo List
### Step 1 — Lock the layer model (simple & explicit)

We derive layers only from normalized height (0–255).

Layer definitions (v1, locked)
```
0   –  79   → Water
80  – 159   → Land
160 – 219   → PineMountain
220 – 255   → RockMountain
```
These numbers:

- Are intuitive

- Produce visually reasonable results

- Can be tuned later without breaking format

---

Rust representation

Add this enum:
```
#[repr(u8)]
#[derive(Debug, Clone, Copy)]
enum TerrainLayer {
    Water = 0,
    Land = 1,
    PineMountain = 2,
    RockMountain = 3,
}
```

This guarantees:

- One byte per layer

- Stable ABI

- Easy tiler decoding

---

### Step 2 — Classify each cell after normalization

Right now you only output height bytes.
We extend this to two parallel buffers:

- heightmap_bytes: Vec<u8>

- terrain_layer_bytes: Vec<u8>

Add this helper function (clear + testable)
```
fn classify_terrain_layer(height_value: u8) -> TerrainLayer {
    match height_value {
        0..=79 => TerrainLayer::Water,
        80..=159 => TerrainLayer::Land,
        160..=219 => TerrainLayer::PineMountain,
        _ => TerrainLayer::RockMountain,
    }
}
```
Step 2 is complete only if all of these are true:

1. A helper function exists that maps u8 → TerrainLayer

2. A terrain_layer_bytes: Vec<u8> buffer exists

3. During normalization, each cell:

    - pushes a height byte

    - classifies a terrain layer

    - pushes a layer byte

4. The two buffers are parallel (same length, same ordering)

- Right now, only (1) is proposed, not implemented.


---

Modify normalization loop

Replace your final normalization logic with this:
```
let mut terrain_layer_bytes: Vec<u8> =
    Vec::with_capacity(total_cell_count as usize);

for &height_value in height_accumulator_values.iter() {
    let normalized_value_zero_to_one: f32 =
        (height_value - minimum_height_value) as f32
            / height_value_range as f32;

    let normalized_value_zero_to_255: u8 =
        (normalized_value_zero_to_one * 255.0).round() as u8;

    heightmap_bytes.push(normalized_value_zero_to_255);

    let terrain_layer: TerrainLayer =
        classify_terrain_layer(normalized_value_zero_to_255);

    terrain_layer_bytes.push(terrain_layer as u8);
}
```

Now every cell has:

- A height

- A terrain classification

---

### Step 3 — Define a real output file format (this matters)

Right now the output is “just bytes”.
That’s fine short-term, but tilers need context.

Final v1 binary format (authoritative)

```
[HEADER]
u32  width
u32  height
u64  seed

[HEIGHTMAP]
u8 * (width * height)

[LAYERMAP]
u8 * (width * height)

```
Why this is correct

- Self-describing

- Forward-compatible

- Zero ambiguity

- Extremely fast to load

- No JSON parsing in the tiler hot path

---

### Rust code to write this format

Replace the final write block with:
```
use std::io::Write;

let mut output_file =
    fs::File::create(output_path)
        .expect("Failed to create output file");

/**
 * Write header information.
 */
output_file
    .write_all(&job.map_width_in_cells.to_le_bytes())
    .expect("Failed to write width");

output_file
    .write_all(&job.map_height_in_cells.to_le_bytes())
    .expect("Failed to write height");

output_file
    .write_all(&job.random_seed.to_le_bytes())
    .expect("Failed to write seed");

/**
 * Write heightmap bytes.
 */
output_file
    .write_all(&heightmap_bytes)
    .expect("Failed to write heightmap bytes");

/**
 * Write terrain layer bytes.
 */
output_file
    .write_all(&terrain_layer_bytes)
    .expect("Failed to write terrain layer bytes");
```

This is now a real artifact, not a temp blob.

---

Step 4 — Update the README contract (mentally, not now)

Your README already explains the algorithm.
What’s now true after this step:

Output contains both height + layer data

Tiler can:

read header

seek directly into buffers

build tiles without reclassification

You’ve effectively finished the heightmapper’s responsibility.

---
Step 5 - I don't know yet.
### Next (pick one, and we go straight there)


- A) Add fault-line metadata recording (ridges, cliffs)
- B) Add PNG debug output (optional, dev-only)
     - I think optional is a good idea, but also:
     - after this is done, lets keep it all in dev-mode
     - The day this goes in production I'll probably be 50 years old.

Step 6
### What I want to do
I want to write a testdrive cli app.
Todo the many things that the A.I
tells me use to test.


## I'm interested in what the A.I says about.
https://github.com/Goldziher/spikard

I think I like the idea of starting to use
a framework that supports polyglot projects is the way I should build tiny isolated APIs

Later I want to create the basic todolist with spikard.

### Suggested next upgrades for the tester
Next logical upgrades (whenever you want)

- clean --all

- watch --once

- inspect-heightmap --stats

- inspect-heightmap --dump-layers

- mapgenctl doctor (sanity checks)

### Very cool ideas that chatGPT came up with

Think of it like this:

- Fault lines → tectonic forces

- Smoothing → erosion over time

- Normalization → sea level

- Classification → ecology

### You’ve now built the geological layer of your world.

## When you’re ready, the next logical upgrades are:

- slope calculation

- river flow direction

- basin detection

But smoothing comes first — and now you’ve done it right.

- If you want next:

- edge-aware smoothing

- erosion simulation

- river carving that respects slopes

I want to do all of these things, but I'll never be done this way so,
I'm stopping after the smoothing and moving on to Tiling.
Maybe after the whole thing is done, I'll revisit these ideas.