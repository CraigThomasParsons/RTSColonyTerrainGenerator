#!/usr/bin/env bash
#
# TreePlanter queue consumer (ONE job per invocation)
#
# Responsibilities:
# - Scan TreePlanter/inbox/* for a complete <id> set:
#     from_heightmap/<id>.heightmap
#     from_tiler/<id>.maptiles
#     from_weather/<id>.weather
# - Invoke the PHP worker to claim + process exactly one job
#
set -euo pipefail

TREEPLANTER_ROOT="$HOME/MapGenerator/TreePlanter"
PHP_BIN="${PHP_BIN:-/usr/bin/php}"

exec "$PHP_BIN" "$TREEPLANTER_ROOT/run.php" --once