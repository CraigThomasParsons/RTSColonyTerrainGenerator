#!/bin/bash
set -e

# Usage: ./create_module.sh <ModuleName>

MODULE_NAME=$1

if [ -z "$MODULE_NAME" ]; then
    echo "Usage: $0 <ModuleName>"
    exit 1
fi

BASE_DIR="$(dirname "$0")/.."
MODULE_DIR="$BASE_DIR/MapGenerator/$MODULE_NAME"
ENGINE_NAME=$(echo "$MODULE_NAME" | tr '[:upper:]' '[:lower:]')-engine

echo "Creating module '$MODULE_NAME' at $MODULE_DIR..."

# 1. Create Directory Structure
mkdir -p "$MODULE_DIR"/{bin,inbox,outbox,failed,systemd}

# 2. Update/Initialize Rust Project
if [ ! -d "$MODULE_DIR/bin/$ENGINE_NAME" ]; then
    echo "Initializing Rust project..."
    cargo new --bin "$MODULE_DIR/bin/$ENGINE_NAME" --name "$ENGINE_NAME"
else
    echo "Directory exists. Running cargo init to ensure standard structure..."
    cargo init --bin "$MODULE_DIR/bin/$ENGINE_NAME" --name "$ENGINE_NAME"
fi

# Write Standard Cargo.toml
cat > "$MODULE_DIR/bin/$ENGINE_NAME/Cargo.toml" <<EOF
[package]
name = "$ENGINE_NAME"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
rand = "0.8"
rand_chacha = "0.3"
EOF

# Write Template main.rs (Overwrite to ensure correct structure for new modules)
# We only do this if it looks like the default hello world
if grep -q "println!(\"Hello, world!\");" "$MODULE_DIR/bin/$ENGINE_NAME/src/main.rs"; then
cat > "$MODULE_DIR/bin/$ENGINE_NAME/src/main.rs" <<EOF
use std::env;
use std::fs;
use std::path::Path;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Job {
    job_id: String,
    // Add module-specific fields here
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 5 {
        eprintln!("Usage: $ENGINE_NAME --job-file <path> --output-file <path>");
        std::process::exit(1);
    }

    let job_file_path = &args[2];
    let output_file_path = &args[4];
    
    println!("Processing job from {}", job_file_path);

    // TODO: Implement logic here specific to $MODULE_NAME
    
    // Example: Create an empty output file
    fs::File::create(output_file_path).expect("Failed to create output file");
    
    println!("Job complete. Output written to {}", output_file_path);
}
EOF
fi


# 3. Create install.sh
cat > "$MODULE_DIR/install.sh" <<EOF
#!/bin/bash
set -e

cd bin/$ENGINE_NAME
cargo build --release
cp target/release/$ENGINE_NAME ../$ENGINE_NAME
chmod +x ../$ENGINE_NAME
echo "Installed $ENGINE_NAME"
EOF
chmod +x "$MODULE_DIR/install.sh"

echo "Module $MODULE_NAME created successfully!"
echo "To build: cd MapGenerator/$MODULE_NAME && ./install.sh"
