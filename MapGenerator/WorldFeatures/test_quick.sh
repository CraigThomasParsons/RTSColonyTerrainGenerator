#!/usr/bin/env bash
#
# Quick WorldFeatures Test (using systemd service)
# Alternative test that uses the existing systemd setup
#

set -euo pipefail

echo "=== WorldFeatures Quick Test (Systemd Method) ==="
echo ""

ROOT="/home/craigpar/Code/RTSColonyTerrainGenerator"
WORLD_FEATURES_DIR="$ROOT/MapGenerator/WorldFeatures"

# Check if service is installed
echo "Step 1: Checking WorldFeatures systemd service..."
if systemctl --user list-unit-files | grep -q worldfeatures.path; then
    echo "✅ worldfeatures.path service found"
else
    echo "⚠️  Service not installed. Running install script..."
    cd "$WORLD_FEATURES_DIR"
    ./install.sh
fi
echo ""

# Check service status
echo "Step 2: Checking service status..."
systemctl --user status worldfeatures.path --no-pager || true
echo ""

# Check for payloads
echo "Step 3: Checking for test payloads..."
cd "$WORLD_FEATURES_DIR"
INBOX_COUNT=$(ls -1 inbox/*.worldpayload 2>/dev/null | wc -l)
OUTBOX_BEFORE=$(ls -1 outbox/*.worldpayload 2>/dev/null | wc -l)

echo "   Inbox: $INBOX_COUNT payloads"
echo "   Outbox before: $OUTBOX_BEFORE payloads"

if [ "$INBOX_COUNT" -eq 0 ]; then
    echo "❌ No payloads in inbox. Pipeline stages before WorldFeatures need to run first."
    echo ""
    echo "   To generate test data:"
    echo "   1. Heightmap → generates .heightmap"
    echo "   2. Tiler → generates .maptiles"
    echo "   3. WeatherAnalyses → generates .weather"
    echo "   4. TreePlanter → generates .worldpayload (WorldFeatures input)"
    exit 1
fi

TEST_PAYLOAD=$(ls -1t inbox/*.worldpayload | head -1)
TEST_JOB_ID=$(basename "$TEST_PAYLOAD" .worldpayload)
echo ""
echo "   Test payload: $(basename "$TEST_PAYLOAD")"
echo "   Job ID: $TEST_JOB_ID"
echo "   Size: $(du -h "$TEST_PAYLOAD" | cut -f1)"
echo ""

# Trigger service manually
echo "Step 4: Triggering WorldFeatures processing..."
echo "   Method: Manual script execution"
echo ""

cd "$WORLD_FEATURES_DIR"
./bin/consume_worldfeatures_job.sh

if [ $? -eq 0 ]; then
    echo "✅ WorldFeatures execution completed"
else
    echo "❌ WorldFeatures execution failed"
    exit 1
fi
echo ""

# Check results
echo "Step 5: Verifying results..."
OUTBOX_AFTER=$(ls -1 outbox/*.worldpayload 2>/dev/null | wc -l)
echo "   Outbox after: $OUTBOX_AFTER payloads"

OUTPUT_FILE="outbox/$TEST_JOB_ID.worldpayload"
if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Output file exists: $(basename "$OUTPUT_FILE")"
    echo "   Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    
    # Show a preview
    echo ""
    echo "   Output preview:"
    head -20 "$OUTPUT_FILE" | jq -r '.job_id, .map, .tiles[0:2]' 2>/dev/null || head -20 "$OUTPUT_FILE"
else
    echo "❌ Output file not created"
    echo "   Expected: $OUTPUT_FILE"
fi
echo ""

# Check logs
LOG_DIR="$ROOT/logs/jobs/$TEST_JOB_ID"
echo "Step 6: Checking logs..."
if [ -d "$LOG_DIR" ]; then
    echo "✅ Log directory: $LOG_DIR"
    ls -lah "$LOG_DIR"/worldfeatures* 2>/dev/null || echo "   (no worldfeatures log yet)"
    
    if [ -f "$LOG_DIR/worldfeatures.log" ]; then
        echo ""
        echo "   Log contents:"
        cat "$LOG_DIR/worldfeatures.log"
    fi
else
    echo "⚠️  Log directory not found: $LOG_DIR"
fi
echo ""

echo "=== Test Complete ==="
echo ""
echo "Next steps:"
echo "  • Check if features were added: diff $TEST_PAYLOAD $OUTPUT_FILE"
echo "  • Move to PathFinder: mv $OUTPUT_FILE $ROOT/MapGenerator/PathFinder/inbox/"
echo "  • View full logs: cat $LOG_DIR/worldfeatures.log"
