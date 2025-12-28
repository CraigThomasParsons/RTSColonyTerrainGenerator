#!/usr/bin/env bash

# WeatherAnalyses Consumer Wrapper
# Invoked by systemd when a file appears in inbox/

set -e

STAGE_DIR="$HOME/Code/RTSColonyTerrainGenerator/MapGenerator/WeatherAnalyses"
INBOX="$STAGE_DIR/inbox"
OUTBOX="$STAGE_DIR/outbox"
ARCHIVE="$STAGE_DIR/archive"
FAILED="$STAGE_DIR/failed"
BIN="$STAGE_DIR/bin/weather-engine" # Path to compiled Rust binary

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Check if binary exists, try debug if release missing
if [ ! -f "$BIN" ]; then
    BIN="$STAGE_DIR/target/debug/weather-engine"
fi

if [ ! -f "$BIN" ]; then
    log "ERROR: Binary not found at $BIN or release path. Please build the project."
    exit 1
fi

# Process files in inbox
# Note: systemd triggers this script, but we loop to handle any ready files
shopt -s nullglob
for job_file in "$INBOX"/*; do
    if [ -f "$job_file" ]; then
        filename=$(basename "$job_file")
        log "Processing job: $filename"

        # Define output path
        # Output file name: <filename>.weather (replacing extension or appending)
        # Assuming input is likely .heightmap or .json defining the job. 
        # But wait, looking at specs, input is "Input jobs". 
        # If input is heightmap binary, we might want to name output similarly.
        # Let's use the basename + .weather
        output_filename="${filename%.*}.weather"
        output_path="$OUTBOX/$output_filename"
        
        # Invoke Rust binary
        # Usage: weather-engine --input <file> --output <file>
        if "$BIN" --input "$job_file" --output "$output_path"; then
            log "Success. Moving $filename to archive."
            mv "$job_file" "$ARCHIVE/"
        else
            log "FAILURE. Moving $filename to failed."
            mv "$job_file" "$FAILED/"
            # We don't exit 1 here to allow processing other files if any (though systemd usually re-triggers)
            # But for systemd unit stability, exiting with error might be okay if we want to signal failure.
            # However, "Failed jobs are expected and acceptable" per spec. So we swallow the error for systemd?
            # Spec says "Exit cleanly".
        fi
    fi
done

exit 0
