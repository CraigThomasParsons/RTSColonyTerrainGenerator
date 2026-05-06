# WorldFeatures Test Instructions

## Issue Found
The WorldFeatures stage requires Java and Gradle, which were just installed but may not be available in the current shell session.

## Setup (One-Time)
```bash
# Install Java and Gradle (if not already done)
sudo pacman -S jdk-openjdk gradle

# Restart your terminal or run:
exec $SHELL
```

## Test Method 1: Direct Gradle Run
```bash
cd /home/craigpar/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures

# Verify tools are available
java -version
gradle --version

# Build the project
gradle build

# Run WorldFeatures on inbox
gradle run --args="--input inbox --output outbox --log-dir $HOME/Code/RTSColonyTerrainGenerator/logs/jobs"
```

## Test Method 2: Use Test Script
```bash
cd /home/craigpar/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures
./test_worldfeatures.sh
```

## Test Method 3: Systemd Service
```bash
cd /home/craigpar/Code/RTSColonyTerrainGenerator/MapGenerator/WorldFeatures

# Trigger the service manually
./bin/consume_worldfeatures_job.sh

# Or let systemd watch for new files
systemctl --user start worldfeatures.path
```

## Expected Results

### Input
- **Location**: `MapGenerator/WorldFeatures/inbox/*.worldpayload`
- **Source**: TreePlanter output
- **Format**: JSON with tiles array, each tile has decorations

### Processing
WorldFeatures should:
1. Read a .worldpayload file from inbox
2. Analyze the map for potential settlement areas (PSA)
3. Plan features:
   - Resource locations (trees/lumber, mines/caverns)
   - Ridge openings (ramps for layer transitions)
   - Cavern opening (potential player start)
4. Add features to the payload

### Output
- **Location**: `MapGenerator/WorldFeatures/outbox/*.worldpayload`
- **Format**: Same JSON structure with added features
- **Logs**: `logs/jobs/{job_id}/worldfeatures.log`

### Verification Commands
```bash
# Check a sample job ID (replace with actual)
JOB_ID="2cf79cb9-8963-454d-809e-898df862263b"

# Compare input vs output
diff MapGenerator/WorldFeatures/inbox/$JOB_ID.worldpayload \
     MapGenerator/WorldFeatures/outbox/$JOB_ID.worldpayload

# View logs
cat logs/jobs/$JOB_ID/worldfeatures.log

# Check output structure
jq '.tiles[0:5]' MapGenerator/WorldFeatures/outbox/$JOB_ID.worldpayload
```

## Next Stage Handoff
After WorldFeatures completes:
```bash
# Move output to PathFinder inbox (next stage)
mv MapGenerator/WorldFeatures/outbox/$JOB_ID.worldpayload \
   MapGenerator/PathFinder/inbox/
```

## Troubleshooting

### "gradle: command not found"
- Open a new terminal after installing
- Or run: `exec $SHELL`

### "No worldpayload files found"
- Run earlier stages first:
  1. Heightmap
  2. Tiler  
  3. WeatherAnalyses
  4. TreePlanter

### Build errors
```bash
cd MapGenerator/WorldFeatures
gradle clean build
```

### Service not running
```bash
systemctl --user status worldfeatures.path
systemctl --user restart worldfeatures.path
journalctl --user -u worldfeatures.service -f
```

## Manual Test (Minimal)
If you just want to verify the stage can execute:
```bash
# Use smallest payload
cd MapGenerator/WorldFeatures
SMALLEST=$(ls -S inbox/*.worldpayload | tail -1)
JOB_ID=$(basename "$SMALLEST" .worldpayload)

echo "Testing with: $JOB_ID"

# Run
gradle -q run --args="--input $SMALLEST --output outbox --log-dir $HOME/Code/RTSColonyTerrainGenerator/logs/jobs"

# Check result
ls -lh outbox/$JOB_ID.worldpayload
cat logs/jobs/$JOB_ID/worldfeatures.log
```
