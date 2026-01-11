#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="$ROOT/bin"

echo "[tiler] Building (Release)…"
dotnet publish -c Release -o "$BIN/published"

echo "[tiler] Installing launcher…"
cat > "$BIN/tiler.sh" <<'EOF'
#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/published/Tiler" "$@"
EOF

chmod +x "$BIN/tiler.sh"

echo "[tiler] Installed to $BIN/tiler.sh"
