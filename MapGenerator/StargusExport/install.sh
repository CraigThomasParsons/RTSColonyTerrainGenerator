#!/bin/bash
set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "$0")" && pwd)"

chmod +x "$MODULE_ROOT/stargus-exporter"
chmod +x "$MODULE_ROOT/bin/consume_stargusexport_job.sh"

echo "StargusExport installed."
