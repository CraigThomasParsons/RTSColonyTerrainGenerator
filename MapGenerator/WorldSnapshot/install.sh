#!/usr/bin/env bash
set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$MODULE_ROOT/outbox" "$MODULE_ROOT/inbox"

"$MODULE_ROOT/systemd/install.sh"

echo "WorldSnapshot install complete."
