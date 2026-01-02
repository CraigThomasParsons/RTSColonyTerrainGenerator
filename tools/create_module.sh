#!/bin/bash
set -e

# Usage: ./create_module.sh <ModuleName>

MODULE_NAME=$1

# Check if module name argument is provided
if [ -z "$MODULE_NAME" ]; then
    echo "Usage: $0 <ModuleName>"
    exit 1
fi

# Determine the absolute path to the project root relative to this script
BASE_DIR="$(dirname "$0")/.."
# Define the target directory for the new module
MODULE_DIR="$BASE_DIR/MapGenerator/$MODULE_NAME"
# Convert the module name to lowercase and append -engine for the binary name
ENGINE_NAME=$(echo "$MODULE_NAME" | tr '[:upper:]' '[:lower:]')-engine

echo "Creating module '$MODULE_NAME' at $MODULE_DIR..."

# 1. Create Directory Structure
# Create the standard folder hierarchy for file-based IPC
mkdir -p "$MODULE_DIR"/{bin,inbox,outbox,failed,systemd}

# 2. Update/Initialize Rust Project
# Check if the binary package already exists
if [ ! -d "$MODULE_DIR/bin/$ENGINE_NAME" ]; then
    echo "Initializing Rust project..."
    # Create a new binary application with the cargo tool
    cargo new --bin "$MODULE_DIR/bin/$ENGINE_NAME" --name "$ENGINE_NAME"
else
    echo "Directory exists. Running cargo init to ensure standard structure..."
    # Initialize existing directory as a crate if needed
    cargo init --bin "$MODULE_DIR/bin/$ENGINE_NAME" --name "$ENGINE_NAME"
fi

# Write Standard Cargo.toml
# Write Standard Cargo.toml
# Configures the package metadata and standard common dependencies
cat > "$MODULE_DIR/bin/$ENGINE_NAME/Cargo.toml" <<EOF
[package]
name = "$ENGINE_NAME"
version = "0.1.0"
edition = "2021"

[dependencies]
# Serde for JSON serialization/deserialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
# Rand for deterministic RNG seeding (common in map gen)
rand = "0.8"
rand_chacha = "0.3"
EOF

# Write Template main.rs (Overwrite to ensure correct structure for new modules)
# We only do this if it looks like the default hello world to avoid clobbering work
if grep -q "println!(\"Hello, world!\");" "$MODULE_DIR/bin/$ENGINE_NAME/src/main.rs"; then
# Overwrite with a file-based job processor template
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
# Create a convenience script to build and deploy the binary
cat > "$MODULE_DIR/install.sh" <<EOF
#!/bin/bash
set -e

# Build the release version of the engine
cd bin/$ENGINE_NAME
cargo build --release
# Copy the compiled binary to the module root
cp target/release/$ENGINE_NAME ../$ENGINE_NAME
# Ensure it is executable
chmod +x ../$ENGINE_NAME
echo "Installed $ENGINE_NAME"
EOF
# Make the install script itself executable
chmod +x "$MODULE_DIR/install.sh"

echo "Module $MODULE_NAME created successfully!"
echo "To build: cd MapGenerator/$MODULE_NAME && ./install.sh"
