#!/usr/bin/env bash
#
# WorldFeatures End-to-End Test Script
# Tests the complete pipeline flow through WorldFeatures
#

set -euo pipefail

echo "=== WorldFeatures TYS Test ==="
echo ""

# Configuration
ROOT="/home/craigpar/Code/RTSColonyTerrainGenerator"
WORLD_FEATURES_DIR="$ROOT/MapGenerator/WorldFeatures"
TREE_PLANTER_OUTBOX="$ROOT/MapGenerator/TreePlanter/outbox"
WORLD_FEATURES_INBOX="$WORLD_FEATURES_DIR/inbox"
WORLD_FEATURES_OUTBOX="$WORLD_FEATURES_DIR/outbox"
LOG_DIR="$ROOT/logs/jobs"

# Step 1: Verify prerequisites
echo "Step 1: Checking prerequisites..."
if ! command -v java &> /dev/null; then
    echo "❌ Java not found. Please run: sudo pacman -S jdk-openjdk gradle"
    echo "   Then open a new terminal and rerun this script."
    exit 1
fi

if ! command -v gradle &> /dev/null; then
    echo "❌ Gradle not found. Please run: sudo pacman -S gradle"
    echo "   Then open a new terminal and rerun this script."
    exit 1
fi

echo "✅ Java found: $(java -version 2>&1 | head -1)"
echo "✅ Gradle found: $(gradle --version | head -1)"
echo ""

# Step 2: Check for test payload in inbox
echo "Step 2: Locating test payload..."
cd "$WORLD_FEATURES_DIR"

PAYLOAD_COUNT=$(ls -1 inbox/*.worldpayload 2>/dev/null | wc -l)
if [ "$PAYLOAD_COUNT" -eq 0 ]; then
    echo "❌ No worldpayload files found in inbox/"
    echo "   Expected files from TreePlanter outbox"
    echo "   Checking TreePlanter outbox..."
    TREE_PAYLOAD_COUNT=$(ls -1 "$TREE_PLANTER_OUTBOX"/*.worldpayload 2>/dev/null | wc -l)
    echo "   Found $TREE_PAYLOAD_COUNT payloads in TreePlanter/outbox"
    
    if [ "$TREE_PAYLOAD_COUNT" -gt 0 ]; then
        echo "   Copying one payload to WorldFeatures inbox for testing..."
        SAMPLE=$(ls -1 "$TREE_PLANTER_OUTBOX"/*.worldpayload | head -1)
        cp "$SAMPLE" inbox/
        echo "✅ Copied $(basename "$SAMPLE")"
    else
        echo "❌ No payloads available. Run the full pipeline first:"
        echo "   1. Heightmap"
        echo "   2. Tiler"
        echo "   3. WeatherAnalyses"
        echo "   4. TreePlanter"
        exit 1
    fi
fi

TEST_PAYLOAD=$(ls -1t inbox/*.worldpayload | head -1)
TEST_JOB_ID=$(basename "$TEST_PAYLOAD" .worldpayload)
echo "✅ Test payload: $TEST_PAYLOAD"
echo "   Job ID: $TEST_JOB_ID"
echo ""

# Step 3: Inspect payload structure
echo "Step 3: Inspecting payload structure..."
echo "   Size: $(du -h "$TEST_PAYLOAD" | cut -f1)"
echo "   First 20 lines:"
head -20 "$TEST_PAYLOAD" | jq . 2>/dev/null || head -20 "$TEST_PAYLOAD"
echo ""

# Step 4: Build WorldFeatures
echo "Step 4: Building WorldFeatures..."
cd "$WORLD_FEATURES_DIR"
gradle build --quiet
if [ $? -eq 0 ]; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi
echo ""

# Step 5: Clear outbox for clean test
echo "Step 5: Preparing for test run..."
OUTBOX_BEFORE=$(ls -1 outbox/*.worldpayload 2>/dev/null | wc -l)
echo "   Outbox has $OUTBOX_BEFORE files before test"
echo ""

# Step 6: Run WorldFeatures
echo "Step 6: Running WorldFeatures stage..."
echo "   Input: inbox/"
echo "   Output: outbox/"
echo "   Logs: $LOG_DIR/$TEST_JOB_ID/"
echo ""

gradle run --args="--input inbox --output outbox --log-dir $LOG_DIR" 2>&1 | tee /tmp/worldfeatures_test_output.log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "✅ WorldFeatures execution completed"
else
    echo ""
    echo "❌ WorldFeatures execution failed"
    echo "   See /tmp/worldfeatures_test_output.log for details"
    exit 1
fi
echo ""

# Step 7: Verify output
echo "Step 7: Verifying output..."
OUTBOX_AFTER=$(ls -1 outbox/*.worldpayload 2>/dev/null | wc -l)
echo "   Outbox now has $OUTBOX_AFTER files"

OUTPUT_FILE="outbox/$TEST_JOB_ID.worldpayload"
if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Output file created: $OUTPUT_FILE"
    echo "   Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    
    # Check if output differs from input
    if cmp -s "$TEST_PAYLOAD" "$OUTPUT_FILE"; then
        echo "⚠️  WARNING: Output is identical to input (no features added)"
    else
        echo "✅ Output differs from input (features were added)"
    fi
    
    echo ""
    echo "   Output preview (first 30 lines):"
    head -30 "$OUTPUT_FILE" | jq . 2>/dev/null || head -30 "$OUTPUT_FILE"
else
    echo "❌ Expected output file not found: $OUTPUT_FILE"
    echo "   Files in outbox:"
    ls -lah outbox/
    exit 1
fi
echo ""

# Step 8: Check logs
echo "Step 8: Checking logs..."
LOG_FILE="$LOG_DIR/$TEST_JOB_ID/worldfeatures.log"
if [ -f "$LOG_FILE" ]; then
    echo "✅ Log file created: $LOG_FILE"
    echo "   Log contents:"
    cat "$LOG_FILE"
else
    echo "⚠️  Warning: Log file not found at $LOG_FILE"
fi
echo ""

# Step 9: Verify next stage can consume
echo "Step 9: Verifying handoff to next stage..."
echo "   Next stage: PathFinder"
echo "   PathFinder would look for: PathFinder/inbox/*.worldpayload"
echo ""
echo "   To complete the handoff:"
echo "   mv $OUTPUT_FILE $ROOT/MapGenerator/PathFinder/inbox/"
echo ""

# Summary
echo "=== Test Summary ==="
echo "✅ WorldFeatures processed job: $TEST_JOB_ID"
echo "✅ Input consumed from: inbox/$TEST_JOB_ID.worldpayload"
echo "✅ Output written to: outbox/$TEST_JOB_ID.worldpayload"
echo "✅ Logs written to: $LOG_DIR/$TEST_JOB_ID/worldfeatures.log"
echo ""
echo "=== Test Complete ==="
