# Rust Coding Style & Commenting Conventions

This document defines the required Rust coding style for the
Heightmap Generator and related MapGenerator components.

The goal is clarity, explicitness, and long-term maintainability,
especially for developers who are new to Rust.

This project intentionally prioritizes readability over conciseness.

---

## Core Philosophy

- Code is written for humans first
- Explicit is better than clever
- Descriptive names are preferred over short names
- Single-character variable names are forbidden
- Comments are required to explain intent and reasoning
- Rust’s safety features should be used, not fought

---

## Formatting & Tooling

### rustfmt
- All code must be formatted using `rustfmt`
- Do not fight rustfmt; structure code so formatting stays readable

```bash
cargo fmt
```

### clippy (Strongly Recommended)

Clippy should be run regularly:
```
cargo clippy -- -D warnings
```

Recommended lint configuration at the top of main.rs or lib.rs:
```
#![warn(clippy::pedantic)]
#![deny(clippy::many_single_char_names)]
#![deny(clippy::single_char_pattern)]
```

These lints help enforce descriptive naming and prevent dense code.
---

Naming Conventions (LOCKED)
Variables

- Use snake_case (Rust standard)

- Use long, descriptive names

- Never use single-letter variable names

✅ Good:
```
let job_file_path: &String = &arguments[2];
let fault_line_iteration_count: u32 = 50;
let height_accumulator_values: Vec<i32> = Vec::new();
```
❌ Bad:
```
let i = 0;
let x = 10;
let tmp = Vec::new();
```

---
Functions

- Use snake_case
- Verb-based, descriptive names
- Avoid abbreviations

✅ Good:
```
parse_heightmap_job_file()
normalize_height_values_to_byte_range()
run_fault_line_iterations()
```
❌ Bad:
```
parse()
do_it()
gen()
```

---
### Structs & Enums

- Use PascalCase

- Names should represent real domain concepts

✅ Good:
```
struct HeightmapJob;
enum TerrainLayer;
```

❌ Bad:
```
struct Job;
enum T;
```

---

### Constants

- Use UPPER_SNAKE_CASE
```
const DEFAULT_FAULT_LINE_ITERATION_COUNT: u32 = 50;
```

---

### Type Usage Rules
## Prefer Explicit Types (Especially Early On)

Rust can infer types, but this project prefers explicitness,
especially in public APIs and non-trivial logic.

✅ Good:
```
let total_cell_count: u32 =
    job.map_width_in_cells * job.map_height_in_cells;
```

❌ Avoid (when logic is non-trivial):
```
let total = job.map_width_in_cells * job.map_height_in_cells;
```
---

 - Use Signed vs Unsigned Ints Intentionally

 - Use u32, usize for sizes and indexing

 - Use i32, i64 for values that can go negative

 - Comment why a signed type is required

 ```
 // Signed because fault lines add and subtract height values
let mut height_accumulator_values: Vec<i32> = vec![0; cell_count];
 ```
---

### Commenting Rules (CRITICAL)
## Comment Density

- A comment every 2–4 logical lines

- Explain why, not obvious syntax

- Break complex logic into commented sections

---
### Section Comments

Use block comments to describe algorithm phases:
```
/**
 * Run the fault-line algorithm.
 *
 * Each iteration selects a random line and displaces
 * height values on either side to form ridges.
 */
```
### Inline Comments
```
// Skip degenerate lines to avoid unstable geometry math
if line_length_squared < 0.0001 {
    continue;
}
```
---
### Guard Clauses Must Be Commented
```
// Exit early if required CLI arguments are missing
if arguments.len() != 5 {
    eprintln!("Usage: ...");
    std::process::exit(1);
}
```
---
### Error Handling Rules
## Prefer Explicit Failure Over Silent Handling

- Use expect() with meaningful messages

- Avoid unwrap() unless the reason is documented

✅ Good:
```
let job_file_contents = fs::read_to_string(job_file_path)
    .expect("Failed to read job file");
```

❌ Bad:
```
let contents = fs::read_to_string(path).unwrap();
```

---
### When to Use Result

- Use Result<T, E> in library code
- main() may exit on error using expect() or explicit logging
---

### Control Flow Rules
### Prefer Clarity Over Iterator Cleverness

Loops are preferred over dense iterator chains when logic is complex.

✅ Good:
```
for row_index in 0..map_height {
    for column_index in 0..map_width {
        // explicit logic here
    }
}
```

❌ Avoid (when it hurts readability):
```
cells.iter().map(|c| ...).collect::<Vec<_>>();
```
---

### Avoid Deep Nesting

- Use early returns

- Use guard clauses

- Break logic into smaller functions if needed
---

### Collections & Memory

- Pre-allocate vectors when size is known

- Comment why capacity is chosen
```
let mut heightmap_bytes: Vec<u8> =
    Vec::with_capacity(total_cell_count as usize);
```

### Determinism Rules

- All randomness must be seeded

- Seeds must come from the job definition

- No global RNG usage

```
let mut deterministic_rng: ChaCha8Rng =
    ChaCha8Rng::seed_from_u64(job.random_seed);
```
---
Binary Output Rules

- Output formats must be documented

- Write exactly one output file per run

- Avoid side effects outside the specified output path
---

### Forbidden Practices

🚫 Single-letter variable names
🚫 Unexplained unwrap()
🚫 Clever iterator tricks
🚫 Hidden global state
🚫 Implicit behavior
🚫 Side effects outside declared outputs

Final Rule (Most Important)

If you have to re-learn what your own Rust code does, the code is wrong.

This project values:
clarity > brevity > cleverness.